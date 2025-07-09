from build123d import *
from ocp_vscode import show

rod_radius = 3

with BuildPart() as swept_shape:
    # Define the path
    with BuildLine() as line_builder:
        path = Polyline((0, 0), (0, 10), (5, 10))

    # Create the circular section at the start of the path
    with BuildSketch(Plane(line_builder.line ^ 0)) as section:
        Circle(rod_radius)

    # Sweep the circle along the polyline path
    sweep(transition=Transition.ROUND)

    # Place spheres at the start and end of the original path
    start_loc = line_builder.line ^ 0
    end_loc = line_builder.line ^ 1
    with Locations(start_loc, end_loc):
        Sphere(radius=rod_radius)

# Visualize
show(swept_shape)
