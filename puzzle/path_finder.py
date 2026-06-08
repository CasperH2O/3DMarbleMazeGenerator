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
    Also provides neighbor generation for the puzzle grid.
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
