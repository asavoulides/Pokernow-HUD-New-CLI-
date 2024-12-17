import argparse
from common import console, Panel
from duplicate_utils import remove_duplicate_files, load_logs
from stats_processor import parse_hands, process_hands, calculate_stats
from display import print_overview_info, display_stats

__version__ = "1.2.0"


def main():
    parser = argparse.ArgumentParser(
        description="Poker Statistics Processor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="PokerStats",
    )
    parser.add_argument(
        "--logs",
        type=str,
        default="C:\\Users\\alexa\\OneDrive\\Desktop\\Folders\\Pokernow-HUD-New-CLI-\\logs",
        help="Path to the directory containing log files.",
    )
    parser.add_argument(
        "--no-duplicates",
        action="store_true",
        help="Skip the duplicate file removal step.",
    )
    parser.add_argument(
        "--sort",
        type=str,
        default="Tightness Score",
        help="Column to sort by: 'Tightness Score', 'Total Hands', 'VPIP (%)', 'PFR (%)', '3Bet (%)', 'Went to Showdown (%)', 'Showdown Win (%)'.",
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Comma-separated list of player numbers to filter after displaying stats. Example: '1,3,5'",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show the program's version and exit."
    )

    args = parser.parse_args()

    if args.version:
        console.print(f"[bold green]PokerStats Version {__version__}[/bold green]")
        return

    # Print a nice header
    console.print(
        Panel(
            "[bold white on blue] Poker Statistics Processor [/bold white on blue]",
            expand=False,
        )
    )
    console.print("[bold green]Starting Poker Statistics Processor...[/bold green]\n")

    if not args.no_duplicates:
        remove_duplicate_files(args.logs)

    logs = load_logs(args.logs)
    if not logs:
        return

    hands = parse_hands(logs)
    preflop, threebets, cbets, can_3bet, showdowns, showdown_wins = process_hands(hands)
    stats = calculate_stats(
        preflop, threebets, cbets, can_3bet, showdowns, showdown_wins
    )

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
