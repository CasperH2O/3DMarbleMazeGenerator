from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Polyline,
    Rot,
    ThreePointArc,
    Transition,
    make_face,
    sweep,
)
from ocp_vscode import show_all

# Dimensions
height_width: float = 10 - 0.001
wall_thickness: float = 1.2
lower_distance: float = 2.0
node_size = 10

adjusted_top_y = height_width / 2 - lower_distance
half_width = height_width / 2
inner_half_width = half_width - wall_thickness

# U-shaped section (2D points)
u_pts = [
    (-half_width, -half_width),
    (-half_width, adjusted_top_y),
    (-inner_half_width, adjusted_top_y),
    (-inner_half_width, -inner_half_width),
    (inner_half_width, -inner_half_width),
    (inner_half_width, adjusted_top_y),
    (half_width, adjusted_top_y),
    (half_width, -half_width),
    (-half_width, -half_width),  # close
]

with BuildPart() as obstacle:
    # Build the path
    with BuildLine() as path:
        Polyline(
            (-3 * node_size, -2 * node_size, 0),
            (-1 * node_size, -2 * node_size, 0),
        )
        ThreePointArc(
            (-1 * node_size, -2 * node_size, 0),
            (0, 2 * node_size, 0),
            (1 * node_size, -2 * node_size, 0),
        )
        Polyline(
            (1 * node_size, -2 * node_size, 0),
            (3 * node_size, -2 * node_size, 0),
        )

    # Build the sweep face
    with BuildSketch(path.line ^ 0):
        with BuildLine(Rot(Z=-90)):
            Polyline(u_pts)
        make_face()

    # Sweep
    sweep(
        path=path.line,
        #transition=Transition.ROUND,
        # is_frenet=False,
        # normal=Vector(0, 0, 1),
    )

show_all()
