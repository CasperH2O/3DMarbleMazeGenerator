from build123d import *
from ocp_vscode import *

# Sketch profile O
with BuildSketch(Plane.XY) as profile:
    Circle(radius=5 - 0.01)
    Circle(radius=4.4, mode=Mode.SUBTRACT)

# Paths prior and after spline for tangents
path1_1 = Polyline((-10, -10, -25), (-10, -10, -20), (-10, -10, -15))
path1_3 = Polyline((-10, 20, 35), (-10, 20, 40), (-5, 20, 40))

path1_2_spline = Spline(
    [(-10, -10, -15), (-10, 20, 35)],
    tangents=[path1_1 % 1, path1_3 % 0],
)

with BuildPart() as sweep_path:
    with BuildLine() as path_line:
        add(path1_2_spline)
    with BuildSketch(path_line.line ^ 0):
        add(profile)
    sweep(transition=Transition.RIGHT)

sweep_path.part.label = "Sweep"

# Move it aside for better view
sweep_path.part.position += (0, 20, 0)

with BuildPart() as sweep_path_alt:
    with BuildLine() as path1_2_spline_alt:
        add(path1_2_spline)
    with BuildSketch(path1_2_spline_alt.line ^ 0) as s1:
        add(profile)
    with BuildSketch(path1_2_spline_alt.line ^ 1) as s2:
        add(profile)
    sweep(
        sections=[s1.sketch, s2.sketch],
        path=path1_2_spline_alt.line,
        multisection=True,
    )

sweep_path_alt.part.label = "Sweep Multisection"

show_object(sweep_path, name=sweep_path.part.label)
show_object(sweep_path_alt, name=sweep_path_alt.part.label)
