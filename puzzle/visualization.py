# puzzle/visualization.py

from puzzle.casing import SphereCasing, BoxCasing
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import plotly.graph_objects as go
import plotly.offline as pyo


def visualize_nodes_and_paths(nodes, total_path, casing):
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
        ax.plot(path_xs, path_ys, path_zs, color='black', linewidth=1)

    # Plot the casing based on its type
    if isinstance(casing, SphereCasing):
        # Create a wireframe sphere
        u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
        x_sphere = casing.inner_radius * np.cos(u) * np.sin(v)
        y_sphere = casing.inner_radius * np.sin(u) * np.sin(v)
        z_sphere = casing.inner_radius * np.cos(v)
        ax.plot_wireframe(x_sphere, y_sphere, z_sphere, color='cyan', linewidth=0.5, alpha=0.5)
    elif isinstance(casing, BoxCasing):
        # Define the 8 corners of the box
        hw = casing.half_width
        hh = casing.half_height
        hl = casing.half_length

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

        # Define the 6 faces of the box
        faces = [
            [corners[0], corners[1], corners[2], corners[3]],  # Bottom face
            [corners[4], corners[5], corners[6], corners[7]],  # Top face
            [corners[0], corners[1], corners[5], corners[4]],  # Front face
            [corners[2], corners[3], corners[7], corners[6]],  # Back face
            [corners[1], corners[2], corners[6], corners[5]],  # Right face
            [corners[4], corners[7], corners[3], corners[0]],  # Left face
        ]

        # Create a 3D polygon collection
        box = Poly3DCollection(faces, linewidths=0.5, edgecolors='black', alpha=0.1)
        box.set_facecolor('cyan')
        ax.add_collection3d(box)

    # Set axis labels and aspect ratio
    ax.set_xlabel('X axis')
    ax.set_ylabel('Y axis')
    ax.set_zlabel('Z axis')
    ax.set_box_aspect([1,1,1])  # Equal aspect ratio

    plt.show()


def visualize_nodes_and_paths_plotly(nodes, total_path, casing):
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
        # Plot the inner sphere as a wireframe
        u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
        x_sphere = casing.inner_radius * np.cos(u) * np.sin(v)
        y_sphere = casing.inner_radius * np.sin(u) * np.sin(v)
        z_sphere = casing.inner_radius * np.cos(v)

        sphere_wireframe = go.Surface(
            x=x_sphere,
            y=y_sphere,
            z=z_sphere,
            opacity=0.1,
            colorscale='Blues',
            showscale=False,
            name='Inner Sphere',
            lighting=dict(ambient=0.5),
            hoverinfo='skip'
        )
        casing_traces.append(sphere_wireframe)
    elif isinstance(casing, BoxCasing):
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

        # Define the edges as pairs of indices into the corners array
        edges = [
            (0, 1), (1,2), (2,3), (3,0),  # Bottom face
            (4,5), (5,6), (6,7), (7,4),  # Top face
            (0,4), (1,5), (2,6), (3,7)   # Vertical edges
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
            line=dict(color='black', width=1),
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