# puzzle/puzzle.py

import logging
import random
from collections import Counter, defaultdict
from typing import Optional

import numpy as np

from cad.path_architect import PathArchitect
from config import CaseShape, Config, PathProfileType
from logging_config import configure_logging
from obstacles.obstacle_manager import ObstacleManager
from puzzle.grid_layouts.grid_layout_box import BoxCasing
from puzzle.grid_layouts.grid_layout_cylinder import CylinderCasing
from puzzle.grid_layouts.grid_layout_sphere import SphereCasing
from puzzle.node import Node
from puzzle.path_finder import AStarPathFinder
from puzzle.utils.geometry import key3

configure_logging()
logger = logging.getLogger(__name__)


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
        # Lazily-populated cache keyed by the discretized z-plane so neighbor
        # lookups can jump straight to relevant circular nodes without scanning
        # the full node list.
        self._circular_nodes_by_plane: Optional[dict[int, list[Node]]] = None

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

    def get_circular_plane_level(self, z_value: float) -> int:
        """Return the rounded plane index for a given z coordinate."""

        if self.node_size == 0:
            return 0
        return int(round(z_value / self.node_size))

    def get_circular_nodes_by_plane(self) -> dict[int, list[Node]]:
        """Group circular nodes by their rounded z plane and cache the result."""

        if self._circular_nodes_by_plane is None:
            # Build circular nodes cache by grouping to snapped z-level
            plane_map: dict[int, list[Node]] = defaultdict(list)
            for node in self.nodes:
                if node.in_circular_grid:
                    plane_index = self.get_circular_plane_level(node.z)
                    plane_map[plane_index].append(node)
            self._circular_nodes_by_plane = plane_map

        return self._circular_nodes_by_plane

    def get_circular_nodes_for_level(self, z_value: float) -> list[Node]:
        """Return circular nodes on the plane that matches the provided z value."""

        plane_index = self.get_circular_plane_level(z_value)
        return self.get_circular_nodes_by_plane().get(plane_index, [])

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
            logger.warning(
                "Reduced number of waypoints to %s due to limited unoccupied nodes.",
                num_waypoints,
            )

        rng = random.Random(self.seed)

        waypoints: list[Node] = []
        for _ in range(num_waypoints):
            # Generate candidates
            candidates: list[Node] = rng.sample(
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
                logger.warning("No suitable candidate found for waypoint selection.")

    def print_puzzle_info(self) -> None:
        """Log detailed information about the generated puzzle configuration and results."""

        logger.info("%s", "=" * 30)
        logger.info("      PUZZLE INFORMATION")
        logger.info("%s", "=" * 30)

        # Configuration Summary
        logger.info("--- Configuration Summary ---")
        logger.info("Seed: %s", self.seed)
        logger.info("Case Shape: %s", self.case_shape.value)
        if hasattr(Config.Puzzle, "CASE_MANUFACTURER"):
            logger.info(
                "Manufacturer Profile: %s", Config.Puzzle.CASE_MANUFACTURER.value
            )
        if hasattr(Config.Puzzle, "THEME"):
            logger.info("Theme: %s", Config.Puzzle.THEME.value)
        logger.info("Node Size (mm): %s", self.node_size)
        logger.info("Ball Diameter (mm): %s", Config.Puzzle.BALL_DIAMETER)
        if isinstance(self.casing, SphereCasing):
            logger.info("Sphere Diameter (mm): %s", Config.Sphere.SPHERE_DIAMETER)
        elif isinstance(self.casing, BoxCasing):
            logger.info(
                "Box Dimensions (LxWxH mm): %s x %s x %s",
                Config.Box.LENGTH,
                Config.Box.WIDTH,
                Config.Box.HEIGHT,
            )
        logger.info("Requested Waypoints: %s", Config.Puzzle.NUMBER_OF_WAYPOINTS)

        # Allowed Settings
        logger.info("")
        logger.info("--- Allowed Path Settings (from Config) ---")
        logger.info(
            "Allowed Pathsegment Design Strategies: %s",
            ", ".join(m.value for m in Config.Path.PATH_SEGMENT_DESIGN_STRATEGY),
        )
        logger.info(
            "Allowed Profile Types: %s",
            ", ".join(p.value for p in Config.Path.PATH_PROFILE_TYPES),
        )
        logger.info(
            "Allowed Curve Types for Detection: %s",
            ", ".join(c.value for c in Config.Path.PATH_CURVE_TYPE),
        )

        # Node Grid Summary
        logger.info("")
        logger.info("--- Node Grid Summary ---")
        total_nodes_generated = len(self.nodes)
        logger.info("Total Nodes Generated: %s", total_nodes_generated)

        start_node = next((node for node in self.nodes if node.puzzle_start), None)
        end_node = next((node for node in self.nodes if node.puzzle_end), None)

        path_nodes = set(self.total_path) if self.total_path else set()
        occupied_count = len(path_nodes)

        all_waypoints_in_grid = [node for node in self.nodes if node.waypoint]

        if total_nodes_generated:
            occupied_pct = occupied_count / total_nodes_generated * 100
            logger.info(
                "Occupied Nodes (Path): %s (%.1f%%)", occupied_count, occupied_pct
            )
        else:
            logger.info("Occupied Nodes (Path): 0")
        logger.info("Total Waypoints in Grid: %s", len(all_waypoints_in_grid))

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
                elif is_waypoint and node != last_wp_node:
                    current_label = "M" if node.mounting else "N"
                    last_wp_node = node

                if current_label:
                    waypoint_labels.append(current_label)

            # Generate Symbolic Pattern
            symbol_map = {
                "Start": "Start",
                "End": "End",
                "M": "|",
                "N": ".",
            }
            symbolic_pattern = " ".join(
                symbol_map.get(label, "?") for label in waypoint_labels
            )
            logger.info("Waypoint Pattern: %s", symbolic_pattern)

            # Generate Gap Statistics
            gap_sizes = []
            current_n_count = 0
            found_first_mount = False

            for label in waypoint_labels:
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

            logger.info(
                "Waypoint Stats: %s mounting points, %s non-mounting points",
                actual_mount_count,
                actual_random_count,
            )

        else:  # If no self.total_path
            logger.info("Waypoint Stats: No path generated.")
        # End Waypoint Pattern/Stats Logic

        if start_node:
            logger.info(
                "Start Node X: %.1f, Y: %.1f, Z: %.1f",
                start_node.x,
                start_node.y,
                start_node.z,
            )
        if end_node:
            logger.info(
                "End Node   X: %.1f, Y: %.1f, Z: %.1f",
                end_node.x,
                end_node.y,
                end_node.z,
            )

        rect_count = sum(1 for node in self.nodes if node.in_rectangular_grid)
        circ_count = sum(1 for node in self.nodes if node.in_circular_grid)
        logger.info(
            "Node Grid Types: Rectangular=%s, Circular=%s", rect_count, circ_count
        )

        # Path Summary
        logger.info("")
        logger.info("--- Path Summary ---")
        total_path_nodes = len(self.total_path) if self.total_path else 0
        num_segments = (
            len(self.path_architect.segments)
            if self.path_architect and self.path_architect.segments
            else 0
        )
        logger.info("Total Path Length (nodes): %s", total_path_nodes)
        logger.info("Number of Segments: %s", num_segments)
        if num_segments > 0 and total_path_nodes > 0:
            avg_nodes_per_segment = total_path_nodes / num_segments
            logger.info("Average Nodes per Segment: %.1f", avg_nodes_per_segment)

        # Segment Details
        if num_segments > 0:
            logger.info("")
            logger.info("--- Segment Details ---")
            segments = self.path_architect.segments

            # Profile Type Distribution
            logical_segment_profiles: dict[int, Optional[PathProfileType]] = {}
            for segment in segments:
                idx = segment.main_index
                if idx not in logical_segment_profiles:
                    logical_segment_profiles[idx] = segment.path_profile_type
                elif (
                    logical_segment_profiles[idx] is None
                    and segment.path_profile_type is not None
                ):
                    logical_segment_profiles[idx] = segment.path_profile_type

            num_logical_segments = len(logical_segment_profiles)
            profile_counter = Counter(
                profile
                for profile in logical_segment_profiles.values()
                if profile is not None
            )
            missing_profile_count = sum(
                1 for profile in logical_segment_profiles.values() if profile is None
            )

            logger.info("Profile Type Distribution:")
            if num_logical_segments == 0:
                logger.info("  No logical segments with assigned profile types.")
            else:
                for profile_type, count in profile_counter.most_common():
                    logger.info(
                        "  - %s: %s (%.1f%%)",
                        profile_type.value,
                        count,
                        (count / num_logical_segments) * 100,
                    )
                if missing_profile_count:
                    logger.info(
                        "  - Unknown: %s (%.1f%%)",
                        missing_profile_count,
                        (missing_profile_count / num_logical_segments) * 100,
                    )

            # Pathsegment Design Strategy Distribution
            model_counter = Counter(
                s.design_strategy for s in segments if s.design_strategy
            )
            logger.info("Design Strategy Distribution:")
            for model, count in model_counter.most_common():
                logger.info(
                    "  - %s: %s (%.1f%%)",
                    model.value,
                    count,
                    (count / num_segments) * 100,
                )

            # Curve Type Distribution (Specific Curves)
            curve_type_counter = Counter(s.curve_type for s in segments if s.curve_type)
            logger.info("Detected Curve Type Distribution:")
            if curve_type_counter:
                num_curved_segments = sum(curve_type_counter.values())
                num_straight_segments = max(0, num_segments - num_curved_segments)
                for curve_type, count in curve_type_counter.most_common():
                    logger.info(
                        "  - %s: %s (%.1f%%)",
                        curve_type.value,
                        count,
                        (count / num_segments) * 100,
                    )
                logger.info(
                    "  - Straight (Implicit): %s (%.1f%%)",
                    num_straight_segments,
                    (num_straight_segments / num_segments) * 100,
                )
            else:
                logger.info("  - All segments appear straight or undefined.")

            # Transition Type Distribution
            transition_counter = Counter(
                s.transition_type for s in segments if s.transition_type
            )
            logger.info("Transition Type Distribution:")
            for transition, count in transition_counter.most_common():
                transition_name = (
                    transition.name if hasattr(transition, "name") else str(transition)
                )
                logger.info(
                    "  - %s: %s (%.1f%%)",
                    transition_name,
                    count,
                    (count / num_segments) * 100,
                )

        else:
            logger.info("")
            logger.info("--- Path Segments ---")
            logger.info("No path segments generated.")

        logger.info("")
        logger.info("%s", "=" * 30)

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

            logger.warning(
                "Pruning %s node(s) with ≤1 neighbour [iteration %s]",
                len(to_prune),
                iteration,
            )
            for n in to_prune[:max_report]:
                tags = []
                if getattr(n, "mounting", False):
                    tags.append("mounting")
                if getattr(n, "waypoint", False):
                    tags.append("waypoint")
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                logger.warning(
                    "    - (%.1f, %.1f, %.1f)%s",
                    n.x,
                    n.y,
                    n.z,
                    tag_str,
                )
            if len(to_prune) > max_report:
                logger.warning("    … and %s more", len(to_prune) - max_report)

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
            logger.warning(
                "Start node has no neighbour after pruning; pathfinding may fail."
            )

        if total_pruned > 0:
            logger.info(
                "Connectivity pruning complete. Removed %s node(s).", total_pruned
            )
