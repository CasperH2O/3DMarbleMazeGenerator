# puzzle/utils/enums.py

from enum import Enum


class PathCurveModel(Enum):
    """
    Enumeration representing the different models for path curves.
    """

    SINGLE = "single"
    COMPOUND = "compound"
    SPLINE = "spline"


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
