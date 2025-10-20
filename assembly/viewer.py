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


def _apply_generic_distinct_colors_per_part(parts: list, seed: int | None = None) -> None:
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
):
    """
    Display all puzzle physical objects.
    """
    # Set the default camera position, to not adjust on new show
    set_defaults(reset_camera=Camera.KEEP)

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

        _apply_generic_distinct_colors_per_part(parts_to_color)

    if case_parts:
        if len(case_parts) == 1:
            show_object(case_parts[0])
        else:
            show_object(case_parts, name="Casing")

    # Display each part from the base
    if base_parts:
        show_object(base_parts, name="Base")

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

    # Display the ball and its path
    show_object(ball)
    show_object(ball_path)


def set_viewer():
    """
    Set the viewer configuration.
    """

    # Do not draw lines on the following groups
    # FIXME works inconsistently
    groups_to_reset = {
        f"/Group/{CasePart.CASING.value}",
        f"/Group/{CasePart.CASE_TOP.value}",
        f"/Group/{CasePart.CASE_BOTTOM.value}",
        "/Group/Ball Path",
        "/Group/Ball",
    }
    current_states = status()["states"]

    # Update the viewer configuration so that the specified groups do not draw lines
    new_config = {
        group: ([1, 0] if group in groups_to_reset else viewer_config)
        for group, viewer_config in current_states.items()
    }

    set_viewer_config(states=new_config)

    # Rotating animation
    animation = Animation(Part())
    times = np.linspace(0, 6, 33)  # 4 seconds split in 0.2 intervals
    values = np.linspace(0, -360, 33)  # as many positions as times

    # Get all the groups for animation
    all_groups = current_states.keys()
    # add all groups to animation tracks except for the base
    for grp in all_groups:
        if grp == "/Group/Base":
            continue  # skip the Base group
        animation.add_track(grp, "rz", times, values)

    animation.animate(1)
