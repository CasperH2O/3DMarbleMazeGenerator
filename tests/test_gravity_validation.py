import math

from puzzle.gravity_validation import (
    PathSample,
    detect_direction_reversals,
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


def detect(samples, verticalness=0.5):
    return detect_direction_reversals(
        samples,
        node_size=10.0,
        window_nodes=4,
        angle_threshold_deg=150.0,
        verticalness_threshold=verticalness,
    )


def _unit_at(degrees):
    radians = math.radians(degrees)
    return (math.cos(radians), math.sin(radians), 0.0)


# "down" is the accent-probe direction (toward the accent body). Per in-model
# validation, the unplayable "ball descends into the reversal" hairpin is the one
# whose apex lies on the side OPPOSITE "down" relative to the entry->exit chord;
# the gate flags that and ignores its mirror. The fixtures below are defined by
# that geometric relationship (using down = world -Z for clarity).

# Apex displaced OPPOSITE to "down" from the chord -> flagged (descends-in case).
HAIRPIN_FLAGGED = [
    ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0), WORLD_DOWN),
    ((-1.0, 0.0, 5.0), (0.0, 0.0, 1.0), WORLD_DOWN),
    ((0.0, 0.0, 10.0), (1.0, 0.0, 0.0), WORLD_DOWN),
    ((1.0, 0.0, 5.0), (0.0, 0.0, -1.0), WORLD_DOWN),
    ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), WORLD_DOWN),
]

# Apex displaced ALONG "down" from the chord -> the playable mirror, not flagged.
HAIRPIN_MIRROR = [
    ((-1.0, 0.0, 10.0), (0.0, 0.0, -1.0), WORLD_DOWN),
    ((-1.0, 0.0, 5.0), (0.0, 0.0, -1.0), WORLD_DOWN),
    ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), WORLD_DOWN),
    ((1.0, 0.0, 5.0), (0.0, 0.0, 1.0), WORLD_DOWN),
    ((1.0, 0.0, 10.0), (0.0, 0.0, 1.0), WORLD_DOWN),
]


def test_unplayable_hairpin_is_flagged_and_marks_involved_nodes():
    issues = detect(HAIRPIN_FLAGGED)

    assert len(issues) >= 1
    assert all(issue.category == "direction-reversal" for issue in issues)
    assert all(issue.segment_label == "path" for issue in issues)
    assert all("hairpin 1" in issue.movement_pattern for issue in issues)


def test_mirror_hairpin_is_not_flagged():
    assert detect(HAIRPIN_MIRROR) == []


def test_sideways_hairpin_is_not_flagged():
    # Reversal turning in the horizontal X-Y plane; "down" (world -Z) is
    # perpendicular to the turn plane, so the ball just rounds the bend.
    sideways = [
        ((-1.0, 10.0, 0.0), (0.0, -1.0, 0.0), WORLD_DOWN),
        ((-1.0, 5.0, 0.0), (0.0, -1.0, 0.0), WORLD_DOWN),
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), WORLD_DOWN),
        ((1.0, 5.0, 0.0), (0.0, 1.0, 0.0), WORLD_DOWN),
        ((1.0, 10.0, 0.0), (0.0, 1.0, 0.0), WORLD_DOWN),
    ]

    assert detect(sideways) == []


def test_hairpin_in_closed_profile_is_not_flagged():
    # Same geometry as the flagged case, but a closed/contained profile (no
    # "down"): the ball is in a tube and cannot escape.
    contained = [(position, tangent, None) for position, tangent, _ in HAIRPIN_FLAGGED]

    assert detect(contained) == []


def test_gentle_turn_is_not_flagged_as_reversal():
    samples = make_path(
        [((0.0, 0.0, 0.0), _unit_at(30 * step), WORLD_DOWN) for step in range(5)]
    )

    assert detect(samples) == []


def test_wide_radius_u_turn_is_not_flagged():
    # A 180 degree turn spread over many node-lengths is not a tight hairpin.
    samples = make_path(
        [((0.0, 0.0, 0.0), _unit_at(10 * step), WORLD_DOWN) for step in range(20)]
    )

    assert detect(samples) == []
