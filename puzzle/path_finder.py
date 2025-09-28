# puzzle/path_finder.py

import heapq
from typing import Any, List, Optional, Set, Tuple

from puzzle.node import Node, NodeGridType
from puzzle.utils.geometry import euclidean_distance, key3, manhattan_distance

Coordinate = Tuple[float, float, float]


class AStarPathFinder:
    """
    Finds paths between nodes in a puzzle grid using the A* algorithm.
    Includes logic to connect a series of waypoints, aiming for an even
    distribution between 'mounting' and 'non-mounting' types, while ensuring
    all mounting waypoints are visited. Also provides neighbor generation.
    """

    def get_neighbors(
        self,
        puzzle: Any,
        node: Node,
    ) -> List[Tuple[Node, float]]:
        """
        Get neighboring nodes for a given node in the grid.

        - Cardinal moves (exactly one axis differs using the exact grid offset) are always allowed.
        - Near-cardinal moves (diff_count == 1) between a circular and a non-circular node are allowed within a certain range
        - Moves between two circular nodes, closest two on the same plane
        - Circular node cross-plane links: connect to closest circular node on the plane one step above and one step below (z ± node_size)

        Each neighbor is returned as a tuple: (neighbor, cost), cost being the distance
        """
        node_dict = puzzle.node_dict
        node_size = puzzle.node_size
        neighbors: List[Tuple[Node, float]] = []
        tolerance = node_size * 0.1  # tolerance to decide if coordinates are "the same"

        # Cardinal moves (exactly one axis differs, using exact grid offsets)
        cardinal_offsets: List[Coordinate] = [
            (node_size, 0, 0),
            (-node_size, 0, 0),
            (0, node_size, 0),
            (0, -node_size, 0),
            (0, 0, node_size),
            (0, 0, -node_size),
        ]
        for dx, dy, dz in cardinal_offsets:
            coord = key3(node.x + dx, node.y + dy, node.z + dz)
            candidate = node_dict.get(coord)
            if candidate:
                neighbors.append((candidate, node_size))
                # print(f"[DEBUG] Cardinal neighbor found at {coord} with cost {node_size}")

        # Examine all nodes for near-cardinal and closest circular node connections.
        for candidate in node_dict.values():
            if candidate is node:
                continue

            dx = abs(candidate.x - node.x)
            dy = abs(candidate.y - node.y)
            dz = abs(candidate.z - node.z)

            # Count how many coordinates differ significantly (beyond tolerance)
            diff_count = sum(1 for d in (dx, dy, dz) if d > tolerance)

            # Near-cardinal move: exactly one axis differs,
            # and allowed only if one node is circular and the other is not.
            if diff_count == 1 and (
                (NodeGridType.CIRCULAR.value in node.grid_type)
                ^ (NodeGridType.CIRCULAR.value in candidate.grid_type)
            ):
                # Keep within ~2 steps along that axis
                if euclidean_distance(node, candidate) <= 2 * node_size - tolerance:
                    neighbors.append((candidate, euclidean_distance(node, candidate)))
                    # print(f"[DEBUG] Near-cardinal neighbor (mixed types) found at ({candidate.x}, {candidate.y}, {candidate.z})")

        # If we're on the circular ring, link to the two closest circular neighbors (same plane).
        if NodeGridType.CIRCULAR.value in node.grid_type:
            same_plane_tol = tolerance  # stay on the ring plane
            circ_same_plane: list[tuple[Node, float]] = []
            for candidate_node in node_dict.values():
                if candidate_node is node:
                    continue
                if NodeGridType.CIRCULAR.value not in candidate_node.grid_type:
                    continue
                if abs(candidate_node.z - node.z) > same_plane_tol:
                    continue  # ensure same z-plane (e.g., z == node.z within tol)

                dist = euclidean_distance(node, candidate_node)
                if (
                    dist > tolerance
                ):  # guard against accidental duplicates at same coord
                    circ_same_plane.append((candidate_node, dist))

            # Take the two closest circular neighbors (same plane)
            circ_same_plane.sort(key=lambda t: t[1])
            for candidate_node, dist in circ_same_plane[:2]:
                neighbors.append((candidate_node, dist))

            # Cross-plane circular neighbors — look exactly one plane above and one plane below (z ± node_size)
            plane_tol = tolerance  # z tolerance when matching planes
            target_z_above = node.z + node_size
            target_z_below = node.z - node_size

            # Helper: pick closest circular node on a specific z plane (within plane_tol)
            def add_best_on_plane(target_z: float) -> None:
                plane_nodes = [
                    cn
                    for cn in node_dict.values()
                    if cn is not node
                    and NodeGridType.CIRCULAR.value in cn.grid_type
                    and abs(cn.z - target_z) <= plane_tol
                ]
                if not plane_nodes:
                    return
                best = min(plane_nodes, key=lambda cn: euclidean_distance(node, cn))
                neighbors.append((best, euclidean_distance(node, best)))

            # Add one above and one below if present
            add_best_on_plane(target_z_above)
            add_best_on_plane(target_z_below)

        # print(f"[DEBUG] Total neighbors found: {len(neighbors)}")
        return neighbors

    def find_path(
        self, start_node: Node, goal_node: Node, puzzle: Any
    ) -> Optional[List[Node]]:
        """
        Implements the A* pathfinding algorithm to find the cheapest path between two nodes.
        """
        # Priority queue for nodes to visit, ordered by f-score (estimated total cost)
        open_set: List[Tuple[float, Node]] = []
        # Set of nodes already evaluated
        closed_set: Set[Node] = set()

        # Reset pathfinding attributes (g, h, f, parent) for all nodes before starting a new search
        self.reset_nodes(puzzle.nodes)

        # Initialize the start node's scores
        start_node.g = 0.0  # Cost from start to start is 0
        start_node.h = manhattan_distance(
            start_node, goal_node
        )  # Heuristic cost estimate
        start_node.f = start_node.h  # Initial f-score
        heapq.heappush(
            open_set, (start_node.f, start_node)
        )  # Add start node to the queue

        # Main A* loop
        while open_set:
            # Get the node with the lowest f-score from the priority queue
            current_f, current_node = heapq.heappop(open_set)

            # If we reached the goal, reconstruct and return the path
            if current_node == goal_node:
                return self.reconstruct_path(current_node)

            # Mark the current node as evaluated
            closed_set.add(current_node)

            # Explore neighbors
            neighbors_with_costs = self.get_neighbors(puzzle, current_node)
            for neighbor, move_cost in neighbors_with_costs:
                # Skip neighbors that have already been evaluated
                if neighbor in closed_set:
                    continue

                # Skip neighbors that are marked as occupied (part of a previous path),
                # unless it's the goal node itself we are trying to reach.
                if neighbor.occupied and neighbor != goal_node:
                    continue

                # Calculate the tentative cost (g-score) to reach this neighbor from the start
                tentative_g = current_node.g + move_cost

                # If this path to the neighbor is better than any previously found path
                if tentative_g < neighbor.g:
                    # Update the neighbor's pathfinding attributes
                    neighbor.parent = current_node  # Record the path
                    neighbor.g = tentative_g  # Update cost from start
                    neighbor.h = manhattan_distance(
                        neighbor, goal_node
                    )  # Recalculate heuristic
                    neighbor.f = neighbor.g + neighbor.h  # Update total estimated cost

                    # Add the neighbor to the open set for evaluation if it's not already there.
                    # (A* implementations sometimes update existing entries, but adding duplicates
                    # and letting the heapq prioritize is simpler and often sufficient).
                    is_in_open_set = any(neighbor == item[1] for item in open_set)
                    if not is_in_open_set:
                        heapq.heappush(open_set, (neighbor.f, neighbor))

        # If the open set becomes empty and the goal was not reached, no path exists
        return None

    def reconstruct_path(self, current_node: Node) -> List[Node]:
        """
        Reconstructs the path from the goal node back to the start node
        by following the parent pointers.
        """
        path: List[Node] = []
        # Traverse backwards from the goal node using the parent links
        while current_node:
            path.append(current_node)
            current_node = current_node.parent
        # The path is constructed backwards, so reverse it for the correct order
        path.reverse()
        return path

    def _find_best_path_to_candidate(
        self, current_node: Node, candidates: List[Node], puzzle: Any
    ) -> Tuple[Optional[Node], Optional[List[Node]]]:
        """
        Finds the shortest path from the current node to the closest reachable
        candidate waypoint from the provided list.
        """
        # Sort candidates by Euclidean distance as a heuristic for closeness
        candidates.sort(key=lambda node: euclidean_distance(current_node, node))

        for candidate in candidates:
            # Attempt to find a path using A*
            path_segment = self.find_path(current_node, candidate, puzzle)

            if path_segment:
                # If a path is found, return this candidate and path
                return candidate, path_segment

        # If no path was found to any candidate
        return None, None

    def _verify_mounting_waypoints_visited(
        self,
        initial_mounting: List[Node],
        visited_waypoints: Set[Node],
        start_node: Node,
    ) -> None:
        """
        Checks if all required mounting waypoints were included in the path.
        Prints an error message for any missing waypoints.
        """
        # Identify mounting waypoints that should have been visited but weren't
        missed_mounting = [
            wp
            for wp in initial_mounting
            # Check against the original list, exclude start node if it happened to be mounting
            if wp not in visited_waypoints and wp != start_node
        ]
        if missed_mounting:
            print(
                f"\nError: Failed to include {len(missed_mounting)} required mounting waypoints in the final path:"
            )
            for node in missed_mounting:
                print(
                    f"  - Missing Mounting Node at: ({node.x:.1f}, {node.y:.1f}, {node.z:.1f})"
                )
            # Consider raising an exception or returning a failure status if this is critical

    def _trim_path_end_condition(self, total_path: List[Node]) -> List[Node]:
        """
        Enforces the rule that the path should end with at most one non-mounting
        waypoint after the last mounting waypoint. Trims the path if necessary.
        """
        if not total_path:
            return []  # Nothing to trim

        # Get the sequence of waypoints actually present in the generated path
        waypoints_in_order = [node for node in total_path if node.waypoint]
        if not waypoints_in_order:
            return total_path  # No waypoints to check against

        # Find the index of the last mounting waypoint in the sequence
        last_mounting_idx = -1
        for i in range(len(waypoints_in_order) - 1, -1, -1):
            if waypoints_in_order[i].mounting:
                last_mounting_idx = i
                break

        # If no mounting waypoints were found in the path, no trimming based on this rule is needed
        if last_mounting_idx == -1:
            # print("Path contains no mounting waypoints. End condition check skipped.")
            return total_path

        # Count how many non-mounting waypoints appear *after* the last mounting one
        non_mounting_after_last = 0
        for i in range(last_mounting_idx + 1, len(waypoints_in_order)):
            if not waypoints_in_order[i].mounting:
                non_mounting_after_last += 1

        # print(f"Non-mounting waypoints after last mounting waypoint in path: {non_mounting_after_last}")

        # If more than one non-mounting waypoint exists after the last mounting one, trim the path
        if non_mounting_after_last > 1:
            # Identify the waypoint that should be the *new* end (the first non-mounting one after the last mounting one)
            target_end_waypoint = waypoints_in_order[last_mounting_idx + 1]

            # Find the index in the *full path* where this target end waypoint appears
            end_path_idx = -1
            for idx, node in enumerate(total_path):
                if node == target_end_waypoint:
                    end_path_idx = idx
                    break  # Found the first occurrence

            if end_path_idx != -1:
                print(
                    f"Path End Rule: Trimming path to end after waypoint ({target_end_waypoint.x:.1f},{target_end_waypoint.y:.1f},{target_end_waypoint.z:.1f}) at path index {end_path_idx}"
                )
                # Return the sliced path, including the target end waypoint
                return total_path[: end_path_idx + 1]
            else:
                # This case should be unlikely if the waypoint exists in waypoints_in_order
                print(
                    "Error: Could not find the target end waypoint in the total path during trimming."
                )
                return total_path  # Return original path on error
        else:
            # Path already satisfies the end condition
            return total_path

    def connect_waypoints(self, puzzle: Any) -> List[Node]:
        """
        Connects all waypoints defined in the puzzle, starting from the puzzle's
        start node. It aims for an even distribution of mounting vs. non-mounting
        waypoints and ensures all mounting waypoints are included.
        """
        # --- 1. Initialization ---
        all_waypoints = [node for node in puzzle.nodes if node.waypoint]
        if not all_waypoints:
            # print("No waypoints defined in the puzzle.")
            return []

        initial_mounting = [node for node in all_waypoints if node.mounting]
        initial_non_mounting = [node for node in all_waypoints if not node.mounting]

        start_node = puzzle.start_node
        if not start_node:
            # This case should ideally not happen based on node_creator logic
            print("Error: Puzzle start node not found.")
            return []

        # Prepare lists of waypoints yet to be visited, excluding the start node
        remaining_mounting = list(initial_mounting)
        remaining_non_mounting = list(initial_non_mounting)
        start_node_is_mounting = start_node.mounting
        if start_node in remaining_mounting:
            remaining_mounting.remove(start_node)
        if start_node in remaining_non_mounting:
            remaining_non_mounting.remove(start_node)

        # --- 2. Distribution Logic Setup ---
        # Calculate the target number of non-mounting waypoints per "gap" between mounting waypoints.
        # A "gap" occurs before the first mounting WP, between consecutive mounting WPs, and after the last one.
        num_gaps_for_distribution = (
            len(remaining_mounting) + 1
        )  # Includes potential segments before first / after last mounting WP.
        if num_gaps_for_distribution > 0 and remaining_non_mounting:
            # Target ratio for distributing non-mounting nodes among the gaps related to mounting nodes
            target_non_mounting_per_gap = (
                len(remaining_non_mounting) / num_gaps_for_distribution
            )
        else:
            # If no mounting points remain, or no non-mounting points exist, this ratio isn't meaningful for distribution.
            # Set high if non-mounts exist (add them all), else 0.
            target_non_mounting_per_gap = float("inf") if remaining_non_mounting else 0

        # --- 3. Path Construction Loop ---
        total_path: List[Node] = [start_node]  # Start the path with the initial node
        current_node: Node = start_node
        # Keep track of waypoints added to the path to avoid duplicates and verify completion
        visited_waypoints: Set[Node] = {start_node} if start_node.waypoint else set()

        # State variables to guide waypoint type selection for distribution
        last_visited_was_mounting: bool = start_node_is_mounting
        # Count non-mounting waypoints added since the last mounting one was added
        non_mounting_count_since_last_mount: int = (
            0 if start_node_is_mounting else (1 if start_node.waypoint else 0)
        )

        # Loop until all waypoints (both types) have been visited
        while remaining_mounting or remaining_non_mounting:
            # --- Decide which type of waypoint to target next ---
            target_mounting: bool
            if not remaining_mounting:
                target_mounting = False  # Can only target non-mounting
            elif not remaining_non_mounting:
                target_mounting = True  # Must target mounting
            else:
                # Core distribution logic:
                if last_visited_was_mounting:
                    # Just added a mounting node, ideally start the next gap with non-mounting
                    target_mounting = False
                else:
                    # Last added was non-mounting. Check if the current gap is "full".
                    if (
                        non_mounting_count_since_last_mount
                        < target_non_mounting_per_gap
                    ):
                        # Gap needs more non-mounting nodes
                        target_mounting = False
                    else:
                        # Gap is full enough, time to target the next mounting node
                        target_mounting = True

            # --- Select candidates and find the best path ---
            candidates: List[Node]
            candidate_type_str = "Mounting" if target_mounting else "Non-Mounting"

            if target_mounting:
                candidates = remaining_mounting
            else:
                candidates = remaining_non_mounting

            # If the preferred type has no candidates left, switch to the other type
            if not candidates:
                # print(f"No candidates for preferred type {candidate_type_str}. Switching target.")
                target_mounting = not target_mounting
                candidate_type_str = "Mounting" if target_mounting else "Non-Mounting"
                if target_mounting:
                    candidates = remaining_mounting
                else:
                    candidates = remaining_non_mounting

                # If still no candidates, all waypoints must have been processed
                if not candidates:
                    # print("No remaining waypoints of either type. Exiting loop.")
                    break

            # Find the closest reachable candidate of the chosen type
            chosen_node, chosen_path = self._find_best_path_to_candidate(
                current_node, candidates, puzzle
            )

            # --- Process the chosen path ---
            if chosen_node and chosen_path:
                # Mark nodes in the new path segment as occupied (excluding the start node of the segment)
                self.occupy_path(chosen_path[1:])

                # Append the new segment to the total path
                total_path.extend(chosen_path[1:])

                # Update state: current node, visited waypoints, remaining lists, distribution counters
                current_node = chosen_node
                visited_waypoints.add(chosen_node)

                if chosen_node.mounting:
                    if chosen_node in remaining_mounting:
                        remaining_mounting.remove(chosen_node)
                    last_visited_was_mounting = True
                    non_mounting_count_since_last_mount = (
                        0  # Reset counter for the new gap
                    )
                else:
                    if chosen_node in remaining_non_mounting:
                        remaining_non_mounting.remove(chosen_node)
                    last_visited_was_mounting = False
                    non_mounting_count_since_last_mount += (
                        1  # Increment count for this gap
                    )

            else:
                # Critical failure: Couldn't reach any remaining candidate of the required type.
                # This might indicate an issue with the node grid, obstacles, or waypoint placement.
                print(
                    f"\nError: Could not find a path to any remaining {candidate_type_str} waypoint from ({current_node.x:.1f}, {current_node.y:.1f}, {current_node.z:.1f})."
                )
                print(
                    f"Stopping path construction. {len(remaining_mounting)} mounting, {len(remaining_non_mounting)} non-mounting waypoints remain unreached."
                )
                self._verify_mounting_waypoints_visited(
                    initial_mounting, visited_waypoints, start_node
                )  # Report missed mounting WPs
                # return what we have thus far for debugging
                return total_path

        # --- 4. Final Checks and Cleanup ---

        # Verify all initial mounting waypoints were included
        self._verify_mounting_waypoints_visited(
            initial_mounting, visited_waypoints, start_node
        )

        # Enforce end condition (max 1 non-mounting after last mounting)
        total_path = self._trim_path_end_condition(total_path)

        # Mark the actual last node of the final path as the puzzle end
        if total_path:
            # Ensure no other node has the puzzle_end flag
            for node in puzzle.nodes:
                node.puzzle_end = False
            total_path[-1].puzzle_end = True
        else:
            print("Warning: No path generated.")

        # print(f"--- connect_waypoints Finished. Final Path Length: {len(total_path)} nodes ---")
        return total_path

    def reset_nodes(self, nodes: List[Node]) -> None:
        """
        Resets the pathfinding attributes (g, h, f, parent) of all nodes.
        This is crucial before starting a new A* search to clear previous run data.
        It does NOT reset the 'occupied' status.
        """
        for node in nodes:
            node.g = float("inf")  # Cost from start
            node.h = 0.0  # Heuristic cost to goal
            node.f = float("inf")  # Total estimated cost
            node.parent = None  # Path reconstruction link

    def occupy_path(self, path: List[Node]) -> None:
        """
        Marks the nodes in the provided path segment as occupied. This prevents
        them from being reused in subsequent pathfinding searches (unless they
        are the target goal node).
        """
        for node in path:
            # Mark node as occupied if it isn't already
            if not node.occupied:
                node.occupied = True
