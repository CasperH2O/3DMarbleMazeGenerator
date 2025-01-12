# cad/path_segment

import build123d as b3d
import math
from typing import List, Optional

from config import PathCurveModel, PathCurveType, PathProfileType
from puzzle.node import Node


class PathSegment:
    def __init__(self, nodes: List[Node], main_index: int, secondary_index: int = 0):
        self.nodes = nodes
        self.main_index = main_index  # Segment index for identification
        self.secondary_index = secondary_index
        
        self.curve_type: Optional[PathCurveType] = None             # Curve type as enum
        self.curve_model: Optional[PathCurveModel] = None           # Assigned path curve model
        self.transition_type: Optional[b3d.Transition] = None       # Assigned path transition type
                                                  
        self.path: None                                             # CAD path
        self.path_profile_type: Optional[PathProfileType] = None    # Assigned path profile type
        self.path_profile: Optional[b3d.Sketch] = None              # CAD path profile
        self.path_body: Optional[b3d.Part] = None                   # CAD swept path body

        self.accent_profile_type: Optional[PathProfileType] = None  # Path corresponding accent profile type
        self.accent_profile: Optional[b3d.Sketch] = None            # CAD path profile
        self.accent_body: Optional[b3d.Part] = None                 # CAD accent body

        self.support_profile_type: Optional[PathProfileType] = None # Path corresponding support profile type
        self.support_profile: Optional[b3d.Sketch] = None           # CAD path profile
        self.support_body: Optional[b3d.Part] = None                # CAD support body

    def adjust_start_and_endpoints(self, node_size, previous_end_point=None, next_start_point=None,
                                previous_curve_type=None, next_curve_type=None):
        """
        Adjust the start and end nodes of this PathSegment based on puzzle rules, 
        while handling 'bridging' segments (segments that occupy the same location 
        as both the previous_end_point and next_start_point).
        """
        
        # Special handling for single-node end segments
        if len(self.nodes) == 1 and self.nodes[0].puzzle_end and previous_end_point is not None:
            # Create a new start node at the previous_end_point location
            start_node = Node(previous_end_point.X, previous_end_point.Y, previous_end_point.Z)
            start_node.segment_start = True

            # **Move the puzzle end node by half the node size in the path direction**
            end_node_point = b3d.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)
            entering_vector = end_node_point - previous_end_point

            if entering_vector.length == 0:
                entering_vector = b3d.Vector(1, 0, 0)  # Default direction

            entering_direction = entering_vector.normalized()

            move_distance = node_size / 2
            move_vector = entering_direction * move_distance
            adjusted_end = end_node_point + move_vector

            # Update the puzzle end node's coordinates
            self.nodes[0].x = adjusted_end.X
            self.nodes[0].y = adjusted_end.Y
            self.nodes[0].z = adjusted_end.Z
            self.nodes[0].segment_end = True

            # Insert the start node
            self.nodes.insert(0, start_node)
            return

        # Do not adjust end points in case of curves
        if self.curve_type is not None:
            return
        
        # If the segment is bridging or was handled accordingly, we can exit
        if self._check_and_handle_bridging_segment(previous_end_point, next_start_point, node_size):            
            return

        if len(self.nodes) >= 2:
            # Adjust start point
            if not self.nodes[0].puzzle_start:
                start_node_point = b3d.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)
                next_node_point = b3d.Vector(self.nodes[1].x, self.nodes[1].y, self.nodes[1].z)
                if previous_end_point is not None:
                    entering_vector = start_node_point - previous_end_point
                    if entering_vector.length == 0:
                        entering_vector = next_node_point - start_node_point
                else:
                    entering_vector = next_node_point - start_node_point

                if entering_vector.length == 0:
                    entering_vector = b3d.Vector(1, 0, 0)  # Default direction

                entering_direction = entering_vector.normalized()

                # Adjust distance based on previous segment's curve_type
                adjust_distance = node_size if previous_curve_type is not None else node_size / 2
                adjusted_start = start_node_point - entering_direction * adjust_distance
                start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
                start_node.segment_start = True
                self.nodes.insert(0, start_node)
            else:
                self.nodes[0].segment_start = True  # Mark the first node as segment start

            # Adjust end point
            end_node_point = b3d.Vector(self.nodes[-1].x, self.nodes[-1].y, self.nodes[-1].z)
            prev_node_point = b3d.Vector(self.nodes[-2].x, self.nodes[-2].y, self.nodes[-2].z)

            if next_start_point is not None:
                exiting_vector = next_start_point - end_node_point
                if exiting_vector.length == 0:
                    exiting_vector = end_node_point - prev_node_point
            else:
                exiting_vector = end_node_point - prev_node_point

            if exiting_vector.length == 0:
                exiting_vector = b3d.Vector(1, 0, 0)  # Default direction

            exiting_direction = exiting_vector.normalized()

            if self.nodes[-1].puzzle_end:
                # **Move the puzzle end node by half the node size in the path direction**
                move_distance = node_size / 2
                move_vector = exiting_direction * move_distance
                adjusted_end = end_node_point + move_vector

                # Update the puzzle end node's coordinates
                self.nodes[-1].X = adjusted_end.X
                self.nodes[-1].Y = adjusted_end.Y
                self.nodes[-1].Z = adjusted_end.Z
                self.nodes[-1].segment_end = True  # Mark the last node as segment end
            else:
                # Adjust distance based on next segment's curve_type
                adjust_distance = node_size if next_curve_type is not None else node_size / 2
                adjusted_end = end_node_point + exiting_direction * adjust_distance
                end_node = Node(adjusted_end.X, adjusted_end.Y, adjusted_end.Z)
                end_node.segment_end = True
                self.nodes.append(end_node)
        else:
            # Handle segments with only one node (e.g., mounting nodes)
            node_point = b3d.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)

            # Compute entering direction
            if previous_end_point is not None:
                entering_vector = node_point - previous_end_point
            elif next_start_point is not None:
                entering_vector = next_start_point - node_point
            else:
                entering_vector = b3d.Vector(1, 0, 0)  # Default direction

            if entering_vector.length == 0:
                entering_vector = b3d.Vector(1, 0, 0)  # Default direction

            entering_direction = entering_vector.normalized()

            # Compute exiting direction
            if next_start_point is not None:
                exiting_vector = next_start_point - node_point
            elif previous_end_point is not None:
                exiting_vector = node_point - previous_end_point
            else:
                exiting_vector = b3d.Vector(1, 0, 0)  # Default direction

            if exiting_vector.length == 0:
                exiting_vector = b3d.Vector(1, 0, 0)  # Default direction

            exiting_direction = exiting_vector.normalized()

            if self.nodes[0].puzzle_end:
                # **Move the puzzle end node by half the node size in the path direction**
                move_distance = node_size / 2
                move_vector = exiting_direction * move_distance
                adjusted_end = node_point + move_vector

                # Update the puzzle end node's coordinates
                self.nodes[0].X = adjusted_end.X
                self.nodes[0].Y = adjusted_end.Y
                self.nodes[0].Z = adjusted_end.Z
                self.nodes[0].segment_end = True
            else:
                if not self.nodes[0].puzzle_start and not self.nodes[0].puzzle_end:
                    # Adjust distances based on previous and next segments' curve_type
                    adjust_distance_start = node_size if previous_curve_type is not None else node_size / 2
                    adjust_distance_end = node_size if next_curve_type is not None else node_size / 2

                    adjusted_start = node_point - entering_direction * adjust_distance_start
                    start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
                    start_node.segment_start = True

                    adjusted_end = node_point + exiting_direction * adjust_distance_end
                    end_node = Node(adjusted_end.X, adjusted_end.Y, adjusted_end.Z)
                    end_node.segment_end = True

                    self.nodes.insert(0, start_node)
                    self.nodes.append(end_node)
                else:
                    self.nodes[0].segment_start = self.nodes[0].puzzle_start
                    self.nodes[0].segment_end = self.nodes[0].puzzle_end

    def _is_same_location(self, p1, p2, tol=1e-7):
        """
        Utility: returns True if p1 and p2 are effectively the same point 
        within a given floating-point tolerance.
        """
        return (p1 - p2).length < tol

    def _check_and_handle_bridging_segment(self, previous_end_point, next_start_point, node_size):
        """
        Returns True if this segment is a 'bridging segment' that should prevent 
        further adjustments. Otherwise, returns False.

        Also handles partial bridging: e.g., if the segment’s single node 
        coincides with previous_end_point but not next_start_point, 
        """
        # Quick exit if we have no valid endpoints to compare
        if (previous_end_point is None) and (next_start_point is None):
            return False

        # Convert Node -> b3d.Vector for convenience
        def as_vector(n):
            return b3d.Vector(n.x, n.y, n.z)

        # ---- Single-node check ----
        if len(self.nodes) == 1:
            node_vec = as_vector(self.nodes[0])

            # 1) Single node equals both previous_end_point & next_start_point
            if (previous_end_point is not None and 
                next_start_point is not None and
                self._is_same_location(node_vec, previous_end_point) and
                self._is_same_location(node_vec, next_start_point)):
                # This is a perfect bridging node: same as end of previous, start of next
                return True  # Stop further adjustments

            # 2) Single node only matches previous_end_point => connect it to next_start_point
            if previous_end_point is not None and \
            self._is_same_location(node_vec, previous_end_point) and \
            next_start_point is not None and \
            not self._is_same_location(node_vec, next_start_point):
                # For example, shift the node to match the next_start_point if you want
                # or do nothing if you prefer to keep it bridging in place
                #
                # Example: shift to the next_start_point
                self.nodes[0].x = next_start_point.X
                self.nodes[0].y = next_start_point.Y
                self.nodes[0].z = next_start_point.Z
                return True

            # 3) Single node only matches next_start_point => connect it to previous_end_point
            if next_start_point is not None and \
            self._is_same_location(node_vec, next_start_point) and \
            previous_end_point is not None and \
            not self._is_same_location(node_vec, previous_end_point):
                # Shift node to the previous_end_point if needed
                self.nodes[0].x = previous_end_point.X
                self.nodes[0].y = previous_end_point.Y
                self.nodes[0].z = previous_end_point.Z
                return True

            # If it doesn’t match anything, we just return False
            # so that the normal adjustments happen
            return False

        # ---- Multiple-node check (check first and last node) ----
        else:
            first_vec = b3d.Vector(self.nodes[0].x, self.nodes[0].y, self.nodes[0].z)
            last_vec = b3d.Vector(self.nodes[-1].x, self.nodes[-1].y, self.nodes[-1].z)

            both_endpoints_present = (previous_end_point is not None and next_start_point is not None)

            # Check if first node matches previous_end_point AND last node matches next_start_point
            if both_endpoints_present and \
            self._is_same_location(first_vec, previous_end_point) and \
            self._is_same_location(last_vec, next_start_point):
                # Perfect bridging
                return True

            # Similarly, you can handle partial bridging if you want:
            #  - if first node matches only previous_end_point
            #  - if last node matches only next_start_point
            # and shift as needed

            # If no bridging pattern matched, let normal adjustments proceed
            return False

    def copy_attributes_from(self, other_segment):
        self.path_profile_type = other_segment.path_profile_type
        self.curve_model = other_segment.curve_model
        self.curve_type = other_segment.curve_type
        self.transition_type = other_segment.transition_type                