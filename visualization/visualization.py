# visualization/visualization.py

import plotly.graph_objects as go

from cad.cases.case_model_base import Case
from cad.path_segment import PathSegment
from obstacles.obstacle import Obstacle
from puzzle.node import Node

from .visualization_helpers import (
    plot_casing,
    plot_invalid_obstacles,
    plot_nodes,
    plot_obstacles_raw_paths,
    plot_puzzle_path,
    plot_rejected_splines,
    plot_segments,
    plot_spline_voxels,
)


def visualize_path_architect(
    nodes: list[Node],
    segments: list[PathSegment],
    casing: Case,
    puzzle_path: list[Node],
    obstacles: list[Obstacle],
    failed_manual_placements: list[dict] = None,
    node_size: float = None,
    rejected_spline_segments: list = None,
    spline_voxel_debug: list = None,
):
    """
    Visualizes the nodes and path segments as defined by path architect.

    Parameters
    ----------
    nodes : list[Node]
        All puzzle nodes
    segments : list[PathSegment]
        Path segments connecting nodes
    casing : Case
        The puzzle casing
    puzzle_path : list[Node]
        The complete path through the puzzle
    obstacles : list[Obstacle]
        Successfully placed obstacles
    failed_manual_placements : list[dict], optional
        Failed manual obstacle placement attempts for visualization
    node_size : float, optional
        Size of grid nodes for visualization
    rejected_spline_segments : list, optional
        SPLINE segments demoted to COMPOUND by the occupancy check
        (cad.spline_occupancy.RejectedSpline), highlighted in red.
    spline_voxel_debug : list, optional
        Debug data (cad.spline_occupancy.SplineVoxelDebug) used to draw the cubes
        each spline occupies. Requires node_size.

    Returns
    -------
    go.Figure
        Configured 3D Plotly visualization of the puzzle layout.
    """

    fig = go.Figure()

    # Plot all nodes with shared styling.
    for trace in plot_nodes(
        nodes,
        segments,
        obstacles_present=bool(obstacles),
    ):
        fig.add_trace(trace)

    # Segments
    for trace in plot_segments(segments):
        fig.add_trace(trace)

    # Highlight splines demoted to compound by the occupancy check (hidden by default)
    for trace in plot_rejected_splines(rejected_spline_segments):
        fig.add_trace(trace)

    # Cubes for the voxels each spline occupies (hidden by default)
    for trace in plot_spline_voxels(spline_voxel_debug, node_size):
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

    # Add invalid obstacle traces if provided
    if failed_manual_placements and node_size:
        for trace in plot_invalid_obstacles(failed_manual_placements, node_size):
            fig.add_trace(trace)

    # Define camera positions
    camera_views = {
        "Iso": dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        "Front": dict(eye=dict(x=0, y=1.5, z=0)),
        "Side": dict(eye=dict(x=1.5, y=0, z=0)),
        "Top": dict(eye=dict(x=0, y=0, z=1.5)),
    }

    # layout, settings, view buttons
    fig.update_layout(
        title="Path Visualization",
        template="plotly_dark",
        scene=dict(
            xaxis=dict(
                title="X (width, mm)",
                backgroundcolor="rgba(0, 0, 0, 0)",
            ),
            yaxis=dict(
                title="Y (length, mm)",
                backgroundcolor="rgba(0, 0, 0, 0)",
            ),
            zaxis=dict(
                title="Z (height, mm)",
                backgroundcolor="rgba(0, 0, 0, 0)",
            ),
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

    return fig
