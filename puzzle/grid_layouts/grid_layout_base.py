# puzzle/grid_layouts/grid_layout_base.py

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
        grid_step: Optional[float] = None,
        tolerance: Optional[float] = None,
    ) -> list[Node]:
        """
        Add circularly placed nodes on one or more Z-planes.

        Matches original behavior:
        - Always place 'count_even' evenly spaced ring nodes (x/y snapped).
        - Add grid–circle intersections; dedupe those by tolerance
          and withhold any that are closer than 'tolerance' to existing
          circular nodes on the same plane.
        - Always create new circular nodes;

        Returns: list of all circular nodes added (ring + intersections).
        """
        import math

        added_circular: list[Node] = []
        tol = tolerance if tolerance is not None else (grid_step or 0.0)
        tol2 = tol * tol

        def is_close_xy(ax: float, ay: float, bx: float, by: float) -> bool:
            dx = ax - bx
            dy = ay - by
            return (dx * dx + dy * dy) < tol2

        def add_new_circular_node(xf: float, yf: float, zf: float) -> Node:
            # Ring nodes, snapped
            xs, ys, zs = snap(xf), snap(yf), zf
            k = key3(xs, ys, zs)

            # Always create a new circular node
            new_node = Node(xs, ys, zs)
            new_node.grid_type.append(NodeGridType.CIRCULAR.value)
            nodes.append(new_node)

            # Overwrite mapping
            node_dict[k] = new_node

            added_circular.append(new_node)
            return new_node

        # Work per plane
        for z_plane in z_planes:
            # 1) Evenly spaced ring nodes (no tolerance-based dedupe)
            ring_nodes_this_plane: list[Node] = []
            for i in range(count_even):
                angle = 2.0 * math.pi * i / count_even
                x_ring = radius * math.cos(angle)
                y_ring = radius * math.sin(angle)
                ring_node = add_new_circular_node(x_ring, y_ring, z_plane)
                ring_nodes_this_plane.append(ring_node)

            # 2) grid–circle intersections (deduped and withheld)
            candidate_xy: list[tuple[float, float]] = []
            max_steps = int(abs(radius) // grid_step)

            # Generate candidates from vertical and horizontal grid lines
            for step_index in range(max_steps + 1):
                for sign in [1] if step_index == 0 else [1, -1]:
                    # Vertical: x fixed
                    x_val = step_index * grid_step * sign
                    remainder_v = radius * radius - x_val * x_val
                    if remainder_v >= 0:
                        y_raw = math.sqrt(remainder_v)
                        y_opts = [y_raw] if abs(y_raw) < tol else [y_raw, -y_raw]
                        for y_cand in y_opts:
                            candidate_xy.append((x_val, y_cand))

                    # Horizontal: y fixed
                    y_val = step_index * grid_step * sign
                    remainder_h = radius * radius - y_val * y_val
                    if remainder_h >= 0:
                        x_raw = math.sqrt(remainder_h)
                        x_opts = [x_raw] if abs(x_raw) < tol else [x_raw, -x_raw]
                        for x_cand in x_opts:
                            candidate_xy.append((x_cand, y_val))

            # Deduplicate intersection candidates among themselves by tolerance
            unique_candidates: list[tuple[float, float]] = []
            for coord in candidate_xy:
                if any(
                    is_close_xy(coord[0], coord[1], uc[0], uc[1])
                    for uc in unique_candidates
                ):
                    continue
                unique_candidates.append(coord)

            # Build current plane circular set for conflict checks
            plane_circular_now: list[Node] = [
                n
                for n in nodes
                if (n.z == z_plane and NodeGridType.CIRCULAR.value in n.grid_type)
            ]

            # Withhold intersections that conflict with existing circulars on this plane
            for cx, cy in unique_candidates:
                if any(is_close_xy(cx, cy, n.x, n.y) for n in plane_circular_now):
                    continue
                add_new_circular_node(cx, cy, z_plane)

        return added_circular

    def remove_rectangular_nodes_close_to(
        self,
        nodes: list[Node],
        node_dict: Dict[Coordinate, Node],
        reference_nodes: list[Node],
        cutoff_distance: float,
        z_planes: Optional[set[float]] = None,
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
            if z_planes is not None and node.z not in z_planes:
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
