# puzzle/node_creator.py

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict
import math

from puzzle.node import Node


def frange(start: float, stop: float, step: float) -> List[float]:
    """
    Generate a range of floating-point numbers.

    :param start: Starting value.
    :param stop: Ending value (inclusive).
    :param step: Step size.
    :return: List of floating-point numbers.
    """
    values = []
    while start <= stop + step / 2:
        values.append(round(start, 10))  # Rounding to avoid floating-point arithmetic issues
        start += step
    return values


class NodeCreator(ABC):
    @abstractmethod
    def create_nodes(self, puzzle) -> Tuple[List[Node], Dict[Tuple[float, float, float], Node], Node]:
        """Create nodes for the puzzle."""
        pass

    @abstractmethod
    def get_neighbors(self, node: Node, node_dict: Dict[Tuple[float, float, float], Node], node_size: float) -> List[Node]:
        """Get neighboring nodes for a given node."""
        pass


class SphereGridNodeCreator(NodeCreator):
    def create_nodes(self, puzzle) -> Tuple[List[Node], Dict[Tuple[float, float, float], Node], Node]:
        """
        Create nodes for a spherical grid.

        :param puzzle: Puzzle object containing node size and casing information.
        :return: Tuple containing list of nodes, node dictionary, and start node.
        """
        nodes = []
        node_size = puzzle.node_size
        casing = puzzle.casing

        cube_half_diagonal = (node_size * math.sqrt(3)) / 2
        effective_radius = casing.inner_radius - cube_half_diagonal

        # Calculate grid boundaries based on the casing dimensions
        internal_dimension = casing.diameter - 2 * casing.shell_thickness
        num_cubes_along_axis = int(math.floor(internal_dimension / node_size))
        if num_cubes_along_axis % 2 == 0:
            num_cubes_along_axis += 1  # Ensure an odd number for symmetry

        start_pos = -(num_cubes_along_axis // 2) * node_size

        x_values = [start_pos + i * node_size for i in range(num_cubes_along_axis)]
        y_values = x_values
        z_values = x_values

        effective_radius_squared = effective_radius ** 2

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    distance_squared = x ** 2 + y ** 2 + z ** 2
                    if distance_squared <= effective_radius_squared:
                        node = Node(x, y, z)
                        nodes.append(node)

        if not nodes:
            raise ValueError("No nodes were created inside the spherical casing.")

        node_dict = {(node.x, node.y, node.z): node for node in nodes}

        # Define the start node
        # Find the minimum x among existing nodes on the X-axis (where y=0 and z=0)
        x_axis_nodes = [node for node in nodes if node.y == 0 and node.z == 0]
        if x_axis_nodes:
            min_x = min(node.x for node in x_axis_nodes)
        else:
            min_x = 0  # If no nodes exist on the X-axis, start from 0

        # Extend the start point with two additional nodes in the negative x direction
        x1 = min_x - node_size
        x2 = x1 - node_size

        # Create two new nodes at positions (x1, 0, 0) and (x2, 0, 0)
        node1 = Node(x1, 0, 0)
        node2 = Node(x2, 0, 0)

        # Add them to nodes and node_dict
        nodes.extend([node1, node2])
        node_dict[(node1.x, node1.y, node1.z)] = node1
        node_dict[(node2.x, node2.y, node2.z)] = node2

        # Mark the furthest node as the start node
        node2.puzzle_start = True  # node2 is the start node since it's furthest along -x
        start_node = node2

        return nodes, node_dict, start_node

    def get_neighbors(self, node: Node, node_dict: Dict[Tuple[float, float, float], Node], node_size: float) -> List[Node]:
        """
        Get neighboring nodes for a given node in the spherical grid.

        :param node: The current node.
        :param node_dict: Dictionary of all nodes.
        :param node_size: The size of each node.
        :return: List of neighboring nodes.
        """
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
    def create_nodes(self, puzzle) -> Tuple[List[Node], Dict[Tuple[float, float, float], Node], Node]:
        """
        Create nodes for a box grid.

        :param puzzle: Puzzle object containing node size and casing information.
        :return: Tuple containing list of nodes, node dictionary, and start node.
        """
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

        x_values = frange(start_x, end_x, node_size)
        y_values = frange(start_y, end_y, node_size)
        z_values = frange(start_z, end_z, node_size)

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if casing.contains_point(x, y, z):
                        node = Node(x, y, z)
                        nodes.append(node)
                        node_dict[(x, y, z)] = node

        if not nodes:
            raise ValueError("No nodes were created inside the box casing.")

        node_dict = {(node.x, node.y, node.z): node for node in nodes}

        # Define the start node for the box case
        # Find the minimum x among existing nodes
        min_x = min(node.x for node in nodes)
        min_y = min(node.y for node in nodes if node.x == min_x)
        min_z = min(node.z for node in nodes if node.x == min_x and node.y == min_y)

        # Extend along the negative x-direction
        x1 = min_x - node_size
        x2 = x1 - node_size

        # Create two new nodes at positions (x1, min_y, min_z) and (x2, min_y, min_z)
        node1 = Node(x1, min_y, min_z)
        node2 = Node(x2, min_y, min_z)

        # Add them to nodes and node_dict
        nodes.extend([node1, node2])
        node_dict[(node1.x, node1.y, node1.z)] = node1
        node_dict[(node2.x, node2.y, node2.z)] = node2

        # Mark the furthest node as the start node
        node2.puzzle_start = True  # node2 is the start node since it's furthest along -x
        start_node = node2

        return nodes, node_dict, start_node

    def get_neighbors(self, node: Node, node_dict: Dict[Tuple[float, float, float], Node], node_size: float) -> List[Node]:
        """
        Get neighboring nodes for a given node in the box grid.

        :param node: The current node.
        :param node_dict: Dictionary of all nodes.
        :param node_size: The size of each node.
        :return: List of neighboring nodes.
        """
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
