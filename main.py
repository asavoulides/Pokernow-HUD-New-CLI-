import argparse
from common import console, Panel
from duplicate_utils import remove_duplicate_files, load_logs
from stats_processor import *
from display import print_overview_info, display_stats
from gui import launch_gui  # Import GUI launcher function

__version__ = "1.5.2"  # Increment version for bug fix


def filter_players(stats, player_map):
    selected_players = set()
    while True:
        console.print(
            "[bold yellow]Choose a filtering option:[/bold yellow]\n"
            "1. Filter by player numbers.\n"
            "2. Filter by rank (e.g., top 5 players by a metric).\n"
            "3. Filter by player names (full or partial matches, comma-separated).\n"
            "4. Filter by statistic thresholds (e.g., 'VPIP (%) > 20').\n"
            "5. Done selecting players.\n"
        )
        option = input("Enter your choice (1-5): ").strip()
        if option == "1":
            console.print(
                "[bold yellow]Enter player numbers separated by commas (e.g., 1,3,5):[/bold yellow]"
            )
            selected = input(">> ").split(",")
            selected_players.update(
                player_map[num.strip()] for num in selected if num.strip() in player_map
            )

        elif option == "2":
            console.print(
                "[bold yellow]Enter the metric to rank players by (e.g., 'Tightness Score'):[/bold yellow]"
            )
            metric = input(">> ").strip()
            console.print(
                "[bold yellow]Enter the number of top players to select:[/bold yellow]"
            )
            count = int(input(">> ").strip())
            sorted_players = sorted(
                stats.items(), key=lambda x: x[1].get(metric, 0), reverse=True
            )
            selected_players.update(player for player, _ in sorted_players[:count])

        elif option == "3":
            console.print(
                "[bold yellow]Enter full or partial names, comma-separated (e.g., 'alex, john'):[/bold yellow]"
            )
            name_fragments = input(">> ").strip().lower().split(",")
            for name_fragment in name_fragments:
                name_fragment = name_fragment.strip()
                selected_players.update(
                    player for player in stats.keys() if name_fragment in player.lower()
                )

        elif option == "4":
            console.print(
                "[bold yellow]Enter filtering criteria (e.g., 'VPIP (%) > 20'):[/bold yellow]"
            )
            criteria = input(">> ").strip()
            try:
                field, condition = criteria.split(" ", 1)
                operator, threshold = condition.split(" ")
                threshold = float(threshold)
                selected_players.update(
                    player
                    for player, stat in stats.items()
                    if eval(f"stat['{field}'] {operator} {threshold}")
                )
            except (ValueError, KeyError):
                console.print("[bold red]Invalid input. Please try again.[/bold red]")

        elif option == "5":
            break

        else:
            console.print(
                "[bold red]Invalid choice. Please enter a number between 1 and 5.[/bold red]"
            )

        console.print(
            f"[bold green]Current selected players:[/bold green] {', '.join(selected_players)}"
        )

    return list(selected_players)


def main():
    parser = argparse.ArgumentParser(
        description="Poker Statistics Processor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog="PokerStats",
    )
    parser.add_argument(
        "--logs",
        type=str,
        default="C:\\Users\\alexa\\OneDrive\\Desktop\\Folders\\Poker_Analytics\\logs",
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
        help="Column to sort by: 'Tightness Score', 'Total Hands', 'VPIP (%)', 'PFR (%)', '2Bet (%)', '3Bet (%)', 'Went to Showdown (%)', 'Showdown Win (%)'.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch a GUI for visualizing statistics.",
    )
    parser.add_argument(
        "--version", action="store_true", help="Show the program's version and exit."
    )

    args = parser.parse_args()

    if args.version:
        console.print(f"[bold green]PokerStats Version {__version__}[/bold green]")
        return

    if args.gui:
        launch_gui(args.logs)  # Launch GUI if the --gui flag is provided
        return

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
    preflop, twobets, threebets, cbets, can_2bet, can_3bet, showdowns, showdown_wins = (
        process_hands(hands)
    )

    player_name_map = load_player_names(args.logs)
    stats = calculate_stats(
        preflop, twobets, threebets, cbets, can_2bet, can_3bet, showdowns, showdown_wins
    )

    stats = merge_player_stats(stats, player_name_map)  # Ensure merging by ID works correctly
    print_overview_info(hands, stats)

    player_map = display_stats(stats, numbered=True, sort_by=args.sort)

    if not player_map:
        return

    filtered_players = filter_players(stats, player_map)

    if filtered_players:
        filtered_stats = {player: stats[player] for player in filtered_players}
        console.print("[bold green]Filtered Results:[/bold green]")
        display_stats(filtered_stats, sort_by=args.sort)
    else:
        console.print("[bold blue]No filter applied. Display complete.[/bold blue]")


# Configure logging to display DEBUG messages in the console
logging.basicConfig(
    level=logging.DEBUG,  # Set the log level to DEBUG
    format="%(asctime)s - %(levelname)s - %(message)s",
)


if __name__ == "__main__":
    main()
