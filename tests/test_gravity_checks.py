import math

from puzzle.gravity_checks import (
    GRAVITY_CHECKS,
    PathSample,
    run_gravity_checks,
)

WORLD_DOWN = (0.0, 0.0, -1.0)


def make_path(specs, step=10.0):
    """Build samples from (position, tangent, down) triples with even spacing."""
    samples = []
    distance = 0.0
    for position, tangent, down in specs:
        samples.append(
            PathSample(
                position=position, tangent=tangent, distance=distance, down=down
            )
        )
        distance += step
    return samples


def detections_by_key(samples):
    """Map each firing check's key to its detections."""
    return {check.key: dets for check, dets in run_gravity_checks(samples, 10.0)}


def _unit_at(degrees):
    radians = math.radians(degrees)
    return (math.cos(radians), math.sin(radians), 0.0)


# Vertical reversal where the ball descends into the turn (apex opposite "down").
DOWNWARD_HAIRPIN = [
    ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), WORLD_DOWN),
    ((-1.0, 0.0, 5.0), (0.0, 0.0, 1.0), WORLD_DOWN),
    ((0.0, 0.0, 10.0), (1.0, 0.0, 0.0), WORLD_DOWN),
    ((1.0, 0.0, 5.0), (0.0, 0.0, -1.0), WORLD_DOWN),
    ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), WORLD_DOWN),
]

# Vertical reversal, but the mirror (apex on the "down" side): playable, flagged
# by neither check.
VERTICAL_MIRROR = [
    ((-1.0, 0.0, 10.0), (0.0, 0.0, -1.0), WORLD_DOWN),
    ((-1.0, 0.0, 5.0), (0.0, 0.0, -1.0), WORLD_DOWN),
    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), WORLD_DOWN),
    ((1.0, 0.0, 5.0), (0.0, 0.0, 1.0), WORLD_DOWN),
    ((1.0, 0.0, 10.0), (0.0, 0.0, 1.0), WORLD_DOWN),
]

# Abrupt 180 degree turn in the horizontal plane (a tight sideways switchback).
SIDEWAYS_TURN = [
    ((-1.0, 10.0, 0.0), (0.0, -1.0, 0.0), WORLD_DOWN),
    ((-1.0, 5.0, 0.0), (0.0, -1.0, 0.0), WORLD_DOWN),
    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), WORLD_DOWN),
    ((1.0, 5.0, 0.0), (0.0, 1.0, 0.0), WORLD_DOWN),
    ((1.0, 10.0, 0.0), (0.0, 1.0, 0.0), WORLD_DOWN),
]


def test_two_checks_are_registered():
    keys = {check.key for check in GRAVITY_CHECKS}
    assert {"downward-hairpin", "sharp-sideways-turn"} <= keys


def test_downward_hairpin_fires_only_downward_check():
    keys = detections_by_key(make_path(DOWNWARD_HAIRPIN))
    assert "downward-hairpin" in keys
    assert "sharp-sideways-turn" not in keys
    # One occurrence, spanning multiple involved nodes.
    assert len(keys["downward-hairpin"]) == 1
    assert len(keys["downward-hairpin"][0].positions) >= 2


def test_sideways_turn_fires_only_sideways_check():
    keys = detections_by_key(make_path(SIDEWAYS_TURN))
    assert "sharp-sideways-turn" in keys
    assert "downward-hairpin" not in keys
    assert len(keys["sharp-sideways-turn"]) == 1


def test_vertical_mirror_fires_nothing():
    assert detections_by_key(make_path(VERTICAL_MIRROR)) == {}


def test_contained_profile_fires_nothing():
    # Same geometry as the downward hairpin but no "down" (closed/contained):
    # the ball is in a tube and cannot escape.
    contained = [(p, t, None) for p, t, _ in DOWNWARD_HAIRPIN]
    assert detections_by_key(make_path(contained)) == {}


def test_gentle_turn_fires_nothing():
    samples = make_path(
        [((0.0, 0.0, 0.0), _unit_at(30 * step), WORLD_DOWN) for step in range(5)]
    )
    assert detections_by_key(samples) == {}


def test_wide_radius_u_turn_fires_nothing():
    # A 180 degree turn spread over many node-lengths is not a tight reversal.
    samples = make_path(
        [((0.0, 0.0, 0.0), _unit_at(10 * step), WORLD_DOWN) for step in range(20)]
    )
    assert detections_by_key(samples) == {}
