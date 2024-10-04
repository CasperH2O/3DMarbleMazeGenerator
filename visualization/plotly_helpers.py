# plotly_helpers.py

from puzzle.casing import SphereCasing, BoxCasing
import numpy as np
import plotly.graph_objects as go


def plot_nodes_plotly(nodes):
    xs = [node.x for node in nodes]
    ys = [node.y for node in nodes]
    zs = [node.z for node in nodes]

    # Colors and sizes based on node properties
    colors = []
    sizes = []
    for node in nodes:
        if node.start:
            colors.append('yellow')
            sizes.append(10)
        elif node.end:
            colors.append('orange')
            sizes.append(10)
        elif node.mounting:
            colors.append('purple')
            sizes.append(8)
        elif node.waypoint:
            colors.append('blue')
            sizes.append(6)
        elif node.occupied:
            colors.append('red')
            sizes.append(6)
        else:
            colors.append('green')
            sizes.append(3)

    scatter = go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode='markers',
        marker=dict(
            size=sizes,
            color=colors,
            opacity=0.8
        ),
        name="Nodes"
    )
    return scatter

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

