from puzzle.casing import SphereCasing, BoxCasing

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import plotly.graph_objects as go
import plotly.offline as pyo
from geomdl import BSpline, utilities
from geomdl.visualization import VisMPL
from scipy import interpolate
from scipy.interpolate import BSpline as SciPyBSpline

##############
# MatPlotLib #
##############

def visualize_nodes_and_paths(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using matplotlib.
    """

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot nodes
    plot_nodes(ax, nodes)

    # Plot the path
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=1)

    # Plot the casing
    plot_casing(ax, casing)

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

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot nodes using the helper function
    plot_nodes(ax, nodes)

    # Plot the path
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=1, label='Path')

    # Add NURBS curve (using total_path nodes as control points)
    if len(total_path) >= 4:  # Need at least degree+1 control points
        control_points = [[node.x, node.y, node.z] for node in total_path]

        # Create a B-Spline curve instance
        curve = BSpline.Curve()

        # Set up the curve degree and control points
        curve.degree = 3
        curve.ctrlpts = control_points

        # Auto-generate the knot vector
        curve.knotvector = utilities.generate_knot_vector(curve.degree, len(control_points))

        # Increase the evaluation resolution for smoother curves
        curve.delta = 0.001  # Lower delta for smoother evaluation

        # Evaluate the curve points
        curve.evaluate()

        # Extract the evaluated points
        curve_points = np.array(curve.evalpts)
        x_spline = curve_points[:, 0]
        y_spline = curve_points[:, 1]
        z_spline = curve_points[:, 2]

        # Plot the NURBS curve
        ax.plot(x_spline, y_spline, z_spline, color='red', linewidth=2, label='NURBS Curve')

    # Plot the casing using the helper function
    plot_casing(ax, casing)

    # Set axis labels and aspect ratio
    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')
    ax.legend()
    ax.set_box_aspect([1, 1, 1])  # Equal aspect ratio

    plt.show()

def visualize_nodes_and_paths_spline(nodes, total_path, casing):
    """
    Visualizes the nodes, the B-spline curve, and the path in a 3D plot using matplotlib.
    """

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot nodes using the helper function
    plot_nodes(ax, nodes)

    # Plot the path
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=1, label='Path')

    # Add B-spline curve (using total_path nodes as control points)
    if len(total_path) >= 4:  # Need at least degree+1 control points
        # Extract control points
        ctrl_pts = np.array([[node.x, node.y, node.z] for node in total_path])
        degree = 3  # Cubic B-spline

        # Number of control points
        n_ctrl_pts = len(ctrl_pts)

        # Generate a uniform knot vector
        n_knots = n_ctrl_pts + degree + 1
        knot_vector = np.linspace(0, 1, n_knots - 2 * degree)
        knot_vector = np.concatenate((
            np.zeros(degree),
            knot_vector,
            np.ones(degree)
        ))

        # Parameter values for evaluation
        t = np.linspace(0, 1, 1000)

        # Create BSpline objects for each coordinate
        spl_x = SciPyBSpline(knot_vector, ctrl_pts[:, 0], degree)
        spl_y = SciPyBSpline(knot_vector, ctrl_pts[:, 1], degree)
        spl_z = SciPyBSpline(knot_vector, ctrl_pts[:, 2], degree)

        # Evaluate the spline
        x_spline = spl_x(t)
        y_spline = spl_y(t)
        z_spline = spl_z(t)

        # Plot the spline curve
        ax.plot(x_spline, y_spline, z_spline, color='red', linewidth=2, label='B-spline Curve')

    else:
        # If not enough points for a spline, plot a simple line
        if total_path:
            path_xs = [node.x for node in total_path]
            path_ys = [node.y for node in total_path]
            path_zs = [node.z for node in total_path]
            ax.plot(path_xs, path_ys, path_zs, color='red', linewidth=2, label='Path')

    # Plot the casing using the helper function
    plot_casing(ax, casing)

    # Set axis labels and aspect ratio
    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')
    ax.legend()
    ax.set_box_aspect([1, 1, 1])  # Equal aspect ratio

    plt.show()

def visualize_nodes_and_paths_curve_fit(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using matplotlib.
    Fits parametric splines using chord-length parameterization to approximate the path
    using the nodes where `waypoint` is True, and also including the nodes directly
    before and after each waypoint node.
    """

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Plot nodes using the helper function
    plot_nodes(ax, nodes)

    # Collect waypoint nodes along with the nodes immediately before and after each waypoint
    relevant_nodes = set()
    for i, node in enumerate(total_path):
        if node.waypoint:
            relevant_nodes.add(node)
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
        u = np.cumsum(np.r_[0, np.linalg.norm(np.diff(xyz, axis=0), axis=1)])

        # Create splines for each coordinate
        sx = interpolate.InterpolatedUnivariateSpline(u, xs_relevant)
        sy = interpolate.InterpolatedUnivariateSpline(u, ys_relevant)
        sz = interpolate.InterpolatedUnivariateSpline(u, zs_relevant)

        # Sample the spline
        uu = np.linspace(u[0], u[-1], 1000)
        xx = sx(uu)
        yy = sy(uu)
        zz = sz(uu)

        # Plot the fitted curve
        ax.plot(xx, yy, zz, color='blue', linewidth=2, label='Fitted Curve')

    # Plot the path
    if total_path:
        path_xs = [node.x for node in total_path]
        path_ys = [node.y for node in total_path]
        path_zs = [node.z for node in total_path]
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=1, label='Path')

    # Plot the casing using the helper function
    plot_casing(ax, casing)

    # Set axis labels and aspect ratio
    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')
    ax.legend()
    ax.set_box_aspect([1, 1, 1])  # Equal aspect ratio

    plt.show()

def plot_nodes(ax, nodes):
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

def plot_casing(ax, casing):
    if isinstance(casing, SphereCasing):
        plot_sphere_casing(ax, casing)
    elif isinstance(casing, BoxCasing):
        plot_box_casing(ax, casing)
    else:
        raise ValueError(f"Unsupported casing type: {type(casing)}")

def plot_sphere_casing(ax, casing):
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

def plot_box_casing(ax, casing):
    # Plot the box edges
    hw = casing.half_width
    hh = casing.half_height
    hl = casing.half_length

    # Define the 8 corners of the box
    corners = np.array([
        [-hw, -hh, -hl],
        [ hw, -hh, -hl],
        [ hw,  hh, -hl],
        [-hw,  hh, -hl],
        [-hw, -hh,  hl],
        [ hw, -hh,  hl],
        [ hw,  hh,  hl],
        [-hw,  hh,  hl]
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

##########
# Plotly #
##########

def visualize_nodes_and_paths_plotly(nodes, total_path, casing):
    """
    Visualizes the nodes and the path in a 3D plot using Plotly.
    """

    # Plot nodes
    scatter = plot_nodes_plotly(nodes)

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
    data = [scatter] + casing_traces
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
    pyo.plot(fig, filename="3d_nodes_and_paths.html")

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
        line=dict(color='cyan', width=1),
        showlegend=False
    )

    return [box_trace]

