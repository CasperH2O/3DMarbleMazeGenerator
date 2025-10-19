# puzzle/puzzle.py

import random
from collections import Counter
from typing import Optional

import numpy as np

from cad.path_architect import PathArchitect
from config import CaseShape, Config
from obstacles.obstacle_manager import ObstacleManager
from puzzle.grid_layouts.grid_layout_box import BoxCasing
from puzzle.grid_layouts.grid_layout_cylinder import CylinderCasing
from puzzle.grid_layouts.grid_layout_sphere import SphereCasing
from puzzle.node import Node
from puzzle.path_finder import AStarPathFinder
from puzzle.utils.geometry import key3


class Puzzle:
    """
    Represents a puzzle consisting of nodes within a casing shape and includes methods
    to generate nodes, select waypoints, find paths, and interpolate paths.
    """

    def __init__(self, node_size: float, seed: int, case_shape: CaseShape) -> None:
        """
        Initializes the Puzzle by setting up the casing, node creator, pathfinder, and generating the nodes.
        """
        self.node_size: float = node_size
        self.seed: int = seed
        self.case_shape: CaseShape = case_shape

        # Initialize the casing and node_creator based on case_shape
        if case_shape in (
            CaseShape.SPHERE,
            CaseShape.SPHERE_WITH_FLANGE,
            CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES,
        ):
            self.casing = SphereCasing(
                diameter=Config.Sphere.SPHERE_DIAMETER,
                shell_thickness=Config.Sphere.SHELL_THICKNESS,
            )
        elif case_shape == CaseShape.BOX:
            self.casing = BoxCasing(
                width=Config.Box.WIDTH,
                height=Config.Box.HEIGHT,
                length=Config.Box.LENGTH,
                panel_thickness=Config.Box.PANEL_THICKNESS,
            )
        elif case_shape == CaseShape.CYLINDER:
            self.casing = CylinderCasing(
                diameter=Config.Cylinder.DIAMETER,
                height=Config.Cylinder.HEIGHT,
                shell_thickness=Config.Cylinder.SHELL_THICKNESS,
            )
        else:
            raise ValueError(f"Unknown case_shape '{case_shape}'.")

        # Initialize the pathfinder
        self.path_finder: AStarPathFinder = AStarPathFinder()

        # nodes, dict, start from casing
        self.nodes, self.node_dict, self.start_node = self.casing.create_nodes()

        # Define mounting waypoints
        self.define_mounting_waypoints()

        # Node neighbor connectivity sanity-check,
        self._check_node_connectivity()

        # Populate puzzle with obstacles
        self.obstacle_manager: ObstacleManager = ObstacleManager(self.nodes)

        # Randomly occupy nodes within the casing as road blocks
        self.randomly_occupy_nodes(min_percentage=0, max_percentage=0)

        # Randomly select waypoints
        self.randomly_select_waypoints(num_waypoints=Config.Puzzle.NUMBER_OF_WAYPOINTS)

        # Connect the waypoints using the pathfinder
        self.total_path: list[Node] = self.path_finder.connect_waypoints(self)

        # Process the path segments
        self.path_architect: PathArchitect = PathArchitect(
            self.total_path, self.obstacle_manager.placed_obstacles
        )

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
        """
        random.seed(self.seed)

        percentage_to_occupy: int = random.randint(min_percentage, max_percentage)
        num_nodes_to_occupy: int = int(len(self.nodes) * (percentage_to_occupy / 100))

        occupied_nodes: list[Node] = random.sample(self.nodes, num_nodes_to_occupy)
        for node in occupied_nodes:
            node.occupied = True

    def randomly_select_waypoints(
        self, num_waypoints: int = 5, num_candidates: int = 10
    ) -> None:
        """
        Randomly selects waypoints from unoccupied nodes, ensuring they are spread out.
        """
        # Select unoccupied nodes
        unoccupied_nodes: list[Node] = [
            node for node in self.nodes if not node.occupied
        ]
        if len(unoccupied_nodes) < num_waypoints:
            num_waypoints = len(unoccupied_nodes)
            print(
                f"Reduced number of waypoints to {num_waypoints} due to limited unoccupied nodes."
            )

        random.seed(self.seed)
        np.random.seed(self.seed)

        waypoints: list[Node] = []
        for _ in range(num_waypoints):
            # Generate candidates
            candidates: list[Node] = random.sample(
                unoccupied_nodes, min(num_candidates, len(unoccupied_nodes))
            )

            # Evaluate each candidate
            best_candidate: Optional[Node] = None
            max_min_dist: float = -1.0
            for candidate in candidates:
                candidate_pos = np.array([candidate.x, candidate.y, candidate.z])

                if not waypoints:
                    # If no waypoints yet, any candidate is acceptable
                    min_dist = float("inf")
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

            if best_candidate:
                # Mark the best candidate as a waypoint
                best_candidate.waypoint = True
                waypoints.append(best_candidate)
                unoccupied_nodes.remove(best_candidate)
            else:
                print("No suitable candidate found for waypoint selection.")

    def print_puzzle_info(self) -> None:
        """
        Prints detailed information about the generated puzzle configuration and results.
        """
        print("\n" + "=" * 30)
        print("      PUZZLE INFORMATION")
        print("=" * 30)

        # Configuration Summary
        print("\n--- Configuration Summary ---")
        print(f"Seed: {self.seed}")
        print(f"Case Shape: {self.case_shape.value}")
        if hasattr(Config.Puzzle, "CASE_MANUFACTURER"):
            print(f"Manufacturer Profile: {Config.Puzzle.CASE_MANUFACTURER.value}")
        if hasattr(Config.Puzzle, "THEME"):
            print(f"Theme: {Config.Puzzle.THEME.value}")
        print(f"Node Size (mm): {self.node_size}")
        print(f"Ball Diameter (mm): {Config.Puzzle.BALL_DIAMETER}")
        if isinstance(self.casing, SphereCasing):
            print(f"Sphere Diameter (mm): {Config.Sphere.SPHERE_DIAMETER}")
        elif isinstance(self.casing, BoxCasing):
            print(
                f"Box Dimensions (LxWxH mm): {Config.Box.LENGTH} x {Config.Box.WIDTH} x {Config.Box.HEIGHT}"
            )
        print(f"Requested Waypoints: {Config.Puzzle.NUMBER_OF_WAYPOINTS}")

        # Allowed Settings
        print("\n--- Allowed Path Settings (from Config) ---")
        print(
            f"Allowed Curve Models: {', '.join(m.value for m in Config.Path.PATH_CURVE_MODEL)}"
        )
        print(
            f"Allowed Profile Types: {', '.join(p.value for p in Config.Path.PATH_PROFILE_TYPES)}"
        )
        print(
            f"Allowed Curve Types for Detection: {', '.join(c.value for c in Config.Path.PATH_CURVE_TYPE)}"
        )

        # Node Grid Summary
        print("\n--- Node Grid Summary ---")
        total_nodes_generated = len(self.nodes)
        print(f"Total Nodes Generated: {total_nodes_generated}")

        start_node = next((node for node in self.nodes if node.puzzle_start), None)
        end_node = next((node for node in self.nodes if node.puzzle_end), None)

        path_nodes = set(self.total_path) if self.total_path else set()
        occupied_count = len(path_nodes)

        all_waypoints_in_grid = [node for node in self.nodes if node.waypoint]

        print(
            f"Occupied Nodes (Path): {occupied_count} ({occupied_count / total_nodes_generated:.1%})"
            if total_nodes_generated
            else "Occupied Nodes (Path): 0"
        )
        print(f"Total Waypoints in Grid: {len(all_waypoints_in_grid)}")

        # Start Waypoint Pattern/Stats Logic
        waypoint_labels = []
        last_wp_node = None  # Track the actual node to avoid duplicates

        if self.total_path:
            for node in self.total_path:
                is_waypoint = node.waypoint
                is_start = node.puzzle_start
                is_end = node.puzzle_end

                current_label = None
                if is_start:
                    current_label = "Start"
                    last_wp_node = node
                elif is_end:
                    current_label = "End"
                    last_wp_node = node
                elif is_waypoint:
                    if node != last_wp_node:
                        current_label = "M" if node.mounting else "N"
                        last_wp_node = node

                if current_label:
                    waypoint_labels.append(current_label)

            # Generate Symbolic Pattern
            symbolic_pattern_parts = []
            symbol_map = {
                "Start": "Start",
                "End": "End",
                "M": "|",
                "N": ".",
            }
            for label in waypoint_labels:
                symbolic_pattern_parts.append(symbol_map.get(label, "?"))
            symbolic_pattern = " ".join(symbolic_pattern_parts)
            print(f"Waypoint Pattern: {symbolic_pattern}")

            # Generate Gap Statistics
            gap_sizes = []
            current_n_count = 0
            found_first_mount = False

            for i, label in enumerate(waypoint_labels):
                if label == "N":
                    current_n_count += 1
                elif label == "M":
                    if not found_first_mount:
                        found_first_mount = True
                    else:
                        gap_sizes.append(current_n_count)
                    current_n_count = 0

            actual_mount_count = waypoint_labels.count("M")
            actual_random_count = waypoint_labels.count("N")

            print(
                f"Waypoint Stats: {actual_mount_count} mounting points, {actual_random_count} non-mounting points"
            )

        else:  # If no self.total_path
            print("Waypoint Stats: No path generated.")
        # End Waypoint Pattern/Stats Logic

        if start_node:
            print(
                f"Start Node X: {start_node.x:.1f}, Y: {start_node.y:.1f}, Z: {start_node.z:.1f}"
            )
        if end_node:
            print(
                f"End Node   X: {end_node.x:.1f}, Y: {end_node.y:.1f}, Z: {end_node.z:.1f}"
            )

        rect_count = sum(1 for node in self.nodes if node.in_rectangular_grid)
        circ_count = sum(1 for node in self.nodes if node.in_circular_grid)
        print(f"Node Grid Types: Rectangular={rect_count}, Circular={circ_count}")

        # Path Summary
        print("\n--- Path Summary ---")
        total_path_nodes = len(self.total_path) if self.total_path else 0
        num_segments = (
            len(self.path_architect.segments)
            if self.path_architect and self.path_architect.segments
            else 0
        )
        print(f"Total Path Length (nodes): {total_path_nodes}")
        print(f"Number of Segments: {num_segments}")
        if num_segments > 0 and total_path_nodes > 0:
            avg_nodes_per_segment = total_path_nodes / num_segments
            print(f"Average Nodes per Segment: {avg_nodes_per_segment:.1f}")

        # Segment Details
        if num_segments > 0:
            print("\n--- Segment Details ---")
            segments = self.path_architect.segments

            # Profile Type Distribution
            profile_counter = Counter(
                s.path_profile_type for s in segments if s.path_profile_type
            )
            print("Profile Type Distribution:")
            for profile_type, count in profile_counter.most_common():
                print(f"  - {profile_type.value}: {count} ({count / num_segments:.1%})")

            # Curve Model Distribution
            model_counter = Counter(s.curve_model for s in segments if s.curve_model)
            print("Curve Model Distribution:")
            for model, count in model_counter.most_common():
                print(f"  - {model.value}: {count} ({count / num_segments:.1%})")

            # Curve Type Distribution (Specific Curves)
            curve_type_counter = Counter(s.curve_type for s in segments if s.curve_type)
            print("Detected Curve Type Distribution:")
            if curve_type_counter:
                num_curved_segments = sum(curve_type_counter.values())
                num_straight_segments = num_segments - num_curved_segments
                for curve_type, count in curve_type_counter.most_common():
                    print(
                        f"  - {curve_type.value}: {count} ({count / num_segments:.1%})"
                    )
                num_straight_segments = max(0, num_straight_segments)
                print(
                    f"  - Straight (Implicit): {num_straight_segments} ({num_straight_segments / num_segments:.1%})"
                )
            else:
                print("  - All segments appear straight or undefined.")

            # Transition Type Distribution
            transition_counter = Counter(
                s.transition_type for s in segments if s.transition_type
            )
            print("Transition Type Distribution:")
            for transition, count in transition_counter.most_common():
                transition_name = (
                    transition.name if hasattr(transition, "name") else str(transition)
                )
                print(f"  - {transition_name}: {count} ({count / num_segments:.1%})")

        else:
            print("\n--- Path Segments ---")
            print("No path segments generated.")

        print("\n" + "=" * 30 + "\n")

    def _check_node_connectivity(self) -> None:
        """
        Verify every non-start node has ≥2 neighbours ie pruning nodes
        with ≤1 neighbour (isolated or leaf/ dead-end nodes).

        Pruning rules:
        - Repeatedly remove all non-start nodes whose neighbour count <= 1.
        This prevents dead-ends in the grid.
        - Keep the start node even if it ends up with ≤1 neighbour; warn about it.
        """
        max_report = 10
        total_pruned = 0
        iteration = 0

        while True:
            iteration += 1

            # Compute neighbour counts for the current node set
            degrees: dict[Node, int] = {}
            for n in self.nodes:
                neighbors = self.path_finder.get_neighbors(self, n)
                degrees[n] = len(neighbors)

            # Candidates: non-start nodes with <= 1 neighbour
            to_prune: list[Node] = [
                n for n, deg in degrees.items() if deg <= 1 and n is not self.start_node
            ]

            if not to_prune:
                break

            print(
                f"[Warning] Pruning {len(to_prune)} node(s) with ≤1 neighbour "
                f"[iteration {iteration}]"
            )
            for n in to_prune[:max_report]:
                tags = []
                if getattr(n, "mounting", False):
                    tags.append("mounting")
                if getattr(n, "waypoint", False):
                    tags.append("waypoint")
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                print(f"    - ({n.x:.1f}, {n.y:.1f}, {n.z:.1f}){tag_str}")
            if len(to_prune) > max_report:
                print(f"    … and {len(to_prune) - max_report} more")

            # Remove from nodes and node_dict
            for n in to_prune:
                self.nodes.remove(n)
                k = key3(n.x, n.y, n.z)
                if self.node_dict.get(k) is n:
                    del self.node_dict[k]

            total_pruned += len(to_prune)

        # Start node special case: warn if it has no neighbour
        if (
            self.start_node
            and len(self.path_finder.get_neighbors(self, self.start_node)) < 1
        ):
            print(
                "[Warning] Start node has no neighbour after pruning; pathfinding may fail."
            )

        if total_pruned > 0:
            print(
                f"[Info] Connectivity pruning complete. Removed {total_pruned} node(s)."
            )
