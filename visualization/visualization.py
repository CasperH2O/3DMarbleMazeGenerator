# visualization/visualization.py

import plotly.graph_objects as go

from cad.cases.case import Case
from cad.path_segment import PathSegment
from obstacles.obstacle import Obstacle
from puzzle.node import Node

from .visualization_helpers import (
    plot_casing,
    plot_nodes,
    plot_obstacles_raw_paths,
    plot_puzzle_path,
    plot_segments,
)


def visualize_path_architect(
    nodes: list[Node],
    segments: list[PathSegment],
    casing: Case,
    puzzle_path: list[Node],
    obstacles: list[Obstacle],
):
    """
    Visualizes the nodes and path segments as defined by path architect.
    """

    fig = go.Figure()

    # Plot all nodes with shared styling.
    for trace in plot_nodes(nodes, segments):
        fig.add_trace(trace)

    # Segments
    for trace in plot_segments(segments):
        fig.add_trace(trace)

    # Add puzzle path (hidden by default; toggle in legend)
    for trace in plot_puzzle_path(puzzle_path):
        fig.add_trace(trace)

    # Add casing traces.
    for trace in plot_casing(casing):
        fig.add_trace(trace)

    if obstacles:
        for trace in plot_obstacles_raw_paths(obstacles):
            fig.add_trace(trace)

    # Define camera positions
    camera_views = {
        "Iso": dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        "Front": dict(eye=dict(x=0, y=1.5, z=0)),
        "Side": dict(eye=dict(x=1.5, y=0, z=0)),
        "Top": dict(eye=dict(x=0, y=0, z=1.5)),
    }

    fig.update_layout(
        title="Path Visualization",
        template="plotly_dark",
        scene=dict(
            xaxis_title="X (width, mm)",
            yaxis_title="Y (length, mm)",
            zaxis_title="Z (height, mm)",
            aspectmode="data",
            camera=dict(
                projection=dict(type="orthographic"), eye=camera_views["Iso"]["eye"]
            ),
        ),
        margin=dict(l=0, r=0, t=40, b=0),  # adjust top margin for title
        updatemenus=[
            # Projection dropdown
            dict(
                buttons=[
                    dict(
                        label="Orthographic",
                        method="relayout",
                        args=["scene.camera.projection.type", "orthographic"],
                    ),
                    dict(
                        label="Perspective",
                        method="relayout",
                        args=["scene.camera.projection.type", "perspective"],
                    ),
                ],
                direction="down",
                showactive=True,
                x=0.0,
                y=1.15,
                xanchor="left",
                font=dict(size=12),
                pad=dict(r=10, t=10),
            ),
            # Viewpoint dropdown
            dict(
                buttons=[
                    dict(
                        label=name,
                        method="relayout",
                        args=["scene.camera.eye", cam["eye"]],
                    )
                    for name, cam in camera_views.items()
                ],
                direction="down",
                showactive=True,
                x=0.3,
                y=1.15,
                xanchor="left",
                font=dict(size=12),
                pad=dict(r=10, t=10),
            ),
        ],
    )

    fig.show()
