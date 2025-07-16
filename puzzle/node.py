# puzzle/node.py

from enum import Enum
from typing import Optional

from config import PathCurveType, PathProfileType


class NodeGridType(Enum):
    """
    Enumeration representing the different types of node grids.
    """

    RECTANGULAR = "rectangular"
    CIRCULAR = "circular"


class Node:
    """
    Represents a node in the 3D maze grid.
    """

    def __init__(
        self,
        x: float,
        y: float,
        z: float,
        occupied: bool = False,
        overlap_allowed: bool = False,
    ) -> None:
        """
        Initializes a Node instance.

        Parameters:
            x (float): The x-coordinate of the node.
            y (float): The y-coordinate of the node.
            z (float): The z-coordinate of the node.
            occupied (bool, optional): Indicates if the node is occupied or used in the puzzle. Defaults to False.
        """
        self.x: float = x
        self.y: float = y
        self.z: float = z

        self.occupied: bool = occupied  # Indicates if node is used for the puzzle
        self.overlap_allowed: bool = overlap_allowed  # Obstacle overlap
        self.waypoint: bool = False  # Waypoint along the puzzle path
        self.puzzle_start: bool = False  # Start of the puzzle
        self.puzzle_end: bool = False  # End of the puzzle
        self.mounting: bool = False  # Mounting node, connects to mounting bridge

        self.path_profile_type: Optional[PathProfileType] = (
            None  # Type of path profile shape
        )
        self.path_curve_type: Optional[PathCurveType] = None  # Type of path curve
        self.used_in_curve: bool = False  # Indicates if node is used in a curve
        self.curve_id = None  # Uniquely match node with detected curve
        self.segment_start: bool = False  # Indicates the start node of a segment
        self.segment_end: bool = False  # Indicates the end node of a segment

        self.parent: Optional["Node"] = None  # For path reconstruction
        self.g: float = float("inf")  # Cost from start to this node
        self.h: float = 0.0  # Heuristic cost to goal
        self.f: float = float("inf")  # Total cost

        self.grid_type = []  # List of grid types (e.g., "rectangular", "circular")

    def __lt__(self, other):
        return self.f < other.f  # For priority queue (heapq)
