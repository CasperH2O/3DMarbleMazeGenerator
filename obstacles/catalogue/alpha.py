# obstacles/catalogue/Alpha.py

from build123d import (
    Bezier,
    BuildLine,
    BuildPart,
    BuildSketch,
    Part,
    Polyline,
    add,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle
from puzzle.node import Node
from puzzle.utils.enums import ObstacleType


class Alpha(Obstacle):
    """An Alpha shaped obstacle."""

    def __init__(self):
        super().__init__(name=ObstacleType.ALPHA.value)

        self.entry_path_segment.nodes = [
            Node(0, -2 * self.node_size, 0, occupied=True),
            Node(0, -1 * self.node_size, 0, occupied=True),
        ]
        self.exit_path_segment.nodes = [
            Node(-1 * self.node_size, 0, 2 * self.node_size, occupied=True),
            Node(-2 * self.node_size, 0, 2 * self.node_size, occupied=True),
        ]

        # Load nodes from cache or determine
        self.overlap_percentage = 2.0
        self.load_relative_node_coords()

    def create_obstacle_geometry(self):
        """Generates the geometry for the obstacle."""

        # Start line, simple straight
        with BuildLine() as start_line:
            Polyline((0, -1 * self.node_size, 0), (0, 0, 0))
        # Bezier for the curve, 4 points of a square at different heights
        with BuildLine() as bezier_line:
            size = 4  # Scale/size
            Bezier(
                (0, 0, 0),  # start
                (0, size * self.node_size, 0 * self.node_size),  # top left
                (size * self.node_size, size * self.node_size, 1.0 * self.node_size),
                (size * self.node_size, 0, 2 * self.node_size),  # bottom right
                (0, 0, 2 * self.node_size),  # end
            )
        with BuildLine() as end_line:
            Polyline(
                (0, 0, 2 * self.node_size),
                (-1 * self.node_size, 0, 2 * self.node_size),
            )

        with BuildLine() as obstacle_line:
            add(start_line)
            add(bezier_line)
            add(end_line)

        self.main_path_segment.path = obstacle_line.line

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for determining
        occupied nodes, debug and overview.
        """
        self._ensure_entry_exit_paths()

        with BuildPart() as obstacle:
            # Recreate the path wire from the stored path
            with BuildLine() as line:
                add(self.entry_path_segment.path)
                add(self.main_path_segment.path)
                add(self.exit_path_segment.path)

            # Sketch the path-profile at the START of the path
            with BuildSketch(line.line ^ 0) as s_start:
                add(self.default_path_profile_type())

            # Sketch the same path-profile at the END of the path, with rotation
            with BuildSketch(line.line ^ 1) as s_end:
                add(self.default_path_profile_type(rotation_angle=90))

            # Multi-section sweep
            sweep(
                sections=[s_start.sketch, s_end.sketch],
                path=line.line,
                multisection=True,
                is_frenet=True,
            )

        obstacle.part.label = f"{self.name} Obstacle Solid"
        return obstacle.part


# Register the obstacle
register_obstacle(ObstacleType.ALPHA.value, Alpha)

if __name__ == "__main__":
    # Create
    obstacle = Alpha()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
