# puzzle/node_creator.py

from abc import ABC, abstractmethod
from .node import Node
import numpy as np


class NodeCreator(ABC):
    @abstractmethod
    def create_nodes(self, puzzle):
        pass

    @abstractmethod
    def get_neighbors(self, node, node_dict, node_size):
        pass


class SphereGridNodeCreator(NodeCreator):
    def create_nodes(self, puzzle):
        nodes = []
        node_size = puzzle.node_size
        casing = puzzle.casing

        cube_half_diagonal = (node_size * np.sqrt(3)) / 2
        effective_radius = casing.inner_radius - cube_half_diagonal

        # Calculate grid boundaries based on the casing dimensions
        dimension = casing.diameter - 2 * casing.shell_thickness
        num_cubes_along_axis = int(np.floor(dimension / node_size))
        if num_cubes_along_axis % 2 == 0:
            num_cubes_along_axis += 1

        start_pos = -(num_cubes_along_axis // 2) * node_size

        x_values = [start_pos + i * node_size for i in range(num_cubes_along_axis)]
        y_values = x_values
        z_values = x_values

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    distance = np.sqrt(x ** 2 + y ** 2 + z ** 2)
                    if distance <= effective_radius:
                        node = Node(x, y, z)
                        nodes.append(node)

        node_dict = {(node.x, node.y, node.z): node for node in nodes}

        # Define the start node
        # Find the minimum x among existing nodes on the X-axis (where y=0 and z=0)
        x_axis_nodes = [node for node in nodes if node.y == 0 and node.z == 0]
        if x_axis_nodes:
            min_x = min(node.x for node in x_axis_nodes)
        else:
            min_x = 0  # If no nodes exist, start from 0

        # Calculate positions for the two new nodes in the negative x direction
        x1 = min_x - node_size
        x2 = x1 - node_size

        # Create two new nodes at positions (x1, 0, 0) and (x2, 0, 0)
        node1 = Node(x1, 0, 0)
        node2 = Node(x2, 0, 0)

        # Add them to nodes and node_dict
        nodes.extend([node1, node2])
        node_dict[(node1.x, node1.y, node1.z)] = node1
        node_dict[(node2.x, node2.y, node2.z)] = node2

        # Since x2 < x1, node2 is furthest from (0, 0, 0)
        node2.start = True  # Mark the furthest node as the start node
        start_node = node2

        return nodes, node_dict, start_node

    def get_neighbors(self, node, node_dict, node_size):
        neighbors = []
        directions = [
            (node_size, 0, 0), (-node_size, 0, 0),
            (0, node_size, 0), (0, -node_size, 0),
            (0, 0, node_size), (0, 0, -node_size)
        ]
        for dx, dy, dz in directions:
            neighbor_coordinates = (node.x + dx, node.y + dy, node.z + dz)
            neighbor = node_dict.get(neighbor_coordinates)
            if neighbor and not neighbor.occupied:
                neighbors.append(neighbor)
        return neighbors


class BoxGridNodeCreator(NodeCreator):
    def create_nodes(self, puzzle):
        nodes = []
        node_dict = {}
        node_size = puzzle.node_size
        casing = puzzle.casing

        # Define grid boundaries adjusted for node_size and casing
        half_width = casing.width / 2 - 2 * casing.panel_thickness
        half_height = casing.height / 2 - 2 * casing.panel_thickness
        half_length = casing.length / 2 - 2 * casing.panel_thickness

        start_x = -half_width + node_size / 2
        end_x = half_width - node_size / 2
        start_y = -half_height + node_size / 2
        end_y = half_height - node_size / 2
        start_z = -half_length + node_size / 2
        end_z = half_length - node_size / 2

        x_values = np.arange(start_x, end_x + node_size * 0.1, node_size)
        y_values = np.arange(start_y, end_y + node_size * 0.1, node_size)
        z_values = np.arange(start_z, end_z + node_size * 0.1, node_size)

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if casing.contains_point(x, y, z):
                        node = Node(x, y, z)
                        nodes.append(node)
                        node_dict[(x, y, z)] = node

        node_dict = {(node.x, node.y, node.z): node for node in nodes}

        # Define the start node
        # For the box, the start node is at the minimum x, y, z
        min_x = min(node.x for node in nodes)
        min_y = min(node.y for node in nodes)
        min_z = min(node.z for node in nodes)
        start_node = node_dict.get((min_x, min_y, min_z))
        if start_node:
            start_node.start = True

        return nodes, node_dict, start_node

    def get_neighbors(self, node, node_dict, node_size):
        neighbors = []
        directions = [
            (node_size, 0, 0), (-node_size, 0, 0),
            (0, node_size, 0), (0, -node_size, 0),
            (0, 0, node_size), (0, 0, -node_size)
        ]
        for dx, dy, dz in directions:
            neighbor_coordinates = (node.x + dx, node.y + dy, node.z + dz)
            neighbor = node_dict.get(neighbor_coordinates)
            if neighbor and not neighbor.occupied:
                neighbors.append(neighbor)
        return neighbors
