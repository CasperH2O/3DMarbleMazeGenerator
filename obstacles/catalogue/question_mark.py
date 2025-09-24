# obstacles/catalogue/question_mark.py

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Part,
    Polyline,
    Spline,
    ThreePointArc,
    add,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class QuestionMark(Obstacle):
    """A question mark shaped obstacle."""

    def __init__(self):
        super().__init__(name="Question Mark")

        # Load nodes from cache or determine
        self.load_relative_node_coords()

    def create_obstacle_geometry(self):
        """Generates the geometry for the obstacle."""

        with BuildPart():
            with BuildLine() as start_line:
                Polyline((0, -3 * self.node_size, 0), (0, -2 * self.node_size, 0))
            with BuildLine() as arc_line:
                ThreePointArc(
                    (1 * self.node_size, 0, 0),
                    (0, 1 * self.node_size, 0),
                    (-1 * self.node_size, 0, 0),
                )
            with BuildLine() as spline_line:
                Spline(
                    [
                        start_line.line @ 1,
                        (1 * self.node_size, 0, 0),
                    ],
                    tangents=[start_line.line % 1, arc_line.line % 0],
                )
            with BuildLine() as obstacle_line:
                add(start_line)
                add(spline_line)
                add(arc_line)

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
            sweep()

        obstacle.part.label = f"{self.name} Obstacle Solid"

        return obstacle.part


# Register the obstacle
register_obstacle("Question Mark", QuestionMark)

if __name__ == "__main__":
    # Create
    obstacle = QuestionMark()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
