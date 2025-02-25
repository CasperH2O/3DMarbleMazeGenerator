# cad/path_architect.py

import random
from typing import List
from build123d import *

import config
from puzzle.node import Node
from config import *
from cad.path_segment import PathSegment
from . import curve_detection
import build123d as b3d

class PathArchitect:
    def __init__(self, nodes: List[Node]):
        # Inputs
        self.nodes = nodes
        self.segments: List[PathSegment] = []
        self.main_index_counter = 1  # Main index counter
        self.secondary_index_counters = {}  # Dictionary to track secondary indices per main_index

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

        # Handle the first two nodes as a special segment, the start ramp
        if nodes_length >= 2:
            # Create a segment with the first two nodes
            first_two_nodes = self.nodes[:2]
            segment = PathSegment(
                first_two_nodes,
                main_index=self.main_index_counter
            )
            self.segments.append(segment)
            self.main_index_counter += 1
            # Start processing from the third node
            node_iter = self.nodes[2:]
        else:
            # If less than two nodes, include all nodes
            node_iter = self.nodes

        # Continue with the rest of the nodes
        for node in node_iter:
            current_segment_nodes.append(node)

            if node.waypoint and not node.mounting:
                waypoint_counter += 1
                if waypoint_counter % self.waypoint_change_interval == 0:
                    # Create a segment with collected nodes
                    self._create_segment(current_segment_nodes, main_index=self.main_index_counter)
                    self.main_index_counter += 1
                    current_segment_nodes = []

        if current_segment_nodes:
            # Create a segment with any remaining nodes
            self._create_segment(current_segment_nodes, main_index=self.main_index_counter)
            self.main_index_counter += 1

    def _create_segment(self, nodes: List[Node], main_index: int):
        segment = PathSegment(nodes, main_index=main_index)
        self.segments.append(segment)

    def assign_path_properties(self):
        
        # Randomly assign path profile types and path curve models to segments
        previous_profile_type = None
        previous_curve_model = None

        for segment in self.segments:
            # Check if the segment contains any mounting node
            has_mounting_node = any(node.mounting for node in segment.nodes)
            if has_mounting_node:
                # For mounting segments, only select specific types, ensures linking with bridge
                available_profile_types = [PathProfileType.O_SHAPE, PathProfileType.U_SHAPE, PathProfileType.U_SHAPE_ADJUSTED_HEIGHT]
                available_curve_models = [PathCurveModel.POLYLINE]
            else:
                # For other segments, use all available types
                available_profile_types = self.path_profile_types.copy()
                available_curve_models = self.path_curve_models.copy()

            # Exclude previous types if possible
            # For path profile type
            if previous_profile_type in available_profile_types and len(available_profile_types) > 1:
                available_profile_types.remove(previous_profile_type)

            # For path curve model
            if previous_curve_model in available_curve_models and len(available_curve_models) > 1:
                available_curve_models.remove(previous_curve_model)

            # Select random types from the available lists
            segment.path_profile_type = random.choice(available_profile_types)
            segment.curve_model = random.choice(available_curve_models)

            # Update previous types for next round
            previous_profile_type = segment.path_profile_type
            previous_curve_model = segment.curve_model

    def assign_path_transition_types(self):

        # Initialize the transition tracker
        next_transition = Transition.ROUND  # Starting with 'round'

        for segment in self.segments:        

            # Check if segment already has a transition type, skip if so
            # Todo, it seems certain segments do not properly copy node properties, thus waypoint nodes do not get copied. info was lost
            if segment.transition_type is not None:
                continue

            # Determine the transition type for the segment
            if segment.path_profile_type in [PathProfileType.V_SHAPE, PathProfileType.O_SHAPE]:
                segment.transition_type = Transition.ROUND
            elif any(node.mounting for node in segment.nodes):
                segment.transition_type = Transition.RIGHT
            else:
                # Alternately choose between 'right' and 'round'
                segment.transition_type = next_transition
                # Flip the next_transition for the subsequent else case
                next_transition = Transition.ROUND if next_transition == Transition.RIGHT else Transition.RIGHT

    def detect_curves_and_adjust_segments(self):
        i = 0
        curve_id_counter = 1  # Initialize the curve ID counter
        while i < len(self.segments):
            segment = self.segments[i]
            if segment.curve_model == PathCurveModel.POLYLINE:
                # Split the segment into sub-segments around mounting nodes
                sub_segments = self._split_around_mounting_nodes(segment.nodes, segment)
                new_split_segments = []
                for sub_segment in sub_segments:
                    if len(sub_segment.nodes) > 1:
                        # Pass the curve_id_counter to detect_curves
                        curve_id_counter = curve_detection.detect_curves(sub_segment.nodes, curve_id_counter)
                        split_segments = self._split_segment_by_detected_curves(sub_segment.nodes, sub_segment)
                        new_split_segments.extend(split_segments)
                    else:
                        new_split_segments.append(sub_segment)
                # Replace the original segment with new_split_segments
                self.segments[i:i+1] = new_split_segments
                i += len(new_split_segments)
            elif segment.curve_model == PathCurveModel.SPLINE:
                # Split the spline segment into parts
                new_segments = self._split_spline_segment(segment)
                self.segments[i:i+1] = new_segments
                i += len(new_segments)
            else:
                i += 1


    def _split_around_mounting_nodes(self, nodes: List[Node], original_segment) -> List[PathSegment]:
        sub_segments = []
        current_segment_nodes = []

        main_index = original_segment.main_index
        # Retrieve or initialize the secondary_index_counter for this main_index
        secondary_index_counter = self.secondary_index_counters.get(main_index, 0)

        for node in nodes:
            # Filter out the puzzle start node, as we don't want that broken up
            if node.mounting and not node.puzzle_start:
                if current_segment_nodes:
                    segment = PathSegment(
                        current_segment_nodes,
                        main_index=main_index,
                        secondary_index=secondary_index_counter
                    )
                    secondary_index_counter += 1
                    # Copy attributes
                    segment.path_profile_type = original_segment.path_profile_type
                    segment.curve_model = original_segment.curve_model
                    segment.transition_type = original_segment.transition_type
                    sub_segments.append(segment)
                    current_segment_nodes = []
                # Segment for the mounting node
                mounting_segment = PathSegment(
                    [node],
                    main_index=main_index,
                    secondary_index=secondary_index_counter
                )
                secondary_index_counter += 1
                mounting_segment.path_profile_type = original_segment.path_profile_type
                mounting_segment.curve_model = original_segment.curve_model
                mounting_segment.transition_type = Transition.RIGHT
                sub_segments.append(mounting_segment)
            else:
                current_segment_nodes.append(node)

        if current_segment_nodes:
            segment = PathSegment(
                current_segment_nodes,
                main_index=main_index,
                secondary_index=secondary_index_counter
            )
            secondary_index_counter += 1  # Increment the counter after creating the segment
            # Copy attributes
            segment.path_profile_type = original_segment.path_profile_type
            segment.curve_model = original_segment.curve_model
            segment.transition_type = original_segment.transition_type
            sub_segments.append(segment)

        # Update the counter in the dictionary
        self.secondary_index_counters[main_index] = secondary_index_counter

        return sub_segments


    def _split_segment_by_detected_curves(self, nodes: List[Node], original_segment) -> List[PathSegment]:
        """
        Splits a given path segment into multiple segments based on detected curves and ensures continuity
        between adjacent curves by creating connecting segments when necessary.

        This method processes the list of nodes from the original segment, detects changes in curve types
        and curve IDs, and creates new segments accordingly. When multiple curves are adjacent, it creates
        a connecting segment between them to maintain path continuity.

        Args:
            nodes (List[Node]): The list of nodes with curve detection information.
            original_segment: The original path segment to be split.

        Returns:
            List[PathSegment]: A list of new path segments resulting from splitting the original segment.
        """
        split_segments = []
        current_segment_nodes = []
        current_curve_type = None
        current_curve_id = None  # Initialize the current curve ID

        main_index = original_segment.main_index
        # Retrieve or initialize the secondary index counter for this main index
        secondary_index_counter = self.secondary_index_counters.get(main_index, 0)

        for idx, node in enumerate(nodes):
            node_curve_id = getattr(node, 'curve_id', None)  # Get curve ID, default to None if not present

            # Check if we need to start a new segment due to a change in curve type or curve ID
            if (node.path_curve_type != current_curve_type) or (node_curve_id != current_curve_id):
                if current_segment_nodes:
                    # Finish the current segment and add it to the list of split segments
                    segment = PathSegment(
                        current_segment_nodes,
                        main_index=main_index,
                        secondary_index=secondary_index_counter
                    )
                    secondary_index_counter += 1
                    # Copy attributes from the original segment to maintain consistency
                    segment.path_profile_type = original_segment.path_profile_type
                    segment.curve_model = original_segment.curve_model
                    segment.curve_type = current_curve_type
                    segment.transition_type = original_segment.transition_type
                    split_segments.append(segment)

                    # Create a connecting segment only when transitioning between different curves
                    if current_curve_id is not None and node_curve_id is not None and current_curve_id != node_curve_id:
                        # Use the last node of the previous segment and the current node to create the connecting segment
                        start_node = current_segment_nodes[-1]
                        end_node = node
                        connecting_nodes = [start_node, end_node]
                        connecting_segment = PathSegment(
                            connecting_nodes,
                            main_index=main_index,
                            secondary_index=secondary_index_counter
                        )
                        secondary_index_counter += 1
                        # Set attributes for the connecting segment
                        connecting_segment.path_profile_type = original_segment.path_profile_type
                        connecting_segment.curve_model = PathCurveModel.POLYLINE  # Assuming a straight line
                        connecting_segment.curve_type = None  # No specific curve type
                        connecting_segment.transition_type = original_segment.transition_type
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
                secondary_index=secondary_index_counter
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
        # Adjust start and end points of segments as needed
        previous_end_point = None
        previous_curve_type = None
        for i, segment in enumerate(self.segments):
            next_start_point = None
            next_curve_type = None
            if i + 1 < len(self.segments):
                next_segment = self.segments[i + 1]
                next_node = next_segment.nodes[0]
                next_start_point = b3d.Vector(next_node.x, next_node.y, next_node.z)
                next_curve_type = next_segment.curve_type
            segment.adjust_start_and_endpoints(
                self.node_size,
                previous_end_point,
                next_start_point,
                previous_curve_type,
                next_curve_type
            )
            # Update previous_end_point and previous_curve_type
            if segment.nodes:
                last_node = segment.nodes[-1]
                previous_end_point = b3d.Vector(last_node.x, last_node.y, last_node.z)
                previous_curve_type = segment.curve_type
            else:
                previous_end_point = None
                previous_curve_type = None

    def create_start_ramp(self):
        # This method finds the segment containing the start node and creates the start ramp

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
        # This method adds a closing shape at the end of the path to close off the route.
        # It does this by extending the path in the opposite direction of the last segment.

        # Find the segment that contains the node with puzzle end node
        end_segment = None
        end_node_index = None
        for segment in self.segments:
            for i, node in enumerate(segment.nodes):
                if node.puzzle_end:
                    end_segment = segment
                    end_node_index = i
                    break
            if end_segment:
                break

        if end_segment is None or end_node_index is None:
            # No end node found, so nothing to do
            return

        # Ensure there are at least two nodes to calculate the direction
        if end_node_index >= 1:
            # Get last node (end node) and second last node
            last_node = end_segment.nodes[end_node_index]
            second_last_node = end_segment.nodes[end_node_index - 1]

            # Compute the vector from second last node to last node
            vec_last = b3d.Vector(last_node.x, last_node.y, last_node.z)
            vec_second_last = b3d.Vector(second_last_node.x, second_last_node.y, second_last_node.z)
            direction_vector = (vec_last - vec_second_last).normalized()

            # Compute opposite direction
            opposite_direction = -direction_vector

            # Determine length of extension (use nozzle diameter)
            extension_length = self.nozzle_diameter * 3

            # Create new node extending from last node in opposite direction
            extension_vector = opposite_direction * extension_length
            new_point = vec_last + extension_vector
            new_node = Node(new_point.X, new_point.Y, new_point.Z)

            # Create new segment consisting of last_node and new_node
            new_segment_nodes = [new_node, last_node]

            # Create new PathSegment for the closing shape
            new_segment = PathSegment(
                nodes=new_segment_nodes,
                main_index=self.main_index_counter,
                secondary_index=0
            )

            # Set the profile type to rectangle shape for the closing shape
            new_segment.curve_model = PathCurveModel.POLYLINE
            new_segment.path_profile_type = PathProfileType.RECTANGLE_SHAPE
            new_segment.curve_type = PathCurveType.STRAIGHT
            new_segment.transition_type = end_segment.transition_type

            # Append new_segment to self.segments
            self.segments.append(new_segment)

            # Increment main_index_counter
            self.main_index_counter += 1

            # Ensure that the path profile type of the segment containing the last node is u shaped
            end_segment.path_profile_type = PathProfileType.U_SHAPE

            # Update the end segment last node to the location
            end_segment.nodes[-1] = new_node
        else:
            # Not enough nodes to compute direction
            pass

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
        # Set the appropriate profile type for the accent color path body
        for segment in self.segments:          
            if segment.path_profile_type == PathProfileType.U_SHAPE:
                segment.accent_profile_type = PathProfileType.U_SHAPE_PATH_COLOR
            elif segment.path_profile_type == PathProfileType.V_SHAPE:
                segment.accent_profile_type = PathProfileType.V_SHAPE_PATH_COLOR

    def create_support_materials(self):
        # Set path profile appropriate support profile types
        for segment in self.segments:
            if segment.path_profile_type == PathProfileType.O_SHAPE:
                segment.support_profile_type = PathProfileType.O_SHAPE_SUPPORT

    def _split_spline_segment(self, segment):
        new_segments = []
        main_index = segment.main_index
        secondary_index_counter = self.secondary_index_counters.get(main_index, 0)
        nodes = segment.nodes

        if len(nodes) > 2:
            # First node segment
            first_node_segment = PathSegment(
                [nodes[0]],
                main_index=main_index,
                secondary_index=secondary_index_counter
            )
            first_node_segment.copy_attributes_from(segment)
            first_node_segment.curve_model = PathCurveModel.POLYLINE
            new_segments.append(first_node_segment)
            secondary_index_counter += 1

            # Middle nodes segment
            middle_nodes_segment = PathSegment(
                nodes[1:-1],
                main_index=main_index,
                secondary_index=secondary_index_counter
            )
            middle_nodes_segment.copy_attributes_from(segment)
            middle_nodes_segment.curve_model = PathCurveModel.SPLINE
            new_segments.append(middle_nodes_segment)
            secondary_index_counter += 1

            # Last node segment
            last_node_segment = PathSegment(
                [nodes[-1]],
                main_index=main_index,
                secondary_index=secondary_index_counter
            )
            last_node_segment.copy_attributes_from(segment)
            last_node_segment.curve_model = PathCurveModel.POLYLINE
            new_segments.append(last_node_segment)
            secondary_index_counter += 1
        else:
            # Handle segments with two or fewer nodes
            for node in nodes:
                single_node_segment = PathSegment(
                    [node],
                    main_index=main_index,
                    secondary_index=secondary_index_counter
                )
                single_node_segment.copy_attributes_from(segment)
                single_node_segment.curve_model = PathCurveModel.POLYLINE
                new_segments.append(single_node_segment)
                secondary_index_counter += 1

        self.secondary_index_counters[main_index] = secondary_index_counter
        
        return new_segments

