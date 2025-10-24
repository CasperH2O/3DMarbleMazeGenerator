from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Plane,
    Polyline,
    Rot,
    Sketch,
    Transition,
    add,
    make_face,
    sweep,
)
from ocp_vscode import show_all, show_object

path_increments = [0.1, 0.5, 0.9]


def create_l_shape(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = 0,
) -> Sketch:
    """
    Creates an L-shaped cross-section centered at the origin
    """
    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    l_shape_points = [
        (-half_width, half_width),  # 1
        (-inner_half_width, half_width),  # 2
        (-inner_half_width, -inner_half_width),  # 3
        (half_width, -inner_half_width),  # 4
        (half_width, -half_width),  # 5
        (-half_width, -half_width),  # 6
        (-half_width, half_width),  # close
    ]

    with BuildSketch(Plane.XY) as l_shape_sketch:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(l_shape_points)
        make_face()

    return l_shape_sketch


with BuildPart() as example_part:
    with BuildLine() as path:
        line = Polyline([(0, 20.0), (20.0, 20.0), (20.0, 0)])
    with BuildSketch(line ^ 0) as sketch:
        add(create_l_shape())
    sweep(transition=Transition.RIGHT)

for val in path_increments:
    show_object(path.line ^ val, name=f"Path Line - {val:.2f}")

show_all()
