# themes/glow_in_the_dark.py

def apply_overrides(puzzle, sphere, box, path):
    """Set glow in the dark theme specific configurations"""
    puzzle.BALL_COLOR = (57, 255, 20)
    puzzle.PATH_COLOR = (57, 255, 20)
    puzzle.PATH_ACCENT_COLOR = (40, 40, 43)
    puzzle.TEXT_COLOR = (57, 255, 20)
    puzzle.MOUNTING_RING_COLOR = (40, 40, 43)