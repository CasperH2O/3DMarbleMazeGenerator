import random
from typing import List
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

        print(self.curve_type)

        # Do not adjust end points in case of curves
        if self.curve_type is not None:
            return

        if len(self.nodes) >= 2:
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

            # Compute exiting direction for the end point
            end_node_point = cq.Vector(self.nodes[-1].x, self.nodes[-1].y, self.nodes[-1].z)
            prev_node_point = cq.Vector(self.nodes[-2].x, self.nodes[-2].y, self.nodes[-2].z)
            if next_start_point is not None:
                exiting_direction = (next_start_point - end_node_point).normalized()
            else:
                exiting_direction = (end_node_point - prev_node_point).normalized()
            # Adjust the end point
            adjusted_end = end_node_point + exiting_direction * (node_size / 2)
            end_node = Node(adjusted_end.x, adjusted_end.y, adjusted_end.z)
            end_node.segment_end = True
            self.nodes.append(end_node)
        else:
            # Handle segments with only one node (e.g., mounting nodes)
            node_point = cq.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)

            # Compute entering direction
            if previous_end_point is not None:
                entering_direction = (node_point - previous_end_point).normalized()
            elif next_start_point is not None:
                entering_direction = (next_start_point - node_point).normalized()
            else:
                entering_direction = cq.Vector(1, 0, 0)  # Default direction

            # Compute exiting direction
            if next_start_point is not None:
                exiting_direction = (next_start_point - node_point).normalized()
            elif previous_end_point is not None:
                exiting_direction = (node_point - previous_end_point).normalized()
            else:
                exiting_direction = cq.Vector(1, 0, 0)  # Default direction

            # Adjust the start point
            adjusted_start = node_point - entering_direction * (node_size / 2)
            start_node = Node(adjusted_start.x, adjusted_start.y, adjusted_start.z)
            start_node.segment_start = True

            # Adjust the end point
            adjusted_end = node_point + exiting_direction * (node_size / 2)
            end_node = Node(adjusted_end.x, adjusted_end.y, adjusted_end.z)
            end_node.segment_end = True

            self.nodes.insert(0, start_node)
            self.nodes.append(end_node)

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
        self.seed = Config.Puzzle.SEED
        random.seed(self.seed) # Set the random seed for reproducibility

        # Process the path
        self.split_path_into_segments()
        self.create_start_ramp()
        self.create_finish_box()

        self.assign_path_profiles_and_models()

        self.detect_curves_and_adjust_segments()

        self.adjust_segments()
        self.reindex_segments()

    def split_path_into_segments(self):
        current_segment_nodes = []
        waypoint_counter = 0

        for i, node in enumerate(self.nodes):
            current_segment_nodes.append(node)

            # todo, rethink, as mounting waypoints can currently only be polyline of profile type u or o without rounded sweep
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
        start_nodes = [node for node in self.nodes if node.start]
        if start_nodes:
            # Use main_index = 0 for the start segment
            segment = PathSegment(
                start_nodes,
                main_index=0,
                secondary_index=0
            )
            segment.path_profile_type = 'u_shape'
            segment.curve_type = 'straight'
            self.segments.append(segment)

    def create_finish_box(self):
        end_nodes = [node for node in self.nodes if node.end]
        if end_nodes:
            # Use main_index as the next value after the last main segment
            segment = PathSegment(
                end_nodes,
                main_index=self.main_index_counter,
                secondary_index=0
            )
            segment.path_profile_type = 'rectangle_shape'
            segment.curve_type = 'straight'
            self.segments.append(segment)
            self.main_index_counter += 1  # Increment for completeness

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


