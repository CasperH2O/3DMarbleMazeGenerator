# manufacturers/playtastic.py

from cad.cases.case_model_base import CaseShape


def apply_base_overrides(puzzle, sphere, box, path):
    """Apply common overrides for Playtastic spheres."""
    puzzle.CASE_SHAPE = CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES
    sphere.SHELL_THICKNESS = 0.25
    sphere.MOUNTING_RING_THICKNESS = 4
    sphere.MOUNTING_HOLE_DIAMETER = 3.5
    sphere.MOUNTING_HOLE_AMOUNT = 6
    sphere.NUMBER_OF_MOUNTING_POINTS = 6
