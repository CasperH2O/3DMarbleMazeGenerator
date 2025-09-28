# puzzle/cases/cylinder.py

import math
from typing import Any, Dict, List, Tuple

from config import Config
from puzzle.node import Node, NodeGridType
from puzzle.utils.geometry import frange, key3, snap, squared_distance_xyz

from .base import Casing

Coordinate = Tuple[float, float, float]


class CylinderCasing(Casing):
    """
    Vertical cylinder centered at origin.
    """

    def __init__(self, diameter: float, height: float, shell_thickness: float):
        self.diameter = diameter
        self.height = height
        self.shell_thickness = shell_thickness
        self.inner_radius = (diameter / 2) - shell_thickness
        self.half_height = (height / 2) - shell_thickness

    def contains_point(self, x: float, y: float, z: float) -> bool:
        return (x * x + y * y) <= self.inner_radius**2 and (
            -self.half_height <= z <= self.half_height
        )

    def get_mounting_waypoints(self, nodes: List[Node]) -> List[Node]:
        """
        Put N waypoints on the mid-height circle (z=0), evenly spaced.
        """
        n = (
            getattr(Config, "Cylinder", None)
            and Config.Cylinder.NUMBER_OF_MOUNTING_POINTS
            or 8
        )
        r = self.inner_radius - Config.Puzzle.NODE_SIZE
        waypoints: List[Node] = []
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y, z = r * math.cos(a), r * math.sin(a), 0.0
            free = [node for node in nodes if not node.occupied]
            if not free:
                break
            nearest = min(
                free, key=lambda nd: squared_distance_xyz(nd.x, nd.y, nd.z, x, y, z)
            )
            nearest.mounting = True
            nearest.waypoint = True
            waypoints.append(nearest)
        return waypoints

    def create_nodes(
        self, puzzle: Any
    ) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
        s = puzzle.node_size
        nodes: List[Node] = []
        d: Dict[Coordinate, Node] = {}

        # Fill by box grid, then filter by cylinder
        x_vals = frange(-self.inner_radius, self.inner_radius, s)
        y_vals = frange(-self.inner_radius, self.inner_radius, s)
        z_vals = frange(-self.half_height, self.half_height, s)

        r2 = self.inner_radius**2
        for x in x_vals:
            for y in y_vals:
                if x * x + y * y > r2:
                    continue
                for z in z_vals:
                    if self.contains_point(x, y, z):
                        n = Node(x, y, z)
                        nodes.append(n)
                        d[key3(x, y, z)] = n

        if not nodes:
            raise ValueError("No nodes created inside cylinder.")

        # Optional: circular ring at z=0 for smoother turns (same behavior as sphere)
        ring_count = (
            getattr(Config, "Cylinder", None)
            and Config.Cylinder.NUMBER_OF_MOUNTING_POINTS
            or 8
        )
        ring_r = self.inner_radius - Config.Puzzle.NODE_SIZE
        for i in range(ring_count):
            a = 2 * math.pi * i / ring_count
            x, y, z = snap(ring_r * math.cos(a)), snap(ring_r * math.sin(a)), 0.0
            nn = Node(x, y, z)
            nn.grid_type.append(NodeGridType.CIRCULAR.value)
            nodes.append(nn)
            d[key3(nn.x, nn.y, nn.z)] = nn

        # Start node: extend -x from minimal x on z≈0,y≈0
        axis_nodes = [n for n in nodes if abs(n.y) < 1e-3 and abs(n.z) < 1e-3]
        min_x = min(n.x for n in axis_nodes) if axis_nodes else min(n.x for n in nodes)
        x1, x2 = snap(min_x - s), snap(min_x - 2 * s)
        n1, n2 = Node(x1, 0, 0), Node(x2, 0, 0)
        nodes.extend([n1, n2])
        d[key3(n1.x, n1.y, n1.z)] = n1
        d[key3(n2.x, n2.y, n2.z)] = n2
        n2.puzzle_start = True
        return nodes, d, n2
