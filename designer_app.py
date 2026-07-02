# designer_app.py

"""Streamlit entry point for generating and visualizing puzzles."""

import streamlit as st

from config import Config, PathProfileType
from puzzle.puzzle import Puzzle
from visualization.visualization import visualize_path_architect

from designer.sidebar import render_sidebar
from designer.tabs.design_tab import render_design_tab
from designer.tabs.export_tab import render_export_tab


def main() -> None:
    """Launch the Streamlit UI for generating and visualizing puzzles."""

    st.set_page_config(page_title="3D Marble Maze Designer", layout="wide")
    st.sidebar.title("3D Marble Maze Designer")

    # The preview tab consumes STL files, so export STL only. With 3MF also
    # enabled, export_all would return the 3MF folder and the STL lookup fails.
    Config.Manufacturing.EXPORT_STL = True
    Config.Manufacturing.EXPORT_3MF = False

    sidebar_state = render_sidebar()

    # Initialize manual obstacles in session state
    if "manual_obstacles" not in st.session_state:
        st.session_state["manual_obstacles"] = []
    # Initialize profile overrides in session state
    if "profile_overrides" not in st.session_state:
        st.session_state["profile_overrides"] = []

    # Include obstacle configuration and profile overrides in cache key
    obstacle_hash = hash(str(st.session_state["manual_obstacles"]))
    profile_hash = hash(str(st.session_state["profile_overrides"]))
    s = sidebar_state
    current_key = (
        f"{s.manufacturer.value}-{s.case_shape.value}-{s.seed}-{s.waypoint_count}"
        f"-{obstacle_hash}-{profile_hash}"
    )

    st.session_state.setdefault("stl_exports", {"key": None, "path": None, "files": []})
    if st.session_state["stl_exports"].get("key") != current_key:
        st.session_state["stl_exports"] = {
            "key": current_key,
            "path": None,
            "files": [],
        }

    puzzle = None
    visualization = None

    try:
        Config.Puzzle.NUMBER_OF_WAYPOINTS = sidebar_state.waypoint_count
        Config.Puzzle.SEED = sidebar_state.seed
        Config.Puzzle.CASE_SHAPE = sidebar_state.case_shape

        # Apply manual obstacles from session state
        Config.Obstacles.MANUAL_PLACEMENTS = tuple(st.session_state["manual_obstacles"])

        # Apply profile overrides from session state (only enabled ones)
        Config.Path.PATH_PROFILE_TYPE_OVERRIDES = {
            override["segment_index"]: PathProfileType(override["profile_type"])
            for override in st.session_state["profile_overrides"]
            if override.get("enabled", True)
        }

        puzzle = Puzzle(
            node_size=Config.Puzzle.NODE_SIZE,
            seed=sidebar_state.seed,
            case_shape=sidebar_state.case_shape,
        )

        visualization = visualize_path_architect(
            puzzle.nodes,
            puzzle.path_architect.segments,
            puzzle.casing,
            puzzle.total_path,
            puzzle.obstacle_manager.placed_obstacles,
            failed_manual_placements=puzzle.obstacle_manager.failed_manual_placements,
            node_size=Config.Puzzle.NODE_SIZE,
            rejected_spline_segments=puzzle.path_architect.rejected_spline_segments,
            spline_voxel_debug=puzzle.path_architect.spline_voxel_debug,
        )
    except Exception as generation_error:  # noqa: BLE001
        st.error(f"Puzzle generation failed: {generation_error}")

    if puzzle and visualization:
        visualization.update_layout(height=720)
        st.subheader("Puzzle Overview")
        st.write(
            f"Nodes: {len(puzzle.nodes)} · "
            f"Segments: {len(puzzle.path_architect.segments)} · "
            f"Obstacles: {len(puzzle.obstacle_manager.placed_obstacles)}"
        )

        design_tab_col, export_tab_col = st.tabs(["Design & Obstacles", "3D Preview & Export"])

        with design_tab_col:
            render_design_tab(puzzle, visualization)

        with export_tab_col:
            render_export_tab(puzzle, sidebar_state, current_key)


if __name__ == "__main__":
    main()
