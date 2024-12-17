import argparse
import pandas as pd
from collections import defaultdict
from os import listdir, remove
from os.path import isfile, join
import hashlib
from rich.console import Console
from rich.progress import track
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Initialize Rich console
console = Console()

__version__ = "1.1.0"


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
    duplicates_removed = 0
    for file_path in files:
        file_hash = calculate_file_hash(file_path)
        if file_hash in seen_hashes:
            console.print(
                f"[bold red]Duplicate detected:[/bold red] {file_path} [red](removed)[/red]"
            )
            remove(file_path)
            duplicates_removed += 1
        else:
            seen_hashes[file_hash] = file_path

    if duplicates_removed > 0:
        console.print(
            f"[bold green]Duplicate file removal completed.[/bold green] "
            f"[bright_green]{duplicates_removed} duplicates removed.[/bright_green]"
        )
    else:
        console.print("[bold green]No duplicates found.[/bold green]")


def load_logs(path_to_logs):
    """Load and reverse logs from the specified directory."""
    files = [f for f in listdir(path_to_logs) if isfile(join(path_to_logs, f))]
    if not files:
        console.print(f"[bold red]No log files found in {path_to_logs}![/bold red]")
        return []
    logs = []
    for file in track(files, description="[cyan]Loading logs...[/cyan]"):
        df = pd.read_csv(join(path_to_logs, file))
        if "entry" not in df.columns:
            console.print(f"[yellow]Skipping file {file} as 'entry' column not found.[/yellow]")
            continue
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
            if current_hand:
                hands.append(current_hand)
            current_hand = []
        if in_hand:
            current_hand.append(log)
        if log.startswith("-- starting"):
            in_hand = True
    return hands


def process_hands(hands):
    """
    Process hands and calculate stats.
    Additionally, track showdown information:
    - If a player shows cards at the end of the hand and there's a pot collected,
      that counts as a showdown.
    - Track how many showdowns each player participated in and how many they won.
    """
    actions = ["folds", "calls", "raises"]
    flop_actions = ["bets", "checks", "folds", "calls", "raises"]

    preflop = defaultdict(lambda: {action: 0 for action in actions})
    threebets = defaultdict(lambda: {action: 0 for action in actions})
    cbets = defaultdict(lambda: {action: 0 for action in flop_actions})
    can_3bet = defaultdict(int)

    # New tracking for showdown stats
    showdowns = defaultdict(int)
    showdown_wins = defaultdict(int)

    for hand in track(hands, description="[cyan]Processing hands...[/cyan]"):
        hand_preflop = {}
        raise_count = 0
        hand_threebet = {}
        hand_cbet = {}
        street = "preflop"
        first_raiser = ""
        preflop_raiser = ""
        possible_3bettors = set()
        has_cbet = False

        # Showdown related tracking for this hand
        players_shown = set()
        players_collected = set()
        showdown_occurred = False

        for log in hand:
            # Detect street changes
            if log.startswith("Flop"):
                street = "flop"
            elif log.startswith("Turn"):
                street = "turn"
            elif log.startswith("River"):
                street = "river"

            # Detect player actions preflop
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

            # Flop processing (for c-bets and other postflop actions)
            if street == "flop":
                for action in flop_actions:
                    if action in log:
                        player = extract_player_id(log)
                        if player == preflop_raiser and (action == "bets" or action == "checks"):
                            hand_cbet[player] = action
                            if action == "bets":
                                has_cbet = True
                        elif has_cbet:
                            hand_cbet[player] = action
                            if action == "raises":
                                has_cbet = False

            # Detect showdown lines: "shows"
            if 'shows a' in log:
                player = extract_player_id(log)
                players_shown.add(player)

            # Detect pot collection (winner) lines
            if 'collected' in log and 'from pot' in log:
                player = extract_player_id(log)
                players_collected.add(player)

        # Update global dictionaries for preflop, threebet, cbet
        for player, action in hand_preflop.items():
            preflop[player][action] += 1

        for player, action in hand_threebet.items():
            threebets[player][action] += 1

        for player, action in hand_cbet.items():
            cbets[player][action] += 1

        for player in possible_3bettors:
            can_3bet[player] += 1

        # Showdown calculation:
        # A showdown occurs if at least one player shows their cards.
        if players_shown:
            showdown_occurred = True

        if showdown_occurred:
            # All players who showed participated in a showdown
            for player in players_shown:
                showdowns[player] += 1

            # Players who both showed and collected after showing won the showdown
            # If multiple players collected (split pot) each one that showed also gets a showdown win.
            for player in players_shown:
                if player in players_collected:
                    showdown_wins[player] += 1

    return preflop, threebets, cbets, can_3bet, showdowns, showdown_wins


def calculate_stats(preflop, threebets, cbets, can_3bet, showdowns, showdown_wins):
    """Calculate and return player statistics, including showdown win percentage."""
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
            (1 - vpip / 100) * 0.5
            + (1 - pfr / 100) * 0.3
            + (1 - threebet / 100) * 0.2
        )
        tightness_score = round(tightness_score * 100, 1)

        # Calculate Showdown Win %
        player_showdowns = showdowns[player] if player in showdowns else 0
        player_showdown_wins = showdown_wins[player] if player in showdown_wins else 0
        if player_showdowns > 0:
            sd_win_pct = round((player_showdown_wins / player_showdowns) * 100, 2)
        else:
            sd_win_pct = 0.0

        stats[player] = {
            "Total Hands": num_hands,
            "VPIP (%)": vpip,
            "PFR (%)": pfr,
            "3Bet (%)": threebet,
            "Tightness Score": tightness_score,
            "Showdown Win (%)": sd_win_pct,
            "Showdowns": player_showdowns,
            "Showdowns Won": player_showdown_wins,
        }
    return stats


def display_stats(stats, numbered=False, sort_by="Tightness Score"):
    """Display player statistics in a styled table, sorted by a given column."""
    if not stats:
        console.print("[bold red]No statistics to display.[/bold red]")
        return {}

    if sort_by not in stats[next(iter(stats))].keys():
        sort_by = "Tightness Score"

    sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1][sort_by]))

    # Highlight top 3 players in different colors based on chosen sort metric
    rank_colors = ["bold green", "bold cyan", "bold magenta"]

    table = Table(
        title=f"Player Statistics (Sorted by {sort_by})",
        box=box.MINIMAL_DOUBLE_HEAD,
        title_style="bold yellow"
    )
    table.add_column("Player ID", justify="left", style="bright_yellow", no_wrap=True)
    if numbered:
        table.add_column("Number", justify="center", style="white")
    table.add_column("Total Hands", justify="center", style="cyan")
    table.add_column("VPIP (%)", justify="center", style="cyan")
    table.add_column("PFR (%)", justify="center", style="cyan")
    table.add_column("3Bet (%)", justify="center", style="cyan")
    table.add_column("Tightness Score", justify="center", style="cyan")
    table.add_column("Showdown Win (%)", justify="center", style="cyan")
    table.add_column("Showdowns", justify="center", style="cyan")
    table.add_column("Showdowns Won", justify="center", style="cyan")

    for idx, (player, stat) in enumerate(sorted_stats.items(), start=1):
        row_style = rank_colors[idx - 1] if idx <= 3 else None
        row = [
            Text(player, style=row_style),
            str(stat["Total Hands"]),
            str(stat["VPIP (%)"]),
            str(stat["PFR (%)"]),
            str(stat["3Bet (%)"]),
            str(stat["Tightness Score"]),
            str(stat["Showdown Win (%)"]),
            str(stat["Showdowns"]),
            str(stat["Showdowns Won"]),
        ]
        if numbered:
            row.insert(1, str(idx))
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(stats)} players shown.[/dim]")

    if numbered:
        return {str(i): p for i, p in enumerate(sorted_stats.keys(), start=1)}
    return {}


def print_overview_info(hands, stats):
    """Print an overview panel with additional info."""
    num_hands = len(hands)
    all_players = set(stats.keys())
    if stats:
        avg_vpip = round(sum(s["VPIP (%)"] for s in stats.values()) / len(stats), 2)
        avg_pfr = round(sum(s["PFR (%)"] for s in stats.values()) / len(stats), 2)
        avg_3bet = round(sum(s["3Bet (%)"] for s in stats.values()) / len(stats), 2)
        avg_sd_win = round(sum(s["Showdown Win (%)"] for s in stats.values()) / len(stats), 2)
    else:
        avg_vpip = avg_pfr = avg_3bet = avg_sd_win = 0

    info_text = (
        f"[bold cyan]Overview:[/bold cyan]\n"
        f"[yellow]Total Hands Processed:[/yellow] {num_hands}\n"
        f"[yellow]Unique Players:[/yellow] {len(all_players)}\n"
        f"[yellow]Average VPIP:[/yellow] {avg_vpip}%\n"
        f"[yellow]Average PFR:[/yellow] {avg_pfr}%\n"
        f"[yellow]Average 3Bet:[/yellow] {avg_3bet}%\n"
        f"[yellow]Average Showdown Win:[/yellow] {avg_sd_win}%\n"
    )
    console.print(Panel(info_text, title="[bold magenta]Session Overview[/bold magenta]", border_style="magenta"))


def main():
    parser = argparse.ArgumentParser(
        description="Poker Statistics Processor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="PokerStats"
    )
    parser.add_argument(
        "--logs",
        type=str,
        default="C:\\Users\\alexa\\OneDrive\\Desktop\\Folders\\Pokernow-HUD-New-CLI-\\logs",
        help="Path to the directory containing log files."
    )
    parser.add_argument(
        "--no-duplicates",
        action="store_true",
        help="Skip the duplicate file removal step."
    )
    parser.add_argument(
        "--sort",
        type=str,
        default="Tightness Score",
        help="Column to sort by: 'Tightness Score', 'Total Hands', 'VPIP (%)', 'PFR (%)', '3Bet (%)', or 'Showdown Win (%)'."
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Comma-separated list of player numbers to filter after displaying stats. Example: '1,3,5'"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the program's version and exit."
    )

    args = parser.parse_args()

    if args.version:
        console.print(f"[bold green]PokerStats Version {__version__}[/bold green]")
        return

    # Print a nice header
    console.print(Panel("[bold white on blue] Poker Statistics Processor [/bold white on blue]", expand=False))
    console.print("[bold green]Starting Poker Statistics Processor...[/bold green]\n")

    if not args.no_duplicates:
        remove_duplicate_files(args.logs)

    logs = load_logs(args.logs)
    if not logs:
        return

    hands = parse_hands(logs)
    preflop, threebets, cbets, can_3bet, showdowns, showdown_wins = process_hands(hands)
    stats = calculate_stats(preflop, threebets, cbets, can_3bet, showdowns, showdown_wins)

    # Print overview info
    print_overview_info(hands, stats)

    player_map = display_stats(stats, numbered=True, sort_by=args.sort)

    if not player_map:
        return

    # If user provided a filter through CLI
    if args.filter:
        selected = [x.strip() for x in args.filter.split(",")]
    else:
        console.print(
            "[bold yellow]Enter player numbers separated by commas to filter the chart (or leave empty to skip):[/bold yellow]"
        )
        selected = input(">> ").split(",")

    selected = [num.strip() for num in selected if num.strip()]
    if selected:
        selected_stats = {
            player_map[num]: stats[player_map[num]]
            for num in selected
            if num in player_map
        }
        console.print("[bold green]Filtered Results:[/bold green]")
        display_stats(selected_stats, sort_by=args.sort)
    else:
        console.print("[bold blue]No filter applied. Display complete.[/bold blue]")


if __name__ == "__main__":
    main()
