import os
from os import listdir
from os.path import join
from collections import defaultdict
from common import console
from rich.progress import track
import logging
import re
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_player_names(logs_dir):
    """
    Load player names and map IDs to their longest names, removing any leading or trailing quotes.
    """
    player_name_map = {}
    files = [f for f in listdir(logs_dir) if f.endswith(".csv")]

    for file in files:
        df = pd.read_csv(join(logs_dir, file))
        if "entry" not in df.columns:
            continue

        for entry in df["entry"]:
            match = re.search(r"([^\s]+) @ ([^\s]+)", entry)
            if match:
                name, player_id = match.groups()
                name = name.strip('"')  # Remove leading/trailing quotes
                if player_id not in player_name_map or len(name) > len(
                    player_name_map[player_id]
                ):
                    player_name_map[player_id] = name

    return player_name_map


def extract_player_id(log):
    """
    Extract and return the unique player ID from a log entry.
    The ID is the string after '@' and before the next space or special character.
    """
    match = re.search(r"@ ([^\s]+)", log)
    if match:
        return match.group(1).strip()
    return None


def merge_flat_dicts(dict1, dict2):
    """Merge two flat dictionaries."""
    for key, value in dict2.items():
        dict1[key] += value


def merge_nested_dicts(dict1, dict2):
    """Merge two nested dictionaries."""
    for key, value in dict2.items():
        if key in dict1:
            if isinstance(value, dict):
                merge_nested_dicts(dict1[key], value)
            else:
                dict1[key] += value
        else:
            dict1[key] = value


def merge_player_stats(stats, player_name_map):
    """
    Merge statistics for players with the same ID, using the longest name for each ID.

    Parameters:
    - stats (dict): A dictionary of player statistics keyed by player ID.
    - player_name_map (dict): A dictionary mapping player IDs to their longest names.

    Returns:
    - dict: A dictionary of merged statistics keyed by player names.
    """
    id_to_stats = defaultdict(
        lambda: defaultdict(int)
    )  # To aggregate stats by player name

    for player_id, stat_values in stats.items():
        # Resolve the canonical name for this player ID
        canonical_name = player_name_map.get(player_id, player_id)

        # Merge the stats under the resolved name
        for key, value in stat_values.items():
            id_to_stats[canonical_name][key] += value

    # Convert the defaultdict to a regular dictionary for final output
    return dict(id_to_stats)


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
    Process hands and calculate stats, including preflop, 2Bet, 3Bet, cBet, showdown info.
    """
    actions = ["folds", "calls", "raises"]
    flop_actions = ["bets", "checks", "folds", "calls", "raises"]

    preflop = defaultdict(lambda: {action: 0 for action in actions})
    twobets = defaultdict(lambda: {action: 0 for action in actions})
    threebets = defaultdict(lambda: {action: 0 for action in actions})
    cbets = defaultdict(lambda: {action: 0 for action in flop_actions})
    can_2bet = defaultdict(int)
    can_3bet = defaultdict(int)

    showdowns = defaultdict(int)
    showdown_wins = defaultdict(int)

    for hand in track(hands, description="[cyan]Processing hands...[/cyan]"):
        hand_preflop = {}
        raise_count = 0
        hand_twobet = {}
        hand_threebet = {}
        hand_cbet = {}
        street = "preflop"
        first_raiser = ""
        preflop_raiser = ""
        possible_2bettors = set()
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
                            possible_2bettors.add(player)
                        if raise_count == 2:
                            possible_3bettors.add(player)
                        if player not in hand_preflop:
                            hand_preflop[player] = action
                        if action == "raises":
                            raise_count += 1
                            if raise_count == 1:
                                first_raiser = player
                            elif raise_count == 2:
                                hand_twobet[player] = action
                            elif raise_count == 3:
                                hand_threebet[player] = action

            # Flop processing (for c-bets and other postflop actions)
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

            # Detect showdown lines: "shows"
            if "shows a" in log:
                player = extract_player_id(log)
                players_shown.add(player)

            # Detect pot collection (winner) lines
            if "collected" in log and "from pot" in log:
                player = extract_player_id(log)
                players_collected.add(player)

        # Update global dictionaries for preflop, 2bet, threebet, cbet
        for player, action in hand_preflop.items():
            preflop[player][action] += 1

        for player, action in hand_twobet.items():
            twobets[player][action] += 1

        for player, action in hand_threebet.items():
            threebets[player][action] += 1

        for player, action in hand_cbet.items():
            cbets[player][action] += 1

        for player in possible_2bettors:
            can_2bet[player] += 1

        for player in possible_3bettors:
            can_3bet[player] += 1

        # Showdown calculation:
        if players_shown:
            showdown_occurred = True

        if showdown_occurred:
            # All players who showed participated in a showdown
            for player in players_shown:
                showdowns[player] += 1

            # Winners: showed + collected
            for player in players_shown:
                if player in players_collected:
                    showdown_wins[player] += 1

    # Merge stats after processing
    stats = {
        "preflop": preflop,
        "twobets": twobets,
        "threebets": threebets,
        "cbets": cbets,
        "can_2bet": can_2bet,
        "can_3bet": can_3bet,
        "showdowns": showdowns,
        "showdown_wins": showdown_wins,
    }

    return (
        stats["preflop"],
        stats["twobets"],
        stats["threebets"],
        stats["cbets"],
        stats["can_2bet"],
        stats["can_3bet"],
        stats["showdowns"],
        stats["showdown_wins"],
    )


def calculate_stats(
    preflop, twobets, threebets, cbets, can_2bet, can_3bet, showdowns, showdown_wins
):
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

        if player in twobets:
            if can_2bet[player] > 0:
                twobet = round(100 * twobets[player]["raises"] / can_2bet[player])
            else:
                twobet = 0
        else:
            twobet = 0

        if player in threebets:
            if can_3bet[player] > 0:
                threebet = round(100 * threebets[player]["raises"] / can_3bet[player])
            else:
                threebet = 0
        else:
            threebet = 0

        tightness_score = (
            (1 - vpip / 100) * 0.4
            + (1 - pfr / 100) * 0.25
            + (1 - twobet / 100) * 0.2
            + (1 - threebet / 100) * 0.15
        )
        tightness_score = round(tightness_score * 100, 1)

        player_showdowns = showdowns[player] if player in showdowns else 0
        player_showdown_wins = showdown_wins[player] if player in showdown_wins else 0
        showdown_win_pct = (
            round((player_showdown_wins / player_showdowns) * 100, 2)
            if player_showdowns > 0
            else 0.0
        )
        went_to_showdown_pct = (
            round((player_showdowns / num_hands) * 100, 2) if num_hands > 0 else 0.0
        )

        stats[player] = {
            "Total Hands": num_hands,
            "VPIP (%)": vpip,
            "PFR (%)": pfr,
            "2Bet (%)": twobet,
            "3Bet (%)": threebet,
            "Went to Showdown (%)": went_to_showdown_pct,
            "Showdown Win (%)": showdown_win_pct,
            "Tightness Score": tightness_score,
        }
    return stats
