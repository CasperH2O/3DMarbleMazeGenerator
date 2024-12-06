from build123d import *
from ocp_vscode import *

# U-shape profile parameters
adjusted_width = adjusted_height = 10 - 0.0001
wall_thickness = 1.2

half_width = adjusted_width / 2
half_height = adjusted_height / 2
inner_half_width = half_width - wall_thickness
inner_half_height = half_height - wall_thickness

# Define the points of the U-shape
profile_pts = (
    (-half_width, half_height),
    (-inner_half_width, half_height),
    (-inner_half_width, -inner_half_height),
    (inner_half_width, -inner_half_height),
    (inner_half_width, half_height),
    (half_width, half_height),
    (half_width, -half_height),
    (-half_width, -half_height),
    (-half_width, half_height),  # Close back to the first point
)

# Points for the path
path_pts_1 = [
    (0, 0, 0),
    (40, 0, 0),
    (40, 0, 40),
    (0, 0, 40),
]

# Points for the path
path_pts_2 = [
    (0, 0, 40),
    (-40, 0, 40),
    (-40, -40, 40),
]

# Points for the path
path_pts_3 = [
    (-40, -40, 40),
    (-40, -45, 40),
    (0, -45, 40),
    (0, -45, 90),
]

# Perform the first sweep
with BuildPart() as swept_shape_part_1:
    with BuildLine() as path_line_1:
        Polyline(path_pts_1)      
    # Create the U-shape sketch in the YZ plane
    with BuildSketch(path_line_1.line^0) as u_shape_sketch_1:
        with BuildLine(Rot(Z=-90)) as u_shape_line_1:
            Polyline(profile_pts)
        make_face()
    sweep(transition=Transition.RIGHT)    

# Perform the second sweep
with BuildPart() as swept_shape_part_2:
    with BuildLine() as path_line_2:
        Polyline(path_pts_2)      
    # Create the U-shape sketch in the YZ plane
    with BuildSketch(path_line_1.line^1) as u_shape_sketch_2:
        with BuildLine(Rot(Z=-90)) as u_shape_line_2:
            Polyline(profile_pts)
        make_face()
    sweep(transition=Transition.RIGHT)

# Perform the third sweep
with BuildPart() as swept_shape_part_3:
    with BuildLine() as path_line_3:
        Polyline(path_pts_3)      
    # Create the U-shape sketch in the YZ plane
    with BuildSketch(path_line_2.line^1) as u_shape_sketch_3:
        with BuildLine(Rot(Z=-180)) as u_shape_line_3:
            Polyline(profile_pts)
        make_face()
    sweep(transition=Transition.RIGHT)         

# Display the results
#set_defaults(reset_camera=Camera.KEEP)
set_defaults(reset_camera=Camera.RESET)
show_all()
