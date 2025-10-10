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


class Spiral(Obstacle):
    """An spiral sweep shaped obstacle."""

    def __init__(self):
        super().__init__(name="Spiral")

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

        self.main_path_segment.path = obstacle_line.line
        self.main_path_segment.use_frenet = True

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for, determining
        occupied nodes, debug and overview.
        """

        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.main_path_segment.path)
            with BuildSketch(line.line ^ 0):
                add(self.default_path_profile_type())
            sweep(is_frenet=self.main_path_segment.use_frenet)

        obstacle.part.label = f"{self.name} Obstacle Solid"

        return obstacle.part


# Register the obstacle
register_obstacle("Spiral", Spiral)

if __name__ == "__main__":
    # Create
    obstacle = Spiral()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
