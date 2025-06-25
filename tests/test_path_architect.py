from cad.path_architect import PathArchitect
from cad.path_segment import PathSegment
from config import PathCurveModel, PathCurveType
from puzzle.node import Node, NodeGridType


# Helper methods
def make_node(x: float, type: NodeGridType = None) -> Node:
    """
    Build a Node with only the attributes that `PathArchitect.adjust_segments`
    actually inspects (x, y, z, grid_type).  Everything else can keep the
    library defaults.
    """
    node = Node(x, 0, 0)  # y = z = 0 keeps things simple
    if type == NodeGridType.CIRCULAR:
        node.grid_type.append(NodeGridType.CIRCULAR.value)
    elif type == NodeGridType.RECTANGULAR:
        node.grid_type.append(NodeGridType.RECTANGULAR.value)
    return node


def run_adjust_segments(nodes):
    """
    Feed a SINGLE PathSegment to a placeholder `PathArchitect` and return
    the segments that come back after calling `adjust_segments()`.
    """
    seg = PathSegment(nodes, main_index=1)
    seg.curve_model = PathCurveModel.SINGLE
    arch = PathArchitect([])  # Intialize PathArchitect with empty puzzle
    arch.segments = [seg]
    arch.adjust_segments()
    return arch.segments


# Tests
def test_first_two_nodes_circular():
    """
    Verify 2 segments are returned
    0. ARC      (nodes 0-1)   circular
    1. STRAIGHT (node 1-2)    non-circular
    """
    nodes = [
        make_node(0, NodeGridType.CIRCULAR),
        make_node(1, NodeGridType.CIRCULAR),
        make_node(2),
    ]
    segments = run_adjust_segments(nodes)

    # adjust_segments should have split the original into *exactly* two pieces
    assert len(segments) == 2

    # first sgement: circular, so ARC
    assert segments[0].curve_model == PathCurveModel.COMPOUND
    assert segments[0].curve_type == PathCurveType.ARC
    assert len(segments[0].nodes) == 2
    # second segment: straight
    assert segments[1].curve_model == PathCurveModel.COMPOUND
    assert segments[1].curve_type == PathCurveType.STRAIGHT
    assert len(segments[1].nodes) == 2


def test_last_two_nodes_circular():
    """
    Verify 2 segments are returned
    0. STRAIGHT (nodes 0-1)   non-circular
    1. ARC      (nodes 1-2)   circular
    """
    nodes = [
        make_node(0),
        make_node(1, NodeGridType.CIRCULAR),
        make_node(2, NodeGridType.CIRCULAR),
    ]
    segments = run_adjust_segments(nodes)

    assert len(segments) == 2

    # first segment: straight
    assert segments[0].curve_model == PathCurveModel.COMPOUND
    assert segments[0].curve_type == PathCurveType.STRAIGHT
    assert len(segments[0].nodes) == 2
    # second segment: circular, so ARC
    assert segments[1].curve_model == PathCurveModel.COMPOUND
    assert segments[1].curve_type == PathCurveType.ARC
    assert len(segments[1].nodes) == 2
