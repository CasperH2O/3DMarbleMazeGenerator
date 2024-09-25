# puzzle/utils.py

def manhattan_distance(node_a, node_b):
    return (abs(node_a.x - node_b.x) +
            abs(node_a.y - node_b.y) +
            abs(node_a.z - node_b.z))


def euclidean_distance(node_a, node_b):
    return ((node_a.x - node_b.x) ** 2 +
            (node_a.y - node_b.y) ** 2 +
            (node_a.z - node_b.z) ** 2) ** 0.5
