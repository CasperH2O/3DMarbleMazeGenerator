# obstacles/catalogue/Alpha.py

import numpy as np
from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Part,
    Polyline,
    Spline,
    Transition,
    add,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class Alpha(Obstacle):
    """An Alpha shaped obstacle."""

    def __init__(self):
        super().__init__(name="Alpha")

        # Load nodes from cache or determine
        self.load_relative_node_coords()

    def create_obstacle_geometry(self):
        """Generates the geometry for the obstacle."""

        # Generate parameter t
        t = np.linspace(0, 2 * np.pi, 31)

        # Modified lemniscate of Bernoulli for infinity symbol
        x = np.cos(t) / (1 + np.sin(t) ** 2)
        y = (np.sin(t) * np.cos(t)) / (1 + np.sin(t) ** 2)

        # Apply scaling to spread the arms more evenly
        x_scaled = 2 * x
        y_scaled = 2 * y

        # Combine into Nx2 array
        points = np.column_stack((x_scaled, y_scaled))

        # Cut infinity symbol in half
        filtered_points = points[points[:, 0] <= 0]

        # Apply 2D rotation matrix for 45° CCW
        theta = np.pi / 4 + np.pi  # 225 degrees
        rotation_matrix = np.array(
            [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
        )
        rotated_points = filtered_points @ rotation_matrix.T

        # Apply easing function to Z values
        t_ease = np.linspace(0, 1, len(rotated_points))
        z = (1 - np.cos(np.pi * t_ease)) / 2  # sine-based ease-in/ease-out

        # Combine into 3D points
        points_3d = np.column_stack((rotated_points, z))

        # Scale points to obstacle space:
        amp = 2 * self.node_size  # lateral amplitude
        pts = np.empty_like(points_3d, dtype=float)
        pts[:, 0] = amp * points_3d[:, 0]  # x
        pts[:, 1] = amp * points_3d[:, 1]  # y
        pts[:, 2] = self.node_size * points_3d[:, 2]  # z, up the obstacle

        # Anchor first and last to connect cleanly:
        pts[0] = (0.0, 0.0, 0.0)
        pts[-1] = (0.0, 0.0, 1 * self.node_size)

        # Convert points to VectorLike:
        mid_pts = [tuple(row) for row in pts]

        with BuildPart():
            # Start and end "handles" that also give us endpoint tangents
            with BuildLine() as start_line:
                Polyline((0, -2 * self.node_size, 0), (0, 0, 0))
            with BuildLine() as end_line:
                Polyline(
                    (0, 0, 1 * self.node_size),
                    (-2 * self.node_size, 0, 1 * self.node_size),
                )
            # Spline, alpha shaped
            with BuildLine() as spline_line:
                Spline(
                    [*mid_pts],
                )

            with BuildLine() as obstacle_line:
                add(start_line)
                add(spline_line)
                add(end_line)

        self.path_segment.path = obstacle_line.line

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for determining
        occupied nodes, debug and overview.
        """
        with BuildPart() as obstacle:
            # Recreate the path wire from the stored path
            with BuildLine() as line:
                add(self.path_segment.path)

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
            )

        obstacle.part.label = f"{self.name} Obstacle Solid"
        return obstacle.part


# Register the obstacle
register_obstacle("Alpha", Alpha)

if __name__ == "__main__":
    # Create
    obstacle = Alpha()

    # Visualization
    # obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
