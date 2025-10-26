# puzzle/path_finder.py

import heapq
import logging
from typing import Any, Optional, Set, Tuple

from cad.cases.case_model_base import CaseShape
from logging_config import configure_logging
from puzzle.node import Node
from puzzle.utils.geometry import euclidean_distance, key3, manhattan_distance

configure_logging()
logger = logging.getLogger(__name__)

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
    ) -> list[Tuple[Node, float]]:
        """
        Get neighboring nodes for a given node in the grid.

        - Cardinal moves (exactly one axis differs using the exact grid offset) are always allowed.
        - Near-cardinal moves (diff_count == 1) between a circular and a non-circular node are allowed within a certain range.
          On cylindrical puzzles, circular nodes can only reach rectangular nodes when the circular node lies on the cylinder axes,
          This is to prevent rotated paths in the rectangular grid.
        - Moves between two circular nodes, closest two on the same plane
        - Circular node cross-plane links: connect to closest circular node on the plane one step above and one step below (z ± node_size)

        Each neighbor is returned as a tuple: (neighbor, cost), cost being the distance
        """
        node_dict = puzzle.node_dict
        node_size = puzzle.node_size
        neighbors: list[Tuple[Node, float]] = []
        tolerance = node_size * 0.1  # tolerance to decide if coordinates are "the same"

        # Cardinal moves (exactly one axis differs, using exact grid offsets)
        cardinal_offsets: list[Coordinate] = [
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
                logger.debug(
                    "Cardinal neighbor found at %s with cost %s", coord, node_size
                )

        # Cache a copy of the circular nodes that share the current z-plane so we can
        # reuse the list when evaluating near-cardinal and ring-only links. This
        # avoids repeatedly traversing the entire node dictionary.
        circular_plane_nodes = puzzle.get_circular_nodes_for_level(node.z)

        def maybe_add_near_cardinal(candidate: Node) -> None:
            if candidate is node:
                return

            dx = abs(candidate.x - node.x)
            dy = abs(candidate.y - node.y)
            dz = abs(candidate.z - node.z)
            diff_count = sum(1 for delta in (dx, dy, dz) if delta > tolerance)

            node_is_circular = node.in_circular_grid
            candidate_is_circular = candidate.in_circular_grid

            if diff_count != 1 or not (node_is_circular ^ candidate_is_circular):
                return

            if (
                puzzle.case_shape == CaseShape.CYLINDER
                and node_is_circular
                and not candidate_is_circular
                and abs(node.x) > tolerance
                and abs(node.y) > tolerance
            ):
                # Cylindrical casings allow circular -> rectangular moves only along
                # the primary axes. Prevents rotated swept paths in the rectangular grid
                return

            distance = euclidean_distance(node, candidate)
            if distance <= 2 * node_size - tolerance:
                neighbors.append((candidate, distance))

        checked_coords: set[Coordinate] = set()
        # Probe near-cardinal neighbors by walking along each axis explicitly.
        # Only visit coordinates that could actually be within
        # ±2 * node_size of the source node along a single axis.
        axis_builders = (
            ("x", node.x, lambda value: (value, node.y, node.z)),
            ("y", node.y, lambda value: (node.x, value, node.z)),
            ("z", node.z, lambda value: (node.x, node.y, value)),
        )

        for axis_name, axis_value, build_coords in axis_builders:
            # Start from the node's current coordinate and the closest snapped
            # grid coordinate. Snapping keeps behavior identical for nodes that
            # sit halfway between integer multiples of the node size.
            base_values: set[float] = {
                round(axis_value / node_size) * node_size,
                axis_value,
            }

            if not node.in_circular_grid and circular_plane_nodes:
                # When a rectangular node is adjacent to circular nodes on the
                # same plane, seed the candidate coordinates with the ring
                # positions.
                for circular_node in circular_plane_nodes:
                    if axis_name == "x":
                        if (
                            abs(circular_node.y - node.y) <= tolerance
                            and abs(circular_node.z - node.z) <= tolerance
                        ):
                            base_values.add(circular_node.x)
                    elif axis_name == "y":
                        if (
                            abs(circular_node.x - node.x) <= tolerance
                            and abs(circular_node.z - node.z) <= tolerance
                        ):
                            base_values.add(circular_node.y)
                    else:
                        if (
                            abs(circular_node.x - node.x) <= tolerance
                            and abs(circular_node.y - node.y) <= tolerance
                        ):
                            base_values.add(circular_node.z)

            for base in base_values:
                # Check exact ±1 and ±2 multiples of the node size from each
                # base coordinate. Limits search scope.
                for offset in (
                    0.0,
                    node_size,
                    -node_size,
                    2 * node_size,
                    -2 * node_size,
                ):
                    candidate_axis = base + offset
                    candidate_coords = build_coords(candidate_axis)
                    if candidate_coords in checked_coords:
                        continue
                    checked_coords.add(candidate_coords)
                    candidate_node = node_dict.get(key3(*candidate_coords))
                    if candidate_node:
                        maybe_add_near_cardinal(candidate_node)

        # When on the circular ring, link to the two closest circular neighbors (same plane).
        if node.in_circular_grid:
            same_plane_tol = tolerance  # stay on the ring plane
            circ_same_plane: list[tuple[Node, float]] = []
            for candidate_node in circular_plane_nodes:
                if candidate_node is node:
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
            circular_planes = puzzle.get_circular_nodes_by_plane()

            def add_best_on_plane(plane_level: int, target_z: float) -> None:
                plane_nodes = circular_planes.get(plane_level, [])
                best_candidate: Optional[Node] = None
                best_distance = float("inf")

                for candidate_node in plane_nodes:
                    if candidate_node is node:
                        continue
                    if abs(candidate_node.z - target_z) > plane_tol:
                        continue

                    distance = euclidean_distance(node, candidate_node)
                    if distance < best_distance:
                        best_distance = distance
                        best_candidate = candidate_node

                if best_candidate is not None:
                    # Maintain the legacy behavior of linking to exactly one
                    # circular neighbor above/below by only keeping the closest
                    # match on each plane.
                    neighbors.append((best_candidate, best_distance))

            # Add one above and one below if present
            add_best_on_plane(
                puzzle.get_circular_plane_level(target_z_above), target_z_above
            )
            add_best_on_plane(
                puzzle.get_circular_plane_level(target_z_below), target_z_below
            )

        logger.debug("Total neighbors found: %d", len(neighbors))
        return neighbors

    def find_path(
        self, start_node: Node, goal_node: Node, puzzle: Any
    ) -> Optional[list[Node]]:
        """
        Implements the A* pathfinding algorithm to find the cheapest path between two nodes.
        """
        # Priority queue for nodes to visit, ordered by f-score (estimated total cost)
        open_set: list[Tuple[float, Node]] = []
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

                # (Non) mounting waypoints can only be entered when they are the target goal.
                # Ensures mounting waypoints are not visited on route, preserving the
                # intended load-bearing distribution.
                if neighbor.waypoint and neighbor != goal_node:
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

    def reconstruct_path(self, current_node: Node) -> list[Node]:
        """
        Reconstructs the path from the goal node back to the start node
        by following the parent pointers.
        """
        path: list[Node] = []
        # Traverse backwards from the goal node using the parent links
        while current_node:
            path.append(current_node)
            current_node = current_node.parent
        # The path is constructed backwards, so reverse it for the correct order
        path.reverse()
        return path

    def _find_best_path_to_candidate(
        self, current_node: Node, candidates: list[Node], puzzle: Any
    ) -> Tuple[Optional[Node], Optional[list[Node]]]:
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
        initial_mounting: list[Node],
        visited_waypoints: Set[Node],
        start_node: Node,
    ) -> None:
        """
        Checks if all required mounting waypoints were included in the path.
        Logs an error message for any missing waypoints.
        """
        # Identify mounting waypoints that should have been visited but weren't
        missed_mounting = [
            wp
            for wp in initial_mounting
            # Check against the original list, exclude start node if it happened to be mounting
            if wp not in visited_waypoints and wp != start_node
        ]
        if missed_mounting:
            logger.error(
                "Failed to include %d required mounting waypoints in the final path:",
                len(missed_mounting),
            )
            for node in missed_mounting:
                logger.error(
                    "  - Missing Mounting Node at: (%.1f, %.1f, %.1f)",
                    node.x,
                    node.y,
                    node.z,
                )
            # Consider raising an exception or returning a failure status if this is critical

    def _trim_path_end_condition(self, total_path: list[Node]) -> list[Node]:
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
            logger.debug(
                "Path contains no mounting waypoints. End condition check skipped."
            )
            return total_path

        # Count how many non-mounting waypoints appear *after* the last mounting one
        non_mounting_after_last = 0
        for i in range(last_mounting_idx + 1, len(waypoints_in_order)):
            if not waypoints_in_order[i].mounting:
                non_mounting_after_last += 1

        logger.debug(
            "Non-mounting waypoints after last mounting waypoint in path: %d",
            non_mounting_after_last,
        )

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
                logger.warning(
                    "Path End Rule: Trimming path to end after waypoint (%.1f,%.1f,%.1f) at path index %d",
                    target_end_waypoint.x,
                    target_end_waypoint.y,
                    target_end_waypoint.z,
                    end_path_idx,
                )
                # Return the sliced path, including the target end waypoint
                return total_path[: end_path_idx + 1]
            else:
                # This case should be unlikely if the waypoint exists in waypoints_in_order
                logger.error(
                    "Could not find the target end waypoint in the total path during trimming."
                )
                return total_path  # Return original path on error
        else:
            # Path already satisfies the end condition
            return total_path

    def connect_waypoints(self, puzzle: Any) -> list[Node]:
        """
        Connects all waypoints defined in the puzzle, starting from the puzzle's
        start node. It aims for an even distribution of mounting vs. non-mounting
        waypoints and ensures all mounting waypoints are included.
        """

        # Compute waypoint lists with
        all_waypoints = [node for node in puzzle.nodes if node.waypoint]
        if not all_waypoints:
            return []
        initial_mounting = [node for node in all_waypoints if node.mounting]
        initial_non_mounting = [node for node in all_waypoints if not node.mounting]

        # Gather obstacle entry/exit nodes and build entry exit mapping
        entry_to_exit: dict[Node, Node] = {}
        for obstacle in puzzle.obstacle_manager.placed_obstacles:
            entry_to_exit[obstacle.entry_node] = obstacle.exit_node

        # Start at the beginning, check we have one
        start_node = puzzle.start_node
        if not start_node:
            # This should never happen, indicates failure in node creator
            logger.error("Puzzle start node not found.")
            return []

        # Prepare lists of waypoints yet to be visited, excluding the start node
        remaining_mounting = list(initial_mounting)
        remaining_non_mounting = list(initial_non_mounting)
        start_node_is_mounting = start_node.mounting
        if start_node in remaining_mounting:
            remaining_mounting.remove(start_node)
        if start_node in remaining_non_mounting:
            remaining_non_mounting.remove(start_node)

        # Distribution Logic Setup
        # Calculate the target number of non-mounting waypoints per "gap" between mounting waypoints.
        # A "gap" occurs before the first mounting WP, between consecutive mounting WPs, and after the last one.
        num_gaps_for_distribution = len(remaining_mounting) + 1
        # Includes potential segments before first / after last mounting WP.
        if num_gaps_for_distribution > 0 and remaining_non_mounting:
            # Target ratio for distributing non-mounting nodes among the gaps related to mounting nodes
            target_non_mounting_per_gap = (
                len(remaining_non_mounting) / num_gaps_for_distribution
            )
        else:
            # If no mounting points remain, or no non-mounting points exist, this ratio isn't meaningful for distribution.
            # Set high if non-mounts exist (add them all), else 0.
            target_non_mounting_per_gap = float("inf") if remaining_non_mounting else 0

        # Path Construction Loop
        total_path: list[Node] = [start_node]  # Start the path with the initial node
        current_node: Node = start_node
        # Keep track of waypoints added to the path to avoid duplicates and verify completion
        visited_waypoints: Set[Node] = {start_node} if start_node.waypoint else set()

        visited_waypoints: set[Node] = {start_node} if start_node.waypoint else set()

        # State variables to guide waypoint type selection for distribution
        last_visited_was_mounting: bool = start_node_is_mounting
        non_mounting_count_since_last_mount: int = (
            0 if start_node_is_mounting else (1 if start_node.waypoint else 0)
        )

        # Visit all the waypoints
        while remaining_mounting or remaining_non_mounting:
            # Decide which type of waypoint to target next
            target_mounting: bool
            if not remaining_mounting:
                target_mounting = False
            elif not remaining_non_mounting:
                target_mounting = True
            else:
                # Core distribution logic:
                if last_visited_was_mounting:
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

            # Select candidates and find the best path
            # Guard against to many non mounting waypoints after final mounting waypoint
            if (
                target_mounting
                and len(remaining_mounting) == 1
                and len(remaining_non_mounting) > 1
            ):
                target_mounting = False

            candidate_type_str = "Mounting" if target_mounting else "Non-Mounting"
            candidates: list[Node] = (
                remaining_mounting if target_mounting else remaining_non_mounting
            )

            # If no candidates availible, switch to the other type
            if not candidates:
                target_mounting = not target_mounting
                candidate_type_str = "Mounting" if target_mounting else "Non-Mounting"
                candidates = (
                    remaining_mounting if target_mounting else remaining_non_mounting
                )
                if not candidates:
                    break

            # Find the closest reachable node of the desired type
            chosen_node, chosen_path = self._find_best_path_to_candidate(
                current_node, candidates, puzzle
            )

            # Process the chosen path
            if chosen_node and chosen_path:
                # Mark nodes in the new path segment as occupied (excluding the start node of the segment)
                self.occupy_path(chosen_path[1:])

                # Append the new segment to the total path
                total_path.extend(chosen_path[1:])

                # Update state for any waypoints encountered along this path segment
                for path_node in chosen_path[1:]:
                    if not path_node.waypoint:
                        continue

                    visited_waypoints.add(path_node)

                    if path_node.mounting:
                        if path_node in remaining_mounting:
                            remaining_mounting.remove(path_node)
                        last_visited_was_mounting = True
                        non_mounting_count_since_last_mount = 0
                    else:
                        if path_node in remaining_non_mounting:
                            remaining_non_mounting.remove(path_node)
                        if last_visited_was_mounting:
                            non_mounting_count_since_last_mount = 1
                        else:
                            non_mounting_count_since_last_mount += 1
                        last_visited_was_mounting = False

                # Advance current node to the end of this segment
                current_node = chosen_path[-1]

                # Teleport, obstacle entry to exit.
                # If segment ended on an obstacle entry, jump to mapped exit
                # Treat EXIT as the visited non-mounting waypoint.
                mapped_exit = entry_to_exit.get(current_node)
                if mapped_exit is not None and mapped_exit is not current_node:
                    # Append as a zero-length hop for downstream visibility
                    if not mapped_exit.occupied:
                        mapped_exit.occupied = True
                    total_path.append(mapped_exit)

                    # Treat it as visiting a (non-mounting) waypoint
                    mapped_exit.waypoint = True
                    mapped_exit.mounting = False
                    visited_waypoints.add(mapped_exit)
                    if mapped_exit in remaining_non_mounting:
                        remaining_non_mounting.remove(mapped_exit)
                    # Update distribution counters
                    if last_visited_was_mounting:
                        non_mounting_count_since_last_mount = 1
                    else:
                        non_mounting_count_since_last_mount += 1
                    last_visited_was_mounting = False

                    # Continue planning from the exit node
                    current_node = mapped_exit

            else:
                logger.error(
                    "Could not find a path to any remaining %s waypoint from (%.1f, %.1f, %.1f).",
                    candidate_type_str,
                    current_node.x,
                    current_node.y,
                    current_node.z,
                )
                logger.error(
                    "Stopping path construction. %d mounting, %d non-mounting waypoints remain unreached.",
                    len(remaining_mounting),
                    len(remaining_non_mounting),
                )
                self._verify_mounting_waypoints_visited(
                    initial_mounting, visited_waypoints, start_node
                )
                return total_path

        # Veryify all mounting waypoints were included
        self._verify_mounting_waypoints_visited(
            initial_mounting, visited_waypoints, start_node
        )

        # Enforce end condition (max 1 non-mounting after last mounting)
        total_path = self._trim_path_end_condition(total_path)

        # Check
        if not total_path:
            logger.warning("No path generated.")

        return total_path

    def reset_nodes(self, nodes: list[Node]) -> None:
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

    def occupy_path(self, path: list[Node]) -> None:
        """
        Marks the nodes in the provided path segment as occupied. This prevents
        them from being reused in subsequent pathfinding searches (unless they
        are the target goal node).
        """
        for node in path:
            # Mark node as occupied if it isn't already
            if not node.occupied:
                node.occupied = True
