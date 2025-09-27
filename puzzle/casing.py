# puzzle/casing.py

import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from config import Config
from puzzle.node import Node


class Casing(ABC):
    """
    Abstract base class representing a generic casing.
    """

    @abstractmethod
    def contains_point(self, x: float, y: float, z: float) -> bool:
        """
        Check if a point is inside the casing.
        """
        pass

    @abstractmethod
    def get_mounting_waypoints(self, nodes: List[Node]) -> List[Node]:
        """
        Get mounting waypoints for the casing.
        """
        pass


class SphereCasing(Casing):
    """
    Class representing a spherical casing.
    """

    def __init__(self, diameter: float, shell_thickness: float):
        """
        Initialize a spherical casing.
        """
        self.diameter = diameter
        self.shell_thickness = shell_thickness
        self.inner_radius = (diameter / 2) - shell_thickness

    def contains_point(self, x: float, y: float, z: float) -> bool:
        """
        Check if the point is inside the inner sphere.
        """
        distance_squared = x**2 + y**2 + z**2
        return distance_squared <= self.inner_radius**2

    def get_mounting_waypoints(self, nodes: List[Node]) -> List[Node]:
        """
        Get mounting waypoints for the spherical casing.
        """
        num_mounting_waypoints = Config.Sphere.NUMBER_OF_MOUNTING_POINTS
        radius = self.inner_radius + Config.Puzzle.NODE_SIZE
        angle_increment = 2 * math.pi / num_mounting_waypoints
        mounting_nodes = []

        # Define mounting waypoints around the sphere,
        # find most outward node near angle increment
        for i in range(num_mounting_waypoints):
            # Start from angle π (180 degrees) to position waypoints appropriately
            angle = i * angle_increment + math.pi
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)

            candidates = [
                node
                for node in nodes
                if node.z == 0 and not node.occupied and node not in mounting_nodes
            ]

            if not candidates:
                print("No available nodes at Z = 0 for mounting waypoints.")
                continue

            nearest_node = min(
                candidates, key=lambda node: (node.x - x) ** 2 + (node.y - y) ** 2
            )
            nearest_node.mounting = True
            nearest_node.waypoint = True  # Include in pathfinding
            mounting_nodes.append(nearest_node)

        return mounting_nodes


class BoxCasing(Casing):
    """
    Class representing a box-shaped casing.
    """

    def __init__(
        self, width: float, height: float, length: float, panel_thickness: float
    ):
        """
        Initialize a box casing.
        """
        self.width = width
        self.height = height
        self.length = length
        self.half_width = width / 2
        self.half_height = height / 2
        self.half_length = length / 2
        self.panel_thickness = panel_thickness

    def contains_point(self, x: float, y: float, z: float) -> bool:
        """
        Check if the point is inside the box.
        """
        return (
            -self.half_width <= x <= self.half_width
            and -self.half_length <= y <= self.half_length
            and -self.half_height <= z <= self.half_height
        )

    def get_start_node(
        self, node_dict: Dict[Tuple[float, float, float], Node]
    ) -> Optional[Node]:
        """
        Get the start node at one corner of the box.
        """
        if not node_dict:
            print("Node dictionary is empty. Cannot determine start node.")
            return None

        min_x = min(x for x, y, z in node_dict.keys())
        min_y = min(y for x, y, z in node_dict.keys())
        min_z = min(z for x, y, z in node_dict.keys())

        start_node = node_dict.get((min_x, min_y, min_z))

        if start_node:
            start_node.puzzle_start = True

        return start_node

    def get_mounting_waypoints(self, nodes: List[Node]) -> List[Node]:
        """
        Get mounting waypoints for the box casing
        """
        # Place mounting points in the center of every panel face
        face_centers = [
            (0, -self.half_length, 0),  # Front face  (-Y)
            (0,  self.half_length, 0),  # Back face   (+Y)
            ( self.half_width, 0, 0),   # Right face  (+X)
            (-self.half_width, 0, 0),   # Left face   (-X)
            (0, 0,  self.half_height),  # Top face    (+Z)
            (0, 0, -self.half_height),  # Bottom face (-Z)
        ]
        mounting_nodes = []

        for x_face, y_face, z_face in face_centers:
            candidates = [node for node in nodes if not node.occupied]

            if not candidates:
                print("No available nodes for mounting waypoints.")
                continue

            nearest_node = min(
                candidates,
                key=lambda node: (node.x - x_face) ** 2
                + (node.y - y_face) ** 2
                + (node.z - z_face) ** 2,
            )

            nearest_node.mounting = True
            nearest_node.waypoint = True  # Include in pathfinding
            mounting_nodes.append(nearest_node)

        return mounting_nodes
