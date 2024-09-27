# utils/config.py

# Puzzle configuration
DIAMETER = 100  # Diameter of the sphere in mm
SPHERE_FLANGE_DIAMETER = 130  # Flange diameter
SHELL_THICKNESS = 3  # Thickness of the shell in mm
RING_THICKNESS = 3  # Thickness of the mounting ring
BALL_DIAMETER = 4  # Diameter of the ball
MOUNTING_HOLE_DIAMETER = 3  # Diameter of the mounting holes
MOUNTING_HOLE_AMOUNT = 5  # Number of mounting holes
NODE_SIZE = 10  # Node size in mm
SEED = 42  # Random seed
WIDTH = 100
HEIGHT = 100
LENGTH = 150
CASE_SHAPE = 'Sphere'  # Options: 'Sphere', 'Box'

# New path types and their parameters
PATH_TYPES = ['u_shape', 'tube_shape', 'u_shape_adjusted_height']

PATH_TYPE_PARAMETERS = {
    'u_shape': {
        'height_width': 10.0 - 0.0001,
        'wall_thickness': 2.0,
    },
    'tube_shape': {
        'outer_diameter': 10.0 - 0.0001,
        'wall_thickness': 2.0
    },
    'u_shape_adjusted_height': {
        'height_width': 10.0 - 0.0001,
        'wall_thickness': 2.0,
        'lower_distance': 3.5
    }
}