from enum import Enum

class CaseShape(Enum):
    SPHERE = 'Sphere'
    SPHERE_WITH_FLANGE = 'Sphere with flange'
    BOX = 'Box'

class PathCurveModel(Enum):
    POLYLINE = 'polyline'
    BEZIER = 'bezier'
    SPLINE = 'spline'

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
