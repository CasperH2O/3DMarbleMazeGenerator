# puzzle/grid_layouts/grid_layout_box.py

from typing import Dict, Tuple

from config import Config
from puzzle.node import Node
from puzzle.utils.geometry import frange, squared_distance_xyz

from .grid_layout_base import Casing

Coordinate = Tuple[float, float, float]


class BoxCasing(Casing):
    def __init__(
        self, width: float, height: float, length: float, panel_thickness: float
    ):
        self.node_size = Config.Puzzle.NODE_SIZE
        self.width = width
        self.height = height
        self.length = length

        self.inner_half_width = width / 2 - panel_thickness
        self.inner_half_height = height / 2 - panel_thickness
        self.inner_half_length = length / 2 - panel_thickness

    def contains_point(self, x: float, y: float, z: float) -> bool:
        # Define boundaries adjusted for casing and half the node size ie path width
        effective_width = self.inner_half_width - self.node_size / 2
        effective_length = self.inner_half_length - self.node_size / 2
        effective_height = self.inner_half_height - self.node_size / 2

        return (
            -effective_width <= x <= effective_width
            and -effective_length <= y <= effective_length
            and -effective_height <= z <= effective_height
        )

    def get_mounting_waypoints(self, nodes: list[Node]) -> list[Node]:
        """
        Determine mounting waypoints for the box casing
        """

        # Place mounting points in the center of every panel face
        face_centers = [
            (0, -self.inner_half_length, 0),
            (0, self.inner_half_length, 0),
            (self.inner_half_width, 0, 0),
            (-self.inner_half_width, 0, 0),
            (0, 0, self.inner_half_height),
            (0, 0, -self.inner_half_height),
        ]

        mounting_nodes: list[Node] = []

        for x_face, y_face, z_face in face_centers:
            candidates = [node for node in nodes]

            if not candidates:
                continue

            nearest_node = min(
                candidates,
                key=lambda n: squared_distance_xyz(
                    n.x, n.y, n.z, x_face, y_face, z_face
                ),
            )

            nearest_node.mounting = True
            nearest_node.waypoint = True
            mounting_nodes.append(nearest_node)

        return mounting_nodes

    def create_nodes(self) -> Tuple[list[Node], Dict[Coordinate, Node], Node]:
        """
        Create nodes for a box grid based on the provided puzzle configuration.
        """

        x_values = frange(-self.inner_half_width, self.inner_half_width, self.node_size)
        y_values = frange(
            -self.inner_half_length, self.inner_half_length, self.node_size
        )
        z_values = frange(
            -self.inner_half_height, self.inner_half_height, self.node_size
        )

        # Use the generic rectangular grid generator (filtered by contains_point)
        nodes, node_dict = self.generate_rectangular_grid_from_values(
            x_values=x_values, y_values=y_values, z_values=z_values
        )

        # Define the start node for the box case
        start_node: Node = self.place_start_node_along_negative_x(
            nodes=nodes,
            node_dict=node_dict,
            node_size=self.node_size,
            prefer_y=min(y_values),
            prefer_z=min(z_values),
        )

        return nodes, node_dict, start_node
