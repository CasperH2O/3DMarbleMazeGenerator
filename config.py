# config.py

from enum import Enum

class CaseShape(Enum):
    SPHERE = 'Sphere'
    SPHERE_WITH_FLANGE = 'Sphere with flange'
    BOX = 'Box'

# Puzzle configuration
class Puzzle:
    CASE_SHAPE = CaseShape.SPHERE_WITH_FLANGE  # Options: 'Sphere', 'Sphere with flange', 'Box'
    BALL_DIAMETER = 6  # Diameter of the marble ball in mm
    NODE_SIZE = 10  # Node size in mm
    SEED = 34  # Random seed for reproducibility
    NUMBER_OF_WAYPOINTS = 6
    WAYPOINT_CHANGE_INTERVAL = 2  # Change path profile and curve type every n waypoints

class Manufacturing:
    LAYER_THICKNESS = 0.2
    NOZZLE_DIAMETER = 0.4

# Sphere case configuration
class Sphere:
    SPHERE_DIAMETER = 100  # Diameter of the sphere in mm
    SPHERE_FLANGE_DIAMETER = SPHERE_DIAMETER + 20  # Diameter of the flange
    SHELL_THICKNESS = 2.5  # Thickness of the sphere shell in mm
    MOUNTING_RING_THICKNESS = 3  # Thickness of the mounting ring in mm
    MOUNTING_HOLE_DIAMETER = 4.2  # Diameter of the mounting holes in mm
    MOUNTING_HOLE_AMOUNT = 4  # Number of mounting holes
    NUMBER_OF_MOUNTING_POINTS = 4

# Box case configuration
class Box:
    WIDTH = 100  # Width of the box in mm
    HEIGHT = 100  # Height of the box in mm
    LENGTH = 150  # Length of the box in mm
    PANEL_THICKNESS = 3  # Thickness of the box panels in mm

class PathCurveModel(Enum):
    POLYLINE = 'polyline'
    BEZIER = 'bezier'  # Uncomment if bezier interpolation becomes supported
    SPLINE = 'spline'  # Uncomment if spline interpolation becomes supported

class PathCurveType(Enum):
    STRAIGHT = 'straight'
    S_CURVE = 's_curve'
    DEGREE_90_SINGLE_PLANE = '90_degree_single_plane'

class PathProfileType(Enum):
    U_SHAPE = 'u_shape'
    L_SHAPE = 'l_shape'
    L_SHAPE_ADJUSTED_HEIGHT = 'l_shape_adjusted_height'
    O_SHAPE = 'o_shape'
    U_SHAPE_ADJUSTED_HEIGHT = 'u_shape_adjusted_height'
    V_SHAPE = 'v_shape'
    RECTANGLE_SHAPE = 'rectangle_shape'

# Path curves and profile configuration
class Path:

    PATH_CURVE_MODEL = [PathCurveModel.POLYLINE,
                        #PathCurveModel.BEZIER,
                        PathCurveModel.SPLINE]

    PATH_CURVE_TYPE = [PathCurveType.S_CURVE,
                       PathCurveType.DEGREE_90_SINGLE_PLANE]

    PATH_PROFILE_TYPES = [
        PathProfileType.U_SHAPE,
        PathProfileType.L_SHAPE,
        PathProfileType.L_SHAPE_ADJUSTED_HEIGHT,
        PathProfileType.O_SHAPE,
        PathProfileType.U_SHAPE_ADJUSTED_HEIGHT,
        PathProfileType.V_SHAPE
    ]

    PATH_PROFILE_TYPE_PARAMETERS = {
        'l_shape': {
            'height_width': 10.0 - 0.0001,
            'wall_thickness': 1.2,
        },
        'l_shape_adjusted_height': {
            'height_width': 10.0 - 0.0001,
            'wall_thickness': 1.2,
            'lower_distance': 3.5
        },
        'o_shape': {
            'outer_diameter': 10.0 - 0.0001,
            'wall_thickness': 1.2
        },
        'u_shape': {
            'height': 10.0 - 0.0001,
            'width': 10.0 - 0.0001,
            'wall_thickness': 1.2,
        },
        'u_shape_adjusted_height': {
            'height_width': 10.0 - 0.0001,
            'wall_thickness': 1.2,
            'lower_distance': 3.5
        },
        'v_shape': {
            'height_width': 10.0 - 0.0001,
            'wall_thickness': 1.2,
        },
        'rectangle_shape': {
            'height_width': 10.0 - 0.0001,
        }
    }

# General Configuration Access
class Config:
    Puzzle = Puzzle
    Sphere = Sphere
    Box = Box
    Path = Path
    Manufacturing = Manufacturing
