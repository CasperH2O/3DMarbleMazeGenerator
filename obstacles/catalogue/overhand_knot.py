# obstacles/catalogue/overhand_knot.py

from math import cos, pi, sin
from typing import List, Tuple

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Line,
    Polyline,
    Rot,
    Spline,
    Vector,
    add,
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

        # Occupied nodes,
        # raw grid coordinates (unit steps)
        # Runtime calculation takes 30 seconds, thus hardcoded
        raw_node_coordinates = [
            (-1.0, -2.0, -2.0),
            (-1.0, -1.0, -2.0),
            (2.0, -1.0, -2.0),
            (2.0, 0.0, -2.0),
            (3.0, 0.0, -2.0),
            (0.0, 2.0, -2.0),
            (1.0, 2.0, -2.0),
            (-1.0, -4.0, -1.0),
            (0.0, -4.0, -1.0),
            (-2.0, -3.0, -1.0),
            (-1.0, -3.0, -1.0),
            (0.0, -3.0, -1.0),
            (-2.0, -2.0, -1.0),
            (-1.0, -2.0, -1.0),
            (0.0, -2.0, -1.0),
            (-2.0, -1.0, -1.0),
            (-1.0, -1.0, -1.0),
            (0.0, -1.0, -1.0),
            (1.0, -1.0, -1.0),
            (2.0, -1.0, -1.0),
            (3.0, -1.0, -1.0),
            (-2.0, 0.0, -1.0),
            (-1.0, 0.0, -1.0),
            (0.0, 0.0, -1.0),
            (1.0, 0.0, -1.0),
            (2.0, 0.0, -1.0),
            (3.0, 0.0, -1.0),
            (-1.0, 1.0, -1.0),
            (0.0, 1.0, -1.0),
            (1.0, 1.0, -1.0),
            (2.0, 1.0, -1.0),
            (3.0, 1.0, -1.0),
            (0.0, 2.0, -1.0),
            (1.0, 2.0, -1.0),
            (2.0, 2.0, -1.0),
            (3.0, 2.0, -1.0),
            (-1.0, -4.0, 0.0),
            (0.0, -4.0, 0.0),
            (1.0, -4.0, 0.0),
            (-1.0, -3.0, 0.0),
            (0.0, -3.0, 0.0),
            (1.0, -3.0, 0.0),
            (-2.0, -2.0, 0.0),
            (-1.0, -2.0, 0.0),
            (0.0, -2.0, 0.0),
            (1.0, -2.0, 0.0),
            (2.0, -2.0, 0.0),
            (-2.0, -1.0, 0.0),
            (-1.0, -1.0, 0.0),
            (0.0, -1.0, 0.0),
            (1.0, -1.0, 0.0),
            (2.0, -1.0, 0.0),
            (-2.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (2.0, 0.0, 0.0),
            (3.0, 0.0, 0.0),
            (-2.0, 1.0, 0.0),
            (-1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (1.0, 1.0, 0.0),
            (2.0, 1.0, 0.0),
            (3.0, 1.0, 0.0),
            (-1.0, 2.0, 0.0),
            (0.0, 2.0, 0.0),
            (1.0, 2.0, 0.0),
            (2.0, 2.0, 0.0),
            (3.0, 2.0, 0.0),
            (2.0, 3.0, 0.0),
            (3.0, 3.0, 0.0),
            (0.0, -4.0, 1.0),
            (1.0, -4.0, 1.0),
            (0.0, -3.0, 1.0),
            (1.0, -3.0, 1.0),
            (2.0, -3.0, 1.0),
            (-2.0, -2.0, 1.0),
            (-1.0, -2.0, 1.0),
            (0.0, -2.0, 1.0),
            (1.0, -2.0, 1.0),
            (2.0, -2.0, 1.0),
            (-2.0, -1.0, 1.0),
            (-1.0, -1.0, 1.0),
            (0.0, -1.0, 1.0),
            (1.0, -1.0, 1.0),
            (2.0, -1.0, 1.0),
            (-2.0, 0.0, 1.0),
            (-1.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 1.0),
            (2.0, 0.0, 1.0),
            (-1.0, 1.0, 1.0),
            (0.0, 1.0, 1.0),
            (1.0, 1.0, 1.0),
            (2.0, 1.0, 1.0),
            (3.0, 1.0, 1.0),
            (-1.0, 2.0, 1.0),
            (0.0, 2.0, 1.0),
            (1.0, 2.0, 1.0),
            (2.0, 2.0, 1.0),
            (3.0, 2.0, 1.0),
            (0.0, 3.0, 1.0),
            (1.0, 3.0, 1.0),
            (2.0, 3.0, 1.0),
            (1.0, -2.0, 2.0),
            (0.0, 2.0, 2.0),
            (1.0, 2.0, 2.0),
            (2.0, 2.0, 2.0),
        ]
        self.node_size = config.Puzzle.NODE_SIZE

        self._occupied_nodes: List[Node] = [
            Node(
                x * self.node_size,
                y * self.node_size,
                z * self.node_size,
                occupied=True,
            )
            for (x, y, z) in raw_node_coordinates
        ]

        # Generate the required geometry on obstacle initialization
        self.create_obstacle_geometry()

        # Sample points along path segment edge for visualization
        self.sample_obstacle_path()

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

    def model_solid(self):
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
    obstacle = OverhandKnotObstacle()
    # obstacle._occupied_nodes = obstacle.determine_occupied_nodes(print_node_xyz=True)
    # obstacle.translate(Vector(X=20, Y=20, Z=-10))
    obstacle.visualize()

    # Solid model
    obstacle_solid = obstacle.model_solid()
    cubes = obstacle.create_occupied_node_cubes()
    show(obstacle_solid, cubes)
