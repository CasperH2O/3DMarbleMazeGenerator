# shapes/path_shapes.py
import math

import cadquery as cq


def create_u_shape(work_plane=None, height_width=9.9999, wall_thickness=2.0):
    """
    Creates a U-shaped cross-section centered at the origin or on the given work plane.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    u_shape = (
        wp
        .moveTo(-half_width, half_width)  # 1
        .lineTo(-inner_half_width, half_width)  # 2
        .lineTo(-inner_half_width, -inner_half_width)  # 3
        .lineTo(inner_half_width, -inner_half_width)  # 4
        .lineTo(inner_half_width, half_width)  # 5
        .lineTo(half_width, half_width)  # 6
        .lineTo(half_width, -half_width)  # 7
        .lineTo(-half_width, -half_width)  # 8
        .close()
    )
    return u_shape


def create_l_shape(work_plane=None, height_width=9.9999, wall_thickness=2.0):
    """
    Creates an L-shaped cross-section centered at the origin or on the given work plane.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    u_shape = (
        wp
        .moveTo(-half_width, half_width)  # 1
        .lineTo(-inner_half_width, half_width)  # 2
        .lineTo(-inner_half_width, -inner_half_width)  # 3
        .lineTo(half_width, -inner_half_width)  # 4
        .lineTo(half_width, -half_width)  # 5
        .lineTo(-half_width, -half_width)  # 6
        .close()
    )
    return u_shape


def create_tube_shape(work_plane=None, outer_diameter=9.9999, wall_thickness=2.0):
    """
    Creates a tube-shaped cross-section centered at the origin or on the given work plane.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    # Calculate inner diameter
    inner_diameter = outer_diameter - 2 * wall_thickness

    # Define the tube shape
    tube_shape = (
        wp
        .circle(outer_diameter / 2)
        .circle(inner_diameter / 2)
    )
    return tube_shape


def create_u_shape_adjusted_height(work_plane=None, height_width=9.9999, wall_thickness=2.0, lower_distance=2.0):
    """
    Creates a U-shaped cross-section with adjusted height centered at the origin or on the given work plane.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    # Check reduced height does not so large as to remove side walls completely
    if height_width - lower_distance < wall_thickness:
        lower_distance = height_width - wall_thickness

    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    u_shape_adjusted_height = (
        wp
        .moveTo(- height_width / 2, height_width / 2)  # Top left of U-shape
        .lineTo(height_width / 2, height_width / 2)    # Top horizontal line
        .lineTo(height_width / 2, -adjusted_top_y)     # Right vertical line
        .lineTo(height_width / 2 - wall_thickness, -adjusted_top_y)
        .lineTo(height_width / 2 - wall_thickness, height_width / 2 - wall_thickness)
        .lineTo(-height_width / 2 + wall_thickness, height_width / 2 - wall_thickness)
        .lineTo(-height_width / 2 + wall_thickness, -adjusted_top_y)
        .lineTo(-height_width / 2, -adjusted_top_y)
        .close()
    )
    return u_shape_adjusted_height


def create_v_shape(work_plane=None, height_width=9.9999, wall_thickness=2.0):
    """
    Creates a V-shaped cross-section centered at the origin or on the given work plane.
    Height/width define the dimensions.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    v_shape = (
        wp
        .moveTo(-wall_thickness, -height_width / 2)   # 1 start bottom left outer corner
        .lineTo(-height_width / 2, -wall_thickness)   # 2
        .lineTo(-height_width / 2 + wall_thickness, -wall_thickness)      # 3
        .lineTo(-wall_thickness, -height_width / 2 + wall_thickness)  # 4
        .lineTo(wall_thickness, -height_width / 2 + wall_thickness)  # 5
        .lineTo(height_width / 2 - wall_thickness, -wall_thickness)  # 6
        .lineTo(height_width / 2, -wall_thickness)  # 7
        .lineTo(wall_thickness, -height_width / 2)  # 8
        .close()                              # Close the shape
    )

    return v_shape
