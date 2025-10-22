# cad/path_architect.py

import logging
import random
from typing import Dict, Optional

from build123d import Transition, Vector

import config
from cad.path_profile_type_shapes import (
    ACCENT_REGISTRY,
    SUPPORT_REGISTRY,
    PathProfileType,
)
from cad.path_segment import PathSegment, _node_to_vector, is_same_location, midpoint
from config import Config, PathCurveModel, PathCurveType
from logging_config import configure_logging
from obstacles.obstacle import Obstacle
from puzzle.node import Node
from puzzle.utils.geometry import snap

from . import curve_detection

configure_logging()
logger = logging.getLogger(__name__)


def _format_node(node: Optional[Node]) -> str:
    if node is None:
        return "None"
    return f"({node.x:.3f}, {node.y:.3f}, {node.z:.3f})"


def _format_node_list(nodes: list[Node]) -> str:
    return "[" + ", ".join(_format_node(node) for node in nodes) + "]"


class PathArchitect:
    def __init__(self, nodes: list[Node], obstacles: Optional[list["Obstacle"]] = None):
        # Inputs
        self.nodes = nodes
        self.segments: list[PathSegment] = []
        self.main_index_counter = 1  # Main index counter
        self.secondary_index_counters = {}  # Dictionary to track secondary indices per main_index

        # TODO, clean up, better understandable
        self.obstacle_by_entry: Dict[Node, "Obstacle"] = {}
        if obstacles:
            self.obstacle_by_entry = {
                obstacle.entry_node: obstacle
                for obstacle in obstacles
                if getattr(obstacle, "entry_node", None) is not None
            }

        # Configuration parameters
        self.waypoint_change_interval = Config.Puzzle.WAYPOINT_CHANGE_INTERVAL
        self.node_size = Config.Puzzle.NODE_SIZE
        self.path_profile_types = list(Config.Path.PATH_PROFILE_TYPES)
        self.path_curve_models = list(Config.Path.PATH_CURVE_MODEL)
        self.nozzle_diameter = config.Manufacturing.NOZZLE_DIAMETER
        self.seed = Config.Puzzle.SEED
        random.seed(self.seed)  # Set the random seed for reproducibility

        # Process the path
        self.split_path_into_segments()

        self.assign_path_properties()

        self.detect_curves_and_adjust_segments()

        self.adjust_segments()

        self.create_start_ramp()

        self.create_finish_box()

        self.assign_path_transition_types()

        self.create_support_materials()

        self.accent_color_paths()

        self.reindex_segments()

    def split_path_into_segments(self):
        current_segment_nodes = []
        waypoint_counter = 0

        nodes_length = len(self.nodes)

        def log_segment_creation(reason: str, nodes: list[Node]):
            logger.debug(
                "split_path_into_segments: creating segment main_index=%s waypoint_counter=%s reason=%s nodes=%s",
                self.main_index_counter,
                waypoint_counter,
                reason,
                _format_node_list(nodes),
            )

        # Handle the first two nodes as a special segment, the start ramp
        if nodes_length >= 2:
            # Create a segment with the first two nodes
            first_two_nodes = self.nodes[:2]
            segment = PathSegment(first_two_nodes, main_index=self.main_index_counter)
            logger.debug(
                "split_path_into_segments: creating initial start ramp main_index=%s nodes=%s",
                self.main_index_counter,
                _format_node_list(first_two_nodes),
            )
            self.segments.append(segment)
            self.main_index_counter += 1
            # Start processing from the third node
            node_iter = self.nodes[2:]
        else:
            # If less than two nodes, include all nodes
            node_iter = self.nodes

        pending_exit_to_skip: Node | None = (
            None  # skip the next node if it is this obstacle's mapped exit
        )

        for node in node_iter:
            # If we just inserted obstacle triplet, the very next node in total_path is the teleported exit.
            if pending_exit_to_skip is not None and node is pending_exit_to_skip:
                pending_exit_to_skip = None
                continue  # skip adding this one; the EXIT SINGLE already starts here

            current_segment_nodes.append(node)

            obstacle = self.obstacle_by_entry.get(node)
            if obstacle is not None:
                # Close any open segment before the obstacle
                if len(current_segment_nodes) > 1:
                    log_segment_creation(
                        "pre-obstacle closure", current_segment_nodes
                    )
                    self._create_segment(
                        current_segment_nodes, main_index=self.main_index_counter
                    )
                    self.main_index_counter += 1
                elif current_segment_nodes and self.segments:
                    self.segments[-1].nodes.extend(current_segment_nodes)
                current_segment_nodes = []

                # Insert the 3 obstacle segments with shared main_index and incremental secondary_index
                obstacle_segments = self._create_obstacle_segments(
                    obstacle, main_index=self.main_index_counter
                )
                if obstacle_segments:
                    logger.debug(
                        "split_path_into_segments: splicing obstacle segments for %s at main_index=%s segments=%s",
                        getattr(obstacle, "name", obstacle.__class__.__name__),
                        self.main_index_counter,
                        [
                            _format_node_list(segment.nodes)
                            for segment in obstacle_segments
                        ],
                    )
                    self.segments.extend(obstacle_segments)
                    self.main_index_counter += 1
                    # ensure we don't immediately start another segment at the teleported exit
                    pending_exit_to_skip = obstacle.exit_node
                continue

            if node.waypoint and not node.mounting:
                waypoint_counter += 1
                if waypoint_counter % self.waypoint_change_interval == 0:
                    # Create a segment with collected nodes
                    log_segment_creation(
                        "waypoint interval reached", current_segment_nodes
                    )
                    self._create_segment(
                        current_segment_nodes, main_index=self.main_index_counter
                    )
                    self.main_index_counter += 1
                    current_segment_nodes = []

        if current_segment_nodes:
            # Create a segment with any remaining nodes
            log_segment_creation("final remainder", current_segment_nodes)
            self._create_segment(
                current_segment_nodes, main_index=self.main_index_counter
            )
            self.main_index_counter += 1

    def _create_segment(self, nodes: list[Node], main_index: int):
        segment = PathSegment(nodes, main_index=main_index)
        self.segments.append(segment)

    def _create_obstacle_segments(
        self, obstacle: "Obstacle", main_index: int
    ) -> list[PathSegment]:
        """Create [entry SINGLE] → [main locked] → [exit SINGLE] for one obstacle."""
        segments: list[PathSegment] = []

        # World-place helper nodes (copy first to avoid mutating obstacle state)
        # TODO, move this to obstacle somehow
        def world_nodes(local_nodes: list[Node]) -> list[Node]:
            if not local_nodes:
                return []
            copies = [
                Node(
                    n.x,
                    n.y,
                    n.z,
                    in_circular_grid=n.in_circular_grid,
                    in_rectangular_grid=n.in_rectangular_grid,
                )
                for n in local_nodes
            ]
            obstacle.get_placed_node_coordinates(copies)
            for node in copies:
                node.x = snap(round(node.x / self.node_size) * self.node_size)
                node.y = snap(round(node.y / self.node_size) * self.node_size)
                node.z = snap(round(node.z / self.node_size) * self.node_size)
            return copies

        entry_world = world_nodes(obstacle.entry_path_segment.nodes)
        exit_world = world_nodes(obstacle.exit_path_segment.nodes)

        # Entry segment single
        if len(entry_world) >= 2:
            entry_seg = PathSegment(
                nodes=entry_world,
                main_index=main_index,
                secondary_index=0,
            )
            entry_seg.copy_attributes_from(obstacle.main_path_segment)
            entry_seg.curve_model = PathCurveModel.SINGLE
            segments.append(entry_seg)

        # Main segment, the obstacle path
        if obstacle.main_path_segment.path is None:
            obstacle.create_obstacle_geometry()
        located_path = obstacle.main_path_segment.path
        # TODO, check this located stuff
        if obstacle.location is not None and hasattr(located_path, "located"):
            located_path = located_path.located(obstacle.location)

        # Minimal 2-node backbone for continuity and visualization
        if entry_world and exit_world:
            main_nodes = [entry_world[-1], exit_world[0]]

        main_seg = obstacle.main_path_segment
        main_seg.path = located_path
        if located_path is not None:
            main_seg.path = located_path
            if (
                hasattr(main_seg, "path_edge_only")
                and main_seg.path_edge_only is not None
            ):
                # Guarded update: re-use original object when no world transform exists.
                main_seg.path_edge_only = located_path

        main_seg.nodes = main_nodes
        main_seg.main_index = main_index
        main_seg.secondary_index = len(segments)
        main_seg.is_obstacle = True
        main_seg.lock_path = True  # keep the placed obstacle geometry
        main_seg.curve_model = PathCurveModel.OBSTACLE
        main_seg.transition_type = obstacle.main_path_segment.transition_type

        segments.append(main_seg)

        # Exit segment single
        if len(exit_world) >= 2:
            exit_seg = PathSegment(
                nodes=exit_world,
                main_index=main_index,
                secondary_index=len(segments),
            )
            exit_seg.copy_attributes_from(obstacle.main_path_segment)
            exit_seg.curve_model = PathCurveModel.SINGLE
            # not locked
            segments.append(exit_seg)

        return segments

    def _harmonise_circular_transitions(self) -> None:
        """
        Fix mismatches where an arc meets a straight run at a segment boundary.
        """
        for idx in range(len(self.segments) - 1):
            seg_a, seg_b = self.segments[idx], self.segments[idx + 1]

            # Only do adjustment if we are handling the end of of main segment and the start of another
            if seg_a.main_index == seg_b.main_index:
                continue

            # need at least [.., end] in seg-A  +  [start, …] in seg-B
            if len(seg_a.nodes) < 2 or len(seg_b.nodes) < 2:
                continue

            second_last_a = seg_a.nodes[-2]
            end_a = seg_a.nodes[-1]
            start_b = seg_b.nodes[0]

            # pattern A (straight -> arc)
            if (
                end_a.in_circular_grid
                and start_b.in_circular_grid
                and len(seg_a.nodes) >= 2
                and not second_last_a.in_circular_grid
            ):
                logger.debug(
                    "Harmonising circular transition pattern A for segments %s.%s and %s.%s",
                    seg_a.main_index,
                    seg_a.secondary_index,
                    seg_b.main_index,
                    seg_b.secondary_index,
                )

                # straight midpoint between the non-circular neighbour and the
                # circular boundary node
                P = _node_to_vector(second_last_a)  # non-circular
                Q = _node_to_vector(start_b)  # circular boundary
                mid = midpoint(P, Q, circular=False)

                bridge = Node(mid.X, mid.Y, mid.Z)
                bridge.in_rectangular_grid = second_last_a.in_rectangular_grid

                # New connecting segment  (bridge -> first B)
                new_seg = PathSegment(
                    [bridge, start_b],
                    main_index=seg_b.main_index,
                    secondary_index=seg_b.secondary_index - 1,
                )
                new_seg.copy_attributes_from(seg_b)  # inherit profile etc.
                new_seg.curve_model = PathCurveModel.COMPOUND
                new_seg.curve_type = None  # No longer arc

                # Insert immediately after seg-A, before seg-B
                self.segments.insert(idx + 1, new_seg)

                # Update end of seg-A
                seg_a.nodes[-1] = bridge

                continue  # skip re-checking pair

            # pattern B (arc -> straight)
            if (
                end_a.in_circular_grid
                and start_b.in_circular_grid
                and len(seg_b.nodes) >= 2
                and not seg_b.nodes[1].in_circular_grid
            ):
                logger.debug(
                    "Harmonising circular transition pattern B for segments %s.%s and %s.%s",
                    seg_a.main_index,
                    seg_a.secondary_index,
                    seg_b.main_index,
                    seg_b.secondary_index,
                )

                second_b = seg_b.nodes[1]

                # straight midpoint between the circular boundary and its neighbour
                P = _node_to_vector(end_a)
                Q = _node_to_vector(second_b)
                mid = midpoint(P, Q, circular=False)

                bridge = Node(mid.X, mid.Y, mid.Z)
                bridge.in_rectangular_grid = seg_b.nodes[1].in_rectangular_grid

                # New connecting segment (end-A → bridge)
                new_seg = PathSegment(
                    [end_a, bridge],
                    main_index=seg_a.main_index,
                    secondary_index=seg_a.secondary_index + 1,
                )

                # inherit useful attributes from seg-A (profile, transition, …)
                new_seg.copy_attributes_from(seg_a)
                new_seg.curve_model = PathCurveModel.COMPOUND
                new_seg.curve_type = None

                # Insert immediately after seg-A, before seg-B
                self.segments.insert(idx + 1, new_seg)

                # Update start of seg-B
                seg_b.nodes[0] = bridge

                continue  # skip re-checking pair

    def assign_path_properties(self):
        # Randomly assign path profile types and path curve models to segments
        previous_profile_type = None
        previous_curve_model = None

        obstacle_main_indices = {
            segment.main_index for segment in self.segments if segment.is_obstacle
        }
        obstacle_profile_type_by_main: dict[int, PathProfileType] = {}

        for segment in self.segments:
            # Check if the segment contains any mounting node
            has_mounting_node = any(node.mounting for node in segment.nodes)
            if has_mounting_node:
                # For mounting segments, only select specific types, ensures linking with bridge
                # Respect config, if none of these are allowed, fall back to U_SHAPE.
                candidates_for_mounting = [
                    PathProfileType.O_SHAPE,
                    PathProfileType.U_SHAPE,
                    PathProfileType.U_SHAPE_ADJUSTED_HEIGHT,
                ]
                # Filter against allowed types from config
                available_profile_types = [
                    profile_type
                    for profile_type in candidates_for_mounting
                    if profile_type in self.path_profile_types
                ]
                # Fallback if nothing allowed
                if not available_profile_types:
                    available_profile_types = [PathProfileType.U_SHAPE]

                available_curve_models = [PathCurveModel.COMPOUND]
            else:
                # For other segments, use all available types
                available_profile_types = self.path_profile_types.copy()
                available_curve_models = self.path_curve_models.copy()

            # Determine whether this segment is part of an obstacle triplet and, if so,
            # whether a shared profile has already been chosen for its main_index.
            is_obstacle_group = segment.main_index in obstacle_main_indices
            shared_profile = obstacle_profile_type_by_main.get(segment.main_index)

            # Exclude previous types if possible when we are about to choose a new profile.
            if shared_profile is None:
                if (
                    previous_profile_type in available_profile_types
                    and len(available_profile_types) > 1
                ):
                    available_profile_types.remove(previous_profile_type)

            # For path curve model
            if (
                previous_curve_model in available_curve_models
                and len(available_curve_models) > 1
            ):
                available_curve_models.remove(previous_curve_model)

            # Select random types from the available lists
            # TODO don't set for obstacle paths, altough path is not adjusted... Improve a bit more
            if shared_profile is not None:
                segment.path_profile_type = shared_profile
            else:
                segment.path_profile_type = random.choice(available_profile_types)
                if is_obstacle_group:
                    obstacle_profile_type_by_main[segment.main_index] = (
                        segment.path_profile_type
                    )
            # IMPORTANT: do not overwrite a curve_model that is already set
            if segment.curve_model is None:
                if segment.is_obstacle:
                    # Only the locked main obstacle needs to be COMPOUND by default
                    segment.curve_model = PathCurveModel.COMPOUND
                else:
                    segment.curve_model = random.choice(available_curve_models)

            # Update previous types for next round
            previous_profile_type = segment.path_profile_type
            previous_curve_model = segment.curve_model

            # If applicalbe, apply forced profile for this main_index
            # Intentionally placed last as override so it does not interfer
            forced = Config.Path.PATH_PROFILE_TYPE_OVERRIDES.get(segment.main_index)
            if forced:
                logger.info(
                    "[Config Override] Segment %s → forcing profile %s",
                    segment.main_index,
                    forced.value,
                )
                segment.path_profile_type = forced

    def assign_path_transition_types(self):
        # Initialize the transition tracker
        transition = Transition.ROUND  # Starting with 'round'

        for segment in self.segments:
            # Check if segment already has a transition type, skip if so, also covers obstacles
            # TODO, it seems certain segments do not properly copy node properties, thus waypoint nodes do not get copied. info was lost
            if segment.transition_type is not None:
                continue

            # Determine the transition type for the segment
            if segment.path_profile_type in [
                PathProfileType.V_SHAPE,
                PathProfileType.O_SHAPE,
            ]:
                segment.transition_type = Transition.ROUND
            elif segment.curve_model == PathCurveModel.SINGLE:
                # Make spline SINGLE connection segments more fluent
                segment.transition_type = Transition.ROUND
            else:
                # Flip the next_transition for the subsequent else case,
                # only for first secondary index ie 0 as that determines it for the whole segment
                if segment.secondary_index == 0:
                    transition = (
                        Transition.ROUND
                        if transition == Transition.RIGHT
                        else Transition.RIGHT
                    )
                # Alternately choose between 'right' and 'round'
                segment.transition_type = transition

    def detect_curves_and_adjust_segments(self):
        i = 0
        curve_id_counter = 1  # Initialize the curve ID counter
        while i < len(self.segments):
            segment = self.segments[i]
            if segment.is_obstacle:
                i += 1
                continue
            if segment.curve_model == PathCurveModel.COMPOUND:
                sub_segments = [segment]
                new_split_segments = []
                for sub_segment in sub_segments:
                    if len(sub_segment.nodes) > 1:
                        # Pass the curve_id_counter to detect_curves
                        curve_id_counter = curve_detection.detect_curves(
                            sub_segment.nodes, curve_id_counter
                        )
                        split_segments = self._split_segment_by_detected_curves(
                            sub_segment.nodes, sub_segment
                        )
                        new_split_segments.extend(split_segments)
                    else:
                        new_split_segments.append(sub_segment)
                # Replace the original segment with new_split_segments
                self.segments[i : i + 1] = new_split_segments
                i += len(new_split_segments)
            elif segment.curve_model == PathCurveModel.SPLINE:
                # Split the spline segment into parts
                previous_segment = self.segments[i - 1] if i > 0 else None
                next_segment = (
                    self.segments[i + 1] if i + 1 < len(self.segments) else None
                )
                new_segments = self._split_spline_segment(
                    segment,
                    previous_segment=previous_segment,
                    next_segment=next_segment,
                )
                self.segments[i : i + 1] = new_segments
                i += len(new_segments)
            else:
                i += 1

    def _split_segment_by_detected_curves(
        self, nodes: list[Node], original_segment: PathSegment
    ) -> list[PathSegment]:
        """
        Splits a given path segment into multiple segments based on detected curves and ensures continuity
        between adjacent curves by creating connecting segments when necessary.

        This method processes the list of nodes from the original segment, detects changes in curve types
        and curve IDs, and creates new segments accordingly. When multiple curves are adjacent, it creates
        a connecting segment between them to maintain path continuity.

        Args:
            nodes (list[Node]): The list of nodes with curve detection information.
            original_segment: The original path segment to be split.

        Returns:
            list[PathSegment]: A list of new path segments resulting from splitting the original segment.
        """
        split_segments = []
        current_segment_nodes = []
        current_curve_type = None
        current_curve_id = None  # Initialize the current curve ID

        main_index = original_segment.main_index
        # Retrieve or initialize the secondary index counter for this main index
        secondary_index_counter = self.secondary_index_counters.get(main_index, 0)

        for idx, node in enumerate(nodes):
            node_curve_id = getattr(
                node, "curve_id", None
            )  # Get curve ID, default to None if not present

            # Check if we need to start a new segment due to a change in curve type or curve ID
            if (node.path_curve_type != current_curve_type) or (
                node_curve_id != current_curve_id
            ):
                if current_segment_nodes:
                    # Finish the current segment and add it to the list of split segments
                    segment = PathSegment(
                        current_segment_nodes,
                        main_index=main_index,
                        secondary_index=secondary_index_counter,
                    )
                    secondary_index_counter += 1
                    # Copy attributes from the original segment to maintain consistency
                    segment.path_profile_type = original_segment.path_profile_type
                    segment.curve_model = original_segment.curve_model
                    segment.curve_type = current_curve_type
                    segment.transition_type = original_segment.transition_type
                    split_segments.append(segment)

                    # Create a connecting segment only when transitioning between different curves
                    if (
                        current_curve_id is not None
                        and node_curve_id is not None
                        and current_curve_id != node_curve_id
                    ):
                        # Use the last node of the previous segment and the current node to create the connecting segment
                        start_node = current_segment_nodes[-1]
                        end_node = node
                        connecting_nodes = [start_node, end_node]
                        connecting_segment = PathSegment(
                            connecting_nodes,
                            main_index=main_index,
                            secondary_index=secondary_index_counter,
                        )
                        secondary_index_counter += 1
                        # Set attributes for the connecting segment
                        connecting_segment.path_profile_type = (
                            original_segment.path_profile_type
                        )
                        connecting_segment.curve_model = (
                            PathCurveModel.COMPOUND
                        )  # Assuming a straight line
                        connecting_segment.curve_type = None  # No specific curve type
                        connecting_segment.transition_type = (
                            original_segment.transition_type
                        )
                        split_segments.append(connecting_segment)

                    # Reset current_segment_nodes for the next segment
                    current_segment_nodes = []

                # Update the current curve type and curve ID to reflect the new segment
                current_curve_type = node.path_curve_type
                current_curve_id = node_curve_id

            # Add the current node to the current segment nodes
            current_segment_nodes.append(node)

        # After processing all nodes, check if there is a segment to be added
        if current_segment_nodes:
            # Finish the last segment and add it to the list of split segments
            segment = PathSegment(
                current_segment_nodes,
                main_index=main_index,
                secondary_index=secondary_index_counter,
            )
            secondary_index_counter += 1
            # Copy attributes from the original segment
            segment.path_profile_type = original_segment.path_profile_type
            segment.curve_model = original_segment.curve_model
            segment.curve_type = current_curve_type
            segment.transition_type = original_segment.transition_type
            split_segments.append(segment)

        # Update the secondary index counter for the main index
        self.secondary_index_counters[main_index] = secondary_index_counter

        return split_segments

    def adjust_segments(self):
        """
        Align segment end-points

        Special considertation for any arc segment that require a
        new segment in front for bridging

        Special considertation for any SINGLE-model segment that mixes
        circular and non-circular nodes.

        TODO It's a tad messy to make this adjustment after segments have already split,
        this code could use a refactor.
        New segments ie not adjusting existing segments needs to happen somewhere else then in segment adjustment
        """

        # Remove duplicates within tolerance
        def dedup(nodes):
            uniq = []
            for n in nodes:
                if not uniq or not is_same_location(
                    _node_to_vector(n), _node_to_vector(uniq[-1])
                ):
                    uniq.append(n)
            return uniq

        previous_end = None
        previous_curve = None
        i = 0
        while i < len(self.segments):
            segment = self.segments[i]
            inserted_bridge = False

            # Bridge prior to curved segment
            # If this segment has a curve_type (so it can't be adjusted)
            # but its first node doesn’t line up with previous_end, insert a bridge.
            # This situation technically only occurs with the first segment
            # coming outside the circular node ring ie at the start of the puzzle
            if previous_end is not None and segment.curve_type is not None:
                if not is_same_location(
                    _node_to_vector(previous_end), _node_to_vector(segment.nodes[0])
                ):
                    target_segment = segment
                    bridge = PathSegment(
                        nodes=[previous_end, segment.nodes[0]],
                        main_index=segment.main_index,
                        secondary_index=segment.secondary_index,
                    )
                    bridge.copy_attributes_from(segment)
                    bridge.curve_model = PathCurveModel.COMPOUND

                    # Decide bridge curve type from the endpoints
                    a_circ = previous_end.in_circular_grid
                    b_circ = segment.nodes[0].in_circular_grid
                    bridge.curve_type = (
                        PathCurveType.ARC
                        if (a_circ and b_circ)
                        else PathCurveType.STRAIGHT
                    )

                    logger.debug(
                        "adjust_segments: inserting bridging segment before main_index=%s secondary_index=%s from %s to %s as %s",
                        target_segment.main_index,
                        target_segment.secondary_index,
                        _format_node(previous_end),
                        _format_node(target_segment.nodes[0]),
                        bridge.curve_type,
                    )

                    # Insert the bridge before the current segment
                    self.segments.insert(i, bridge)
                    segment = bridge
                    inserted_bridge = True

                    # Bridge’s end is the new “previous_end”
                    previous_end = bridge.nodes[-1]
                    previous_curve = bridge.curve_type

            # Regular adjustment
            next_start = (
                self.segments[i + 1].nodes[0] if i + 1 < len(self.segments) else None
            )
            next_curve = (
                self.segments[i + 1].curve_type if i + 1 < len(self.segments) else None
            )

            logger.debug(
                "adjust_segments: handing %ssegment main_index=%s secondary_index=%s to adjust_start_and_endpoints with previous_end=%s next_start=%s previous_curve=%s next_curve=%s",
                "bridge " if inserted_bridge else "",
                segment.main_index,
                segment.secondary_index,
                _format_node(previous_end),
                _format_node(next_start),
                previous_curve,
                next_curve,
            )

            segment.adjust_start_and_endpoints(
                self.node_size,
                previous_end,
                next_start,
                previous_curve,
                next_curve,
            )

            # Split mixed SINGLE segments
            if segment.curve_model == PathCurveModel.SINGLE:
                uniq_nodes = dedup(segment.nodes)
                if len(uniq_nodes) > 2:
                    circ_flags = [n.in_circular_grid for n in uniq_nodes]
                    if any(circ_flags) and not all(circ_flags):
                        new_segments = []
                        for k in range(len(uniq_nodes) - 1):
                            pair = [uniq_nodes[k], uniq_nodes[k + 1]]
                            is_circ = all(n.in_circular_grid for n in pair)
                            new_segments.append(
                                self.make_circular_run(segment, pair, is_circ)
                            )

                        # substitute the original with the new chain
                        self.segments[i : i + 1] = new_segments

                        # advance cursor to *after* the inserted runs
                        last = new_segments[-1]
                        previous_end = last.nodes[-1]
                        previous_curve = last.curve_type
                        i += len(new_segments)
                        continue  # restart main loop

            # Proceed with next original segment
            if segment.nodes:
                previous_end = segment.nodes[-1]
                previous_curve = segment.curve_type
            i += 1

        # Ensure segments don't start/end at a change between circular and straight or vice versa
        self._harmonise_circular_transitions()

    def create_start_ramp(self):
        # This method finds the segment containing the start node and creates the start ramp

        # TODO this method does so little after update, could set U shape is path assignment?
        # Setting the path profile here is only an indicator for the puzzle, as the path builder
        # uses hardcoded values

        # Find the segment that contains the puzzle start node
        start_segment = None
        for segment in self.segments:
            for node in segment.nodes:
                if node.puzzle_start:
                    start_segment = segment
                    break  # Exit the inner loop once the start node is found
            if start_segment:
                break  # Exit the outer loop once the start segment is identified

        if start_segment:
            # Set the path profile type to u shape for the start segment
            start_segment.path_profile_type = PathProfileType.U_SHAPE

    def create_finish_box(self):
        # Locate the segment + index of the puzzle_end node
        end_segment = None
        end_idx = None
        for seg in self.segments:
            for i, n in enumerate(seg.nodes):
                if n.puzzle_end:
                    end_segment = seg
                    end_idx = i
                    break
            if end_segment:
                break
        # Nothing to do if we didn’t find a proper end with at least two nodes
        if end_segment is None or end_idx is None or end_idx < 1:
            return

        # Grab the two last nodes
        last_node = end_segment.nodes[end_idx]
        prev_node = end_segment.nodes[end_idx - 1]

        # Compute the direction, depending on circular or rectangular nodes
        P = Vector(prev_node.x, prev_node.y, prev_node.z)
        Q = Vector(last_node.x, last_node.y, last_node.z)

        if prev_node.in_circular_grid and last_node.in_circular_grid:
            # on a circle → true tangent
            R = Vector(Q.X, Q.Y, 0)
            tangent = Vector(-R.Y, R.X, 0).normalized()
            travel = (Q - P).normalized()
            if travel.dot(tangent) < 0:
                tangent = -tangent
        else:
            tangent = (Q - P).normalized()

        # Extend by half the node size
        ext_len = self.node_size / 2.0
        Q_ext = Q + tangent * ext_len

        # Clear old end-flags, update new flags
        last_node.puzzle_end = False
        last_node.segment_end = False

        new_node = Node(Q_ext.X, Q_ext.Y, Q_ext.Z)
        new_node.in_circular_grid = last_node.in_circular_grid
        new_node.in_rectangular_grid = last_node.in_rectangular_grid
        new_node.puzzle_end = True
        new_node.segment_end = True

        # Build a new path segment for at the end
        ext_segment = PathSegment(
            [last_node, new_node],
            main_index=end_segment.main_index,
            secondary_index=end_segment.secondary_index + 1,
        )
        ext_segment.copy_attributes_from(end_segment)
        ext_segment.curve_model = PathCurveModel.COMPOUND
        ext_segment.curve_type = PathCurveType.STRAIGHT
        ext_segment.transition_type = end_segment.transition_type

        self.segments.append(ext_segment)

    def reindex_segments(self):
        new_main_index_counter = 1
        main_index_mapping = {}
        secondary_index_counter = 0
        previous_main_index = None

        for segment in self.segments:
            old_main_index = segment.main_index
            if old_main_index != previous_main_index:
                # New main index encountered
                main_index_mapping[old_main_index] = new_main_index_counter
                new_main_index = new_main_index_counter
                new_main_index_counter += 1
                secondary_index_counter = 0
                previous_main_index = old_main_index
            else:
                new_main_index = main_index_mapping[old_main_index]

            segment.main_index = new_main_index
            segment.secondary_index = secondary_index_counter
            secondary_index_counter += 1

    def accent_color_paths(self):
        # Set the appropriate profile type for the accent color path body using the path profile accent registry
        for segment in self.segments:
            segment.accent_profile_type = ACCENT_REGISTRY.get(segment.path_profile_type)

    def create_support_materials(self):
        # Set path profile appropriate support profile types using the path profile support registry
        for segment in self.segments:
            segment.support_profile_type = SUPPORT_REGISTRY.get(
                segment.path_profile_type
            )

    def _split_spline_segment(
        self,
        segment: PathSegment,
        previous_segment: PathSegment | None = None,
        next_segment: PathSegment | None = None,
    ):
        """
        Split the spline segment into parts. Neighbouring segments are provided so
        the splitter can compare directions across the boundary and decide
        whether it needs the single-node “stitch” segments at each end.

        Stitch segments are included when the direction changes from either
        the previous segment or the next. This ensures improved feasible spline
        paths within the puzzle.
        """

        new_segments = []
        main_index = segment.main_index
        secondary_index_counter = self.secondary_index_counters.get(main_index, 0)
        nodes = segment.nodes

        # Sufficient nodes are required to create
        # stitch segments, if applicable and spline segment
        if len(nodes) > 2:

            def _are_collinear(vec_a: Vector, vec_b: Vector, tol: float = 1e-5) -> bool:
                """Return True when the two direction vectors are effectively the same line."""
                if vec_a.length == 0 or vec_b.length == 0:
                    return False
                dir_a = vec_a.normalized()
                dir_b = vec_b.normalized()
                dot = dir_a.dot(dir_b)
                # Clamp potential floating point drift before comparison
                dot = max(min(dot, 1.0), -1.0)
                if abs(dot) >= 1 - tol:
                    return True
                # Fallback to cross product magnitude check to cover near-opposite
                cross_x = dir_a.Y * dir_b.Z - dir_a.Z * dir_b.Y
                cross_y = dir_a.Z * dir_b.X - dir_a.X * dir_b.Z
                cross_z = dir_a.X * dir_b.Y - dir_a.Y * dir_b.X
                cross_mag_sq = cross_x * cross_x + cross_y * cross_y + cross_z * cross_z
                return cross_mag_sq <= tol

            # Decide whether the spline needs to start with a stitch segment
            needs_leading_single = True
            if previous_segment and previous_segment.nodes:
                prev_tail_vec = _node_to_vector(previous_segment.nodes[-1])
                first_vec = _node_to_vector(nodes[0])
                second_vec = _node_to_vector(nodes[1])
                in_vec = first_vec - prev_tail_vec
                out_vec = second_vec - first_vec
                needs_leading_single = not _are_collinear(in_vec, out_vec)

            # Decide whether the spline needs to end with a stitch segment
            needs_trailing_single = True
            if next_segment and next_segment.nodes:
                next_head_vec = _node_to_vector(next_segment.nodes[0])
                penultimate_vec = _node_to_vector(nodes[-2])
                last_vec = _node_to_vector(nodes[-1])
                in_vec = last_vec - penultimate_vec
                out_vec = next_head_vec - last_vec
                needs_trailing_single = not _are_collinear(in_vec, out_vec)

            # Select nodes based on decisions for requiring start or end stitch segments
            middle_start = 1 if needs_leading_single else 0
            middle_end = len(nodes) - 1 if needs_trailing_single else len(nodes)

            # Prepare start stitch segment, if applicable
            if needs_leading_single:
                first_node_segment = PathSegment(
                    [nodes[0]],
                    main_index=main_index,
                    secondary_index=secondary_index_counter,
                )
                first_node_segment.copy_attributes_from(segment)
                first_node_segment.curve_model = PathCurveModel.SINGLE
                new_segments.append(first_node_segment)
                secondary_index_counter += 1

            # Prepare spline segment
            middle_nodes = nodes[middle_start:middle_end]
            if middle_nodes:
                middle_nodes_segment = PathSegment(
                    middle_nodes,
                    main_index=main_index,
                    secondary_index=secondary_index_counter,
                )
                middle_nodes_segment.copy_attributes_from(segment)
                middle_nodes_segment.curve_model = PathCurveModel.SPLINE
                new_segments.append(middle_nodes_segment)
                secondary_index_counter += 1

            # Prepare end stitch segment, if applicable
            if needs_trailing_single:
                last_node_segment = PathSegment(
                    [nodes[-1]],
                    main_index=main_index,
                    secondary_index=secondary_index_counter,
                )
                last_node_segment.copy_attributes_from(segment)
                last_node_segment.curve_model = PathCurveModel.SINGLE
                new_segments.append(last_node_segment)
                secondary_index_counter += 1
        else:
            # Not enough nodes for spline, define regular segment
            for node in nodes:
                single_node_segment = PathSegment(
                    [node],
                    main_index=main_index,
                    secondary_index=secondary_index_counter,
                )
                single_node_segment.copy_attributes_from(segment)
                single_node_segment.curve_model = PathCurveModel.COMPOUND
                new_segments.append(single_node_segment)
                secondary_index_counter += 1

        self.secondary_index_counters[main_index] = secondary_index_counter

        return new_segments

    def make_circular_run(
        self, original: PathSegment, run_nodes: list[Node], is_circ: bool
    ) -> PathSegment:
        """
        Given a slice of nodes all sharing the same circular‐flag, make a new
        PathSegment carrying over all the original attributes. Force
        curve_type = ARC if is_circ else STRAIGHT.
        """
        segment = PathSegment(
            run_nodes,
            main_index=original.main_index,
            secondary_index=original.secondary_index,  # reindex done later
        )
        # copy everything (profile_type, transition_type, etc.)
        segment.copy_attributes_from(original)
        segment.curve_model = PathCurveModel.COMPOUND
        segment.curve_type = PathCurveType.ARC if is_circ else PathCurveType.STRAIGHT
        return segment
