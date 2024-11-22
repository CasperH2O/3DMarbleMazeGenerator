# themes/marble.py

def apply_overrides(Puzzle, Sphere, Box, Path):
    '''Set marble theme specific configurations'''
    Puzzle.BALL_COLOR = (1, 1, 1)
    Puzzle.PATH_COLOR = (212, 210, 209)
    Puzzle.PATH_ACCENT_COLOR = (244, 193, 49)
    Puzzle.TEXT_COLOR = (204, 134, 28)
    Puzzle.MOUNTING_RING_COLOR = (222, 198, 144)