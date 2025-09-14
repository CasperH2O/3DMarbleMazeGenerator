# obstacles/catalogue/spiral.py

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Helix,
    Part,
    Polyline,
    Rot,
    Spline,
    add,
    make_face,
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
            sweep(is_frenet=True)

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
