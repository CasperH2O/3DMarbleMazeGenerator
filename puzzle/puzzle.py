# puzzle/puzzle.py

from .node_creator import NodeCreator
from .pathfinder import PathFinder
import random
from .node import Node
import numpy as np

class Puzzle:
    """
    Generates a 3D maze puzzle within a sphere using specified node creation and pathfinding strategies.

    Attributes:
        diameter (float): Diameter of the sphere.
        shell_thickness (float): Thickness of the shell.
        node_size (float): Size of each node in the grid.
        seed (int): Seed for random number generators.
        node_creator (NodeCreator): Strategy for creating nodes.
        pathfinder (PathFinder): Strategy for pathfinding.
    """

    def __init__(self, diameter, shell_thickness, node_size, seed, node_creator: NodeCreator, pathfinder: PathFinder):
        self.diameter = diameter
        self.shell_thickness = shell_thickness
        self.node_size = node_size
        self.seed = seed

        # Calculate inner radius and effective radius
        self.inner_radius = (self.diameter / 2) - self.shell_thickness

        # Initialize the node creator and generate nodes
        self.node_creator = node_creator
        self.nodes, self.node_dict = self.node_creator.create_nodes(self)

        # Initialize the pathfinder
        self.pathfinder = pathfinder

        # Define start and initial route from start
        self.define_start_node_and_route()

        # Define mounting waypoints and home
        self.define_mounting_waypoints()

        # Randomly occupy nodes within the sphere as obstacles
        self.randomly_occupy_nodes(min_percentage=0, max_percentage=0)

        # Randomly select waypoints
        self.randomly_select_waypoints(num_waypoints=5)

        # Connect the waypoints using the pathfinder
        self.total_path = self.pathfinder.connect_waypoints(self)

    def get_neighbors(self, node):
        """Delegates neighbor retrieval to the node creator."""
        return self.node_creator.get_neighbors(node, self.node_dict, self.node_size)

    def define_start_node_and_route(self):
        # Find the minimum x among existing nodes on the X-axis (where y=0 and z=0)
        x_axis_nodes = [node for node in self.nodes if node.y == 0 and node.z == 0]
        if x_axis_nodes:
            min_x = min(node.x for node in x_axis_nodes)
        else:
            min_x = 0  # If no nodes exist, start from 0

        # Calculate positions for the two new nodes in the negative x direction
        x1 = min_x - self.node_size
        x2 = x1 - self.node_size

        # Create two new nodes at positions (x1, 0, 0) and (x2, 0, 0)
        node1 = Node(x1, 0, 0)
        node2 = Node(x2, 0, 0)

        # Add them to self.nodes and self.node_dict
        self.nodes.extend([node1, node2])
        self.node_dict[(node1.x, node1.y, node1.z)] = node1
        self.node_dict[(node2.x, node2.y, node2.z)] = node2

        # Since x2 < x1, node2 is furthest from (0, 0, 0)
        node2.start = True  # Mark the furthest node as the start node

    def define_mounting_waypoints(self):
        random.seed(self.seed)

        # Determine the number of mounting waypoints (between 3 and 5)
        num_mounting_waypoints = random.randint(3, 5)

        # Get the outer radius at Z = 0
        outer_radius = self.inner_radius

        # Calculate the angle between waypoints
        angle_increment = 2 * np.pi / num_mounting_waypoints

        mounting_nodes = []

        for i in range(num_mounting_waypoints):
            angle = i * angle_increment + np.pi  # Start from angle π (180 degrees)

            # Calculate the (x, y) coordinates for this mounting node
            x = outer_radius * np.cos(angle)
            y = outer_radius * np.sin(angle)

            # Find the nearest unoccupied node at Z = 0
            nearest_node = min(
                (node for node in self.nodes if node.z == 0 and not node.occupied and node not in mounting_nodes),
                key=lambda node: np.sqrt((node.x - x) ** 2 + (node.y - y) ** 2)
            )
            nearest_node.mounting = True
            nearest_node.waypoint = True  # Mark as a waypoint to include in pathfinding

            mounting_nodes.append(nearest_node)

        print(f"Defined {len(mounting_nodes)} mounting waypoints: {mounting_nodes}")
        return mounting_nodes

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

