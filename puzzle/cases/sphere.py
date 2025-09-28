# puzzle/cases/sphere.py

import math
from typing import Any, Dict, List, Tuple

from config import Config
from puzzle.node import Node, NodeGridType
from puzzle.utils.geometry import key3, snap, squared_distance_xyz

from .base import Casing

Coordinate = Tuple[float, float, float]


class SphereCasing(Casing):
    def __init__(self, diameter: float, shell_thickness: float):
        self.diameter = diameter
        self.shell_thickness = shell_thickness
        self.inner_radius = (diameter / 2) - shell_thickness

    def contains_point(self, x: float, y: float, z: float) -> bool:
        return x * x + y * y + z * z <= self.inner_radius**2

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
                candidates,
                key=lambda nd: squared_distance_xyz(nd.x, nd.y, nd.z, x, y, 0.0),
            )
            nearest_node.mounting = True
            nearest_node.waypoint = True  # Include in pathfinding
            mounting_nodes.append(nearest_node)

        return mounting_nodes

    def create_nodes(
        self, puzzle: Any
    ) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
        """
        Create nodes for a spherical grid based on the provided puzzle configuration.
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

        effective_radius_squared: float = effective_radius**2

        # Create grid (rectangular) nodes inside the sphere
        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if (x**2 + y**2 + z**2) <= effective_radius_squared:
                        node = Node(x, y, z)
                        nodes.append(node)

        if not nodes:
            raise ValueError("No nodes were created inside the spherical casing.")

        node_dict: Dict[Coordinate, Node] = {
            key3(node.x, node.y, node.z): node for node in nodes
        }

        # Prepare for circular placed nodes along the sphere's circumference
        circular_even_count = Config.Sphere.NUMBER_OF_MOUNTING_POINTS
        circular_diameter = (
            Config.Sphere.SPHERE_DIAMETER
            - 2 * Config.Sphere.SHELL_THICKNESS
            - 2 * Config.Puzzle.NODE_SIZE
        )
        circular_radius = circular_diameter / 2.0
        tolerance = node_size * 0.1

        # Evenly distributed circular nodes along the circle in the XY plane (z=0) for mounting waypoints
        for i in range(circular_even_count):
            angle = 2 * math.pi * i / circular_even_count
            x = snap(circular_radius * math.cos(angle))
            y = snap(circular_radius * math.sin(angle))
            z = 0.0

            new_node = Node(x, y, z)
            new_node.grid_type.append(NodeGridType.CIRCULAR.value)
            nodes.append(new_node)
            node_dict[key3(new_node.x, new_node.y, new_node.z)] = new_node

        # Nodes at the intersections of the grid and the circle
        grid_step = node_size
        max_steps = int(circular_radius // grid_step)
        tolerance = node_size

        # Generate candidate coordinates from both vertical and horizontal grid lines.
        candidate_coords = []
        for k in range(max_steps + 1):
            for sign in [1] if k == 0 else [1, -1]:
                # Vertical candidate (constant x)
                x_val = k * grid_step * sign
                remainder = circular_radius**2 - x_val**2
                if remainder >= 0:
                    y_val = math.sqrt(remainder)
                    for y_candidate in (
                        [y_val] if abs(y_val) < tolerance else [y_val, -y_val]
                    ):
                        candidate_coords.append((x_val, y_candidate, 0.0))
                # Horizontal candidate (constant y)
                y_val = k * grid_step * sign
                remainder = circular_radius**2 - y_val**2
                if remainder >= 0:
                    x_val = math.sqrt(remainder)
                    for x_candidate in (
                        [x_val] if abs(x_val) < tolerance else [x_val, -x_val]
                    ):
                        candidate_coords.append((x_candidate, y_val, 0.0))

        # Deduplicate candidates: if two coordinates are closer than tolerance, keep one.
        unique_candidates = []
        for coord in candidate_coords:
            if any(
                math.sqrt((coord[0] - uc[0]) ** 2 + (coord[1] - uc[1]) ** 2) < tolerance
                for uc in unique_candidates
            ):
                continue
            unique_candidates.append(coord)

        # Add these unique candidate nodes (but do not add if they conflict with mounting nodes)
        for candidate in unique_candidates:
            # Ensure we don't add a candidate too close to any preexisting mounting node.
            if not any(
                math.sqrt((candidate[0] - n.x) ** 2 + (candidate[1] - n.y) ** 2)
                < tolerance
                for n in nodes
                if n.z == 0 and NodeGridType.CIRCULAR.value in n.grid_type
            ):
                new_node = Node(candidate[0], candidate[1], candidate[2])
                new_node.grid_type.append(NodeGridType.CIRCULAR.value)
                nodes.append(new_node)
                node_dict[key3(new_node.x, new_node.y, new_node.z)] = new_node

        # Remove rectangular grid nodes at z == 0 that are closer than node_size to any circular node
        circular_nodes = [
            node for node in nodes if NodeGridType.CIRCULAR.value in node.grid_type
        ]
        nodes_to_remove = []
        for node in nodes:
            # Only consider nodes at z == 0 that are not circular
            if node.z != 0 or NodeGridType.CIRCULAR.value in node.grid_type:
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
            key = key3(node.x, node.y, node.z)
            if node_dict.get(key) is node:
                del node_dict[key]

        # Define the start node by extending the x-axis in the negative direction
        x_axis_nodes: List[Node] = [
            node for node in nodes if abs(node.y) < 1e-3 and node.z == 0
        ]
        min_x: float = min(node.x for node in x_axis_nodes) if x_axis_nodes else 0
        x1 = snap(min_x - node_size)
        x2 = snap(x1 - node_size)
        node1 = Node(x1, 0, 0)
        node2 = Node(x2, 0, 0)
        nodes.extend([node1, node2])
        node_dict[key3(node1.x, node1.y, node1.z)] = node1
        node_dict[key3(node2.x, node2.y, node2.z)] = node2
        node2.puzzle_start = True  # furthest in -x becomes start
        start_node: Node = node2

        return nodes, node_dict, start_node
