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


def run_harmonise(nodes_a, nodes_b):
    """
    Build two temporary SINGLE-model segments, inject them into a
    dummy `PathArchitect`, run `_harmonise_circular_transitions`, and
    return the resulting segment list.
    """
    seg_a = PathSegment(nodes_a, main_index=1)
    seg_b = PathSegment(nodes_b, main_index=2)
    seg_a.curve_model = seg_b.curve_model = PathCurveModel.SINGLE  # pass-through

    arch = PathArchitect([])  # empty puzzle
    arch.segments = [seg_a, seg_b]
    arch._harmonise_circular_transitions()
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


TOL = 1e-7


#  Pattern A :  straight -> arc
def test_bridge_insert_pattern_a():
    segs = run_harmonise(
        # seg-A : non-circ(0)  →  circ(1)
        [make_node(0), make_node(1, type=NodeGridType.CIRCULAR)],
        # seg-B : circ(1)  →  circ(2)
        [
            make_node(1, type=NodeGridType.CIRCULAR),
            make_node(2, type=NodeGridType.CIRCULAR),
        ],
    )

    # three segments expected
    assert len(segs) == 3
    seg_a, new_seg, seg_b = segs

    # shared bridge locations
    assert seg_a.nodes[-1] is new_seg.nodes[0]
    assert new_seg.nodes[-1] is seg_b.nodes[0]
    assert abs(new_seg.nodes[0].x - 0.5) < TOL
    assert NodeGridType.CIRCULAR.value not in seg_a.nodes[-1].grid_type

    # seg-A shortened (last but one is original non-circ 0)
    assert abs(seg_a.nodes[-2].x - 0) < TOL

    # new_seg holds [bridge , old start_B (circ x=1)]
    assert len(new_seg.nodes) == 2
    assert abs(new_seg.nodes[1].x - 1) < TOL
    assert NodeGridType.CIRCULAR.value in new_seg.nodes[1].grid_type
    assert new_seg.main_index == seg_b.main_index  # attaches to group B
    assert new_seg.secondary_index == seg_b.secondary_index - 1
    assert new_seg.curve_model == PathCurveModel.COMPOUND
    assert new_seg.curve_type is None

    # ── seg-B now starts at bridge, second node is x=2
    assert abs(seg_b.nodes[1].x - 2) < TOL


#  Pattern B :  arc -> straight
def test_bridge_insert_pattern_b():
    segs = run_harmonise(
        # seg-A : circ(0) → circ(1)
        [
            make_node(0, type=NodeGridType.CIRCULAR),
            make_node(1, type=NodeGridType.CIRCULAR),
        ],
        # seg-B : circ(1) → non-circ(2)
        [make_node(1, type=NodeGridType.CIRCULAR), make_node(2)],
    )

    # three segments expected
    assert len(segs) == 3
    seg_a, new_seg, seg_b = segs

    # shared bridge
    assert seg_a.nodes[-1] is new_seg.nodes[0]
    assert new_seg.nodes[-1] is seg_b.nodes[0]
    assert abs(new_seg.nodes[-1].x - 1.5) < TOL
    assert NodeGridType.CIRCULAR.value not in seg_b.nodes[0].grid_type

    # new_seg holds [old end_A (circ x=1) , bridge]
    assert len(new_seg.nodes) == 2
    assert abs(new_seg.nodes[0].x - 1) < TOL
    assert NodeGridType.CIRCULAR.value in new_seg.nodes[0].grid_type
    assert new_seg.main_index == seg_a.main_index  # attaches to group A
    assert new_seg.secondary_index == seg_a.secondary_index + 1
    assert new_seg.curve_model == PathCurveModel.COMPOUND
    assert new_seg.curve_type is None

    # seg-B continues straight, node at x=2 remains
    assert abs(seg_b.nodes[1].x - 2) < TOL
