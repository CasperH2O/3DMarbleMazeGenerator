# obstacles/catalogue/overhand_knot.py

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
from ocp_vscode import show

import config
from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle
from puzzle.node import Node


class OverhandKnotObstacle(Obstacle):
    """An overhand knot shaped obstacle."""

    def __init__(self):
        super().__init__(name="OverhandKnot")

        # Occupied nodes, a 2 x 2 x 2 cube
        # raw grid coordinates (unit steps)
        raw_coords = [
            (0, 0, 0),
            (1, 0, 0),
            (2, 0, 0),
            (3, 0, 0),
            (0, 0, 1),
            (1, 0, 1),
            (2, 0, 1),
            (3, 0, 1),
        ]
        self.node_size = config.Puzzle.NODE_SIZE

        self._occupied_nodes: List[Node] = [
            Node(
                x * self.node_size,
                y * self.node_size,
                z * self.node_size,
                occupied=True,
            )
            for (x, y, z) in raw_coords
        ]

    def create_obstacle_geometry(self) -> Part:
        """Generates the geometry for the overhand knot."""

        # Knot parameters
        t0 = pi / 3
        t1 = 4 * pi / 3
        samples = 200
        scale = self.node_size * 0.6  # scale knot to grid size

        # Generate points for the knot
        knot_points = [
            Vector(
                scale * (sin(t / samples) + 2 * sin(2 * t / samples)),
                scale * (cos(t / samples) - 2 * cos(2 * t / samples)),
                scale * (-sin(3 * t / samples)),
            )
            for t in range(int(t0), int(t1 * samples))
        ]

        # Define profile (e.g., L-shape)
        height_width = self.node_size * 0.6
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

        with BuildPart() as knot_part:
            with BuildLine() as line:
                spline = Spline(knot_points)
                Line(spline @ 1, spline @ 1 + 4 * self.node_size * (spline % 1))
                Line(spline @ 0, spline @ 0 - 4 * self.node_size * (spline % 0))

            with BuildSketch(line.line ^ 0):
                with BuildLine(Rot(Z=-90)):
                    Polyline(l_shape)
                make_face()
            sweep()

        return knot_part.part

    def get_relative_occupied_coords(self) -> List[Node]:
        """
        Return occupied Node instances, already scaled to world units.
        """
        print(f"Found {len(self._occupied_nodes)} occupied nodes for {self.name}")
        return list(self._occupied_nodes)

    def get_relative_entry_exit_coords(self) -> Tuple[Vector, Vector]:
        """Define entry/exit points relative to the knot's geometry."""
        entry = Vector(0, 0, 0) * self.node_size
        exit = Vector(0, 0, 0) * self.node_size
        print(f"{self.name} relative entry: {entry}, exit: {exit}")
        return entry, exit


# Register obstacle
register_obstacle("OverhandKnot", OverhandKnotObstacle)

if __name__ == "__main__":
    # Visualization
    spiral = OverhandKnotObstacle()
    spiral.translate(Vector(X=20, Y=20, Z=-10))
    #spiral.visualize()

    # Solid model
    obstacle = spiral.create_obstacle_geometry()
    show(obstacle)
