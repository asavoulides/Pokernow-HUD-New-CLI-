import argparse
import pandas as pd
from collections import defaultdict
from os import listdir
from os.path import isfile, join
from rich.console import Console
from rich.progress import track

# Initialize Rich console
console = Console()


def load_logs(path_to_logs):
    """Load and reverse logs from the specified directory."""
    files = [f for f in listdir(path_to_logs) if isfile(join(path_to_logs, f))]
    logs = []
    for file in track(files, description="Loading logs..."):
        df = pd.read_csv(join(path_to_logs, file))
        logs.extend(reversed(df["entry"]))
    return logs


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
                        player = (
                            log[1 : log.index(" @")].lower()
                            if " @" in log
                            else log.split()[0].strip('"').lower()
                        )
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
                        player = (
                            log[1 : log.index(" @")].lower()
                            if " @" in log
                            else log.split()[0].strip('"').lower()
                        )
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
            got_threebet = threebets[player]["calls"] + threebets[player]["folds"]
            fold_threebet = (
                round(100 * threebets[player]["folds"] / got_threebet)
                if got_threebet > 0
                else 0
            )
        else:
            threebet = 0
            fold_threebet = 0

        if player in cbets:
            cbet_total = cbets[player]["bets"] + cbets[player]["checks"]
            cbet = (
                round(100 * cbets[player]["bets"] / cbet_total) if cbet_total > 0 else 0
            )
            face_cbet = (
                cbets[player]["calls"]
                + cbets[player]["raises"]
                + cbets[player]["folds"]
            )
            fold_cbet = (
                round(100 * cbets[player]["folds"] / face_cbet) if face_cbet > 0 else 0
            )
        else:
            cbet = 0
            fold_cbet = 0

        stats[player] = {
            "VPIP (%)": vpip,
            "PFR (%)": pfr,
            "3Bet (%)": threebet,
            "Fold to 3Bet (%)": fold_threebet,
            "CBet (%)": cbet,
            "Fold to CBet (%)": fold_cbet,
        }
    return stats


def display_stats(stats):
    """Display player statistics in a styled table."""
    from rich.table import Table

    table = Table(title="Player Statistics")
    table.add_column("Player", justify="left", style="cyan")
    table.add_column("VPIP (%)", justify="center")
    table.add_column("PFR (%)", justify="center")
    table.add_column("3Bet (%)", justify="center")
    table.add_column("Fold to 3Bet (%)", justify="center")
    table.add_column("CBet (%)", justify="center")
    table.add_column("Fold to CBet (%)", justify="center")

    for player, stat in stats.items():
        table.add_row(
            player,
            str(stat["VPIP (%)"]),
            str(stat["PFR (%)"]),
            str(stat["3Bet (%)"]),
            str(stat["Fold to 3Bet (%)"]),
            str(stat["CBet (%)"]),
            str(stat["Fold to CBet (%)"]),
        )

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Poker Statistics Processor")
    parser.add_argument(
        "--logs",
        type=str,
        required=True,
        help="Path to the directory containing log files",
    )
    args = parser.parse_args()

    console.print("[bold green]Starting Poker Statistics Processor...[/bold green]")
    logs = load_logs(args.logs)
    hands = parse_hands(logs)
    preflop, threebets, cbets, can_3bet = process_hands(hands)
    stats = calculate_stats(preflop, threebets, cbets, can_3bet)
    display_stats(stats)


if __name__ == "__main__":
    main()
