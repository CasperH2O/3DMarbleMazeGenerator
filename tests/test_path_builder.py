"""Tests for the PathBuilder helpers."""

import sys
from enum import Enum
from types import ModuleType, SimpleNamespace

import pytest

from puzzle.utils.enums import PathCurveModel, PathCurveType

if "cad.path_profile_type_shapes" not in sys.modules:
    path_profile_stub = ModuleType("cad.path_profile_type_shapes")

    class _PathProfileType(Enum):
        U_SHAPE = "u_shape"
        L_SHAPE_MIRRORED = "l_shape_mirrored"
        L_SHAPE_ADJUSTED_HEIGHT = "l_shape_adjusted_height"
        O_SHAPE = "o_shape"
        V_SHAPE = "v_shape"

    def _create_u_shape(*args, **kwargs):
        return None

    def _create_u_shape_path_color(*args, **kwargs):
        return None

    path_profile_stub.PathProfileType = _PathProfileType
    path_profile_stub.create_u_shape = _create_u_shape
    path_profile_stub.create_u_shape_path_color = _create_u_shape_path_color
    path_profile_stub.PROFILE_TYPE_FUNCTIONS = {_PathProfileType.U_SHAPE: _create_u_shape}
    sys.modules["cad.path_profile_type_shapes"] = path_profile_stub
else:
    path_profile_stub = sys.modules["cad.path_profile_type_shapes"]

if "config" not in sys.modules:
    config_stub = SimpleNamespace()
    config_stub.Config = SimpleNamespace(
        Puzzle=SimpleNamespace(NODE_SIZE=10, SEED=0),
        Path=SimpleNamespace(
            PATH_PROFILE_TYPE_PARAMETERS={},
            PATH_PROFILE_TYPE_OVERRIDES={},
        ),
        Manufacturing=SimpleNamespace(NOZZLE_DIAMETER=0.4),
    )
    config_stub.Puzzle = config_stub.Config.Puzzle
    config_stub.Path = config_stub.Config.Path
    config_stub.Manufacturing = config_stub.Config.Manufacturing
    config_stub.PathCurveModel = PathCurveModel
    config_stub.PathCurveType = PathCurveType
    config_stub.PathProfileType = path_profile_stub.PathProfileType
    sys.modules["config"] = config_stub

from puzzle.node import Node

if "puzzle.puzzle" not in sys.modules:
    puzzle_stub = ModuleType("puzzle.puzzle")

    class _StubPuzzle:
        def __init__(self) -> None:
            self.path_architect = None
            self.total_path = []

    puzzle_stub.Node = Node
    puzzle_stub.Puzzle = _StubPuzzle
    sys.modules["puzzle.puzzle"] = puzzle_stub

if "cad.path_architect" not in sys.modules:
    path_architect_module = ModuleType("cad.path_architect")

    class _StubPathArchitect:
        def __init__(self) -> None:
            self.segments: list = []

    path_architect_module.PathArchitect = _StubPathArchitect
    sys.modules["cad.path_architect"] = path_architect_module

from cad.path_builder import PathBuilder
from cad.path_segment import PathSegment


@pytest.fixture()
def stubbed_path_builder(monkeypatch) -> PathBuilder:
    """Create a PathBuilder instance with geometry helpers stubbed out."""

    builder = PathBuilder.__new__(PathBuilder)

    # Avoid invoking build123d geometry creation during the test.
    monkeypatch.setattr(
        PathBuilder, "_collect_edges", lambda self, seg_list: [f"edge-{s.secondary_index}" for s in seg_list]
    )

    class _DummyWire:
        def __init__(self, edges: list[str]):
            self.edges = edges

    monkeypatch.setattr("cad.path_builder.Wire", _DummyWire)

    return builder


def _make_compound_segment(main_index: int, secondary_index: int, start: float, end: float) -> PathSegment:
    """Create a compound PathSegment spanning the given x coordinates."""

    nodes = [Node(start, 0.0, 0.0), Node(end, 0.0, 0.0)]
    segment = PathSegment(nodes, main_index=main_index, secondary_index=secondary_index)
    segment.curve_model = PathCurveModel.COMPOUND
    return segment


def test_combine_compound_segments_includes_all_nodes(stubbed_path_builder: PathBuilder) -> None:
    """Regression test: every sub-segment contributes its nodes to the combined segment."""

    segments = [
        _make_compound_segment(0, 0, 0.0, 1.0),
        _make_compound_segment(0, 1, 1.0, 2.0),
        _make_compound_segment(0, 2, 2.0, 3.0),
    ]

    combined_segments = stubbed_path_builder._combine_compound_segments_for_path(segments)

    assert len(combined_segments) == 1
    combined_nodes = combined_segments[0].nodes
    assert [node.x for node in combined_nodes] == [0.0, 1.0, 2.0, 3.0]
