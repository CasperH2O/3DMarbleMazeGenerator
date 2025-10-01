# puzzle/cases/cylinder.py

import math
from typing import Dict, List, Tuple

from config import Config
from puzzle.node import Node
from puzzle.utils.geometry import frange

from .base import Casing

Coordinate = Tuple[float, float, float]


class CylinderCasing(Casing):
    """
    Vertical cylinder centered at origin.
    """

    def __init__(self, diameter: float, height: float, shell_thickness: float):
        self.node_size = Config.Puzzle.NODE_SIZE
        self.diameter = diameter
        self.height = height
        self.shell_thickness = shell_thickness

        self.inner_radius = (diameter / 2) - shell_thickness
        self.inner_half_height = (height / 2) - shell_thickness

    def contains_point(self, x: float, y: float, z: float) -> bool:
        square_half_diagonal = self.node_size / math.sqrt(2)
        effective_radius = self.inner_radius - square_half_diagonal

        return (x * x + y * y) <= effective_radius**2 and (
            -self.inner_half_height <= z <= self.inner_half_height
        )

    def get_mounting_waypoints(self, nodes: List[Node]) -> List[Node]:
        """
        Generic circular waypoint selection.
        For a cylinder we can choose multiple planes; by default: bottom, mid, top.
        """

        count = Config.Cylinder.NUMBER_OF_MOUNTING_POINTS
        target_radius = self.inner_radius + self.node_size
        z_planes = [-self.inner_half_height, 0.0, self.inner_half_height]

        return self.select_circular_waypoints(
            nodes=nodes,
            radius=target_radius,
            z_planes=z_planes,
            count_per_plane=count,
        )

    def create_nodes(self) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
        # Symmetric value lists
        x_values = frange(-self.inner_radius, self.inner_radius, self.node_size)
        y_values = frange(-self.inner_radius, self.inner_radius, self.node_size)
        z_values = frange(
            -self.inner_half_height, self.inner_half_height, self.node_size
        )

        # Fill by rectangular grid and filter by contains point shape
        nodes, node_dict = self.generate_rectangular_grid_from_values(
            x_values=x_values, y_values=y_values, z_values=z_values
        )

        # Circular rings, multiple planes
        mounting_points_count = Config.Cylinder.NUMBER_OF_MOUNTING_POINTS
        ring_radius = self.inner_radius - self.node_size
        ring_planes = z_values

        added_circular = self.add_circular_nodes_on_planes(
            nodes=nodes,
            node_dict=node_dict,
            radius=ring_radius,
            z_planes=ring_planes,
            count_even=mounting_points_count,
            grid_step=self.node_size,
        )

        # Remove rectangular nodes too close to the circular nodes on all z planes
        self.remove_rectangular_nodes_close_to(
            nodes=nodes,
            node_dict=node_dict,
            reference_nodes=added_circular,
            cutoff_distance=self.node_size,
            z_planes=z_values,
        )

        # Start node: extend along -X on the center line (y = 0, z = 0)
        start_node: Node = self.place_start_node_along_negative_x(
            nodes=nodes,
            node_dict=node_dict,
            node_size=self.node_size,
            prefer_y=0.0,
            prefer_z=0.0,
        )

        return nodes, node_dict, start_node
