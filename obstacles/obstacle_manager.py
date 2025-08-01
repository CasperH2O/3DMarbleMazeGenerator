# obstacles/obstacle_manager.py

import random
from typing import Dict, List, Optional

import numpy as np
from build123d import Axis, Location, Rotation, Vector

from config import Config
from obstacles.obstacle import Obstacle

# Use the registry
from obstacles.obstacle_registry import get_available_obstacles, get_obstacle_class
from puzzle.node import Node


class ObstacleManager:
    """
    Manages the selection, placement, and node occupation of obstacles.
    """

    def __init__(self, nodes: List[Node]) -> None:
        """
        Initializes the obstacle manager.

        Parameters:
            puzzle nodes: puzzle nodes, for placement of the nodes.
        """

        """
        Design and implementation thoughts:

        - Obstacles are placed in the casing
        - Obstacles are placed in random location (translation) and orientation (rotation) based on seed
        - Obstacles are checked for collision with other obstacles and the casing

        - There can be multiple obstacles in the puzzle
        - Different types of obstacles can be created, no more then 3 obstacles of the same type
        - Space between obstacles is important so that paths can be made between them, for this we can use nodes marked with in between
        - Obstacles have a start and end node, segment paths have to be created between them
        - Somehow the space obstacles use need to be defined and matched with the node grid ie the nodes they occupy

        """
        self.placed_obstacles: List[Obstacle] = []
        self.seed = Config.Puzzle.SEED
        random.seed(self.seed)
        np.random.seed(self.seed)

        if Config.Puzzle.OBSTACLES:
            self.place_obstacles()

    def place_obstacles(
        self,
        num_obstacles: int,
        allowed_types: Optional[List[str]] = None,
        max_attempts: int = 50,
    ):
        """
        Selects and places obstacles randomly within the puzzle casing.
        Obstacles are placed, checked if they can be placed (within puzzle grid and no collision)
        Obstacles can be translated (in node size increments) and rotated (0,90,180,270 degrees around XYZ axis)
        These translations and rotations are random based on a seed for reproducibility
        Placement of obstacles can be limited to their own min max xyz node placements and the min max xyz of the node grid of the puzzle

        Parameters:
            num_obstacles (int): The desired number of obstacles.
            max_attempts (int): Max attempts to place each obstacle before giving up.
        """

    def _is_placement_valid(self, obstacle: Obstacle) -> bool:
        """Checks if the proposed placement is valid (inside casing, no collisions)."""
        # --- Check 1: Inside Casing ---
        # Check that all obstacles nodes (overlap and occupied) have a
        # respective node within the node grid of the casing, this is to check if it can be placed

        # --- Check 2: Collision with other placed obstacles ---
        # overlap nodes may overlap with other obstacles
        # occupied nodes may not overlap with other placed obstacles

        # If all checks pass
        return True

    def _occupy_nodes_for_obstacle(self, obstacle: Obstacle):
        """Marks grid nodes as occupied based on the obstacle's placement."""
        # Mark the puzzle nodes that the obstacle occupies with it's occupied nodes (not with the overlap nodes) as occupied

    def _assign_entry_exit_nodes(self, obstacle: Obstacle):
        """Finds the closest grid nodes to the obstacle's entry/exit points and marks them."""
        entry_exit_coords = obstacle.get_placed_entry_exit_coords()
        if not entry_exit_coords:
            return

        entry_coord, exit_coord = entry_exit_coords
        node_dict = self.puzzle.node_dict

        entry_node = self._find_closest_node(entry_coord, node_dict)
        exit_node = self._find_closest_node(exit_coord, node_dict)

        if entry_node:
            obstacle.entry_node = entry_node
            entry_node.waypoint = True  # Must be visited
            entry_node.occupied = True  # Part of the obstacle path
            entry_node.obstacle_entry = obstacle  # Add reference
            print(
                f"Assigned entry node {entry_node.x, entry_node.y, entry_node.z} for {obstacle.name}"
            )

        if exit_node and exit_node != entry_node:
            obstacle.exit_node = exit_node
            exit_node.waypoint = True  # Must be visited
            exit_node.occupied = True  # Part of the obstacle path
            exit_node.obstacle_exit = obstacle  # Add reference
            print(
                f"Assigned exit node {exit_node.x, exit_node.y, exit_node.z} for {obstacle.name}"
            )
        elif exit_node == entry_node:
            print(f"Warning: Entry and Exit nodes are the same for {obstacle.name}")

    def _find_closest_node(
        self, target_coord: Vector, node_dict: Dict[Vector, Node]
    ) -> Optional[Node]:
        """Finds the node in the dictionary closest to the target coordinate."""
        min_dist_sq = float("inf")
        closest_node = None
        tx, ty, tz = target_coord

        # Optimization: Only check nodes within a bounding box around the target?
        search_radius = self.puzzle.node_size * 1.5

        for node in node_dict.values():
            # Quick check if node is roughly nearby
            if (
                abs(node.x - tx) > search_radius
                or abs(node.y - ty) > search_radius
                or abs(node.z - tz) > search_radius
            ):
                continue

            dist_sq = (node.x - tx) ** 2 + (node.y - ty) ** 2 + (node.z - tz) ** 2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_node = node

        # Check if the closest node is within a reasonable distance threshold
        if (
            closest_node and min_dist_sq <= (self.puzzle.node_size * 0.75) ** 2
        ):  # Threshold: e.g., 3/4 of node size
            return closest_node
        else:
            # print(f"Warning: No node found close enough to target coord {target_coord}. Closest dist: {min_dist_sq**0.5}")
            return None  # No node found within threshold
