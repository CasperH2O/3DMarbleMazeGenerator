# manufacturers/sphere_playtastic_130_mm.py

from .playtastic import apply_base_overrides


def apply_overrides(Puzzle, Sphere, Box, Path):
    # Apply the base Playtastic overrides
    apply_base_overrides(Puzzle, Sphere, Box)
    # Apply specific overrides for the 130 mm sphere    
    Sphere.SPHERE_DIAMETER = 130
    Sphere.SPHERE_FLANGE_DIAMETER = Sphere.SPHERE_DIAMETER + 20
