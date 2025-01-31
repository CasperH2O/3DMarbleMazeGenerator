# cad/curve_detection.py

from typing import List
from puzzle.node import Node
import math
from config import PathCurveType, Path

def detect_curves(nodes: List[Node], curve_id_counter: int) -> int:
    """
    Detect curves in the given nodes based on the configuration.

    Args:
        nodes (List[Node]): A list of nodes to analyze for curves.
        curve_id_counter (int): The starting curve ID.

    Returns:
        int: The next curve ID after processing.
    """
    if PathCurveType.S_CURVE in Path.PATH_CURVE_TYPE:
        curve_id_counter = detect_s_curves(nodes, curve_id_counter)

    if PathCurveType.DEGREE_90_SINGLE_PLANE in Path.PATH_CURVE_TYPE:
        curve_id_counter = detect_arcs(nodes, curve_id_counter)

    return curve_id_counter


def detect_s_curves(nodes: List[Node], curve_id_counter: int) -> int:
    s_curve_length = 6  # Number of nodes in an S-curve
    if len(nodes) < s_curve_length:
        return curve_id_counter  # Not enough nodes to form an S-curve

    for i in range(len(nodes) - s_curve_length + 1):
        segment = nodes[i:i + s_curve_length]
        if is_in_plane(segment):
            # Split into three parts and check linearity and direction changes
            first_part = segment[:3]
            middle_segment = segment[2:4]
            last_part = segment[3:]

            # Check if first and last parts are linear in the same direction and middle segment changes direction
            for axis in ['x', 'y', 'z']:
                if is_linear(first_part, axis) and is_linear(last_part, axis) and not is_linear(middle_segment, axis):
                    # Compute direction vectors
                    first_vector = vector_between_nodes(first_part[0], first_part[1])
                    last_vector = vector_between_nodes(last_part[-2], last_part[-1])

                    # Normalize vectors
                    first_vector_normalized = normalize_vector(first_vector)
                    last_vector_normalized = normalize_vector(last_vector)

                    # Compute dot product
                    dot_product = sum(f * l for f, l in zip(first_vector_normalized, last_vector_normalized))

                    # Threshold for same direction
                    direction_threshold = 0.95

                    if dot_product > direction_threshold:
                        # Mark nodes as part of an S-curve
                        for node in segment[1:-1]:  # Exclude first and last nodes
                            node.path_curve_type = PathCurveType.S_CURVE
                            node.used_in_curve = True  # Mark node as used
                            node.curve_id = curve_id_counter  # Assign curve ID
                        curve_id_counter += 1  # Increment curve ID counter
                        break  # No need to check other axes

    return curve_id_counter


def detect_arcs(nodes: List[Node], curve_id_counter: int) -> int:
    curve_lengths = [5, 3]  # Marking 5 and 3 nodes, but segments are of length n + 2 (7 and 5)
    n_to_curve_type = {
        5: PathCurveType.DEGREE_90_SINGLE_PLANE,
        3: PathCurveType.DEGREE_90_SINGLE_PLANE,
    }

    for n in curve_lengths:
        segment_length = n + 2  # Actual segment length to consider
        if len(nodes) < segment_length:
            continue  # Not enough nodes for this curve length

        for i in range(len(nodes) - segment_length + 1):
            segment = nodes[i:i + segment_length]

            # Check if any node in the segment (excluding first and last) has already been used
            middle_nodes = segment[1:-1]
            if any(getattr(node, 'used_in_curve', False) for node in middle_nodes):
                continue  # Skip overlapping segments

            if check_90_deg_curve(segment):
                # Mark only the middle nodes as part of the curve
                for node in middle_nodes:
                    node.path_curve_type = n_to_curve_type[n]
                    node.used_in_curve = True  # Mark node as used
                    node.curve_id = curve_id_counter  # Assign curve ID
                curve_id_counter += 1  # Increment curve ID counter

    return curve_id_counter

def is_in_plane(pts: List[Node]) -> bool:
    x_vals = [pt.x for pt in pts]
    y_vals = [pt.y for pt in pts]
    z_vals = [pt.z for pt in pts]
    return len(set(x_vals)) == 1 or len(set(y_vals)) == 1 or len(set(z_vals)) == 1

def is_linear(pts: List[Node], axis: str) -> bool:
    if axis == 'x':
        return all(pt.y == pts[0].y and pt.z == pts[0].z for pt in pts)
    elif axis == 'y':
        return all(pt.x == pts[0].x and pt.z == pts[0].z for pt in pts)
    elif axis == 'z':
        return all(pt.x == pts[0].x and pt.y == pts[0].y for pt in pts)
    return False

def vector_between_nodes(n1: Node, n2: Node):
    return n2.x - n1.x, n2.y - n1.y, n2.z - n1.z

def check_90_deg_curve(segment: List[Node]) -> bool:
    if not is_in_plane(segment):
        return False

    # Determine the plane and the axes involved
    x_vals = [pt.x for pt in segment]
    y_vals = [pt.y for pt in segment]
    z_vals = [pt.z for pt in segment]

    if len(set(x_vals)) == 1:
        # Nodes are in the YZ plane
        plane_axes = ['y', 'z']
    elif len(set(y_vals)) == 1:
        # Nodes are in the XZ plane
        plane_axes = ['x', 'z']
    elif len(set(z_vals)) == 1:
        # Nodes are in the XY plane
        plane_axes = ['x', 'y']
    else:
        return False  # Should not happen as we already checked is_in_plane

    # Split the segment into first and second halves, overlapping at the middle node
    length = len(segment)
    middle_index = length // 2  # Middle index (integer division)

    # Include the middle node in both halves
    first_half = segment[:middle_index+1]  # Nodes from start to middle node (inclusive)
    second_half = segment[middle_index:]   # Nodes from middle node to end

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

def all_vectors_aligned_in_plane(pts: List[Node], plane_axes: List[str]) -> bool:
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

def vector_in_plane(n1: Node, n2: Node, plane_axes: List[str]):
    v = []
    for axis in plane_axes:
        coord1 = getattr(n1, axis)
        coord2 = getattr(n2, axis)
        v.append(coord2 - coord1)
    return v

def normalize_vector(v):
    magnitude = math.sqrt(sum(c ** 2 for c in v))
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