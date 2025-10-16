# puzzle/cases/cylinder.py

import math
from typing import Dict, Tuple

from config import Config
from puzzle.node import Node, NodeGridType
from puzzle.utils.geometry import frange, squared_distance_xyz

from .base import Casing

Coordinate = Tuple[float, float, float]


class CylinderCasing(Casing):
    """
    Vertical cylinder centered at origin.
    """

    def __init__(self, diameter: float, height: float, shell_thickness: float):
        self.node_size = Config.Puzzle.NODE_SIZE
        self.diameter = diameter
        self.height = height
        self.shell_thickness = shell_thickness

        self.inner_radius = (diameter / 2) - shell_thickness
        self.inner_half_height = (height / 2) - shell_thickness
        self.pillar_radius = self.inner_radius - (1.5 * self.node_size)

    def contains_point(self, x: float, y: float, z: float) -> bool:
        square_half_diagonal = self.node_size / math.sqrt(2)
        effective_radius = self.inner_radius - square_half_diagonal

        return (x * x + y * y) <= effective_radius**2 and (
            -self.inner_half_height <= z <= self.inner_half_height
        )

    def get_mounting_waypoints(self, nodes: list[Node]) -> list[Node]:
        """
        Generic circular waypoint selection.
        For a cylinder we can choose multiple planes; by default: bottom, mid, top.
        """

        count = Config.Cylinder.NUMBER_OF_MOUNTING_POINTS
        target_radius = self.inner_radius + self.node_size
        z_planes = [-self.inner_half_height, 0.0, self.inner_half_height]

        return self.select_circular_waypoints(
            nodes=nodes,
            radius=target_radius,
            z_planes=z_planes,
            count_per_plane=count,
        )

    def create_nodes(self) -> Tuple[list[Node], Dict[Coordinate, Node], Node]:
        # Symmetric value lists
        x_values = frange(-self.inner_radius, self.inner_radius, self.node_size)
        y_values = frange(-self.inner_radius, self.inner_radius, self.node_size)
        z_values = frange(
            -self.inner_half_height, self.inner_half_height, self.node_size
        )

        # Fill by rectangular grid and filter by contains point shape
        nodes, node_dict = self.generate_rectangular_grid_from_values(
            x_values=x_values, y_values=y_values, z_values=z_values
        )

        # Circular rings, multiple planes
        mounting_points_count = Config.Cylinder.NUMBER_OF_MOUNTING_POINTS
        ring_radius = self.inner_radius - self.node_size

        added_circular = self.add_circular_nodes_on_planes(
            nodes=nodes,
            node_dict=node_dict,
            radius=ring_radius,
            z_planes=z_values,
            count_even=mounting_points_count,
            grid_step=self.node_size,
        )

        # Remove rectangular nodes too close to the circular nodes on all z planes
        self.remove_rectangular_nodes_close_to(
            nodes=nodes,
            node_dict=node_dict,
            reference_nodes=added_circular,
            cutoff_distance=self.node_size,
            z_planes=z_values,
        )

        self.mark_pillar_nodes_as_occupied(
            nodes=nodes,
            z_levels=z_values,
            directions_count=mounting_points_count,
        )

        # Start node, extend along -X on the center line
        start_node: Node = self.place_start_node_along_negative_x(
            nodes=nodes,
            node_dict=node_dict,
            node_size=self.node_size,
            prefer_y=0.0,
            prefer_z=0.0,
        )

        return nodes, node_dict, start_node

    def mark_pillar_nodes_as_occupied(
        self,
        nodes: list[Node],
        z_levels: list[float],
        directions_count: int,
    ) -> list[Node]:
        """
        Finds nodes near waypoints and mark as occupied to
        allow space for placing pillars during 3D design.

        Returns the list of nodes marked as occupied.

        TODO, uneven numbers, the 3D placement of the pillars and the
        selected node are not in the same location. Circular vs rectangular grid.
        Could consider two rows of circular nodes or always using even numbers for
        mounting waypoints.
        """

        if directions_count <= 0 or not z_levels:
            return []

        # Pick the reference Z plane
        ref_z = 0.0
        reference_plane_nodes = [
            candidate
            for candidate in nodes
            if (NodeGridType.CIRCULAR.value not in candidate.grid_type)
            and (candidate.z == ref_z)
        ]
        if not reference_plane_nodes:
            return []

        selected_xy: set[tuple[float, float]] = set()
        chosen_xy_per_direction: list[tuple[float, float]] = []

        # For each direction, choose nearest rectangular node on the reference plane
        for angle_index in range(directions_count):
            angle = 2.0 * math.pi * angle_index / directions_count
            target_x = self.pillar_radius * math.cos(angle)
            target_y = self.pillar_radius * math.sin(angle)

            # Only consider XY we haven't taken yet
            candidates = (
                candidate_node
                for candidate_node in reference_plane_nodes
                if (candidate_node.x, candidate_node.y) not in selected_xy
            )

            # Use 2D squared distance; z is constant on the plane
            nearest = min(
                candidates,
                key=lambda nd: (nd.x - target_x) ** 2 + (nd.y - target_y) ** 2,
            )

            selected_xy.add((nearest.x, nearest.y))
            chosen_xy_per_direction.append((nearest.x, nearest.y))

        if not chosen_xy_per_direction:
            return []

        chosen_xy_set = set(chosen_xy_per_direction)
        z_set = set(z_levels)

        # Propagate the same (x, y) to all Z planes and mark nodes as occupied
        marked: list[Node] = []
        for node in nodes:
            if NodeGridType.CIRCULAR.value in node.grid_type:
                continue
            if node.z in z_set and (node.x, node.y) in chosen_xy_set:
                node.occupied = True
                marked.append(node)

        return marked
