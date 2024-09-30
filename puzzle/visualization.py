# puzzle/visualization.py

from geomdl import BSpline, utilities
from geomdl.visualization import VisMPL
from puzzle.casing import SphereCasing, BoxCasing
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import plotly.graph_objects as go
import plotly.offline as pyo
from scipy import interpolate


def visualize_nodes_and_paths(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using matplotlib.
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot all nodes
    xs = [node.x for node in nodes]
    ys = [node.y for node in nodes]
    zs = [node.z for node in nodes]

    # Determine colors and sizes based on node properties
    colors = []
    sizes = []
    for node in nodes:
        if node.start:
            colors.append('yellow')  # Start node
            sizes.append(40)
        elif node.end:
            colors.append('orange')  # End node
            sizes.append(40)
        elif node.mounting:
            colors.append('purple')  # Mounting nodes
            sizes.append(30)
        elif node.waypoint:
            colors.append('blue')  # Waypoints
            sizes.append(20)
        elif node.occupied:
            colors.append('red')  # Occupied nodes
            sizes.append(20)
        else:
            colors.append('green')  # Unoccupied nodes
            sizes.append(1)  # Smaller size for unoccupied nodes

    ax.scatter(xs, ys, zs, c=colors, marker='o', s=sizes)

    # Plot the path
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=1)

    # Plot casing based on its type
    if isinstance(casing, SphereCasing):
        # Plot circles in the XY, XZ, and YZ planes
        theta = np.linspace(0, 2 * np.pi, 100)
        r = casing.inner_radius

        # Circle in XY plane (z = 0)
        x_circle_xy = r * np.cos(theta)
        y_circle_xy = r * np.sin(theta)
        z_circle_xy = np.zeros_like(theta)
        ax.plot(x_circle_xy, y_circle_xy, z_circle_xy, color='cyan')

        # Circle in XZ plane (y = 0)
        x_circle_xz = r * np.cos(theta)
        y_circle_xz = np.zeros_like(theta)
        z_circle_xz = r * np.sin(theta)
        ax.plot(x_circle_xz, y_circle_xz, z_circle_xz, color='magenta')

        # Circle in YZ plane (x = 0)
        x_circle_yz = np.zeros_like(theta)
        y_circle_yz = r * np.cos(theta)
        z_circle_yz = r * np.sin(theta)
        ax.plot(x_circle_yz, y_circle_yz, z_circle_yz, color='yellow')

    elif isinstance(casing, BoxCasing):
        # Plot the box edges (as before)
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

        # Define the edges of the box
        edges = [
            [corners[0], corners[1]],
            [corners[1], corners[2]],
            [corners[2], corners[3]],
            [corners[3], corners[0]],
            [corners[4], corners[5]],
            [corners[5], corners[6]],
            [corners[6], corners[7]],
            [corners[7], corners[4]],
            [corners[0], corners[4]],
            [corners[1], corners[5]],
            [corners[2], corners[6]],
            [corners[3], corners[7]]
        ]

        edge_collection = Line3DCollection(edges, colors='cyan', linewidths=1)
        ax.add_collection3d(edge_collection)

    # Set axis labels and aspect ratio
    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')
    ax.set_box_aspect([1, 1, 1])  # Equal aspect ratio

    plt.show()


def visualize_nodes_and_paths_nurbs(nodes, total_path, casing):
    """
    Visualizes the nodes, the NURBS curve, and the path in a 3D plot using matplotlib and geomdl.
    """
    #  Setup the matplotlib figure and axis
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Extract node coordinates
    xs = [node.x for node in nodes]
    ys = [node.y for node in nodes]
    zs = [node.z for node in nodes]

    # Plot all nodes with colors and sizes
    colors = []
    sizes = []
    for node in nodes:
        if node.start:
            colors.append('yellow')  # Start node
            sizes.append(40)
        elif node.end:
            colors.append('orange')  # End node
            sizes.append(40)
        elif node.mounting:
            colors.append('purple')  # Mounting nodes
            sizes.append(30)
        elif node.waypoint:
            colors.append('blue')  # Waypoints
            sizes.append(20)
        elif node.occupied:
            colors.append('red')  # Occupied nodes
            sizes.append(20)
        else:
            colors.append('green')  # Unoccupied nodes
            sizes.append(1)  # Smaller size for unoccupied nodes

    ax.scatter(xs, ys, zs, c=colors, marker='o', s=sizes)

    # Plot the path
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=1)

    # Add NURBS curve (using total_path nodes as control points)
    ctrlpts = [[node.x, node.y, node.z] for node in total_path]

    # Create a B-Spline curve instance
    curve = BSpline.Curve()

    # Set up the curve degree and control points (increase the degree for smoother curves)
    curve.degree = 3
    curve.ctrlpts = ctrlpts

    # Auto-generate the knot vector
    curve.knotvector = utilities.generate_knot_vector(curve.degree, len(ctrlpts))

    # Increase the evaluation resolution for smoother curves (reduce delta)
    curve.delta = 0.001  # Lower delta for smoother evaluation

    # Use geomdl's visualization for NURBS curve plotting
    curve.vis = VisMPL.VisCurve3D()
    curve.render()

    # Plot the casing
    if isinstance(casing, SphereCasing):
        # Plot circles in the XY, XZ, and YZ planes
        theta = np.linspace(0, 2 * np.pi, 100)
        r = casing.inner_radius

        # Circle in XY plane (z = 0)
        x_circle_xy = r * np.cos(theta)
        y_circle_xy = r * np.sin(theta)
        z_circle_xy = np.zeros_like(theta)
        ax.plot(x_circle_xy, y_circle_xy, z_circle_xy, color='cyan')

        # Circle in XZ plane (y = 0)
        x_circle_xz = r * np.cos(theta)
        y_circle_xz = np.zeros_like(theta)
        z_circle_xz = r * np.sin(theta)
        ax.plot(x_circle_xz, y_circle_xz, z_circle_xz, color='magenta')

        # Circle in YZ plane (x = 0)
        x_circle_yz = np.zeros_like(theta)
        y_circle_yz = r * np.cos(theta)
        z_circle_yz = r * np.sin(theta)
        ax.plot(x_circle_yz, y_circle_yz, z_circle_yz, color='yellow')

    elif isinstance(casing, BoxCasing):
        # Plot the box edges
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

        # Define the edges of the box
        edges = [
            [corners[0], corners[1]],
            [corners[1], corners[2]],
            [corners[2], corners[3]],
            [corners[3], corners[0]],
            [corners[4], corners[5]],
            [corners[5], corners[6]],
            [corners[6], corners[7]],
            [corners[7], corners[4]],
            [corners[0], corners[4]],
            [corners[1], corners[5]],
            [corners[2], corners[6]],
            [corners[3], corners[7]]
        ]

        edge_collection = Line3DCollection(edges, colors='cyan', linewidths=1)
        ax.add_collection3d(edge_collection)

    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')
    ax.set_box_aspect([1, 1, 1])  # Equal aspect ratio

    plt.show()


def visualize_nodes_and_paths_curve_fit(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using matplotlib.
    Fits parametric splines using chord-length parameterization to approximate the path
    for overlapping chunks of 5 nodes, alternating colors between light blue and dark blue.
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot the original nodes (as markers)
    colors = []
    sizes = []
    for node in total_path:
        if node.start:
            colors.append('yellow')  # Start node
            sizes.append(40)
        elif node.end:
            colors.append('orange')  # End node
            sizes.append(40)
        elif node.mounting:
            colors.append('purple')  # Mounting nodes
            sizes.append(30)
        elif node.waypoint:
            colors.append('blue')  # Waypoints
            sizes.append(20)
        elif node.occupied:
            colors.append('red')  # Occupied nodes
            sizes.append(20)
        else:
            colors.append('green')  # Unoccupied nodes
            sizes.append(1)  # Smaller size for unoccupied nodes

    xs = [node.x for node in total_path]
    ys = [node.y for node in total_path]
    zs = [node.z for node in total_path]

    ax.scatter(xs, ys, zs, c=colors, marker='o', s=sizes)

    # Divide total_path into overlapping chunks of 5 nodes
    chunk_size = 5
    curve_colors = ['lightblue', 'darkblue']

    for i in range(0, len(total_path) - chunk_size + 1,
                   chunk_size - 1):  # Step by chunk_size - 1 to overlap the last node
        chunk = total_path[i:i + chunk_size]

        xs_chunk = [node.x for node in chunk]
        ys_chunk = [node.y for node in chunk]
        zs_chunk = [node.z for node in chunk]

        # Fit parametric splines for x(u), y(u), z(u) using chord-length parameterization
        xyz = np.vstack([xs_chunk, ys_chunk, zs_chunk]).T  # Stack xs, ys, zs into an (N, 3) array
        u = np.cumsum(np.r_[[0], np.linalg.norm(np.diff(xyz, axis=0), axis=1)])  # Chord-length parameterization

        # Create splines for each coordinate
        sx = interpolate.InterpolatedUnivariateSpline(u, xs_chunk)  # x(u)
        sy = interpolate.InterpolatedUnivariateSpline(u, ys_chunk)  # y(u)
        sz = interpolate.InterpolatedUnivariateSpline(u, zs_chunk)  # z(u)

        # Sample the spline with fine values of u
        uu = np.linspace(u[0], u[-1], 100)  # 100 sample points along the spline
        xx = sx(uu)
        yy = sy(uu)
        zz = sz(uu)

        # Plot the parametric spline for the current chunk
        ax.plot(xx, yy, zz, color=curve_colors[i // (chunk_size - 1) % 2], linewidth=2)

    # Plot casing based on its type
    if isinstance(casing, SphereCasing):
        # Plot circles in the XY, XZ, and YZ planes
        theta = np.linspace(0, 2 * np.pi, 100)
        r = casing.inner_radius

        # Circle in XY plane (z = 0)
        x_circle_xy = r * np.cos(theta)
        y_circle_xy = r * np.sin(theta)
        z_circle_xy = np.zeros_like(theta)
        ax.plot(x_circle_xy, y_circle_xy, z_circle_xy, color='cyan')

        # Circle in XZ plane (y = 0)
        x_circle_xz = r * np.cos(theta)
        y_circle_xz = np.zeros_like(theta)
        z_circle_xz = r * np.sin(theta)
        ax.plot(x_circle_xz, y_circle_xz, z_circle_xz, color='magenta')

        # Circle in YZ plane (x = 0)
        x_circle_yz = np.zeros_like(theta)
        y_circle_yz = r * np.cos(theta)
        z_circle_yz = r * np.sin(theta)
        ax.plot(x_circle_yz, y_circle_yz, z_circle_yz, color='yellow')

    elif isinstance(casing, BoxCasing):
        # Plot the box edges
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

        # Define the edges of the box
        edges = [
            [corners[0], corners[1]],
            [corners[1], corners[2]],
            [corners[2], corners[3]],
            [corners[3], corners[0]],
            [corners[4], corners[5]],
            [corners[5], corners[6]],
            [corners[6], corners[7]],
            [corners[7], corners[4]],
            [corners[0], corners[4]],
            [corners[1], corners[5]],
            [corners[2], corners[6]],
            [corners[3], corners[7]]
        ]

        edge_collection = Line3DCollection(edges, colors='cyan', linewidths=1)
        ax.add_collection3d(edge_collection)

    # Set axis labels and aspect ratio
    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')
    ax.set_box_aspect([1, 1, 1])  # Equal aspect ratio

    plt.show()


def visualize_nodes_and_paths_plotly(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using Plotly.
    """

    # Create lists for nodes
    xs = [node.x for node in nodes]
    ys = [node.y for node in nodes]
    zs = [node.z for node in nodes]

    # Colors and sizes based on node properties
    colors = []
    sizes = []
    for node in nodes:
        if node.start:
            colors.append('yellow')  # Start node
            sizes.append(10)
        elif node.end:
            colors.append('orange')  # End node
            sizes.append(10)
        elif node.mounting:
            colors.append('purple')  # Mounting nodes
            sizes.append(8)
        elif node.waypoint:
            colors.append('blue')  # Waypoints
            sizes.append(6)
        elif node.occupied:
            colors.append('red')  # Occupied nodes
            sizes.append(6)
        else:
            colors.append('green')  # Unoccupied nodes
            sizes.append(3)  # Smaller size for unoccupied nodes

    # Scatter plot for the nodes
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

    # Plot the path, if provided
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

    # Initialize a list for casing traces
    casing_traces = []

    # Plot casing based on its type
    if isinstance(casing, SphereCasing):
        # Plot circles in the XY, XZ, and YZ planes
        theta = np.linspace(0, 2 * np.pi, 100)
        r = casing.inner_radius

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

    elif isinstance(casing, BoxCasing):
        # Plot the box edges (as before)
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
            line=dict(color='cyan', width=1),
            name='Box'
        )
        casing_traces.append(box_trace)

    # Combine all traces
    data = [scatter] + casing_traces
    if path_trace:
        data.append(path_trace)

    # Create the layout
    layout = go.Layout(
        scene=dict(
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis',
            aspectmode='data'  # Ensures aspect ratio is correct
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    pyo.plot(fig, filename="3d_nodes_and_paths.html")
