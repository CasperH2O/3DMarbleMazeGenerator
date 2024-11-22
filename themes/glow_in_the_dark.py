# themes/glow_in_the_dark.py

def apply_overrides(Puzzle, Sphere, Box, Path):
    '''Set glow in the dark theme specific configurations'''
    Puzzle.BALL_COLOR = (57, 255, 20)
    Puzzle.PATH_COLOR = (57, 255, 20)
    Puzzle.PATH_ACCENT_COLOR = (40, 40, 43)
    Puzzle.TEXT_COLOR = (57, 255, 20)
    Puzzle.MOUNTING_RING_COLOR = (40, 40, 43)