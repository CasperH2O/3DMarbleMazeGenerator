from build123d import *
from ocp_vscode import *
from OCP.gp import gp_Trsf
from math import radians

def sweep_twist_angle(curve: Edge | Wire):
    loc1 = curve ^ 0
    loc2 = curve ^ 1
    
    angle = loc2.y_axis.direction.get_signed_angle(loc1.y_axis.direction, loc2.z_axis.direction)
    print(f"\nAngle: {angle}")

    return angle

def rotated_location(loc: Location, angle: float):
    return rotation_around_axis(loc.z_axis, angle) * loc

def rotation_around_axis(axis: Axis, angle: float) -> Location:
    trsf = gp_Trsf()
    trsf.SetRotation(axis.wrapped, radians(angle))
    return Location(trsf)

increments = [0.1, 0.5, 0.9]

with BuildSketch() as sketch0:
    Rectangle(1.5, 2.5)

with BuildSketch() as sketch1:
    Rectangle(1, 3)

with BuildSketch() as sketch2:
    Rectangle(0.5, 3.5)    

path0 = Polyline((0, 25, 0),(0, 30, 0),(5, 30, 0))
path1 = Polyline((5, 30, 0), (10, 30, 0), (10, 30, -10), (10, 20, -10), (10, 20, -20), (10, 15, -20))
path2 = Polyline((10, 15, -20), (10, 10, -20), (10, 0, -20), (10, 0, -10))

with BuildPart() as path_sweep_part0:
    with BuildLine() as path_line0:
        add(path0)      
    with BuildSketch(path_line0.line^0) as sketch_path_profile0:
        add(sketch0)
    sweep(transition=Transition.RIGHT)  

show_object(path_line0, name=f"Path Line 1")
show_object(sketch_path_profile0.sketch, name=f"Path Profile 1")
show_object(path_sweep_part0, name=f"Path Body 1")

with BuildPart() as path_sweep_part1:
    with BuildLine() as path_line1:
        add(path1)      
    #with BuildSketch(rotated_location(path_line1.line ^ 0, sweep_twist_angle(path_line0.line))) as sketch_path_profile1:
    with BuildSketch(path_line1.line^0) as sketch_path_profile1:
        add(sketch1)
    sweep(transition=Transition.RIGHT)  

show_object(path_line1, name=f"Path Line 1")
show_object(sketch_path_profile1.sketch, name=f"Path Profile 1")
show_object(path_sweep_part1, name=f"Path Body 1")

for val in increments:
    show_object(path_line1.line^val, name=f"Path Line 1 - {val:.2f}")

with BuildPart() as path_sweep_part2:
    with BuildLine() as path_line2:
        add(path2)
    #with BuildSketch(path_line1.line^1) as sketch_path_profile2:
    with BuildSketch(rotated_location(path_line2.line ^ 0, sweep_twist_angle(path_line1.line))) as sketch_path_profile2:
        add(sketch2)
    sweep(transition=Transition.RIGHT)  

show_object(path_line2, name=f"Path Line 2")
show_object(sketch_path_profile2.sketch, name=f"Path Profile 2")
show_object(path_sweep_part2, name=f"Path Body 2")

for val in increments:
    show_object(path_line2.line^val, name=f"Path Line 2 - {val:.2f}")

 