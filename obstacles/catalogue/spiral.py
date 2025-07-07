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

        # occupied nodes, a 2 x 2 x 2 cube
        # raw grid coordinates (unit steps)
        raw_coords = [
            (0, 0, 0),
            (1, 0, 0),
            (0, 1, 0),
            (1, 1, 0),
            (0, 0, 1),
            (1, 0, 1),
            (0, 1, 1),
            (1, 1, 1),
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

    def create_obstacle_geometry(self) -> Part:
        """Generates the geometry for the obstacle."""

        with BuildPart() as obstacle:
            with BuildLine() as helix_path:
                Helix(
                    pitch=2 * self.node_size,
                    height=2 * self.node_size,
                    radius=self.node_size,
                )

            with BuildSketch(helix_path.line ^ 0) as profile:
                Rectangle(4, self.node_size)
            sweep(is_frenet=True)

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
    spiral = Spiral()
    spiral.translate(Vector(X=20, Y=20, Z=-10))
    spiral.visualize()

    # Solid model
    obstacle = spiral.create_obstacle_geometry()
    show(obstacle)
