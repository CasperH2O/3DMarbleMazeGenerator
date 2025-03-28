# puzzle/path_finder.py

import heapq
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set, Tuple

from puzzle.node import Node
from puzzle.utils.distances import euclidean_distance, manhattan_distance


class PathFinder(ABC):
    @abstractmethod
    def find_path(
        self, start_node: Node, goal_node: Node, puzzle: Any
    ) -> Optional[List[Node]]:
        """
        Finds a path from the start node to the goal node using a pathfinding algorithm.

        Parameters:
            start_node (Node): The starting node of the path.
            goal_node (Node): The goal node of the path.
            puzzle (Any): The puzzle containing nodes and configurations.

        Returns:
            Optional[List[Node]]: A list of nodes representing the path from start to goal,
            or None if no path is found.
        """
        pass

    @abstractmethod
    def connect_waypoints(self, puzzle: Any) -> List[Node]:
        """
        Connects all waypoints in the puzzle using the pathfinding algorithm.

        Parameters:
            puzzle (Any): The puzzle containing nodes and waypoints.

        Returns:
            List[Node]: The total path connecting all waypoints.
        """
        pass

    @abstractmethod
    def reset_nodes(self, nodes: List[Node]) -> None:
        """
        Resets the pathfinding attributes of the nodes.

        Parameters:
            nodes (List[Node]): The list of nodes to reset.
        """
        pass

    @abstractmethod
    def occupy_path(self, path: List[Node], nodes: List[Node]) -> None:
        """
        Marks the nodes in the path as occupied and resets their pathfinding attributes.

        Parameters:
            path (List[Node]): The path of nodes to occupy.
            nodes (List[Node]): The list of all nodes to reset.
        """
        pass


class AStarPathFinder(PathFinder):
    def find_path(
        self, start_node: Node, goal_node: Node, puzzle: Any
    ) -> Optional[List[Node]]:
        """
        Implements the A* pathfinding algorithm to find the cheapest path between two nodes.

        Parameters:
            start_node (Node): The starting node.
            goal_node (Node): The goal node.
            puzzle (Any): The puzzle containing nodes and configurations.

        Returns:
            Optional[List[Node]]: The cheapest path as a list of nodes, or None if no path is found.
        """
        open_set: List[Tuple[float, Node]] = []
        heapq.heappush(open_set, (start_node.f, start_node))
        closed_set: Set[Node] = set()

        start_node.g = 0.0
        start_node.h = manhattan_distance(start_node, goal_node)
        start_node.f = start_node.h

        while open_set:
            current_f, current_node = heapq.heappop(open_set)
            # print(f"[DEBUG] Visiting node: {current_node} with f = {current_f}")

            if current_node == goal_node:
                # print("[DEBUG] Goal reached!")
                return self.reconstruct_path(current_node)

            closed_set.add(current_node)

            for neighbor, move_cost in puzzle.get_neighbors(current_node):
                if neighbor in closed_set or neighbor.occupied:
                    # print(f"[DEBUG] Skipping neighbor {neighbor} (closed or occupied)")
                    continue

                tentative_g = current_node.g + move_cost
                # print(f"[DEBUG] Evaluating neighbor {neighbor}: tentative_g = {tentative_g}")

                if tentative_g < neighbor.g:
                    # print(f"[DEBUG] Updating neighbor {neighbor}: new g = {tentative_g}")
                    neighbor.parent = current_node
                    neighbor.g = tentative_g
                    neighbor.h = manhattan_distance(neighbor, goal_node)
                    neighbor.f = neighbor.g + neighbor.h
                    # print(f"[DEBUG] Neighbor {neighbor}: h = {neighbor.h}, f = {neighbor.f}")

                    if not any(neighbor == item[1] for item in open_set):
                        heapq.heappush(open_set, (neighbor.f, neighbor))
                        # print(f"[DEBUG] Neighbor {neighbor} added to open set with f = {neighbor.f}")

        # print("[DEBUG] No path found.")
        return None  # No path found

    def reconstruct_path(self, current_node: Node) -> List[Node]:
        """
        Reconstructs the path from the goal node back to the start node.

        Parameters:
            current_node (Node): The goal node from which to start the reconstruction.

        Returns:
            List[Node]: The reconstructed path as a list of nodes.
        """
        path: List[Node] = []
        while current_node:
            path.append(current_node)
            current_node = current_node.parent
        path.reverse()
        return path

    def connect_waypoints(self, puzzle: Any) -> List[Node]:
        """
        Connects all waypoints in the puzzle using the A* pathfinding algorithm and returns the total path.
        This version forces an even distribution of mounting and non mounting waypoints.
        It uses a fixed ideal gap calculated from the initial counts:
          - If the start node is mounting, then let remaining mounting = (total mounting waypoints - 1)
            and remaining non-mounting = total non-mounting waypoints.
          - We reserve exactly one non-mounting node for the final gap.
          - The remaining non-mounting nodes should be evenly distributed between the mounting nodes.

        Parameters:
            puzzle (Any): The puzzle containing nodes and waypoints.

        Returns:
            List[Node]: The total path connecting all waypoints.
        """
        # Separate waypoints into mounting and non mounting lists
        mounting_waypoints: List[Node] = [
            node for node in puzzle.nodes if node.waypoint and node.mounting
        ]
        non_mounting_waypoints: List[Node] = [
            node for node in puzzle.nodes if node.waypoint and not node.mounting
        ]

        # print(f"Initial mounting waypoints count: {len(mounting_waypoints)}")
        # print(f"Initial non-mounting waypoints count: {len(non_mounting_waypoints)}")

        if not (mounting_waypoints or non_mounting_waypoints):
            print("No waypoints to connect.")
            return []

        # start node
        start_node: Optional[Node] = next(
            (node for node in puzzle.nodes if node.puzzle_start), None
        )
        if start_node:
            current_node = start_node
            # Remove start node from waypoint lists if it is marked as one
            if start_node in mounting_waypoints:
                mounting_waypoints.remove(start_node)
            if start_node in non_mounting_waypoints:
                non_mounting_waypoints.remove(start_node)
        else:
            if non_mounting_waypoints:
                current_node = non_mounting_waypoints.pop(0)
            elif mounting_waypoints:
                current_node = mounting_waypoints.pop(0)
            else:
                return []

        # print(f"Start node type: {'Mounting' if current_node.mounting else 'Non-Mounting'}")

        total_path: List[Node] = []
        first_iteration: bool = True  # To handle the first segment

        # Calculate the ideal gap based on the initial counts after the start node is removed.
        # If the start is mounting, then:
        #   remaining_mount = len(mounting_waypoints)
        #   remaining_non_mount = len(non_mounting_waypoints)
        # We want exactly 1 non-mounting after the last mounting; so the other gaps should use:
        #   ideal_gap = (remaining_non_mount - 1) / remaining_mount    (if remaining_mount > 0)
        if mounting_waypoints:
            ideal_gap = (len(non_mounting_waypoints) - 1) / len(mounting_waypoints)
        else:
            ideal_gap = 0
        # print(f"Ideal gap between mounting nodes (non-mounting nodes per gap): {ideal_gap:.2f}")

        # --- Distribution control variable ---
        # Count of consecutive non-mounting nodes inserted since the last mounting node.
        non_mounting_since_last: float = 0.0
        # Track the type of the last inserted waypoint
        last_type: str = "mounting" if current_node.mounting else "non_mounting"

        # interleave waypoints until mounting waypoints are exhausted
        while mounting_waypoints or non_mounting_waypoints:
            # print(f"\nLoop start -- Remaining mounting: {len(mounting_waypoints)}, Remaining non-mounting: {len(non_mounting_waypoints)}")
            # print(f"Current node: {'Mounting' if current_node.mounting else 'Non-Mounting'}; non_mounting_since_last: {non_mounting_since_last:.2f}")

            # If mounting nodes remain, use the ideal gap to decide.
            if mounting_waypoints:
                if last_type == "mounting":
                    # Always start a gap after a mounting node.
                    required_type = "non_mounting"
                else:
                    # If current node is non mounting, check if we still need more non mounting nodes
                    # in this gap before inserting the next mounting.
                    if non_mounting_since_last < ideal_gap:
                        required_type = "non_mounting"
                    else:
                        required_type = "mounting"
            else:
                # No mounting nodes remain.
                # Per requirement, if available, append exactly one non mounting node after the last mounting.
                required_type = "non_mounting"
                # And if we've already appended one in the final gap, break.
                if non_mounting_since_last >= 1:
                    # print("Final gap already has one non-mounting node; terminating loop.")
                    break

            # print(f"Required next waypoint type: {required_type}")

            # Choose candidate(s) from the appropriate list.
            if required_type == "mounting":
                candidates = mounting_waypoints.copy()
            else:
                candidates = non_mounting_waypoints.copy()

            # Sort candidates by Euclidean distance from current_node.
            candidates.sort(key=lambda node: euclidean_distance(current_node, node))

            chosen = None
            chosen_path = None
            for candidate in candidates:
                self.reset_nodes(puzzle.nodes)
                path = self.find_path(current_node, candidate, puzzle)
                if path:
                    chosen = candidate
                    chosen_path = path
                    break

            if not chosen:
                # print("No reachable candidate for required type; breaking loop.")
                break

            # print(f"Chosen next waypoint: {'Mounting' if chosen.mounting else 'Non-Mounting'}")

            # Occupy and add the found path segment
            self.occupy_path(chosen_path, puzzle.nodes)
            if first_iteration:
                total_path.extend(chosen_path)
                first_iteration = False
            else:
                total_path.extend(chosen_path[1:])  # avoid duplication

            # Remove the chosen waypoint from its list.
            if chosen.mounting:
                if chosen in mounting_waypoints:
                    mounting_waypoints.remove(chosen)
            else:
                if chosen in non_mounting_waypoints:
                    non_mounting_waypoints.remove(chosen)

            # Update current node and our control variables.
            current_node = chosen
            if chosen.mounting:
                last_type = "mounting"
                non_mounting_since_last = 0.0
            else:
                last_type = "non_mounting"
                non_mounting_since_last += 1

        # If mounting nodes are exhausted but the last inserted node is not non mounting,
        # and if a non mounting candidate is available, append one final non mounting node.
        if mounting_waypoints == [] and non_mounting_waypoints:
            if last_type == "mounting" and non_mounting_since_last < 1:
                # print("Appending final non-mounting waypoint after last mounting node.")
                candidates = non_mounting_waypoints.copy()
                candidates.sort(key=lambda node: euclidean_distance(current_node, node))
                chosen = None
                chosen_path = None
                for candidate in candidates:
                    self.reset_nodes(puzzle.nodes)
                    path = self.find_path(current_node, candidate, puzzle)
                    if path:
                        chosen = candidate
                        chosen_path = path
                        break
                if chosen and chosen_path:
                    self.occupy_path(chosen_path, puzzle.nodes)
                    total_path.extend(chosen_path[1:])
            elif last_type == "non_mounting":
                # Already ended with non mounting.
                pass

        # Print final order of waypoint nodes
        final_waypoints = []
        for node in total_path:
            if node.waypoint:
                if not final_waypoints or final_waypoints[-1] is not node:
                    final_waypoints.append(node)
        if final_waypoints:
            # print("\nFinal waypoint distribution order:")
            for idx, node in enumerate(final_waypoints):
                # print(f"{idx+1}: {'Mounting' if node.mounting else 'Non-Mounting'}")
                pass

        if total_path:
            total_path[-1].puzzle_end = True

        return total_path

    def find_nearest_waypoint(
        self, current_node: Node, unvisited_waypoints: List[Node], puzzle: Any
    ) -> Tuple[Optional[Node], Optional[List[Node]]]:
        """
        Finds the nearest waypoint to the current node and the path to it.

        Parameters:
            current_node (Node): The current node.
            unvisited_waypoints (List[Node]): A list of waypoints not yet visited.
            puzzle (Any): The puzzle containing nodes and configurations.

        Returns:
            Tuple[Optional[Node], Optional[List[Node]]]:
                - The next waypoint (Node) if a path is found, else None.
                - The path to the next waypoint as a list of nodes, else None.
        """
        # Sort unvisited waypoints by Euclidean distance
        unvisited_waypoints.sort(
            key=lambda node: euclidean_distance(current_node, node)
        )
        for waypoint in unvisited_waypoints:
            self.reset_nodes(puzzle.nodes)
            path = self.find_path(current_node, waypoint, puzzle)
            if path:
                return waypoint, path
        return None, None

    def reset_nodes(self, nodes: List[Node]) -> None:
        """
        Resets the pathfinding attributes of the nodes.

        Parameters:
            nodes (List[Node]): The list of nodes to reset.
        """
        for node in nodes:
            node.g = float("inf")
            node.h = 0.0
            node.f = float("inf")
            node.parent = None

    def occupy_path(self, path: List[Node], nodes: List[Node]) -> None:
        """
        Marks the nodes in the path as occupied and resets their pathfinding attributes.

        Parameters:
            path (List[Node]): The path of nodes to occupy.
            nodes (List[Node]): The list of all nodes to reset.
        """
        for node in path:
            node.occupied = True
            node.g = float("inf")
            node.h = 0.0
            node.f = float("inf")
            node.parent = None
        # Reset the nodes before the next pathfinding iteration
        self.reset_nodes(nodes)
