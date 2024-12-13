# puzzle/node_creator.py

from abc import ABC, abstractmethod
import math
from typing import Any, Dict, List, Tuple

from puzzle.node import Node

Coordinate = Tuple[float, float, float]


def frange(start: float, stop: float, step: float) -> List[float]:
    """
    Generate a range of floating-point numbers from `start` to `stop` inclusive with a given `step`.

    Parameters:
        start (float): The starting value of the sequence.
        stop (float): The end value of the sequence (inclusive).
        step (float): The difference between each number in the sequence.

    Returns:
        List[float]: A list of floating-point numbers.
    """
    values: List[float] = []
    while start <= stop + step / 2:
        values.append(round(start, 10))  # Rounding to avoid floating-point arithmetic issues
        start += step
    return values


class NodeCreator(ABC):
    @abstractmethod
    def create_nodes(
        self, puzzle: Any
    ) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
        """
        Create nodes for the puzzle.

        Parameters:
            puzzle (Any): The puzzle object containing node size and casing information.

        Returns:
            Tuple[List[Node], Dict[Coordinate, Node], Node]: A tuple containing the list of nodes,
            a dictionary mapping coordinates to nodes, and the start node.
        """
        pass

    @abstractmethod
    def get_neighbors(
        self, node: Node, node_dict: Dict[Coordinate, Node], node_size: float
    ) -> List[Node]:
        """
        Get neighboring nodes for a given node.

        Parameters:
            node (Node): The node for which neighbors are to be found.
            node_dict (Dict[Coordinate, Node]): Dictionary mapping coordinates to nodes.
            node_size (float): The size of each node.

        Returns:
            List[Node]: List of neighboring nodes.
        """
        pass


class SphereGridNodeCreator(NodeCreator):
    def create_nodes(
        self, puzzle: Any
    ) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
        """
        Create nodes for a spherical grid based on the provided puzzle configuration.

        Parameters:
            puzzle (Any): The puzzle object containing node size and casing information.

        Returns:
            Tuple[List[Node], Dict[Coordinate, Node], Node]:
                - List of nodes within the spherical casing.
                - Dictionary mapping node coordinates to Node instances.
                - The start node for the puzzle.
        """
        nodes: List[Node] = []
        node_size: float = puzzle.node_size
        casing = puzzle.casing

        cube_half_diagonal: float = (node_size * math.sqrt(3)) / 2
        effective_radius: float = casing.inner_radius - cube_half_diagonal

        # Calculate grid boundaries based on the casing dimensions
        internal_dimension: float = casing.diameter - 2 * casing.shell_thickness
        num_cubes_along_axis: int = int(math.floor(internal_dimension / node_size))
        if num_cubes_along_axis % 2 == 0:
            num_cubes_along_axis += 1  # Ensure an odd number for symmetry

        start_pos: float = -(num_cubes_along_axis // 2) * node_size

        x_values: List[float] = [
            start_pos + i * node_size for i in range(num_cubes_along_axis)
        ]
        y_values: List[float] = x_values
        z_values: List[float] = x_values

        effective_radius_squared: float = effective_radius ** 2

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    distance_squared: float = x ** 2 + y ** 2 + z ** 2
                    if distance_squared <= effective_radius_squared:
                        node = Node(x, y, z)
                        nodes.append(node)

        if not nodes:
            raise ValueError("No nodes were created inside the spherical casing.")

        node_dict: Dict[Coordinate, Node] = {
            (node.x, node.y, node.z): node for node in nodes
        }

        # Define the start node
        # Find the minimum x among existing nodes on the X-axis (where y=0 and z=0)
        x_axis_nodes: List[Node] = [
            node for node in nodes if node.y == 0 and node.z == 0
        ]
        if x_axis_nodes:
            min_x: float = min(node.x for node in x_axis_nodes)
        else:
            min_x = 0  # If no nodes exist on the X-axis, start from 0

        # Extend the start point with two additional nodes in the negative x direction
        x1: float = min_x - node_size
        x2: float = x1 - node_size

        # Create two new nodes at positions (x1, 0, 0) and (x2, 0, 0)
        node1 = Node(x1, 0, 0)
        node2 = Node(x2, 0, 0)

        # Add them to nodes and node_dict
        nodes.extend([node1, node2])
        node_dict[(node1.x, node1.y, node1.z)] = node1
        node_dict[(node2.x, node2.y, node2.z)] = node2

        # Mark the furthest node as the start node
        node2.puzzle_start = True  # node2 is the start node since it's furthest along -x
        start_node: Node = node2

        return nodes, node_dict, start_node

    def get_neighbors(
        self, node: Node, node_dict: Dict[Coordinate, Node], node_size: float
    ) -> List[Node]:
        """
        Get neighboring nodes for a given node in the spherical grid.

        Parameters:
            node (Node): The current node.
            node_dict (Dict[Coordinate, Node]): Dictionary mapping node coordinates to Node instances.
            node_size (float): The size of each node.

        Returns:
            List[Node]: List of neighboring nodes that are not occupied.
        """
        neighbors: List[Node] = []
        directions: List[Coordinate] = [
            (node_size, 0, 0),
            (-node_size, 0, 0),
            (0, node_size, 0),
            (0, -node_size, 0),
            (0, 0, node_size),
            (0, 0, -node_size),
        ]
        for dx, dy, dz in directions:
            neighbor_coordinates: Coordinate = (
                node.x + dx,
                node.y + dy,
                node.z + dz,
            )
            neighbor = node_dict.get(neighbor_coordinates)
            if neighbor and not neighbor.occupied:
                neighbors.append(neighbor)
        return neighbors


class BoxGridNodeCreator(NodeCreator):
    def create_nodes(
        self, puzzle: Any
    ) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
        """
        Create nodes for a box grid based on the provided puzzle configuration.

        Parameters:
            puzzle (Any): The puzzle object containing node size and casing information.

        Returns:
            Tuple[List[Node], Dict[Coordinate, Node], Node]:
                - List of nodes within the box casing.
                - Dictionary mapping node coordinates to Node instances.
                - The start node for the puzzle.
        """
        nodes: List[Node] = []
        node_dict: Dict[Coordinate, Node] = {}
        node_size: float = puzzle.node_size
        casing = puzzle.casing

        # Define grid boundaries adjusted for node_size and casing
        half_width: float = casing.width / 2 - 2 * casing.panel_thickness
        half_length: float = casing.length / 2 - 2 * casing.panel_thickness
        half_height: float = casing.height / 2 - 2 * casing.panel_thickness

        start_x: float = -half_width + node_size / 2
        end_x: float = half_width - node_size / 2
        start_y: float = -half_length + node_size / 2
        end_y: float = half_length - node_size / 2
        start_z: float = -half_height + node_size / 2
        end_z: float = half_height - node_size / 2

        x_values: List[float] = frange(start_x, end_x, node_size)
        y_values: List[float] = frange(start_y, end_y, node_size)
        z_values: List[float] = frange(start_z, end_z, node_size)

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if casing.contains_point(x, y, z):
                        node = Node(x, y, z)
                        nodes.append(node)
                        node_dict[(x, y, z)] = node

        if not nodes:
            raise ValueError("No nodes were created inside the box casing.")

        # Define the start node for the box case
        # Find the minimum x among existing nodes
        min_x: float = min(node.x for node in nodes)
        min_y: float = min(node.y for node in nodes if node.x == min_x)
        min_z: float = min(node.z for node in nodes if node.x == min_x and node.y == min_y)

        # Extend along the negative x-direction
        x1: float = min_x - node_size
        x2: float = x1 - node_size

        # Create two new nodes at positions (x1, min_y, min_z) and (x2, min_y, min_z)
        node1 = Node(x1, min_y, min_z)
        node2 = Node(x2, min_y, min_z)

        # Add them to nodes and node_dict
        nodes.extend([node1, node2])
        node_dict[(node1.x, node1.y, node1.z)] = node1
        node_dict[(node2.x, node2.y, node2.z)] = node2

        # Mark the furthest node as the start node
        node2.puzzle_start = True  # node2 is the start node since it's furthest along -x
        start_node: Node = node2

        return nodes, node_dict, start_node

    def get_neighbors(
        self, node: Node, node_dict: Dict[Coordinate, Node], node_size: float
    ) -> List[Node]:
        """
        Get neighboring nodes for a given node in the box grid.

        Parameters:
            node (Node): The current node.
            node_dict (Dict[Coordinate, Node]): Dictionary mapping coordinates to nodes.
            node_size (float): The size of each node.

        Returns:
            List[Node]: List of neighboring nodes that are not occupied.
        """
        neighbors: List[Node] = []
        directions: List[Coordinate] = [
            (node_size, 0, 0),
            (-node_size, 0, 0),
            (0, node_size, 0),
            (0, -node_size, 0),
            (0, 0, node_size),
            (0, 0, -node_size),
        ]
        for dx, dy, dz in directions:
            neighbor_coordinates: Coordinate = (
                node.x + dx,
                node.y + dy,
                node.z + dz,
            )
            neighbor = node_dict.get(neighbor_coordinates)
            if neighbor and not neighbor.occupied:
                neighbors.append(neighbor)
        return neighbors
