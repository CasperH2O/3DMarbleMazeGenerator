# puzzle/path_finder.py

from abc import ABC, abstractmethod
import heapq
from .utils import manhattan_distance, euclidean_distance


class PathFinder(ABC):
    @abstractmethod
    def find_path(self, start_node, goal_node, puzzle):
        pass

    @abstractmethod
    def connect_waypoints(self, puzzle):
        pass

    @abstractmethod
    def reset_nodes(self, nodes):
        pass

    @abstractmethod
    def occupy_path(self, path, nodes):
        pass


class AStarPathFinder(PathFinder):
    def find_path(self, start_node, goal_node, puzzle):
        open_set = []
        heapq.heappush(open_set, (start_node.f, start_node))
        closed_set = set()

        start_node.g = 0
        start_node.h = manhattan_distance(start_node, goal_node)
        start_node.f = start_node.h

        while open_set:
            current_f, current_node = heapq.heappop(open_set)
            if current_node == goal_node:
                return self.reconstruct_path(current_node)

            closed_set.add(current_node)

            for neighbor in puzzle.get_neighbors(current_node):
                if neighbor in closed_set:
                    continue

                tentative_g = current_node.g + puzzle.node_size

                if tentative_g < neighbor.g:
                    neighbor.parent = current_node
                    neighbor.g = tentative_g
                    neighbor.h = manhattan_distance(neighbor, goal_node)
                    neighbor.f = neighbor.g + neighbor.h

                    in_open_set = any(neighbor == item[1] for item in open_set)
                    if not in_open_set:
                        heapq.heappush(open_set, (neighbor.f, neighbor))

        return None  # Path not found

    def reconstruct_path(self, current_node):
        path = []
        while current_node:
            path.append(current_node)
            current_node = current_node.parent
        path.reverse()
        return path

    def connect_waypoints(self, puzzle):
        """
        Connects waypoints using the pathfinding algorithm and returns the total path.
        """
        waypoints = [node for node in puzzle.nodes if node.waypoint]
        if not waypoints:
            print("No waypoints to connect.")
            return []

        # Ensure the start node is the first node in the route
        start_node = next((node for node in puzzle.nodes if node.puzzle_start), None)
        if start_node:
            current_node = start_node
            if start_node in waypoints:
                waypoints.remove(start_node)
        else:
            # If no start node is set, use the first waypoint
            current_node = waypoints.pop(0)

        total_path = []

        first_iteration = True  # Flag to handle the first path differently

        while waypoints:
            next_waypoint, path = self.find_nearest_waypoint(current_node, waypoints, puzzle)
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

    def find_nearest_waypoint(self, current_node, unvisited_waypoints, puzzle):
        # Sort unvisited waypoints by Euclidean distance
        unvisited_waypoints.sort(key=lambda node: euclidean_distance(current_node, node))
        for waypoint in unvisited_waypoints:
            self.reset_nodes(puzzle.nodes)
            path = self.find_path(current_node, waypoint, puzzle)
            if path:
                return waypoint, path
        return None, None

    def reset_nodes(self, nodes):
        for node in nodes:
            node.g = float('inf')
            node.h = 0
            node.f = float('inf')
            node.parent = None

    def occupy_path(self, path, nodes):
        for node in path:
            node.occupied = True
            node.g = float('inf')
            node.h = 0
            node.f = float('inf')
            node.parent = None
        # Reset the nodes before the next pathfinding iteration
        self.reset_nodes(nodes)
