# obstacles/obstacle_placeholder2.py

from build123d import BuildLine, BuildPart, Cylinder, Part, Polyline
from ocp_vscode import show

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class ObstaclePlaceHolder2(Obstacle):
    """An obstacle."""

    def __init__(self):
        super().__init__(name="ObstaclePlaceHolder2")

        # TODO for laterupon creation, do location/orientation

        # Load occupied nodes from cache or determine
        self.load_relative_node_coords()

        # From obstacle geometry, determine entry and exit nodes
        # TODO move to better place, either on usage of obstacle or on visualization
        self.determine_entry_exit_nodes()

    def create_obstacle_geometry(self):
        """Generates the geometry for the obstacle."""

        with BuildLine() as obstacle_line:
            Polyline([(0, 0, 0), (0, self.node_size, 0)])

        self.path_segment.path = obstacle_line.line

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for, determining
        occupied nodes, debug and overview.
        """

        with BuildPart() as obstacle:
            Cylinder(radius=self.node_size / 2, height=self.node_size)

        return obstacle


# Register the obstacle
register_obstacle("ObstaclePlaceHolder2", ObstaclePlaceHolder2)

if __name__ == "__main__":
    # Visualization
    obstacle = ObstaclePlaceHolder2()
    obstacle.visualize()

    # Solid model
    obstacle.create_obstacle_geometry()
    obstacle_solid = obstacle.model_solid()
    overlap_cubes = obstacle.solid_model_node_cubes(
        nodes=obstacle.overlap_nodes, name="Overlap Node", color="#00444900"
    )
    occupied_cubes = obstacle.solid_model_node_cubes(
        nodes=obstacle.occupied_nodes, name="Occupied Node", color="#40004947"
    )
    show(obstacle_solid, occupied_cubes, overlap_cubes)
