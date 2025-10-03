import math
import sys
from enum import Enum
from types import ModuleType


if "build123d" not in sys.modules:
    stub = ModuleType("build123d")

    class _StubVector:
        def __init__(self, x=0.0, y=0.0, z=0.0):
            self.X = float(x)
            self.Y = float(y)
            self.Z = float(z)

        def __add__(self, other):
            return _StubVector(self.X + other.X, self.Y + other.Y, self.Z + other.Z)

        def __sub__(self, other):
            return _StubVector(self.X - other.X, self.Y - other.Y, self.Z - other.Z)

        def __mul__(self, scalar):
            return _StubVector(self.X * scalar, self.Y * scalar, self.Z * scalar)

        __rmul__ = __mul__

        @property
        def length(self):
            return math.sqrt(self.X**2 + self.Y**2 + self.Z**2)

        def normalized(self):
            length = self.length
            if length == 0:
                return _StubVector(0.0, 0.0, 0.0)
            return _StubVector(self.X / length, self.Y / length, self.Z / length)

        def dot(self, other):
            return self.X * other.X + self.Y * other.Y + self.Z * other.Z

        @property
        def x(self):
            return self.X

        @property
        def y(self):
            return self.Y

        @property
        def z(self):
            return self.Z

    class _StubTransition:
        ROUND = "round"
        RIGHT = "right"

    class _StubGeometry:
        pass

    stub.Vector = _StubVector
    stub.Transition = _StubTransition
    stub.Edge = _StubGeometry
    stub.Part = _StubGeometry
    stub.Sketch = _StubGeometry
    stub.Wire = _StubGeometry

    sys.modules["build123d"] = stub


if "ocp_vscode" not in sys.modules:
    ocp_stub = ModuleType("ocp_vscode")

    class _StubCamera:
        KEEP = "keep"

    def _noop(*args, **kwargs):
        return None

    def _status():
        return {"states": {}}

    ocp_stub.Camera = _StubCamera
    ocp_stub.set_defaults = _noop
    ocp_stub.set_viewer_config = _noop
    ocp_stub.show = _noop
    ocp_stub.status = _status

    sys.modules["ocp_vscode"] = ocp_stub


if "cad.path_profile_type_shapes" not in sys.modules:
    path_stub = ModuleType("cad.path_profile_type_shapes")

    class PathProfileType(Enum):
        L_SHAPE_MIRRORED = "l_shape_mirrored"
        L_SHAPE_MIRRORED_PATH_COLOR = "l_shape_mirrored_path_color"
        L_SHAPE_ADJUSTED_HEIGHT = "l_shape_adjusted_height"
        L_SHAPE_ADJUSTED_HEIGHT_PATH_COLOR = "l_shape_adjusted_height_path_color"
        O_SHAPE = "o_shape"
        O_SHAPE_SUPPORT = "o_shape_support"
        U_SHAPE = "u_shape"
        U_SHAPE_PATH_COLOR = "u_shape_path_color"
        U_SHAPE_ADJUSTED_HEIGHT = "u_shape_adjusted_height"
        U_SHAPE_ADJUSTED_HEIGHT_PATH_COLOR = "u_shape_adjusted_height_path_color"
        V_SHAPE = "v_shape"
        V_SHAPE_PATH_COLOR = "v_shape_path_color"
        RECTANGLE_SHAPE = "rectangle_shape"

    path_stub.PathProfileType = PathProfileType
    path_stub.ACCENT_REGISTRY = {}
    path_stub.SUPPORT_REGISTRY = {}

    sys.modules["cad.path_profile_type_shapes"] = path_stub


from cad.path_architect import PathArchitect
from cad.path_segment import PathSegment, _node_to_vector
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


def make_xyz_node(x: float, y: float = 0.0, z: float = 0.0) -> Node:
    """Shortcut for building nodes at arbitrary coordinates."""
    return Node(x, y, z)


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
    segment.curve_model = PathCurveModel.SPLINE

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


def test_detect_curves_vertical_step_creates_compound_segment():
    """Vertical steps inside an arc should become standalone compound segments."""

    arc_nodes = [
        Node(1.0, 0.0, 0.0),
        Node(0.0, 1.0, 0.0),
        Node(0.0, 1.0, 1.0),  # vertical lift (same X/Y as previous node)
        Node(-1.0, 0.0, 1.0),
    ]
    for node in arc_nodes:
        node.grid_type.append(NodeGridType.CIRCULAR.value)

    segment = PathSegment(arc_nodes, main_index=3)
    segment.curve_model = PathCurveModel.COMPOUND

    arch = PathArchitect.__new__(PathArchitect)
    arch.segments = [segment]
    arch.secondary_index_counters = {}

    arch.detect_curves_and_adjust_segments()

    assert len(arch.segments) == 3

    leading_arc, vertical_span, trailing_arc = arch.segments

    assert leading_arc.curve_type == PathCurveType.ARC
    assert trailing_arc.curve_type == PathCurveType.ARC

    assert vertical_span.curve_model == PathCurveModel.COMPOUND
    assert vertical_span.curve_type is None

    # Shared nodes maintained to preserve continuity
    assert leading_arc.nodes[-1] is vertical_span.nodes[0]
    assert vertical_span.nodes[-1] is trailing_arc.nodes[0]

    # Vertical span keeps identical X/Y but different Z coordinates
    start_vec = _node_to_vector(vertical_span.nodes[0])
    end_vec = _node_to_vector(vertical_span.nodes[-1])
    assert abs(start_vec.X - end_vec.X) < TOL
    assert abs(start_vec.Y - end_vec.Y) < TOL
    assert abs(start_vec.Z - end_vec.Z) > TOL


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

    assert first.curve_model == PathCurveModel.SINGLE
    assert first.nodes[0] is nodes[0]

    assert body.curve_model == PathCurveModel.SPLINE
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

    assert lead.curve_model == PathCurveModel.SINGLE
    assert lead.nodes[0] is nodes[0]

    assert body.curve_model == PathCurveModel.SPLINE
    assert body.nodes == nodes[1:-1]

    assert tail.curve_model == PathCurveModel.SINGLE
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

    assert body.curve_model == PathCurveModel.SPLINE
    assert body.nodes == nodes[:-1]

    assert tail.curve_model == PathCurveModel.SINGLE
    assert tail.nodes[0] is nodes[-1]

    assert arch.secondary_index_counters[7] == 2
