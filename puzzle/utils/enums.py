# puzzle/utils/enums.py

from enum import Enum


class ObstacleType(Enum):
    """
    Enumeration representing the obstacles
    """

    ALPHA = "Alpha"
    ARROW = "Arrow"
    GOSPER_CURVE_RANGE_1_TO_4 = "Gosper Curve - Range 1-4"
    GOSPER_CURVE_RANGE_6_TO_10 = "Gosper Curve - Range 6-10"
    GOSPER_CURVE_RANGE_11_TO_15 = "Gosper Curve - Range 11-15"
    OMEGA = "Omega"
    OVERHAND_KNOT = "Overhand Knot"
    QUESTION_MARK = "Question Mark"
    SPIRAL = "Spiral"
    U_TURN = "U Turn"


class PathCurveModel(Enum):
    """
    Enumeration representing the different models for path curves.
    """

    SINGLE = "single"
    COMPOUND = "compound"
    SPLINE = "spline"
    OBSTACLE = "obstacle"


class PathCurveType(Enum):
    """
    Enumeration representing the different types of path curves.
    """

    ARC = "arc"
    CURVE_90_DEGREE_SINGLE_PLANE = "90_degree_single_plane_curve"
    STRAIGHT = "straight"
    S_CURVE = "s_curve"


class Theme(Enum):
    GENERIC = "generic"
    MARBLE = "marble"
    GLOW_IN_THE_DARK = "glow_in_the_dark"
    HIGH_CONTRAST = "high_contrast"
    ULTRA_MARINE = "ultra_marine"
