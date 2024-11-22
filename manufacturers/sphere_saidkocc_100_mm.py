# manufacturers/sphere_saidkocc_100_mm.py

from puzzle.utils.enums import CaseShape


def apply_overrides(Puzzle, Sphere, Box, Path):
    Puzzle.CASE_SHAPE = CaseShape.SPHERE_WITH_FLANGE
    
    Sphere.SPHERE_DIAMETER = 100           # Diameter of the sphere in mm
    Sphere.SPHERE_FLANGE_DIAMETER = Sphere.SPHERE_DIAMETER + 20 # Diameter of the flange
    Sphere.SHELL_THICKNESS = 2.5           # Thickness of the sphere shell in mm
    Sphere.MOUNTING_RING_THICKNESS = 3     # Thickness of the mounting ring in mm
    Sphere.MOUNTING_HOLE_DIAMETER = 4.2    # Diameter of the mounting holes in mm
    Sphere.MOUNTING_HOLE_AMOUNT = 4        # Number of mounting holes
    Sphere.NUMBER_OF_MOUNTING_POINTS = 4   # Number of mounting points
