# plotly_helpers.py

from puzzle.casing import SphereCasing, BoxCasing
import numpy as np
import plotly.graph_objects as go


def plot_nodes_plotly(nodes):
    """
    Plots the nodes in a 3D scatter plot with different colors and sizes for different node types.
    Adds legends for start, end, waypoint, and other node types.
    """
    # Prepare coordinates
    xs = [node.x for node in nodes]
    ys = [node.y for node in nodes]
    zs = [node.z for node in nodes]

    # Segregate nodes based on their properties
    start_nodes = [node for node in nodes if node.start]
    end_nodes = [node for node in nodes if node.end]
    waypoint_nodes = [node for node in nodes if node.waypoint and not node.mounting and not node.end]  # Exclude mounting waypoints
    mounting_nodes = [node for node in nodes if node.mounting and not node.start ]
    occupied_nodes = [node for node in nodes if node.occupied and not node.waypoint and not node.mounting]  # Exclude occupied waypoints and mountings
    regular_nodes = [node for node in nodes if not (node.start or node.end or node.waypoint or node.mounting or node.occupied)]

    # Create scatter traces for each node type with corresponding legends
    scatter_start = go.Scatter3d(
        x=[node.x for node in start_nodes],
        y=[node.y for node in start_nodes],
        z=[node.z for node in start_nodes],
        mode='markers',
        marker=dict(color='yellow', size=5),
        name="Start Node",
        legendgroup="Start"
    )

    scatter_end = go.Scatter3d(
        x=[node.x for node in end_nodes],
        y=[node.y for node in end_nodes],
        z=[node.z for node in end_nodes],
        mode='markers',
        marker=dict(color='magenta', size=5),
        name="End Node",
        legendgroup="End"
    )

    scatter_waypoint = go.Scatter3d(
        x=[node.x for node in waypoint_nodes],
        y=[node.y for node in waypoint_nodes],
        z=[node.z for node in waypoint_nodes],
        mode='markers',
        marker=dict(color='blue', size=3),
        name="Waypoint",
        legendgroup="Waypoint"
    )

    scatter_mounting = go.Scatter3d(
        x=[node.x for node in mounting_nodes],
        y=[node.y for node in mounting_nodes],
        z=[node.z for node in mounting_nodes],
        mode='markers',
        marker=dict(color='purple', size=4),
        name="Mounting",
        legendgroup="Mounting"
    )

    scatter_occupied = go.Scatter3d(
        x=[node.x for node in occupied_nodes],
        y=[node.y for node in occupied_nodes],
        z=[node.z for node in occupied_nodes],
        mode='markers',
        marker=dict(color='red', size=3),
        name="Occupied",
        legendgroup="Occupied"
    )

    scatter_regular = go.Scatter3d(
        x=[node.x for node in regular_nodes],
        y=[node.y for node in regular_nodes],
        z=[node.z for node in regular_nodes],
        mode='markers',
        marker=dict(color='green', size=1),
        name="Regular Node",
        legendgroup="Regular"
    )

    # Combine all scatter traces
    return [scatter_start, scatter_end, scatter_waypoint, scatter_mounting, scatter_occupied, scatter_regular]


def plot_casing_plotly(casing):
    if isinstance(casing, SphereCasing):
        return plot_sphere_casing_plotly(casing)
    elif isinstance(casing, BoxCasing):
        return plot_box_casing_plotly(casing)
    else:
        raise ValueError(f"Unsupported casing type: {type(casing)}")

def plot_sphere_casing_plotly(casing):
    theta = np.linspace(0, 2 * np.pi, 100)
    r = casing.inner_radius

    casing_traces = []

    # Circle in XY plane (z = 0)
    x_circle_xy = r * np.cos(theta)
    y_circle_xy = r * np.sin(theta)
    z_circle_xy = np.zeros_like(theta)
    circle_trace_xy = go.Scatter3d(
        x=x_circle_xy,
        y=y_circle_xy,
        z=z_circle_xy,
        mode='lines',
        line=dict(color='gray', width=2),
        showlegend=False
    )
    casing_traces.append(circle_trace_xy)

    # Circle in XZ plane (y = 0)
    x_circle_xz = r * np.cos(theta)
    y_circle_xz = np.zeros_like(theta)
    z_circle_xz = r * np.sin(theta)
    circle_trace_xz = go.Scatter3d(
        x=x_circle_xz,
        y=y_circle_xz,
        z=z_circle_xz,
        mode='lines',
        line=dict(color='gray', width=2),
        showlegend=False
    )
    casing_traces.append(circle_trace_xz)

    # Circle in YZ plane (x = 0)
    x_circle_yz = np.zeros_like(theta)
    y_circle_yz = r * np.cos(theta)
    z_circle_yz = r * np.sin(theta)
    circle_trace_yz = go.Scatter3d(
        x=x_circle_yz,
        y=y_circle_yz,
        z=z_circle_yz,
        mode='lines',
        line=dict(color='gray', width=2),
        showlegend=False
    )
    casing_traces.append(circle_trace_yz)

    return casing_traces

def plot_box_casing_plotly(casing):
    hw = casing.half_width
    hh = casing.half_height
    hl = casing.half_length

    # Define the 8 corners of the box
    corners = np.array([
        [-hw, -hh, -hl],
        [hw, -hh, -hl],
        [hw, hh, -hl],
        [-hw, hh, -hl],
        [-hw, -hh, hl],
        [hw, -hh, hl],
        [hw, hh, hl],
        [-hw, hh, hl]
    ])

    # Define the edges as pairs of indices into the corners array
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom face
        (4, 5), (5, 6), (6, 7), (7, 4),  # Top face
        (0, 4), (1, 5), (2, 6), (3, 7)  # Vertical edges
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
        mode='lines',
        line=dict(color='gray', width=1),
        showlegend=False
    )

    return [box_trace]

