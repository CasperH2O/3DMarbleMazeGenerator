# streamlit_app.py

"""Streamlit entry point for generating and visualizing puzzles."""

from importlib import import_module, util
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import streamlit as st

from cad.cases.case_model_base import CaseManufacturer
from config import CaseShape, Config, apply_case_manufacturer_overrides
from model_assembly import export_components
from puzzle.puzzle import Puzzle
from visualization.visualization import visualize_path_architect

CASE_SHAPE_OPTIONS = list(CaseShape)
MANUFACTURER_OPTIONS = [
    CaseManufacturer.GENERIC,
    CaseManufacturer.SPHERE_SAIDKOCC_100_MM,
    CaseManufacturer.SPHERE_PLAYTASTIC_120_MM,
]
MANUFACTURER_LABELS = {
    CaseManufacturer.GENERIC: "Generic",
    CaseManufacturer.SPHERE_SAIDKOCC_100_MM: "SaidKocc 100 mm",
    CaseManufacturer.SPHERE_PLAYTASTIC_120_MM: "Playtastic 120 mm",
}


def _get_pyvista_components() -> tuple[ModuleType, Callable] | None:
    """Return the PyVista and stpyvista components if available."""

    pyvista_spec = util.find_spec("pyvista")
    stpyvista_spec = util.find_spec("stpyvista")

    if not pyvista_spec or not stpyvista_spec:
        return None

    pyvista_module = import_module("pyvista")
    stpyvista_component = import_module("stpyvista").stpyvista
    return pyvista_module, stpyvista_component


def _clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp ``value`` to the inclusive range between ``minimum`` and ``maximum``."""

    return max(minimum, min(value, maximum))


def _load_stl_files(export_root: str | Path) -> list[Path]:
    """Return STL files from the export root, if available."""

    root_path = Path(export_root)
    if not root_path.exists():
        return []

    return sorted(root_path.rglob("*.stl"))


def _build_pyvista_plotter(stl_files: list[Path], pyvista_module: ModuleType) -> Any:
    """Return a PyVista plotter containing the provided STL meshes."""

    plotter = pyvista_module.Plotter()
    added_mesh = False

    for stl_file in stl_files:
        try:
            mesh = pyvista_module.read(stl_file)
        except Exception as mesh_error:  # noqa: BLE001
            st.warning(f"Could not load {stl_file.name}: {mesh_error}")
            continue

        mesh_name = stl_file.stem
        name_lower = mesh_name.lower()
        opacity = 0.05 if ("case" in name_lower or "casing" in name_lower) else 1.0
        color = _color_from_mesh_name(mesh_name)

        plotter.add_mesh(
            mesh,
            name=mesh_name,
            color=color,
            opacity=opacity,
            show_edges=False,
        )
        added_mesh = True

    if not added_mesh:
        return None

    background_color = _color_to_rgb(
        st.get_option("theme.backgroundColor") or "#0e1117"
    )
    try:
        plotter.set_background(color=(*background_color, 0))
    except Exception:
        plotter.set_background(background_color)

    try:
        plotter.enable_terrain_style()
    except Exception:
        plotter.reset_camera()
    else:
        plotter.reset_camera()
    plotter.enable_anti_aliasing()
    return plotter


def _color_from_mesh_name(name: str) -> tuple[float, float, float]:
    """Return an RGB tuple that matches the part's configured color when possible."""

    name_lower = name.lower()

    if name_lower.startswith("standard path"):
        try:
            index = int(name_lower.split("standard path")[-1]) - 1
        except ValueError:
            index = 0
        colors = Config.Puzzle.PATH_COLORS
        return _color_to_rgb(colors[index % len(colors)])

    if "support path" in name_lower:
        return _color_to_rgb(Config.Puzzle.SUPPORT_MATERIAL_COLOR)

    if "accent color path" in name_lower:
        return _color_to_rgb(Config.Puzzle.PATH_ACCENT_COLOR)

    if "mounting ring" in name_lower or "mounting clip" in name_lower:
        return _color_to_rgb(Config.Puzzle.MOUNTING_RING_COLOR)

    if "path bridges" in name_lower:
        return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])

    if name_lower.startswith("base top"):
        return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])

    if name_lower.startswith("base bottom"):
        return _color_to_rgb(Config.Puzzle.MOUNTING_RING_COLOR)

    if name_lower.startswith("base edge"):
        return _color_to_rgb(Config.Puzzle.PATH_ACCENT_COLOR)

    if "base" in name_lower:
        return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])

    if "case" in name_lower or "casing" in name_lower or "dome" in name_lower:
        return _color_to_rgb(Config.Puzzle.TRANSPARENT_CASE_COLOR)

    return _color_to_rgb(Config.Puzzle.PATH_COLORS[0])


def _color_to_rgb(color: Any) -> tuple[float, float, float]:
    """Convert color inputs (hex strings, Color, tuples) to an RGB tuple."""

    if isinstance(color, str) and color.startswith("#"):
        hex_value = color.lstrip("#")
        if len(hex_value) in {6, 8}:  # ignore alpha if present
            r = int(hex_value[0:2], 16) / 255
            g = int(hex_value[2:4], 16) / 255
            b = int(hex_value[4:6], 16) / 255
            return (r, g, b)

    if hasattr(color, "r") and hasattr(color, "g") and hasattr(color, "b"):
        return (float(color.r), float(color.g), float(color.b))

    if isinstance(color, (tuple, list)) and len(color) >= 3:
        return tuple(float(component) for component in color[:3])  # type: ignore[misc]

    return (0.7, 0.7, 0.7)


def main() -> None:
    """Launch the Streamlit UI for generating and visualizing puzzles."""

    st.set_page_config(page_title="3D Marble Maze Designer", layout="wide")
    st.sidebar.title("3D Marble Maze Designer")

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
    manufacturer = st.sidebar.selectbox(
        "Case manufacturer",
        options=MANUFACTURER_OPTIONS,
        index=MANUFACTURER_OPTIONS.index(Config.Puzzle.CASE_MANUFACTURER),
        format_func=lambda option: MANUFACTURER_LABELS.get(option, option.value),
    )

    Config.Puzzle.CASE_MANUFACTURER = manufacturer
    apply_case_manufacturer_overrides()

    case_shape: CaseShape = Config.Puzzle.CASE_SHAPE
    if manufacturer == CaseManufacturer.GENERIC:
        case_shape = st.sidebar.selectbox(
            "Case shape",
            options=CASE_SHAPE_OPTIONS,
            index=CASE_SHAPE_OPTIONS.index(Config.Puzzle.CASE_SHAPE),
            format_func=lambda shape: shape.value,
        )

    current_key = f"{manufacturer.value}-{case_shape.value}-{seed}-{waypoint_count}"
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
        visualization.update_layout(height=720)
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
                        export_root = export_components(puzzle)
                        stl_progress.progress(0.5, text="Collecting STL files...")

                        if export_root:
                            stl_files = _load_stl_files(export_root)
                            st.session_state["stl_exports"] = {
                                "key": f"{manufacturer.value}-{case_shape.value}-{seed}-{waypoint_count}",
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
                            plotter = _build_pyvista_plotter(
                                selected_files, pyvista_module
                            )
                            if plotter:
                                selected_names = [path.stem for path in selected_files]
                                selection_key = (
                                    "-".join(sorted(selected_names)) or "all"
                                )
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


if __name__ == "__main__":
    main()
