# obstacles/obstacle_manager.py

import random
from typing import Dict, List, Optional

import numpy as np
from build123d import Axis, Box, Location, Rotation, Vector

from config import Config
from obstacles.obstacle import Obstacle

# Use the registry
from obstacles.obstacle_registry import get_available_obstacles, get_obstacle_class
from puzzle.node import Node
from puzzle.puzzle import Puzzle


class ObstacleManager:
    """
    Manages the selection, placement, and node occupation of obstacles.
    """

    def __init__(self, puzzle: Puzzle) -> None:
        """
        Initializes the obstacle manager.

        Parameters:
            puzzle: The main Puzzle instance.
        """

        """
        Design and implementation thoughts:

        - Obstacles are placed in the casing
        - Obstacles are placed in random location (translation) and orientation (rotation) based on seed
        - Obstacles are checked for collision with other obstacles and the casing

        - There can be multiple obstacles in the puzzle
        - Different types of obstacles can be created, no more then 3 obstacles of the same type
        - Space between obstacles is important so that paths can be made between them
        - Obstacles have a start and end node, segment paths have to be created between them
        - Somehow the space obstacles use need to be defined and matched with the node grid ie the nodes they occupy

        - A software architecture needs to be determined for the obstacles, perhaps a registry or inheritance?
        - Each obstacle should have it's own file and class
        - It's expected to have catalog of obstacles in the library, assume up to 200 obstacles

        """
        self.puzzle = puzzle
        self.placed_obstacles: List[Obstacle] = []
        self.seed = Config.Puzzle.SEED
        random.seed(self.seed)
        np.random.seed(self.seed)

    def place_obstacles(
        self,
        num_obstacles: int,
        allowed_types: Optional[List[str]] = None,
        max_attempts: int = 50,
    ):
        """
        Selects and places obstacles randomly within the puzzle casing.

        Parameters:
            num_obstacles (int): The desired number of obstacles.
            allowed_types (Optional[List[str]]): Specific obstacle names to use. If None, uses all registered.
            max_attempts (int): Max attempts to place each obstacle before giving up.
        """
        if not allowed_types:
            available_obstacle_names = get_available_obstacles()
        else:
            available_obstacle_names = [
                name for name in allowed_types if name in get_available_obstacles()
            ]

        if not available_obstacle_names:
            print("Warning: No available or allowed obstacle types found.")
            return

        print(
            f"Attempting to place {num_obstacles} obstacles from types: {available_obstacle_names}"
        )

        for i in range(num_obstacles):
            obstacle_placed = False
            for attempt in range(max_attempts):
                # 1. Select Obstacle Type
                obstacle_name = random.choice(available_obstacle_names)
                ObstacleClass = get_obstacle_class(obstacle_name)
                obstacle = ObstacleClass()

                # 2. Generate Random Placement (Location)
                #    Needs to be within the *inner* bounds of the casing
                #    This depends heavily on casing type (Sphere vs Box)
                #    Let's simplify: Assume origin (0,0,0) for now, add random rotation
                #    A proper implementation needs random point generation *inside* the casing volume.
                random_pos = Vector(
                    0, 0, 0
                )  # Placeholder - NEEDS BETTER RANDOM POINT IN VOLUME
                random_rot = Rotation(
                    Axis.random(), random.uniform(0, 360)
                )  # Random axis, random angle
                placement_location = Location(random_pos, random_rot)
                obstacle.set_placement(placement_location)

                # 3. Check Validity
                if self._is_placement_valid(obstacle):
                    # 4. If Valid: Add, Occupy Nodes, Assign Entry/Exit
                    self.placed_obstacles.append(obstacle)
                    print(
                        f"Placed obstacle {i + 1}: {obstacle.name} at {obstacle.location.position}, rot {obstacle.location.orientation}"
                    )

                    # Mark nodes as occupied
                    self._occupy_nodes_for_obstacle(obstacle)

                    # Find and assign entry/exit nodes in the main grid
                    self._assign_entry_exit_nodes(obstacle)

                    obstacle_placed = True
                    break  # Move to next obstacle

            if not obstacle_placed:
                print(
                    f"Warning: Failed to place obstacle {i + 1} after {max_attempts} attempts."
                )

    def _is_placement_valid(self, obstacle: Obstacle) -> bool:
        """Checks if the proposed placement is valid (inside casing, no collisions)."""
        # --- Check 1: Inside Casing ---
        # Use the obstacle's placed bounding box for a quick check
        placed_part = obstacle.get_placed_part()
        if placed_part is None:
            return False  # Cannot get geometry

        bb = placed_part.bounding_box()
        # Check if all corners of the BB are inside the casing's inner volume
        # This requires a method on the Casing object.
        if not self.puzzle.casing.contains_bounding_box(
            bb
        ):  # Assumes Casing has this method
            # print(f"Placement check failed: {obstacle.name} bounding box outside casing.")
            return False

        # --- Check 2: Collision with other placed obstacles ---
        # Again, use bounding boxes for a faster check
        # A more accurate check would use Part intersection (slower)
        for other in self.placed_obstacles:
            other_part = other.get_placed_part()
            if other_part is None:
                continue
            other_bb = other_part.bounding_box()
            if bb.intersects(other_bb):  # Assumes BoundingBox has intersects method
                # print(f"Placement check failed: {obstacle.name} intersects with {other.name}.")
                # Optional: Perform precise Part intersection check here if BBs intersect
                # if placed_part.intersect(other_part).solids: return False
                return False

        # --- Check 3: Minimum distance (optional) ---
        # Ensure minimum space between obstacles
        min_dist = self.puzzle.node_size * 2  # Example minimum distance
        for other in self.placed_obstacles:
            other_part = other.get_placed_part()
            if other_part is None:
                continue
            # distance = placed_part.distance(other_part) # Might be slow
            # Approximate distance between bounding box centers
            dist_sq = (bb.center() - other_part.bounding_box().center()).length_squared
            if dist_sq < min_dist**2:
                # print(f"Placement check failed: {obstacle.name} too close to {other.name}.")
                return False

        # If all checks pass
        return True

    def _occupy_nodes_for_obstacle(self, obstacle: Obstacle):
        """Marks grid nodes as occupied based on the obstacle's placement."""
        placed_coords = obstacle.get_placed_occupied_coords(self.puzzle.node_size)
        if not placed_coords:
            return

        count = 0
        node_dict = self.puzzle.node_dict
        for coord in placed_coords:
            # Find the *closest* actual node in the grid dictionary
            # This snaps the continuous occupied coords to the discrete grid
            closest_node = self._find_closest_node(coord, node_dict)
            if closest_node and not closest_node.occupied:
                closest_node.occupied = True
                # Optionally add obstacle reference: closest_node.occupied_by = obstacle
                count += 1
        print(f"Occupied {count} nodes for {obstacle.name}")

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

    # --- Helper methods needed by _is_placement_valid ---
    # These should ideally be implemented in the Casing classes

    # Example placeholder for Casing method:
    def _casing_contains_bounding_box(self, bb: Box) -> bool:
        # Placeholder - actual implementation depends on casing shape
        # For a sphere: Check if all 8 corners of bb are within inner_radius
        # For a box: Check if bb min/max are within casing inner min/max
        print("Warning: _casing_contains_bounding_box not fully implemented.")
        return True  # Assume true for now

    # Example placeholder for BoundingBox method:
    def _bounding_box_intersects(self, bb1: Box, bb2: Box) -> bool:
        # Placeholder - Build123D's BoundingBox might not have this directly.
        # Standard AABB intersection test:
        return (
            (bb1.min.X < bb2.max.X and bb1.max.X > bb2.min.X)
            and (bb1.min.Y < bb2.max.Y and bb1.max.Y > bb2.min.Y)
            and (bb1.min.Z < bb2.max.Z and bb1.max.Z > bb2.min.Z)
        )


# Add the required methods to your Casing classes (SphereCasing, BoxCasing)
# class SphereCasing(Casing):
#     ...
#     def contains_bounding_box(self, bb: Box) -> bool:
#         corners = [Vector(x, y, z) for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y) for z in (bb.min.Z, bb.max.Z)]
#         inner_radius_sq = self.inner_radius**2
#         return all(corner.length_squared <= inner_radius_sq for corner in corners)
#
# class BoxCasing(Casing):
#     ...
#     def contains_bounding_box(self, bb: Box) -> bool:
#         inner_min_x = -self.half_width + self.panel_thickness
#         inner_max_x = self.half_width - self.panel_thickness
#         # ... define inner_min/max for Y and Z ...
#         return (bb.min.X >= inner_min_x and bb.max.X <= inner_max_x and
#                 bb.min.Y >= inner_min_y and bb.max.Y <= inner_max_y and
#                 bb.min.Z >= inner_min_z and bb.max.Z <= inner_max_z)
