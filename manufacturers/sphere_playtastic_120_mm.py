# manufacturers/sphere_playtastic_120_mm.py

from .sphere_playtastic import apply_base_overrides


def apply_overrides(puzzle, sphere, box, path):
    
    # Apply the base Playtastic overrides
    apply_base_overrides(puzzle, sphere, box, path)
    
    # Apply specific overrides for the 120 mm sphere    
    sphere.SPHERE_FLANGE_DIAMETER = 132
    sphere.SPHERE_FLANGE_INNER_DIAMETER = 117.4
    sphere.SPHERE_DIAMETER = sphere.SPHERE_FLANGE_INNER_DIAMETER
    sphere.SPHERE_FLANGE_SLOT_ANGLE = 8
    sphere.SHELL_THICKNESS = 0.3
    sphere.MOUNTING_HOLE_DIAMETER = 6
    sphere.MOUNTING_RING_THICKNESS = 8.3
    sphere.MOUNTING_RING_EDGE = 1.6
    sphere.MOUNTING_RING_INNER_HEIGHT = 3.3
    sphere.MOUNTING_BRIDGE_HEIGHT = sphere.MOUNTING_RING_INNER_HEIGHT - 2 * sphere.SHELL_THICKNESS
