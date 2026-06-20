# assembly/viewer.py

import colorsys
import random

import numpy as np
from ocp_vscode import (
    Animation,
    Camera,
    StudioTextureMapping,
    set_defaults,
    set_viewer_config,
    show_object,
    status,
)
from threejs_materials import PbrProperties

from assembly.casing import CasePart
from config import Config
from puzzle.utils.enums import Theme


def _load_material(name: str, scale: tuple) -> PbrProperties | None:
    """Load a GPU Open PBR material by name and apply UV scale. Returns None on failure."""
    try:
        return PbrProperties.from_gpuopen(name).scale(*scale)
    except Exception as e:
        print(f"[viewer] Could not load material '{name}': {e}")
        return None


def _get_materials() -> dict:
    """Return a dict of role -> PbrProperties (or None) based on config."""
    if not Config.Materials.ENABLED:
        return {"casing": None, "track": None, "ball": None}
    cfg = Config.Materials
    return {
        "casing": _load_material(cfg.CASING_MATERIAL, cfg.CASING_MATERIAL_SCALE),
        "track": _load_material(cfg.TRACK_MATERIAL, cfg.TRACK_MATERIAL_SCALE),
        "ball": _load_material(cfg.BALL_MATERIAL, cfg.BALL_MATERIAL_SCALE),
    }


def _is_transparent(color: str) -> bool:
    """True if color is '#RRGGBBAA' with AA != 'FF' (i.e., not fully opaque)."""
    if not isinstance(color, str) or not color.startswith("#"):
        return False  # treat unknown/absent as opaque
    if len(color) == 9:  # '#RRGGBBAA'
        return color[-2:].upper() != "FF"
    return False  # '#RRGGBB' (no alpha) -> opaque


def _apply_generic_distinct_colors_per_part(parts: list, seed: int) -> None:
    """
    Update part colors for maximum contrast with evenly spaced HSV space, skip transparent, shuffle colors
    """
    if not parts:
        return

    # Remove transparent parts in-place
    i = 0
    while i < len(parts):
        c = getattr(parts[i], "color", None)
        if _is_transparent(c):
            parts.pop(i)
        else:
            i += 1

    n = len(parts)
    if n == 0:
        return

    # Build evenly spaced HSV colors
    colors = []
    for idx in range(n):
        h = idx / n
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        colors.append(
            f"#{int(round(r * 255)):02X}{int(round(g * 255)):02X}{int(round(b * 255)):02X}FF"
        )

    # Shuffle colors
    rng = random.Random(seed if seed is not None else Config.Puzzle.SEED)
    rng.shuffle(colors)

    # Assign colors to parts
    for p, c in zip(parts, colors):
        p.color = c


def display_parts(
    case_parts,
    base_parts,
    standard_paths,
    support_path,
    coloring_path,
    obstacle_extras,
    ball,
    ball_path,
    ball_path_direction,
):
    """
    Display all puzzle physical objects.
    """
    materials = _get_materials()
    use_pbr = Config.Materials.ENABLED and any(v is not None for v in materials.values())

    # Set the default camera position, to not adjust on new show
    set_defaults(
        reset_camera=Camera.KEEP,
        black_edges=True,
        studio_texture_mapping=StudioTextureMapping.PARAMETRIC if use_pbr else None,
    )

    # If Generic theme, assign distinct HSV colors per part
    if Config.Puzzle.THEME == Theme.HIGH_CONTRAST:
        # Build the list of parts to recolor
        parts_to_color = []
        parts_to_color.extend(case_parts or [])
        parts_to_color.extend(base_parts or [])
        parts_to_color.extend(standard_paths or [])

        if support_path:
            parts_to_color.append(support_path)
        if coloring_path:
            parts_to_color.append(coloring_path)
        if obstacle_extras:
            parts_to_color.append(obstacle_extras)

        _apply_generic_distinct_colors_per_part(parts_to_color, Config.Puzzle.SEED)

    # Display the ball, its path and direction
    show_object([ball, ball_path, ball_path_direction], name="Path Indicator", material=materials["ball"])

    if case_parts:
        if len(case_parts) == 1:
            show_object(case_parts[0], material=materials["casing"])
        else:
            show_object(case_parts, name="Casing", material=materials["casing"])

    # The paths, standard paths, support path and coloring path
    if standard_paths:
        if len(standard_paths) == 1:
            show_object(standard_paths[0], material=materials["track"])
        else:
            show_object(standard_paths, name="Standard Paths", material=materials["track"])

    if support_path:
        show_object(support_path, material=materials["track"])

    if coloring_path:
        show_object(coloring_path, material=materials["track"])

    if obstacle_extras:
        show_object(obstacle_extras, name="Obstacle Extra's", material=materials["track"])

    # Display each part from the base
    if base_parts:
        show_object(base_parts, name="Base")


def set_viewer():
    """
    Set the viewer configuration. Hide edges for certain parts, create animation.
    """
    st = status()["states"].copy()

    target_leaf_names = {
        CasePart.CASING.value,  # "Casing" (only if it's a leaf/singleton)
        CasePart.CASE_TOP.value,  # "Case Top"
        CasePart.CASE_BOTTOM.value,  # "Case Bottom"
        "Ball",
        "Ball Path Direction",
    }

    # Only touch leaves whose basename matches one of the targets
    for path, val in list(st.items()):
        if not (isinstance(val, list) and len(val) == 2):
            continue
        basename = path.rsplit("/", 1)[-1]
        if basename in target_leaf_names:
            shape_on, _edges_on = val
            st[path] = [shape_on, 0]  # keep current shape visibility, hide edges

    # Rotating animation — must be created before any viewer state changes
    animation = Animation()
    times = np.linspace(0, 12, 33)  # 12 seconds split in 0.2 intervals
    values = np.linspace(0, -360, 33)  # as many positions as times

    # add all groups to animation tracks except for the base
    for grp in list(status()["states"].keys()):
        if "/Group/Base" in grp:
            continue
        animation.paths.append(grp)
        animation.add_track(grp, "rz", times, values)

    animation.animate(1)

    set_viewer_config(states=st)
