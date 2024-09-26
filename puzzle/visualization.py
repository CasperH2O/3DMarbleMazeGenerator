# puzzle/visualization.py

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import plotly.offline as pyo


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


def visualize_nodes_and_paths_plotly(nodes, total_path, inner_radius):
    # Create empty lists for nodes
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

    # Plot the inner circle in the XY plane (z = 0)
    theta = np.linspace(0, 2 * np.pi, 100)
    x_circle_xy = inner_radius * np.cos(theta)
    y_circle_xy = inner_radius * np.sin(theta)
    z_circle_xy = np.zeros_like(theta)

    circle_trace_xy = go.Scatter3d(
        x=x_circle_xy,
        y=y_circle_xy,
        z=z_circle_xy,
        mode='lines',
        line=dict(color='cyan', width=2),
        name="Inner Circle (XY plane)"
    )

    # Plot the inner circle in the ZY plane (x = 0)
    y_circle_zy = inner_radius * np.cos(theta)
    z_circle_zy = inner_radius * np.sin(theta)
    x_circle_zy = np.zeros_like(theta)

    circle_trace_zy = go.Scatter3d(
        x=x_circle_zy,
        y=y_circle_zy,
        z=z_circle_zy,
        mode='lines',
        line=dict(color='magenta', width=2),
        name="Inner Circle (ZY plane)"
    )

    # Combine all traces
    data = [scatter, circle_trace_xy, circle_trace_zy]
    if path_trace:
        data.append(path_trace)

    # Create the layout
    layout = go.Layout(
        scene=dict(
            xaxis_title='X axis',
            yaxis_title='Y axis',
            zaxis_title='Z axis'
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )

    # Create the figure
    fig = go.Figure(data=data, layout=layout)

    # Display the plot in a browser
    pyo.plot(fig, filename="3d_nodes_and_paths.html")
