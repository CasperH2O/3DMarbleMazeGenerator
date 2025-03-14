# visualization/plotly_visualization.py

import numpy as np
import plotly.graph_objects as go
from geomdl import BSpline, utilities
from scipy import interpolate

from config import PathCurveModel, PathCurveType

from .plotly_helpers import (  # Import shared helper functions
    plot_casing_plotly,
    plot_nodes_plotly,
)


def visualize_nodes_and_paths_plotly(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using Plotly.
    """

    # Plot nodes
    node_traces = plot_nodes_plotly(nodes)

    # Prepare path data
    path_trace = None
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        path_trace = go.Scatter3d(
            x=path_xs,
            y=path_ys,
            z=path_zs,
            mode="lines",
            line=dict(color="gray", width=2),
            name="Path",
        )

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)

    # Combine all traces
    data = node_traces + casing_traces
    if path_trace:
        data.append(path_trace)

    # Create the layout with dark theme
    layout = go.Layout(
        scene=dict(
            xaxis_title="X axis",
            yaxis_title="Y axis",
            zaxis_title="Z axis",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        template="plotly_dark",
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    fig.show()


def visualize_nodes_and_paths_curve_fit_plotly(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using Plotly.
    Fits parametric splines using chord-length parameterization to approximate the path
    using the nodes where `waypoint` is True, and also including the nodes directly
    before and after each waypoint node.
    Splits the spline at each waypoint.
    """

    # Plot nodes
    node_traces = plot_nodes_plotly(nodes)

    # Collect waypoint nodes along with the nodes immediately before and after each waypoint
    relevant_nodes = set()
    for i, current_node in enumerate(total_path):
        if current_node.waypoint:
            relevant_nodes.add(current_node)
            if i > 0:
                relevant_nodes.add(total_path[i - 1])
            if i < len(total_path) - 1:
                relevant_nodes.add(total_path[i + 1])

    # Sort the relevant nodes by their original order in total_path
    relevant_nodes = sorted(relevant_nodes, key=lambda node: total_path.index(node))

    if len(relevant_nodes) > 1:
        # Extract coordinates
        xs_relevant = [node.x for node in relevant_nodes]
        ys_relevant = [node.y for node in relevant_nodes]
        zs_relevant = [node.z for node in relevant_nodes]

        # Chord-length parameterization
        xyz = np.vstack([xs_relevant, ys_relevant, zs_relevant]).T
        u_nodes = np.cumsum(np.r_[0, np.linalg.norm(np.diff(xyz, axis=0), axis=1)])

        # Create splines for each coordinate
        sx = interpolate.InterpolatedUnivariateSpline(u_nodes, xs_relevant)
        sy = interpolate.InterpolatedUnivariateSpline(u_nodes, ys_relevant)
        sz = interpolate.InterpolatedUnivariateSpline(u_nodes, zs_relevant)

        # Sample the spline
        uu = np.linspace(u_nodes[0], u_nodes[-1], 1000)
        xx = sx(uu)
        yy = sy(uu)
        zz = sz(uu)

        # Identify indices of waypoints in relevant_nodes
        waypoint_indices = [i for i, node in enumerate(relevant_nodes) if node.waypoint]
        u_waypoints = u_nodes[waypoint_indices]

        # Split the spline at waypoints and plot each segment separately
        fitted_curve_traces = []
        start_idx = 0
        colors = ["blue", "green", "purple", "orange", "brown"]  # Colors for segments
        color_idx = 0

        for i in range(len(u_waypoints)):
            # Find the index in uu corresponding to the current segment
            end_u = u_waypoints[i]
            end_idx = np.searchsorted(uu, end_u)

            # Get the segment points
            segment_xx = xx[start_idx : end_idx + 1]
            segment_yy = yy[start_idx : end_idx + 1]
            segment_zz = zz[start_idx : end_idx + 1]

            # Create a trace for the segment
            segment_trace = go.Scatter3d(
                x=segment_xx,
                y=segment_yy,
                z=segment_zz,
                mode="lines",
                line=dict(color=colors[color_idx % len(colors)], width=2),
                showlegend=False,
            )
            fitted_curve_traces.append(segment_trace)

            # Update indices for next segment
            start_idx = end_idx
            color_idx += 1

        # Plot the remaining segment after the last waypoint
        if start_idx < len(uu) - 1:
            segment_trace = go.Scatter3d(
                x=xx[start_idx:],
                y=yy[start_idx:],
                z=zz[start_idx:],
                mode="lines",
                line=dict(color=colors[color_idx % len(colors)], width=2),
                showlegend=False,
            )
            fitted_curve_traces.append(segment_trace)
    else:
        # If not enough points for a spline, plot a simple line
        fitted_curve_traces = []
        if total_path:
            path_xs = [node.x for node in total_path]
            path_ys = [node.y for node in total_path]
            path_zs = [node.z for node in total_path]
            segment_trace = go.Scatter3d(
                x=path_xs,
                y=path_ys,
                z=path_zs,
                mode="lines",
                line=dict(color="blue", width=2),
                name="Path",
            )
            fitted_curve_traces.append(segment_trace)

    # Prepare path data
    path_trace = None
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        path_trace = go.Scatter3d(
            x=path_xs,
            y=path_ys,
            z=path_zs,
            mode="lines",
            line=dict(color="gray", width=1),
            name="Path",
        )

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)

    # Combine all traces
    data = node_traces + casing_traces
    if path_trace:
        data.append(path_trace)
    data.extend(fitted_curve_traces)

    # Create the layout with dark theme
    layout = go.Layout(
        scene=dict(
            xaxis_title="X axis",
            yaxis_title="Y axis",
            zaxis_title="Z axis",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        template="plotly_dark",
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    fig.show()


def visualize_interpolated_path_plotly(nodes, interpolated_segments, casing):
    """
    Visualizes the nodes and the interpolated path in a 3D plot using Plotly.
    """
    # Plot nodes
    node_traces = plot_nodes_plotly(nodes)

    # Prepare path traces from interpolated segments
    path_traces = []
    colors = {
        PathCurveModel.POLYLINE: "gray",
        PathCurveModel.BEZIER: "orange",
        PathCurveModel.SPLINE: "lime",
    }
    legend_added = set()
    for segment in interpolated_segments:
        segment_type = segment["type"]
        points = np.array(segment["points"])
        show_legend = False
        if segment_type not in legend_added:
            show_legend = True
            legend_added.add(segment_type)
        trace = go.Scatter3d(
            x=points[:, 0],
            y=points[:, 1],
            z=points[:, 2],
            mode="lines",
            line=dict(color=colors.get(segment_type, "gray"), width=2),
            name=segment_type.value.capitalize(),
            showlegend=show_legend,
        )
        path_traces.append(trace)

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)

    # Combine all traces
    data = node_traces + casing_traces + path_traces

    # Create the layout with dark theme
    layout = go.Layout(
        scene=dict(
            xaxis_title="X axis",
            yaxis_title="Y axis",
            zaxis_title="Z axis",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        template="plotly_dark",
        legend=dict(itemsizing="constant"),
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    fig.show()


def visualize_path_architect(nodes, segments, casing):
    import math  # for atan2, hypot, etc.

    import plotly.graph_objects as go

    # Combine original nodes with any segment nodes that have segment_start or segment_end flags.
    all_nodes = list(nodes)  # start with the provided nodes
    for segment in segments:
        for node in segment.nodes:
            if getattr(node, "segment_start", False) or getattr(
                node, "segment_end", False
            ):
                # Check by coordinate and legend label to avoid duplicates, 
                # mostly start and end segment nodes from one segment to the next
                if not any(
                    abs(n.x - node.x) < 1e-6
                    and abs(n.y - node.y) < 1e-6
                    and abs(n.z - node.z) < 1e-6
                    for n in all_nodes
                ):
                    all_nodes.append(node)

    fig = go.Figure()

    # Plot all nodes using the combined list so that segment start/end nodes are styled correctly.
    node_traces = plot_nodes_plotly(all_nodes)
    for trace in node_traces:
        fig.add_trace(trace)

    # Set up unique colors for each segment.
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
        # Assign a unique color for each (main_index, secondary_index) combination.
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

        # Build the segment connection using a pairwise approach.
        x_vals, y_vals, z_vals = [], [], []
        for i in range(len(segment.nodes) - 1):
            start_node = segment.nodes[i]
            end_node = segment.nodes[i + 1]
            # If both nodes are from a circular grid, generate an arc.
            if ("circular" in start_node.grid_type) and (
                "circular" in end_node.grid_type
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
                # Otherwise, draw a straight line.
                if i == 0:
                    x_vals.append(start_node.x)
                    y_vals.append(start_node.y)
                    z_vals.append(start_node.z)
                x_vals.append(end_node.x)
                y_vals.append(end_node.y)
                z_vals.append(end_node.z)

        # Plot the segment line using the computed points.
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
    casing_traces = plot_casing_plotly(casing)
    for trace in casing_traces:
        fig.add_trace(trace)

    fig.update_layout(
        title="Path Visualization",
        scene=dict(xaxis_title="X Axis", yaxis_title="Y Axis", zaxis_title="Z Axis"),
        template="plotly_dark",
    )
    fig.show()
