# puzzle/utils/enums.py

from enum import Enum

class CaseShape(Enum):
    """
    Enumeration representing the different shapes of the puzzle casing.
    """
    SPHERE = 'Sphere'
    SPHERE_WITH_FLANGE = 'Sphere with flange'
    SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES = 'Sphere with flange enclosed two sides'
    BOX = 'Box'

class PathCurveModel(Enum):
    """
    Enumeration representing the different models for path curves.
    """
    POLYLINE = 'polyline'
    BEZIER = 'bezier'
    SPLINE = 'spline'

class PathCurveType(Enum):
    """
    Enumeration representing the different types of path curves.
    """
    STRAIGHT = 'straight'
    S_CURVE = 's_curve'
    DEGREE_90_SINGLE_PLANE = '90_degree_single_plane'

class PathProfileType(Enum):
    """
    Enumeration representing the different types of path profiles.
    """
    L_SHAPE = 'l_shape'
    L_SHAPE_ADJUSTED_HEIGHT = 'l_shape_adjusted_height'
    O_SHAPE = 'o_shape'
    O_SHAPE_SUPPORT = 'o_shape_support'
    U_SHAPE = 'u_shape'
    U_SHAPE_PATH_COLOR = 'u_shape_path_color'
    U_SHAPE_ADJUSTED_HEIGHT = 'u_shape_adjusted_height'
    V_SHAPE = 'v_shape'
    V_SHAPE_PATH_COLOR = 'v_shape_path_color'
    RECTANGLE_SHAPE = 'rectangle_shape'

class CaseManufacturer(Enum):
    GENERIC = 'generic'
    SPHERE_PLAYTASTIC_120_MM = 'sphere_playtastic_120_mm'
    SPHERE_PLAYTASTIC_170_MM = 'sphere_playtastic_170_mm'
    SPHERE_SAIDKOCC_100_MM = 'sphere_saidkocc_100_mm'

class Theme(Enum):
    GENERIC = 'generic'
    MARBLE = 'marble'
    GLOW_IN_THE_DARK = 'glow_in_the_dark'