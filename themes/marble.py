# themes/marble.py


def apply_overrides(puzzle, sphere, box, path):
    """
    Set wood, white marble, and brass theme specific configurations
    """
    puzzle.BALL_COLOR = "#FFFFFF"  # White (Marble)
    puzzle.PATH_COLOR = "#D4D2D1"  # Light Grey (White Marble)
    puzzle.PATH_ACCENT_COLOR = "#F4C131"  # Brass Gold
    puzzle.TEXT_COLOR = "#CC861C"  # Darker Brass
    puzzle.MOUNTING_RING_COLOR = "#DEC690"  # Wood Tone
