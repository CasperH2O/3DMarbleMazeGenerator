# obstacles/catalogue/spiral.py

from typing import List, Tuple

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Helix,
    Part,
    Polyline,
    Rectangle,
    Spline,
    add,
    sweep,
)
from ocp_vscode import show

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class Spiral(Obstacle):
    """An spiral sweep shaped obstacle."""

    def __init__(self):
        super().__init__(name="Spiral")

        # Generate the required geometry on obstacle initialization
        self.create_obstacle_geometry()

        # Sample points along path segment edge for visualization
        self.sample_obstacle_path()

        # Determine occupied nodes or load from cach
        self._occupied_nodes = self.get_relative_occupied_coords()

    def create_obstacle_geometry(self):
        """Generates the geometry for the obstacle."""

        with BuildPart():
            with BuildLine() as start_line:
                Polyline(
                    (self.node_size, -1 * self.node_size, 0), (self.node_size, 0, 0)
                )
            with BuildLine() as end_line:
                Polyline(
                    (self.node_size, 0, 2 * self.node_size),
                    (self.node_size, 1 * self.node_size, 2 * self.node_size),
                )
            with BuildLine() as helper_helix:
                Helix(
                    pitch=2 * self.node_size,
                    height=2 * self.node_size,
                    radius=self.node_size,
                )
            with BuildLine() as middle_spline:
                Spline(
                    [
                        start_line.line @ 1,
                        helper_helix.line @ 0.25,
                        helper_helix.line @ 0.35,
                        helper_helix.line @ 0.5,
                        helper_helix.line @ 0.65,
                        helper_helix.line @ 0.75,
                        end_line.line @ 0,
                    ],
                    tangents=[start_line.line % 1, end_line.line % 0],
                    tangent_scalars=[1.25, 1.25],
                )
            with BuildLine() as obstacle_line:
                add(start_line)
                add(helper_helix)
                add(end_line)

        self.path_segment.path = obstacle_line.line

    def model_solid(self) -> Part:
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


# Register the obstacle
register_obstacle("Spiral", Spiral)

if __name__ == "__main__":
    # Visualization
    obstacle = Spiral()
    obstacle.visualize()

    # Solid model
    obstacle_solid = obstacle.model_solid()
    cubes = obstacle.create_occupied_node_cubes()
    show(obstacle_solid, cubes)
