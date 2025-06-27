# cad/path_segment.py

import math
from typing import List, Optional, Union

from build123d import Edge, Part, Sketch, Transition, Vector, Wire

from config import PathCurveModel, PathCurveType, PathProfileType
from puzzle.node import Node, NodeGridType


def _node_to_vector(node: Node) -> Vector:
    """Helper to convert a Node to a b3d.Vector."""
    return Vector(node.x, node.y, node.z)


def _safe_normalize(vec: Vector) -> Vector:
    """
    Returns a normalized vector.
    If the vector length is zero, returns a default vector (1, 0, 0)
    to avoid division by zero.
    """
    if vec.length == 0:
        return Vector(1, 0, 0)
    return vec.normalized()


def midpoint(P: Vector, Q: Vector, circular: bool = False) -> Vector:
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
        return Vector(r_mid * math.cos(theta_mid), r_mid * math.sin(theta_mid), z_mid)
    else:
        return (P + Q) * 0.5


class PathSegment:
    def __init__(self, nodes: List[Node], main_index: int, secondary_index: int = 0):
        """
        Initialize a PathSegment instance.

        Parameters:
            nodes (List[Node]): List of nodes that form this segment.
            main_index (int): Main index for identifying the segment.
            secondary_index (int): Secondary index for ordering segments within a main segment.
        """
        self.nodes = nodes
        self.main_index = main_index  # Segment index for identification
        self.secondary_index = secondary_index

        self.curve_type: Optional[PathCurveType] = None  # Curve type as enum
        self.curve_model: Optional[PathCurveModel] = None  # Assigned path curve model
        self.transition_type: Optional[Transition] = (
            None  # Assigned path transition type
        )
        # CAD path (might be specific edge type or combined wire for the group)
        self.path: Optional[Union[Edge, Wire]] = None
        # Assigned path profile type
        self.path_profile_type: Optional[PathProfileType] = None
        self.path_profile: Optional[Sketch] = None  # CAD path profile
        self.path_body: Optional[Part] = None  # CAD swept path body

        self.accent_profile_type: Optional[PathProfileType] = (
            None  # Path corresponding accent profile type
        )
        self.accent_profile: Optional[Sketch] = None  # CAD path profile
        self.accent_body: Optional[Part] = None  # CAD accent body

        self.support_profile_type: Optional[PathProfileType] = (
            None  # Path corresponding support profile type
        )
        self.support_profile: Optional[Sketch] = None  # CAD path profile
        self.support_body: Optional[Part] = None  # CAD support body

        # Store the specific edge created for this segment before combination
        self.path_edge_only: Optional[Union[Edge, Wire]] = None

    def adjust_start_and_endpoints(
        self,
        node_size,
        previous_end_node: Optional[Node] = None,
        next_start_node: Optional[Node] = None,
        previous_curve_type=None,
        next_curve_type=None,
    ):
        """
        Adjust the start and end nodes of this PathSegment based on puzzle rules,
        while handling bridging segments and single-node puzzle ends.

        Parameters:
            node_size: The size of a node used for computing adjustments.
            previous_end_node (Node): The last node from the previous segment.
            next_start_node (Node): The first node from the next segment.
            previous_curve_type: Curve type of the previous segment.
            next_curve_type: Curve type of the next segment.
        """
        # If this segment has a defined curve type, no adjustment is needed.
        if self.curve_type is not None:
            return

        # Check if this segment is bridging (its nodes match both previous and next endpoints)
        if self._check_and_handle_bridging_segment(previous_end_node, next_start_node):
            return

        # Special handling for single-node segments flagged as puzzle_end.
        if self._handle_single_node_puzzle_end(node_size, previous_end_node):
            return

        # FIXME found a bug, if this is followed by a SINGLE segment, say pre spline
        # Then the half way point is adjusted again
        # Adept first segment midpoint for half node size path corner:
        if self._handle_first_segment_midpoint(previous_end_node, next_start_node):
            return

        # For segments with two or more nodes, perform multi-node adjustment;
        # otherwise, handle the single-node case.
        if len(self.nodes) >= 2:
            self._adjust_multi_node_segment(
                node_size,
                previous_end_node,
                next_start_node,
                previous_curve_type,
                next_curve_type,
            )
        else:
            # Single-node segment that is not a puzzle_end bridging scenario.
            # Possibly a mounting node or partial bridging scenario that didn't match above.
            self._adjust_single_node_segment(
                node_size,
                previous_end_node,
                next_start_node,
                previous_curve_type,
                next_curve_type,
            )

    def _check_and_handle_bridging_segment(
        self, previous_end_node: Optional[Node], next_start_node: Optional[Node]
    ) -> bool:
        """
        Checks if this segment is a bridging segment, i.e., its node(s) match both
        the previous segment's end and the next segment's start.

        Returns:
            bool: True if bridging is detected and handled; otherwise, False.
        """
        if previous_end_node is None and next_start_node is None:
            return False

        # For a single-node segment, check if the node matches both endpoints.
        if len(self.nodes) == 1:
            node_vec = _node_to_vector(self.nodes[0])
            if (
                previous_end_node is not None
                and next_start_node is not None
                and is_same_location(node_vec, _node_to_vector(previous_end_node))
                and is_same_location(node_vec, _node_to_vector(next_start_node))
            ):
                return True
            return False

        # Multi node bridging check:
        else:
            # For multi-node segments, check first and last nodes.
            first_vec = _node_to_vector(self.nodes[0])
            last_vec = _node_to_vector(self.nodes[-1])
            if (
                previous_end_node is not None
                and next_start_node is not None
                and is_same_location(first_vec, _node_to_vector(previous_end_node))
                and is_same_location(last_vec, _node_to_vector(next_start_node))
            ):
                return True
            return False

    def _handle_single_node_puzzle_end(
        self, node_size, previous_end_node: Optional[Node]
    ) -> bool:
        """
        Handles the special logic for a single-node segment flagged as puzzle_end.
        The node is adjusted based on the previous segment's end node.

        Returns:
            bool: True if the special case was handled; otherwise, False.
        """
        if (
            len(self.nodes) == 1
            and self.nodes[0].puzzle_end
            and previous_end_node is not None
        ):
            # Create a new start node from the previous segment's end node.
            start_node = Node(
                previous_end_node.x, previous_end_node.y, previous_end_node.z
            )
            start_node.segment_start = True

            # Get current puzzle-end node position.
            end_node_point = _node_to_vector(self.nodes[0])
            # If the current node is circular, compute the arc midpoint.
            if (
                hasattr(self.nodes[0], "grid_type")
                and NodeGridType.CIRCULAR.value in self.nodes[0].grid_type
            ):
                adjusted_end = midpoint(
                    _node_to_vector(previous_end_node), end_node_point, circular=True
                )
            else:
                # Otherwise, use a linear offset by half the node size.
                entering_vector = end_node_point - _node_to_vector(previous_end_node)
                if entering_vector.length == 0:
                    entering_vector = Vector(1, 0, 0)
                entering_direction = _safe_normalize(entering_vector)
                move_distance = node_size / 2
                move_vector = entering_direction * move_distance
                adjusted_end = end_node_point + move_vector

            # Update the puzzle-end node's coordinates.
            self.nodes[0].x = adjusted_end.X
            self.nodes[0].y = adjusted_end.Y
            self.nodes[0].z = adjusted_end.Z
            self.nodes[0].segment_end = True

            # Insert the start node at the beginning of the segment.
            self.nodes.insert(0, start_node)
            return True

        return False

    def _adjust_multi_node_segment(
        self,
        node_size,
        previous_end_node: Optional[Node],
        next_start_node: Optional[Node],
        previous_curve_type,
        next_curve_type,
    ):
        """
        Adjusts a segment with two or more nodes.

        For the start node, if a previous_end_node is provided, it snaps exactly to that node,
        and its circular flag is derived from the previous node's grid_type.
        For the end node, a similar adjustment is performed based on next_start_node.
        """
        # Adjust start node.
        if not self.nodes[0].puzzle_start:
            if previous_end_node is not None:
                adjusted_start = _node_to_vector(previous_end_node)
                # Propagate the circular property from the previous segment's end node.
                is_circular_start = (
                    NodeGridType.CIRCULAR.value in previous_end_node.grid_type
                )
            else:
                adjusted_start = _node_to_vector(self.nodes[0])
                is_circular_start = (
                    hasattr(self.nodes[0], "grid_type")
                    and NodeGridType.CIRCULAR.value in self.nodes[0].grid_type
                )

            start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
            if is_circular_start:
                start_node.grid_type.append(NodeGridType.CIRCULAR.value)
            start_node.segment_start = True
            self.nodes.insert(0, start_node)
        else:
            self.nodes[0].segment_start = True

        # Adjust end node.
        end_node_point = _node_to_vector(self.nodes[-1])
        is_circular_end = False
        if next_start_node is not None:
            if next_curve_type is not None:
                # Full adjustment: snap exactly to the next segment's start node.
                adjusted_end = _node_to_vector(next_start_node)
            else:
                # For half adjustment: if current end node is circular, compute arc midpoint.
                if (
                    hasattr(self.nodes[-1], "grid_type")
                    and NodeGridType.CIRCULAR.value in self.nodes[-1].grid_type
                ):
                    is_circular_end = True
                    adjusted_end = midpoint(
                        end_node_point, _node_to_vector(next_start_node), circular=True
                    )
                else:
                    adjusted_end = midpoint(
                        end_node_point, _node_to_vector(next_start_node), circular=False
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
            if is_circular_end:
                end_node.grid_type.append(NodeGridType.CIRCULAR.value)
            end_node.segment_end = True
            self.nodes.append(end_node)

    def _adjust_single_node_segment(
        self,
        node_size,
        previous_end_node: Optional[Node],
        next_start_node: Optional[Node],
        previous_curve_type,
        next_curve_type,
    ):
        """
        Handles adjustments for a segment containing a single node.

        For the start node, use previous_end_node if provided (and propagate its circular property).
        For the end node, if next_start_node is provided, adjust accordingly based on whether the node is circular.
        """
        node_point = _node_to_vector(self.nodes[0])
        if previous_end_node is not None:
            adjusted_start = _node_to_vector(previous_end_node)
            is_circular_start = (
                NodeGridType.CIRCULAR.value in previous_end_node.grid_type
            )
        else:
            adjusted_start = node_point
            is_circular_start = (
                hasattr(self.nodes[0], "grid_type")
                and NodeGridType.CIRCULAR.value in self.nodes[0].grid_type
            )

        start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
        if is_circular_start:
            start_node.grid_type.append(NodeGridType.CIRCULAR.value)
        start_node.segment_start = True

        is_circular_end = False
        if next_start_node is not None:
            exiting_vector = _node_to_vector(next_start_node) - node_point
        elif previous_end_node is not None:
            exiting_vector = node_point - _node_to_vector(previous_end_node)
        else:
            exiting_vector = Vector(1, 0, 0)

        exiting_direction = _safe_normalize(exiting_vector)

        if self.nodes[0].puzzle_end:
            if next_start_node is not None:
                if (
                    hasattr(self.nodes[0], "grid_type")
                    and NodeGridType.CIRCULAR.value in self.nodes[0].grid_type
                ):
                    adjusted_end = midpoint(
                        node_point, _node_to_vector(next_start_node), circular=True
                    )
                else:
                    adjusted_end = midpoint(
                        node_point, _node_to_vector(next_start_node), circular=False
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
                if next_start_node is not None:
                    if next_curve_type is not None:
                        adjusted_end = _node_to_vector(next_start_node)
                    else:
                        # For half adjustment, use arc midpoint if the node is circular.
                        if (
                            hasattr(self.nodes[0], "grid_type")
                            and NodeGridType.CIRCULAR.value in self.nodes[0].grid_type
                        ):
                            is_circular_end = True
                            adjusted_end = midpoint(
                                node_point,
                                _node_to_vector(next_start_node),
                                circular=True,
                            )
                        else:
                            adjusted_end = midpoint(
                                node_point,
                                _node_to_vector(next_start_node),
                                circular=False,
                            )
                else:
                    adjusted_end = node_point

                end_node = Node(adjusted_end.X, adjusted_end.Y, adjusted_end.Z)
                if is_circular_end:
                    end_node.grid_type.append(NodeGridType.CIRCULAR.value)
                end_node.segment_end = True

                self.nodes.insert(0, start_node)
                self.nodes.append(end_node)
            else:
                # If already flagged as puzzle_start or puzzle_end, simply mark them.
                self.nodes[0].segment_start = self.nodes[0].puzzle_start
                self.nodes[0].segment_end = self.nodes[0].puzzle_end

    def copy_attributes_from(self, other_segment: "PathSegment"):
        """
        Copy path-related attributes from another PathSegment instance.
        """
        self.path_profile_type = other_segment.path_profile_type
        self.accent_profile_type = other_segment.accent_profile_type
        self.support_profile_type = other_segment.support_profile_type
        self.curve_model = other_segment.curve_model
        self.curve_type = other_segment.curve_type
        self.transition_type = other_segment.transition_type

    def _handle_first_segment_midpoint(
        self,
        previous_end_node: Optional[Node],
        next_start_node: Optional[Node],
    ) -> bool:
        """
        This end node adjustment is required to provide a half node size length segment
        prior to the next segment. To allow the start ramp to properly connect to a segment
        that goes left, straight or right just after the start ramp

        If this is the very first segment (no previous_end_node) AND contains
        the puzzle_start node AND there is a next_start_node, then:
        • compute the linear midpoint between this segment's last node
            and the next segment's first node,
        • append that midpoint Node here,
        Otherwise, return False.
        """
        if (
            previous_end_node is None
            and any(n.puzzle_start for n in self.nodes)
            and next_start_node is not None
        ):
            # compute linear midpoint
            P = _node_to_vector(self.nodes[-1])
            Q = _node_to_vector(next_start_node)
            M = midpoint(P, Q)

            # create & append the new mid-node
            end_node = Node(M.X, M.Y, M.Z)
            end_node.occupied = True
            end_node.segment_end = True
            self.nodes[-1].segment_end = False
            # propagate “circular” if either end is circular
            # FIXME this works only if it gets set to circular, but technically that's wrong.
            if (
                NodeGridType.CIRCULAR.value in self.nodes[-1].grid_type
                or NodeGridType.CIRCULAR.value in next_start_node.grid_type
            ):
                end_node.grid_type.append(NodeGridType.CIRCULAR.value)
            self.nodes.append(end_node)
            return True

        return False


def is_same_location(p1: Vector, p2: Vector, tol: float = 1e-7) -> bool:
    """
    Returns True if p1 and p2 are effectively the same point within a given tolerance.
    """
    return (p1 - p2).length < tol
