from build123d import *
from ocp_vscode import *

path_increments = [0.1, 0.5, 0.9]

# U-shape profile parameters
adjusted_width = adjusted_height = 10 - 0.0001
wall_thickness = 1.2

half_width = adjusted_width / 2
half_height = adjusted_height / 2
inner_half_width = half_width - wall_thickness
inner_half_height = half_height - wall_thickness

# Define the points of the U-shape
u_profile_pts = (
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

# V-shape profile parameters
height_width = 10 - 0.0001
wall_thickness = 1.2

# Define the points of the v-shape
v_profile_pts = (
    (-wall_thickness, -height_width / 2),                     # 1 start bottom left outer corner
    (-height_width / 2, -wall_thickness),                     # 2
    (-height_width / 2 + wall_thickness, -wall_thickness),    # 3
    (-wall_thickness, -height_width / 2 + wall_thickness),    # 4
    ( wall_thickness, -height_width / 2 + wall_thickness),    # 5
    ( height_width / 2 - wall_thickness, -wall_thickness),    # 6
    ( height_width / 2, -wall_thickness),                     # 7
    ( wall_thickness, -height_width / 2),                     # 8
    (-wall_thickness, -height_width / 2)                      # close
)

# part 1, poly
path_1 = [(-35, 0, 0), (-30, 0, 0), (-30, 10, 0),]

# part 2, bezier
path_2 = [(-30, 10, 0), (-30, 20, 0), (-20, 20, 0)]

# part 3, poly
path_3 = [(-20, 20, 0), (-10, 20, 0), (0, 20, 0), (0, 25, 0)]

with BuildPart() as part1:
    with BuildLine() as path_line1:
        Polyline(path_1)
    with BuildSketch(path_line1.line^0) as profile_shape_sketch1:
        with BuildLine(Rot(Z=-90)) as profile_shape_line1:
            Polyline(u_profile_pts)
        make_face()
    sweep(transition=Transition.RIGHT)      

for val in path_increments:
    show_object(path_line1.line ^ val, name=f"Path Line 1 - {val:.2f}")   

show_object(path_line1)
show_object(part1) 

with BuildPart() as part2:
    with BuildLine() as path_line2:
        Bezier(path_2)
    with BuildSketch(path_line1.line^1) as profile_shape_sketch:
        with BuildLine(Rot(Z=-90)) as profile_shape_line:
            Polyline(v_profile_pts)
        make_face()
    sweep(transition=Transition.RIGHT)   

for val in path_increments:
    show_object(path_line2.line ^ val, name=f"Path Line 2 - {val:.2f}")  

show_object(path_line2)
show_object(part2)       


with BuildPart() as part3:
    with BuildLine() as path_line3:
        Polyline(path_3)
    with BuildSketch(path_line2.line^1) as profile_shape_sketch:
        with BuildLine(Rot(Z=-90)) as profile_shape_line:
            Polyline(v_profile_pts)
        make_face()
    sweep(transition=Transition.RIGHT)        

for val in path_increments:
    show_object(path_line3.line ^ val, name=f"Path Line 3 - {val:.2f}")  

show_object(path_line3)
show_object(part3) 
