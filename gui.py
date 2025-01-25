import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from stats_processor import (
    calculate_stats,
    process_hands,
    parse_hands,
    load_player_names,
    merge_player_stats,
)
from duplicate_utils import load_logs


class PokerStatsGUI:
    def __init__(self, root, stats):
        self.root = root
        self.stats = stats
        self.filtered_stats = stats.copy()
        self.whitelist = set()
        self.show_whitelist_only = False

        self.root.title("Poker Statistics Board")
        self.root.geometry("1400x700")

        # Styling
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Treeview", rowheight=30)
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

        self.create_widgets()

    def create_widgets(self):
        # Title
        title_label = tk.Label(
            self.root,
            text="Poker Statistics Board",
            font=("Helvetica", 18, "bold"),
            fg="white",
            bg="blue",
            pady=10,
        )
        title_label.pack(fill="x")

        # Filter and Sort Controls
        controls_frame = tk.Frame(self.root)
        controls_frame.pack(fill="x", padx=10, pady=5)

        # Sorting dropdown
        self.sort_var = tk.StringVar(value="Tightness Score")
        sort_label = tk.Label(controls_frame, text="Sort By:", font=("Helvetica", 12))
        sort_label.pack(side="left", padx=5)
        sort_dropdown = ttk.Combobox(
            controls_frame,
            textvariable=self.sort_var,
            values=[
                "Tightness Score",
                "Total Hands",
                "VPIP (%)",
                "PFR (%)",
                "2Bet (%)",
                "3Bet (%)",
                "Went to Showdown (%)",
                "Showdown Win (%)",
            ],
            state="readonly",
        )
        sort_dropdown.pack(side="left", padx=5)
        sort_button = ttk.Button(controls_frame, text="Sort", command=self.sort_stats)
        sort_button.pack(side="left", padx=5)

        # Whitelist Management
        self.whitelist_frame = tk.Frame(
            self.root, bg="lightgray", bd=1, relief="sunken"
        )
        self.whitelist_frame.pack(fill="x", padx=10, pady=5)

        whitelist_title = tk.Label(
            self.whitelist_frame,
            text="Whitelist Management",
            font=("Helvetica", 14, "bold"),
            bg="lightgray",
        )
        whitelist_title.pack(side="top", pady=5)

        whitelist_add_label = tk.Label(
            self.whitelist_frame,
            text="Add Player ID:",
            font=("Helvetica", 12),
            bg="lightgray",
        )
        whitelist_add_label.pack(side="left", padx=10)
        self.whitelist_add_entry = ttk.Entry(self.whitelist_frame, width=30)
        self.whitelist_add_entry.pack(side="left", padx=5)
        self.whitelist_add_entry.bind("<Return>", lambda event: self.add_to_whitelist())
        add_button = ttk.Button(
            self.whitelist_frame, text="Add", command=self.add_to_whitelist
        )
        add_button.pack(side="left", padx=5)

        remove_button = ttk.Button(
            self.whitelist_frame, text="Remove", command=self.remove_from_whitelist
        )
        remove_button.pack(side="left", padx=5)

        reset_button = ttk.Button(
            self.whitelist_frame, text="Clear Whitelist", command=self.clear_whitelist
        )
        reset_button.pack(side="left", padx=5)

        toggle_view_button = ttk.Button(
            self.whitelist_frame,
            text="Toggle Whitelist View",
            command=self.toggle_whitelist_view,
        )
        toggle_view_button.pack(side="left", padx=5)

        # Stats Table
        self.table = ttk.Treeview(
            self.root,
            columns=[
                "Player Name",
                "Total Hands",
                "VPIP (%)",
                "PFR (%)",
                "2Bet (%)",
                "3Bet (%)",
                "Went to Showdown (%)",
                "Showdown Win (%)",
                "Tightness Score",
            ],
            show="headings",
        )
        for col in self.table["columns"]:
            self.table.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.table.column(col, anchor="center", width=120)

        self.table.pack(fill="both", expand=True, padx=10, pady=10)

        # Search functionality
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill="x", padx=10, pady=5)

        search_label = tk.Label(search_frame, text="Search:", font=("Helvetica", 12))
        search_label.pack(side="left", padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda event: self.search_table())

        # Populate initial stats
        self.populate_table(self.stats)

    def populate_table(self, stats):
        """Populate the table with player statistics."""
        for row in self.table.get_children():
            self.table.delete(row)

        for player_name, stat in stats.items():
            if self.show_whitelist_only and player_name not in self.whitelist:
                continue

            tags = ("whitelisted",) if player_name in self.whitelist else ()
            self.table.insert(
                "",
                "end",
                values=(
                    player_name,  # Display resolved player name
                    stat["Total Hands"],
                    stat["VPIP (%)"],
                    stat["PFR (%)"],
                    stat["2Bet (%)"],
                    stat["3Bet (%)"],
                    stat["Went to Showdown (%)"],
                    stat["Showdown Win (%)"],
                    stat["Tightness Score"],
                ),
                tags=tags,
            )

        self.table.tag_configure("whitelisted", background="lightgreen")

    def sort_stats(self):
        """Sort the statistics based on the selected column."""
        sort_by = self.sort_var.get()
        # Ensure the selected sort_by is valid
        if (
            not self.filtered_stats
            or sort_by not in next(iter(self.filtered_stats.values())).keys()
        ):
            sort_by = "Tightness Score"  # Default to Tightness Score if invalid
        # Sort the stats
        self.filtered_stats = dict(
            sorted(
                self.filtered_stats.items(),
                key=lambda item: item[1][sort_by],
                reverse=True,
            )
        )
        # Re-populate the table with sorted stats
        self.populate_table(self.filtered_stats)

    def add_to_whitelist(self):
        """Add a player name to the whitelist."""
        player_name = self.whitelist_add_entry.get().strip()
        if not player_name:
            messagebox.showwarning("Warning", "Please enter a valid Player Name.")
            return

        self.whitelist.add(player_name)
        self.populate_table(self.stats)

    def remove_from_whitelist(self):
        """Remove a player name from the whitelist."""
        player_name = self.whitelist_add_entry.get().strip()
        if player_name in self.whitelist:
            self.whitelist.remove(player_name)
            self.populate_table(self.stats)

    def clear_whitelist(self):
        """Clear the entire whitelist."""
        self.whitelist = set()
        self.populate_table(self.stats)

    def toggle_whitelist_view(self):
        """Toggle the view to show only whitelisted players or all players."""
        self.show_whitelist_only = not self.show_whitelist_only
        self.populate_table(self.stats)

    def sort_column(self, col):
        """Sort the table by a specific column when the header is clicked."""
        self.filtered_stats = dict(
            sorted(
                self.filtered_stats.items(),
                key=lambda item: item[1][col],
                reverse=True,
            )
        )
        self.populate_table(self.filtered_stats)

    def search_table(self):
        """Search the table for a specific player or statistic."""
        query = self.search_entry.get().strip().lower()
        if not query:
            self.populate_table(self.stats)
            return

        filtered_stats = {
            player: stat
            for player, stat in self.stats.items()
            if query in player.lower()
            or any(query in str(value).lower() for value in stat.values())
        }
        self.populate_table(filtered_stats)


def launch_gui(log_dir):
    """Launch the GUI for displaying poker stats."""
    logs = load_logs(log_dir)
    if not logs:
        print("No logs found. Exiting GUI.")
        return

    hands = parse_hands(logs)
    preflop, twobets, threebets, cbets, can_2bet, can_3bet, showdowns, showdown_wins = (
        process_hands(hands)
    )

    player_name_map = load_player_names(log_dir)
    stats = calculate_stats(
        preflop, twobets, threebets, cbets, can_2bet, can_3bet, showdowns, showdown_wins
    )
    resolved_stats = merge_player_stats(stats, player_name_map)

    root = tk.Tk()
    PokerStatsGUI(root, resolved_stats)
    root.mainloop()
