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
                    if casing.contains_point(x, y, z):
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
        node_size = puzzle.node_size
        casing = puzzle.casing

        # Calculate grid boundaries based on the casing dimensions
        num_x = int(np.floor(casing.width / node_size))
        num_y = int(np.floor(casing.height / node_size))
        num_z = int(np.floor(casing.length / node_size))

        if num_x % 2 == 0:
            num_x += 1
        if num_y % 2 == 0:
            num_y += 1
        if num_z % 2 == 0:
            num_z += 1

        start_x = -(num_x // 2) * node_size
        start_y = -(num_y // 2) * node_size
        start_z = -(num_z // 2) * node_size

        x_values = [start_x + i * node_size for i in range(num_x)]
        y_values = [start_y + i * node_size for i in range(num_y)]
        z_values = [start_z + i * node_size for i in range(num_z)]

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if casing.contains_point(x, y, z):
                        node = Node(x, y, z)
                        nodes.append(node)

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
