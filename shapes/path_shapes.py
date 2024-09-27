# shapes/path_shapes.py

import cadquery as cq


def create_u_shape(workplane=None, height_width=9.9999, wall_thickness=2.0):
    """
    Creates a U-shaped cross-section centered at the origin or on the given Workplane.
    """
    if workplane is None:
        wp = cq.Workplane("XY")
    else:
        wp = workplane

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    u_shape = (
        wp
        .moveTo(-half_width, -half_width)  # Bottom left corner of U
        .lineTo(-half_width, half_width)   # Up to top left corner
        .lineTo(half_width, half_width)    # Right to top right corner
        .lineTo(half_width, -half_width)   # Down to bottom right corner
        .lineTo(inner_half_width, -half_width)  # Left along bottom inner edge
        .lineTo(inner_half_width, inner_half_width)  # Up to inner top right
        .lineTo(-inner_half_width, inner_half_width)  # Left to inner top left
        .lineTo(-inner_half_width, -half_width)  # Down to inner bottom left
        .close()
    )
    return u_shape

def create_tube_shape(workplane=None, outer_diameter=9.9999, wall_thickness=2.0):
    """
    Creates a tube-shaped cross-section centered at the origin or on the given Workplane.
    """
    if workplane is None:
        wp = cq.Workplane("XY")
    else:
        wp = workplane

    # Calculate inner diameter
    inner_diameter = outer_diameter - 2 * wall_thickness

    # Define the tube shape
    tube_shape = (
        wp
        .circle(outer_diameter / 2)
        .circle(inner_diameter / 2)
    )
    return tube_shape


def create_u_shape_adjusted_height(workplane=None, height_width=9.9999, wall_thickness=2.0, lower_distance=2.0):
    """
    Creates a U-shaped cross-section with adjusted height centered at the origin or on the given Workplane.
    """
    if workplane is None:
        wp = cq.Workplane("XY")
    else:
        wp = workplane

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
