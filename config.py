# config.py

# Puzzle configuration
CASE_SHAPE = 'Sphere with flange'  # Options: 'Sphere', 'Sphere with flange', 'Box'
BALL_DIAMETER = 6  # Diameter of the marble ball
NODE_SIZE = 10  # Node size in mm
SEED = 42  # Random seed
NUMBER_OF_WAYPOINTS = 1

# Sphere case
SPHERE_DIAMETER = 100  # Diameter of the sphere in mm
SPHERE_FLANGE_DIAMETER = 120  # Flange diameter
SHELL_THICKNESS = 2.5  # Thickness of the sphere shell in mm
MOUNTING_RING_THICKNESS = 3  # Thickness of the mounting ring
MOUNTING_HOLE_DIAMETER = 4  # Diameter of the mounting holes
MOUNTING_HOLE_AMOUNT = 4  # Number of mounting holes

# Box case
WIDTH = 100
HEIGHT = 100
LENGTH = 150
PANEL_THICKNESS = 3

# Path types and their parameters
PATH_TYPES = ['u_shape',
              # 'l_shape',
              'tube_shape',
              # 'u_shape_adjusted_height',
              'v_shape']

PATH_TYPE_PARAMETERS = {
    'u_shape': {
        'height_width': 10.0 - 0.0001,
        'wall_thickness': 1.2,
    },
    'l_shape': {
        'height_width': 10.0 - 0.0001,
        'wall_thickness': 1.2,
    },
    'tube_shape': {
        'outer_diameter': 10.0 - 0.0001,
        'wall_thickness': 1.2
    },
    'u_shape_adjusted_height': {
        'height_width': 10.0 - 0.0001,
        'wall_thickness': 1.2,
        'lower_distance': 3.5
    },
    'v_shape': {
        'height_width': 10.0 - 0.0001,
        'wall_thickness': 1.2,
    }
}
