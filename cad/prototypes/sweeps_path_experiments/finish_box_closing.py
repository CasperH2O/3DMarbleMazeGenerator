from build123d import *
from ocp_vscode import show_all

# Define a vertex at (0, 0, 0)
origin_vertex = Vertex(0, 0, 0)
arc_start = Vector(87.5, 0, 0)
arc_end = Vector(71.807033081725, -50, 0)

with BuildPart() as path:
    with BuildLine() as line:
        arc = RadiusArc(
            Vector(87.5, 0, 0), Vector(71.807033081725, -50, 0), radius=87.5
        )

    with BuildSketch(line.line ^ 0) as path_profile_sketch:
        Circle(radius=4.99)
        Circle(radius=4, mode=Mode.SUBTRACT)
        split(bisect_by=Plane.XZ, keep=Keep.BOTTOM)
    sweep()

    with BuildLine() as closure_line:
        add(arc)
        split(bisect_by=Plane(arc ^ (1 - (1.2 / arc.length))), keep=Keep.TOP)
    with BuildSketch(closure_line.line ^ 0) as closure_sketch:
        make_hull(edges=path_profile_sketch.edges())
    sweep()

# Show all objects
show_all()
