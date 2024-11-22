# manufacturers/sphere_playtastic_170_mm.py

from .playtastic import apply_base_overrides


def apply_overrides(Puzzle, Sphere, Box, Path):
    # Apply the base Playtastic overrides
    apply_base_overrides(Puzzle, Sphere, Box, Path)
    # Apply specific overrides for the 170 mm sphere
    Sphere.SPHERE_DIAMETER = 170
    Sphere.SPHERE_FLANGE_DIAMETER = Sphere.SPHERE_DIAMETER + 20
