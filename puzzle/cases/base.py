# puzzle/cases/base.py

import math
from abc import ABC, abstractmethod
from typing import Dict, Iterable, Optional, Tuple

from puzzle.node import Node, NodeGridType
from puzzle.utils.geometry import key3, snap, squared_distance_xyz

Coordinate = Tuple[float, float, float]


class Casing(ABC):
    """Abstract base for a casing shape."""

    @abstractmethod
    def contains_point(self, x: float, y: float, z: float) -> bool:
        pass

    @abstractmethod
    def get_mounting_waypoints(self, nodes: list[Node]) -> list[Node]:
        """Mark & return mounting waypoint nodes inside 'nodes'."""
        pass

    @abstractmethod
    def create_nodes(self) -> Tuple[list[Node], Dict[Coordinate, Node], Node]:
        """Return (nodes, node_dict, start_node) for this casing."""
        pass

    def generate_rectangular_grid_from_values(
        self,
        x_values: Iterable[float],
        y_values: Iterable[float],
        z_values: Iterable[float],
    ) -> Tuple[list[Node], Dict[Coordinate, Node]]:
        """
        Generate a rectangular grid using explicit value lists, filtering with
        this casing's contains_point().
        """
        nodes: list[Node] = []
        node_dict: Dict[Coordinate, Node] = {}

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    if self.contains_point(x, y, z):
                        node = Node(x, y, z)
                        nodes.append(node)
                        node_dict[key3(x, y, z)] = node

        return nodes, node_dict

    def add_circular_nodes_on_planes(
        self,
        nodes: list[Node],
        node_dict: Dict[Coordinate, Node],
        radius: float,
        z_planes: list[float],
        count_even: int,
        grid_step: float,
        tolerance: Optional[float] = None,
    ) -> list[Node]:
        """
        Add circularly placed nodes on one or more Z-planes.

        - Adds 'count_even' evenly spaced nodes on each plane at 'radius'.
        - Always adds nodes where the rectangular grid lines (spacing 'grid_step')
          intersect the circle on that plane.
        - Marks added nodes with NodeGridType.CIRCULAR and dedupes via node_dict.
        """

        # TODO remove near duplicates like original code

        added_nodes: list[Node] = []
        tolerance_value = grid_step if tolerance is None else tolerance

        def maybe_add_node(x_value: float, y_value: float, z_value: float) -> None:
            node_key = key3(x_value, y_value, z_value)
            if node_key not in node_dict:
                new_node = Node(x_value, y_value, z_value)
                new_node.grid_type.append(NodeGridType.CIRCULAR.value)
                nodes.append(new_node)
                node_dict[node_key] = new_node
                added_nodes.append(new_node)

        # Evenly spaced ring nodes and grid-circle intersections
        for z_value in z_planes:
            for angle_index in range(count_even):
                angle = 2.0 * math.pi * angle_index / count_even
                x_value = snap(radius * math.cos(angle))
                y_value = snap(radius * math.sin(angle))
                maybe_add_node(x_value, y_value, z_value)

            max_steps = int(abs(radius) // grid_step)
            for step_index in range(max_steps + 1):
                for sign in [1] if step_index == 0 else [1, -1]:
                    # Vertical candidates (x fixed)
                    x_fixed = snap(step_index * grid_step * sign)
                    remainder_y = radius * radius - x_fixed * x_fixed
                    if remainder_y >= 0:
                        y_raw = math.sqrt(remainder_y)
                        y_candidates = (
                            [y_raw] if abs(y_raw) < tolerance_value else [y_raw, -y_raw]
                        )
                        for y_candidate in y_candidates:
                            maybe_add_node(snap(x_fixed), snap(y_candidate), z_value)

                    # Horizontal candidates (y fixed)
                    y_fixed = snap(step_index * grid_step * sign)
                    remainder_x = radius * radius - y_fixed * y_fixed
                    if remainder_x >= 0:
                        x_raw = math.sqrt(remainder_x)
                        x_candidates = (
                            [x_raw] if abs(x_raw) < tolerance_value else [x_raw, -x_raw]
                        )
                        for x_candidate in x_candidates:
                            maybe_add_node(snap(x_candidate), snap(y_fixed), z_value)

        return added_nodes

    def remove_rectangular_nodes_close_to(
        self,
        nodes: list[Node],
        node_dict: Dict[Coordinate, Node],
        reference_nodes: list[Node],
        cutoff_distance: float,
        only_on_planes: Optional[set[float]] = None,
    ) -> None:
        """
        Remove non-circular nodes that lie within 'cutoff_distance' of any
        'reference_nodes'. Optionally limited to nodes on specific z planes.
        """
        to_remove: list[Node] = []
        cutoff_squared = cutoff_distance * cutoff_distance

        for node in nodes:
            if NodeGridType.CIRCULAR.value in node.grid_type:
                continue
            if only_on_planes is not None and node.z not in only_on_planes:
                continue

            for ref_node in reference_nodes:
                dx = node.x - ref_node.x
                dy = node.y - ref_node.y
                dz = node.z - ref_node.z
                if dx * dx + dy * dy + dz * dz < cutoff_squared:
                    to_remove.append(node)
                    break

        if not to_remove:
            return

        for node in to_remove:
            nodes.remove(node)
            node_key = key3(node.x, node.y, node.z)
            if node_dict.get(node_key) is node:
                del node_dict[node_key]

    def place_start_node_along_negative_x(
        self,
        nodes: list[Node],
        node_dict: Dict[Coordinate, Node],
        node_size: float,
        prefer_y: float = 0.0,
        prefer_z: float = 0.0,
        epsilon: float = 1e-3,
    ) -> Node:
        """
        Place two extra nodes along -X from the minimal X on the preferred axis
        line (|y-prefer_y|<eps and |z-prefer_z|<eps). Marks the furthest as
        puzzle_start and returns it.
        """
        axis_nodes = [
            node
            for node in nodes
            if abs(node.y - prefer_y) < epsilon and abs(node.z - prefer_z) < epsilon
        ]
        if axis_nodes:
            min_x_value = min(node.x for node in axis_nodes)
            use_y_value = prefer_y
            use_z_value = prefer_z
        else:
            # Fallback: use absolute minimal X among all nodes
            anchor_node = min(nodes, key=lambda node: node.x)
            min_x_value, use_y_value, use_z_value = (
                anchor_node.x,
                anchor_node.y,
                anchor_node.z,
            )

        x1 = snap(min_x_value - node_size)
        x2 = snap(x1 - node_size)
        node1 = Node(x1, use_y_value, use_z_value)
        node2 = Node(x2, use_y_value, use_z_value)

        nodes.extend([node1, node2])
        node_dict[key3(node1.x, node1.y, node1.z)] = node1
        node_dict[key3(node2.x, node2.y, node2.z)] = node2
        node2.puzzle_start = True

        return node2

    def select_circular_waypoints(
        self,
        nodes: list[Node],
        radius: float,
        z_planes: list[float],
        count_per_plane: int,
    ) -> list[Node]:
        """
        Circular waypoint selector:
        - For each z in z_planes, build 'count_per_plane' targets around a circle.
        - For each target, select the nearest free node (not occupied and not
          already chosen), mark it as mounting+waypoint, and return the set.
        """
        selected: list[Node] = []
        for z_value in z_planes:
            for angle_index in range(count_per_plane):
                angle = 2.0 * math.pi * angle_index / count_per_plane
                target_x = radius * math.cos(angle)
                target_y = radius * math.sin(angle)

                candidates = [
                    candidate_node
                    for candidate_node in nodes
                    if not candidate_node.occupied and candidate_node not in selected
                ]
                if not candidates:
                    continue

                nearest = min(
                    candidates,
                    key=lambda nd: squared_distance_xyz(
                        nd.x, nd.y, nd.z, target_x, target_y, z_value
                    ),
                )
                nearest.mounting = True
                nearest.waypoint = True
                selected.append(nearest)

        return selected
