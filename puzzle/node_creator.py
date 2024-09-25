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
        effective_radius = (puzzle.diameter / 2) - puzzle.shell_thickness - ((node_size * np.sqrt(3)) / 2)

        num_cubes_along_axis = int(np.floor(2 * effective_radius / node_size))
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
        return nodes, node_dict

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
