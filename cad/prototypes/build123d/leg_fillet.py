from build123d import * 
from ocp_vscode import show_all

leg_1_height = 30
slot_length = 10
thickness = 5

with BuildPart() as leg_1:
    with BuildSketch() as sketch:
        with Locations((0,0)): 
            Rectangle(leg_1_height/3, slot_length*2)
        with Locations((leg_1_height/3,0)):
            Rectangle(leg_1_height/3, slot_length*1.8)
        with Locations((leg_1_height/3*2,0)):
            Rectangle(leg_1_height/3, slot_length*1.6)

        offset(amount=0)

        # Identify the extreme left and right vertices
        extreme_vertices = [
            sketch.vertices().sort_by(Axis.X)[0],  # Leftmost vertex
            sketch.vertices().sort_by(Axis.X)[1],  # Second leftmost vertex
            sketch.vertices().sort_by(Axis.X)[-1], # Rightmost vertex
            sketch.vertices().sort_by(Axis.X)[-2]  # Second rightmost vertex
        ]

        fillet(objects=extreme_vertices, radius=1)

    extrude(amount=thickness)


show_all()