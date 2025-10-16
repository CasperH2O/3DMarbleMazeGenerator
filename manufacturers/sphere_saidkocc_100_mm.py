# manufacturers/sphere_saidkocc_100_mm.py

from cad.cases.case_model_base import CaseShape


def apply_overrides(puzzle, sphere, box, path):
    puzzle.CASE_SHAPE = CaseShape.SPHERE_WITH_FLANGE

    sphere.SPHERE_DIAMETER = 100  # Diameter of the sphere in mm
    sphere.SPHERE_FLANGE_DIAMETER = (
        sphere.SPHERE_DIAMETER + 20
    )  # Diameter of the flange
    sphere.SHELL_THICKNESS = 2.5  # Thickness of the sphere shell in mm
    sphere.MOUNTING_RING_THICKNESS = 3  # Thickness of the mounting ring in mm
    sphere.MOUNTING_HOLE_DIAMETER = 4.2  # Diameter of the mounting holes in mm
    sphere.MOUNTING_HOLE_AMOUNT = 4  # Number of mounting holes
    sphere.NUMBER_OF_MOUNTING_POINTS = 4  # Number of mounting points
