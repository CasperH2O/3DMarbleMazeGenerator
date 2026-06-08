from dataclasses import dataclass

import streamlit as st

from cad.cases.case_model_base import CaseManufacturer
from config import CaseShape, Config, apply_case_manufacturer_overrides
from puzzle.utils.enums import PathSegmentDesignStrategy

from .constants import CASE_SHAPE_OPTIONS, MANUFACTURER_LABELS, MANUFACTURER_OPTIONS
from .utils import _clamp


@dataclass
class SidebarState:
    seed: int
    waypoint_count: int
    manufacturer: CaseManufacturer
    case_shape: CaseShape


def render_sidebar() -> SidebarState:
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

    # Path design strategy options
    use_spline = st.sidebar.checkbox(
        "Enable Spline path strategy",
        value=PathSegmentDesignStrategy.SPLINE in Config.Path.PATH_SEGMENT_DESIGN_STRATEGY,
    )

    # Update path segment design strategy based on checkbox
    if use_spline:
        if PathSegmentDesignStrategy.SPLINE not in Config.Path.PATH_SEGMENT_DESIGN_STRATEGY:
            Config.Path.PATH_SEGMENT_DESIGN_STRATEGY.append(PathSegmentDesignStrategy.SPLINE)
    else:
        if PathSegmentDesignStrategy.SPLINE in Config.Path.PATH_SEGMENT_DESIGN_STRATEGY:
            Config.Path.PATH_SEGMENT_DESIGN_STRATEGY.remove(PathSegmentDesignStrategy.SPLINE)

    return SidebarState(
        seed=int(seed),
        waypoint_count=waypoint_count,
        manufacturer=manufacturer,
        case_shape=case_shape,
    )
