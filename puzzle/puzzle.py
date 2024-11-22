# puzzle/puzzle.py

import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import CaseShape, Config
from .path_interpolator import PathInterpolator
from .path_finder import AStarPathFinder
from shapes.path_architect import PathArchitect
from .node import Node
from .node_creator import SphereGridNodeCreator, BoxGridNodeCreator
from .casing import SphereCasing, BoxCasing


class Puzzle:
    """
    Represents a puzzle consisting of nodes within a casing shape and includes methods
    to generate nodes, select waypoints, find paths, and interpolate paths.
    """

    def __init__(self, node_size: float, seed: int, case_shape: CaseShape) -> None:
        """
        Initializes the Puzzle by setting up the casing, node creator, pathfinder, and generating the nodes.

        Parameters:
            node_size (float): The size of each node in the grid.
            seed (int): Seed value for random number generators.
            case_shape (CaseShape): The shape of the puzzle casing.
        """
        self.node_size: float = node_size
        self.seed: int = seed
        self.case_shape: CaseShape = case_shape

        # Initialize the casing and node_creator based on case_shape
        if case_shape in (CaseShape.SPHERE, CaseShape.SPHERE_WITH_FLANGE, CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES):
            self.casing: SphereCasing = SphereCasing(
                diameter=Config.Sphere.SPHERE_DIAMETER,
                shell_thickness=Config.Sphere.SHELL_THICKNESS,
            )
            self.node_creator: SphereGridNodeCreator = SphereGridNodeCreator()
        elif case_shape == CaseShape.BOX:
            self.casing: BoxCasing = BoxCasing(
                width=Config.Box.WIDTH,
                height=Config.Box.HEIGHT,
                length=Config.Box.LENGTH,
                panel_thickness=Config.Box.PANEL_THICKNESS,
            )
            self.node_creator: BoxGridNodeCreator = BoxGridNodeCreator()
        else:
            raise ValueError(f"Unknown case_shape '{case_shape}' specified.")

        # Initialize the pathfinder
        self.pathfinder: AStarPathFinder = AStarPathFinder()

        # Generate nodes using the node creator
        self.nodes: List[Node]
        self.node_dict: Dict[Tuple[float, float, float], Node]
        self.start_node: Node
        self.nodes, self.node_dict, self.start_node = self.node_creator.create_nodes(self)

        # Define mounting waypoints
        self.define_mounting_waypoints()

        # Randomly occupy nodes within the casing as obstacles
        self.randomly_occupy_nodes(min_percentage=0, max_percentage=0)

        # Randomly select waypoints
        self.randomly_select_waypoints(num_waypoints=Config.Puzzle.NUMBER_OF_WAYPOINTS)

        # Connect the waypoints using the pathfinder
        self.total_path: List[Node] = self.pathfinder.connect_waypoints(self)

        # Interpolate the path
        '''
        self.path_interpolator: PathInterpolator = PathInterpolator(
            total_path=self.total_path,
            seed=self.seed,
        )
        self.interpolated_segments: List[Any] = self.path_interpolator.interpolated_segments
        '''
        
        # Process the path segments
        self.path_architect: PathArchitect = PathArchitect(self.total_path)

    def get_neighbors(self, node: Node) -> List[Node]:
        """
        Delegates neighbor retrieval to the node creator.

        Parameters:
            node (Node): The node for which to retrieve neighbors.

        Returns:
            List[Node]: A list of neighboring nodes.
        """
        return self.node_creator.get_neighbors(node, self.node_dict, self.node_size)

    def define_mounting_waypoints(self) -> None:
        """
        Defines mounting waypoints within the casing by delegating to the casing object.
        """
        self.casing.get_mounting_waypoints(self.nodes)

    def randomly_occupy_nodes(
        self, min_percentage: int = 0, max_percentage: int = 0
    ) -> None:
        """
        Randomly occupies a percentage of nodes within the casing as obstacles.

        Parameters:
            min_percentage (int, optional): Minimum percentage of nodes to occupy. Defaults to 0.
            max_percentage (int, optional): Maximum percentage of nodes to occupy. Defaults to 0.
        """
        random.seed(self.seed)

        percentage_to_occupy: int = random.randint(min_percentage, max_percentage)
        num_nodes_to_occupy: int = int(len(self.nodes) * (percentage_to_occupy / 100))

        occupied_nodes: List[Node] = random.sample(self.nodes, num_nodes_to_occupy)
        for node in occupied_nodes:
            node.occupied = True

    def randomly_select_waypoints(
        self, num_waypoints: int = 5, num_candidates: int = 10
    ) -> None:
        """
        Randomly selects waypoints from unoccupied nodes, ensuring they are spread out.

        Parameters:
            num_waypoints (int, optional): Number of waypoints to select. Defaults to 5.
            num_candidates (int, optional): Number of candidate nodes to consider when selecting each waypoint. Defaults to 10.
        """
        # Select unoccupied nodes
        unoccupied_nodes: List[Node] = [node for node in self.nodes if not node.occupied]
        if len(unoccupied_nodes) < num_waypoints:
            num_waypoints = len(unoccupied_nodes)
            print(
                f"Reduced number of waypoints to {num_waypoints} due to limited unoccupied nodes."
            )

        random.seed(self.seed)
        np.random.seed(self.seed)

        waypoints: List[Node] = []
        for _ in range(num_waypoints):
            # Generate candidates
            candidates: List[Node] = random.sample(
                unoccupied_nodes, min(num_candidates, len(unoccupied_nodes))
            )

            # Evaluate each candidate
            best_candidate: Optional[Node] = None
            max_min_dist: float = -1.0
            for candidate in candidates:
                candidate_pos = np.array([candidate.x, candidate.y, candidate.z])

                if not waypoints:
                    # If no waypoints yet, any candidate is acceptable
                    min_dist = float('inf')
                else:
                    # Compute distances to existing waypoints
                    dists = [
                        np.linalg.norm(
                            candidate_pos - np.array([wp.x, wp.y, wp.z])
                        )
                        for wp in waypoints
                    ]
                    min_dist = min(dists)

                # Select candidate with maximum minimum distance
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    best_candidate = candidate

            if best_candidate:
                # Mark the best candidate as a waypoint
                best_candidate.waypoint = True
                waypoints.append(best_candidate)
                unoccupied_nodes.remove(best_candidate)
            else:
                print("No suitable candidate found for waypoint selection.")

    def print_puzzle_info(self) -> None:
        """
        Prints detailed information about the puzzle, including segment statistics and usage of profile and curve types.
        """
        print("=== Puzzle Information ===")
        print(f"Total path length: {len(self.total_path)}")
        print(f"Number of segments: {len(self.path_architect.segments)}")

        # Segment statistics
        straight_segments = sum(
            1
            for segment in self.path_architect.segments
            if segment.curve_type is None
        )
        curved_segments = len(self.path_architect.segments) - straight_segments
        print(f"\n=== Segment Statistics ===")
        print(f"Straight segments: {straight_segments}")
        print(f"Curved segments: {curved_segments}")
        print(
            f"Ratio (curved/total): {curved_segments/len(self.path_architect.segments):.2%}"
        )

        # Path profile counts
        profile_counts: Dict[Any, int] = {}
        for segment in self.path_architect.segments:
            profile_counts[segment.profile_type] = (
                profile_counts.get(segment.profile_type, 0) + 1
            )

        print("\n=== Profile Type Usage ===")
        for profile_type, count in profile_counts.items():
            print(
                f"{profile_type.value}: {count} times ({count/len(self.path_architect.segments):.1%})"
            )

        # Curve type counts
        curve_counts: Dict[Any, int] = {}
        for segment in self.path_architect.segments:
            if segment.curve_type:
                curve_counts[segment.curve_type] = (
                    curve_counts.get(segment.curve_type, 0) + 1
                )

        print("\n=== Curve Type Usage ===")
        for curve_type, count in curve_counts.items():
            print(
                f"{curve_type.value}: {count} times ({count/len(self.path_architect.segments):.1%})"
            )

        # Straight segments count
        straight_segments = len(self.path_architect.segments) - sum(
            curve_counts.values()
        )
        print(
            f"Straight segments: {straight_segments} ({straight_segments/len(self.path_architect.segments):.1%})"
        )

        # Path profile information
        profile_types_used = set(
            segment.profile_type for segment in self.path_architect.segments
        )
        print(
            f"Profile types used: {len(profile_types_used)}, "
            f"{', '.join(pt.value for pt in profile_types_used)}"
        )

        # Curve models information
        curve_models_used = set(
            segment.curve_model for segment in self.path_architect.segments
        )
        print(f"Number of different curve models used: {len(curve_models_used)}")

        # Curve types information
        curve_types_used = set(
            segment.curve_type
            for segment in self.path_architect.segments
            if segment.curve_type is not None
        )
        print(
            f"Different curves used: {len(curve_types_used)}, "
            f"{', '.join(ct.value for ct in curve_types_used)}"
        )

        # Additional useful information
        print("\n=== Additional Details ===")
        print(f"Number of nodes: {len(self.nodes)}")
        print(
            f"Start point (xyz): ({self.nodes[0].x:.2f}, {self.nodes[0].y:.2f}, {self.nodes[0].z:.2f})"
        )
        print(
            f"End point (xyz): ({self.nodes[-1].x:.2f}, {self.nodes[-1].y:.2f}, {self.nodes[-1].z:.2f})"
        )
        print("\n")
