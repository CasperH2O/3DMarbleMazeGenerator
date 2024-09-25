# puzzle/visualization.py

import matplotlib.pyplot as plt
import numpy as np


def visualize_nodes_and_paths(nodes, total_path, inner_radius):
    """
    Visualizes the nodes and the path in a 3D plot.
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
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=0.75)

    # Plot the inner circle in the XY plane (z = 0)
    theta = np.linspace(0, 2 * np.pi, 100)
    x_circle_xy = inner_radius * np.cos(theta)
    y_circle_xy = inner_radius * np.sin(theta)
    z_circle_xy = np.zeros_like(theta)
    ax.plot(x_circle_xy, y_circle_xy, z_circle_xy, color='cyan', label='Inner Circle (XY plane)')

    # Plot the inner circle in the ZY plane (x = 0)
    y_circle_zy = inner_radius * np.cos(theta)
    z_circle_zy = inner_radius * np.sin(theta)
    x_circle_zy = np.zeros_like(theta)
    ax.plot(x_circle_zy, y_circle_zy, z_circle_zy, color='magenta', label='Inner Circle (ZY plane)')

    # Set axis labels
    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')

    plt.show()
