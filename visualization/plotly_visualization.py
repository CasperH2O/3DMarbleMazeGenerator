# visualization/plotly_visualization.py

import math

import numpy as np
import plotly.graph_objects as go
from geomdl import BSpline, utilities
from scipy import interpolate

from cad.cases.case import Case
from cad.path_segment import PathSegment
from config import PathCurveModel, PathCurveType
from puzzle.node import Node, NodeGridType

from .plotly_helpers import (  # Import shared helper functions
    plot_casing_plotly,
    plot_nodes_plotly,
)


def visualize_path_architect(nodes: Node, segments: list[PathSegment], casing: Case):
    """
    Visualizes the nodes and path segments as defined by path architect.
    """

    # Combine provided nodes with any segment nodes flagged as segment_start or segment_end
    all_nodes = list(nodes)

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

    fig = go.Figure()

    # Plot all nodes with shared styling.
    for trace in plot_nodes_plotly(all_nodes):
        fig.add_trace(trace)

    # Set up unique colors for segments.
    colors = [
        "blue",
        "green",
        "red",
        "purple",
        "orange",
        "pink",
        "brown",
        "cyan",
        "magenta",
        "yellow",
        "lime",
        "teal",
        "olive",
        "navy",
        "maroon",
        "aquamarine",
        "coral",
        "gold",
        "indigo",
        "lavender",
    ]
    segment_colors = {}
    color_index = 0

    for segment in segments:
        # Assign a unique color based on (main_index, secondary_index)
        segment_key = (segment.main_index, segment.secondary_index)
        if segment_key not in segment_colors:
            segment_colors[segment_key] = colors[color_index % len(colors)]
            color_index += 1
        segment_color = segment_colors[segment_key]

        # Create hover text for the segment.
        segment_name = (
            f"Segment ({segment.main_index}, {segment.secondary_index})<br>"
            f"Path Curve Model: {segment.curve_model}<br>"
            f"Curve Type: {segment.curve_type}<br>"
            f"Path Profile Type: {segment.path_profile_type}"
        )

        # Determine the method to generate the segment curve.
        if segment.curve_model == PathCurveModel.COMPOUND:
            # Use Bézier (B-Spline) if the curve type is S_CURVE or DEGREE_90_SINGLE_PLANE.
            if segment.curve_type in [
                PathCurveType.S_CURVE,
                PathCurveType.CURVE_90_DEGREE_SINGLE_PLANE,
            ]:
                control_points = [[node.x, node.y, node.z] for node in segment.nodes]
                num_control_points = len(control_points)
                if num_control_points < 2:
                    x_vals = [node.x for node in segment.nodes]
                    y_vals = [node.y for node in segment.nodes]
                    z_vals = [node.z for node in segment.nodes]
                else:
                    curve_degree = num_control_points - 1
                    curve = BSpline.Curve()
                    curve.degree = curve_degree
                    curve.ctrlpts = control_points
                    curve.knotvector = utilities.generate_knot_vector(
                        curve.degree, num_control_points
                    )
                    curve.delta = 0.001  # High resolution for smoother curves
                    curve.evaluate()
                    curve_points = np.array(curve.evalpts)
                    x_vals = curve_points[:, 0]
                    y_vals = curve_points[:, 1]
                    z_vals = curve_points[:, 2]
            else:
                # For standard polylines, build the segment using a pairwise approach.
                x_vals, y_vals, z_vals = [], [], []
                for i in range(len(segment.nodes) - 1):
                    start_node = segment.nodes[i]
                    end_node = segment.nodes[i + 1]
                    # If both nodes are from a circular grid, generate an arc.
                    if (NodeGridType.CIRCULAR.value in start_node.grid_type) and (
                        NodeGridType.CIRCULAR.value in end_node.grid_type
                    ):
                        theta1 = math.atan2(start_node.y, start_node.x)
                        theta2 = math.atan2(end_node.y, end_node.x)
                        dtheta = theta2 - theta1
                        if dtheta > math.pi:
                            dtheta -= 2 * math.pi
                        elif dtheta < -math.pi:
                            dtheta += 2 * math.pi
                        num_points = 20  # Adjust for smoother or coarser arcs.
                        theta_values = np.linspace(theta1, theta1 + dtheta, num_points)
                        r1 = math.hypot(start_node.x, start_node.y)
                        r2 = math.hypot(end_node.x, end_node.y)
                        r_values = np.linspace(r1, r2, num_points)
                        x_segment = r_values * np.cos(theta_values)
                        y_segment = r_values * np.sin(theta_values)
                        z_segment = np.linspace(start_node.z, end_node.z, num_points)
                        if i > 0:
                            x_vals.extend(x_segment[1:])
                            y_vals.extend(y_segment[1:])
                            z_vals.extend(z_segment[1:])
                        else:
                            x_vals.extend(x_segment)
                            y_vals.extend(y_segment)
                            z_vals.extend(z_segment)
                    else:
                        # Otherwise, draw a straight line between the nodes.
                        if i == 0:
                            x_vals.append(start_node.x)
                            y_vals.append(start_node.y)
                            z_vals.append(start_node.z)
                        x_vals.append(end_node.x)
                        y_vals.append(end_node.y)
                        z_vals.append(end_node.z)
        elif segment.curve_model == PathCurveModel.SPLINE:
            # For SPLINE curve model, perform spline interpolation.
            total_nodes = segment.nodes
            spline_nodes = []
            if len(total_nodes) >= 2:
                spline_nodes.extend(total_nodes[:2])
                for node in total_nodes[2:-2]:
                    if node.waypoint and node not in spline_nodes:
                        spline_nodes.append(node)
                for node in total_nodes[-2:]:
                    if node not in spline_nodes:
                        spline_nodes.append(node)
            else:
                spline_nodes = total_nodes

            # Preserve the original order.
            spline_nodes = sorted(spline_nodes, key=lambda n: total_nodes.index(n))
            xs = [node.x for node in spline_nodes]
            ys = [node.y for node in spline_nodes]
            zs = [node.z for node in spline_nodes]

            # Use chord-length parameterization.
            xyz = np.vstack([xs, ys, zs]).T
            u_nodes = np.cumsum(np.r_[0, np.linalg.norm(np.diff(xyz, axis=0), axis=1)])

            if len(u_nodes) < 2:
                x_vals, y_vals, z_vals = xs, ys, zs
            else:
                try:
                    sx = interpolate.InterpolatedUnivariateSpline(u_nodes, xs)
                    sy = interpolate.InterpolatedUnivariateSpline(u_nodes, ys)
                    sz = interpolate.InterpolatedUnivariateSpline(u_nodes, zs)
                except Exception:
                    x_vals, y_vals, z_vals = xs, ys, zs
                else:
                    uu = np.linspace(u_nodes[0], u_nodes[-1], 1000)
                    x_vals = sx(uu)
                    y_vals = sy(uu)
                    z_vals = sz(uu)
        else:
            # For any other curve model, fall back to drawing straight lines.
            x_vals = [node.x for node in segment.nodes]
            y_vals = [node.y for node in segment.nodes]
            z_vals = [node.z for node in segment.nodes]

        # Plot the computed segment curve.
        fig.add_trace(
            go.Scatter3d(
                x=x_vals,
                y=y_vals,
                z=z_vals,
                mode="lines",
                name=f"Segment {segment.main_index}.{segment.secondary_index}",
                line=dict(color=segment_color),
                hoverinfo="text",
                text=segment_name,
                showlegend=True,
            )
        )

    # Add casing traces.
    for trace in plot_casing_plotly(casing):
        fig.add_trace(trace)

    # Define camera positions
    camera_views = {
        "Iso": dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        "Front": dict(eye=dict(x=0, y=1.5, z=0)),
        "Side": dict(eye=dict(x=1.5, y=0, z=0)),
        "Top": dict(eye=dict(x=0, y=0, z=1.5)),
    }

    fig.update_layout(
        title="Path Visualization",
        template="plotly_dark",
        scene=dict(
            xaxis_title="X Axis",
            yaxis_title="Y Axis",
            zaxis_title="Z Axis",
            aspectmode="data",
            camera=dict(
                projection=dict(type="orthographic"), eye=camera_views["Iso"]["eye"]
            ),
        ),
        margin=dict(l=0, r=0, t=40, b=0),  # adjust top margin for title
        updatemenus=[
            # Projection dropdown
            dict(
                buttons=[
                    dict(
                        label="Orthographic",
                        method="relayout",
                        args=["scene.camera.projection.type", "orthographic"],
                    ),
                    dict(
                        label="Perspective",
                        method="relayout",
                        args=["scene.camera.projection.type", "perspective"],
                    ),
                ],
                direction="down",
                showactive=True,
                x=0.0,
                y=1.15,
                xanchor="left",
                font=dict(size=12),
                pad=dict(r=10, t=10),
            ),
            # Viewpoint dropdown
            dict(
                buttons=[
                    dict(
                        label=name,
                        method="relayout",
                        args=["scene.camera.eye", cam["eye"]],
                    )
                    for name, cam in camera_views.items()
                ],
                direction="down",
                showactive=True,
                x=0.3,
                y=1.15,
                xanchor="left",
                font=dict(size=12),
                pad=dict(r=10, t=10),
            ),
        ],
    )

    fig.show()
