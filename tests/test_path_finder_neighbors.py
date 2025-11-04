import pytest

from config import CaseShape, Config
from puzzle.path_finder import AStarPathFinder
from puzzle.puzzle import Puzzle
from puzzle.utils.geometry import euclidean_distance, key3


@pytest.fixture(autouse=True)
def disable_random_obstacles():
    original_setting = Config.Obstacles.RANDOM_PLACEMENT_ENABLED
    Config.Obstacles.RANDOM_PLACEMENT_ENABLED = False
    try:
        yield
    finally:
        Config.Obstacles.RANDOM_PLACEMENT_ENABLED = original_setting


def _reference_neighbors(puzzle: Puzzle, node):
    """Faithfully reproduce the pre-refactor neighbor search for comparisons."""
    node_dict = puzzle.node_dict
    node_size = puzzle.node_size
    neighbors: list[tuple] = []
    tolerance = node_size * 0.1

    cardinal_offsets = [
        (node_size, 0, 0),
        (-node_size, 0, 0),
        (0, node_size, 0),
        (0, -node_size, 0),
        (0, 0, node_size),
        (0, 0, -node_size),
    ]
    for dx, dy, dz in cardinal_offsets:
        coord = key3(node.x + dx, node.y + dy, node.z + dz)
        candidate = node_dict.get(coord)
        if candidate:
            neighbors.append((candidate, node_size))

    for candidate in node_dict.values():
        if candidate is node:
            continue

        dx = abs(candidate.x - node.x)
        dy = abs(candidate.y - node.y)
        dz = abs(candidate.z - node.z)
        diff_count = sum(1 for delta in (dx, dy, dz) if delta > tolerance)

        node_is_circular = node.in_circular_grid
        candidate_is_circular = candidate.in_circular_grid

        if diff_count == 1 and (node_is_circular ^ candidate_is_circular):
            if (
                puzzle.case_shape == CaseShape.CYLINDER
                and node_is_circular
                and not candidate_is_circular
                and abs(node.x) > tolerance
                and abs(node.y) > tolerance
            ):
                continue

            distance = euclidean_distance(node, candidate)
            if distance <= 2 * node_size - tolerance:
                neighbors.append((candidate, distance))

    if node.in_circular_grid:
        same_plane_tol = tolerance
        circ_same_plane: list[tuple] = []
        for candidate_node in node_dict.values():
            if candidate_node is node:
                continue
            if not candidate_node.in_circular_grid:
                continue
            if abs(candidate_node.z - node.z) > same_plane_tol:
                continue

            dist = euclidean_distance(node, candidate_node)
            if dist > tolerance:
                circ_same_plane.append((candidate_node, dist))

        circ_same_plane.sort(key=lambda item: item[1])
        for candidate_node, dist in circ_same_plane[:2]:
            neighbors.append((candidate_node, dist))

        plane_tol = tolerance
        target_z_above = node.z + node_size
        target_z_below = node.z - node_size

        def add_best_on_plane(target_z: float) -> None:
            plane_nodes = [
                cn
                for cn in node_dict.values()
                if cn is not node
                and cn.in_circular_grid
                and abs(cn.z - target_z) <= plane_tol
            ]
            if not plane_nodes:
                return
            best = min(plane_nodes, key=lambda cn: euclidean_distance(node, cn))
            neighbors.append((best, euclidean_distance(node, best)))

        add_best_on_plane(target_z_above)
        add_best_on_plane(target_z_below)

    return neighbors


def _neighbors_to_map(neighbors):
    mapping: dict[tuple[float, float, float], list[float]] = {}
    for candidate, cost in neighbors:
        key = key3(candidate.x, candidate.y, candidate.z)
        mapping.setdefault(key, []).append(cost)
    for costs in mapping.values():
        costs.sort()
    return mapping


@pytest.mark.parametrize(
    "case_shape",
    [CaseShape.BOX, CaseShape.SPHERE, CaseShape.CYLINDER, CaseShape.ELLIPSOID],
)
def test_neighbor_lookup_matches_reference(case_shape):
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=case_shape,
    )
    path_finder = AStarPathFinder()

    for node in puzzle.nodes:
        new_neighbors = path_finder.get_neighbors(puzzle, node)
        reference_neighbors = _reference_neighbors(puzzle, node)

        new_map = _neighbors_to_map(new_neighbors)
        reference_map = _neighbors_to_map(reference_neighbors)

        assert set(new_map.keys()) == set(reference_map.keys())
        for key in new_map:
            assert len(new_map[key]) == len(reference_map[key])
            for new_cost, reference_cost in zip(new_map[key], reference_map[key]):
                assert new_cost == pytest.approx(reference_cost)


def test_ellipsoid_nodes_are_marked_as_elliptical():
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=CaseShape.ELLIPSOID,
    )

    elliptical_nodes = [node for node in puzzle.nodes if node.in_elliptical_grid]

    assert elliptical_nodes, "Expected helper nodes tagged with in_elliptical_grid"
    for node in elliptical_nodes:
        assert node.in_circular_grid
        assert node.ellipse_axis_x is not None
        assert node.ellipse_axis_y is not None
