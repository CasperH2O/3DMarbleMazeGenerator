from cad.path_architect import PathArchitect
from cad.path_segment import PathSegment
from config import Config, PathCurveModel, PathCurveType
from puzzle.node import Node, NodeGridType


# Helper methods
def make_node(x: float, grid_type: NodeGridType = None) -> Node:
    """
    Build a Node with only the attributes that `PathArchitect.adjust_segments`
    actually inspects (x, y, z, grid_type).  Everything else can keep the
    library defaults.
    """
    node = Node(x, 0, 0)  # y = z = 0 keeps things simple
    if grid_type == NodeGridType.CIRCULAR:
        node.grid_type.append(NodeGridType.CIRCULAR.value)
    elif grid_type == NodeGridType.RECTANGULAR:
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
        [make_node(0), make_node(1, grid_type=NodeGridType.CIRCULAR)],
        # seg-B : circ(1)  →  circ(2)
        [
            make_node(1, grid_type=NodeGridType.CIRCULAR),
            make_node(2, grid_type=NodeGridType.CIRCULAR),
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
            make_node(0, grid_type=NodeGridType.CIRCULAR),
            make_node(1, grid_type=NodeGridType.CIRCULAR),
        ],
        # seg-B : circ(1) → non-circ(2)
        [make_node(1, grid_type=NodeGridType.CIRCULAR), make_node(2)],
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


def test_single_before_non_circular_spline():
    node_size = Config.Puzzle.NODE_SIZE

    # SINGLE segment centred on a circular node, with a following spline run
    core_node = make_node(0, NodeGridType.CIRCULAR)
    single_segment = PathSegment([core_node], main_index=1)
    single_segment.curve_model = PathCurveModel.SINGLE

    spline_entry = make_node(1)
    spline_follow = make_node(2)
    spline_segment = PathSegment([spline_entry, spline_follow], main_index=2)
    spline_segment.curve_model = PathCurveModel.SPLINE
    spline_segment.curve_type = None  # explicit non-circular run

    single_segment.adjust_start_and_endpoints(
        node_size,
        previous_end_node=None,
        next_start_node=spline_entry,
        previous_curve_type=None,
        next_curve_type=None,
    )

    spline_segment.adjust_start_and_endpoints(
        node_size,
        previous_end_node=single_segment.nodes[-1],
        next_start_node=None,
        previous_curve_type=None,
        next_curve_type=None,
    )

    # Guard should keep the shared boundary nodes linear
    assert NodeGridType.CIRCULAR.value not in single_segment.nodes[-1].grid_type
    assert NodeGridType.CIRCULAR.value not in spline_segment.nodes[0].grid_type

    arch = PathArchitect([])
    arch.segments = [single_segment, spline_segment]
    arch._harmonise_circular_transitions()

    # No additional bridge should be created
    assert len(arch.segments) == 2
    assert NodeGridType.CIRCULAR.value not in arch.segments[0].nodes[-1].grid_type
    assert NodeGridType.CIRCULAR.value not in arch.segments[1].nodes[0].grid_type


def test_single_after_non_circular_spline():
    node_size = Config.Puzzle.NODE_SIZE

    # Upstream spline segment remains linear at the junction
    spline_exit = make_node(-1)
    spline_segment = PathSegment([make_node(-2), spline_exit], main_index=1)
    spline_segment.curve_model = PathCurveModel.SPLINE
    spline_segment.curve_type = None

    # SINGLE segment centred on a circular grid node
    core_node = make_node(0, NodeGridType.CIRCULAR)
    single_segment = PathSegment([core_node], main_index=2)
    single_segment.curve_model = PathCurveModel.SINGLE

    # Following arc run should still pick up the circular context
    arc_entry = make_node(1, NodeGridType.CIRCULAR)
    arc_follow = make_node(2, NodeGridType.CIRCULAR)
    arc_segment = PathSegment([arc_entry, arc_follow], main_index=3)
    arc_segment.curve_model = PathCurveModel.COMPOUND
    arc_segment.curve_type = PathCurveType.ARC

    spline_segment.adjust_start_and_endpoints(
        node_size,
        previous_end_node=None,
        next_start_node=core_node,
        previous_curve_type=None,
        next_curve_type=None,
    )

    single_segment.adjust_start_and_endpoints(
        node_size,
        previous_end_node=spline_segment.nodes[-1],
        next_start_node=arc_entry,
        previous_curve_type=spline_segment.curve_type,
        next_curve_type=arc_segment.curve_type,
    )

    arc_segment.adjust_start_and_endpoints(
        node_size,
        previous_end_node=single_segment.nodes[-1],
        next_start_node=None,
        previous_curve_type=None,
        next_curve_type=None,
    )

    # Junction back to the spline should stay linear
    assert NodeGridType.CIRCULAR.value not in single_segment.nodes[0].grid_type
    assert NodeGridType.CIRCULAR.value not in spline_segment.nodes[-1].grid_type

    # Junction into the arc should remain circular
    assert NodeGridType.CIRCULAR.value in single_segment.nodes[-1].grid_type
    assert NodeGridType.CIRCULAR.value in arc_segment.nodes[0].grid_type

    arch = PathArchitect([])
    arch.segments = [spline_segment, single_segment, arc_segment]
    arch._harmonise_circular_transitions()

    # Harmonisation should not insert an extra arc at the spline / SINGLE boundary
    assert len(arch.segments) == 3
    assert NodeGridType.CIRCULAR.value not in arch.segments[0].nodes[-1].grid_type
    assert NodeGridType.CIRCULAR.value in arch.segments[1].nodes[-1].grid_type
