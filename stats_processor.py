from collections import defaultdict
from common import console
from rich.progress import track


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
    Process hands and calculate stats, including preflop, 3bet, cbet, showdown info.
    """
    actions = ["folds", "calls", "raises"]
    flop_actions = ["bets", "checks", "folds", "calls", "raises"]

    preflop = defaultdict(lambda: {action: 0 for action in actions})
    threebets = defaultdict(lambda: {action: 0 for action in actions})
    cbets = defaultdict(lambda: {action: 0 for action in flop_actions})
    can_3bet = defaultdict(int)

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

    return preflop, threebets, cbets, can_3bet, showdowns, showdown_wins


def calculate_stats(preflop, threebets, cbets, can_3bet, showdowns, showdown_wins):
    """
    Calculate and return player statistics.
    Includes Tightness Score, Showdown Win (%), Went to Showdown (%).
    """
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

        # Showdown calculations
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
            "3Bet (%)": threebet,
            "Went to Showdown (%)": went_to_showdown_pct,
            "Showdown Win (%)": showdown_win_pct,
            "Tightness Score": tightness_score,
        }
    return stats
