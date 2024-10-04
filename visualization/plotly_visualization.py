# plotly_visualization.py

import plotly.graph_objects as go
import plotly.offline as pyo
from scipy import interpolate
import numpy as np
from .plotly_helpers import plot_nodes_plotly, plot_casing_plotly  # Import shared helper functions


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
            line=dict(color='black', width=2),
            name="Path"
        )

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)

    # Combine all traces
    data = node_traces + casing_traces
    if path_trace:
        data.append(path_trace)

    # Create the layout
    layout = go.Layout(
        scene=dict(
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    pyo.plot(fig, filename="../3d_nodes_and_paths.html")


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
            line=dict(color='black', width=1),
            name="Path"
        )

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)

    # Combine all traces
    data = node_traces + casing_traces
    if path_trace:
        data.append(path_trace)
    data.extend(fitted_curve_traces)

    # Create the layout
    layout = go.Layout(
        scene=dict(
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    pyo.plot(fig, filename="../3d_nodes_and_paths_curve_fit.html")


def visualize_interpolated_path_plotly(nodes, interpolated_segments, casing):
    """
    Visualizes the nodes and the interpolated path in a 3D plot using Plotly.
    """
    # Plot nodes
    node_traces = plot_nodes_plotly(nodes)

    # Prepare path traces from interpolated segments
    path_traces = []
    colors = {
        'straight': 'black',
        'bezier': 'orange',
        'spline': 'lime'
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
            line=dict(color=colors.get(segment_type, 'black'), width=2),
            name=segment_type.capitalize(),
            showlegend=show_legend
        )
        path_traces.append(trace)

    # Get casing traces
    casing_traces = plot_casing_plotly(casing)

    # Combine all traces
    data = node_traces + casing_traces + path_traces

    # Create the layout
    layout = go.Layout(
        scene=dict(
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        legend=dict(itemsizing='constant')
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    pyo.plot(fig, filename="../3d_interpolated_path.html")
