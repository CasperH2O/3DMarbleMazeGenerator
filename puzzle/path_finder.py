# puzzle/path_finder.py

from abc import ABC, abstractmethod
import heapq
from typing import Any, Dict, List, Optional, Set, Tuple

from puzzle.utils.distances import manhattan_distance, euclidean_distance
from puzzle.node import Node

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
        Implements the A* pathfinding algorithm to find the shortest path between two nodes.

        Parameters:
            start_node (Node): The starting node.
            goal_node (Node): The goal node.
            puzzle (Any): The puzzle containing nodes and configurations.

        Returns:
            Optional[List[Node]]: The shortest path as a list of nodes, or None if no path is found.
        """
        open_set: List[Tuple[float, Node]] = []
        heapq.heappush(open_set, (start_node.f, start_node))
        closed_set: Set[Node] = set()

        start_node.g = 0.0
        start_node.h = manhattan_distance(start_node, goal_node)
        start_node.f = start_node.h

        while open_set:
            current_f, current_node = heapq.heappop(open_set)
            if current_node == goal_node:
                return self.reconstruct_path(current_node)

            closed_set.add(current_node)

            for neighbor in puzzle.get_neighbors(current_node):
                if neighbor in closed_set or neighbor.occupied:
                    continue

                tentative_g = current_node.g + puzzle.node_size

                if tentative_g < neighbor.g:
                    neighbor.parent = current_node
                    neighbor.g = tentative_g
                    neighbor.h = manhattan_distance(neighbor, goal_node)
                    neighbor.f = neighbor.g + neighbor.h

                    # Check if neighbor is already in open_set
                    in_open_set = any(neighbor == item[1] for item in open_set)
                    if not in_open_set:
                        heapq.heappush(open_set, (neighbor.f, neighbor))

        return None  # Path not found

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

        Parameters:
            puzzle (Any): The puzzle containing nodes and waypoints.

        Returns:
            List[Node]: The total path connecting all waypoints.
        """
        waypoints: List[Node] = [node for node in puzzle.nodes if node.waypoint]
        if not waypoints:
            print("No waypoints to connect.")
            return []

        # Ensure the start node is the first node in the route
        start_node: Optional[Node] = next(
            (node for node in puzzle.nodes if node.puzzle_start), None
        )
        if start_node:
            current_node = start_node
            if start_node in waypoints:
                waypoints.remove(start_node)
        else:
            # If no start node is set, use the first waypoint
            current_node = waypoints.pop(0)

        total_path: List[Node] = []
        first_iteration: bool = True  # Flag to handle the first path differently

        while waypoints:
            next_waypoint, path = self.find_nearest_waypoint(
                current_node, waypoints, puzzle
            )
            if next_waypoint and path:
                self.occupy_path(path, puzzle.nodes)
                if first_iteration:
                    total_path.extend(path)
                    first_iteration = False
                else:
                    # Skip the first node to prevent duplication
                    total_path.extend(path[1:])
                waypoints.remove(next_waypoint)
                current_node = next_waypoint
            else:
                print("No more reachable waypoints.")
                break

        # Set the last node in the path as the end node
        if total_path:
            end_node = total_path[-1]
            end_node.puzzle_end = True

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
        unvisited_waypoints.sort(key=lambda node: euclidean_distance(current_node, node))
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
            node.g = float('inf')
            node.h = 0.0
            node.f = float('inf')
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
            node.g = float('inf')
            node.h = 0.0
            node.f = float('inf')
            node.parent = None
        # Reset the nodes before the next pathfinding iteration
        self.reset_nodes(nodes)
