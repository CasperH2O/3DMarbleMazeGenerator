# obstacles/catalogue/question_mark.py

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Part,
    Polyline,
    RadiusArc,
    Rot,
    Spline,
    add,
    make_face,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class QuestionMark(Obstacle):
    """A question make shaped obstacle."""

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
                RadiusArc(
                    start_point=(1 * self.node_size, 0, 0),
                    end_point=(-1 * self.node_size, 0, 0),
                    radius=-self.node_size,
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

        # Dimensions
        height_width: float = 9.999
        wall_thickness: float = 1.2
        lower_distance: float = 2.0

        # Adjusted top Y-coordinate
        adjusted_top_y = height_width / 2 - lower_distance

        half_width = height_width / 2
        inner_half_width = half_width - wall_thickness

        u_shape_adjusted_points = [
            (-half_width, -half_width),  # 1
            (-half_width, adjusted_top_y),  # 2
            (-inner_half_width, adjusted_top_y),  # 3
            (-inner_half_width, -inner_half_width),  # 4
            (inner_half_width, -inner_half_width),  # 5
            (inner_half_width, adjusted_top_y),  # 6
            (half_width, adjusted_top_y),  # 7
            (half_width, -half_width),  # 8
            (-half_width, -half_width),  # close
        ]

        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.path_segment.path)
            with BuildSketch(line.line ^ 0):
                with BuildLine(Rot(Z=-90)):
                    Polyline(u_shape_adjusted_points)
                make_face()
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
