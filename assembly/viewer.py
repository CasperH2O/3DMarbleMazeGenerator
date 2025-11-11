# assembly/viewer.py

import colorsys
import random

import numpy as np
from build123d import Part
from ocp_vscode import (
    Animation,
    Camera,
    set_defaults,
    set_viewer_config,
    show_object,
    status,
)

from assembly.casing import CasePart
from config import Config
from puzzle.utils.enums import Theme


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
    # Set the default camera position, to not adjust on new show
    set_defaults(reset_camera=Camera.KEEP, black_edges=True)

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
    show_object([ball, ball_path, ball_path_direction], name="Path Indcator")

    if case_parts:
        if len(case_parts) == 1:
            show_object(case_parts[0])
        else:
            show_object(case_parts, name="Casing")

    # The paths, standard paths, support path and coloring path
    if standard_paths:
        if len(standard_paths) == 1:
            show_object(standard_paths[0])
        else:
            show_object(standard_paths, name="Standard Paths")

    if support_path:
        show_object(support_path)

    if coloring_path:
        show_object(coloring_path)

    if obstacle_extras:
        # TODO, prevent when empty
        show_object(obstacle_extras, name="Obstacle Extra's")

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

    set_viewer_config(states=st)

    # Rotating animation
    animation = Animation(Part())
    times = np.linspace(0, 12, 33)  # 12 seconds split in 0.2 intervals
    values = np.linspace(0, -360, 33)  # as many positions as times

    # add all groups to animation tracks except for the base
    for grp in list(status()["states"].keys()):
        if "/Group/Base" in grp:
            continue
        animation.add_track(grp, "rz", times, values)

    animation.animate(1)
