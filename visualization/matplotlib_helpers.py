# matplotlib_helpers.py

from puzzle.casing import SphereCasing, BoxCasing
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection


def plot_nodes(ax, nodes):
    xs = [node.x for node in nodes]
    ys = [node.y for node in nodes]
    zs = [node.z for node in nodes]

    # Determine colors and sizes based on node properties
    colors = []
    sizes = []
    for node in nodes:
        if node.puzzle_start:
            colors.append('yellow')  # Start node
            sizes.append(40)
        elif node.puzzle_end:
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