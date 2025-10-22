# cad/path_segment.py

import logging
import math
from typing import Optional, Union

from build123d import Edge, Part, Sketch, Transition, Vector, Wire

from config import PathCurveModel, PathCurveType, PathProfileType
from puzzle.node import Node


logger = logging.getLogger(__name__)


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


def _format_node(node: Optional[Node]) -> str:
    if node is None:
        return "None"
    return f"({node.x:.3f}, {node.y:.3f}, {node.z:.3f})"


def _format_vector(vec: Vector) -> str:
    return f"({vec.X:.3f}, {vec.Y:.3f}, {vec.Z:.3f})"


def _format_node_list(nodes: list[Node]) -> str:
    return "[" + ", ".join(_format_node(node) for node in nodes) + "]"


class PathSegment:
    def __init__(self, nodes: list[Node], main_index: int, secondary_index: int = 0):
        """
        Initialize a PathSegment instance.

        Parameters:
            nodes (list[Node]): List of nodes that form this segment.
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

        # Obstacle
        self.is_obstacle: bool = False
        self.lock_path: bool = False  # if True, PathBuilder must not overwrite .path
        self.use_frenet: bool = False  # for helix/spiral-like geometries

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
        logger.debug(
            "PathSegment[%s.%s] adjust_start_and_endpoints nodes=%s previous_end=%s next_start=%s previous_curve=%s next_curve=%s",
            self.main_index,
            self.secondary_index,
            _format_node_list(self.nodes),
            _format_node(previous_end_node),
            _format_node(next_start_node),
            previous_curve_type,
            next_curve_type,
        )

        # If this segment has a defined curve type, no adjustment is needed.
        if self.curve_type is not None:
            logger.debug(
                "PathSegment[%s.%s] has fixed curve_type=%s, skipping adjustments",
                self.main_index,
                self.secondary_index,
                self.curve_type,
            )
            return

        # Check if this segment is bridging (its nodes match both previous and next endpoints)
        if self._check_and_handle_bridging_segment(previous_end_node, next_start_node):
            logger.debug(
                "PathSegment[%s.%s] detected bridging segment between %s and %s",
                self.main_index,
                self.secondary_index,
                _format_node(previous_end_node),
                _format_node(next_start_node),
            )
            return

        # Special handling for single-node segments flagged as puzzle_end.
        if self._handle_single_node_puzzle_end(node_size, previous_end_node):
            logger.debug(
                "PathSegment[%s.%s] handled single-node puzzle end using half-node extension",
                self.main_index,
                self.secondary_index,
            )
            return

        # FIXME found a bug, if this is followed by a SINGLE segment, say pre spline
        # Then the half way point is adjusted again
        # Adept first segment midpoint for half node size path corner:
        if self._handle_first_segment_midpoint(previous_end_node, next_start_node):
            logger.debug(
                "PathSegment[%s.%s] inserted first-segment midpoint towards %s",
                self.main_index,
                self.secondary_index,
                _format_node(next_start_node),
            )
            return

        # For segments with two or more nodes, perform multi-node adjustment;
        # otherwise, handle the single-node case.
        if len(self.nodes) >= 2:
            logger.debug(
                "PathSegment[%s.%s] using multi-node adjustment path",
                self.main_index,
                self.secondary_index,
            )
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
            logger.debug(
                "PathSegment[%s.%s] using single-node adjustment path",
                self.main_index,
                self.secondary_index,
            )
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
            logger.debug(
                "PathSegment[%s.%s] handling puzzle_end single node from %s towards %s",
                self.main_index,
                self.secondary_index,
                _format_node(previous_end_node),
                _format_node(self.nodes[0]),
            )
            # Create a new start node from the previous segment's end node.
            start_node = Node(
                previous_end_node.x, previous_end_node.y, previous_end_node.z
            )
            start_node.segment_start = True

            # Get current puzzle-end node position.
            end_node_point = _node_to_vector(self.nodes[0])
            # If the current node is circular, compute the arc midpoint.
            if self.nodes[0].in_circular_grid:
                adjusted_end = midpoint(
                    _node_to_vector(previous_end_node), end_node_point, circular=True
                )
                logger.debug(
                    "PathSegment[%s.%s] puzzle_end midpoint (circular) between %s and %s -> %s",
                    self.main_index,
                    self.secondary_index,
                    _format_node(previous_end_node),
                    _format_node(self.nodes[0]),
                    _format_vector(adjusted_end),
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
                logger.debug(
                    "PathSegment[%s.%s] puzzle_end linear extension half-node %.3f along %s -> %s",
                    self.main_index,
                    self.secondary_index,
                    move_distance,
                    _format_vector(entering_direction),
                    _format_vector(adjusted_end),
                )

            # Update the puzzle-end node's coordinates.
            self.nodes[0].x = adjusted_end.X
            self.nodes[0].y = adjusted_end.Y
            self.nodes[0].z = adjusted_end.Z
            self.nodes[0].segment_end = True

            # Insert the start node at the beginning of the segment.
            self.nodes.insert(0, start_node)
            logger.debug(
                "PathSegment[%s.%s] puzzle_end segment expanded with start %s and adjusted end %s",
                self.main_index,
                self.secondary_index,
                _format_node(start_node),
                _format_vector(adjusted_end),
            )
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
        and its circular flag is derived from the previous node's circular status.
        For the end node, a similar adjustment is performed based on next_start_node.
        """
        # Adjust start node.
        if not self.nodes[0].puzzle_start:
            if previous_end_node is not None:
                adjusted_start = _node_to_vector(previous_end_node)
                previous_is_circular = (
                    previous_end_node.in_circular_grid
                    or previous_curve_type == PathCurveType.ARC
                )
                # Propagate only if both sides of the junction are circular.
                is_circular_start = (
                    previous_is_circular
                    and self.nodes[0].in_circular_grid
                )
            else:
                adjusted_start = _node_to_vector(self.nodes[0])
                is_circular_start = self.nodes[0].in_circular_grid

            start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
            start_node.in_circular_grid = is_circular_start
            start_node.in_rectangular_grid = (
                previous_end_node.in_rectangular_grid
                if previous_end_node is not None
                else self.nodes[0].in_rectangular_grid
            )
            start_node.segment_start = True
            self.nodes.insert(0, start_node)
            logger.debug(
                "PathSegment[%s.%s] multi-node start anchored at %s (circular=%s)",
                self.main_index,
                self.secondary_index,
                _format_vector(adjusted_start),
                is_circular_start,
            )
        else:
            self.nodes[0].segment_start = True
            logger.debug(
                "PathSegment[%s.%s] multi-node start retains existing puzzle start at %s",
                self.main_index,
                self.secondary_index,
                _format_node(self.nodes[0]),
            )

        # Adjust end node.
        end_node_point = _node_to_vector(self.nodes[-1])
        is_circular_end = False
        end_adjustment_reason = ""
        if next_start_node is not None:
            next_is_circular = (
                next_start_node.in_circular_grid
                or next_curve_type == PathCurveType.ARC
            )
            if next_curve_type is not None:
                # Full adjustment: snap exactly to the next segment's start node.
                adjusted_end = _node_to_vector(next_start_node)
                is_circular_end = (
                    self.nodes[-1].in_circular_grid
                    and next_is_circular
                )
                end_adjustment_reason = (
                    "snapped to next start (fixed curve)"
                )
            else:
                # For half adjustment: if current end node is circular, compute arc midpoint.
                if (
                    self.nodes[-1].in_circular_grid
                    and next_is_circular
                ):
                    is_circular_end = True
                    adjusted_end = midpoint(
                        end_node_point, _node_to_vector(next_start_node), circular=True
                    )
                    end_adjustment_reason = "circular midpoint"
                else:
                    adjusted_end = midpoint(
                        end_node_point, _node_to_vector(next_start_node), circular=False
                    )
                    end_adjustment_reason = "linear midpoint"
        else:
            # Fallback if no next_start_point: use the current end node's position (no adjustment)
            adjusted_end = end_node_point
            end_adjustment_reason = "no next segment"

        logger.debug(
            "PathSegment[%s.%s] multi-node end adjusted via %s to %s (circular=%s)",
            self.main_index,
            self.secondary_index,
            end_adjustment_reason,
            _format_vector(adjusted_end),
            is_circular_end,
        )

        if self.nodes[-1].puzzle_end:
            # For a puzzle_end node, update the node in place
            self.nodes[-1].x = adjusted_end.X
            self.nodes[-1].y = adjusted_end.Y
            self.nodes[-1].z = adjusted_end.Z
            self.nodes[-1].segment_end = True
            if is_circular_end:
                self.nodes[-1].in_circular_grid = True
            logger.debug(
                "PathSegment[%s.%s] multi-node end updated in place at %s",
                self.main_index,
                self.secondary_index,
                _format_vector(adjusted_end),
            )
        else:
            # Otherwise, append a new node at the adjusted position
            end_node = Node(adjusted_end.X, adjusted_end.Y, adjusted_end.Z)
            end_node.in_circular_grid = is_circular_end
            end_node.in_rectangular_grid = self.nodes[-1].in_rectangular_grid
            end_node.segment_end = True
            self.nodes.append(end_node)
            logger.debug(
                "PathSegment[%s.%s] multi-node end appended at %s (circular=%s)",
                self.main_index,
                self.secondary_index,
                _format_vector(adjusted_end),
                is_circular_end,
            )

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
            previous_is_circular = (
                previous_end_node.in_circular_grid
                or previous_curve_type == PathCurveType.ARC
            )
            is_circular_start = (
                previous_is_circular
                and self.nodes[0].in_circular_grid
            )
        else:
            adjusted_start = node_point
            is_circular_start = self.nodes[0].in_circular_grid

        start_node = Node(adjusted_start.X, adjusted_start.Y, adjusted_start.Z)
        start_node.in_circular_grid = is_circular_start
        start_node.in_rectangular_grid = (
            previous_end_node.in_rectangular_grid
            if previous_end_node is not None
            else self.nodes[0].in_rectangular_grid
        )
        start_node.segment_start = True
        logger.debug(
            "PathSegment[%s.%s] single-node start anchored at %s (circular=%s)",
            self.main_index,
            self.secondary_index,
            _format_vector(adjusted_start),
            is_circular_start,
        )

        is_circular_end = False
        if next_start_node is not None:
            exiting_vector = _node_to_vector(next_start_node) - node_point
        elif previous_end_node is not None:
            exiting_vector = node_point - _node_to_vector(previous_end_node)
        else:
            exiting_vector = Vector(1, 0, 0)

        exiting_direction = _safe_normalize(exiting_vector)
        logger.debug(
            "PathSegment[%s.%s] single-node exiting direction %s from vector %s",
            self.main_index,
            self.secondary_index,
            _format_vector(exiting_direction),
            _format_vector(exiting_vector),
        )

        if self.nodes[0].puzzle_end:
            if next_start_node is not None:
                next_is_circular = (
                    next_start_node.in_circular_grid
                    or next_curve_type == PathCurveType.ARC
                )
                should_use_circular_midpoint = (
                    self.nodes[0].in_circular_grid
                    and next_is_circular
                )
                if should_use_circular_midpoint:
                    adjusted_end = midpoint(
                        node_point, _node_to_vector(next_start_node), circular=True
                    )
                    logger.debug(
                        "PathSegment[%s.%s] single-node puzzle_end using circular midpoint towards %s -> %s",
                        self.main_index,
                        self.secondary_index,
                        _format_node(next_start_node),
                        _format_vector(adjusted_end),
                    )
                else:
                    adjusted_end = midpoint(
                        node_point, _node_to_vector(next_start_node), circular=False
                    )
                    logger.debug(
                        "PathSegment[%s.%s] single-node puzzle_end using linear midpoint towards %s -> %s",
                        self.main_index,
                        self.secondary_index,
                        _format_node(next_start_node),
                        _format_vector(adjusted_end),
                    )
            else:
                adjusted_end = node_point + exiting_direction * (node_size / 2)
                logger.debug(
                    "PathSegment[%s.%s] single-node puzzle_end extending by half-node %.3f along %s -> %s",
                    self.main_index,
                    self.secondary_index,
                    node_size / 2,
                    _format_vector(exiting_direction),
                    _format_vector(adjusted_end),
                )
            self.nodes[0].x = adjusted_end.X
            self.nodes[0].y = adjusted_end.Y
            self.nodes[0].z = adjusted_end.Z
            self.nodes[0].segment_end = True
            logger.debug(
                "PathSegment[%s.%s] single-node puzzle_end positioned at %s",
                self.main_index,
                self.secondary_index,
                _format_vector(adjusted_end),
            )
        else:
            # For nodes that are neither puzzle_start nor puzzle_end,
            # create start and end nodes on either side.
            if not self.nodes[0].puzzle_start and not self.nodes[0].puzzle_end:
                if next_start_node is not None:
                    next_is_circular = (
                        next_start_node.in_circular_grid
                        or next_curve_type == PathCurveType.ARC
                    )
                    if next_curve_type is not None:
                        adjusted_end = _node_to_vector(next_start_node)
                        is_circular_end = (
                            self.nodes[0].in_circular_grid
                            and next_is_circular
                        )
                        logger.debug(
                            "PathSegment[%s.%s] single-node snapped end to next start %s (fixed curve)",
                            self.main_index,
                            self.secondary_index,
                            _format_node(next_start_node),
                        )
                    else:
                        # For half adjustment, use arc midpoint if the node is circular.
                        if (
                            self.nodes[0].in_circular_grid
                            and next_is_circular
                        ):
                            is_circular_end = True
                            adjusted_end = midpoint(
                                node_point,
                                _node_to_vector(next_start_node),
                                circular=True,
                            )
                            logger.debug(
                                "PathSegment[%s.%s] single-node using circular midpoint towards %s -> %s",
                                self.main_index,
                                self.secondary_index,
                                _format_node(next_start_node),
                                _format_vector(adjusted_end),
                            )
                        else:
                            adjusted_end = midpoint(
                                node_point,
                                _node_to_vector(next_start_node),
                                circular=False,
                            )
                            logger.debug(
                                "PathSegment[%s.%s] single-node using linear midpoint towards %s -> %s",
                                self.main_index,
                                self.secondary_index,
                                _format_node(next_start_node),
                                _format_vector(adjusted_end),
                            )
                else:
                    adjusted_end = node_point
                    logger.debug(
                        "PathSegment[%s.%s] single-node end remains at original position %s",
                        self.main_index,
                        self.secondary_index,
                        _format_vector(adjusted_end),
                    )

                end_node = Node(adjusted_end.X, adjusted_end.Y, adjusted_end.Z)
                end_node.in_circular_grid = is_circular_end
                end_node.in_rectangular_grid = self.nodes[0].in_rectangular_grid
                end_node.segment_end = True

                self.nodes.insert(0, start_node)
                self.nodes.append(end_node)
                logger.debug(
                    "PathSegment[%s.%s] single-node expanded with start %s and end %s (circular_end=%s)",
                    self.main_index,
                    self.secondary_index,
                    _format_node(start_node),
                    _format_node(end_node),
                    is_circular_end,
                )
            else:
                # If already flagged as puzzle_start or puzzle_end, simply mark them.
                self.nodes[0].segment_start = self.nodes[0].puzzle_start
                self.nodes[0].segment_end = self.nodes[0].puzzle_end
                if self.nodes[0].segment_end and is_circular_end:
                    self.nodes[0].in_circular_grid = True
                logger.debug(
                    "PathSegment[%s.%s] single-node retained flags start=%s end=%s",
                    self.main_index,
                    self.secondary_index,
                    self.nodes[0].segment_start,
                    self.nodes[0].segment_end,
                )

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
            end_node.in_circular_grid = self.nodes[-1].in_circular_grid
            end_node.in_rectangular_grid = self.nodes[-1].in_rectangular_grid
            end_node.occupied = True
            end_node.segment_end = True
            self.nodes[-1].segment_end = False
            self.nodes.append(end_node)
            return True

        return False


def is_same_location(p1: Vector, p2: Vector, tol: float = 1e-7) -> bool:
    """
    Returns True if p1 and p2 are effectively the same point within a given tolerance.
    """
    return (p1 - p2).length < tol
