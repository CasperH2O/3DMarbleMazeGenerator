# shapes/path_architect.py

import random
from typing import List

import config
from puzzle.node import Node
from config import *
from . import curve_detection
import cadquery as cq
from typing import Optional

class PathSegment:
    def __init__(self, nodes: List[Node], main_index: int, secondary_index: int = 0):
        self.nodes = nodes
        self.main_index = main_index  # Segment index for identification
        self.secondary_index = secondary_index
        self.curve_type: Optional[PathCurveType] = None             # Curve type as enum
        self.profile_type: Optional[PathProfileType] = None         # Assigned path profile type
        self.curve_model: Optional[PathCurveModel] = None           # Assigned path curve model
        self.transition_type: Optional[PathTransitionType] = None   # Assigned path transition type
        self.profile: None  # CAD path profile
        self.path: None     # CAD path
        self.body: None     # CAD swept body

    def adjust_start_and_endpoints(self, node_size, previous_end_point=None, next_start_point=None,
                                   previous_curve_type=None, next_curve_type=None):
    
        # Special handling for single-node end segments
        if len(self.nodes) == 1 and self.nodes[0].puzzle_end and previous_end_point is not None:
            # Create a new start node at the previous_end_point location
            start_node = Node(previous_end_point.x, previous_end_point.y, previous_end_point.z)
            start_node.segment_start = True
            self.nodes.insert(0, start_node)
            self.nodes[-1].segment_end = True
            return
            
        # Do not adjust end points in case of curves
        if self.curve_type is not None:
            return

        if len(self.nodes) >= 2:
            # Adjust start point
            if not self.nodes[0].puzzle_start:
                start_node_point = cq.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)
                next_node_point = cq.Vector(self.nodes[1].x, self.nodes[1].y, self.nodes[1].z)
                if previous_end_point is not None:
                    entering_vector = start_node_point - previous_end_point
                    if entering_vector.Length == 0:
                        entering_vector = next_node_point - start_node_point
                else:
                    entering_vector = next_node_point - start_node_point

                if entering_vector.Length == 0:
                    entering_vector = cq.Vector(1, 0, 0)  # Default direction

                entering_direction = entering_vector.normalized()

                # Adjust distance based on previous segment's curve_type
                adjust_distance = node_size if previous_curve_type is not None else node_size / 2
                adjusted_start = start_node_point - entering_direction * adjust_distance
                start_node = Node(adjusted_start.x, adjusted_start.y, adjusted_start.z)
                start_node.segment_start = True
                self.nodes.insert(0, start_node)
            else:
                self.nodes[0].segment_start = True  # Mark the first node as segment start

            # Adjust end point
            end_node_point = cq.Vector(self.nodes[-1].x, self.nodes[-1].y, self.nodes[-1].z)
            prev_node_point = cq.Vector(self.nodes[-2].x, self.nodes[-2].y, self.nodes[-2].z)
            if next_start_point is not None:
                exiting_vector = next_start_point - end_node_point
                if exiting_vector.Length == 0:
                    exiting_vector = end_node_point - prev_node_point
            else:
                exiting_vector = end_node_point - prev_node_point

            if exiting_vector.Length == 0:
                exiting_vector = cq.Vector(1, 0, 0)  # Default direction

            exiting_direction = exiting_vector.normalized()

            if not self.nodes[-1].puzzle_end:
                # Adjust distance based on next segment's curve_type
                adjust_distance = node_size if next_curve_type is not None else node_size / 2
                adjusted_end = end_node_point + exiting_direction * adjust_distance
                end_node = Node(adjusted_end.x, adjusted_end.y, adjusted_end.z)
                end_node.segment_end = True
                self.nodes.append(end_node)
            else:
                self.nodes[-1].segment_end = True  # Mark the last node as segment end
        else:
            # Handle segments with only one node (e.g., mounting nodes)
            node_point = cq.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)

            # Compute entering direction
            if previous_end_point is not None:
                entering_vector = node_point - previous_end_point
            elif next_start_point is not None:
                entering_vector = next_start_point - node_point
            else:
                entering_vector = cq.Vector(1, 0, 0)  # Default direction

            if entering_vector.Length == 0:
                entering_vector = cq.Vector(1, 0, 0)  # Default direction

            entering_direction = entering_vector.normalized()

            # Compute exiting direction
            if next_start_point is not None:
                exiting_vector = next_start_point - node_point
            elif previous_end_point is not None:
                exiting_vector = node_point - previous_end_point
            else:
                exiting_vector = cq.Vector(1, 0, 0)  # Default direction

            if exiting_vector.Length == 0:
                exiting_vector = cq.Vector(1, 0, 0)  # Default direction

            exiting_direction = exiting_vector.normalized()

            if not self.nodes[0].puzzle_start and not self.nodes[0].puzzle_end:
                # Adjust distances based on previous and next segments' curve_type
                adjust_distance_start = node_size if previous_curve_type is not None else node_size / 2
                adjust_distance_end = node_size if next_curve_type is not None else node_size / 2

                adjusted_start = node_point - entering_direction * adjust_distance_start
                start_node = Node(adjusted_start.x, adjusted_start.y, adjusted_start.z)
                start_node.segment_start = True

                adjusted_end = node_point + exiting_direction * adjust_distance_end
                end_node = Node(adjusted_end.x, adjusted_end.y, adjusted_end.z)
                end_node.segment_end = True

                self.nodes.insert(0, start_node)
                self.nodes.append(end_node)
            else:
                self.nodes[0].segment_start = self.nodes[0].puzzle_start
                self.nodes[0].segment_end = self.nodes[0].puzzle_end


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
        self.color_segments()

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
                available_profile_types = [PathProfileType.O_SHAPE, PathProfileType.U_SHAPE]
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
            segment.profile_type = random.choice(available_profile_types)
            segment.curve_model = random.choice(available_curve_models)


            # Update previous types for next round
            previous_profile_type = segment.profile_type
            previous_curve_model = segment.curve_model

    def assign_path_transition_types(self):

        # Initialize the transition tracker
        next_transition = PathTransitionType.ROUND  # Starting with 'round'

        for segment in self.segments:        

            # Check if segment already has a transition type, skip if so
            # Todo, it seems certain segments do not properly copy node properties, thus waypoint nodes do not get copied. info was lost
            if segment.transition_type is not None:
                continue

            # Determine the transition type for the segment
            if segment.profile_type in [PathProfileType.V_SHAPE, PathProfileType.O_SHAPE]:
                segment.transition_type = PathTransitionType.ROUND
            elif any(node.mounting for node in segment.nodes):
                segment.transition_type = PathTransitionType.RIGHT
            else:
                # Alternately choose between 'right' and 'round'
                segment.transition_type = next_transition
                # Flip the next_transition for the subsequent else case
                next_transition = PathTransitionType.ROUND if next_transition == PathTransitionType.RIGHT else PathTransitionType.RIGHT

    def detect_curves_and_adjust_segments(self):
        new_segments = []

        for segment in self.segments:
            if segment.curve_model == PathCurveModel.POLYLINE:
                # Split the segment into sub-segments around mounting nodes, can't make curves of those
                sub_segments = self._split_around_mounting_nodes(segment.nodes, segment)
                for sub_segment in sub_segments:
                    if len(sub_segment.nodes) > 1:
                        curve_detection.detect_curves(sub_segment.nodes)
                        new_split_segments = self._split_segment_by_detected_curves(sub_segment.nodes, sub_segment)
                        new_segments.extend(new_split_segments)
                    else:
                        # For segments with only one node (e.g., mounting nodes)
                        new_segments.append(sub_segment)
            elif segment.curve_model == PathCurveModel.SPLINE:
                # Split the spline segment into three parts: first node, middle nodes, last node
                if len(segment.nodes) > 2:
                    first_node_segment = PathSegment(
                        [segment.nodes[0]],
                        main_index=segment.main_index,
                        secondary_index=self.secondary_index_counters.get(segment.main_index, 0)
                    )
                    first_node_segment.profile_type = segment.profile_type
                    first_node_segment.curve_model = PathCurveModel.POLYLINE
                    first_node_segment.transition_type = segment.transition_type
                    new_segments.append(first_node_segment)

                    # Increment the secondary index counter
                    self.secondary_index_counters[segment.main_index] = self.secondary_index_counters.get(
                        segment.main_index, 0) + 1

                    middle_nodes_segment = PathSegment(
                        segment.nodes[1:-1],
                        main_index=segment.main_index,
                        secondary_index=self.secondary_index_counters[segment.main_index]
                    )
                    middle_nodes_segment.profile_type = segment.profile_type
                    middle_nodes_segment.curve_model = PathCurveModel.SPLINE
                    middle_nodes_segment.transition_type = segment.transition_type
                    new_segments.append(middle_nodes_segment)

                    # Increment the secondary index counter
                    self.secondary_index_counters[segment.main_index] += 1

                    last_node_segment = PathSegment(
                        [segment.nodes[-1]],
                        main_index=segment.main_index,
                        secondary_index=self.secondary_index_counters[segment.main_index]
                    )
                    last_node_segment.profile_type = segment.profile_type
                    last_node_segment.curve_model = PathCurveModel.POLYLINE
                    last_node_segment.transition_type = segment.transition_type
                    new_segments.append(last_node_segment)

                    # Increment the secondary index counter
                    self.secondary_index_counters[segment.main_index] += 1
                else:
                    # If there are only two nodes, treat them as separate POLYLINE segments
                    for node in segment.nodes:
                        single_node_segment = PathSegment(
                            [node],
                            main_index=segment.main_index,
                            secondary_index=self.secondary_index_counters.get(segment.main_index, 0)
                        )
                        single_node_segment.profile_type = segment.profile_type
                        single_node_segment.curve_model = PathCurveModel.POLYLINE
                        single_node_segment.transition_type = segment.transition_type
                        new_segments.append(single_node_segment)

                        # Increment the secondary index counter
                        self.secondary_index_counters[segment.main_index] = self.secondary_index_counters.get(
                            segment.main_index, 0) + 1
            else:
                new_segments.append(segment)

        self.segments = new_segments

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
                    segment.profile_type = original_segment.profile_type
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
                mounting_segment.profile_type = original_segment.profile_type
                mounting_segment.curve_model = original_segment.curve_model
                mounting_segment.transition_type = PathTransitionType.RIGHT
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
            segment.profile_type = original_segment.profile_type
            segment.curve_model = original_segment.curve_model
            segment.transition_type = original_segment.transition_type
            sub_segments.append(segment)

        # Update the counter in the dictionary
        self.secondary_index_counters[main_index] = secondary_index_counter

        return sub_segments

    def _split_segment_by_detected_curves(self, nodes: List[Node], original_segment) -> List[PathSegment]:
        split_segments = []
        current_segment_nodes = []
        current_curve_type = None

        main_index = original_segment.main_index
        # Retrieve or initialize the secondary_index_counter for this main_index
        secondary_index_counter = self.secondary_index_counters.get(main_index, 0)

        for node in nodes:
            if node.path_curve_type != current_curve_type:
                if current_segment_nodes:
                    segment = PathSegment(
                        current_segment_nodes,
                        main_index=main_index,
                        secondary_index=secondary_index_counter
                    )
                    secondary_index_counter += 1
                    # Copy attributes
                    segment.profile_type = original_segment.profile_type
                    segment.curve_model = original_segment.curve_model
                    segment.curve_type = current_curve_type  # Set the curve_type
                    segment.transition_type = original_segment.transition_type
                    split_segments.append(segment)
                    current_segment_nodes = []
                current_curve_type = node.path_curve_type
            current_segment_nodes.append(node)

        if current_segment_nodes:
            segment = PathSegment(
                current_segment_nodes,
                main_index=main_index,
                secondary_index=secondary_index_counter
            )
            secondary_index_counter += 1
            # Copy attributes
            segment.profile_type = original_segment.profile_type
            segment.curve_model = original_segment.curve_model
            segment.curve_type = current_curve_type  # Set the curve_type
            segment.transition_type = original_segment.transition_type
            split_segments.append(segment)

        # Update the counter in the dictionary
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
                next_start_point = cq.Vector(next_node.x, next_node.y, next_node.z)
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
                previous_end_point = cq.Vector(last_node.x, last_node.y, last_node.z)
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
            start_segment.profile_type = PathProfileType.U_SHAPE

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
            vec_last = cq.Vector(last_node.x, last_node.y, last_node.z)
            vec_second_last = cq.Vector(second_last_node.x, second_last_node.y, second_last_node.z)
            direction_vector = (vec_last - vec_second_last).normalized()

            # Compute opposite direction
            opposite_direction = -direction_vector

            # Determine length of extension (use nozzle diameter)
            extension_length = self.nozzle_diameter * 3

            # Create new node extending from last node in opposite direction
            extension_vector = opposite_direction * extension_length
            new_point = vec_last + extension_vector
            new_node = Node(new_point.x, new_point.y, new_point.z)

            # Create new segment consisting of last_node and new_node
            new_segment_nodes = [last_node, new_node]

            # Create new PathSegment for the closing shape
            new_segment = PathSegment(
                nodes=new_segment_nodes,
                main_index=self.main_index_counter,
                secondary_index=0
            )

            # Set the profile type to rectangle shape for the closing shape
            new_segment.curve_model = PathCurveModel.POLYLINE
            new_segment.profile_type = PathProfileType.RECTANGLE_SHAPE
            new_segment.curve_type = PathCurveType.STRAIGHT
            new_segment.transition_type = end_segment.transition_type

            # Append new_segment to self.segments
            self.segments.append(new_segment)

            # Increment main_index_counter
            self.main_index_counter += 1

            # Ensure that the path profile type of the segment containing the last node is u shaped
            end_segment.profile_type = PathProfileType.U_SHAPE

            # Update the end segment last node to the location
            end_segment.nodes[-1] = new_node
        else:
            # Not enough nodes to compute direction
            pass

    def reindex_segments(self):
        # First, sort the segments
        self.segments.sort(key=lambda s: (s.main_index, s.secondary_index))

        # Reassign main_index and secondary_index sequentially
        new_main_index_counter = 1
        main_index_mapping = {}
        secondary_index_counters = {}

        for segment in self.segments:
            old_main_index = segment.main_index
            if old_main_index not in main_index_mapping:
                # Assign a new main index
                main_index_mapping[old_main_index] = new_main_index_counter
                new_main_index = new_main_index_counter
                new_main_index_counter += 1
                # Initialize secondary index counter for this main index
                secondary_index_counters[new_main_index] = 0
            else:
                new_main_index = main_index_mapping[old_main_index]
            # Assign new secondary index
            new_secondary_index = secondary_index_counters[new_main_index]
            secondary_index_counters[new_main_index] += 1
            # Reassign indices
            segment.main_index = new_main_index
            segment.secondary_index = new_secondary_index

    def color_segments(self):
        # Parse all exisiting segments, find certain path profile types, generate new segments with
        # respectively matching path profile coloring profile. Use exisiting route/nodes, make a copy and change profile type

        # Iterate through all existing segments
        for segment in self.segments[:-1]:

            # If the segment contains the puzzle start node, skip it
            if any(node.puzzle_start for node in segment.nodes):
                continue

            # If the segment's profile type is U_SHAPE
            if segment.profile_type == PathProfileType.U_SHAPE:
                # Create a copy of the segment
                copied_nodes = [Node(node.x, node.y, node.z) for node in segment.nodes]
                colored_segment = PathSegment(
                    nodes=copied_nodes,
                    main_index=segment.main_index,
                    secondary_index=segment.secondary_index + 1
                )
                
                # Assign the new profile type as U_SHAPE_PATH_COLOR
                colored_segment.profile_type = PathProfileType.U_SHAPE_PATH_COLOR
                colored_segment.curve_model = segment.curve_model
                colored_segment.curve_type = segment.curve_type
                colored_segment.transition_type = segment.transition_type

                # Append the colored segment to the segments list
                self.segments.append(colored_segment)

    def create_support_materials(self):
        # Parse all exisiting segments, find certain path profile types, generate support bodies

        # Iterate through all existing segments
        for segment in self.segments:

            # If the segment's profile type is O_SHAPE
            if segment.profile_type == PathProfileType.O_SHAPE:
                # Create a copy of the segment
                copied_nodes = [Node(node.x, node.y, node.z) for node in segment.nodes]
                support_segment = PathSegment(
                    nodes=copied_nodes,
                    main_index=segment.main_index,
                    secondary_index=segment.secondary_index + 1
                )
                
                # Assign the new profile type as O_SHAPE_SUPPORT
                support_segment.profile_type = PathProfileType.O_SHAPE_SUPPORT
                support_segment.curve_model = segment.curve_model
                support_segment.curve_type = segment.curve_type
                support_segment.transition_type = segment.transition_type

                # Append the colored segment to the segments list
                self.segments.append(support_segment)

