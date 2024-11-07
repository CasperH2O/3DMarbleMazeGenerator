# shapes/path_profile_type_shapes.py

import cadquery as cq
from typing import Optional
import config

def create_l_shape(work_plane: Optional[cq.Workplane] = None, height_width: float = 9.9999, wall_thickness: float = 2.0) -> cq.Workplane:
    """
    Creates an L-shaped cross-section centered at the origin or on the given work plane.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - height_width: The total height and width of the L-shape.
    - wall_thickness: The thickness of the walls of the L-shape.

    Returns:
    - A CadQuery workplane with the created L-shape.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    l_shape = (
        wp
        .moveTo(-half_width, half_width)                # 1
        .lineTo(-inner_half_width, half_width)          # 2
        .lineTo(-inner_half_width, -inner_half_width)   # 3
        .lineTo(half_width, -inner_half_width)          # 4
        .lineTo(half_width, -half_width)                # 5
        .lineTo(-half_width, -half_width)               # 6
        .close()
    )
    return l_shape

def create_l_shape_adjusted_height(work_plane: Optional[cq.Workplane] = None, height_width: float = 9.9999, wall_thickness: float = 2.0, lower_distance: float = 2.0) -> cq.Workplane:
    """
    Creates an L-shaped cross-section with adjusted height centered at the origin or on the given work plane.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - height_width: The total height and width of the L-shape.
    - wall_thickness: The thickness of the walls of the L-shape.
    - lower_distance: The distance to reduce the height from the top.

    Returns:
    - A CadQuery workplane with the created L-shape with adjusted height.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    # Check reduced height does not become so large as to remove side walls completely
    if height_width - lower_distance < wall_thickness:
        lower_distance = height_width - wall_thickness

    # Adjusted top Y-coordinate
    adjusted_top_y = height_width / 2 - lower_distance

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    l_shape_adjusted_height = (
        wp
        .moveTo(-half_width, -half_width)                   # 1
        .lineTo(-half_width, adjusted_top_y)                # 2
        .lineTo(-inner_half_width, adjusted_top_y)          # 3
        .lineTo(-inner_half_width, -inner_half_width)       # 4
        .lineTo(half_width, -inner_half_width)              # 5
        .lineTo(half_width, -half_width)                    # 8
        .close()
    )
    return l_shape_adjusted_height

def create_o_shape(work_plane: Optional[cq.Workplane] = None, outer_diameter: float = 9.9999, wall_thickness: float = 2.0) -> cq.Workplane:
    """
    Creates a tube-shaped cross-section centered at the origin or on the given work plane.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - outer_diameter: The outer diameter of the tube.
    - wall_thickness: The thickness of the tube walls.

    Returns:
    - A CadQuery workplane with the created tube shape.
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
        .consolidateWires()
    )
    return tube_shape

def create_o_shape_support(work_plane: Optional[cq.Workplane] = None, outer_diameter: float = 9.9999, wall_thickness: float = 2.0) -> cq.Workplane:
    """
    Creates a circle-shaped cross-section centered at the origin or on the given work plane.
    Required as additional 3D print support material for the O-shaped cross-section.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - outer_diameter: The outer diameter of the tube.
    - wall_thickness: The thickness of the tube walls.

    Returns:
    - A CadQuery workplane with the created support circle shape.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    # Distance from edges
    distance = wall_thickness + config.Manufacturing.LAYER_THICKNESS * 2

    # Calculate inner diameter
    inner_diameter = outer_diameter - 2 * wall_thickness - distance

    # Define the tube shape
    tube_shape = (
        wp
        .polygon(nSides=4, diameter=inner_diameter - distance, circumscribed=False)
        .circle(inner_diameter / 2)
        .consolidateWires()
    )
    return tube_shape

def create_u_shape(work_plane: Optional[cq.Workplane] = None, height: float = 9.9999, width: float = 9.9999, wall_thickness: float = 2.0, factor: float = 1.0) -> cq.Workplane:
    """
    Creates a U-shaped cross-section centered at the origin or on the given work plane.
    The width of the shape can be scaled using the factor parameter.
    Optionally, the wall thickness can also be defined.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - height: The total height of the U-shape (along the Y-axis).
    - width: The total width of the U-shape (along the X-axis).
    - wall_thickness: The thickness of the walls of the U-shape.
    - factor: Scaling factor applied only to the width.

    Returns:
    - A CadQuery workplane with the created U-shape.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    # Apply the factor only to the width
    adjusted_width = width * factor
    adjusted_height = height  # Height remains unchanged

    half_width = adjusted_width / 2
    half_height = adjusted_height / 2
    inner_half_width = half_width - wall_thickness
    inner_half_height = half_height - wall_thickness

    u_shape = (
        wp
        .moveTo(-half_width, half_height)               # 1 Start at top-left corner of outer rectangle
        .lineTo(-inner_half_width, half_height)         # 2 Move to top-left inner corner
        .lineTo(-inner_half_width, -inner_half_height)  # 3 Down inner left wall
        .lineTo(inner_half_width, -inner_half_height)   # 4 Across bottom inner
        .lineTo(inner_half_width, half_height)          # 5 Up inner right wall
        .lineTo(half_width, half_height)                # 6 Move to top-right outer corner
        .lineTo(half_width, -half_height)               # 7 Down outer right wall
        .lineTo(-half_width, -half_height)              # 8 Across bottom outer
        .close()
    )
    return u_shape

def create_u_shape_path_color(work_plane: Optional[cq.Workplane] = None, height: float = 9.9999, width: float = 9.9999, wall_thickness: float = 2.0, factor: float = 1.0) -> cq.Workplane:
    """
    Creates a single layer path for within a U-shaped cross-section to apply a color on top.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - height: The total height of the U-shape (along the Y-axis).
    - width: The total width of the U-shape (along the X-axis).
    - wall_thickness: The thickness of the walls of the U-shape.
    - factor: Scaling factor applied only to the width.

    Returns:
    - A CadQuery workplane with the created single layer path for the U-shape.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    # Apply the factor only to the width
    adjusted_width = width * factor
    adjusted_height = height  # Height remains unchanged
    
    half_width = adjusted_width / 2
    half_height = adjusted_height / 2
    inner_half_width = half_width - wall_thickness
    inner_half_height = half_height - wall_thickness

    nozzle_diameter = config.Manufacturing.NOZZLE_DIAMETER

    u_shape = (
        wp
        .moveTo(-inner_half_width, -inner_half_height + nozzle_diameter)    # 1
        .lineTo(-inner_half_width, -inner_half_height)                      # 2
        .lineTo(inner_half_width, -inner_half_height)                       # 3
        .lineTo(inner_half_width,  -inner_half_height + nozzle_diameter)    # 4
        .close()        
    )
    return u_shape

def create_u_shape_adjusted_height(work_plane: Optional[cq.Workplane] = None, height_width: float = 9.9999, wall_thickness: float = 2.0, lower_distance: float = 2.0) -> cq.Workplane:
    """
    Creates a U-shaped cross-section with adjusted height centered at the origin or on the given work plane.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - height_width: The total height and width of the U-shape.
    - wall_thickness: The thickness of the walls of the U-shape.
    - lower_distance: The distance to reduce the height from the top.

    Returns:
    - A CadQuery workplane with the created U-shape with adjusted height.
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

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    u_shape_adjusted_height = (
        wp
        .moveTo(-half_width, -half_width)               # 1
        .lineTo(-half_width, adjusted_top_y)            # 2
        .lineTo(-inner_half_width, adjusted_top_y)      # 3
        .lineTo(-inner_half_width, -inner_half_width)   # 4
        .lineTo(inner_half_width, -inner_half_width)    # 5
        .lineTo(inner_half_width, adjusted_top_y)       # 6
        .lineTo(half_width, adjusted_top_y)             # 7
        .lineTo(half_width, -half_width)                # 8
        .close()
    )
    return u_shape_adjusted_height

def create_v_shape(work_plane: Optional[cq.Workplane] = None, height_width: float = 9.9999, wall_thickness: float = 2.0) -> cq.Workplane:
    """
    Creates a V-shaped cross-section centered at the origin or on the given work plane.
    Height/width define the dimensions.

    Parameters:
    - work_plane: The CadQuery workplane to create the shape on. Defaults to the XY plane if None.
    - height_width: The total height and width of the V-shape.
    - wall_thickness: The thickness of the walls of the V-shape.

    Returns:
    - A CadQuery workplane with the created V-shape.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    v_shape = (
        wp
        .moveTo(-wall_thickness, -height_width / 2)                     # 1 start bottom left outer corner
        .lineTo(-height_width / 2, -wall_thickness)                     # 2
        .lineTo(-height_width / 2 + wall_thickness, -wall_thickness)    # 3
        .lineTo(-wall_thickness, -height_width / 2 + wall_thickness)    # 4
        .lineTo(wall_thickness, -height_width / 2 + wall_thickness)     # 5
        .lineTo(height_width / 2 - wall_thickness, -wall_thickness)     # 6
        .lineTo(height_width / 2, -wall_thickness)                      # 7
        .lineTo(wall_thickness, -height_width / 2)                      # 8
        .close()                                                        # Close the shape
    )

    return v_shape

def create_rectangle_shape(work_plane: Optional[cq.Workplane] = None, height_width: float = 9.9999) -> cq.Workplane:
    """
    Creates a rectangular cross-section centered at the origin or on the given work plane.

    Parameters:
    - work_plane: The CadQuery workplane to create the rectangle on. Defaults to the XY plane if None.
    - height_width: The total height and width of the rectangle.

    Returns:
    - A CadQuery workplane with the created rectangle shape.
    """
    if work_plane is None:
        wp = cq.Workplane("XY")
    else:
        wp = work_plane

    # Create the rectangle profile
    rectangle = wp.rect(height_width, height_width, centered=True)

    return rectangle
