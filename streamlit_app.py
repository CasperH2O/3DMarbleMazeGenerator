# streamlit_app.py

"""Streamlit entry point for generating and visualizing puzzles."""

from pathlib import Path

import streamlit as st
from streamlit_stl import stl_from_file

from config import CaseShape, Config
from model_assembly import export_components
from puzzle.puzzle import Puzzle
from visualization.visualization import visualize_path_architect


CASE_SHAPE_OPTIONS = list(CaseShape)


def _clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp ``value`` to the inclusive range between ``minimum`` and ``maximum``."""

    return max(minimum, min(value, maximum))


def _load_stl_files(export_root: str | Path) -> list[Path]:
    """Return STL files from the export root, if available."""

    root_path = Path(export_root)
    if not root_path.exists():
        return []

    return sorted(root_path.rglob("*.stl"))


def main() -> None:
    """Launch the Streamlit UI for generating and visualizing puzzles."""

    st.set_page_config(page_title="3D Marble Maze Visualizer", layout="wide")
    st.title("3D Marble Maze Visualizer")

    Config.Manufacturing.EXPORT_STL = True

    st.sidebar.header("Configuration")
    seed = st.sidebar.slider(
        "Seed", min_value=1, max_value=10, value=_clamp(Config.Puzzle.SEED, 1, 10)
    )
    waypoint_count = st.sidebar.slider(
        "Waypoint nodes",
        min_value=0,
        max_value=5,
        value=_clamp(Config.Puzzle.NUMBER_OF_WAYPOINTS, 0, 5),
    )
    case_shape = st.sidebar.selectbox(
        "Case shape",
        options=CASE_SHAPE_OPTIONS,
        index=CASE_SHAPE_OPTIONS.index(Config.Puzzle.CASE_SHAPE),
        format_func=lambda shape: shape.value,
    )

    current_key = f"{case_shape.value}-{seed}-{waypoint_count}"
    st.session_state.setdefault("stl_exports", {"key": None, "path": None, "files": []})
    if st.session_state["stl_exports"].get("key") != current_key:
        st.session_state["stl_exports"] = {"key": current_key, "path": None, "files": []}

    puzzle = None
    visualization = None

    try:
        Config.Puzzle.NUMBER_OF_WAYPOINTS = waypoint_count
        Config.Puzzle.SEED = int(seed)
        Config.Puzzle.CASE_SHAPE = case_shape

        puzzle = Puzzle(
            node_size=Config.Puzzle.NODE_SIZE,
            seed=int(seed),
            case_shape=case_shape,
        )

        visualization = visualize_path_architect(
            puzzle.nodes,
            puzzle.path_architect.segments,
            puzzle.casing,
            puzzle.total_path,
            puzzle.obstacle_manager.placed_obstacles,
        )
    except Exception as generation_error:  # noqa: BLE001
        st.error(f"Puzzle generation failed: {generation_error}")

    if puzzle and visualization:
        st.subheader("Puzzle Overview")
        st.write(
            f"Nodes: {len(puzzle.nodes)} · "
            f"Segments: {len(puzzle.path_architect.segments)} · "
            f"Obstacles: {len(puzzle.obstacle_manager.placed_obstacles)}"
        )

        visualization_column, stl_column = st.columns(2, gap="large")

        with visualization_column:
            st.markdown("#### 3D Path Visualization")
            st.plotly_chart(visualization, use_container_width=True)

        with stl_column:
            st.markdown("#### 3D Printable STL Preview")
            st.caption(
                "Generate printable parts with model assembly, then preview any exported STL."
            )

            progress_placeholder = st.empty()
            generate_stl = st.button(
                "Generate STL files",
                type="primary",
                disabled=puzzle is None,
                help="Runs model assembly and exports all printable parts to STL files.",
            )

            if generate_stl and puzzle:
                stl_progress = progress_placeholder.progress(0, text="Exporting STL files...")
                try:
                    export_root = export_components(puzzle)
                    stl_progress.progress(0.5, text="Collecting STL files...")

                    if export_root:
                        stl_files = _load_stl_files(export_root)
                        st.session_state["stl_exports"] = {
                            "key": f"{case_shape.value}-{seed}-{waypoint_count}",
                            "path": export_root,
                            "files": stl_files,
                        }
                        stl_progress.progress(1.0, text="STL files ready.")
                    else:
                        stl_progress.empty()
                        st.warning("STL export did not produce any files.")
                except Exception as stl_error:  # noqa: BLE001
                    stl_progress.empty()
                    st.error(f"Failed to prepare STL preview: {stl_error}")
                else:
                    stl_progress.empty()

            export_state = st.session_state.get("stl_exports", {})

            if export_state.get("files"):
                relative_names = [
                    str(
                        Path(stl_file).relative_to(export_state["path"])
                        if export_state.get("path")
                        else stl_file.name
                    )
                    for stl_file in export_state["files"]
                ]

                selection_key = f"stl-selection-{export_state.get('key', 'default')}"
                selected_label = st.selectbox(
                    "Select an STL file to preview",
                    options=relative_names,
                    index=0,
                    key=selection_key,
                )

                selected_file = export_state["files"][relative_names.index(selected_label)]
                viewer_key = f"stl-viewer-{export_state.get('key', 'default')}-{selected_label}"
                stl_from_file(
                    str(selected_file),
                    height=450,
                    key=viewer_key,
                    auto_rotate=True,
                )
            elif export_state.get("path"):
                st.warning(
                    "No STL files were found in the export folder after generation."
                )
            else:
                st.info("Click \"Generate STL files\" to export and preview any part.")


if __name__ == "__main__":
    main()
