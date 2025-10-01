# puzzle/cases/sphere.py

import math
from typing import Dict, Tuple

from config import Config
from puzzle.node import Node
from puzzle.utils.geometry import frange

from .base import Casing

Coordinate = Tuple[float, float, float]


class SphereCasing(Casing):
    def __init__(self, diameter: float, shell_thickness: float):
        self.node_size = Config.Puzzle.NODE_SIZE
        self.diameter = diameter
        self.shell_thickness = shell_thickness
        self.inner_radius = (diameter / 2) - shell_thickness

    def contains_point(self, x: float, y: float, z: float) -> bool:
        # Basic containment: inside inner sphere
        # Clearance, shrink effective radius by the cube half-diagonal so node cubes fit in utmost diagonal corner.

        cube_half_diagonal = (self.node_size * math.sqrt(3)) / 2.0
        effective_radius = self.inner_radius - cube_half_diagonal

        return x * x + y * y + z * z <= effective_radius**2

    def get_mounting_waypoints(self, nodes: list[Node]) -> list[Node]:
        """
        Get mounting waypoints for the spherical casing.
        Uses the generic circular waypoint selector on z=0.
        """
        number_of_waypoints = Config.Sphere.NUMBER_OF_MOUNTING_POINTS

        # Target a circle just outside the inner surface to pick the most outward nodes on z=0.
        target_radius = self.inner_radius + self.node_size

        return self.select_circular_waypoints(
            nodes=nodes,
            radius=target_radius,
            z_planes=[0.0],
            count_per_plane=number_of_waypoints,
        )

    def create_nodes(self) -> Tuple[list[Node], Dict[Coordinate, Node], Node]:
        """
        Create nodes for a spherical grid based on the provided puzzle configuration.
        """

        # Symmetric value lists using frange
        x_values = frange(-self.inner_radius, self.inner_radius, self.node_size)
        y_values = frange(-self.inner_radius, self.inner_radius, self.node_size)
        z_values = frange(-self.inner_radius, self.inner_radius, self.node_size)

        # Generate the rectangular grid using the base helper
        nodes, node_dict = self.generate_rectangular_grid_from_values(
            x_values=x_values, y_values=y_values, z_values=z_values
        )

        # Circular nodes on z=0
        circular_radius = self.inner_radius - self.node_size  # inside the shell
        circular_count = Config.Sphere.NUMBER_OF_MOUNTING_POINTS

        added_circular = self.add_circular_nodes_on_planes(
            nodes=nodes,
            node_dict=node_dict,
            radius=circular_radius,
            z_planes=[0.0],
            count_even=circular_count,
            grid_step=self.node_size,
            tolerance=self.node_size,
        )

        # Remove rectangular nodes too close to the circular nodes on z = 0
        self.remove_rectangular_nodes_close_to(
            nodes=nodes,
            node_dict=node_dict,
            reference_nodes=added_circular,
            cutoff_distance=self.node_size,
            z_planes={0.0},
        )

        # Start node along -X on the equatorial line (z = 0, y = 0)
        start_node: Node = self.place_start_node_along_negative_x(
            nodes=nodes,
            node_dict=node_dict,
            node_size=self.node_size,
            prefer_y=0.0,
            prefer_z=0.0,
        )

        return nodes, node_dict, start_node
