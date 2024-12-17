def color_by_threshold(
    value,
    low_color="green",
    mid_color="yellow",
    high_color="red",
    low_thresh=None,
    high_thresh=None,
):
    """
    Generic helper function to color a value based on thresholds.
    - If value < low_thresh => low_color
    - If low_thresh <= value <= high_thresh => mid_color
    - If value > high_thresh => high_color
    """
    if low_thresh is not None and high_thresh is not None:
        if value < low_thresh:
            return low_color
        elif value > high_thresh:
            return high_color
        else:
            return mid_color
    else:
        # If no thresholds provided, default to white
        return "white"


def color_total_hands(hands):
    # <50 = red, 50-200 = yellow, >200 = green
    if hands < 50:
        return "red"
    elif hands <= 200:
        return "yellow"
    else:
        return "green"


def color_aggression_stat(value):
    # For VPIP, PFR, 3Bet, Went to Showdown: <15 green, 15-30 yellow, >30 red
    return color_by_threshold(
        value,
        low_color="green",
        mid_color="yellow",
        high_color="red",
        low_thresh=15,
        high_thresh=30,
    )


def color_showdown_win(value):
    # Showdown Win (%): <40 red, 40-60 yellow, >60 green
    return color_by_threshold(
        value,
        low_color="red",
        mid_color="yellow",
        high_color="green",
        low_thresh=40,
        high_thresh=60,
    )


def color_tightness_score(value):
    # Tightness Score: <30 red, 30-70 yellow, >70 green
    return color_by_threshold(
        value,
        low_color="red",
        mid_color="yellow",
        high_color="green",
        low_thresh=30,
        high_thresh=70,
    )
