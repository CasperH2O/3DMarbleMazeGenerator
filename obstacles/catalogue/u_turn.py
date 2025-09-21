# obstacles/catalogue/obstacle_placeholder2.py

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Part,
    Polyline,
    Rot,
    Transition,
    add,
    make_face,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class UTurn(Obstacle):
    """An obstacle."""

    def __init__(self):
        super().__init__(name="U Turn")

        # Load occupied nodes from cache or determine
        self.load_relative_node_coords()

    def create_obstacle_geometry(self):
        """Generates the geometry for the obstacle."""

        with BuildLine() as obstacle_line:
            Polyline(
                (0, 0, 0),
                (0, self.node_size, 0),
                (0, self.node_size, self.node_size),
                (self.node_size, self.node_size, self.node_size),
                (self.node_size, self.node_size, 0),
                (self.node_size, self.node_size, -2 * self.node_size),
                (0, self.node_size, -2 * self.node_size),
                (0, self.node_size, -self.node_size),
                (0, 0, -self.node_size),
            )

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
                add(self.default_path_profile_type())
            sweep(transition=Transition.RIGHT)

        obstacle.part.label = f"{self.name} Obstacle Solid"

        return obstacle.part


# Register the obstacle
register_obstacle("U Turn", UTurn)

if __name__ == "__main__":
    # Create
    obstacle = UTurn()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
