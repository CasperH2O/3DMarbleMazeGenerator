# puzzle/pathfinding.py

import heapq


def a_star(start_node, goal_node, puzzle):
    """
    A* pathfinding algorithm to find the shortest path between start_node and goal_node.
    """
    open_set = []
    heapq.heappush(open_set, (start_node.f, start_node))
    closed_set = set()

    start_node.g = 0
    start_node.h = manhattan_distance(start_node, goal_node)
    start_node.f = start_node.h

    while open_set:
        current_f, current_node = heapq.heappop(open_set)
        if current_node == goal_node:
            return reconstruct_path(current_node)

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


def reconstruct_path(current_node):
    """
    Reconstructs the path from the goal node to the start node.
    """
    path = []
    while current_node:
        path.append(current_node)
        current_node = current_node.parent
    path.reverse()
    return path


def manhattan_distance(node_a, node_b):
    """
    Calculates the Manhattan distance between two nodes.
    """
    return (abs(node_a.x - node_b.x) +
            abs(node_a.y - node_b.y) +
            abs(node_a.z - node_b.z))


def euclidean_distance(node_a, node_b):
    """
    Calculates the Euclidean distance between two nodes.
    """
    return ((node_a.x - node_b.x) ** 2 +
            (node_a.y - node_b.y) ** 2 +
            (node_a.z - node_b.z) ** 2) ** 0.5
