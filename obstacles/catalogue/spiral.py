# obstacles/catalogue/spiral.py

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Helix,
    Part,
    Polyline,
    add,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle
from puzzle.node import Node
from puzzle.utils.enums import ObstacleType


class Spiral(Obstacle):
    """An spiral sweep shaped obstacle."""

    def __init__(self):
        super().__init__(name=ObstacleType.SPIRAL.value)

        self.entry_path_segment.nodes = [
            Node(1 * self.node_size, -2 * self.node_size, 0, occupied=True),
            Node(1 * self.node_size, -1 * self.node_size, 0, occupied=True),
        ]
        self.exit_path_segment.nodes = [
            Node(
                1 * self.node_size,
                1 * self.node_size,
                2 * self.node_size,
                occupied=True,
            ),
            Node(
                1 * self.node_size,
                2 * self.node_size,
                2 * self.node_size,
                occupied=True,
            ),
        ]

        # Load nodes from cache or determine
        self.load_relative_node_coords()

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
            with BuildLine() as obstacle_line:
                add(start_line)
                add(helper_helix)
                add(end_line)

        self.main_path_segment.path = obstacle_line.line.wires().first
        self.main_path_segment.use_frenet = True

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for, determining
        occupied nodes, debug and overview.
        """
        self._ensure_entry_exit_paths()

        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.entry_path_segment.path)
                add(self.main_path_segment.path)
                add(self.exit_path_segment.path)
            with BuildSketch(line.line ^ 0):
                add(self.default_path_profile_type())
            sweep(is_frenet=self.main_path_segment.use_frenet)

        obstacle.part.label = f"{self.name} Obstacle Solid"

        return obstacle.part


# Register the obstacle
register_obstacle(ObstacleType.SPIRAL.value, Spiral)

if __name__ == "__main__":
    # Create
    obstacle = Spiral()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
