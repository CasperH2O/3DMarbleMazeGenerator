# puzzle/cases/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from puzzle.node import Node

Coordinate = Tuple[float, float, float]


class Casing(ABC):
    """Abstract base for a casing shape."""

    @abstractmethod
    def contains_point(self, x: float, y: float, z: float) -> bool:
        pass

    @abstractmethod
    def get_mounting_waypoints(self, nodes: List[Node]) -> List[Node]:
        """Mark & return mounting waypoint nodes inside 'nodes'."""
        pass

    @abstractmethod
    def create_nodes(
        self, puzzle: Any
    ) -> Tuple[List[Node], Dict[Coordinate, Node], Node]:
        """Return (nodes, node_dict, start_node) for this casing."""
        pass
