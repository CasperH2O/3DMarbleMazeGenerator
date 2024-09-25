# shapes/path_shapes.py

import cadquery as cq


def create_u_shape(position, height_width=10.0 - 0.0001, wall_thickness=2.0):
    """
    Creates a U-shaped cross-section at the given position.
    """

    # Note, this shape is actually drawn as an 'n'
    u_shape = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(position), rotate=cq.Vector(0, 90, 270))
        .moveTo(- height_width / 2, height_width / 2)  # Top left of U-shape
        .lineTo(height_width / 2, height_width / 2)  # Top horizontal line
        .lineTo(height_width / 2, -height_width / 2)  # Right vertical line
        .lineTo(height_width / 2 - wall_thickness, -height_width / 2)  # Right wall thickness
        .lineTo(height_width / 2 - wall_thickness, height_width / 2 - wall_thickness)  # Bottom inner part
        .lineTo(-height_width / 2 + wall_thickness, height_width / 2 - wall_thickness)  # Bottom inner part (other side)
        .lineTo(-height_width / 2 + wall_thickness, -height_width / 2)  # Left wall thickness
        .lineTo(-height_width / 2, -height_width / 2)  # Left vertical line
        .close()  # Close the U-shape
    )
    return u_shape


def create_tube_shape(position, outer_diameter=10 - 0.0001, wall_thickness=2.0):
    """
    Creates a tube-shaped cross-section at the given position.
    """
    # Calculate inner diameter
    inner_diameter = outer_diameter - 2 * wall_thickness

    # Define the tube shape
    tube_shape = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(position), rotate=cq.Vector(0, 90, 270))
        .circle(outer_diameter / 2)
        .circle(inner_diameter / 2)
    )
    return tube_shape


def create_u_shape_adjusted_height(position, height_width=10.0 - 0.0001, wall_thickness=2.0, lower_distance=2.0):
    """
    Creates a U-shaped cross-section with adjusted height at the given position.
    """
    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    # Note, this shape is actually drawn as an 'n'
    u_shape_adjusted_height = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(position), rotate=cq.Vector(0, 90, 270))
        .moveTo(- height_width / 2, height_width / 2)  # Top left of U-shape
        .lineTo(height_width / 2, height_width / 2)  # Top horizontal line
        .lineTo(height_width / 2, -adjusted_top_y)  # Right vertical line
        .lineTo(height_width / 2 - wall_thickness, -adjusted_top_y)  # Right wall thickness
        .lineTo(height_width / 2 - wall_thickness, height_width / 2 - wall_thickness)  # Bottom inner part
        .lineTo(-height_width / 2 + wall_thickness, height_width / 2 - wall_thickness)  # Bottom inner part (other side)
        .lineTo(-height_width / 2 + wall_thickness, -adjusted_top_y)  # Left wall thickness
        .lineTo(-height_width / 2, -adjusted_top_y)  # Left vertical line
        .close()  # Close the U-shape
    )
    return u_shape_adjusted_height


def create_u_shape_adjusted_height_edge_1(position, height_width=10.0 - 0.0001, wall_thickness=2.0, lower_distance=2.0):
    """
    Creates a rectangle-shaped cross-section with adjusted height at the given position to fit the edge of the U shape
    """
    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    # Note, this shape is actually drawn as an n
    u_shape_adjusted_height_edge_1 = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(position), rotate=cq.Vector(0, 90, 270))
        .moveTo(-height_width / 2, -adjusted_top_y)
        .lineTo(-height_width / 2, -height_width / 2)
        .lineTo(-height_width / 2 + wall_thickness, -height_width / 2)  # Right wall thickness
        .lineTo(-height_width / 2 + wall_thickness,
                -height_width / 2 + lower_distance)  # Right wall thickness
        .close()  # Close the shape
    )
    return u_shape_adjusted_height_edge_1


def create_u_shape_adjusted_height_edge_2(position, height_width=10.0 - 0.0001, wall_thickness=2.0, lower_distance=2.0):
    """
    Creates a rectangle-shaped cross-section with adjusted height at the given position to fit the edge of the U shape
    """
    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    # Note, this shape is actually drawn as an n
    u_shape_adjusted_height_edge_2 = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(position), rotate=cq.Vector(0, 90, 270))
        .moveTo(height_width / 2, -adjusted_top_y)
        .lineTo(height_width / 2, -height_width / 2)
        .lineTo(height_width / 2 - wall_thickness, -height_width / 2)  # Right wall thickness
        .lineTo(height_width / 2 - wall_thickness,
                -height_width / 2 + lower_distance)  # Right wall thickness
        .close()  # Close the shape
    )
    return u_shape_adjusted_height_edge_2
