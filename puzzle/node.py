# puzzle/node.py

class Node:
    """
    Represents a node in the 3D maze grid.
    """
    def __init__(self, x, y, z, occupied=False):
        self.x = x
        self.y = y
        self.z = z
        self.occupied = occupied
        self.waypoint = False  # Waypoint property
        self.start = False  # Start property
        self.end = False  # End property
        self.mounting = False  # Mounting property
        self.parent = None  # For path reconstruction
        self.g = float('inf')  # Cost from start to this node
        self.h = 0  # Heuristic cost to goal
        self.f = float('inf')  # Total cost

    def __repr__(self):
        return (f"Node(x={self.x}, y={self.y}, z={self.z}, "
                f"occupied={self.occupied}, waypoint={self.waypoint}, start={self.start}, end={self.end})")

    def __lt__(self, other):
        return self.f < other.f  # For priority queue (heapq)
