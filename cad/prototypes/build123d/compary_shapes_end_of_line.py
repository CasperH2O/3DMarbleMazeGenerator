from build123d import *
from ocp_vscode import show_all, show_object

def areEqualArea(face1, face2):
    return (face1 - face2).area + (face2 - face1).area == 0.0

shape1 = Rectangle(3, 5)
shape2 = Rectangle(3, 5) 

path1 = Polyline((0, 0, 0), (30, 0, 0), (30, 30, 0))
path2 = Line((30, 30, 0), (30, 60, 0))

# Create initial sweep
with BuildPart() as swept_shape_part_1:
    with BuildLine() as path_line_1:
        add(path1)
    # Create the U-shape sketch in the YZ plane
    with BuildSketch(path1^0) as u_shape_sketch_1:
        add(shape1)
    sweep(transition=Transition.RIGHT)  

# Create face at start of the second path
with BuildSketch(path2^0) as u_shape_sketch_2:
    add(shape2)

# Obtain faces from sweep
faces = swept_shape_part_1.faces()

for face in faces:
    # Filter out faces that match the area of the second sketch, normally we can expect 2
    if face.area == u_shape_sketch_2.sketch.area:
        if areEqualArea(face, u_shape_sketch_2.sketch):
            print(f"Found matching face at {face.location}")
            show_object(face, name="Profile at end of path 1")

show_object(swept_shape_part_1, name="Path 1 Sweep")
show_object(path2, name="Path 2 Line")
show_object(u_shape_sketch_2.sketch, name="Profile at start path 2")