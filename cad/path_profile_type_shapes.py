# cad/path_profile_type_shapes.py

from enum import Enum

from build123d import (
    BuildLine,
    BuildSketch,
    Circle,
    Location,
    Locations,
    Mode,
    Plane,
    Polyline,
    Rectangle,
    RegularPolygon,
    Rot,
    make_face,
)

import config


class PathProfileType(Enum):
    """
    Enumeration representing the different types of path profiles.
    """

    L_SHAPE = "l_shape"
    L_SHAPE_ADJUSTED_HEIGHT = "l_shape_adjusted_height"
    L_SHAPE_PATH_COLOR = "l_shape_path_color"
    L_SHAPE_MIRRORED = "l_shape_mirrored"
    L_SHAPE_MIRRORED_ADJUSTED_HEIGHT = "l_shape_mirrored_adjusted_height"
    L_SHAPE_MIRRORED_PATH_COLOR = "l_shape_mirrored_path_color"
    O_SHAPE = "o_shape"
    O_SHAPE_SUPPORT = "o_shape_support"
    U_SHAPE = "u_shape"
    U_SHAPE_ADJUSTED_HEIGHT = "u_shape_adjusted_height"
    U_SHAPE_PATH_COLOR = "u_shape_path_color"
    V_SHAPE = "v_shape"
    V_SHAPE_PATH_COLOR = "v_shape_path_color"
    SQUARE_CLOSED_SHAPE = "square_closed_shape"
    SQUARE_WITH_HOLE_SHAPE = "square_with_hole_shape"


def create_l_shape(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates an L-shaped cross-section centered at the origin

    Points are technically a mirrored L, as they are applied at the start of the edge in a mirrored fashion.
    To maintain sanity, the variables and methods refer to how it looks at the start of the edge during placement.
    """
    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    l_shape_points = [
        (half_width, half_width),  # 1
        (inner_half_width, half_width),  # 2
        (inner_half_width, -inner_half_width),  # 3
        (-half_width, -inner_half_width),  # 4
        (-half_width, -half_width),  # 5
        (half_width, -half_width),  # 6
        (half_width, half_width),  # close
    ]

    with BuildSketch(Plane.XY) as l_shape_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(l_shape_points)
        make_face()

    return l_shape_sketch


def create_l_shape_adjusted_height(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    lower_distance: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates an L-shaped cross-section with adjusted height centered at the origin or on the given work plane.
    """
    # Check reduced height does not become so large as to remove side walls completely
    if height_width - lower_distance < wall_thickness:
        lower_distance = height_width - wall_thickness

    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    l_shape_adjusted_points = [
        (half_width, -half_width),  # 1
        (half_width, adjusted_top_y),  # 2
        (inner_half_width, adjusted_top_y),  # 3
        (inner_half_width, -inner_half_width),  # 4
        (-half_width, -inner_half_width),  # 5
        (-half_width, -half_width),  # 6
        (half_width, -half_width),  # close
    ]

    with BuildSketch(Plane.XY) as l_shape_adjusted_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(l_shape_adjusted_points)
        make_face()

    return l_shape_adjusted_sketch


def create_l_shape_path_color(
    height: float = 9.9999,
    width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates the color path for the L-shaped cross-sections.
    """
    adjusted_width = width
    adjusted_height = height

    half_width = adjusted_width / 2
    half_height = adjusted_height / 2
    inner_half_width = half_width - wall_thickness
    inner_half_height = half_height - wall_thickness

    accent_height = 2 * config.Manufacturing.NOZZLE_DIAMETER

    l_shape_path_color_points = [
        (inner_half_width, -inner_half_height + accent_height),  # 1
        (inner_half_width, -inner_half_height),  # 2
        (-half_width, -inner_half_height),  # 3
        (-half_width, -inner_half_height + accent_height),  # 4
        (inner_half_width, -inner_half_height + accent_height),  # close
    ]

    with BuildSketch(Plane.XY) as l_shape_path_color_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(l_shape_path_color_points)
        make_face()

    return l_shape_path_color_sketch


def create_mirrored_l_shape(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """Build the mirrored L shape"""

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    mirrored_l_shape_points = [
        (-half_width, half_width),  # 1
        (-inner_half_width, half_width),  # 2
        (-inner_half_width, -inner_half_width),  # 3
        (half_width, -inner_half_width),  # 4
        (half_width, -half_width),  # 5
        (-half_width, -half_width),  # 6
        (-half_width, half_width),  # close
    ]

    with BuildSketch(Plane.XY) as mirrored_l_shape_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(mirrored_l_shape_points)
        make_face()

    return mirrored_l_shape_sketch


def create_mirrored_l_shape_adjusted_height(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    lower_distance: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    # Check reduced height does not become so large as to remove side walls completely
    if height_width - lower_distance < wall_thickness:
        lower_distance = height_width - wall_thickness

    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    mirrored_l_shape_adjusted_points = [
        (-half_width, -half_width),  # 1
        (-half_width, adjusted_top_y),  # 5
        (-inner_half_width, adjusted_top_y),  # 4
        (-inner_half_width, -inner_half_width),  # 3
        (half_width, -inner_half_width),  # 2
        (half_width, -half_width),  # 6
        (-half_width, -half_width),  # close
    ]

    with BuildSketch(Plane.XY) as mirrored_l_shape_adjusted_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(mirrored_l_shape_adjusted_points)
        make_face()

    return mirrored_l_shape_adjusted_sketch


def create_mirrored_l_shape_path_color(
    height: float = 9.9999,
    width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """Mirrored L shape path color"""

    adjusted_width = width
    adjusted_height = height

    half_width = adjusted_width / 2
    half_height = adjusted_height / 2
    inner_half_width = half_width - wall_thickness
    inner_half_height = half_height - wall_thickness

    accent_height = 2 * config.Manufacturing.NOZZLE_DIAMETER

    mirrored_l_shape_path_color_points = [
        (-inner_half_width, -inner_half_height + accent_height),  # 1
        (-inner_half_width, -inner_half_height),  # 2
        (half_width, -inner_half_height),  # 3
        (half_width, -inner_half_height + accent_height),  # 4
        (-inner_half_width, -inner_half_height + accent_height),  # close
    ]

    with BuildSketch(Plane.XY) as mirrored_l_shape_path_color_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(mirrored_l_shape_path_color_points)
        make_face()

    return mirrored_l_shape_path_color_sketch


def create_o_shape(
    outer_diameter: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a tube-shaped cross-section centered at the origin or on the given work plane.
    """
    # Calculate inner diameter
    inner_diameter = outer_diameter - 2 * wall_thickness
    outer_radius = outer_diameter / 2
    inner_radius = inner_diameter / 2

    with BuildSketch(Plane.XY) as o_shape_sketch:
        # Position the seam with Location and rotation angle
        with Locations(Location((0, 0, 0), (0, 0, rotation_angle))):
            Circle(radius=outer_radius)
            Circle(radius=inner_radius, mode=Mode.SUBTRACT)

    return o_shape_sketch


def create_o_shape_support(
    outer_diameter: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a circle-shaped cross-section centered at the origin or on the given work plane.
    Required as additional 3D print support material for the O-shaped cross-section.
    """
    # Distance from edges
    distance = wall_thickness + config.Manufacturing.LAYER_THICKNESS * 2

    # Calculate inner diameter
    inner_diameter = outer_diameter - 2 * wall_thickness - distance

    with BuildSketch(Plane.XY) as support_sketch:
        # Position the seam with Location and rotation angle
        with Locations(Location((0, 0, 0), (0, 0, rotation_angle))):
            Circle(radius=inner_diameter / 2)
            RegularPolygon(
                radius=(inner_diameter - distance) / 2, side_count=4, mode=Mode.SUBTRACT
            )

    return support_sketch


def create_u_shape(
    height: float = 9.9999,
    width: float = 9.9999,
    wall_thickness: float = 2.0,
    factor: float = 1.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a U-shaped cross-section centered at the origin or on the given work plane.
    The width of the shape can be scaled using the factor parameter.
    Optionally, the wall thickness can also be defined.
    """
    adjusted_width = width * factor
    adjusted_height = height

    half_width = adjusted_width / 2
    half_height = adjusted_height / 2
    inner_half_width = half_width - wall_thickness
    inner_half_height = half_height - wall_thickness

    u_shape_points = [
        (-half_width, half_height),  # 1
        (-inner_half_width, half_height),  # 2
        (-inner_half_width, -inner_half_height),  # 3
        (inner_half_width, -inner_half_height),  # 4
        (inner_half_width, half_height),  # 5
        (half_width, half_height),  # 6
        (half_width, -half_height),  # 7
        (-half_width, -half_height),  # 8
        (-half_width, half_height),  # close
    ]

    with BuildSketch(Plane.XY) as u_shape_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(u_shape_points)
        make_face()

    return u_shape_sketch


def create_u_shape_path_color(
    height: float = 9.9999,
    width: float = 9.9999,
    wall_thickness: float = 2.0,
    factor: float = 1.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a single layer path for within a U-shaped cross-section to apply a color on top.
    """
    adjusted_width = width * factor
    adjusted_height = height

    half_width = adjusted_width / 2
    half_height = adjusted_height / 2
    inner_half_width = half_width - wall_thickness
    inner_half_height = half_height - wall_thickness

    accent_height = 2 * config.Manufacturing.NOZZLE_DIAMETER

    u_shape_path_color_points = [
        (-inner_half_width, -inner_half_height + accent_height),  # 1
        (-inner_half_width, -inner_half_height),  # 2
        (inner_half_width, -inner_half_height),  # 3
        (inner_half_width, -inner_half_height + accent_height),  # 4
        (-inner_half_width, -inner_half_height + accent_height),  # close
    ]

    with BuildSketch(Plane.XY) as u_shape_path_color_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(u_shape_path_color_points)
        make_face()

    return u_shape_path_color_sketch


def create_u_shape_adjusted_height(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    lower_distance: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a U-shaped cross-section with adjusted height centered at the origin or on the given work plane.
    """
    # Check reduced height does not become so large as to remove side walls completely
    if height_width - lower_distance < wall_thickness:
        lower_distance = height_width - wall_thickness

    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    u_shape_adjusted_points = [
        (-half_width, -half_width),  # 1
        (-half_width, adjusted_top_y),  # 2
        (-inner_half_width, adjusted_top_y),  # 3
        (-inner_half_width, -inner_half_width),  # 4
        (inner_half_width, -inner_half_width),  # 5
        (inner_half_width, adjusted_top_y),  # 6
        (half_width, adjusted_top_y),  # 7
        (half_width, -half_width),  # 8
        (-half_width, -half_width),  # close
    ]

    with BuildSketch(Plane.XY) as u_shape_adjusted_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(u_shape_adjusted_points)
        make_face()

    return u_shape_adjusted_sketch


def create_v_shape(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a V-shaped cross-section centered at the origin or on the given work plane.
    Height/width define the dimensions.
    """
    v_shape_points = [
        (-wall_thickness, -height_width / 2),  # 1 start bottom left outer corner
        (-height_width / 2, -wall_thickness),  # 2
        (-height_width / 2 + wall_thickness, -wall_thickness),  # 3
        (-wall_thickness, -height_width / 2 + wall_thickness),  # 4
        (wall_thickness, -height_width / 2 + wall_thickness),  # 5
        (height_width / 2 - wall_thickness, -wall_thickness),  # 6
        (height_width / 2, -wall_thickness),  # 7
        (wall_thickness, -height_width / 2),  # 8
        (-wall_thickness, -height_width / 2),  # close
    ]

    with BuildSketch(Plane.XY) as v_shape_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(v_shape_points)
        make_face()

    return v_shape_sketch


def create_v_shape_path_color(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a colored path area for the V-shaped cross-section centered at the origin or on the given work plane.
    Height/width define the dimensions.
    """
    accent_height = 2 * config.Manufacturing.NOZZLE_DIAMETER

    v_shape_path_color_points = [
        (-wall_thickness, -height_width / 2 + wall_thickness),  # 1
        (
            -wall_thickness - accent_height,
            -height_width / 2 + wall_thickness + accent_height,
        ),  # 2
        (
            wall_thickness + accent_height,
            -height_width / 2 + wall_thickness + accent_height,
        ),  # 3
        (wall_thickness, -height_width / 2 + wall_thickness),  # 4
        (-wall_thickness, -height_width / 2 + wall_thickness),  # close
    ]

    with BuildSketch(Plane.XY) as v_shape_path_color_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(v_shape_path_color_points)
        make_face()

    return v_shape_path_color_sketch


def create_square_closed_shape(
    height_width: float = 9.9999,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a closed square cross-section centered at the origin.
    """

    with BuildSketch(Plane.XY) as square_closed_sketch:
        with Locations(Location((0, 0, 0), (0, 0, rotation_angle))):
            Rectangle(width=height_width, height=height_width)

    return square_closed_sketch


def create_square_with_hole_shape(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """
    Creates a square cross-section with a square hole centered at the origin.
    """

    inner_height_width = height_width - 2 * wall_thickness

    with BuildSketch(Plane.XY) as square_with_hole_sketch:
        with Locations(Location((0, 0, 0), (0, 0, rotation_angle))):
            Rectangle(width=height_width, height=height_width)
            Rectangle(
                width=inner_height_width, height=inner_height_width, mode=Mode.SUBTRACT
            )

    return square_with_hole_sketch


# Central registry mapping for all shape creation functions
PROFILE_TYPE_FUNCTIONS = {
    PathProfileType.L_SHAPE: create_l_shape,
    PathProfileType.L_SHAPE_PATH_COLOR: create_l_shape_path_color,
    PathProfileType.L_SHAPE_MIRRORED: create_mirrored_l_shape,
    PathProfileType.L_SHAPE_MIRRORED_PATH_COLOR: create_mirrored_l_shape_path_color,
    PathProfileType.L_SHAPE_ADJUSTED_HEIGHT: create_l_shape_adjusted_height,
    PathProfileType.L_SHAPE_MIRRORED_ADJUSTED_HEIGHT: create_mirrored_l_shape_adjusted_height,
    PathProfileType.O_SHAPE: create_o_shape,
    PathProfileType.O_SHAPE_SUPPORT: create_o_shape_support,
    PathProfileType.U_SHAPE: create_u_shape,
    PathProfileType.U_SHAPE_PATH_COLOR: create_u_shape_path_color,
    PathProfileType.U_SHAPE_ADJUSTED_HEIGHT: create_u_shape_adjusted_height,
    PathProfileType.V_SHAPE: create_v_shape,
    PathProfileType.V_SHAPE_PATH_COLOR: create_v_shape_path_color,
    PathProfileType.SQUARE_CLOSED_SHAPE: create_square_closed_shape,
    PathProfileType.SQUARE_WITH_HOLE_SHAPE: create_square_with_hole_shape,
}

# Accent registry, map a path profile to its accent color profile
ACCENT_REGISTRY = {
    PathProfileType.U_SHAPE: PathProfileType.U_SHAPE_PATH_COLOR,
    PathProfileType.U_SHAPE_ADJUSTED_HEIGHT: PathProfileType.U_SHAPE_PATH_COLOR,
    PathProfileType.V_SHAPE: PathProfileType.V_SHAPE_PATH_COLOR,
    PathProfileType.L_SHAPE: PathProfileType.L_SHAPE_PATH_COLOR,
    PathProfileType.L_SHAPE_ADJUSTED_HEIGHT: PathProfileType.L_SHAPE_PATH_COLOR,
    PathProfileType.L_SHAPE_MIRRORED: PathProfileType.L_SHAPE_MIRRORED_PATH_COLOR,
    PathProfileType.L_SHAPE_MIRRORED_ADJUSTED_HEIGHT: PathProfileType.L_SHAPE_MIRRORED_PATH_COLOR,
    PathProfileType.SQUARE_WITH_HOLE_SHAPE: PathProfileType.U_SHAPE_PATH_COLOR,
}

# Support registry, map a path profile to its support profile
SUPPORT_REGISTRY = {
    PathProfileType.O_SHAPE: PathProfileType.O_SHAPE_SUPPORT,
}
