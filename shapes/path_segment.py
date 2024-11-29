# shapes/path_segment
import cadquery as cq
from typing import List, Optional

from config import PathCurveModel, PathCurveType, PathProfileType, PathTransitionType
from puzzle.node import Node


class PathSegment:
    def __init__(self, nodes: List[Node], main_index: int, secondary_index: int = 0):
        self.nodes = nodes
        self.main_index = main_index  # Segment index for identification
        self.secondary_index = secondary_index
        
        self.curve_type: Optional[PathCurveType] = None             # Curve type as enum
        self.curve_model: Optional[PathCurveModel] = None           # Assigned path curve model
        self.transition_type: Optional[PathTransitionType] = None   # Assigned path transition type
                                                  
        self.path: None                                             # CAD path
        self.path_profile_type: Optional[PathProfileType] = None    # Assigned path profile type
        self.path_profile: Optional[cq.Workplane] = None            # CAD path profile
        self.path_body: Optional[cq.Workplane] = None               # CAD swept path body

        self.accent_path: None   
        self.accent_profile_type: Optional[PathProfileType] = None  # Path corresponding accent profile type
        self.accent_profile: Optional[cq.Workplane] = None          # CAD path profile
        self.accent_body: Optional[cq.Workplane] = None             # CAD accent body

        self.support_path: None   
        self.support_profile_type: Optional[PathProfileType] = None # Path corresponding support profile type
        self.support_profile: Optional[cq.Workplane] = None         # CAD path profile
        self.support_body: Optional[cq.Workplane] = None            # CAD support body

    def adjust_start_and_endpoints(self, node_size, previous_end_point=None, next_start_point=None,
                                previous_curve_type=None, next_curve_type=None):

        # Special handling for single-node end segments
        if len(self.nodes) == 1 and self.nodes[0].puzzle_end and previous_end_point is not None:
            # Create a new start node at the previous_end_point location
            start_node = Node(previous_end_point.x, previous_end_point.y, previous_end_point.z)
            start_node.segment_start = True

            # **Move the puzzle end node by half the node size in the path direction**
            end_node_point = cq.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)
            entering_vector = end_node_point - previous_end_point

            if entering_vector.Length == 0:
                entering_vector = cq.Vector(1, 0, 0)  # Default direction

            entering_direction = entering_vector.normalized()

            move_distance = node_size / 2
            move_vector = entering_direction * move_distance
            adjusted_end = end_node_point + move_vector

            # Update the puzzle end node's coordinates
            self.nodes[0].x = adjusted_end.x
            self.nodes[0].y = adjusted_end.y
            self.nodes[0].z = adjusted_end.z
            self.nodes[0].segment_end = True

            # Insert the start node
            self.nodes.insert(0, start_node)
            return

        # Do not adjust end points in case of curves
        if self.curve_type is not None:
            return
        
        # Do not adjust segments that have been created to bridge curves
        if previous_curve_type is not None and next_curve_type is not None:
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

            if self.nodes[-1].puzzle_end:
                # **Move the puzzle end node by half the node size in the path direction**
                move_distance = node_size / 2
                move_vector = exiting_direction * move_distance
                adjusted_end = end_node_point + move_vector

                # Update the puzzle end node's coordinates
                self.nodes[-1].x = adjusted_end.x
                self.nodes[-1].y = adjusted_end.y
                self.nodes[-1].z = adjusted_end.z
                self.nodes[-1].segment_end = True  # Mark the last node as segment end
            else:
                # Adjust distance based on next segment's curve_type
                adjust_distance = node_size if next_curve_type is not None else node_size / 2
                adjusted_end = end_node_point + exiting_direction * adjust_distance
                end_node = Node(adjusted_end.x, adjusted_end.y, adjusted_end.z)
                end_node.segment_end = True
                self.nodes.append(end_node)
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

            if self.nodes[0].puzzle_end:
                # **Move the puzzle end node by half the node size in the path direction**
                move_distance = node_size / 2
                move_vector = exiting_direction * move_distance
                adjusted_end = node_point + move_vector

                # Update the puzzle end node's coordinates
                self.nodes[0].x = adjusted_end.x
                self.nodes[0].y = adjusted_end.y
                self.nodes[0].z = adjusted_end.z
                self.nodes[0].segment_end = True
            else:
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


    def copy_attributes_from(self, other_segment):
        self.path_profile_type = other_segment.path_profile_type
        self.curve_model = other_segment.curve_model
        self.curve_type = other_segment.curve_type
        self.transition_type = other_segment.transition_type                