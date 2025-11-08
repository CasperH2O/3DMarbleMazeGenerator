# cad/curve_detection.py

import logging
import math
from typing import Optional

from config import Path, PathCurveType
from puzzle.node import Node

logger = logging.getLogger(__name__)


def _format_node(node: Optional[Node]) -> str:
    """Return a compact string representation of a node for logging."""
    if node is None:
        return "None"
    return f"({node.x:.3f}, {node.y:.3f}, {node.z:.3f})"


def _format_node_list(nodes: list[Node]) -> str:
    """Return a compact string representation of multiple nodes for logging."""
    return "[" + ", ".join(_format_node(node) for node in nodes) + "]"


def detect_curves(nodes: list[Node], curve_id_counter: int) -> int:
    """
    Detect curves in the given nodes based on the configuration.

    Args:
        nodes (list[Node]): A list of nodes to analyze for curves.
        curve_id_counter (int): The starting curve ID.

    Returns:
        int: The next curve ID after processing.
    """
    logger.debug(
        "detect_curves: starting with %s nodes and curve_id_counter=%s",
        len(nodes),
        curve_id_counter,
    )

    if PathCurveType.S_CURVE in Path.PATH_CURVE_TYPE:
        logger.debug("detect_curves: S-curve detection enabled")
        curve_id_counter = detect_s_curves(nodes, curve_id_counter)

    if PathCurveType.CURVE_90_DEGREE_SINGLE_PLANE in Path.PATH_CURVE_TYPE:
        logger.debug("detect_curves: 90-degree arc detection enabled")
        curve_id_counter = detect_arcs(nodes, curve_id_counter)

    if PathCurveType.ARC in Path.PATH_CURVE_TYPE:
        logger.debug("detect_curves: circular segment detection enabled")
        curve_id_counter = detect_circular_segments(nodes, curve_id_counter)

    logger.debug("detect_curves: completed with curve_id_counter=%s", curve_id_counter)
    return curve_id_counter


def detect_s_curves(nodes: list[Node], curve_id_counter: int) -> int:
    s_curve_length = 6  # Number of nodes in an S-curve
    if len(nodes) < s_curve_length:
        logger.debug(
            "detect_s_curves: skipping detection, require %s nodes but received %s",
            s_curve_length,
            len(nodes),
        )
        return curve_id_counter  # Not enough nodes to form an S-curve

    for i in range(len(nodes) - s_curve_length + 1):
        segment = nodes[i : i + s_curve_length]
        logger.debug(
            "detect_s_curves: evaluating segment index=%s nodes=%s",
            i,
            _format_node_list(segment),
        )
        if is_in_plane(segment):
            # Split into three parts and check linearity and direction changes
            first_part = segment[:3]
            middle_segment = segment[2:4]
            last_part = segment[3:]

            # Check if first and last parts are linear in the same direction and middle segment changes direction
            for axis in ["x", "y", "z"]:
                if (
                    is_linear(first_part, axis)
                    and is_linear(last_part, axis)
                    and not is_linear(middle_segment, axis)
                ):
                    # Compute direction vectors
                    first_vector = vector_between_nodes(first_part[0], first_part[1])
                    last_vector = vector_between_nodes(last_part[-2], last_part[-1])

                    # Normalize vectors
                    first_vector_normalized = normalize_vector(first_vector)
                    last_vector_normalized = normalize_vector(last_vector)

                    # Compute dot product
                    dot_product = sum(
                        first * last
                        for first, last in zip(
                            first_vector_normalized, last_vector_normalized
                        )
                    )

                    # Threshold for same direction
                    direction_threshold = 0.95

                    logger.debug(
                        "detect_s_curves: axis=%s dot_product=%.3f threshold=%.3f",
                        axis,
                        dot_product,
                        direction_threshold,
                    )
                    if dot_product > direction_threshold:
                        # Mark nodes as part of an S-curve
                        for node in segment[1:-1]:  # Exclude first and last nodes
                            node.path_curve_type = PathCurveType.S_CURVE
                            node.used_in_curve = True  # Mark node as used
                            node.curve_id = curve_id_counter  # Assign curve ID
                        logger.debug(
                            "detect_s_curves: detected S-curve curve_id=%s indices=[%s,%s) nodes=%s",
                            curve_id_counter,
                            i,
                            i + s_curve_length,
                            _format_node_list(segment[1:-1]),
                        )
                        curve_id_counter += 1  # Increment curve ID counter
                        break  # No need to check other axes
        else:
            logger.debug(
                "detect_s_curves: skipping segment index=%s not in single plane", i
            )

    return curve_id_counter


def detect_circular_segments(
    nodes: list[Node],
    curve_id_counter: int,
) -> int:
    """
    Detect consecutive nodes flagged as belonging to the circular grid and mark them as ARC curves.
    Requires at minimum of 2 nodes in a run to consider it a valid circular segment.

    Args:
        nodes: The list of nodes to process.
        curve_id_counter: The current curve ID counter.

    Returns:
        The updated curve ID counter.
    """
    min_guard_nodes = 2

    logger.debug(
        "detect_circular_segments: starting with %s nodes, curve_id_counter=%s, min_guard_nodes=%s",
        len(nodes),
        curve_id_counter,
        min_guard_nodes,
    )

    i = 0
    while i < len(nodes):
        # Check if the node is circular
        if nodes[i].in_circular_grid:
            start = i
            # Continue while subsequent nodes are circular.
            while i < len(nodes) and nodes[i].in_circular_grid:
                i += 1
            block_len = i - start

            # Prevent making segments of a single node, can happen near start and end of puzzle
            if block_len < min_guard_nodes:
                logger.debug(
                    "detect_circular_segments: skipping short circular run len=%s (<%s) at indices=[%s,%s) nodes=%s",
                    block_len,
                    min_guard_nodes,
                    start,
                    i,
                    _format_node_list(nodes[start:i]),
                )
                continue

            # Valid circular run — mark all nodes in the block
            for j in range(start, i):
                node = nodes[j]
                node.path_curve_type = PathCurveType.ARC
                node.used_in_curve = True
                node.curve_id = curve_id_counter

            logger.debug(
                "detect_circular_segments: ARC curve_id=%s indices=[%s,%s) len=%s nodes=%s",
                curve_id_counter,
                start,
                i,
                block_len,
                _format_node_list(nodes[start:i]),
            )
            curve_id_counter += 1
        else:
            i += 1

    logger.debug(
        "detect_circular_segments: completed with curve_id_counter=%s", curve_id_counter
    )
    return curve_id_counter


def detect_arcs(nodes: list[Node], curve_id_counter: int) -> int:
    curve_lengths = [
        5,
        3,
    ]  # Marking 5 and 3 nodes, but segments are of length n + 2 (7 and 5)
    n_to_curve_type = {
        5: PathCurveType.CURVE_90_DEGREE_SINGLE_PLANE,
        3: PathCurveType.CURVE_90_DEGREE_SINGLE_PLANE,
    }

    for n in curve_lengths:
        segment_length = n + 2  # Actual segment length to consider
        if len(nodes) < segment_length:
            logger.debug(
                "detect_arcs: skipping curve length=%s requires segment_length=%s but only %s nodes",
                n,
                segment_length,
                len(nodes),
            )
            continue  # Not enough nodes for this curve length

        for i in range(len(nodes) - segment_length + 1):
            segment = nodes[i : i + segment_length]
            logger.debug(
                "detect_arcs: evaluating length=%s segment index=%s nodes=%s",
                n,
                i,
                _format_node_list(segment),
            )

            # Check if any node in the segment (excluding first and last) has already been used
            middle_nodes = segment[1:-1]
            if any(node.used_in_curve for node in middle_nodes):
                logger.debug(
                    "detect_arcs: skipping segment index=%s length=%s due to reused middle nodes",
                    i,
                    n,
                )
                continue  # Skip overlapping segments

            if check_90_deg_curve(segment):
                # Find the sharp corner triad first
                triad_nodes = _trim_middle_nodes_to_corner_triad(middle_nodes)

                # Expand, target_count == n (the number of middle nodes to mark).
                nodes_to_mark = _expand_triad_to_centered_span(
                    middle_nodes=middle_nodes,
                    triad_nodes=triad_nodes,
                    target_count=n,
                )

                # Mark selected nodes as part of the curve
                for node in nodes_to_mark:
                    node.path_curve_type = n_to_curve_type[n]
                    node.used_in_curve = True  # Mark node as used
                    node.curve_id = curve_id_counter  # Assign curve ID

                logger.debug(
                    "detect_arcs: detected 90-degree curve curve_id=%s length=%s indices=[%s,%s) middle_nodes=%s",
                    curve_id_counter,
                    n,
                    i,
                    i + segment_length,
                    _format_node_list(nodes_to_mark),
                )
                curve_id_counter += 1  # Increment curve ID counter

    return curve_id_counter


def _expand_triad_to_centered_span(
    middle_nodes: list[Node],
    triad_nodes: list[Node],
    target_count: int,
) -> list[Node]:
    """
    Return a contiguous, centered, odd-length window around the triad's center node.
    """
    triad_center_node = triad_nodes[1]  # center of the triad
    center_index = middle_nodes.index(triad_center_node)

    half_span = (target_count - 1) // 2
    start_index = center_index - half_span
    end_index = center_index + half_span + 1  # slice end is exclusive

    # Slice appropriately
    return middle_nodes[start_index:end_index]


def _trim_middle_nodes_to_corner_triad(nodes: list[Node]) -> list[Node]:
    """Return only the corner triad that defines a 90-degree turn.

    The detector can return a window that includes extra collinear nodes on either
    side of the actual corner. Those nodes should remain available for straight
    segments, so we trim the selection to the three nodes that form the sharpest
    bend in the window.
    """

    if len(nodes) <= 3:
        return nodes

    directions: list[tuple[float, float, float]] = []
    for idx in range(1, len(nodes)):
        previous_node = nodes[idx - 1]
        current_node = nodes[idx]
        directions.append(
            (
                current_node.x - previous_node.x,
                current_node.y - previous_node.y,
                current_node.z - previous_node.z,
            )
        )

    max_bend_index = 1
    max_score = -1.0

    for idx in range(1, len(directions)):
        first_vector = directions[idx - 1]
        second_vector = directions[idx]
        score = 1.0 - abs(_cosine_of_angle(first_vector, second_vector))
        if score > max_score:
            max_score = score
            max_bend_index = idx

    corner_index = max_bend_index
    trimmed: list[Node] = []
    if corner_index - 1 >= 0:
        trimmed.append(nodes[corner_index - 1])
    trimmed.append(nodes[corner_index])
    if corner_index + 1 < len(nodes):
        trimmed.append(nodes[corner_index + 1])
    return trimmed


def _cosine_of_angle(
    first_vector: tuple[float, float, float], second_vector: tuple[float, float, float]
) -> float:
    """Return the cosine of the angle between two vectors."""

    first_length = math.sqrt(sum(component * component for component in first_vector))
    second_length = math.sqrt(sum(component * component for component in second_vector))
    if first_length == 0 or second_length == 0:
        return 1.0
    dot_product = sum(
        first_component * second_component
        for first_component, second_component in zip(first_vector, second_vector)
    )
    return dot_product / (first_length * second_length)


def is_in_plane(pts: list[Node]) -> bool:
    x_vals = [pt.x for pt in pts]
    y_vals = [pt.y for pt in pts]
    z_vals = [pt.z for pt in pts]
    return len(set(x_vals)) == 1 or len(set(y_vals)) == 1 or len(set(z_vals)) == 1


def is_linear(pts: list[Node], axis: str) -> bool:
    if axis == "x":
        return all(pt.y == pts[0].y and pt.z == pts[0].z for pt in pts)
    elif axis == "y":
        return all(pt.x == pts[0].x and pt.z == pts[0].z for pt in pts)
    elif axis == "z":
        return all(pt.x == pts[0].x and pt.y == pts[0].y for pt in pts)
    return False


def vector_between_nodes(n1: Node, n2: Node):
    return n2.x - n1.x, n2.y - n1.y, n2.z - n1.z


def check_90_deg_curve(segment: list[Node]) -> bool:
    if not is_in_plane(segment):
        return False

    # Determine the plane and the axes involved
    x_vals = [pt.x for pt in segment]
    y_vals = [pt.y for pt in segment]
    z_vals = [pt.z for pt in segment]

    if len(set(x_vals)) == 1:
        # Nodes are in the YZ plane
        plane_axes = ["y", "z"]
    elif len(set(y_vals)) == 1:
        # Nodes are in the XZ plane
        plane_axes = ["x", "z"]
    elif len(set(z_vals)) == 1:
        # Nodes are in the XY plane
        plane_axes = ["x", "y"]
    else:
        return False  # Should not happen as we already checked is_in_plane

    # Split the segment into first and second halves, overlapping at the middle node
    length = len(segment)
    middle_index = length // 2  # Middle index (integer division)

    # Include the middle node in both halves
    first_half = segment[
        : middle_index + 1
    ]  # Nodes from start to middle node (inclusive)
    second_half = segment[middle_index:]  # Nodes from middle node to end

    # Check if nodes in each half are moving in a consistent direction
    if not all_vectors_aligned_in_plane(first_half, plane_axes):
        return False
    if not all_vectors_aligned_in_plane(second_half, plane_axes):
        return False

    # Compute direction vectors for each half
    first_direction = vector_in_plane(first_half[0], first_half[-1], plane_axes)
    second_direction = vector_in_plane(second_half[0], second_half[-1], plane_axes)

    # Normalize direction vectors
    first_direction = normalize_vector(first_direction)
    second_direction = normalize_vector(second_direction)

    # Compute the angle between the two direction vectors
    angle = angle_between_vectors(first_direction, second_direction)

    # Check if the angle is approximately 90 degrees
    if not is_close(angle, 90):
        return False

    return True


def all_vectors_aligned_in_plane(pts: list[Node], plane_axes: list[str]) -> bool:
    if len(pts) < 2:
        return True  # Not enough points to check alignment

    # Compute the main direction vector for the half
    main_vector = vector_in_plane(pts[0], pts[-1], plane_axes)
    main_vector = normalize_vector(main_vector)

    for i in range(len(pts) - 1):
        # Compute the vector between consecutive nodes
        v = vector_in_plane(pts[i], pts[i + 1], plane_axes)
        v = normalize_vector(v)
        dot_product = sum(m * n for m, n in zip(main_vector, v))
        # Check if the vectors are aligned (dot product close to 1)
        if dot_product < 0.95:  # Threshold can be adjusted
            return False
    return True


def vector_in_plane(n1: Node, n2: Node, plane_axes: list[str]):
    v = []
    for axis in plane_axes:
        coord1 = getattr(n1, axis)
        coord2 = getattr(n2, axis)
        v.append(coord2 - coord1)
    return v


def normalize_vector(v):
    magnitude = math.sqrt(sum(c**2 for c in v))
    if magnitude == 0:
        return [0 for _ in v]
    return [c / magnitude for c in v]


def angle_between_vectors(v1, v2):
    v1 = normalize_vector(v1)
    v2 = normalize_vector(v2)
    dot_product = sum(a * b for a, b in zip(v1, v2))
    # Clamp the dot product to avoid numerical errors
    dot_product = max(min(dot_product, 1), -1)
    angle_rad = math.acos(dot_product)
    angle_deg = math.degrees(angle_rad)
    return angle_deg


def is_close(a, b, tol=5):
    return abs(a - b) <= tol
