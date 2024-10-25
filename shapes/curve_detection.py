from typing import List
from puzzle.node import Node

def detect_curves(nodes: List[Node]):
    detect_s_curves(nodes)
    detect_arcs(nodes)

def detect_s_curves(nodes: List[Node]):
    s_curve_length = 6  # Number of nodes in an S-curve
    if len(nodes) < s_curve_length:
        return  # Not enough nodes to form an S-curve

    for i in range(len(nodes) - s_curve_length + 1):
        segment = nodes[i:i + s_curve_length]
        if is_in_plane(segment):
            # Split into three parts and check linearity and direction changes
            first_part = segment[:3]
            middle_segment = segment[2:4]
            last_part = segment[3:]

            # Check if first and last parts are linear in the same direction and middle segment changes direction
            for axis in ['x', 'y', 'z']:
                if (is_linear(first_part, axis) and is_linear(last_part, axis) and not is_linear(middle_segment, axis)):
                    # Mark nodes as part of an S-curve
                    for node in segment[1:-1]:  # Exclude first and last nodes
                        node.path_curve_type = 's_curve'
                    break  # No need to check other axes

def detect_arcs(nodes: List[Node]):
    # Small 90-degree arc detection (5 nodes)
    small_arc_length = 5
    for i in range(len(nodes) - small_arc_length + 1):
        segment = nodes[i:i + small_arc_length]
        if check_90_deg_curve(segment):
            # Mark nodes as part of a small 90-degree arc
            for node in segment[1:-1]:
                node.path_curve_type = '90_degree_single_plane_small'

    # Large 90-degree arc detection (7 nodes)
    large_arc_length = 7
    for i in range(len(nodes) - large_arc_length + 1):
        segment = nodes[i:i + large_arc_length]
        if check_90_deg_curve(segment, large=True):
            # Mark nodes as part of a large 90-degree arc
            for node in segment[1:-1]:
                node.path_curve_type = '90_degree_single_plane_big'

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

def check_90_deg_curve(segment: List[Node], large=False) -> bool:
    if not is_in_plane(segment):
        return False

    split_index = 4 if large else 3
    first_half = segment[:split_index]
    second_half = segment[split_index:]

    for axis in ['x', 'y', 'z']:
        if is_linear(first_half, axis):
            other_axes = [a for a in ['x', 'y', 'z'] if a != axis]
            if any(is_linear(second_half, other_axis) for other_axis in other_axes):
                return True
    return False