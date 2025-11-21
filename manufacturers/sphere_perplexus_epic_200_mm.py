# manufacturers/sphere_perplexus_epic_200_mm.py
from cad.cases.case_model_base import CaseShape


def apply_overrides(puzzle, sphere, box, path):
    # Apply the base overrides
    puzzle.CASE_SHAPE = CaseShape.SPHERE_EPIC
    sphere.SPHERE_FLANGE_DIAMETER = 214  # Measured
    sphere.SPHERE_DIAMETER = 208.5 - 2 * 5  # Measured
    sphere.SHELL_THICKNESS = 0.25  # Measured
    sphere.SPHERE_FLANGE_INNER_DIAMETER = 197  # ?

    sphere.NUMBER_OF_MOUNTING_POINTS = 8
    sphere.MOUNTING_HOLE_DIAMETER = 3
    sphere.MOUNTING_RING_THICKNESS = 8.3
    sphere.MOUNTING_RING_EDGE = 1.6
    sphere.MOUNTING_RING_INNER_HEIGHT = 3.3
    sphere.MOUNTING_BRIDGE_HEIGHT = (
        sphere.MOUNTING_RING_INNER_HEIGHT - 2 * sphere.SHELL_THICKNESS
    )
