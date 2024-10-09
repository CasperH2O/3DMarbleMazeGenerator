# puzzle/casing.py

from abc import ABC, abstractmethod
import numpy as np
import random

import config


class Casing(ABC):
    @abstractmethod
    def contains_point(self, x, y, z) -> bool:
        """Check if a point is inside the casing."""
        pass

    @abstractmethod
    def get_mounting_waypoints(self, nodes, seed):
        pass

    @abstractmethod
    def get_dimensions(self):
        """Return the dimensions of the casing."""
        pass


class SphereCasing(Casing):
    def __init__(self, diameter, shell_thickness):
        self.diameter = diameter
        self.shell_thickness = shell_thickness
        self.inner_radius = (diameter / 2) - shell_thickness

    def contains_point(self, x, y, z) -> bool:
        distance = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        return distance <= self.inner_radius

    def get_mounting_waypoints(self, nodes, seed):
        random.seed(seed)

        # Use the number of mounting waypoints from config
        num_mounting_waypoints = config.NUMBER_OF_WAYPOINTS

        # Get the outer radius at Z = 0
        outer_radius = self.inner_radius

        # Calculate the angle between waypoints
        angle_increment = 2 * np.pi / num_mounting_waypoints

        mounting_nodes = []

        for i in range(num_mounting_waypoints):
            angle = i * angle_increment + np.pi  # Start from angle π (180 degrees)

            # Calculate the (x, y) coordinates for this mounting node
            x = outer_radius * np.cos(angle)
            y = outer_radius * np.sin(angle)

            # Find the nearest unoccupied node at Z = 0
            candidates = [
                node for node in nodes
                if node.z == 0 and not node.occupied and node not in mounting_nodes
            ]

            if not candidates:
                print("No available nodes at Z = 0 for mounting waypoints.")
                continue

            nearest_node = min(
                candidates,
                key=lambda node: np.sqrt((node.x - x) ** 2 + (node.y - y) ** 2)
            )
            nearest_node.mounting = True
            nearest_node.waypoint = True  # Mark as a waypoint to include in pathfinding

            mounting_nodes.append(nearest_node)

        print(f"Defined {len(mounting_nodes)} mounting waypoints: {mounting_nodes}")
        return mounting_nodes

    def get_dimensions(self):
        return {'diameter': self.diameter, 'shell_thickness': self.shell_thickness}


class BoxCasing(Casing):
    def __init__(self, width, height, length, panel_thickness):
        self.width = width
        self.height = height
        self.length = length
        self.half_width = width / 2
        self.half_height = height / 2
        self.half_length = length / 2
        self.panel_thickness = panel_thickness

    def contains_point(self, x, y, z) -> bool:
        return (-self.half_width <= x <= self.half_width and
                -self.half_height <= y <= self.half_height and
                -self.half_length <= z <= self.half_length)

    def get_start_node(self, node_dict):
        # Start node at one corner of the box
        min_x = min(x for x, y, z in node_dict.keys())
        min_y = min(y for x, y, z in node_dict.keys())
        min_z = min(z for x, y, z in node_dict.keys())
        start_node = node_dict.get((min_x, min_y, min_z))
        if start_node:
            start_node.start = True
        return start_node

    def get_mounting_waypoints(self, nodes, seed):
        # Implement mounting waypoints logic for box casing
        random.seed(seed)

        # For example, select nodes at the center of each face
        face_centers = [
            (0, 0, -self.half_length),  # Front face
            (0, 0, self.half_length),  # Back face
            (self.half_width, 0, 0),  # Right face
            (-self.half_width, 0, 0),  # Left face
            (0, self.half_height, 0),  # Top face
            (0, -self.half_height, 0),  # Bottom face
        ]

        mounting_nodes = []

        for x_face, y_face, z_face in face_centers:
            # Find the nearest unoccupied node to the face center
            candidates = [
                node for node in nodes
                if not node.occupied
            ]

            nearest_node = min(
                candidates,
                key=lambda node: np.sqrt((node.x - x_face) ** 2 + (node.y - y_face) ** 2 + (node.z - z_face) ** 2)
            )
            nearest_node.mounting = True
            nearest_node.waypoint = True  # Mark as a waypoint to include in pathfinding

            mounting_nodes.append(nearest_node)

        print(f"Defined {len(mounting_nodes)} mounting waypoints for Box: {mounting_nodes}")
        return mounting_nodes

    def get_dimensions(self):
        return {'width': self.width, 'height': self.height, 'length': self.length}
