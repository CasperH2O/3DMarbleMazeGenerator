# manufacturers/sphere_playtastic_170_mm.py

from .sphere_playtastic import apply_base_overrides


def apply_overrides(puzzle, sphere, box, path):
    
    # Apply the base Playtastic overrides
    apply_base_overrides(puzzle, sphere, box, path)
    
    # Apply specific overrides for the 170 mm sphere
    sphere.SPHERE_DIAMETER = 170
    sphere.SPHERE_FLANGE_DIAMETER = sphere.SPHERE_DIAMETER + 4 * 2
    sphere.SHELL_THICKNESS = 0.3
    sphere.MOUNTING_HOLE_DIAMETER = 6
    sphere.MOUNTING_RING_THICKNESS = 4