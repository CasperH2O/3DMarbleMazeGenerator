# manufacturers/sphere_playtastic_120_mm.py

from .sphere_playtastic import apply_base_overrides


def apply_overrides(Puzzle, Sphere, Box, Path):
    
    # Apply the base Playtastic overrides
    apply_base_overrides(Puzzle, Sphere, Box, Path)
    
    # Apply specific overrides for the 120 mm sphere    
    Sphere.SPHERE_DIAMETER = 120
    Sphere.SPHERE_FLANGE_DIAMETER = Sphere.SPHERE_DIAMETER + 4 * 2
    Sphere.SHELL_THICKNESS = 0.3
    Sphere.MOUNTING_HOLE_DIAMETER = 6
    Sphere.MOUNTING_RING_THICKNESS = 4
