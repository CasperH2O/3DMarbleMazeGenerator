# themes/glow_in_the_dark.py
from config import Box, Manufacturing, Path, Puzzle, Sphere


def apply_overrides(
    puzzle: Puzzle, sphere: Sphere, box: Box, path: Path, manufacturing: Manufacturing
):
    """Set glow in the dark theme specific configurations"""
    puzzle.BALL_COLOR = "#CAFFBFFF"  # Neon Green
    puzzle.PATH_COLORS = [
        puzzle.BALL_COLOR,  # First standard color
        "#8A00C4FF",  # Second standard color (Neon Purple)
        "#FF5C00FF",  # Third standard color (Neon Orange)
    ]
    puzzle.PATH_ACCENT_COLOR = "#28282BFF"  # Black
    puzzle.TEXT_COLOR = puzzle.BALL_COLOR
    puzzle.MOUNTING_RING_COLOR = puzzle.PATH_ACCENT_COLOR
    manufacturing.DIVIDE_PATHS_IN = 3  # Divide paths into 3 parts for printing
