# obstacles/catalogue/spiral.py

from typing import List, Tuple

from build123d import (
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Helix,
    Part,
    Plane,
    Rectangle,
    Vector,
    add,
    sweep,
)
from ocp_vscode import show

import config
from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle
from puzzle.node import Node


class Spiral(Obstacle):
    """An spiral sweep shaped obstacle."""

    def __init__(self):
        super().__init__(name="Spiral")

        # occupied nodes, roughly a 3 x 3 x 3 cube
        # raw grid coordinates (unit steps)
        raw_coords = [
            (-1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (-1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (1.0, 1.0, 0.0),
            (-1.0, -1.0, 1.0),
            (0.0, -1.0, 1.0),
            (1.0, -1.0, 1.0),
            (-1.0, 0.0, 1.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 1.0),
            (-1.0, 1.0, 1.0),
            (0.0, 1.0, 1.0),
            (1.0, 1.0, 1.0),
            (-1.0, -1.0, 2.0),
            (0.0, -1.0, 2.0),
            (1.0, -1.0, 2.0),
            (-1.0, 0.0, 2.0),
            (0.0, 0.0, 2.0),
            (1.0, 0.0, 2.0),
        ]
        self.node_size = config.Puzzle.NODE_SIZE

        # build Node instances with node sized scaled coordinates
        self._occupied_nodes: List[Node] = [
            Node(
                x * self.node_size,
                y * self.node_size,
                z * self.node_size,
                occupied=True,
            )
            for x, y, z in raw_coords
        ]

        # Generate the required geometry on obstacle initialization
        self.create_obstacle_geometry()

        # Sample points along path segment edge for visualization
        self.sample_obstacle_path()

    def create_obstacle_geometry(self):
        """Generates the geometry for the obstacle."""

        with BuildPart():
            with BuildLine() as obstacle_line:
                Helix(
                    pitch=2 * self.node_size,
                    height=2 * self.node_size,
                    radius=self.node_size,
                )

        self.path_segment.path = obstacle_line.line

    def model_solid(self):
        """
        Solid model the obstacle, but used for, determining
        occupied nodes, debug and overview.
        """

        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.path_segment.path)
            with BuildSketch(line.line ^ 0):
                Rectangle(self.node_size - 1, self.node_size - 1)
            sweep(is_frenet=True)

        obstacle.part.label = f"{self.name} Obstacle Solid"

        return obstacle.part

    def get_relative_occupied_coords(self) -> List[Node]:
        """
        Return the list of occupied Node instances, with absolute positions in world units.
        """
        print(f"Found {len(self._occupied_nodes)} occupied nodes for {self.name}")
        return list(self._occupied_nodes)

    def get_relative_entry_exit_coords(self) -> Tuple[Vector, Vector]:
        """Define entry/exit points relative to the obstacle's geometry."""

        entry_coord = (0, 0, 0)
        exit_coord = (0, 0, 0)

        print(f"{self.name} relative entry: {entry_coord}, exit: {exit_coord}")
        return entry_coord, exit_coord


# Register the obstacle
register_obstacle("Spiral", Spiral)

if __name__ == "__main__":
    # Visualization
    obstacle = Spiral()
    # obstacle._occupied_nodes = obstacle.determine_occupied_nodes(print_node_xyz=True)
    obstacle.visualize()

    # Solid model
    obstacle_solid = obstacle.model_solid()
    cubes = obstacle.create_occupied_node_cubes()
    show(obstacle_solid, cubes)
