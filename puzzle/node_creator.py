# puzzle/node_creator.py

from abc import ABC, abstractmethod
import math
from typing import Any, Dict, List, Tuple

from config import Config
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
    def create_nodes(self, puzzle: Any) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
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

        x_values: List[float] = [start_pos + i * node_size for i in range(num_cubes_along_axis)]
        y_values: List[float] = x_values
        z_values: List[float] = x_values

        effective_radius_squared: float = effective_radius ** 2

        # Create grid (rectangular) nodes inside the sphere
        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if (x ** 2 + y ** 2 + z ** 2) <= effective_radius_squared:
                        node = Node(x, y, z)
                        nodes.append(node)

        if not nodes:
            raise ValueError("No nodes were created inside the spherical casing.")

        node_dict: Dict[Coordinate, Node] = {(node.x, node.y, node.z): node for node in nodes}

        # Prepare for circular placed nodes along the sphere's circumference
        circular_even_count = Config.Sphere.NUMBER_OF_MOUNTING_POINTS
        circular_diameter = Config.Sphere.SPHERE_DIAMETER - 2 * Config.Sphere.SHELL_THICKNESS - 2 * Config.Puzzle.NODE_SIZE
        circular_radius = circular_diameter / 2.0
        tolerance = node_size * 0.1

        # Evenly distributed circular nodes along the circle in the XY plane (z=0) for mounting waypoints
        for i in range(circular_even_count):
            angle = 2 * math.pi * i / circular_even_count
            x = circular_radius * math.cos(angle)
            y = circular_radius * math.sin(angle)
            z = 0.0

            new_node = Node(x, y, z)
            new_node.grid_type.append("circular")
            nodes.append(new_node)
            node_dict[(new_node.x, new_node.y, new_node.z)] = new_node

        # Nodes at the intersections of the grid and the circle
        grid_step = node_size
        max_steps = int(circular_radius // grid_step)
        tolerance = node_size
        
        # Generate candidate coordinates from both vertical and horizontal grid lines.
        candidate_coords = []
        for k in range(max_steps + 1):
            for sign in ([1] if k == 0 else [1, -1]):
                # Vertical candidate (constant x)
                x_val = k * grid_step * sign
                remainder = circular_radius**2 - x_val**2
                if remainder >= 0:
                    y_val = math.sqrt(remainder)
                    for y_candidate in ([y_val] if abs(y_val) < tolerance else [y_val, -y_val]):
                        candidate_coords.append((x_val, y_candidate, 0.0))
                # Horizontal candidate (constant y)
                y_val = k * grid_step * sign
                remainder = circular_radius**2 - y_val**2
                if remainder >= 0:
                    x_val = math.sqrt(remainder)
                    for x_candidate in ([x_val] if abs(x_val) < tolerance else [x_val, -x_val]):
                        candidate_coords.append((x_candidate, y_val, 0.0))

        # Deduplicate candidates: if two coordinates are closer than tolerance, keep one.
        unique_candidates = []
        for coord in candidate_coords:
            if any(math.sqrt((coord[0] - uc[0])**2 + (coord[1] - uc[1])**2) < tolerance
                   for uc in unique_candidates):
                continue
            unique_candidates.append(coord)

        # Add these unique candidate nodes (but do not add if they conflict with mounting nodes)
        for candidate in unique_candidates:
            # Ensure we don't add a candidate too close to any preexisting mounting node.
            if not any(math.sqrt((candidate[0] - n.x)**2 + (candidate[1] - n.y)**2) < tolerance
                       for n in nodes if n.z == 0 and "circular" in n.grid_type):
                new_node = Node(candidate[0], candidate[1], candidate[2])
                new_node.grid_type.append("circular")
                nodes.append(new_node)
                node_dict[(new_node.x, new_node.y, new_node.z)] = new_node

        # Remove rectangular grid nodes at z == 0 that are closer than node_size to any circular node
        circular_nodes = [node for node in nodes if "circular" in node.grid_type]
        nodes_to_remove = []
        tolerance = node_size * 0.1
        for node in nodes:
            # Only consider nodes at z == 0 that are not circular
            if node.z != 0 or "circular" in node.grid_type:
                continue
            for circ_node in circular_nodes:
                dx = node.x - circ_node.x
                dy = node.y - circ_node.y
                dz = node.z - circ_node.z
                distance = math.sqrt(dx * dx + dy * dy + dz * dz)
                if distance < node_size:
                    nodes_to_remove.append(node)
                    break  # No need to check further circular nodes.
        for node in nodes_to_remove:
            nodes.remove(node)
            key = (node.x, node.y, node.z)
            if key in node_dict:
                del node_dict[key]
        
        # Define the start node by extending the x-axis in the negative direction
        x_axis_nodes: List[Node] = [node for node in nodes if node.y == 0 and node.z == 0]
        min_x: float = min(node.x for node in x_axis_nodes) if x_axis_nodes else 0
        x1: float = min_x - node_size
        x2: float = x1 - node_size
        node1 = Node(x1, 0, 0)
        node2 = Node(x2, 0, 0)
        nodes.extend([node1, node2])
        node_dict[(node1.x, node1.y, node1.z)] = node1
        node_dict[(node2.x, node2.y, node2.z)] = node2
        node2.puzzle_start = True  # furthest in -x becomes start
        start_node: Node = node2
        
        return nodes, node_dict, start_node


    def get_neighbors(self, node: Node, node_dict: Dict[Coordinate, Node], node_size: float) -> List[Tuple[Node, float]]:
        """
        Get neighboring nodes for a given node in the spherical grid.
        
        - Cardinal moves (exactly one axis differs using the exact grid offset) are always allowed.
        - Near-cardinal moves (diff_count == 1) between a circular and a non-circular node are allowed
        if the Euclidean distance is <= (node_size + tolerance).
        - Diagonal moves (exactly two axes differ) are allowed only if both nodes are circular and
        the Euclidean distance is <= (node_size + tolerance).
        
        Each neighbor is returned as a tuple: (neighbor, cost), with non-cardinal moves costing (distance * 2/3).
        """
        neighbors: List[Tuple[Node, float]] = []
        tolerance = node_size * 0.1  # tolerance to decide if coordinates are "the same"
        max_diag_distance = node_size + tolerance

        # Cardinal moves (exactly one axis differs, using exact grid offsets)
        cardinal_offsets: List[Coordinate] = [
            (node_size, 0, 0),
            (-node_size, 0, 0),
            (0, node_size, 0),
            (0, -node_size, 0),
            (0, 0, node_size),
            (0, 0, -node_size),
        ]
        for dx, dy, dz in cardinal_offsets:
            coord: Coordinate = (node.x + dx, node.y + dy, node.z + dz)
            candidate = node_dict.get(coord)
            if candidate and not candidate.occupied:
                neighbors.append((candidate, node_size))
                #print(f"[DEBUG] Cardinal neighbor found at {coord} with cost {node_size}")

        # Examine all nodes for near-cardinal and diagonal connections.
        for candidate in node_dict.values():
            if candidate == node or candidate.occupied:
                continue

            dx = abs(candidate.x - node.x)
            dy = abs(candidate.y - node.y)
            dz = abs(candidate.z - node.z)
            distance = (dx**2 + dy**2 + dz**2) ** 0.5

            # Count how many coordinates differ significantly (beyond tolerance)
            diff_count = sum(1 for d in (dx, dy, dz) if d > tolerance)

            # Near-cardinal move: exactly one axis differs,
            # and allowed only if one node is circular and the other is not.
            if diff_count == 1 and (("circular" in node.grid_type) ^ ("circular" in candidate.grid_type)):
                if distance <= 2 * max_diag_distance:
                    cost = distance
                    neighbors.append((candidate, cost))
                    #print(f"[DEBUG] Near-cardinal neighbor (mixed types) found at ({candidate.x}, {candidate.y}, {candidate.z}) with cost {cost}, distance {distance}")

            # Diagonal move: exactly two axes differ, allowed only if both nodes are circular.
            elif diff_count == 2:
                if "circular" in node.grid_type and "circular" in candidate.grid_type:
                    if distance <= 2 * max_diag_distance:
                        cost = distance
                        neighbors.append((candidate, cost))
                        #print(f"[DEBUG] Diagonal neighbor (both circular) found at ({candidate.x}, {candidate.y}, {candidate.z}) with cost {cost}, distance {distance}")

        #print(f"[DEBUG] Total neighbors found: {len(neighbors)}")
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
