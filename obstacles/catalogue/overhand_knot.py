# obstacles/catalogue/overhand_knot.py

from math import cos, pi, sin

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Line,
    Part,
    Polyline,
    Rot,
    Spline,
    Vector,
    add,
    make_face,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class OverhandKnotObstacle(Obstacle):
    """An overhand knot shaped obstacle."""

    def __init__(self):
        super().__init__(name="Overhand Knot")

        # TODO for laterupon creation, do location/orientation

        # Load occupied nodes from cache or determine
        self.load_relative_node_coords()

        # From obstacle geometry, determine entry and exit nodes
        # TODO move to better place, either on usage of obstacle or on visualization
        self.determine_entry_exit_nodes()

    def create_obstacle_geometry(self):
        """Generates the geometry for the overhand knot."""

        # Knot parameters
        t0 = pi / 3
        t1 = 4 * pi / 3
        samples = 200
        scale = self.node_size * 1  # scale knot to grid size

        # Generate points for the knot
        knot_points = [
            Vector(
                scale * (sin(t / samples) + 2 * sin(2 * t / samples)),
                scale * (cos(t / samples) - 2 * cos(2 * t / samples)),
                scale * (-sin(3 * t / samples)),
            )
            for t in range(int(t0), int(t1 * samples))
        ]

        with BuildLine() as obstacle_line:
            spline = Spline(knot_points)
            Line(spline @ 1, spline @ 1 + 2 * self.node_size * (spline % 1))
            Line(spline @ 0, spline @ 0 - 2 * self.node_size * (spline % 0))

        self.path_segment.path = obstacle_line.line

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for, determining
        occupied nodes, debug and overview.
        """

        # Define profile (e.g., L-shape)
        height_width = self.node_size
        wall_thickness = self.node_size * 0.12
        half_w = height_width / 2
        inner = half_w - wall_thickness
        l_shape = [
            (-half_w, half_w),
            (-inner, half_w),
            (-inner, -inner),
            (half_w, -inner),
            (half_w, -half_w),
            (-half_w, -half_w),
            (-half_w, half_w),
        ]

        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.path_segment.path)
            with BuildSketch(line.line ^ 0):
                with BuildLine(Rot(Z=-90)):
                    Polyline(l_shape)
                make_face()
            sweep()

        obstacle.part.label = f"{self.name} Obstacle Solid"

        return obstacle.part


# Register obstacle
register_obstacle("OverhandKnot", OverhandKnotObstacle)

if __name__ == "__main__":
    # Create
    obstacle = OverhandKnotObstacle()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
