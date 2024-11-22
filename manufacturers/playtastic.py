# manufacturers/playtastic.py

from puzzle.utils.enums import CaseShape


def apply_base_overrides(Puzzle, Sphere, Box, Path):
    """Apply common overrides for Playtastic spheres."""
    Puzzle.CASE_SHAPE = CaseShape.SPHERE
    Sphere.SHELL_THICKNESS = 0.5
    Sphere.MOUNTING_RING_THICKNESS = 4
    Sphere.MOUNTING_HOLE_DIAMETER = 3.2
    Sphere.MOUNTING_HOLE_AMOUNT = 6
    Sphere.NUMBER_OF_MOUNTING_POINTS = 4
