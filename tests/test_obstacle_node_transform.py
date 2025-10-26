import math

import pytest
from build123d import Location, Pos, Vector

from obstacles.obstacle import Obstacle
from puzzle.node import Node


class DummyObstacle(Obstacle):
    """Minimal concrete obstacle for testing coordinate transforms."""

    def create_obstacle_geometry(self):  # pragma: no cover - not needed for test
        return None

    def model_solid(self):  # pragma: no cover - not needed for test
        return None

    def model_solid_extras(self):  # pragma: no cover - not needed for test
        return None


@pytest.fixture
def obstacle():
    obs = DummyObstacle("Dummy")
    obs.location = Location(Pos(Vector(10.0, -5.0, 2.5)))
    obs.occupied_nodes = [Node(0.0, 0.0, 0.0, occupied=True)]
    obs.overlap_nodes = [Node(1.0, 2.0, 3.0, overlap_allowed=True)]
    return obs


def test_get_placed_node_coordinates_returns_copies(obstacle: DummyObstacle):
    first_call = obstacle.get_placed_node_coordinates(obstacle.occupied_nodes)
    second_call = obstacle.get_placed_node_coordinates(obstacle.occupied_nodes)

    # cached data stays in local coordinates
    assert obstacle.occupied_nodes[0].x == 0.0
    assert obstacle.occupied_nodes[0].y == 0.0
    assert obstacle.occupied_nodes[0].z == 0.0

    # transformed nodes are new instances
    assert first_call[0] is not obstacle.occupied_nodes[0]
    assert second_call[0] is not obstacle.occupied_nodes[0]

    # repeated calls remain consistent and reflect placement translation
    assert math.isclose(first_call[0].x, 10.0)
    assert math.isclose(first_call[0].y, -5.0)
    assert math.isclose(first_call[0].z, 2.5)
    assert math.isclose(second_call[0].x, 10.0)
    assert math.isclose(second_call[0].y, -5.0)
    assert math.isclose(second_call[0].z, 2.5)


def test_world_nodes_snap_and_copy(obstacle: DummyObstacle):
    helper_nodes = [
        Node(
            2.2,
            -2.4,
            3.6,
            occupied=True,
            in_circular_grid=True,
            in_rectangular_grid=True,
        )
    ]

    world_nodes = obstacle.world_nodes(helper_nodes, snap_to_grid=True)

    # original helper nodes remain untouched
    assert helper_nodes[0].x == 2.2
    assert helper_nodes[0].y == -2.4
    assert helper_nodes[0].z == 3.6

    assert world_nodes[0] is not helper_nodes[0]
    # snapped to grid of size 10 with obstacle's translation applied
    assert world_nodes[0].x == 10.0
    assert world_nodes[0].y == -10.0
    assert world_nodes[0].z == 10.0
    # helper flags preserved
    assert world_nodes[0].in_circular_grid
    assert world_nodes[0].in_rectangular_grid
