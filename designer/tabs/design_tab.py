from typing import Any

import streamlit as st

from config import Config, PathProfileType
from puzzle.puzzle import Puzzle
from puzzle.utils.enums import ObstacleType


def render_design_tab(puzzle: Puzzle, visualization: Any) -> None:
    st.markdown("#### 3D Path Visualization")
    st.plotly_chart(visualization, width="stretch")

    st.markdown("#### Manual Obstacles")
    _render_obstacles_editor(puzzle)

    st.markdown("#### Path Profile Type Overrides")
    _render_profile_overrides_editor(puzzle)


def _render_obstacles_editor(puzzle: Puzzle) -> None:
    if st.session_state["manual_obstacles"]:
        # Header row
        hdr_name, hdr_x, hdr_y, hdr_z, hdr_rx, hdr_ry, hdr_rz, hdr_actions = (
            st.columns([2, 1, 1, 1, 1, 1, 1, 1])
        )
        with hdr_name:
            st.caption("Name")
        with hdr_x:
            st.caption("X")
        with hdr_y:
            st.caption("Y")
        with hdr_z:
            st.caption("Z")
        with hdr_rx:
            st.caption("Rot X")
        with hdr_ry:
            st.caption("Rot Y")
        with hdr_rz:
            st.caption("Rot Z")
        with hdr_actions:
            st.caption("Actions")

        obstacles_to_remove = []

        # Build a set of failed obstacles for quick lookup (by name and position)
        failed_obstacles = set()
        if puzzle.obstacle_manager.failed_manual_placements:
            for failed_obstacle in puzzle.obstacle_manager.failed_manual_placements:
                name = failed_obstacle.name
                origin = failed_obstacle.grid_origin
                if origin is not None:
                    # Create a key from name and position (rounded to avoid floating point issues)
                    key = (name, tuple(round(x, 2) for x in origin))
                    failed_obstacles.add(key)

        for idx, obstacle in enumerate(st.session_state["manual_obstacles"]):
            (
                col_name,
                col_x,
                col_y,
                col_z,
                col_rx,
                col_ry,
                col_rz,
                col_actions,
            ) = st.columns([2, 1, 1, 1, 1, 1, 1, 1])

            # Check if this obstacle failed validation
            obstacle_key = (
                obstacle["name"],
                tuple(round(x, 2) for x in obstacle["origin"]),
            )
            is_failed = obstacle_key in failed_obstacles

            with col_name:
                # Add error icon if this obstacle failed validation
                if is_failed:
                    st.text(f"{obstacle['name']} ❌")
                else:
                    st.text(obstacle["name"])

            with col_x:
                new_pos_x = st.number_input(
                    "X",
                    value=obstacle["origin"][0],
                    step=float(Config.Puzzle.NODE_SIZE),
                    key=f"obstacle_pos_x_{idx}",
                    label_visibility="collapsed",
                )
            with col_y:
                new_pos_y = st.number_input(
                    "Y",
                    value=obstacle["origin"][1],
                    step=float(Config.Puzzle.NODE_SIZE),
                    key=f"obstacle_pos_y_{idx}",
                    label_visibility="collapsed",
                )
            with col_z:
                new_pos_z = st.number_input(
                    "Z",
                    value=obstacle["origin"][2],
                    step=float(Config.Puzzle.NODE_SIZE),
                    key=f"obstacle_pos_z_{idx}",
                    label_visibility="collapsed",
                )
            with col_rx:
                new_rot_x = st.number_input(
                    "Rot X",
                    value=int(obstacle["orientation"][0]),
                    step=90,
                    key=f"obstacle_rot_x_{idx}",
                    label_visibility="collapsed",
                )
            with col_ry:
                new_rot_y = st.number_input(
                    "Rot Y",
                    value=int(obstacle["orientation"][1]),
                    step=90,
                    key=f"obstacle_rot_y_{idx}",
                    label_visibility="collapsed",
                )
            with col_rz:
                new_rot_z = st.number_input(
                    "Rot Z",
                    value=int(obstacle["orientation"][2]),
                    step=90,
                    key=f"obstacle_rot_z_{idx}",
                    label_visibility="collapsed",
                )
            with col_actions:
                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    is_enabled = st.checkbox(
                        "On",
                        value=obstacle["enabled"],
                        key=f"obstacle_enabled_{idx}",
                        label_visibility="collapsed",
                    )
                    if is_enabled != obstacle["enabled"]:
                        st.session_state["manual_obstacles"][idx]["enabled"] = is_enabled
                        st.rerun()
                with act_col2:
                    if st.button("🗑️", key=f"delete_obstacle_{idx}"):
                        obstacles_to_remove.append(idx)

            # Update obstacle if any values changed
            if (
                new_pos_x != obstacle["origin"][0]
                or new_pos_y != obstacle["origin"][1]
                or new_pos_z != obstacle["origin"][2]
                or float(new_rot_x) != obstacle["orientation"][0]
                or float(new_rot_y) != obstacle["orientation"][1]
                or float(new_rot_z) != obstacle["orientation"][2]
            ):
                st.session_state["manual_obstacles"][idx]["origin"] = (
                    new_pos_x,
                    new_pos_y,
                    new_pos_z,
                )
                st.session_state["manual_obstacles"][idx]["orientation"] = (
                    float(new_rot_x),
                    float(new_rot_y),
                    float(new_rot_z),
                )
                st.rerun()

        # Remove obstacles marked for deletion
        if obstacles_to_remove:
            for idx in sorted(obstacles_to_remove, reverse=True):
                st.session_state["manual_obstacles"].pop(idx)
            st.rerun()

    # Add new obstacle controls
    obstacle_types = list(ObstacleType)
    add_col1, add_col2 = st.columns([3, 1])
    with add_col1:
        selected_obstacle = st.selectbox(
            "Obstacle Type",
            options=obstacle_types,
            format_func=lambda x: x.value,
            key="new_obstacle_type",
            label_visibility="collapsed",
        )
    with add_col2:
        if st.button("Add Obstacle", type="primary", width="stretch"):
            new_obstacle = {
                "enabled": True,
                "name": selected_obstacle.value,
                "origin": (0.0, 0.0, 0.0),
                "orientation": (0.0, 0.0, 0.0),
            }
            st.session_state["manual_obstacles"].append(new_obstacle)
            st.rerun()


def _render_profile_overrides_editor(puzzle: Puzzle) -> None:
    # Get available segment main indices from the puzzle (unique, sorted)
    # Exclude index 1 which is hardcoded
    segment_indices = sorted(
        idx for idx in set(seg.main_index for seg in puzzle.path_architect.segments)
        if idx != 1
    )

    if st.session_state["profile_overrides"]:
        # Header row
        hdr_segment, hdr_profile, hdr_override_actions = st.columns([2, 3, 1])
        with hdr_segment:
            st.caption("Segment Index")
        with hdr_profile:
            st.caption("Profile Type")
        with hdr_override_actions:
            st.caption("Actions")

        overrides_to_remove = []

        for idx, override in enumerate(st.session_state["profile_overrides"]):
            col_segment, col_profile, col_actions = st.columns([2, 3, 1])

            current_segment_idx = override["segment_index"]
            segment_available = current_segment_idx in segment_indices

            # Auto-enable/disable based on segment availability
            current_enabled = override.get("enabled", True)
            if not segment_available and current_enabled:
                st.session_state["profile_overrides"][idx]["enabled"] = False
                st.session_state["profile_overrides"][idx]["auto_disabled"] = True
                st.session_state[f"override_enabled_{idx}"] = False
            elif segment_available and not current_enabled and override.get("auto_disabled", False):
                st.session_state["profile_overrides"][idx]["enabled"] = True
                st.session_state["profile_overrides"][idx]["auto_disabled"] = False
                st.session_state[f"override_enabled_{idx}"] = True

            with col_segment:
                # Use current index if available, otherwise show it but mark as unavailable
                display_indices = segment_indices if segment_available else [current_segment_idx] + segment_indices
                new_segment_index = st.selectbox(
                    "Segment",
                    options=display_indices,
                    index=0,
                    format_func=lambda x, seg=current_segment_idx, avail=segment_available: f"{x} (unavailable)" if x == seg and not avail else str(x),
                    key=f"override_segment_{idx}",
                    label_visibility="collapsed",
                )

            with col_profile:
                profile_types = Config.Path.PATH_PROFILE_TYPES
                current_profile = PathProfileType(override["profile_type"])
                if current_profile not in profile_types:
                    current_profile = profile_types[0] if profile_types else current_profile
                new_profile_type = st.selectbox(
                    "Profile Type",
                    options=profile_types,
                    index=profile_types.index(current_profile) if current_profile in profile_types else 0,
                    format_func=lambda x: x.value.replace("_", " ").title(),
                    key=f"override_profile_{idx}",
                    label_visibility="collapsed",
                )

            with col_actions:
                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    is_enabled = st.checkbox(
                        "On",
                        value=override.get("enabled", True),
                        key=f"override_enabled_{idx}",
                        label_visibility="collapsed",
                        disabled=not segment_available,
                    )
                    if is_enabled != override.get("enabled", True):
                        st.session_state["profile_overrides"][idx]["enabled"] = is_enabled
                        st.session_state["profile_overrides"][idx]["auto_disabled"] = False
                        st.rerun()
                with act_col2:
                    if st.button("🗑️", key=f"delete_override_{idx}"):
                        overrides_to_remove.append(idx)

            # Update override if any values changed
            if (
                new_segment_index != override["segment_index"]
                or new_profile_type.value != override["profile_type"]
            ):
                st.session_state["profile_overrides"][idx]["segment_index"] = int(new_segment_index)
                st.session_state["profile_overrides"][idx]["profile_type"] = new_profile_type.value
                # If segment changed to an available one, mark as not auto-disabled
                if new_segment_index in segment_indices:
                    st.session_state["profile_overrides"][idx]["auto_disabled"] = False
                st.rerun()

        # Remove overrides marked for deletion
        if overrides_to_remove:
            for idx in sorted(overrides_to_remove, reverse=True):
                st.session_state["profile_overrides"].pop(idx)
            st.rerun()

    # Add new override controls
    profile_type_options = Config.Path.PATH_PROFILE_TYPES

    # Initialize pending selections in session state
    if "pending_override_segment" not in st.session_state:
        st.session_state["pending_override_segment"] = segment_indices[0] if segment_indices else 0
    if "pending_override_profile" not in st.session_state:
        st.session_state["pending_override_profile"] = profile_type_options[0]

    # Validate stored segment is still valid
    current_seg = st.session_state["pending_override_segment"]
    if current_seg not in segment_indices:
        current_seg = segment_indices[0] if segment_indices else 0
        st.session_state["pending_override_segment"] = current_seg

    add_col1, add_col2, add_col3 = st.columns([2, 3, 1])
    with add_col1:
        st.selectbox(
            "Segment Index",
            options=segment_indices,
            index=segment_indices.index(current_seg) if current_seg in segment_indices else 0,
            key="pending_override_segment",
            label_visibility="collapsed",
        )
    with add_col2:
        current_profile = st.session_state["pending_override_profile"]
        if current_profile not in profile_type_options:
            current_profile = profile_type_options[0]
        st.selectbox(
            "Profile Type",
            options=profile_type_options,
            index=profile_type_options.index(current_profile),
            format_func=lambda x: x.value.replace("_", " ").title(),
            key="pending_override_profile",
            label_visibility="collapsed",
        )
    with add_col3:
        if st.button("Add Override", type="primary", key="add_override_button"):
            new_override = {
                "enabled": True,
                "segment_index": int(st.session_state["pending_override_segment"]),
                "profile_type": st.session_state["pending_override_profile"].value,
            }
            st.session_state["profile_overrides"].append(new_override)
            st.rerun()
