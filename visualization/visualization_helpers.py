# visualization/visualization_helpers.py

import colorsys
import math
import random
from typing import Iterable, List, Tuple

import numpy as np
import plotly.graph_objects as go
from build123d import Spline, Vector, Polyline
from geomdl import BSpline, utilities

from cad.cases.case_model_base import Case
from cad.path_segment import PathSegment
from config import Config, PathCurveType, PathSegmentDesignStrategy
from puzzle.grid_layouts.grid_layout_box import BoxCasing
from puzzle.grid_layouts.grid_layout_cylinder import CylinderCasing
from puzzle.grid_layouts.grid_layout_sphere import SphereCasing
from puzzle.node import Node


def _segment_endpoint_tangent(adjacent_segment: PathSegment, *, at_end: bool) -> Vector:

    if at_end:
        n1, n2 = adjacent_segment.nodes[-2], adjacent_segment.nodes[-1]
    else:
        n1, n2 = adjacent_segment.nodes[0], adjacent_segment.nodes[1]
    return Polyline((n1.x, n1.y, n1.z), (n2.x, n2.y, n2.z)) % (0 if at_end else 1)

def _sample_build123d_spline(
    spline_nodes: list[Node],
    previous_segment: PathSegment,
    next_segment: PathSegment,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample the same Build123D/OCCT spline type used for physical path creation."""
    spline_points = [Vector(node.x, node.y, node.z) for node in spline_nodes]
    spline = Spline(
        spline_points,
        tangents=[
            _segment_endpoint_tangent(previous_segment, at_end=True),
            _segment_endpoint_tangent(next_segment, at_end=False),
        ],
    )

    sampled_positions = spline.positions(np.linspace(0, 1, 50))
    sampled_points = np.array(
        [[position.X, position.Y, position.Z] for position in sampled_positions]
    )
    return sampled_points[:, 0], sampled_points[:, 1], sampled_points[:, 2]


def plot_nodes(
    nodes: list[Node],
    segments: list[PathSegment] | None = None,
    group_name: str = "",
    obstacles_present: bool = False,
) -> list[go.Scatter3d]:
    """
    Groups nodes by their primary property so that the legend only displays the primary label,
    while the hover text for each marker shows all applicable flags on separate lines.

    Based on segments, any nodes within those segments that are flagged as
    segment_start or segment_end are merged into the local node list

    # TODO some optimization, code consolidation with flags and labels
    """
    # Start with a local copy; don't mutate the caller's list
    all_nodes: list[Node] = list(nodes) if nodes else []

    # Optionally merge segment start/end nodes
    if segments:
        for segment in segments:
            for node in segment.nodes:
                if getattr(node, "segment_start", False) or getattr(
                    node, "segment_end", False
                ):
                    if not any(
                        abs(n.x - node.x) < 1e-6
                        and abs(n.y - node.y) < 1e-6
                        and abs(n.z - node.z) < 1e-6
                        for n in all_nodes
                    ):
                        all_nodes.append(node)

    # Define the priority order for determining the primary flag.
    priority_flags = [
        ("puzzle_start", "Puzzle Start"),
        ("puzzle_end", "Puzzle End"),
        ("mounting", "Mounting"),
        ("waypoint", "Waypoint"),
        ("segment_start", "Segment Start"),
        ("segment_end", "Segment End"),
        ("occupied", "Occupied"),
        ("circular", "Circular"),
        ("overlap_allowed", "Overlap"),
    ]

    groups = {}  # key: primary flag; value: dict with x, y, z lists and hover texts
    seen = set()  # To avoid duplicate nodes based on coordinates only

    for node in all_nodes:
        labels = []
        if node.puzzle_start:
            labels.append("Puzzle Start")
        if node.puzzle_end:
            labels.append("Puzzle End")
        if node.mounting:
            labels.append("Mounting")
        if node.waypoint:
            labels.append("Waypoint")
        if node.segment_start:
            labels.append("Segment Start")
        if node.segment_end:
            labels.append("Segment End")
        if node.occupied:
            labels.append("Occupied")
        if node.in_circular_grid:
            labels.append("Circular")
        if node.overlap_allowed:
            labels.append("Overlap")
        if not labels:
            labels.append("Regular")

        # Determine the primary flag (for the legend) based on the defined priority.
        primary = None
        for flag, label in priority_flags:
            if flag == "circular":
                if node.in_circular_grid:
                    primary = label
                    break
            else:
                if getattr(node, flag, False):
                    primary = label
                    break
        if primary is None:
            primary = "Regular"

        # Construct the hover text by joining all applicable flags with line breaks.
        hover_text = "<br>".join(labels)

        # Use only the coordinates (rounded) for duplicate filtering.
        coord_key = (round(node.x, 6), round(node.y, 6), round(node.z, 6))
        if coord_key in seen:
            continue
        seen.add(coord_key)

        # Group nodes by their primary flag.
        if primary not in groups:
            groups[primary] = {"x": [], "y": [], "z": [], "hover": []}
        groups[primary]["x"].append(node.x)
        groups[primary]["y"].append(node.y)
        groups[primary]["z"].append(node.z)
        groups[primary]["hover"].append(hover_text)

    # Map primary flags to colors and sizes.
    color_map = {
        "Puzzle Start": "yellow",
        "Puzzle End": "magenta",
        "Mounting": "purple",
        "Waypoint": "blue",
        "Segment Start": "cyan",
        "Segment End": "white",
        "Occupied": "red",
        "Circular": "orange",
        "Overlap": "pink",
        "Regular": "green",
    }
    size_map = {
        "Puzzle Start": 5,
        "Puzzle End": 5,
        "Mounting": 4,
        "Waypoint": 3,
        "Segment Start": 4,
        "Segment End": 4,
        "Occupied": 3,
        "Overlap": 3,
        "Circular": 1,
        "Regular": 1,
    }

    traces = []
    # Create a trace for each group using the primary flag as the legend label.
    for primary, coords in groups.items():
        trace = go.Scatter3d(
            x=coords["x"],
            y=coords["y"],
            z=coords["z"],
            mode="markers",
            marker=dict(
                color=color_map.get(primary, "green"), size=size_map.get(primary, 1)
            ),
            name=primary,  # Legend shows only the primary flag.
            legendgroup=group_name,
            text=coords["hover"],  # Custom detailed info (all flags, with line breaks).
            hovertemplate="X: %{x}<br>Y: %{y}<br>Z: %{z}<br>%{text}<extra></extra>",
            visible=(
                "legendonly"
                if obstacles_present
                and primary
                in {
                    "Regular",
                    "Circular",
                    "Overlap",
                    "Occupied",
                }
                else True
            ),
        )
        traces.append(trace)
    return traces


def plot_casing(casing: Case) -> list[go.Scatter3d]:
    if isinstance(casing, SphereCasing):
        return plot_sphere_casing(casing)
    elif isinstance(casing, BoxCasing):
        return plot_box_casing(casing)
    elif isinstance(casing, CylinderCasing):
        return plot_cylinder_casing(casing)
    else:
        return [go.Scatter3d()]  # Empty graph


def plot_cylinder_casing(casing: CylinderCasing) -> list[go.Scatter3d]:
    """
    Draw a minimal wireframe for a vertical cylinder centered at the origin:
    - Top and bottom circles (z = ± half height)
    - A set of vertical lines to suggest the side wall
    """
    r = casing.diameter / 2
    z_top = casing.height / 2
    z_bot = -casing.height / 2

    casing_traces = []

    # top and bottom circles
    theta = np.linspace(0, 2 * np.pi, 100)

    x_top = r * np.cos(theta)
    y_top = r * np.sin(theta)
    z_top_arr = np.full_like(theta, z_top)

    top_circle = go.Scatter3d(
        x=x_top,
        y=y_top,
        z=z_top_arr,
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
    )
    casing_traces.append(top_circle)

    x_bot = r * np.cos(theta)
    y_bot = r * np.sin(theta)
    z_bot_arr = np.full_like(theta, z_bot)

    bottom_circle = go.Scatter3d(
        x=x_bot,
        y=y_bot,
        z=z_bot_arr,
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
    )
    casing_traces.append(bottom_circle)

    # vertical generator lines (evenly spaced by angle)
    n_generators = 8
    gen_angles = np.linspace(0, 2 * np.pi, n_generators, endpoint=False)

    x_lines, y_lines, z_lines = [], [], []
    for a in gen_angles:
        x = r * np.cos(a)
        y = r * np.sin(a)
        # line from bottom to top, then None to break
        x_lines.extend([x, x, None])
        y_lines.extend([y, y, None])
        z_lines.extend([z_bot, z_top, None])

    verticals = go.Scatter3d(
        x=x_lines,
        y=y_lines,
        z=z_lines,
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
    )
    casing_traces.append(verticals)

    return casing_traces


def plot_sphere_casing(casing: SphereCasing) -> list[go.Scatter3d]:
    theta = np.linspace(0, 2 * np.pi, 100)
    radius = casing.diameter / 2

    casing_traces = []

    # Circle in XY plane (z = 0)
    x_circle_xy = radius * np.cos(theta)
    y_circle_xy = radius * np.sin(theta)
    z_circle_xy = np.zeros_like(theta)
    circle_trace_xy = go.Scatter3d(
        x=x_circle_xy,
        y=y_circle_xy,
        z=z_circle_xy,
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
    )
    casing_traces.append(circle_trace_xy)

    # Circle in XZ plane (y = 0)
    x_circle_xz = radius * np.cos(theta)
    y_circle_xz = np.zeros_like(theta)
    z_circle_xz = radius * np.sin(theta)
    circle_trace_xz = go.Scatter3d(
        x=x_circle_xz,
        y=y_circle_xz,
        z=z_circle_xz,
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
    )
    casing_traces.append(circle_trace_xz)

    # Circle in YZ plane (x = 0)
    x_circle_yz = np.zeros_like(theta)
    y_circle_yz = radius * np.cos(theta)
    z_circle_yz = radius * np.sin(theta)
    circle_trace_yz = go.Scatter3d(
        x=x_circle_yz,
        y=y_circle_yz,
        z=z_circle_yz,
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
    )
    casing_traces.append(circle_trace_yz)

    return casing_traces


def plot_box_casing(casing: BoxCasing) -> list[go.Scatter3d]:
    half_width = casing.width / 2
    half_height = casing.height / 2
    half_length = casing.length / 2

    # Define the 8 corners of the box
    corners = np.array(
        [
            [-half_width, -half_length, -half_height],
            [half_width, -half_length, -half_height],
            [half_width, half_length, -half_height],
            [-half_width, half_length, -half_height],
            [-half_width, -half_length, half_height],
            [half_width, -half_length, half_height],
            [half_width, half_length, half_height],
            [-half_width, half_length, half_height],
        ]
    )

    # Define the edges as pairs of indices into the corners array
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),  # Bottom face
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),  # Top face
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),  # Vertical edges
    ]

    # Create lists for edge coordinates
    x_lines = []
    y_lines = []
    z_lines = []

    for edge in edges:
        for idx in edge:
            x_lines.append(corners[idx][0])
            y_lines.append(corners[idx][1])
            z_lines.append(corners[idx][2])
        x_lines.append(None)  # None to create breaks between lines
        y_lines.append(None)
        z_lines.append(None)

    box_trace = go.Scatter3d(
        x=x_lines,
        y=y_lines,
        z=z_lines,
        mode="lines",
        line=dict(color="gray", width=1),
        showlegend=False,
    )

    return [box_trace]


def _cube_wireframe_xyz(
    centers: list[tuple[float, float, float]], size: float
) -> tuple[list, list, list]:
    """Return x/y/z lists drawing wire-frame cubes of ``size`` at each centre.

    Cube edges are concatenated into a single polyline with ``None`` separators so
    all cubes render as one Scatter3d trace.
    """
    half = size / 2.0
    corner_offsets = [
        (-half, -half, -half),
        (half, -half, -half),
        (half, half, -half),
        (-half, half, -half),
        (-half, -half, half),
        (half, -half, half),
        (half, half, half),
        (-half, half, half),
    ]
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # bottom
        (4, 5), (5, 6), (6, 7), (7, 4),  # top
        (0, 4), (1, 5), (2, 6), (3, 7),  # verticals
    ]
    x_vals: list = []
    y_vals: list = []
    z_vals: list = []
    for cx, cy, cz in centers:
        corners = [(cx + ox, cy + oy, cz + oz) for ox, oy, oz in corner_offsets]
        for i, j in edges:
            x_vals += [corners[i][0], corners[j][0], None]
            y_vals += [corners[i][1], corners[j][1], None]
            z_vals += [corners[i][2], corners[j][2], None]
    return x_vals, y_vals, z_vals


def plot_node_cubes(
    nodes: list[Node], node_size: float, group_name: str = ""
) -> list[go.Scatter3d]:
    """
    Draw a wire-frame cube (edge length=node_size) centred on each node, as a
    single Scatter3d trace. Returns a one-element list (callers iterate).
    """
    if not nodes:
        return []
    centers = [(node.x, node.y, node.z) for node in nodes]
    x_vals, y_vals, z_vals = _cube_wireframe_xyz(centers, node_size)
    return [
        go.Scatter3d(
            x=x_vals,
            y=y_vals,
            z=z_vals,
            mode="lines",
            line=dict(width=1, color="gray"),
            opacity=0.5,
            showlegend=False,
            legendgroup=group_name,
        )
    ]


def plot_segments(segments: list[PathSegment]) -> list[go.Scatter3d]:
    """
    Build traces for PathSegments. Each (main_index, secondary_index) gets a stable color.
    """
    traces: list[go.Scatter3d] = []

    if not segments:
        return traces

    # Collect unique keys based main index and secondary_index
    unique_keys = sorted({(s.main_index, s.secondary_index) for s in segments})

    # Build a maximally-contrasting color list, shuffled but reproducible
    hsv_colors = _generate_distinct_hsv_colors(
        len(unique_keys), seed=Config.Puzzle.SEED
    )

    # Stable mapping: map each unique key to one color
    segment_colors: dict[tuple[int, int], str] = {
        seg_key: color for seg_key, color in zip(unique_keys, hsv_colors)
    }

    for segment_index, segment in enumerate(segments):
        previous_segment = segments[segment_index - 1] if segment_index > 0 else None
        next_segment = (
            segments[segment_index + 1]
            if segment_index < len(segments) - 1
            else None
        )

        # Assign unique colors based on main and secondary index
        seg_key = (segment.main_index, segment.secondary_index)
        segment_color = segment_colors[seg_key]

        # Hover text
        segment_name = (
            f"Segment ({segment.main_index}, {segment.secondary_index})<br>"
            f"Transition Type: {segment.transition_type}<br>"
            f"Design Strategy: {segment.design_strategy.value if segment.design_strategy is not None else 'N/A'}<br>"
            f"Curve Type: {segment.curve_type}<br>"
            f"Path Profile Type: {segment.path_profile_type.value if segment.path_profile_type is not None else 'N/A'}"
        )

        # Compute curve samples for this segment
        if segment.design_strategy == PathSegmentDesignStrategy.COMPOUND:
            # Bézier (B-Spline) for S-curve or 90° single-plane
            if segment.curve_type in [
                PathCurveType.S_CURVE,
                PathCurveType.CURVE_90_DEGREE_SINGLE_PLANE,
            ]:
                control_points = [[n.x, n.y, n.z] for n in segment.nodes]
                num_cpts = len(control_points)
                if num_cpts < 2:
                    x_vals = [n.x for n in segment.nodes]
                    y_vals = [n.y for n in segment.nodes]
                    z_vals = [n.z for n in segment.nodes]
                else:
                    degree = num_cpts - 1
                    curve = BSpline.Curve()
                    curve.degree = degree
                    curve.ctrlpts = control_points
                    curve.knotvector = utilities.generate_knot_vector(degree, num_cpts)
                    curve.delta = 0.001
                    curve.evaluate()
                    cpts = np.array(curve.evalpts)
                    x_vals, y_vals, z_vals = cpts[:, 0], cpts[:, 1], cpts[:, 2]
            else:
                # Pairwise: arc if both nodes are circular; else straight
                x_vals: list[float] = []
                y_vals: list[float] = []
                z_vals: list[float] = []
                for i in range(len(segment.nodes) - 1):
                    a = segment.nodes[i]
                    b = segment.nodes[i + 1]
                    # Both circular, generate arc
                    if a.in_circular_grid and b.in_circular_grid:
                        theta1 = math.atan2(a.y, a.x)
                        theta2 = math.atan2(b.y, b.x)
                        dtheta = theta2 - theta1
                        if dtheta > math.pi:
                            dtheta -= 2 * math.pi
                        elif dtheta < -math.pi:
                            dtheta += 2 * math.pi
                        num_points = 20
                        theta_values = np.linspace(theta1, theta1 + dtheta, num_points)
                        r1 = math.hypot(a.x, a.y)
                        r2 = math.hypot(b.x, b.y)
                        r_values = np.linspace(r1, r2, num_points)
                        xs = r_values * np.cos(theta_values)
                        ys = r_values * np.sin(theta_values)
                        zs = np.linspace(a.z, b.z, num_points)
                        if i > 0:
                            x_vals.extend(xs[1:])
                            y_vals.extend(ys[1:])
                            z_vals.extend(zs[1:])
                        else:
                            x_vals.extend(xs)
                            y_vals.extend(ys)
                            z_vals.extend(zs)
                    else:
                        if i == 0:
                            x_vals.append(a.x)
                            y_vals.append(a.y)
                            z_vals.append(a.z)
                        x_vals.append(b.x)
                        y_vals.append(b.y)
                        z_vals.append(b.z)
        elif segment.design_strategy == PathSegmentDesignStrategy.SPLINE:
            total_nodes = segment.nodes
            spline_nodes = [total_nodes[0], total_nodes[-1]] if len(total_nodes) >= 2 else total_nodes
            xs = [node.x for node in spline_nodes]
            ys = [node.y for node in spline_nodes]
            zs = [node.z for node in spline_nodes]

            x_vals, y_vals, z_vals = _sample_build123d_spline(
                spline_nodes,
                previous_segment,
                next_segment,
            )

        else:
            # Fallback: straight lines through the nodes
            x_vals = [n.x for n in segment.nodes]
            y_vals = [n.y for n in segment.nodes]
            z_vals = [n.z for n in segment.nodes]

        # Obstacle paths are instant, break up into line for visual indication
        if segment.is_obstacle:
            x_vals, y_vals, z_vals = _dashed_line(x_vals, y_vals, z_vals)

        # Plot this curve
        traces.append(
            go.Scatter3d(
                x=x_vals,
                y=y_vals,
                z=z_vals,
                mode="lines",
                name=f"Segment {segment.main_index}.{segment.secondary_index}{' (Obstacle)' if segment.is_obstacle else ''}",
                line=dict(color=segment_color),
                hoverinfo="text",
                text=segment_name,
                showlegend=True,
            )
        )

    return traces


def plot_rejected_splines(rejected_splines: list) -> list[go.Scatter3d]:
    """Highlight SPLINE segments demoted to COMPOUND by the occupancy check.

    Each entry is expected to expose ``.segment`` (a PathSegment),
    ``.overlap_fraction`` (0-1), ``.spline_points`` (sampled (x, y, z) of the
    evaluated option-1 spline) and ``.intersection_points`` (centres of the
    occupied cubes it intruded on), as produced by
    ``cad.spline_occupancy.RejectedSpline``.

    Per rejected spline, two traces are drawn: the actual bulging spline curve
    (solid red line) and red ``x`` markers at the spots where it intersects
    occupied cubes. All share one legend entry ("Rejected Splines"), so a single
    click toggles every rejected spline at once. Hidden by default.
    """
    traces: list[go.Scatter3d] = []
    legend_shown = False
    for rejected in rejected_splines or []:
        segment = rejected.segment
        label = (
            f"Rejected spline {segment.main_index}.{segment.secondary_index} "
            f"({rejected.overlap_fraction * 100:.0f}% overlap)"
        )

        # The evaluated spline curve (what actually bulged into occupied space).
        spline_points = rejected.spline_points or [
            (node.x, node.y, node.z) for node in segment.nodes
        ]
        traces.append(
            go.Scatter3d(
                x=[point[0] for point in spline_points],
                y=[point[1] for point in spline_points],
                z=[point[2] for point in spline_points],
                mode="lines",
                line=dict(color="red", width=6),
                name="Rejected Splines",
                legendgroup="rejected_splines",
                hoverinfo="text",
                text=label,
                visible="legendonly",
                showlegend=not legend_shown,
            )
        )
        legend_shown = True

        # The cubes the spline actually intersected.
        intersection_points = rejected.intersection_points
        if intersection_points:
            traces.append(
                go.Scatter3d(
                    x=[point[0] for point in intersection_points],
                    y=[point[1] for point in intersection_points],
                    z=[point[2] for point in intersection_points],
                    mode="markers",
                    marker=dict(color="red", size=5, symbol="x"),
                    name="Rejected Splines",
                    legendgroup="rejected_splines",
                    hoverinfo="text",
                    text=label,
                    visible="legendonly",
                    showlegend=False,
                )
            )
    return traces


def plot_spline_voxels(spline_voxel_debug: list, node_size: float) -> list[go.Scatter3d]:
    """Wire-frame cubes for the voxels each spline occupies.

    Each entry exposes ``.voxel_centers`` (the free-floating cubes sampled along
    the spline) and ``.foreign_voxel_centers`` (the subset that collided), as
    produced by ``cad.spline_occupancy.SplineVoxelDebug``. Sample cubes are drawn
    grey and collision cubes red, under a single "Spline Voxels" legend entry,
    hidden by default.
    """
    if not spline_voxel_debug or not node_size:
        return []

    traversed_centers: list[tuple[float, float, float]] = []
    foreign_centers: list[tuple[float, float, float]] = []
    for debug in spline_voxel_debug:
        foreign_set = {tuple(center) for center in debug.foreign_voxel_centers}
        foreign_centers.extend(debug.foreign_voxel_centers)
        # Draw a sample cube grey only when it is not already drawn red.
        traversed_centers.extend(
            center for center in debug.voxel_centers if tuple(center) not in foreign_set
        )

    traces: list[go.Scatter3d] = []
    legend_shown = False
    for centers, color in ((traversed_centers, "gray"), (foreign_centers, "red")):
        if not centers:
            continue
        x_vals, y_vals, z_vals = _cube_wireframe_xyz(centers, node_size)
        traces.append(
            go.Scatter3d(
                x=x_vals,
                y=y_vals,
                z=z_vals,
                mode="lines",
                line=dict(color=color, width=2),
                name="Spline Voxels",
                legendgroup="spline_voxels",
                hoverinfo="skip",
                visible="legendonly",
                showlegend=not legend_shown,
            )
        )
        legend_shown = True
    return traces


def plot_raw_obstacle_path(path: list, name: str = "Raw Path") -> list[go.Scatter3d]:
    """
    Given a list of vector like objects (.X/.Y/.Z),
    return a list of Scatter3d trace, plotting them in order to create a line.
    """

    xs, ys, zs = [], [], []
    for p in path:
        xs.append(p.X)
        ys.append(p.Y)
        zs.append(p.Z)

    trace = go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        name=name,
        line=dict(color="white", width=2),
        showlegend=True,
    )
    return [trace]


def plot_obstacles_raw_paths(obstacles: list) -> list[go.Scatter3d]:
    """
    Build traces for all placed obstacles (in world coordinates)
    """
    traces = []

    if not obstacles:
        return traces

    for obstacle in obstacles:
        # Plot single obstacle
        raw_path_points = obstacle.sample_obstacle_path_world()

        obstacle_traces = plot_raw_obstacle_path(
            raw_path_points, name=f"{obstacle.name} Raw Path"
        )

        traces.extend(obstacle_traces)

    return traces


def plot_invalid_obstacles(
    failed_obstacles: list, node_size: float
) -> list[go.Scatter3d]:
    """
    Build traces for obstacles that failed placement validation.
    Shows the attempted position with color-coding by failure type.

    Parameters:
        failed_obstacles: List of Obstacle instances with placement_failure_info set
        node_size: Size of grid nodes for visualization

    Returns:
        List of Plotly Scatter3d traces showing invalid placements
    """
    traces = []

    if not failed_obstacles:
        return traces

    for idx, obstacle in enumerate(failed_obstacles):
        # Read failure info from obstacle properties
        failure_type = obstacle.placement_failure_type
        conflicting_coords = obstacle.placement_failure_coordinates

        # Skip if no failure info is set
        if failure_type is None or conflicting_coords is None:
            continue

        # Get color/label for this failure type using enum methods
        color = failure_type.get_color()
        label = failure_type.get_label()

        # Draw the obstacle's path shape/curve
        raw_path_points = obstacle.sample_obstacle_path_world()
        if raw_path_points:
            xs = [p.X for p in raw_path_points]
            ys = [p.Y for p in raw_path_points]
            zs = [p.Z for p in raw_path_points]

            # Add the obstacle path trace
            path_trace = go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines",
                line=dict(width=6, color=color),
                opacity=0.6,
                showlegend=True,
                name=f"{obstacle.name} ❌",
                legendgroup=f"invalid_{idx}",
                hovertext=f"<b>{obstacle.name}</b> ❌<br>Reason: {label}",
                hoverinfo="text",
            )
            traces.append(path_trace)

        # Draw red box wireframes for conflicting nodes
        d = node_size / 2.0
        corner_offsets = [
            (dx, dy, dz) for dx in (-d, d) for dy in (-d, d) for dz in (-d, d)
        ]
        edges = [
            (0, 1),
            (1, 3),
            (3, 2),
            (2, 0),  # bottom
            (4, 5),
            (5, 7),
            (7, 6),
            (6, 4),  # top
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),  # verticals
        ]

        # Draw red boxes for conflicting coordinates
        for conflict_coord in conflicting_coords:
            x0, y0, z0 = conflict_coord
            verts = [(x0 + dx, y0 + dy, z0 + dz) for dx, dy, dz in corner_offsets]

            hover_text = (
                f"<b>⚠️ CONFLICT NODE</b><br>"
                f"Obstacle: {obstacle.name}<br>"
                f"Reason: {label}<br>"
                f"Position: ({x0:.1f}, {y0:.1f}, {z0:.1f})"
            )

            for i, j in edges:
                x1, y1, z1 = verts[i]
                x2, y2, z2 = verts[j]

                trace = go.Scatter3d(
                    x=[x1, x2],
                    y=[y1, y2],
                    z=[z1, z2],
                    mode="lines",
                    line=dict(width=2, color="#FF0000"),
                    opacity=0.9,
                    showlegend=False,
                    legendgroup=f"invalid_{idx}",
                    hovertext=hover_text,
                    hoverinfo="text",
                )
                traces.append(trace)

    return traces


def plot_puzzle_path(path_nodes: list[Node]) -> list[go.Scatter3d]:
    """
    Plot the full puzzle path (list of Nodes) as a single line.
    Hidden by default; toggle via legend.
    """
    xs = [n.x for n in path_nodes]
    ys = [n.y for n in path_nodes]
    zs = [n.z for n in path_nodes]
    trace = go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        name="Puzzle Path",
        line=dict(width=4),
        showlegend=True,
        visible="legendonly",
        hoverinfo="skip",
        legendgroup="Puzzle Path",
    )
    return [trace]


def _generate_distinct_hsv_colors(
    number_of_colors: int,
    seed: int | None = None,
) -> list[str]:
    """
    Build evenly spaced HSV colors converted to hex, then shuffle once.
    Using evenly spaced hues gives maximum contrast across the set.
    """
    if number_of_colors <= 0:
        return []

    # Evenly spaced hues
    hues = [index / number_of_colors for index in range(number_of_colors)]

    hex_colors: list[str] = []
    for hue in hues:
        red, green, blue = colorsys.hsv_to_rgb(hue, 1, 1)
        red_i = int(round(red * 255))
        green_i = int(round(green * 255))
        blue_i = int(round(blue * 255))
        hex_colors.append(f"#{red_i:02X}{green_i:02X}{blue_i:02X}")

    # Deterministic shuffle
    random_generator = random.Random(seed)
    random_generator.shuffle(hex_colors)

    return hex_colors


def _dashed_line(
    x_vals: Iterable[float],
    y_vals: Iterable[float],
    z_vals: Iterable[float],
) -> Tuple[List[float], List[float], List[float]]:
    """
    Build Scatter3d-compatible arrays (with None separators) that render a dashed
    straight line between the first and last XYZ points provided.

    Only uses start and end xyz values.
    """
    start_point = (float(x_vals[0]), float(y_vals[0]), float(z_vals[0]))
    end_point = (float(x_vals[-1]), float(y_vals[-1]), float(z_vals[-1]))
    num_dashes = 5
    gap_ratio = 0.6

    delta_x = end_point[0] - start_point[0]
    delta_y = end_point[1] - start_point[1]
    delta_z = end_point[2] - start_point[2]

    total_length = math.sqrt(delta_x**2 + delta_y**2 + delta_z**2)
    if total_length == 0:
        # Degenerate case: points coincide -> nothing to draw as a line
        return [start_point[0]], [start_point[1]], [start_point[2]]

    # Compute dash & gap as fractions of the full param t in [0, 1]
    # One cycle = dash + gap. We aim for ~num_dashes cycles over [0,1].
    cycle_count = max(1, int(num_dashes))
    dash_fraction = 1.0 / (cycle_count * (1.0 + gap_ratio))
    gap_fraction = dash_fraction * gap_ratio

    def lerp(start_value: float, end_value: float, t: float) -> float:
        return start_value + (end_value - start_value) * t

    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []

    t_cursor = 0.0
    epsilon = 1e-9  # guard against floating-point drift, tiny dash

    while t_cursor < 1.0 - epsilon:
        # Dash segment [t_cursor, t_dash_end]
        t_dash_end = min(t_cursor + dash_fraction, 1.0)

        x0 = lerp(start_point[0], end_point[0], t_cursor)
        y0 = lerp(start_point[1], end_point[1], t_cursor)
        z0 = lerp(start_point[2], end_point[2], t_cursor)

        x1 = lerp(start_point[0], end_point[0], t_dash_end)
        y1 = lerp(start_point[1], end_point[1], t_dash_end)
        z1 = lerp(start_point[2], end_point[2], t_dash_end)

        # Emit one visible dash segment, then a separator None to create a gap
        xs.extend([x0, x1, None])
        ys.extend([y0, y1, None])
        zs.extend([z0, z1, None])

        # Advance past the gap
        t_cursor = t_dash_end + gap_fraction

    return xs, ys, zs
