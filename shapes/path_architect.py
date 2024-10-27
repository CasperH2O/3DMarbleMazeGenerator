import random
from typing import List

import config
from puzzle.node import Node
from config import *
from . import curve_detection
import cadquery as cq

class PathSegment:
    def __init__(self, nodes: List[Node], main_index: int, secondary_index: int = 0):
        self.nodes = nodes
        self.main_index = main_index # Segment index for identification
        self.secondary_index = secondary_index
        self.curve_type = None  # 'straight', 's_curve', 'arc'
        self.path_profile_type = None  # Assigned path profile type
        self.path_curve_model = None  # Assigned path curve model
        self.path_profile_location = None  # Location and orientation data
        self.geometry_data = None  # Data for 3D solid modelling

    def adjust_start_and_endpoints(self, node_size, previous_end_point=None, next_start_point=None):
        # Do not adjust end points in case of curves
        if self.curve_type is not None:
            return

        if len(self.nodes) >= 2:
            # Check if the first node is marked as a puzzle start node
            if not self.nodes[0].puzzle_start:
                # Compute entering direction for the start point
                start_node_point = cq.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)
                next_node_point = cq.Vector(self.nodes[1].x, self.nodes[1].y, self.nodes[1].z)
                if previous_end_point is not None:
                    entering_direction = (start_node_point - previous_end_point).normalized()
                else:
                    entering_direction = (next_node_point - start_node_point).normalized()
                # Adjust the start point
                adjusted_start = start_node_point - entering_direction * (node_size / 2)
                start_node = Node(adjusted_start.x, adjusted_start.y, adjusted_start.z)
                start_node.segment_start = True
                self.nodes.insert(0, start_node)
            else:
                # Do not adjust the start point
                self.nodes[0].segment_start = True  # Mark the first node as segment start

            # Compute exiting direction for the end point
            end_node_point = cq.Vector(self.nodes[-1].x, self.nodes[-1].y, self.nodes[-1].z)
            prev_node_point = cq.Vector(self.nodes[-2].x, self.nodes[-2].y, self.nodes[-2].z)
            if next_start_point is not None:
                exiting_direction = (next_start_point - end_node_point).normalized()
            else:
                exiting_direction = (end_node_point - prev_node_point).normalized()

            # Check if the last node is marked as a puzzle end node
            if not self.nodes[-1].puzzle_end:
                # Adjust the end point
                adjusted_end = end_node_point + exiting_direction * (node_size / 2)
                end_node = Node(adjusted_end.x, adjusted_end.y, adjusted_end.z)
                end_node.segment_end = True
                self.nodes.append(end_node)
            else:
                # Do not adjust the end point
                self.nodes[-1].segment_end = True  # Mark the last node as segment end
        else:
            # Handle segments with only one node (e.g., mounting nodes)
            node_point = cq.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)

            # Compute entering and exiting directions
            if previous_end_point is not None:
                entering_direction = (node_point - previous_end_point).normalized()
            elif next_start_point is not None:
                entering_direction = (next_start_point - node_point).normalized()
            else:
                entering_direction = cq.Vector(1, 0, 0)  # Default direction

            if next_start_point is not None:
                exiting_direction = (next_start_point - node_point).normalized()
            elif previous_end_point is not None:
                exiting_direction = (node_point - previous_end_point).normalized()
            else:
                exiting_direction = cq.Vector(1, 0, 0)  # Default direction

            # Check if the node is marked as a puzzle start or end node
            if not self.nodes[0].puzzle_start and not self.nodes[0].puzzle_end:
                # Adjust the segment start and end points
                adjusted_start = node_point - entering_direction * (node_size / 2)
                start_node = Node(adjusted_start.x, adjusted_start.y, adjusted_start.z)
                start_node.segment_start = True

                adjusted_end = node_point + exiting_direction * (node_size / 2)
                end_node = Node(adjusted_end.x, adjusted_end.y, adjusted_end.z)
                end_node.segment_end = True

                self.nodes.insert(0, start_node)
                self.nodes.append(end_node)
            else:
                # Do not adjust the puzzle start or end point
                self.nodes[0].segment_start = self.nodes[0].puzzle_start
                self.nodes[0].segment_end = self.nodes[0].puzzle_end

    def generate_geometry(self):
        # Prepare 3D geometry data for construction
        pass


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
        self.path_profile_types = Config.Path.PATH_PROFILE_TYPES.copy()
        self.path_curve_models = Config.Path.PATH_CURVE_MODEL.copy()
        self.nozzle_diameter = config.Manufacturing.NOZZLE_DIAMETER
        self.seed = Config.Puzzle.SEED
        random.seed(self.seed) # Set the random seed for reproducibility

        # Process the path
        self.split_path_into_segments()

        self.assign_path_profiles_and_models()

        self.create_start_ramp()
        self.create_finish_box()

        self.detect_curves_and_adjust_segments()

        self.adjust_segments()
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

    def assign_path_profiles_and_models(self):
        # Randomly assign path profile types and path curve models to segments
        for segment in self.segments:
            segment.path_profile_type = random.choice(self.path_profile_types)
            segment.path_curve_model = random.choice(self.path_curve_models)

    def detect_curves_and_adjust_segments(self):
        new_segments = []

        for segment in self.segments:
            # todo, rethink, because splines also can't be mounting waypoints...
            if segment.path_curve_model == 'polyline':
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
            if node.mounting:
                if current_segment_nodes:
                    segment = PathSegment(
                        current_segment_nodes,
                        main_index=main_index,
                        secondary_index=secondary_index_counter
                    )
                    secondary_index_counter += 1
                    # Copy attributes
                    segment.path_profile_type = original_segment.path_profile_type
                    segment.path_curve_model = original_segment.path_curve_model
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
                mounting_segment.path_curve_model = original_segment.path_curve_model
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
            segment.path_curve_model = original_segment.path_curve_model
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
                    segment.path_profile_type = original_segment.path_profile_type
                    segment.path_curve_model = original_segment.path_curve_model
                    segment.curve_type = current_curve_type  # Set the curve_type
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
            segment.path_profile_type = original_segment.path_profile_type
            segment.path_curve_model = original_segment.path_curve_model
            segment.curve_type = current_curve_type  # Set the curve_type
            split_segments.append(segment)

        # Update the counter in the dictionary
        self.secondary_index_counters[main_index] = secondary_index_counter

        return split_segments

    def adjust_segments(self):
        # Adjust start and end points of segments as needed
        previous_end_point = None
        for i, segment in enumerate(self.segments):
            next_start_point = None
            if i + 1 < len(self.segments):
                next_node = self.segments[i + 1].nodes[0]
                next_start_point = cq.Vector(next_node.x, next_node.y, next_node.z)
            segment.adjust_start_and_endpoints(self.node_size, previous_end_point, next_start_point)
            # Update previous_end_point to the last node of the current segment
            last_node = segment.nodes[-1]
            previous_end_point = cq.Vector(last_node.x, last_node.y, last_node.z)

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
            # Set the path_profile_type to 'u_shape' for the start segment
            start_segment.path_profile_type = 'u_shape'

    def create_finish_box(self):
        # This method adds a closing shape at the end of the path to close off the route.
        # It does this by extending the path in the opposite direction of the last segment.

        # Find the segment that contains the node with node.end == True
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

            # Set the profile type to 'rectangle_shape' for the closing shape
            new_segment.path_profile_type = 'rectangle_shape'
            new_segment.curve_type = 'straight'

            # Append new_segment to self.segments
            self.segments.append(new_segment)

            # Increment main_index_counter
            self.main_index_counter += 1

            # Ensure that the path_profile_type of the segment containing the last node is 'u_shape'
            end_segment.path_profile_type = 'u_shape'
        else:
            # Not enough nodes to compute direction
            pass

    def reindex_segments(self):
        # First, sort the segments
        self.segments.sort(key=lambda s: (s.main_index, s.secondary_index))

        # Reassign main_index and secondary_index sequentially
        new_main_index_counter = 0
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


