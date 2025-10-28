# config.py

from cad.cases.case_model_base import (
    CaseManufacturer,
    CaseShape,
)
from cad.path_profile_type_shapes import PathProfileType
from puzzle.utils.enums import ObstacleType, PathCurveModel, PathCurveType, Theme


# Puzzle configuration
class Puzzle:
    CASE_MANUFACTURER = CaseManufacturer.SPHERE_PLAYTASTIC_120_MM
    THEME = Theme.ULTRA_MARINE
    CASE_SHAPE = CaseShape.SPHERE  # Options: Sphere, Box, Sphere with flange etc

    BALL_DIAMETER = 6  # Diameter of the ball in mm
    NODE_SIZE = 10  # Node size in mm
    SEED = 4  # Random seed for reproducibility
    NUMBER_OF_WAYPOINTS = 8  # Number of randomly placed waypoints
    WAYPOINT_CHANGE_INTERVAL = 1  # Change path profile and curve type every n waypoints

    BALL_COLOR = "#C0C0C0FF"  # Metal grey
    PATH_COLORS = ["#F0CC00FF", "#3D3FCEFF", "#B82D2DFF"]  # Gold, Cyan, Magenta
    PATH_ACCENT_COLOR = "#ECECECFF"  # Blue
    TEXT_COLOR = "#C4C4C4FF"  # Blue
    MOUNTING_RING_COLOR = "#FFD700FF"  # Yellow
    TRANSPARENT_CASE_COLOR = "#FFFFFF0D"  # White with alpha 0.05
    SUPPORT_MATERIAL_COLOR = "#FFFFFF1A"  # White with alpha 0.10


class Obstacles:
    RANDOM_PLACEMENT_ENABLED = False  # random obstacle on/off switch.
    ALLOWED_TYPES = [  # registry names to consider
        ObstacleType.QUESTION_MARK,
        ObstacleType.SPIRAL,
        ObstacleType.U_TURN,
        ObstacleType.ARROW,
        ObstacleType.OMEGA,
        ObstacleType.GOSPER_CURVE_RANGE_1_TO_4,
        ObstacleType.GOSPER_CURVE_RANGE_6_TO_10,
        ObstacleType.GOSPER_CURVE_RANGE_11_TO_15,
        # ObstacleType.ALPHA, # TODO multi section
        # ObstacleType.OVERHAND_KNOT, # TODO multi section
    ]
    MAX_TO_PLACE = 5  # target number of obstacles to place (total)
    ATTEMPTS_PER_PLACEMENT = 5  # random tries per single obstacle instance
    PER_TYPE_LIMIT = 1  # optional cap per obstacle type (None = unlimited)
    # Manual obstacle placement (processed before random placement)
    # name: ObstacleType
    # origin: world coords (x, y, z) in mm
    # rotation: Euler XYZ degrees (x, y, z) increments of 90 degrees
    MANUAL_PLACEMENT_ENABLED = False  # global manual obstacle placement on/off switch
    MANUAL_PLACEMENTS = (
        {
            "enabled": True,
            "name": ObstacleType.OMEGA.value,
            "origin": (0.0, 10.0, 0.0),
            "orientation": (90.0, 0.0, 0.0),
        },
        {
            "enabled": True,
            "name": ObstacleType.ARROW.value,
            "origin": (0.0, -10.0, 0.0),
            "orientation": (90.0, 0.0, 0.0),
        },
    )


# Manufacturing configuration
class Manufacturing:
    LAYER_THICKNESS = 0.2
    NOZZLE_DIAMETER = 0.4
    EXPORT_STL = False
    # Divide paths into n parts for printing,
    # 0 for everything seperate
    # 1 for one part, 2 for two parts, etc.
    DIVIDE_PATHS_IN = 1


# Sphere case configuration
class Sphere:
    SPHERE_DIAMETER = 150  # Diameter of the sphere in mm
    SPHERE_FLANGE_DIAMETER = SPHERE_DIAMETER + 20  # Diameter of the flange
    SPHERE_FLANGE_INNER_DIAMETER = SPHERE_FLANGE_DIAMETER - 5
    SPHERE_FLANGE_SLOT_ANGLE = 5
    SHELL_THICKNESS = 2.5  # Thickness of the sphere shell in mm
    MOUNTING_RING_THICKNESS = 3  # Thickness of the mounting ring in mm
    MOUNTING_RING_EDGE = 1  # Thickness internal
    MOUNTING_RING_INNER_HEIGHT = 2  # Inner opening of two-sided flange
    MOUNTING_HOLE_DIAMETER = 4.2  # Diameter of the mounting holes in mm
    MOUNTING_HOLE_AMOUNT = 4  # Number of mounting holes
    NUMBER_OF_MOUNTING_POINTS = 4  # Number of mounting points
    MOUNTING_BRIDGE_HEIGHT = MOUNTING_RING_THICKNESS


# Box case configuration
class Box:
    LENGTH = 100  # Length of the box in mm
    WIDTH = 100  # Width of the box in mm
    HEIGHT = 150  # Height of the box in mm
    PANEL_THICKNESS = 3  # Thickness of the box panels in mm


class Cylinder:
    DIAMETER = 120.0
    HEIGHT = 180.0
    SHELL_THICKNESS = 4.0
    NUMBER_OF_MOUNTING_POINTS = 2


# Path curves and profile configuration
class Path:
    PATH_CURVE_MODEL = [
        PathCurveModel.COMPOUND,
        PathCurveModel.SPLINE,
    ]

    PATH_CURVE_TYPE = [
        PathCurveType.S_CURVE,
        PathCurveType.CURVE_90_DEGREE_SINGLE_PLANE,
        PathCurveType.ARC,
    ]

    PATH_PROFILE_TYPES = [
        # PathProfileType.U_SHAPE,
        PathProfileType.U_SHAPE_ADJUSTED_HEIGHT,
        PathProfileType.L_SHAPE,
        PathProfileType.L_SHAPE_MIRRORED,
        PathProfileType.L_SHAPE_ADJUSTED_HEIGHT,
        PathProfileType.L_SHAPE_MIRRORED_ADJUSTED_HEIGHT,
        PathProfileType.O_SHAPE,
        PathProfileType.V_SHAPE,
    ]

    # Map a segment main index to a forced profile type, optionally
    ENABLE_OVERRIDES = True

    PATH_PROFILE_TYPE_OVERRIDES = (
        {
            7: PathProfileType.L_SHAPE_MIRRORED_ADJUSTED_HEIGHT
        }
        if ENABLE_OVERRIDES
        else {}
    )

    # Tight corner sweep tolerance
    sweep_tolerance = 0.001
    wall_thickness = 1.2

    PATH_PROFILE_TYPE_PARAMETERS = {
        "l_shape": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "l_shape_path_color": {
            "height": 10.0 - sweep_tolerance,
            "width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "l_shape_adjusted_height": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
            "lower_distance": 3.5,
        },
        "l_shape_mirrored": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "l_shape_mirrored_path_color": {
            "height": 10.0 - sweep_tolerance,
            "width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "l_shape_mirrored_adjusted_height": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
            "lower_distance": 3.5,
        },
        "o_shape": {
            "outer_diameter": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "o_shape_support": {
            "outer_diameter": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "u_shape": {
            "height": 10.0 - sweep_tolerance,
            "width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "u_shape_path_color": {
            "height": 10.0 - sweep_tolerance,
            "width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "u_shape_adjusted_height": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
            "lower_distance": 3.5,
        },
        "v_shape": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "v_shape_path_color": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
        "square_closed_shape": {
            "height_width": 10.0 - sweep_tolerance,
        },
        "square_with_hole_shape": {
            "height_width": 10.0 - sweep_tolerance,
            "wall_thickness": wall_thickness,
        },
    }


# Apply overrides
def apply_case_manufacturer_overrides():
    manufacturer = Puzzle.CASE_MANUFACTURER.value
    module_name = f"manufacturers.{manufacturer}"
    try:
        manufacturer_module = __import__(module_name, fromlist=[""])
        manufacturer_module.apply_overrides(Puzzle, Sphere, Box, Path)
    except ImportError:
        raise ValueError(f"Unknown CASE_MANUFACTURER: {Puzzle.CASE_MANUFACTURER}")
    except AttributeError:
        raise ValueError(
            f"'apply_overrides' function not found in module: {module_name}"
        )


def apply_theme_overrides():
    theme = Puzzle.THEME.value
    module_name = f"themes.{theme}"
    try:
        theme_module = __import__(module_name, fromlist=[""])
        theme_module.apply_overrides(Puzzle, Sphere, Box, Path, Manufacturing)
    except ImportError:
        pass  # Generic theme or unknown theme, no overrides


apply_case_manufacturer_overrides()
apply_theme_overrides()


# General Configuration Access
class Config:
    Puzzle = Puzzle
    Sphere = Sphere
    Box = Box
    Cylinder = Cylinder
    Path = Path
    Manufacturing = Manufacturing
    Obstacles = Obstacles
