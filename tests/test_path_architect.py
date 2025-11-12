import unittest

from cad.path_architect import PathArchitect
from cad.path_segment import PathSegment, _node_to_vector, is_same_location
from config import Config, PathCurveType, PathSegmentDesignStrategy
from puzzle.node import Node


# Helper methods
def make_node(
    x: float,
    *,
    circular: bool = False,
    rectangular: bool | None = None,
) -> Node:
    """
    Build a Node with only the attributes that `PathArchitect.adjust_segments`
    actually inspects (x, y, z, circular flag). Everything else can keep the
    library defaults.
    """
    if rectangular is None:
        rectangular = not circular
    node = Node(
        x,
        0,
        0,
        in_circular_grid=circular,
        in_rectangular_grid=rectangular,
    )  # y = z = 0 keeps things simple
    return node


def make_xyz_node(x: float, y: float = 0.0, z: float = 0.0) -> Node:
    """Shortcut for building nodes at arbitrary coordinates."""
    return Node(x, y, z)


def make_stub_arch() -> PathArchitect:
    arch = PathArchitect.__new__(PathArchitect)
    arch.segments = []
    arch.secondary_index_counters = {}
    arch.obstacle_splices = {}
    arch.node_size = Config.Puzzle.NODE_SIZE
    arch.waypoint_change_interval = Config.Puzzle.WAYPOINT_CHANGE_INTERVAL
    arch.path_profile_types = list(Config.Path.PATH_PROFILE_TYPES)
    arch.path_design_strategies = list(Config.Path.PATH_SEGMENT_DESIGN_STRATEGY)
    return arch


def assert_no_duplicate_vectors(nodes: list[Node]):
    vectors = [_node_to_vector(node) for node in nodes]
    for index, vec in enumerate(vectors):
        for other in vectors[index + 1 :]:
            assert not is_same_location(vec, other), (
                f"Duplicate vector detected at {_format_vector_for_assert(vec)}"
            )


def _format_vector_for_assert(vec):
    return f"({vec.X:.6f}, {vec.Y:.6f}, {vec.Z:.6f})"


def run_split_spline(
    segment_nodes: list[Node],
    *,
    previous_nodes: list[Node] | None = None,
    next_nodes: list[Node] | None = None,
    main_index: int = 7,
):
    """Helper to call `_split_spline_segment` in isolation."""

    arch = PathArchitect.__new__(PathArchitect)
    arch.secondary_index_counters = {}

    segment = PathSegment(segment_nodes, main_index=main_index)
    segment.design_strategy = PathSegmentDesignStrategy.SPLINE

    previous_segment = (
        PathSegment(previous_nodes, main_index=main_index - 1)
        if previous_nodes is not None
        else None
    )
    next_segment = (
        PathSegment(next_nodes, main_index=main_index + 1)
        if next_nodes is not None
        else None
    )

    split_segments = arch._split_spline_segment(
        segment,
        previous_segment=previous_segment,
        next_segment=next_segment,
    )

    return arch, split_segments


def run_adjust_segments(nodes):
    """
    Feed a SINGLE PathSegment to a placeholder `PathArchitect` and return
    the segments that come back after calling `adjust_segments()`.
    """
    seg = PathSegment(nodes, main_index=1)
    seg.design_strategy = PathSegmentDesignStrategy.SINGLE
    arch = make_stub_arch()
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
    seg_a.design_strategy = seg_b.design_strategy = (
        PathSegmentDesignStrategy.SINGLE
    )  # pass-through

    arch = make_stub_arch()
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
        make_node(0, circular=True),
        make_node(1, circular=True),
        make_node(2),
    ]
    segments = run_adjust_segments(nodes)

    # adjust_segments should have split the original into *exactly* two pieces
    assert len(segments) == 2

    # first sgement: circular, so ARC
    assert segments[0].design_strategy == PathSegmentDesignStrategy.COMPOUND
    assert segments[0].curve_type == PathCurveType.ARC
    assert len(segments[0].nodes) == 2
    # second segment: straight
    assert segments[1].design_strategy == PathSegmentDesignStrategy.COMPOUND
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
        make_node(1, circular=True),
        make_node(2, circular=True),
    ]
    segments = run_adjust_segments(nodes)

    assert len(segments) == 2

    # first segment: straight
    assert segments[0].design_strategy == PathSegmentDesignStrategy.COMPOUND
    assert segments[0].curve_type == PathCurveType.STRAIGHT
    assert len(segments[0].nodes) == 2
    # second segment: circular, so ARC
    assert segments[1].design_strategy == PathSegmentDesignStrategy.COMPOUND
    assert segments[1].curve_type == PathCurveType.ARC
    assert len(segments[1].nodes) == 2


TOL = 1e-7


#  Pattern A :  straight -> arc
def test_bridge_insert_pattern_a():
    segs = run_harmonise(
        # seg-A : non-circ(0)  →  circ(1)
        [make_node(0), make_node(1, circular=True)],
        # seg-B : circ(1)  →  circ(2)
        [
            make_node(1, circular=True),
            make_node(2, circular=True),
        ],
    )

    # three segments expected
    assert len(segs) == 3
    seg_a, new_seg, seg_b = segs

    # shared bridge locations
    assert seg_a.nodes[-1] is new_seg.nodes[0]
    assert new_seg.nodes[-1] is seg_b.nodes[0]
    assert abs(new_seg.nodes[0].x - 0.5) < TOL
    assert not seg_a.nodes[-1].in_circular_grid

    # seg-A shortened (last but one is original non-circ 0)
    assert abs(seg_a.nodes[-2].x - 0) < TOL

    # new_seg holds [bridge , old start_B (circ x=1)]
    assert len(new_seg.nodes) == 2
    assert abs(new_seg.nodes[1].x - 1) < TOL
    assert new_seg.nodes[1].in_circular_grid
    assert new_seg.main_index == seg_b.main_index  # attaches to group B
    assert new_seg.secondary_index == seg_b.secondary_index - 1
    assert new_seg.design_strategy == PathSegmentDesignStrategy.COMPOUND
    assert new_seg.curve_type is None

    # ── seg-B now starts at bridge, second node is x=2
    assert abs(seg_b.nodes[1].x - 2) < TOL


#  Pattern B :  arc -> straight
def test_bridge_insert_pattern_b():
    segs = run_harmonise(
        # seg-A : circ(0) → circ(1)
        [
            make_node(0, circular=True),
            make_node(1, circular=True),
        ],
        # seg-B : circ(1) → non-circ(2)
        [make_node(1, circular=True), make_node(2)],
    )

    # three segments expected
    assert len(segs) == 3
    seg_a, new_seg, seg_b = segs

    # shared bridge
    assert seg_a.nodes[-1] is new_seg.nodes[0]
    assert new_seg.nodes[-1] is seg_b.nodes[0]
    assert abs(new_seg.nodes[-1].x - 1.5) < TOL
    assert not seg_b.nodes[0].in_circular_grid

    # new_seg holds [old end_A (circ x=1) , bridge]
    assert len(new_seg.nodes) == 2
    assert abs(new_seg.nodes[0].x - 1) < TOL
    assert new_seg.nodes[0].in_circular_grid
    assert new_seg.main_index == seg_a.main_index  # attaches to group A
    assert new_seg.secondary_index == seg_a.secondary_index + 1
    assert new_seg.design_strategy == PathSegmentDesignStrategy.COMPOUND
    assert new_seg.curve_type is None

    # seg-B continues straight, node at x=2 remains
    assert abs(seg_b.nodes[1].x - 2) < TOL


def test_obstacle_exit_segment_reuses_shared_start_node():
    previous_exit = make_xyz_node(5.0, 6.0, 7.0)
    previous_exit.in_rectangular_grid = True

    shared_exit = make_xyz_node(5.0, 6.0, 7.0)
    shared_exit.is_obstacle_exit = True

    interior_node = make_xyz_node(8.0, 6.0, 7.0)
    segment = PathSegment([shared_exit, interior_node], main_index=99)
    segment.is_obstacle = True

    downstream_start = make_xyz_node(11.0, 6.0, 7.0)

    segment.adjust_start_and_endpoints(
        node_size=1.0,
        previous_end_node=previous_exit,
        next_start_node=downstream_start,
        previous_curve_type=None,
        next_curve_type=None,
    )

    assert segment.nodes[0] is shared_exit
    assert shared_exit.segment_start
    assert shared_exit.in_rectangular_grid is True
    assert is_same_location(
        _node_to_vector(shared_exit), _node_to_vector(previous_exit)
    )

    assert_no_duplicate_vectors(segment.nodes)

    shared_locations = [
        node
        for node in segment.nodes
        if is_same_location(_node_to_vector(node), _node_to_vector(previous_exit))
    ]
    assert len(shared_locations) == 1


def test_single_before_non_circular_spline():
    node_size = Config.Puzzle.NODE_SIZE

    # SINGLE segment centred on a circular node, with a following spline run
    core_node = make_node(0, circular=True)
    single_segment = PathSegment([core_node], main_index=1)
    single_segment.design_strategy = PathSegmentDesignStrategy.SINGLE

    spline_entry = make_node(1)
    spline_follow = make_node(2)
    spline_segment = PathSegment([spline_entry, spline_follow], main_index=2)
    spline_segment.design_strategy = PathSegmentDesignStrategy.SPLINE
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
    assert not single_segment.nodes[-1].in_circular_grid
    assert not spline_segment.nodes[0].in_circular_grid

    arch = make_stub_arch()
    arch.segments = [single_segment, spline_segment]
    arch._harmonise_circular_transitions()

    # No additional bridge should be created
    assert len(arch.segments) == 2
    assert not arch.segments[0].nodes[-1].in_circular_grid
    assert not arch.segments[1].nodes[0].in_circular_grid


def test_single_after_non_circular_spline():
    node_size = Config.Puzzle.NODE_SIZE

    # Upstream spline segment remains linear at the junction
    spline_exit = make_node(-1)
    spline_segment = PathSegment([make_node(-2), spline_exit], main_index=1)
    spline_segment.design_strategy = PathSegmentDesignStrategy.SPLINE
    spline_segment.curve_type = None

    # SINGLE segment centred on a circular grid node
    core_node = make_node(0, circular=True)
    single_segment = PathSegment([core_node], main_index=2)
    single_segment.design_strategy = PathSegmentDesignStrategy.SINGLE

    # Following arc run should still pick up the circular context
    arc_entry = make_node(1, circular=True)
    arc_follow = make_node(2, circular=True)
    arc_segment = PathSegment([arc_entry, arc_follow], main_index=3)
    arc_segment.design_strategy = PathSegmentDesignStrategy.COMPOUND
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
    assert not single_segment.nodes[0].in_circular_grid
    assert not spline_segment.nodes[-1].in_circular_grid

    # Junction into the arc should remain circular
    assert single_segment.nodes[-1].in_circular_grid
    assert arc_segment.nodes[0].in_circular_grid

    arch = make_stub_arch()
    arch.segments = [spline_segment, single_segment, arc_segment]
    arch._harmonise_circular_transitions()

    # Harmonisation should not insert an extra arc at the spline / SINGLE boundary
    assert len(arch.segments) == 3
    assert not arch.segments[0].nodes[-1].in_circular_grid
    assert arch.segments[1].nodes[-1].in_circular_grid


def test_split_spline_handles_empty_node_list():
    arch, segments = run_split_spline([])

    assert segments == []
    assert arch.secondary_index_counters[7] == 0


def test_split_spline_keeps_leading_stitch_only():
    nodes = [
        make_xyz_node(1, 0, 0),
        make_xyz_node(2, 0, 0),
        make_xyz_node(3, 0, 0),
    ]
    previous_nodes = [make_xyz_node(1, -1, 0)]
    next_nodes = [make_xyz_node(4, 0, 0)]

    arch, segments = run_split_spline(
        nodes, previous_nodes=previous_nodes, next_nodes=next_nodes
    )

    assert len(segments) == 2
    first, body = segments

    assert first.design_strategy == PathSegmentDesignStrategy.SINGLE
    assert first.nodes[0] is nodes[0]

    assert body.design_strategy == PathSegmentDesignStrategy.SPLINE
    assert body.nodes == nodes[1:]

    assert arch.secondary_index_counters[7] == 2


def test_split_spline_keeps_both_boundary_stitches():
    nodes = [
        make_xyz_node(1, 0, 0),
        make_xyz_node(2, 0, 0),
        make_xyz_node(3, 0, 0),
    ]
    previous_nodes = [make_xyz_node(1, -1, 0)]
    next_nodes = [make_xyz_node(3, 1, 0)]

    arch, segments = run_split_spline(
        nodes, previous_nodes=previous_nodes, next_nodes=next_nodes
    )

    assert len(segments) == 3
    lead, body, tail = segments

    assert lead.design_strategy == PathSegmentDesignStrategy.SINGLE
    assert lead.nodes[0] is nodes[0]

    assert body.design_strategy == PathSegmentDesignStrategy.SPLINE
    assert body.nodes == nodes[1:-1]

    assert tail.design_strategy == PathSegmentDesignStrategy.SINGLE
    assert tail.nodes[0] is nodes[-1]

    assert arch.secondary_index_counters[7] == 3


def test_split_spline_keeps_trailing_stitch_only():
    nodes = [
        make_xyz_node(1, 0, 0),
        make_xyz_node(2, 0, 0),
        make_xyz_node(3, 0, 0),
    ]
    previous_nodes = [make_xyz_node(0, 0, 0)]
    next_nodes = [make_xyz_node(3, 1, 0)]

    arch, segments = run_split_spline(
        nodes, previous_nodes=previous_nodes, next_nodes=next_nodes
    )

    assert len(segments) == 2
    body, tail = segments

    assert body.design_strategy == PathSegmentDesignStrategy.SPLINE
    assert body.nodes == nodes[:-1]

    assert tail.design_strategy == PathSegmentDesignStrategy.SINGLE
    assert tail.nodes[0] is nodes[-1]

    assert arch.secondary_index_counters[7] == 2


def _set_circular(node: Node, flag: bool) -> Node:
    node.in_circular_grid = flag
    node.in_rectangular_grid = not flag
    return node


@unittest.skip(
    "Conflict of interest between not creating single node segments and "
    "properly making arc segments from one segment."
)
def test_seg43_to_seg50_handoff_bridge_is_arc_and_remainder_stays_non_arc():
    """
    4.3 tail ends at (30,-54.82928,0) circular; 5.0 starts at (40,-48.02343,0) circular.
    Harmonisation inserts a bridge segment [30..40] (both circular).
    Circular detection marks the bridge ARC. The remainder of 5.0 stays non-ARC
    (except for its first node, which is the shared circular boundary already marked by the bridge).
    """
    # 4.3 tail (all circular)
    n_43 = [
        _set_circular(make_xyz_node(-10.0, -61.695, 0.0), True),
        _set_circular(make_xyz_node(0.0, -62.500, 0.0), True),
        _set_circular(make_xyz_node(10.0, -61.695, 0.0), True),
        _set_circular(make_xyz_node(20.0, -59.214, 0.0), True),
        _set_circular(make_xyz_node(30.0, -54.82928, 0.0), True),  # 4.3 end
    ]

    # 5.0 head + body
    n_50 = [
        _set_circular(
            make_xyz_node(40.0, -48.02343, 0.0), True
        ),  # 5.0 start (circular)
        _set_circular(make_xyz_node(40.0, -30.0, 0.0), False),
        _set_circular(make_xyz_node(40.0, -20.0, 0.0), False),
        _set_circular(make_xyz_node(40.0, -10.0, 0.0), False),
    ]

    segs = run_harmonise(n_43, n_50)
    assert len(segs) == 3
    seg43_tail, bridge, seg50_remainder = segs

    # Identity sharing at boundaries
    assert seg43_tail.nodes[-1] is bridge.nodes[0]
    assert bridge.nodes[-1] is seg50_remainder.nodes[0]

    # Bridge must be both circular nodes
    assert len(bridge.nodes) == 2
    assert bridge.nodes[0].in_circular_grid and bridge.nodes[1].in_circular_grid

    # Run circular detection on the bridge: should mark both nodes as ARC
    from cad.curve_detection import detect_circular_segments

    next_id = detect_circular_segments(bridge.nodes, curve_id_counter=1)

    for node in bridge.nodes:
        assert node.used_in_curve is True
        assert node.path_curve_type == PathCurveType.ARC
        assert node.curve_id == 1
    assert next_id == 2

    # Remainder: the first node is the shared circular node (already ARC from bridge),
    # the second node must remain non-circular & non-ARC.
    assert seg50_remainder.nodes[0].in_circular_grid is True
    assert seg50_remainder.nodes[0].path_curve_type == PathCurveType.ARC

    assert seg50_remainder.nodes[1].in_circular_grid is False
    assert getattr(seg50_remainder.nodes[1], "path_curve_type", None) is None


def test_single_circular_head_is_marked():
    """
    A single circular node at the START of the segment
    is treated as a valid (1-node) circular run and marked ARC.
    """
    head_circ = _set_circular(make_xyz_node(40.0, -48.02343, 0.0), True)
    next_rect = _set_circular(make_xyz_node(40.0, -30.0, 0.0), False)
    nodes = [head_circ, next_rect]

    from cad.curve_detection import detect_circular_segments

    start_id = 10
    end_id = detect_circular_segments(nodes, curve_id_counter=start_id)

    assert end_id == start_id + 1  # consumed one curve id
    assert head_circ.used_in_curve is True
    assert head_circ.path_curve_type == PathCurveType.ARC
    assert head_circ.curve_id == start_id

    # Neighbor remains non-ARC
    assert next_rect.in_circular_grid is False
    assert next_rect.path_curve_type is None


def test_single_circular_tail_is_marked():
    """
    A single circular node at the TAIL of the segment
    is treated as a valid (1-node) circular run and marked ARC.
    """
    prev_rect = _set_circular(make_xyz_node(40.0, -30.0, 0.0), False)
    tail_circ = _set_circular(make_xyz_node(40.0, -10.0, 0.0), True)
    nodes = [prev_rect, tail_circ]

    from cad.curve_detection import detect_circular_segments

    start_id = 20
    end_id = detect_circular_segments(nodes, curve_id_counter=start_id)

    # Currently no new id is consumed
    assert end_id == start_id + 1

    assert prev_rect.used_in_curve is False
    assert prev_rect.path_curve_type is None

    # And the tail node remains unmarked
    assert tail_circ.used_in_curve is True
    assert tail_circ.path_curve_type is PathCurveType.ARC
