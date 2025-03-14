# plotly_helpers.py

import numpy as np
import plotly.graph_objects as go

from puzzle.casing import BoxCasing, SphereCasing


def plot_nodes_plotly(nodes):
    """
    Groups nodes by their primary property so that the legend only displays the primary label,
    while the hover text for each marker shows all applicable flags on separate lines.
    """
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
    ]

    groups = {}  # key: primary flag; value: dict with x, y, z lists and hover texts
    seen = set()  # To avoid duplicate nodes based on coordinates only

    for node in nodes:
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
        if "circular" in node.grid_type:
            labels.append("Circular")
        if not labels:
            labels.append("Regular")

        # Determine the primary flag (for the legend) based on the defined priority.
        primary = None
        for flag, label in priority_flags:
            if flag == "circular":
                if "circular" in node.grid_type:
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
            legendgroup=primary,
            text=coords["hover"],  # Custom detailed info (all flags, with line breaks).
            hovertemplate="X: %{x}<br>Y: %{y}<br>Z: %{z}<br>%{text}<extra></extra>",
        )
        traces.append(trace)
    return traces


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
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
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
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
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
        mode="lines",
        line=dict(color="gray", width=2),
        showlegend=False,
    )
    casing_traces.append(circle_trace_yz)

    return casing_traces


def plot_box_casing_plotly(casing):
    hw = casing.half_width
    hh = casing.half_length
    hl = casing.half_height

    # Define the 8 corners of the box
    corners = np.array(
        [
            [-hw, -hh, -hl],
            [hw, -hh, -hl],
            [hw, hh, -hl],
            [-hw, hh, -hl],
            [-hw, -hh, hl],
            [hw, -hh, hl],
            [hw, hh, hl],
            [-hw, hh, hl],
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
