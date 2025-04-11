# themes/marble.py
from config import Box, Manufacturing, Path, Puzzle, Sphere


def apply_overrides(
    puzzle: Puzzle, sphere: Sphere, box: Box, path: Path, manufacturing: Manufacturing
):
    """
    Set wood, white marble, and brass theme specific configurations
    """
    puzzle.BALL_COLOR = "#FFFFFF"  # White (Marble)
    puzzle.PATH_COLORS = ["#D4D2D1"]  # Light Grey (White Marble)
    puzzle.PATH_ACCENT_COLOR = "#F4C131"  # Brass Gold
    puzzle.TEXT_COLOR = "#CC861C"  # Darker Brass
    puzzle.MOUNTING_RING_COLOR = "#523429"  # Wood Tone
