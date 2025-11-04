# puzzle/grid_layouts/grid_layout_ellipsoid.py

import math
from typing import Dict, Tuple

from config import Config
from puzzle.node import Node
from puzzle.utils.geometry import frange

from .grid_layout_base import Casing

Coordinate = Tuple[float, float, float]


class EllipsoidCasing(Casing):
    def __init__(
        self,
        diameter_x: float,
        diameter_y: float,
        diameter_z: float,
        shell_thickness: float,
    ):
        self.node_size = Config.Puzzle.NODE_SIZE
        self.diameter_x = diameter_x
        self.diameter_y = diameter_y
        self.diameter_z = diameter_z
        self.shell_thickness = shell_thickness

        # Inner radii define where the playable volume ends inside the shell.
        self.inner_radius_x = (diameter_x / 2.0) - shell_thickness
        self.inner_radius_y = (diameter_y / 2.0) - shell_thickness
        self.inner_radius_z = (diameter_z / 2.0) - shell_thickness

    def _effective_radii(self) -> tuple[float, float, float]:
        # Shrink the ellipsoid by the cube half diagonal so node cubes fit entirely within it.
        cube_half_diagonal = (self.node_size * math.sqrt(3.0)) / 2.0
        return (
            max(self.inner_radius_x - cube_half_diagonal, 0.0),
            max(self.inner_radius_y - cube_half_diagonal, 0.0),
            max(self.inner_radius_z - cube_half_diagonal, 0.0),
        )

    def contains_point(self, x: float, y: float, z: float) -> bool:
        effective_x, effective_y, effective_z = self._effective_radii()
        if not all(radius > 0.0 for radius in (effective_x, effective_y, effective_z)):
            return False

        # Membership test using the implicit ellipsoid equation with clearance-adjusted radii.
        return (
            (x * x) / (effective_x * effective_x)
            + (y * y) / (effective_y * effective_y)
            + (z * z) / (effective_z * effective_z)
        ) <= 1.0

    def get_mounting_waypoints(self, nodes: list[Node]) -> list[Node]:
        number_of_waypoints = Config.Ellipsoid.NUMBER_OF_MOUNTING_POINTS
        effective_radius_xy = min(self.inner_radius_x, self.inner_radius_y)
        target_radius = max(effective_radius_xy - (self.node_size * 0.5), self.node_size)

        return self.select_circular_waypoints(
            nodes=nodes,
            radius=target_radius,
            z_planes=[0.0],
            count_per_plane=number_of_waypoints,
        )

    def create_nodes(self) -> Tuple[list[Node], Dict[Coordinate, Node], Node]:
        # Sample the bounding box of the ellipsoid using the grid spacing.
        x_values = frange(-self.inner_radius_x, self.inner_radius_x, self.node_size)
        y_values = frange(-self.inner_radius_y, self.inner_radius_y, self.node_size)
        z_values = frange(-self.inner_radius_z, self.inner_radius_z, self.node_size)

        nodes, node_dict = self.generate_rectangular_grid_from_values(
            x_values=x_values,
            y_values=y_values,
            z_values=z_values,
        )

        elliptical_nodes: list[Node] = []
        helper_axis_x = self.inner_radius_x - self.node_size
        helper_axis_y = self.inner_radius_y - self.node_size
        if helper_axis_x > 0.0 and helper_axis_y > 0.0:
            # Add a snapped helper ring so path helpers sit on the ellipsoid equator.
            elliptical_nodes = self.add_elliptical_nodes_on_planes(
                nodes=nodes,
                node_dict=node_dict,
                axis_x=helper_axis_x,
                axis_y=helper_axis_y,
                z_planes=[0.0],
                count_even=Config.Ellipsoid.NUMBER_OF_MOUNTING_POINTS,
                grid_step=Config.Puzzle.NODE_SIZE,
                tolerance=self.node_size,
            )

            # Remove conflicting rectangular points so the helper ring remains clean.
            self.remove_rectangular_nodes_close_to(
                nodes=nodes,
                node_dict=node_dict,
                reference_nodes=elliptical_nodes,
                cutoff_distance=self.node_size,
                z_planes={0.0},
            )

        start_node: Node = self.place_start_node_along_negative_x(
            nodes=nodes,
            node_dict=node_dict,
            node_size=self.node_size,
            prefer_y=0.0,
            prefer_z=0.0,
        )

        return nodes, node_dict, start_node
