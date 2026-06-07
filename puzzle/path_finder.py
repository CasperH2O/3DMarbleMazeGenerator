# puzzle/path_finder.py

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Set, Tuple

from cad.cases.case_model_base import CaseShape
from logging_config import configure_logging
from puzzle.node import Node
from puzzle.utils.geometry import euclidean_distance, key3, manhattan_distance

configure_logging()
logger = logging.getLogger(__name__)

Coordinate = Tuple[float, float, float]


@dataclass
class BacktrackingState:
    """State for backtracking search through waypoint orderings."""

    current_node: Node
    remaining_mounting: list[Node]
    remaining_non_mounting: list[Node]
    path: list[Node]
    occupied_nodes: set[Node] = field(default_factory=set)
    visited_waypoints: set[Node] = field(default_factory=set)
    last_visited_was_mounting: bool = False
    non_mounting_count_since_last_mount: int = 0


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

    def _is_waypoint_reachable(
        self, from_node: Node, target: Node, puzzle: Any
    ) -> bool:
        """
        Quick check to determine if a waypoint is reachable from the current node.
        Uses A* but returns early once reachability is confirmed.
        """
        path = self.find_path(from_node, target, puzzle)
        return path is not None

    def _check_mounting_waypoints_reachable(
        self,
        from_node: Node,
        remaining_mounting: list[Node],
        puzzle: Any,
    ) -> bool:
        """
        Checks if all remaining mounting waypoints are still reachable from the
        current position. Used for pruning in backtracking search.
        """
        for waypoint in remaining_mounting:
            if not self._is_waypoint_reachable(from_node, waypoint, puzzle):
                logger.debug(
                    "Pruning: Mounting waypoint at (%.1f, %.1f, %.1f) is unreachable from (%.1f, %.1f, %.1f)",
                    waypoint.x,
                    waypoint.y,
                    waypoint.z,
                    from_node.x,
                    from_node.y,
                    from_node.z,
                )
                return False
        return True

    def _clear_occupied_nodes(self, nodes: set[Node]) -> None:
        """
        Clears the occupied status of the provided nodes.
        Used when backtracking to restore the grid state.
        """
        for node in nodes:
            node.occupied = False

    def _get_next_waypoint_preference(
        self,
        remaining_mounting: list[Node],
        remaining_non_mounting: list[Node],
        last_visited_was_mounting: bool,
        non_mounting_count_since_last_mount: int,
        target_non_mounting_per_gap: float,
    ) -> bool:
        """
        Determines whether the next waypoint should be mounting or non-mounting
        based on distribution preferences.

        Returns True if mounting should be targeted, False otherwise.
        """
        if not remaining_mounting:
            return False
        if not remaining_non_mounting:
            return True

        # Guard against too many non-mounting waypoints after final mounting waypoint
        if len(remaining_mounting) == 1 and len(remaining_non_mounting) > 1:
            return False

        if last_visited_was_mounting:
            return False
        else:
            # Last added was non-mounting. Check if the current gap is "full".
            if non_mounting_count_since_last_mount < target_non_mounting_per_gap:
                return False
            else:
                return True

    def _connect_waypoints_backtracking(
        self,
        puzzle: Any,
        initial_state: BacktrackingState,
        entry_to_exit: dict[Node, Node],
        target_non_mounting_per_gap: float,
        max_depth: int = 100,
    ) -> Optional[list[Node]]:
        """
        Backtracking search to find a valid waypoint ordering when greedy fails.

        Uses depth-first search with pruning based on mounting waypoint reachability.
        Respects distribution preferences but explores alternatives when needed.
        """
        logger.info(
            "Starting backtracking search with %d mounting and %d non-mounting waypoints remaining",
            len(initial_state.remaining_mounting),
            len(initial_state.remaining_non_mounting),
        )

        # Stack for DFS: each entry is a BacktrackingState
        stack: list[tuple[BacktrackingState, int]] = [(initial_state, 0)]
        iterations = 0
        max_iterations = 10000  # Safety limit to prevent infinite loops

        while stack and iterations < max_iterations:
            iterations += 1
            state, depth = stack.pop()

            if depth > max_depth:
                logger.debug("Max depth %d reached, backtracking", max_depth)
                # Clear occupied nodes from this branch
                self._clear_occupied_nodes(state.occupied_nodes)
                continue

            # Check if we've visited all waypoints
            if not state.remaining_mounting and not state.remaining_non_mounting:
                logger.info(
                    "Backtracking search succeeded after %d iterations at depth %d",
                    iterations,
                    depth,
                )
                return state.path

            # Restore the occupied state for this branch
            # First clear any nodes that shouldn't be occupied
            for node in puzzle.nodes:
                if node.occupied and node not in state.occupied_nodes and node not in state.path:
                    node.occupied = False
            # Then mark the nodes from this state as occupied
            for node in state.occupied_nodes:
                node.occupied = True

            # Determine preferred waypoint type based on distribution
            prefer_mounting = self._get_next_waypoint_preference(
                state.remaining_mounting,
                state.remaining_non_mounting,
                state.last_visited_was_mounting,
                state.non_mounting_count_since_last_mount,
                target_non_mounting_per_gap,
            )

            # Build candidate list: preferred type first, then alternative
            if prefer_mounting:
                candidates = list(state.remaining_mounting) + list(
                    state.remaining_non_mounting
                )
            else:
                candidates = list(state.remaining_non_mounting) + list(
                    state.remaining_mounting
                )

            # Sort each group by distance (closest first within each group)
            mounting_sorted = sorted(
                [c for c in candidates if c.mounting],
                key=lambda n: euclidean_distance(state.current_node, n),
            )
            non_mounting_sorted = sorted(
                [c for c in candidates if not c.mounting],
                key=lambda n: euclidean_distance(state.current_node, n),
            )

            # Rebuild candidates with distance ordering within preference groups
            if prefer_mounting:
                ordered_candidates = mounting_sorted + non_mounting_sorted
            else:
                ordered_candidates = non_mounting_sorted + mounting_sorted

            # Try each candidate
            found_valid_successor = False
            for candidate in ordered_candidates:
                # Attempt to find path to this candidate
                path_segment = self.find_path(state.current_node, candidate, puzzle)

                if not path_segment:
                    logger.debug(
                        "Backtracking: No path to candidate at (%.1f, %.1f, %.1f)",
                        candidate.x,
                        candidate.y,
                        candidate.z,
                    )
                    continue

                # Create new state for this branch
                new_occupied = state.occupied_nodes.copy()
                for node in path_segment[1:]:
                    new_occupied.add(node)

                new_remaining_mounting = list(state.remaining_mounting)
                new_remaining_non_mounting = list(state.remaining_non_mounting)

                if candidate in new_remaining_mounting:
                    new_remaining_mounting.remove(candidate)
                if candidate in new_remaining_non_mounting:
                    new_remaining_non_mounting.remove(candidate)

                # Temporarily mark nodes as occupied to check reachability
                for node in path_segment[1:]:
                    node.occupied = True

                # Prune if any mounting waypoints become unreachable
                if new_remaining_mounting and not self._check_mounting_waypoints_reachable(
                    candidate, new_remaining_mounting, puzzle
                ):
                    logger.debug(
                        "Backtracking: Pruning branch - mounting waypoints would become unreachable after visiting (%.1f, %.1f, %.1f)",
                        candidate.x,
                        candidate.y,
                        candidate.z,
                    )
                    # Restore occupied state
                    for node in path_segment[1:]:
                        if node not in state.occupied_nodes:
                            node.occupied = False
                    continue

                # Update distribution tracking
                new_last_was_mounting = candidate.mounting
                if candidate.mounting:
                    new_non_mounting_count = 0
                else:
                    if state.last_visited_was_mounting:
                        new_non_mounting_count = 1
                    else:
                        new_non_mounting_count = state.non_mounting_count_since_last_mount + 1

                # Handle obstacle entry/exit teleportation
                new_path = state.path + path_segment[1:]
                new_current_node = candidate

                mapped_exit = entry_to_exit.get(candidate)
                if mapped_exit is not None and mapped_exit is not candidate:
                    new_occupied.add(mapped_exit)
                    new_path.append(mapped_exit)
                    new_current_node = mapped_exit
                    # Treat exit as non-mounting waypoint
                    if mapped_exit in new_remaining_non_mounting:
                        new_remaining_non_mounting.remove(mapped_exit)
                    if new_last_was_mounting:
                        new_non_mounting_count = 1
                    else:
                        new_non_mounting_count += 1
                    new_last_was_mounting = False

                new_visited = state.visited_waypoints.copy()
                new_visited.add(candidate)
                if mapped_exit:
                    new_visited.add(mapped_exit)

                new_state = BacktrackingState(
                    current_node=new_current_node,
                    remaining_mounting=new_remaining_mounting,
                    remaining_non_mounting=new_remaining_non_mounting,
                    path=new_path,
                    occupied_nodes=new_occupied,
                    visited_waypoints=new_visited,
                    last_visited_was_mounting=new_last_was_mounting,
                    non_mounting_count_since_last_mount=new_non_mounting_count,
                )

                stack.append((new_state, depth + 1))
                found_valid_successor = True

                logger.debug(
                    "Backtracking: Added branch to waypoint at (%.1f, %.1f, %.1f), depth %d, %d mounting and %d non-mounting remaining",
                    candidate.x,
                    candidate.y,
                    candidate.z,
                    depth + 1,
                    len(new_remaining_mounting),
                    len(new_remaining_non_mounting),
                )

            if not found_valid_successor:
                logger.debug(
                    "Backtracking: No valid successors from (%.1f, %.1f, %.1f) at depth %d",
                    state.current_node.x,
                    state.current_node.y,
                    state.current_node.z,
                    depth,
                )

        if iterations >= max_iterations:
            logger.warning(
                "Backtracking search reached max iterations (%d) without finding solution",
                max_iterations,
            )
        else:
            logger.warning(
                "Backtracking search exhausted all possibilities after %d iterations",
                iterations,
            )

        return None

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

        Uses a hybrid approach:
        1. First attempts greedy pathfinding (fast, works most of the time)
        2. If greedy fails, falls back to backtracking search with pruning
        """
        logger.info("Starting waypoint connection process")

        # Compute waypoint lists
        all_waypoints = [node for node in puzzle.nodes if node.waypoint]
        if not all_waypoints:
            logger.warning("No waypoints found in puzzle")
            return []

        initial_mounting = [node for node in all_waypoints if node.mounting]
        initial_non_mounting = [node for node in all_waypoints if not node.mounting]

        logger.info(
            "Found %d total waypoints: %d mounting, %d non-mounting",
            len(all_waypoints),
            len(initial_mounting),
            len(initial_non_mounting),
        )

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
        num_gaps_for_distribution = len(remaining_mounting) + 1
        if num_gaps_for_distribution > 0 and remaining_non_mounting:
            target_non_mounting_per_gap = (
                len(remaining_non_mounting) / num_gaps_for_distribution
            )
        else:
            target_non_mounting_per_gap = float("inf") if remaining_non_mounting else 0

        logger.debug(
            "Distribution target: %.2f non-mounting waypoints per gap",
            target_non_mounting_per_gap,
        )

        # === PHASE 1: Try greedy approach first ===
        logger.info("Phase 1: Attempting greedy waypoint connection")
        greedy_result = self._connect_waypoints_greedy(
            puzzle=puzzle,
            start_node=start_node,
            remaining_mounting=list(remaining_mounting),
            remaining_non_mounting=list(remaining_non_mounting),
            entry_to_exit=entry_to_exit,
            target_non_mounting_per_gap=target_non_mounting_per_gap,
            start_node_is_mounting=start_node_is_mounting,
        )

        greedy_path, greedy_visited, greedy_remaining_m, greedy_remaining_nm = greedy_result

        # Check if greedy succeeded (all waypoints visited)
        if not greedy_remaining_m and not greedy_remaining_nm:
            logger.info(
                "Greedy approach succeeded - all %d waypoints connected",
                len(greedy_visited),
            )
            self._verify_mounting_waypoints_visited(
                initial_mounting, greedy_visited, start_node
            )
            total_path = self._trim_path_end_condition(greedy_path)
            return total_path

        # === PHASE 2: Greedy failed, try backtracking ===
        logger.warning(
            "Greedy approach failed - %d mounting and %d non-mounting waypoints unreached. "
            "Initiating backtracking search.",
            len(greedy_remaining_m),
            len(greedy_remaining_nm),
        )

        # Reset all occupied nodes before backtracking
        logger.debug("Resetting occupied nodes for backtracking")
        for node in puzzle.nodes:
            node.occupied = False

        # Mark start node as occupied
        start_node.occupied = True

        # Create initial state for backtracking
        initial_state = BacktrackingState(
            current_node=start_node,
            remaining_mounting=list(remaining_mounting),
            remaining_non_mounting=list(remaining_non_mounting),
            path=[start_node],
            occupied_nodes={start_node},
            visited_waypoints={start_node} if start_node.waypoint else set(),
            last_visited_was_mounting=start_node_is_mounting,
            non_mounting_count_since_last_mount=(
                0 if start_node_is_mounting else (1 if start_node.waypoint else 0)
            ),
        )

        backtrack_path = self._connect_waypoints_backtracking(
            puzzle=puzzle,
            initial_state=initial_state,
            entry_to_exit=entry_to_exit,
            target_non_mounting_per_gap=target_non_mounting_per_gap,
        )

        if backtrack_path:
            logger.info(
                "Backtracking search succeeded - path with %d nodes found",
                len(backtrack_path),
            )
            # Mark the final path nodes as occupied
            for node in backtrack_path:
                node.occupied = True

            visited_in_backtrack = {n for n in backtrack_path if n.waypoint}
            self._verify_mounting_waypoints_visited(
                initial_mounting, visited_in_backtrack, start_node
            )
            total_path = self._trim_path_end_condition(backtrack_path)
            return total_path

        # === PHASE 3: Both approaches failed, return best effort ===
        logger.error(
            "Both greedy and backtracking approaches failed. "
            "Returning partial path from greedy attempt."
        )

        # Restore the greedy path's occupied state
        for node in puzzle.nodes:
            node.occupied = False
        for node in greedy_path:
            node.occupied = True

        self._verify_mounting_waypoints_visited(
            initial_mounting, greedy_visited, start_node
        )
        total_path = self._trim_path_end_condition(greedy_path)

        if not total_path:
            logger.warning("No path generated.")

        return total_path

    def _connect_waypoints_greedy(
        self,
        puzzle: Any,
        start_node: Node,
        remaining_mounting: list[Node],
        remaining_non_mounting: list[Node],
        entry_to_exit: dict[Node, Node],
        target_non_mounting_per_gap: float,
        start_node_is_mounting: bool,
    ) -> tuple[list[Node], set[Node], list[Node], list[Node]]:
        """
        Greedy waypoint connection - always picks the closest reachable waypoint.

        Returns:
            tuple of (path, visited_waypoints, remaining_mounting, remaining_non_mounting)
        """
        total_path: list[Node] = [start_node]
        current_node: Node = start_node
        visited_waypoints: set[Node] = {start_node} if start_node.waypoint else set()

        last_visited_was_mounting: bool = start_node_is_mounting
        non_mounting_count_since_last_mount: int = (
            0 if start_node_is_mounting else (1 if start_node.waypoint else 0)
        )

        while remaining_mounting or remaining_non_mounting:
            # Determine preferred waypoint type
            target_mounting = self._get_next_waypoint_preference(
                remaining_mounting,
                remaining_non_mounting,
                last_visited_was_mounting,
                non_mounting_count_since_last_mount,
                target_non_mounting_per_gap,
            )

            candidate_type_str = "Mounting" if target_mounting else "Non-Mounting"
            candidates: list[Node] = (
                remaining_mounting if target_mounting else remaining_non_mounting
            )

            # If no candidates available, switch to the other type
            if not candidates:
                target_mounting = not target_mounting
                candidate_type_str = "Mounting" if target_mounting else "Non-Mounting"
                candidates = (
                    remaining_mounting if target_mounting else remaining_non_mounting
                )
                if not candidates:
                    break

            logger.debug(
                "Greedy: Targeting %s waypoint from (%.1f, %.1f, %.1f), %d candidates",
                candidate_type_str,
                current_node.x,
                current_node.y,
                current_node.z,
                len(candidates),
            )

            # Find the closest reachable node of the desired type
            chosen_node, chosen_path = self._find_best_path_to_candidate(
                current_node, candidates, puzzle
            )

            if chosen_node and chosen_path:
                logger.debug(
                    "Greedy: Found path to waypoint at (%.1f, %.1f, %.1f), path length %d",
                    chosen_node.x,
                    chosen_node.y,
                    chosen_node.z,
                    len(chosen_path),
                )

                # Mark nodes in the new path segment as occupied
                self.occupy_path(chosen_path[1:])
                total_path.extend(chosen_path[1:])

                # Update state for waypoints encountered
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

                current_node = chosen_path[-1]

                # Handle obstacle entry/exit teleportation
                mapped_exit = entry_to_exit.get(current_node)
                if mapped_exit is not None and mapped_exit is not current_node:
                    if not mapped_exit.occupied:
                        mapped_exit.occupied = True
                    total_path.append(mapped_exit)

                    mapped_exit.waypoint = True
                    mapped_exit.mounting = False
                    visited_waypoints.add(mapped_exit)
                    if mapped_exit in remaining_non_mounting:
                        remaining_non_mounting.remove(mapped_exit)

                    if last_visited_was_mounting:
                        non_mounting_count_since_last_mount = 1
                    else:
                        non_mounting_count_since_last_mount += 1
                    last_visited_was_mounting = False

                    current_node = mapped_exit
            else:
                logger.warning(
                    "Greedy: Could not find path to any %s waypoint from (%.1f, %.1f, %.1f)",
                    candidate_type_str,
                    current_node.x,
                    current_node.y,
                    current_node.z,
                )
                break

        return total_path, visited_waypoints, remaining_mounting, remaining_non_mounting

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
