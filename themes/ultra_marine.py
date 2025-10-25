# themes/ultra_marine.py
from config import Box, Manufacturing, Path, Puzzle, Sphere


def apply_overrides(
    puzzle: Puzzle, sphere: Sphere, box: Box, path: Path, manufacturing: Manufacturing
):
    """
    Set white, blue and bolt gun metal theme
    """
    puzzle.BALL_COLOR = "#464646"  # Metal
    puzzle.PATH_COLORS = [
        "#4166F5",
    ]  # Ultra marine blue
    puzzle.PATH_ACCENT_COLOR = "#F5F2EA"  # White
    puzzle.TEXT_COLOR = "#F4C131"  # White
    puzzle.MOUNTING_RING_COLOR = "#464646"  # Dark metal grey
    manufacturing.DIVIDE_PATHS_IN = 1
