# puzzle/cases/box.py

from typing import Any, Dict, List, Tuple

from puzzle.node import Node
from puzzle.utils.geometry import frange, key3, snap, squared_distance_xyz

from .base import Casing

Coordinate = Tuple[float, float, float]


class BoxCasing(Casing):
    def __init__(
        self, width: float, height: float, length: float, panel_thickness: float
    ):
        self.width = width
        self.height = height
        self.length = length
        self.panel_thickness = panel_thickness
        self.half_width = width / 2
        self.half_height = height / 2
        self.half_length = length / 2

    def contains_point(self, x: float, y: float, z: float) -> bool:
        return (
            -self.half_width <= x <= self.half_width
            and -self.half_length <= y <= self.half_length
            and -self.half_height <= z <= self.half_height
        )

    def get_mounting_waypoints(self, nodes: list[Node]) -> list[Node]:
        """
        Determine mounting waypoints for the box casing
        """

        # Place mounting points in the center of every panel face
        face_centers = [
            (0, -self.half_length, 0),
            (0, self.half_length, 0),
            (self.half_width, 0, 0),
            (-self.half_width, 0, 0),
            (0, 0, self.half_height),
            (0, 0, -self.half_height),
        ]

        mounting_nodes: list[Node] = []

        for x_face, y_face, z_face in face_centers:
            candidates = [node for node in nodes if not node.occupied]

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

    def create_nodes(
        self, puzzle: Any
    ) -> Tuple[list[Node], Dict[Coordinate, Node], Node]:
        """
        Create nodes for a box grid based on the provided puzzle configuration.
        """
        nodes: list[Node] = []
        node_dict: Dict[Coordinate, Node] = {}
        node_size: float = puzzle.node_size
        casing = puzzle.casing

        # Define grid boundaries adjusted for node_size and casing
        half_width: float = casing.width / 2 - casing.panel_thickness
        half_length: float = casing.length / 2 - casing.panel_thickness
        half_height: float = casing.height / 2 - casing.panel_thickness

        start_x: float = -half_width + node_size / 2
        end_x: float = half_width - node_size / 2
        start_y: float = -half_length + node_size / 2
        end_y: float = half_length - node_size / 2
        start_z: float = -half_height + node_size / 2
        end_z: float = half_height - node_size / 2

        x_values: list[float] = frange(start_x, end_x, node_size)
        y_values: list[float] = frange(start_y, end_y, node_size)
        z_values: list[float] = frange(start_z, end_z, node_size)

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if casing.contains_point(x, y, z):
                        node = Node(x, y, z)
                        nodes.append(node)
                        node_dict[key3(x, y, z)] = node

        if not nodes:
            raise ValueError("No nodes were created inside the box casing.")

        # Define the start node for the box case
        # Find the minimum x among existing nodes
        min_x: float = min(node.x for node in nodes)
        min_y: float = min(node.y for node in nodes if node.x == min_x)
        min_z: float = min(
            node.z for node in nodes if node.x == min_x and node.y == min_y
        )

        # Extend along the negative x-direction
        x1 = snap(min_x - node_size)
        x2 = snap(x1 - node_size)

        # Create two new nodes at positions (x1, min_y, min_z) and (x2, min_y, min_z)
        node1 = Node(x1, min_y, min_z)
        node2 = Node(x2, min_y, min_z)

        # Add them to nodes and node_dict
        nodes.extend([node1, node2])
        node_dict[key3(node1.x, node1.y, node1.z)] = node1
        node_dict[key3(node2.x, node2.y, node2.z)] = node2

        # Mark the furthest node as the start node (node 2)
        node2.puzzle_start = True
        start_node: Node = node2

        return nodes, node_dict, start_node
