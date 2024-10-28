# puzzle/node.py

class Node:
    """
    Represents a node in the 3D maze grid.
    """
    def __init__(self, x, y, z, occupied=False):
        self.x = x
        self.y = y
        self.z = z

        self.occupied = occupied    # Indicates if node is used for the puzzle
        self.waypoint = False       # Waypoint along the puzzle path
        self.puzzle_start = False   # Start of the puzzle
        self.puzzle_end = False     # End of the puzzle
        self.mounting = False       # Mounting node, connects to mounting bridge

        self.path_profile_type = None   # Type of path profile shape
        self.path_curve_type = None     # Type of path curve
        self.used_in_curve = False     # Todo, improve
        self.segment_start = False      # Indicates the start node of a segment
        self.segment_end = False        # Indicates the end node of a segment

        self.parent = None          # For path reconstruction
        self.g = float('inf')       # Cost from start to this node
        self.h = 0                  # Heuristic cost to goal
        self.f = float('inf')       # Total cost

    def __repr__(self):
        return (f"Node(x={self.x}, y={self.y}, z={self.z}, "
                f"occupied={self.occupied}, waypoint={self.waypoint}, start={self.puzzle_start}, end={self.puzzle_end})")

    def __lt__(self, other):
        return self.f < other.f  # For priority queue (heapq)
