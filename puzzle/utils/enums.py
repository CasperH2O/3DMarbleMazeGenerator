# puzzle/utils/enums.py

from enum import Enum


class CaseShape(Enum):
    """
    Enumeration representing the different shapes of the puzzle casing.
    """

    SPHERE = "Sphere"
    SPHERE_WITH_FLANGE = "Sphere with flange"
    SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES = "Sphere with flange enclosed two sides"
    BOX = "Box"


class PathCurveModel(Enum):
    """
    Enumeration representing the different models for path curves.
    """

    STANDARD = "standard"
    SPLINE = "spline"


class PathCurveType(Enum):
    """
    Enumeration representing the different types of path curves.
    """

    ARC = "arc"
    CURVE_90_DEGREE_SINGLE_PLANE = "90_degree_single_plane_curve"
    STRAIGHT = "straight"
    S_CURVE = "s_curve"


class CaseManufacturer(Enum):
    GENERIC = "generic"
    SPHERE_PLAYTASTIC_120_MM = "sphere_playtastic_120_mm"
    SPHERE_PLAYTASTIC_170_MM = "sphere_playtastic_170_mm"
    SPHERE_SAIDKOCC_100_MM = "sphere_saidkocc_100_mm"


class Theme(Enum):
    GENERIC = "generic"
    MARBLE = "marble"
    GLOW_IN_THE_DARK = "glow_in_the_dark"
