# obstacles/overhand_knot.py

from math import cos, pi, sin
from typing import List, Tuple

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
    make_face,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class OverhandKnotObstacle(Obstacle):
    """An overhand knot shaped obstacle."""

    def __init__(self):
        # TODO, double check if this is the approach I want
        super().__init__(name="OverhandKnot")

    def create_obstacle_geometry(self) -> Part:
        """Generates the geometry for the overhand knot."""

        # Knot parameters
        t0 = pi / 3
        t1 = 4 * pi / 3
        samples = 200
        scale = 10  # Scale factor for the knot size

        # Generate points for the knot
        knot_points = [
            Vector(
                scale * (sin(t / samples) + 2 * sin(2 * t / samples)),
                scale * (cos(t / samples) - 2 * cos(2 * t / samples)),
                scale * (-sin(3 * t / samples)),
            )
            for t in range(int(t0), int(t1 * samples))
        ]

        # TODO use random (from seed in init) to use different profile path shapes from predefined selection
        # TODO if applicable, add accent color or support part

        # Define profile (e.g., L-shape)
        height_width = 3  # Smaller profile for an obstacle?
        wall_thickness = 0.6

        half_width = height_width / 2
        inner_half_width = half_width - wall_thickness

        # L-shape profile points
        l_shape_points = [
            (-half_width, half_width),
            (-inner_half_width, half_width),
            (-inner_half_width, -inner_half_width),
            (half_width, -inner_half_width),
            (half_width, -half_width),
            (-half_width, -half_width),
            (-half_width, half_width),
        ]

        with BuildPart() as knot_part:
            with BuildLine() as line:
                m1 = Spline(knot_points)
                # TODO use node size to scale the knot size
                Line(m1 @ 1, m1 @ 1 + 40 * (m1 % 1))
                Line(m1 @ 0, m1 @ 0 - 40 * (m1 % 0))

            with BuildSketch(line.line ^ 0):
                with BuildLine(Rot(Z=-90)):
                    Polyline(l_shape_points)
                make_face()
            sweep()

        return knot_part.part

    def get_relative_occupied_coords(self, node_size: float) -> List[Vector]:
        """
        Determine occupied nodes for this obstacle.
        """

        # Harcoded values for the knot shape, scale with node size
        occupied_relative_coords = []

        print(
            f"Found {len(occupied_relative_coords)} relative occupied coords for {self.name}"
        )
        return list(occupied_relative_coords)

    def get_relative_entry_exit_coords(self) -> Tuple[Vector, Vector]:
        """Define entry/exit points relative to the knot's geometry."""

        entry_coord = (0, 0, 0)
        exit_coord = (0, 0, 0)

        print(f"{self.name} relative entry: {entry_coord}, exit: {exit_coord}")
        return entry_coord, exit_coord


# Register the obstacle
register_obstacle("OverhandKnot", OverhandKnotObstacle)
