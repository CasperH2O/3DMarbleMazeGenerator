# visualization/plotly_visualization.py

import plotly.graph_objects as go
from scipy import interpolate
import numpy as np
from geomdl import BSpline, utilities

from .plotly_helpers import plot_nodes_plotly, plot_casing_plotly  # Import shared helper functions
from config import PathCurveModel, PathCurveType

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
            mode='lines',
            line=dict(color='gray', width=2),
            name="Path"
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
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        template="plotly_dark"
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
        colors = ['blue', 'green', 'purple', 'orange', 'brown']  # Colors for segments
        color_idx = 0

        for i in range(len(u_waypoints)):
            # Find the index in uu corresponding to the current segment
            end_u = u_waypoints[i]
            end_idx = np.searchsorted(uu, end_u)

            # Get the segment points
            segment_xx = xx[start_idx:end_idx + 1]
            segment_yy = yy[start_idx:end_idx + 1]
            segment_zz = zz[start_idx:end_idx + 1]

            # Create a trace for the segment
            segment_trace = go.Scatter3d(
                x=segment_xx,
                y=segment_yy,
                z=segment_zz,
                mode='lines',
                line=dict(color=colors[color_idx % len(colors)], width=2),
                showlegend=False
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
                mode='lines',
                line=dict(color=colors[color_idx % len(colors)], width=2),
                showlegend=False
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
                mode='lines',
                line=dict(color='blue', width=2),
                name='Path'
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
            mode='lines',
            line=dict(color='gray', width=1),
            name="Path"
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
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        template="plotly_dark"
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
        PathCurveModel.POLYLINE: 'gray',
        PathCurveModel.BEZIER: 'orange',
        PathCurveModel.SPLINE: 'lime'
    }
    legend_added = set()
    for segment in interpolated_segments:
        segment_type = segment['type']
        points = np.array(segment['points'])
        show_legend = False
        if segment_type not in legend_added:
            show_legend = True
            legend_added.add(segment_type)
        trace = go.Scatter3d(
            x=points[:, 0],
            y=points[:, 1],
            z=points[:, 2],
            mode='lines',
            line=dict(color=colors.get(segment_type, 'gray'), width=2),
            name=segment_type.value.capitalize(),
            showlegend=show_legend
        )
        path_traces.append(trace)

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)

    # Combine all traces
    data = node_traces + casing_traces + path_traces

    # Create the layout with dark theme
    layout = go.Layout(
        scene=dict(
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        template="plotly_dark",
        legend=dict(itemsizing='constant')
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    fig.show()

def visualize_path_architect(nodes, segments, casing):
    # Visualize the path and segments using Plotly
    fig = go.Figure()

    # Plot all nodes
    node_traces = plot_nodes_plotly(nodes)
    for trace in node_traces:
        fig.add_trace(trace)

    # Plot segments with unique colors based on main_index and secondary_index
    colors = [
        'blue', 'green', 'red', 'purple', 'orange', 'pink', 'brown',
        'cyan', 'magenta', 'yellow', 'lime', 'teal', 'olive', 'navy',
        'maroon', 'aquamarine', 'coral', 'gold', 'indigo', 'lavender'
    ]
    segment_colors = {}
    color_index = 0

    for segment in segments:
        # Assign a unique color for each (main_index, secondary_index)
        segment_key = (segment.main_index, segment.secondary_index)
        if segment_key not in segment_colors:
            segment_colors[segment_key] = colors[color_index % len(colors)]
            color_index += 1
        segment_color = segment_colors[segment_key]

        # Create a hover text with line breaks
        segment_name = (
            f"Segment ({segment.main_index}, {segment.secondary_index})<br>"
            f"Path Curve Model: {segment.curve_model}<br>"
            f"Curve Type: {segment.curve_type}<br>"
            f"Path Profile Type: {segment.path_profile_type}"
        )

        # Depending on the curve_model and curve_type, generate the points
        if segment.curve_model == PathCurveModel.POLYLINE:
            # Only apply Bezier if curve_type is S_CURVE or DEGREE_90_SINGLE_PLANE
            if segment.curve_type in [PathCurveType.S_CURVE, PathCurveType.DEGREE_90_SINGLE_PLANE]:
                # Generate Bezier curve points
                control_points = [[node.x, node.y, node.z] for node in segment.nodes]
                num_control_points = len(control_points)
                if num_control_points < 2:
                    # Not enough points for Bezier curve, fall back to straight lines
                    x_vals = [node.x for node in segment.nodes]
                    y_vals = [node.y for node in segment.nodes]
                    z_vals = [node.z for node in segment.nodes]
                else:
                    # Set the degree of the curve to number of control points minus 1
                    curve_degree = num_control_points - 1
                    # Create a B-Spline curve instance
                    curve = BSpline.Curve()
                    # Set up the curve degree and control points
                    curve.degree = curve_degree
                    curve.ctrlpts = control_points
                    # Auto-generate the knot vector
                    curve.knotvector = utilities.generate_knot_vector(curve.degree, num_control_points)
                    # Increase the evaluation resolution for smoother curves
                    curve.delta = 0.001  # Lower delta for smoother evaluation
                    # Evaluate the curve points
                    curve.evaluate()
                    # Extract the evaluated points
                    curve_points = np.array(curve.evalpts)
                    x_vals = curve_points[:, 0]
                    y_vals = curve_points[:, 1]
                    z_vals = curve_points[:, 2]
            else:
                # If curve_type is not S_CURVE or DEGREE_90_SINGLE_PLANE, plot straight lines
                x_vals = [node.x for node in segment.nodes]
                y_vals = [node.y for node in segment.nodes]
                z_vals = [node.z for node in segment.nodes]
        elif segment.curve_model == PathCurveModel.SPLINE:
            # Collect nodes for spline interpolation
            total_nodes = segment.nodes
            num_nodes = len(total_nodes)
            spline_nodes = []

            if num_nodes >= 2:
                # Add first two nodes
                spline_nodes.extend(total_nodes[:2])
                # Add any waypoint nodes in between, avoiding duplicates
                for node in total_nodes[2:-2]:
                    if node.waypoint and node not in spline_nodes:
                        spline_nodes.append(node)
                # Add last two nodes, avoiding duplicates
                for node in total_nodes[-2:]:
                    if node not in spline_nodes:
                        spline_nodes.append(node)
            else:
                # Not enough nodes for spline, use all nodes
                spline_nodes = total_nodes

            # Ensure nodes are in the correct order
            spline_nodes = sorted(spline_nodes, key=lambda n: total_nodes.index(n))

            # Prepare coordinates
            xs = [node.x for node in spline_nodes]
            ys = [node.y for node in spline_nodes]
            zs = [node.z for node in spline_nodes]

            # Chord-length parameterization
            xyz = np.vstack([xs, ys, zs]).T
            u_nodes = np.cumsum(np.r_[0, np.linalg.norm(np.diff(xyz, axis=0), axis=1)])

            if len(u_nodes) < 2:
                # Not enough points for spline, fall back to straight lines
                x_vals = xs
                y_vals = ys
                z_vals = zs
            else:
                try:
                    sx = interpolate.InterpolatedUnivariateSpline(u_nodes, xs)
                    sy = interpolate.InterpolatedUnivariateSpline(u_nodes, ys)
                    sz = interpolate.InterpolatedUnivariateSpline(u_nodes, zs)
                except Exception as e:
                    # In case of errors, fall back to straight lines
                    x_vals = xs
                    y_vals = ys
                    z_vals = zs
                else:
                    # Sample the spline
                    uu = np.linspace(u_nodes[0], u_nodes[-1], 1000)
                    x_vals = sx(uu)
                    y_vals = sy(uu)
                    z_vals = sz(uu)
        else:
            # For other types, plot straight lines between nodes
            x_vals = [node.x for node in segment.nodes]
            y_vals = [node.y for node in segment.nodes]
            z_vals = [node.z for node in segment.nodes]

        # Plot the lines for the segment
        fig.add_trace(go.Scatter3d(
            x=x_vals,
            y=y_vals,
            z=z_vals,
            mode='lines',
            name=f"Segment {segment.main_index}.{segment.secondary_index}",
            line=dict(color=segment_color),
            hoverinfo='text',
            text=segment_name,
            showlegend=True
        ))

        # Plot markers only at segment start and end nodes
        start_end_nodes = [
            node for node in segment.nodes
            if getattr(node, 'segment_start', False) or getattr(node, 'segment_end', False)
        ]
        if start_end_nodes:
            x_marker_vals = [node.x for node in start_end_nodes]
            y_marker_vals = [node.y for node in start_end_nodes]
            z_marker_vals = [node.z for node in start_end_nodes]
            # Use the segment color for markers
            marker_colors = [segment_color for _ in start_end_nodes]
            # Create hover text for markers
            marker_texts = []
            for node in start_end_nodes:
                node_type = 'Segment Start' if getattr(node, 'segment_start', False) else 'Segment End'
                marker_texts.append(
                    f"{node_type}<br>"
                    f"Node ID: {getattr(node, 'id', 'N/A')}<br>"
                    f"Coordinates: ({node.x}, {node.y}, {node.z})"
                )

            fig.add_trace(go.Scatter3d(
                x=x_marker_vals,
                y=y_marker_vals,
                z=z_marker_vals,
                mode='markers',
                name=f"Segment {segment.main_index}.{segment.secondary_index} Markers",
                marker=dict(size=4, color=marker_colors),
                legendgroup=f"Segment {segment.main_index}.{segment.secondary_index}",
                showlegend=False,  # Avoid duplicate legend entries
                hoverinfo='text',
                text=marker_texts
            ))

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)
    for trace in casing_traces:
        fig.add_trace(trace)

    fig.update_layout(
        title='Path Visualization',
        scene=dict(
            xaxis_title='X Axis',
            yaxis_title='Y Axis',
            zaxis_title='Z Axis'
        ),
        template="plotly_dark"
    )
    fig.show()
