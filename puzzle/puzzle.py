# puzzle/puzzle.py

import random
import numpy as np
from utils import config  # Import config to access configuration variables


class Puzzle:
    def __init__(self, node_size, seed, case_shape):
        self.node_size = node_size
        self.seed = seed
        self.case_shape = case_shape

        # Initialize the casing, node_creator, and pathfinder based on case_shape
        if case_shape == 'Sphere':
            from .casing import SphereCasing
            self.casing = SphereCasing(
                diameter=config.DIAMETER,
                shell_thickness=config.SHELL_THICKNESS
            )
            from .node_creator import SphereGridNodeCreator
            self.node_creator = SphereGridNodeCreator()
        elif case_shape == 'Box':
            from .casing import BoxCasing
            self.casing = BoxCasing(
                width=config.WIDTH,
                height=config.HEIGHT,
                length=config.LENGTH
            )
            from .node_creator import BoxGridNodeCreator
            self.node_creator = BoxGridNodeCreator()
        else:
            raise ValueError(f"Unknown case_shape '{case_shape}' specified.")

        # Initialize the pathfinder
        from .path_finder import AStarPathFinder
        self.pathfinder = AStarPathFinder()

        # Generate nodes using the node creator
        self.nodes, self.node_dict, self.start_node = self.node_creator.create_nodes(self)

        # Define mounting waypoints
        self.casing.get_mounting_waypoints(self.nodes, self.seed)

        # Randomly occupy nodes within the casing as obstacles
        self.randomly_occupy_nodes(min_percentage=0, max_percentage=0)

        # Randomly select waypoints
        self.randomly_select_waypoints(num_waypoints=5)

        # Connect the waypoints using the pathfinder
        self.total_path = self.pathfinder.connect_waypoints(self)

    def get_neighbors(self, node):
        """Delegates neighbor retrieval to the node creator."""
        return self.node_creator.get_neighbors(node, self.node_dict, self.node_size)

    def define_mounting_waypoints(self):
        self.casing.get_mounting_waypoints(self.nodes, self.seed)

    def randomly_occupy_nodes(self, min_percentage=0, max_percentage=0):
        random.seed(self.seed)

        percentage_to_occupy = random.randint(min_percentage, max_percentage)
        print(f"Percentage to occupy: {percentage_to_occupy}%")

        num_cubes_to_occupy = int(len(self.nodes) * (percentage_to_occupy / 100))

        print(f"Number of nodes to occupy: {num_cubes_to_occupy}")
        print(f"Total number of nodes: {len(self.nodes)}")

        occupied_nodes = random.sample(self.nodes, num_cubes_to_occupy)
        for node in occupied_nodes:
            node.occupied = True

    def randomly_select_waypoints(self, num_waypoints=5, num_candidates=10):
        # Select unoccupied nodes
        unoccupied_nodes = [node for node in self.nodes if not node.occupied]
        if len(unoccupied_nodes) < num_waypoints:
            num_waypoints = len(unoccupied_nodes)
            print(f"Reduced number of waypoints to {num_waypoints} due to limited unoccupied nodes.")

        random.seed(self.seed)
        np.random.seed(self.seed)

        waypoints = []
        for _ in range(num_waypoints):
            # Generate candidates
            candidates = random.sample(unoccupied_nodes, min(num_candidates, len(unoccupied_nodes)))

            # Evaluate each candidate
            best_candidate = None
            max_min_dist = -1
            for candidate in candidates:
                candidate_pos = np.array([candidate.x, candidate.y, candidate.z])

                if not waypoints:
                    # If no waypoints yet, any candidate is acceptable
                    min_dist = float('inf')
                else:
                    # Compute distances to existing waypoints
                    dists = [
                        np.linalg.norm(candidate_pos - np.array([wp.x, wp.y, wp.z]))
                        for wp in waypoints
                    ]
                    min_dist = min(dists)

                # Select candidate with maximum minimum distance
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    best_candidate = candidate

            # Mark the best candidate as a waypoint
            best_candidate.waypoint = True
            waypoints.append(best_candidate)
            unoccupied_nodes.remove(best_candidate)

        print(f"Selected {num_waypoints} waypoints using Mitchell's Best-Candidate Algorithm.")
