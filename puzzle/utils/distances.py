# puzzle/utils/distances.py

from puzzle.node import Node

def manhattan_distance(node_a: Node, node_b: Node) -> float:
    """
    Calculate the Manhattan distance between two nodes in 3D space.

    The Manhattan distance is the sum of the absolute differences between the x, y, and z coordinates of two nodes.

    Args:
        node_a (Node): The first node.
        node_b (Node): The second node.

    Returns:
        float: The Manhattan distance between node_a and node_b.
    """
    return (abs(node_a.x - node_b.x) +
            abs(node_a.y - node_b.y) +
            abs(node_a.z - node_b.z))

def euclidean_distance(node_a: Node, node_b: Node) -> float:
    """
    Calculate the Euclidean distance between two nodes in 3D space.

    The Euclidean distance is the straight-line distance between two points in 3D space.

    Args:
        node_a (Node): The first node.
        node_b (Node): The second node.

    Returns:
        float: The Euclidean distance between node_a and node_b.
    """
    return ((node_a.x - node_b.x) ** 2 +
            (node_a.y - node_b.y) ** 2 +
            (node_a.z - node_b.z) ** 2) ** 0.5
