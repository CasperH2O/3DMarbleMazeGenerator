# matplotlib_visualization.py

import matplotlib.pyplot as plt
import numpy as np
from geomdl import BSpline, utilities
from scipy import interpolate
from scipy.interpolate import BSpline as SciPyBSpline
from .matplotlib_helpers import plot_nodes, plot_casing  # Import shared helper functions

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
        curve.delta = 0.01  # Lower delta for smoother evaluation

        # Evaluate the curve points
        curve.evaluate()

        # Extract the evaluated points
        curve_points = np.array(curve.evalpts)
        x_spline = curve_points[:, 0]
        y_spline = curve_points[:, 1]
        z_spline = curve_points[:, 2]

        if False:
            print('# Define the points for the spline path')
            print('pts = [')
    
            for i, node in enumerate(curve_points):
                x, y, z = node  # Extract x, y, z coordinates from the current node
                coords = f'    ({x}, {y}, {z}),'
                comment = ''
                if i == 0:
                    comment = '  # Start point'
                elif i == len(curve_points) - 1:
                    comment = '  # End point'
                print(coords + comment)
            print(']')

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

