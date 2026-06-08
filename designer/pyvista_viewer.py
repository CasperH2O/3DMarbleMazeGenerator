from importlib import import_module, util
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import streamlit as st

from .colors import _color_from_mesh_name, _color_to_rgb


def _get_pyvista_components() -> tuple[ModuleType, Callable] | None:
    pyvista_spec = util.find_spec("pyvista")
    stpyvista_spec = util.find_spec("stpyvista")

    if not pyvista_spec or not stpyvista_spec:
        return None

    pyvista_module = import_module("pyvista")
    stpyvista_component = import_module("stpyvista").stpyvista
    return pyvista_module, stpyvista_component


def _build_pyvista_plotter(stl_files: list[Path], pyvista_module: ModuleType) -> Any:
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

    # Set up camera view with parameters
    plotter.camera_position = "iso"
    plotter.camera.azimuth = -10
    plotter.camera.elevation = -20

    # Enable terrain interaction style (shift to pan, mouse wheel to zoom)
    try:
        plotter.enable_terrain_style()
    except Exception:
        pass  # Fallback if terrain style not available

    plotter.enable_anti_aliasing()
    return plotter
