from pathlib import Path

import streamlit as st

from model_assembly import export_components
from puzzle.puzzle import Puzzle

from ..pyvista_viewer import _build_pyvista_plotter, _get_pyvista_components
from ..sidebar import SidebarState
from ..utils import _load_stl_files


def render_export_tab(puzzle: Puzzle, sidebar_state: SidebarState, current_key: str) -> None:
    st.markdown("#### 3D Printable STL Preview")

    export_state = st.session_state.get("stl_exports", {})
    progress_placeholder = st.empty()
    export_ready_for_config = (
        bool(export_state.get("files"))
        and export_state.get("key") == current_key
    )

    if not export_ready_for_config:
        generate_stl = st.button(
            "Generate STL files",
            type="primary",
            disabled=puzzle is None,
            help="Runs model assembly and exports all printable parts to STL files.",
        )

        if generate_stl and puzzle:
            stl_progress = progress_placeholder.progress(
                0, text="Exporting STL files..."
            )
            try:
                export_root = export_components(
                    puzzle, apply_manufacturing_preparation=False
                )
                stl_progress.progress(0.5, text="Collecting STL files...")

                if export_root:
                    stl_files = _load_stl_files(export_root)
                    # Store the full cache key (including obstacle and profile
                    # hashes) so the exported state survives Streamlit reruns.
                    st.session_state["stl_exports"] = {
                        "key": current_key,
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
    else:
        st.caption("STL files are ready. Change configuration to regenerate.")

    export_state = st.session_state.get("stl_exports", export_state)

    if export_state.get("files"):
        relative_names = [
            str(
                Path(stl_file).relative_to(export_state["path"])
                if export_state.get("path")
                else stl_file.name
            )
            for stl_file in export_state["files"]
        ]

        visibility_key = f"stl-visibility-{export_state.get('key', 'default')}"
        default_visibility = {name: True for name in relative_names}
        st.session_state.setdefault(visibility_key, default_visibility)

        viewer_container = st.container()
        visibility_state = st.session_state[visibility_key]
        selected_files: list[Path] = []
        for index, name in enumerate(relative_names):
            visibility_state[name] = st.checkbox(
                f"Show {name}",
                value=visibility_state.get(name, True),
                key=f"{visibility_key}-{index}",
            )
            if visibility_state[name]:
                selected_files.append(export_state["files"][index])

        with viewer_container:
            viewer_placeholder = st.empty()

            if selected_files:
                pyvista_components = _get_pyvista_components()
                if pyvista_components is None:
                    viewer_placeholder.info(
                        "Install optional dependencies to enable the combined PyVista"
                        ' viewer: pip install "pyvista==0.44.1 stpyvista==0.0.15'
                        ' vtk==9.3.1".'
                    )
                else:
                    viewer_placeholder.info("Loading 3D viewer...")
                    pyvista_module, stpyvista_component = pyvista_components
                    plotter = _build_pyvista_plotter(selected_files, pyvista_module)
                    if plotter:
                        selected_names = [path.stem for path in selected_files]
                        selection_key = "-".join(sorted(selected_names)) or "all"
                        viewer_key = (
                            f"stl-viewer-{export_state.get('key', 'default')}-"
                            f"{selection_key}"
                        )
                        with viewer_placeholder.container():
                            stpyvista_component(plotter, key=viewer_key)
                    else:
                        viewer_placeholder.warning(
                            "No STL meshes could be loaded for preview."
                        )
            else:
                viewer_placeholder.info(
                    "Select at least one STL file to include in the combined view."
                )
    elif export_state.get("path"):
        st.warning(
            "No STL files were found in the export folder after generation."
        )
    else:
        st.info('Click "Generate STL files" to export and preview any part.')
