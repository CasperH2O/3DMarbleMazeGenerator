# obstacles/obstacle_placeholder2.py

from build123d import BuildPart, Cylinder, Part
from ocp_vscode import show

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class ObstaclePlaceHolder2(Obstacle):
    """An obstacle."""

    def __init__(self):
        super().__init__(name="ObstaclePlaceHolder2")

        # Generate the required geometry on obstacle initialization
        self.create_obstacle_geometry()

        # Sample points along path segment edge for visualization
        self.sample_obstacle_path()

        # Determine occupied nodes or load from cach
        self._occupied_nodes = self.get_relative_occupied_coords()

    def create_obstacle_geometry(self) -> Part:
        """Generates the geometry for the obstacle."""

        with BuildPart() as obstacle:
            Cylinder(radius=self.node_size / 2, height=self.node_size)

        return obstacle.part

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for, determining
        occupied nodes, debug and overview.
        """
        return self.create_obstacle_geometry()


# Register the obstacle
register_obstacle("ObstaclePlaceHolder2", ObstaclePlaceHolder2)

if __name__ == "__main__":
    # Visualization
    obstacle = ObstaclePlaceHolder2()
    obstacle.visualize()

    # Solid model
    obstacle_solid = obstacle.model_solid()
    cubes = obstacle.create_occupied_node_cubes()
    show(obstacle_solid, cubes)
