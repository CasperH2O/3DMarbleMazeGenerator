# cad/path_segment.py

import math
from typing import List, Optional

import build123d as b3d

from config import PathCurveModel, PathCurveType, PathProfileType
from puzzle.node import Node


def _node_to_vector(node: Node) -> b3d.Vector:
    """Helper to convert a Node to a b3d.Vector."""
    return b3d.Vector(node.x, node.y, node.z)


def _safe_normalize(vec: b3d.Vector) -> b3d.Vector:
    """
    Returns a normalized vector.
    If the vector length is zero, returns a default vector (1, 0, 0)
    to avoid division by zero.
    """
    if vec.length == 0:
        return b3d.Vector(1, 0, 0)
    return vec.normalized()


def midpoint(P: b3d.Vector, Q: b3d.Vector, circular: bool = False) -> b3d.Vector:
    """
    Returns the midpoint between two vectors.
    If circular is True, returns the midpoint along the arc of the circle with center (0,0)
    (in the XY plane) defined by P and Q as endpoints; the Z coordinate is averaged.
    Otherwise, returns the linear (Euclidean) midpoint.
    """
    if circular:
        # Compute polar angles for P and Q in the XY plane.
        theta1 = math.atan2(P.Y, P.X)
        theta2 = math.atan2(Q.Y, Q.X)
        # Adjust the angle difference to take the shorter arc.
        d = theta2 - theta1
        if d > math.pi:
            d -= 2 * math.pi
        elif d < -math.pi:
            d += 2 * math.pi
        theta_mid = theta1 + d / 2
        # Average the radii from (0,0); if P and Q are on the same circle they should be equal.
        r1 = math.hypot(P.X, P.Y)
        r2 = math.hypot(Q.X, Q.Y)
        r_mid = (r1 + r2) / 2.0
        z_mid = (P.Z + Q.Z) / 2.0
        return b3d.Vector(
            r_mid * math.cos(theta_mid), r_mid * math.sin(theta_mid), z_mid
        )
    else:
        return (P + Q) * 0.5


class PathSegment:
    def __init__(self, nodes: List[Node], main_index: int, secondary_index: int = 0):
        self.nodes = nodes
        self.main_index = main_index  # Segment index for identification
        self.secondary_index = secondary_index

        self.curve_type: Optional[PathCurveType] = None  # Curve type as enum
        self.curve_model: Optional[PathCurveModel] = None  # Assigned path curve model
        self.transition_type: Optional[b3d.Transition] = (
            None  # Assigned path transition type
        )

        self.path = None  # CAD path
        self.path_profile_type: Optional[PathProfileType] = (
            None  # Assigned path profile type
        )
        self.path_profile: Optional[b3d.Sketch] = None  # CAD path profile
        self.path_body: Optional[b3d.Part] = None  # CAD swept path body

        self.accent_profile_type: Optional[PathProfileType] = (
            None  # Path corresponding accent profile type
        )
        self.accent_profile: Optional[b3d.Sketch] = None  # CAD path profile
        self.accent_body: Optional[b3d.Part] = None  # CAD accent body

        self.support_profile_type: Optional[PathProfileType] = (
            None  # Path corresponding support profile type
        )
        self.support_profile: Optional[b3d.Sketch] = None  # CAD path profile
        self.support_body: Optional[b3d.Part] = None  # CAD support body

    def adjust_start_and_endpoints(
        self,
        node_size,
        previous_end_point=None,
        next_start_point=None,
        previous_curve_type=None,
        next_curve_type=None,
    ):
        """
        Adjust the start and end nodes of this PathSegment based on puzzle rules,
        while handling bridging segments and single-node puzzle ends.
        """

        # In case of curve, no adjustment is needed.
        if self.curve_type is not None:
            return

        # Check bridging first. If this segment is bridging (occupies the same
        # location as both previous_end_point and next_start_point), or has
        # partial bridging logic, handle it accordingly and possibly return.
        # If bridging is detected and handled, we can skip further adjustments.
        if self._check_and_handle_bridging_segment(
            previous_end_point, next_start_point
        ):
            return

        # Special handling for single-node puzzle-end segments:
        # If we detect a single-node that is a puzzle_end with a known previous_end_point,
        # handle that logic and return.
        if self._handle_single_node_puzzle_end(node_size, previous_end_point):
            return

        # In case of multiple nodes (>= 2), handle normal adjustments.
        if len(self.nodes) >= 2:
            self._adjust_multi_node_segment(
                node_size,
                previous_end_point,
                next_start_point,
                previous_curve_type,
                next_curve_type,
            )
        else:
            # Single-node segment that is not a puzzle_end bridging scenario.
            # Possibly a mounting node or partial bridging scenario that didn't match above.
            self._adjust_single_node_segment(
                node_size,
                previous_end_point,
                next_start_point,
                previous_curve_type,
                next_curve_type,
            )

    def _check_and_handle_bridging_segment(
        self, previous_end_point, next_start_point
    ) -> bool:
        """
        Checks if this segment is bridging: i.e., a single node or first/last node
        that exactly matches both previous_end_point and next_start_point.
        If bridging is detected and processed, returns True to indicate that we
        should skip further adjustments. Otherwise, returns False.
        """
        # If there's no valid endpoint to compare, no bridging can occur:
        if previous_end_point is None and next_start_point is None:
            return False

        # Single node bridging check:
        if len(self.nodes) == 1:
            node_vec = _node_to_vector(self.nodes[0])
            # Check if the single node matches both previous_end_point and next_start_point:
            if (
                previous_end_point is not None
                and next_start_point is not None
                and is_same_location(node_vec, previous_end_point)
                and is_same_location(node_vec, next_start_point)
            ):
                # Perfect bridging node: same location as both ends
                return True
            return False

        # Multi node bridging check:
        else:
            first_vec = _node_to_vector(self.nodes[0])
            last_vec = _node_to_vector(self.nodes[-1])
            if (
                previous_end_point is not None
                and next_start_point is not None
                and is_same_location(first_vec, previous_end_point)
                and is_same_location(last_vec, next_start_point)
            ):
                # Perfect bridging: first node = previous_end_point AND last node = next_start_point
                return True
            return False

    def _handle_single_node_puzzle_end(self, node_size, previous_end_point) -> bool:
        """
        Handles the special logic where we have a single-node segment that is
        flagged as puzzle_end and we know the previous_end_point to connect to.
        Returns True if this scenario was handled, else False.
        """
        if (
            len(self.nodes) == 1
            and self.nodes[0].puzzle_end
            and previous_end_point is not None
        ):
            # Create a new start node at the previous_end_point location
            start_node = Node(
                previous_end_point.X, previous_end_point.Y, previous_end_point.Z
            )
            start_node.segment_start = True

            # Get current puzzle-end node position.
            end_node_point = _node_to_vector(self.nodes[0])
            # If the current node is circular, compute the arc midpoint between
            # previous_end_point and the current puzzle-end node.
            if (
                hasattr(self.nodes[0], "grid_type")
                and "circular" in self.nodes[0].grid_type
            ):
                adjusted_end = midpoint(
                    previous_end_point, end_node_point, circular=True
                )
            else:
                # Otherwise, use the linear offset by half the node size.
                entering_vector = end_node_point - previous_end_point
                if entering_vector.length == 0:
                    entering_vector = b3d.Vector(
                        1, 0, 0
                    )  # Default direction if we can't compute
                entering_direction = _safe_normalize(entering_vector)
                move_distance = node_size / 2
                move_vector = entering_direction * move_distance
                adjusted_end = end_node_point + move_vector

            # Update the puzzle-end node's coordinates
            self.nodes[0].x = adjusted_end.X
            self.nodes[0].y = adjusted_end.Y
            self.nodes[0].z = adjusted_end.Z
            self.nodes[0].segment_end = True

            # Insert the start node at the front
            self.nodes.insert(0, start_node)
            return True

        return False

    def _adjust_multi_node_segment(
        self,
        node_size,
        previous_end_point,
        next_start_point,
        previous_curve_type,
        next_curve_type,
    ):
        """
        Adjusts a segment that contains 2 or more nodes.
        For the start node, if previous_end_point is provided:
        - With a full adjustment (previous_curve_type set): new start = previous_end_point.
        - With a half adjustment: new start = midpoint(previous_end_point, first node).
        However, to avoid gaps when the previous segment already adjusted its end,
        we now always snap to previous_end_point if it is provided.
        The end node is adjusted similarly using next_start_point.
        """
        # Adjust start node if not already marked as puzzle_start.
        if not self.nodes[0].puzzle_start:
            start_node_point = _node_to_vector(self.nodes[0])
            if previous_end_point is not None:
                # Always snap to previous_end_point to ensure continuity.
                adjusted_start = previous_end_point
            else:
                # Fallback if no previous_end_point: use the current node's position (no adjustment)
                adjusted_start = start_node_point

            start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
            start_node.segment_start = True
            self.nodes.insert(0, start_node)
        else:
            self.nodes[0].segment_start = True

        # Adjust end node
        end_node_point = _node_to_vector(self.nodes[-1])
        if next_start_point is not None:
            if next_curve_type is not None:
                # Full adjustment: snap to next_start_point exactly
                adjusted_end = next_start_point
            else:
                # For half adjustment, if the current end node is circular,
                # compute the arc midpoint between its position and next_start_point.
                if (
                    hasattr(self.nodes[-1], "grid_type")
                    and "circular" in self.nodes[-1].grid_type
                ):
                    adjusted_end = midpoint(
                        end_node_point, next_start_point, circular=True
                    )
                else:
                    adjusted_end = midpoint(
                        end_node_point, next_start_point, circular=False
                    )
        else:
            # Fallback if no next_start_point: use the current end node's position (no adjustment)
            adjusted_end = end_node_point

        if self.nodes[-1].puzzle_end:
            # For a puzzle_end node, update the node in place
            self.nodes[-1].x = adjusted_end.X
            self.nodes[-1].y = adjusted_end.Y
            self.nodes[-1].z = adjusted_end.Z
            self.nodes[-1].segment_end = True
        else:
            # Otherwise, append a new node at the adjusted position
            end_node = Node(adjusted_end.X, adjusted_end.Y, adjusted_end.Z)
            end_node.segment_end = True
            self.nodes.append(end_node)

    def _adjust_single_node_segment(
        self,
        node_size,
        previous_end_point,
        next_start_point,
        previous_curve_type,
        next_curve_type,
    ):
        """
        Handles adjustments for segments containing a single node (non puzzle endpoints).
        The adjustment logic here follows the same idea:
        - Use the midpoint between the current node and the reference (previous or next)
          when a half adjustment is intended.
        - Otherwise, snap to the reference location.
        To ensure segments connect without a gap, if previous_end_point is provided,
        we always snap the start to that point rather than doing a half adjustment.
        """
        node_point = _node_to_vector(self.nodes[0])

        # Compute exiting direction using next_start_point if available
        if next_start_point is not None:
            exiting_vector = next_start_point - node_point
        elif previous_end_point is not None:
            exiting_vector = node_point - previous_end_point
        else:
            exiting_vector = b3d.Vector(1, 0, 0)

        exiting_direction = _safe_normalize(exiting_vector)

        if self.nodes[0].puzzle_end:
            if next_start_point is not None:
                # For puzzle_end nodes, if circular, compute arc midpoint; otherwise, linear midpoint.
                if (
                    hasattr(self.nodes[0], "grid_type")
                    and "circular" in self.nodes[0].grid_type
                ):
                    adjusted_end = midpoint(node_point, next_start_point, circular=True)
                else:
                    adjusted_end = midpoint(
                        node_point, next_start_point, circular=False
                    )
            else:
                adjusted_end = node_point + exiting_direction * (node_size / 2)
            self.nodes[0].x = adjusted_end.X
            self.nodes[0].y = adjusted_end.Y
            self.nodes[0].z = adjusted_end.Z
            self.nodes[0].segment_end = True
        else:
            # For nodes that are neither puzzle_start nor puzzle_end,
            # create start and end nodes on either side.
            if not self.nodes[0].puzzle_start and not self.nodes[0].puzzle_end:
                if previous_end_point is not None:
                    # Always snap to previous_end_point to ensure continuity.
                    adjusted_start = previous_end_point
                else:
                    adjusted_start = node_point

                start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
                start_node.segment_start = True

                if next_start_point is not None:
                    if next_curve_type is not None:
                        adjusted_end = next_start_point
                    else:
                        # For half adjustment, use arc midpoint if the node is circular.
                        if (
                            hasattr(self.nodes[0], "grid_type")
                            and "circular" in self.nodes[0].grid_type
                        ):
                            adjusted_end = midpoint(
                                node_point, next_start_point, circular=True
                            )
                        else:
                            adjusted_end = midpoint(
                                node_point, next_start_point, circular=False
                            )
                else:
                    adjusted_end = node_point

                end_node = Node(adjusted_end.X, adjusted_end.Y, adjusted_end.Z)
                end_node.segment_end = True

                self.nodes.insert(0, start_node)
                self.nodes.append(end_node)
            else:
                # If already flagged as puzzle_start or puzzle_end, simply mark them.
                self.nodes[0].segment_start = self.nodes[0].puzzle_start
                self.nodes[0].segment_end = self.nodes[0].puzzle_end

    def copy_attributes_from(self, other_segment):
        """
        Copy path-related attributes from another PathSegment instance.
        """
        self.path_profile_type = other_segment.path_profile_type
        self.curve_model = other_segment.curve_model
        self.curve_type = other_segment.curve_type
        self.transition_type = other_segment.transition_type


def is_same_location(p1: b3d.Vector, p2: b3d.Vector, tol: float = 1e-7) -> bool:
    """
    Returns True if p1 and p2 are effectively the same point
    within a given floating-point tolerance.
    """
    return (p1 - p2).length < tol
