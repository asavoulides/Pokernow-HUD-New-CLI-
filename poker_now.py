import argparse
import pandas as pd
from collections import defaultdict
from os import listdir, remove
from os.path import isfile, join
import hashlib
from rich.console import Console
from rich.progress import track

# Initialize Rich console
console = Console()


def calculate_file_hash(file_path):
    """Calculate the hash of a file to detect duplicates."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as file:
        buf = file.read()
        hasher.update(buf)
    return hasher.hexdigest()


def remove_duplicate_files(path_to_logs):
    """Remove duplicate files from the logs directory based on file content."""
    files = [
        join(path_to_logs, f)
        for f in listdir(path_to_logs)
        if isfile(join(path_to_logs, f))
    ]
    seen_hashes = {}
    for file_path in files:
        file_hash = calculate_file_hash(file_path)
        if file_hash in seen_hashes:
            console.print(
                f"[bold red]Duplicate detected:[/bold red] {file_path} (removed)"
            )
            remove(file_path)
        else:
            seen_hashes[file_hash] = file_path
    console.print("[bold green]Duplicate file removal completed.[/bold green]")


def load_logs(path_to_logs):
    """Load and reverse logs from the specified directory."""
    files = [f for f in listdir(path_to_logs) if isfile(join(path_to_logs, f))]
    logs = []
    for file in track(files, description="Loading logs..."):
        df = pd.read_csv(join(path_to_logs, file))
        logs.extend(reversed(df["entry"]))
    return logs


def extract_player_id(log):
    """Extract and return the unique player ID from a log entry."""
    if " @" in log:
        return log[1 : log.index(" @")].lower()
    return log.split()[0].strip('"').lower()


def parse_hands(logs):
    """Extract individual hands from logs."""
    hands = []
    in_hand = False
    current_hand = []
    for log in logs:
        if log.startswith("-- ending"):
            in_hand = False
            hands.append(current_hand)
            current_hand = []
        if in_hand:
            current_hand.append(log)
        if log.startswith("-- starting"):
            in_hand = True
    return hands


def process_hands(hands):
    """Process hands and calculate stats."""
    actions = ["folds", "calls", "raises"]
    flop_actions = ["bets", "checks", "folds", "calls", "raises"]

    preflop = defaultdict(lambda: {action: 0 for action in actions})
    threebets = defaultdict(lambda: {action: 0 for action in actions})
    cbets = defaultdict(lambda: {action: 0 for action in flop_actions})
    can_3bet = defaultdict(int)

    for hand in track(hands, description="Processing hands..."):
        hand_preflop = {}
        raise_count = 0
        hand_threebet = {}
        hand_cbet = {}
        street = "preflop"
        first_raiser = ""
        preflop_raiser = ""
        possible_3bettors = set()
        has_cbet = False

        for log in hand:
            if log.startswith("Flop"):
                street = "flop"
            elif log.startswith("Turn"):
                street = "turn"
            elif log.startswith("River"):
                street = "river"

            # Preflop processing
            if street == "preflop":
                for action in actions:
                    if action in log:
                        player = extract_player_id(log)
                        if raise_count == 1:
                            possible_3bettors.add(player)
                        if player not in hand_preflop:
                            hand_preflop[player] = action
                        if action == "raises":
                            preflop_raiser = player
                            raise_count += 1
                            if raise_count == 1:
                                first_raiser = player
                            if raise_count == 2:
                                hand_threebet[player] = action
                        elif raise_count == 2 and player == first_raiser:
                            hand_threebet[player] = action

            # Flop processing
            if street == "flop":
                for action in flop_actions:
                    if action in log:
                        player = extract_player_id(log)
                        if player == preflop_raiser and (
                            action == "bets" or action == "checks"
                        ):
                            hand_cbet[player] = action
                            if action == "bets":
                                has_cbet = True
                        elif has_cbet:
                            hand_cbet[player] = action
                            if action == "raises":
                                has_cbet = False

        # Update global dictionaries
        for player, action in hand_preflop.items():
            preflop[player][action] += 1

        for player, action in hand_threebet.items():
            threebets[player][action] += 1

        for player, action in hand_cbet.items():
            cbets[player][action] += 1

        for player in possible_3bettors:
            can_3bet[player] += 1

    return preflop, threebets, cbets, can_3bet


def calculate_stats(preflop, threebets, cbets, can_3bet):
    """Calculate and return player statistics."""
    stats = {}
    for player, player_actions in preflop.items():
        num_hands = sum(player_actions.values())
        vpip = (
            round(
                100 * (player_actions["calls"] + player_actions["raises"]) / num_hands
            )
            if num_hands > 0
            else 0
        )
        pfr = round(100 * player_actions["raises"] / num_hands) if num_hands > 0 else 0

        if player in threebets:
            if can_3bet[player] > 0:
                threebet = round(100 * threebets[player]["raises"] / can_3bet[player])
            else:
                threebet = 0
        else:
            threebet = 0

        # Calculate Tightness Score
        tightness_score = (
            (1 - vpip / 100) * 0.5 + (1 - pfr / 100) * 0.3 + (1 - threebet / 100) * 0.2
        )
        tightness_score = round(tightness_score * 100, 1)

        stats[player] = {
            "Total Hands": num_hands,
            "VPIP (%)": vpip,
            "PFR (%)": pfr,
            "3Bet (%)": threebet,
            "Tightness Score": tightness_score,
        }
    return stats


def display_stats(stats, numbered=False):
    """Display player statistics in a styled table, sorted by Tightness Score."""
    from rich.table import Table

    # Sort stats by Tightness Score
    sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1]["Tightness Score"]))

    table = Table(title="Player Statistics (Sorted by Tightness Score)")
    table.add_column("Player ID", justify="left", style="cyan")
    if numbered:
        table.add_column("Number", justify="center")
    table.add_column("Total Hands", justify="center")
    table.add_column("VPIP (%)", justify="center")
    table.add_column("PFR (%)", justify="center")
    table.add_column("3Bet (%)", justify="center")
    table.add_column("Tightness Score", justify="center")

    for idx, (player, stat) in enumerate(sorted_stats.items(), start=1):
        row = [
            player,
            str(stat["Total Hands"]),
            str(stat["VPIP (%)"]),
            str(stat["PFR (%)"]),
            str(stat["3Bet (%)"]),
            str(stat["Tightness Score"]),
        ]
        if numbered:
            row.insert(1, str(idx))
        table.add_row(*row)

    console.print(table)

    if numbered:
        return {
            str(idx): player for idx, player in enumerate(sorted_stats.keys(), start=1)
        }


def main():
    parser = argparse.ArgumentParser(description="Poker Statistics Processor")
    parser.add_argument(
        "--logs",
        type=str,
        default="C:\\Users\\alexa\\PokerNow-HUD-1\\logs",
        help="Path to the directory containing log files",
    )
    args = parser.parse_args()

    console.print("[bold green]Starting Poker Statistics Processor...[/bold green]")
    remove_duplicate_files(args.logs)
    logs = load_logs(args.logs)
    hands = parse_hands(logs)
    preflop, threebets, cbets, can_3bet = process_hands(hands)
    stats = calculate_stats(preflop, threebets, cbets, can_3bet)

    player_map = display_stats(stats, numbered=True)
    console.print(
        "[bold yellow]Enter player numbers separated by commas to filter the chart:[/bold yellow]"
    )
    selected = input(">> ").split(",")

    selected_stats = {
        player_map[num.strip()]: stats[player_map[num.strip()]]
        for num in selected
        if num.strip() in player_map
    }
    console.print("[bold green]Filtered Results:[/bold green]")
    display_stats(selected_stats)


if __name__ == "__main__":
    main()
