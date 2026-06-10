# puzzle/waypoint_connector.py

import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Set, Tuple

from logging_config import configure_logging
from puzzle.node import Node
from puzzle.path_finder import AStarPathFinder
from puzzle.utils.geometry import euclidean_distance

configure_logging()
logger = logging.getLogger(__name__)


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


class WaypointConnector:
    """
    Connects waypoints in a puzzle using a hybrid greedy + backtracking strategy.

    Uses an injected AStarPathFinder for individual path queries, and adds
    higher-level logic to order waypoints with an even mounting / non-mounting
    distribution while guaranteeing all mounting waypoints are visited.
    """

    def __init__(self, path_finder: AStarPathFinder) -> None:
        self._path_finder = path_finder

    def _find_best_path_to_candidate(
        self, current_node: Node, candidates: list[Node], puzzle: Any
    ) -> Tuple[Optional[Node], Optional[list[Node]]]:
        """
        Finds the shortest path from the current node to the closest reachable
        candidate waypoint from the provided list.
        """
        # Pre-sort by Euclidean distance as a heuristic; A* still finds the true shortest path
        candidates.sort(key=lambda node: euclidean_distance(current_node, node))

        for candidate in candidates:
            path_segment = self._path_finder.find_path(current_node, candidate, puzzle)

            if path_segment:
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
        path = self._path_finder.find_path(from_node, target, puzzle)
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
        # Would result in structurally unstable physical puzzle end
        if len(remaining_mounting) == 1 and len(remaining_non_mounting) > 1:
            return False

        if last_visited_was_mounting:
            return False
        else:
            # Last visited was non-mounting — check if the current gap is "full"
            if non_mounting_count_since_last_mount < target_non_mounting_per_gap:
                return False  # Gap not yet full — keep adding non-mounting
            else:
                return True  # Gap is full — time to target the next mounting node

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
            # First clear any nodes that shouldn't be occupied (preserve obstacle-occupied nodes)
            for node in puzzle.nodes:
                if node.occupied and not node.is_obstacle_occupied and node not in state.occupied_nodes and node not in state.path:
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
                path_segment = self._path_finder.find_path(state.current_node, candidate, puzzle)

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
        # A "gap" is the space before the first mounting WP, between consecutive mounting WPs,
        # and after the last one; num_gaps = len(mounting) + 1.
        num_gaps_for_distribution = len(remaining_mounting) + 1
        if num_gaps_for_distribution > 0 and remaining_non_mounting:
            # Target ratio for distributing non-mounting nodes evenly among gaps
            target_non_mounting_per_gap = (
                len(remaining_non_mounting) / num_gaps_for_distribution
            )
        else:
            # No mounting points or no non-mounting points: ratio is not meaningful.
            # Set to inf so all non-mounting nodes are added; 0 if none exist.
            target_non_mounting_per_gap = float("inf") if remaining_non_mounting else 0

        logger.debug(
            "Distribution target: %.2f non-mounting waypoints per gap",
            target_non_mounting_per_gap,
        )

        # Try greedy approach first
        logger.info("Attempting greedy waypoint connection")
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

        # Greedy failed, try backtracking
        logger.warning(
            "Greedy approach failed - %d mounting and %d non-mounting waypoints unreached. "
            "Initiating backtracking search.",
            len(greedy_remaining_m),
            len(greedy_remaining_nm),
        )

        # Reset all occupied nodes before backtracking (preserve obstacle-occupied nodes)
        logger.debug("Resetting occupied nodes for backtracking")
        for node in puzzle.nodes:
            if not node.is_obstacle_occupied:
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

        # Both approaches failed, return best effort
        logger.error(
            "Both greedy and backtracking approaches failed. "
            "Returning partial path from greedy attempt."
        )

        # Restore the greedy path's occupied state (preserve obstacle-occupied nodes)
        for node in puzzle.nodes:
            if not node.is_obstacle_occupied:
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
                self._path_finder.occupy_path(chosen_path[1:])
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

                # If path ended on an obstacle entry, jump to its exit.
                # Append as a zero-length hop so downstream code sees the entry→exit adjacency.
                mapped_exit = entry_to_exit.get(current_node)
                if mapped_exit is not None and mapped_exit is not current_node:
                    if not mapped_exit.occupied:
                        mapped_exit.occupied = True
                    total_path.append(mapped_exit)

                    # Treat exit as a (non-mounting) waypoint
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
