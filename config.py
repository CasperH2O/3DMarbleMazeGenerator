# config.py

from puzzle.utils.enums import CaseShape, CaseManufacturer, Theme, PathCurveModel, PathCurveType, PathProfileType

# Puzzle configuration
class Puzzle:
    CASE_MANUFACTURER = CaseManufacturer.SPHERE_PLAYTASTIC_120_MM
    THEME = Theme.GENERIC
    CASE_SHAPE = CaseShape.SPHERE_WITH_FLANGE # Options: Sphere, Box, Sphere with flange, Sphere with flange enclosed two sides
    
    BALL_DIAMETER = 6               # Diameter of the ball in mm
    NODE_SIZE = 10                  # Node size in mm
    SEED = 24                       # Random seed for reproducibility
    NUMBER_OF_WAYPOINTS = 6         # Number of randomly placed waypoints
    WAYPOINT_CHANGE_INTERVAL = 2    # Change path profile and curve type every n waypoints

    BALL_COLOR = (192, 192, 192)    # Metal grey
    PATH_COLOR = None
    PATH_ACCENT_COLOR = (47, 102, 245)
    TEXT_COLOR = (47, 102, 245)
    MOUNTING_RING_COLOR = None

# Manufacturing configuration
class Manufacturing:
    LAYER_THICKNESS = 0.2
    NOZZLE_DIAMETER = 0.4

# Sphere case configuration
class Sphere:
    SPHERE_DIAMETER = 200           # Diameter of the sphere in mm
    SPHERE_FLANGE_DIAMETER = SPHERE_DIAMETER + 20  # Diameter of the flange
    SPHERE_FLANGE_INNER_DIAMETER = SPHERE_FLANGE_DIAMETER - 5
    SPHERE_FLANGE_SLOT_ANGLE = 5
    SHELL_THICKNESS = 2.5           # Thickness of the sphere shell in mm
    MOUNTING_RING_THICKNESS = 3     # Thickness of the mounting ring in mm
    MOUNTING_RING_EDGE = 1          # Thickness internal 
    MOUNTING_RING_INNER_HEIGHT = 2  # Inner opening of two sided flange
    MOUNTING_HOLE_DIAMETER = 4.2    # Diameter of the mounting holes in mm
    MOUNTING_HOLE_AMOUNT = 4        # Number of mounting holes
    NUMBER_OF_MOUNTING_POINTS = 4   # Number of mounting points
    MOUNTING_BRIDGE_HEIGHT = MOUNTING_RING_THICKNESS

# Box case configuration
class Box:
    LENGTH = 100        # Length of the box in mm
    WIDTH = 100         # Width of the box in mm
    HEIGHT = 150        # Height of the box in mm
    PANEL_THICKNESS = 3 # Thickness of the box panels in mm

# Path curves and profile configuration
class Path:

    PATH_CURVE_MODEL = [
        PathCurveModel.POLYLINE,
        #PathCurveModel.BEZIER,
        PathCurveModel.SPLINE
        ]

    PATH_CURVE_TYPE = [
        PathCurveType.S_CURVE,
        PathCurveType.DEGREE_90_SINGLE_PLANE
        ]

    PATH_PROFILE_TYPES = [
        PathProfileType.U_SHAPE,
        PathProfileType.L_SHAPE,
        #PathProfileType.L_SHAPE_ADJUSTED_HEIGHT,
        #PathProfileType.O_SHAPE,
        PathProfileType.U_SHAPE_ADJUSTED_HEIGHT,
        PathProfileType.V_SHAPE
        ]
    
    # Tight corner sweep tolerance
    sweep_tolerance = 0.0001

    PATH_PROFILE_TYPE_PARAMETERS = {
        'l_shape': {
            'height_width': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
        },
        'l_shape_adjusted_height': {
            'height_width': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
            'lower_distance': 3.5
        },
        'o_shape': {
            'outer_diameter': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2
        },
        'o_shape_support': {
            'outer_diameter': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
        },
        'u_shape': {
            'height': 10.0 - sweep_tolerance,
            'width': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
        },
        'u_shape_path_color': {
            'height': 10.0 - sweep_tolerance,
            'width': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
        },        
        'u_shape_adjusted_height': {
            'height_width': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
            'lower_distance': 3.5
        },
        'v_shape': {
            'height_width': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
        },
        'v_shape_path_color': {
            'height_width': 10.0 - sweep_tolerance,
            'wall_thickness': 1.2,
        },
        'rectangle_shape': {
            'height_width': 10.0 - sweep_tolerance,
        }
    }

# Apply overrides
def apply_case_manufacturer_overrides():
    manufacturer = Puzzle.CASE_MANUFACTURER.value
    module_name = f"manufacturers.{manufacturer}"
    try:
        manufacturer_module = __import__(module_name, fromlist=[''])
        manufacturer_module.apply_overrides(Puzzle, Sphere, Box, Path)
    except ImportError:
        raise ValueError(f"Unknown CASE_MANUFACTURER: {Puzzle.CASE_MANUFACTURER}")
    except AttributeError:
        raise ValueError(f"'apply_overrides' function not found in module: {module_name}")    

def apply_theme_overrides():
    theme = Puzzle.THEME.value
    module_name = f"themes.{theme}"
    try:
        theme_module = __import__(module_name, fromlist=[''])
        theme_module.apply_overrides(Puzzle, Sphere, Box, Path)
    except ImportError:
        pass  # Generic theme or unknown theme, no overrides

apply_case_manufacturer_overrides()
apply_theme_overrides()    

# General Configuration Access
class Config:
    Puzzle = Puzzle
    Sphere = Sphere
    Box = Box
    Path = Path
    Manufacturing = Manufacturing
