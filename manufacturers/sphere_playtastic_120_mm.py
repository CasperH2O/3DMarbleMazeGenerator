# manufacturers/sphere_playtastic_120_mm.py

from .sphere_playtastic import apply_base_overrides


def apply_overrides(Puzzle, Sphere, Box, Path):
    
    # Apply the base Playtastic overrides
    apply_base_overrides(Puzzle, Sphere, Box, Path)
    
    # Apply specific overrides for the 120 mm sphere    
    Sphere.SPHERE_FLANGE_DIAMETER = 132 
    Sphere.SPHERE_FLANGE_INNER_DIAMETER = 117.4
    Sphere.SPHERE_DIAMETER = Sphere.SPHERE_FLANGE_INNER_DIAMETER
    Sphere.SPHERE_FLANGE_SLOT_ANGLE = 8
    Sphere.SHELL_THICKNESS = 0.3
    Sphere.MOUNTING_HOLE_DIAMETER = 6
    Sphere.MOUNTING_RING_THICKNESS = 8.3
    Sphere.MOUNTING_RING_EDGE = 1.6
    Sphere.MOUNTING_RING_INNER_HEIGHT = 3.3
    Sphere.MOUNTING_BRIDGE_HEIGHT = Sphere.MOUNTING_RING_INNER_HEIGHT - 2 * Sphere.SHELL_THICKNESS
