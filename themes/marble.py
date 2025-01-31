# themes/marble.py

def apply_overrides(puzzle, sphere, box, path):
    """
    Set marble theme specific configurations
    """
    puzzle.BALL_COLOR = (1, 1, 1)
    puzzle.PATH_COLOR = (212, 210, 209)
    puzzle.PATH_ACCENT_COLOR = (244, 193, 49)
    puzzle.TEXT_COLOR = (204, 134, 28)
    puzzle.MOUNTING_RING_COLOR = (222, 198, 144)