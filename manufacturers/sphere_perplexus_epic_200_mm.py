# manufacturers/sphere_perplexus_epic_200_mm.py
from cad.cases.case_model_base import CaseShape


def apply_overrides(puzzle, sphere, box, path):
    # Apply the base overrides
    puzzle.CASE_SHAPE = CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES
    sphere.SHELL_THICKNESS = 0.25
    sphere.MOUNTING_RING_THICKNESS = 4
    sphere.MOUNTING_HOLE_DIAMETER = 3.5
    sphere.MOUNTING_HOLE_AMOUNT = 8
    sphere.NUMBER_OF_MOUNTING_POINTS = 8

    # Apply specific overrides for the 200 mm sphere
    sphere.SPHERE_FLANGE_DIAMETER = 212 #132
    sphere.SPHERE_FLANGE_INNER_DIAMETER = 197#117.4
    sphere.SPHERE_DIAMETER = 197.5#117.9
    sphere.SPHERE_FLANGE_SLOT_ANGLE = 8
    sphere.SHELL_THICKNESS = 0.3
    sphere.MOUNTING_HOLE_DIAMETER = 6
    sphere.MOUNTING_RING_THICKNESS = 8.3
    sphere.MOUNTING_RING_EDGE = 1.6
    sphere.MOUNTING_RING_INNER_HEIGHT = 3.3
    sphere.MOUNTING_BRIDGE_HEIGHT = (
        sphere.MOUNTING_RING_INNER_HEIGHT - 2 * sphere.SHELL_THICKNESS
    )
