from config import PathProfileType
from cad.path_segment import PathSegment
from puzzle.gravity_validation import detect_gravity_warning_issues
from puzzle.node import Node


def make_segment(
    profile_type: PathProfileType,
    coordinates: list[tuple[float, float, float]],
):
    nodes = [
        Node(x_coordinate, y_coordinate, z_coordinate)
        for x_coordinate, y_coordinate, z_coordinate in coordinates
    ]
    segment = PathSegment(nodes, main_index=3)
    segment.path_profile_type = profile_type
    return segment


def test_detects_consecutive_downward_moves_for_open_profiles():
    segment = make_segment(
        PathProfileType.U_SHAPE_ADJUSTED_HEIGHT,
        [(0.0, 0.0, 20.0), (0.0, 0.0, 10.0), (0.0, 0.0, 0.0)],
    )

    issues = detect_gravity_warning_issues([segment], node_size=10.0)

    assert len(issues) == 1
    assert issues[0].movement_pattern == "down-down"
    assert issues[0].node.z == 0.0


def test_detects_local_low_point_for_open_profiles():
    segment = make_segment(
        PathProfileType.L_SHAPE,
        [(0.0, 0.0, 10.0), (0.0, 0.0, 0.0), (0.0, 0.0, 10.0)],
    )

    issues = detect_gravity_warning_issues([segment], node_size=10.0)

    assert len(issues) == 1
    assert issues[0].movement_pattern == "down-up"
    assert issues[0].node.z == 0.0


def test_closed_o_shape_does_not_warn_for_consecutive_downward_moves():
    segment = make_segment(
        PathProfileType.O_SHAPE,
        [(0.0, 0.0, 20.0), (0.0, 0.0, 10.0), (0.0, 0.0, 0.0)],
    )

    issues = detect_gravity_warning_issues([segment], node_size=10.0)

    assert issues == []
