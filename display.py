from common import console, Table, Panel, Text, box
from color_utils import (
    color_total_hands,
    color_aggression_stat,
    color_showdown_win,
    color_tightness_score,
)


def print_overview_info(hands, stats):
    """Print an overview panel with additional info."""
    num_hands = len(hands)
    all_players = set(stats.keys())
    if stats:
        avg_vpip = round(sum(s["VPIP (%)"] for s in stats.values()) / len(stats), 2)
        avg_pfr = round(sum(s["PFR (%)"] for s in stats.values()) / len(stats), 2)
        avg_3bet = round(sum(s["3Bet (%)"] for s in stats.values()) / len(stats), 2)
        avg_sd_win = round(
            sum(s["Showdown Win (%)"] for s in stats.values()) / len(stats), 2
        )
        avg_wtsd = round(
            sum(s["Went to Showdown (%)"] for s in stats.values()) / len(stats), 2
        )
    else:
        avg_vpip = avg_pfr = avg_3bet = avg_sd_win = avg_wtsd = 0

    info_text = (
        f"[bold cyan]Overview:[/bold cyan]\n"
        f"[yellow]Total Hands Processed:[/yellow] {num_hands}\n"
        f"[yellow]Unique Players:[/yellow] {len(all_players)}\n"
        f"[yellow]Average VPIP:[/yellow] {avg_vpip}%\n"
        f"[yellow]Average PFR:[/yellow] {avg_pfr}%\n"
        f"[yellow]Average 3Bet:[/yellow] {avg_3bet}%\n"
        f"[yellow]Average Went to Showdown:[/yellow] {avg_wtsd}%\n"
        f"[yellow]Average Showdown Win:[/yellow] {avg_sd_win}%\n"
    )
    console.print(
        Panel(
            info_text,
            title="[bold magenta]Session Overview[/bold magenta]",
            border_style="magenta",
        )
    )


def display_stats(stats, numbered=False, sort_by="Tightness Score"):
    """Display player statistics in a styled table with color coding."""
    if not stats:
        console.print("[bold red]No statistics to display.[/bold red]")
        return {}

    # Ensure sort_by is a valid key
    if sort_by not in stats[next(iter(stats))].keys():
        sort_by = "Tightness Score"

    # Sort
    sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1][sort_by]))

    # Highlight top 3 players in different colors based on chosen sort metric
    rank_colors = ["bold green", "bold cyan", "bold magenta"]

    table = Table(
        title=f"Player Statistics (Sorted by {sort_by})",
        box=box.MINIMAL_DOUBLE_HEAD,
        title_style="bold yellow",
    )
    table.add_column("Player ID", justify="left", style="bright_yellow", no_wrap=True)
    if numbered:
        table.add_column("Number", justify="center", style="white")
    table.add_column("Total Hands", justify="center")
    table.add_column("VPIP (%)", justify="center")
    table.add_column("PFR (%)", justify="center")
    table.add_column("3Bet (%)", justify="center")
    table.add_column("Went to Showdown (%)", justify="center")
    table.add_column("Showdown Win (%)", justify="center")
    table.add_column("Tightness Score", justify="center")

    for idx, (player, stat) in enumerate(sorted_stats.items(), start=1):
        row_style = rank_colors[idx - 1] if idx <= 3 else None

        # Color each cell based on its metric
        th_color = color_total_hands(stat["Total Hands"])
        vpip_color = color_aggression_stat(stat["VPIP (%)"])
        pfr_color = color_aggression_stat(stat["PFR (%)"])
        threebet_color = color_aggression_stat(stat["3Bet (%)"])
        wtsd_color = color_aggression_stat(stat["Went to Showdown (%)"])
        sd_win_color = color_showdown_win(stat["Showdown Win (%)"])
        tight_color = color_tightness_score(stat["Tightness Score"])

        player_text = Text(player, style=row_style) if row_style else Text(player)

        row = [
            player_text,
            Text(str(stat["Total Hands"]), style=th_color),
            Text(str(stat["VPIP (%)"]), style=vpip_color),
            Text(str(stat["PFR (%)"]), style=pfr_color),
            Text(str(stat["3Bet (%)"]), style=threebet_color),
            Text(str(stat["Went to Showdown (%)"]), style=wtsd_color),
            Text(str(stat["Showdown Win (%)"]), style=sd_win_color),
            Text(str(stat["Tightness Score"]), style=tight_color),
        ]

        if numbered:
            row.insert(1, str(idx))

        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(stats)} players shown.[/dim]")

    if numbered:
        return {str(i): p for i, p in enumerate(sorted_stats.keys(), start=1)}
    return {}
