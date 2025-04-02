# obstacles/obstacle_placeholder1.py

from typing import List, Tuple

from build123d import Box, BuildPart, Part, Vector

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class ObstaclePlaceHolder1(Obstacle):
    """An obstacle."""

    def __init__(self):
        # TODO, double check if this is the approach I want
        super().__init__(name="ObstaclePlaceHolder1")

    def create_obstacle_geometry(self) -> Part:
        """Generates the geometry for the obstacle."""

        with BuildPart() as obstacle:
            Box(10, 10, 10)

        return obstacle.part

    def get_relative_occupied_coords(self, node_size: float) -> List[Vector]:
        """
        Determine occupied nodes for this obstacle.
        """

        # Harcoded values for this obstacle shape, scale with node size
        occupied_relative_coords = []

        print(
            f"Found {len(occupied_relative_coords)} relative occupied coords for {self.name}"
        )
        return list(occupied_relative_coords)

    def get_relative_entry_exit_coords(self) -> Tuple[Vector, Vector]:
        """Define entry/exit points relative to the obstacle's geometry."""

        entry_coord = (0, 0, 0)
        exit_coord = (0, 0, 0)

        print(f"{self.name} relative entry: {entry_coord}, exit: {exit_coord}")
        return entry_coord, exit_coord


# Register the obstacle
register_obstacle("ObstaclePlaceHolder1", ObstaclePlaceHolder1)
