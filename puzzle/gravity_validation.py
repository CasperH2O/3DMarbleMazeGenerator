# puzzle/gravity_validation.py

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from config import PathProfileType
from puzzle.node import Node

# Sentinel main index for issues that belong to the whole path rather than a
# single route segment (e.g. wire-sampled direction checks).
PATH_LEVEL_INDEX = -1


class GravityIssueSeverity(Enum):
    """Severity levels for gravity feasibility findings."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class GravityIssue:
    """A detected route/profile combination that may be hard to play by gravity."""

    severity: GravityIssueSeverity
    segment_main_index: int
    segment_secondary_index: int
    profile_type: Optional[PathProfileType]
    node: Node
    reason: str
    movement_pattern: str
    # Identifies which check produced the issue. Useful for labelling and, later,
    # colour-coding the diagnostic markers per issue type.
    category: str = "general"

    @property
    def segment_label(self) -> str:
        """Return the segment index in the same main.secondary format used elsewhere."""
        if self.segment_main_index == PATH_LEVEL_INDEX:
            return "path"
        return f"{self.segment_main_index}.{self.segment_secondary_index}"


# --- Wire-sampled direction checks ------------------------------------------
#
# These operate on samples taken along the resolved ball-path wire (splines and
# obstacle paths included) rather than on raw route nodes, so they can reason
# about the direction the marble actually travels. The geometry layer builds the
# samples and passes them in as plain data, keeping this module build123d-free.


Vec3 = tuple[float, float, float]


@dataclass(frozen=True)
class PathSample:
    """A point sampled along the ball-path wire with its forward tangent."""

    position: Vec3
    tangent: Vec3  # unit forward direction
    distance: float  # cumulative arc length from the start of the sampled path
    # Resolved local "down": the unit support direction of the open profile (the
    # way gravity must point to keep the ball seated). None when the profile is
    # closed/contained (O, square), so the ball cannot escape there.
    down: Optional[Vec3] = None
    segment_main_index: int = PATH_LEVEL_INDEX
    segment_secondary_index: int = 0


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(a: Vec3) -> float:
    return math.sqrt(_dot(a, a))


def _angle_between_degrees(a: Vec3, b: Vec3) -> float:
    """Angle in degrees between two (assumed unit) direction vectors."""
    dot = max(-1.0, min(1.0, _dot(a, b)))
    return math.degrees(math.acos(dot))


def _is_downward_valley(
    samples: list[PathSample],
    start: int,
    peak: int,
    verticalness_threshold: float,
) -> bool:
    """
    Decide whether a detected reversal is a downward ∪-valley (unplayable).

    A hairpin is only a problem when, relative to the profile's support
    direction, the turn lies in a vertical plane and the ball descends into the
    reversal and would have to climb back out. Sideways hairpins (turn plane
    perpendicular to "down") and the mirror (ascending) case are playable and not
    flagged. Closed/contained profiles have no "down" and are never flagged.

    Sign note: "down" is the accent-probe direction (toward the accent body). As
    measured in the real model, the unplayable "descends-into-the-reversal" case
    is the one whose apex sits on the side OPPOSITE "down" relative to the chord,
    so the test below is ``< 0``. (An earlier ``> 0`` flagged the ascending
    mirror case; corrected against in-model validation.)
    """
    apex = (start + peak) // 2
    down = samples[apex].down
    if down is None:
        # Apex sits in a closed/contained profile; the ball cannot escape.
        return False

    p_in = samples[start].position
    p_apex = samples[apex].position
    p_out = samples[peak].position

    # Normal of the plane the hairpin turns in.
    turn_normal = _cross(_sub(p_apex, p_in), _sub(p_out, p_apex))
    normal_length = _length(turn_normal)
    if normal_length < 1e-9:
        return False  # Degenerate / straight: not a real turn.
    turn_normal = tuple(component / normal_length for component in turn_normal)

    down_length = _length(down)
    if down_length < 1e-9:
        return False
    down_unit = tuple(component / down_length for component in down)

    # "Down" perpendicular to the turn plane -> sideways loop -> playable.
    # "Down" lying in the turn plane -> vertical loop -> candidate valley.
    verticalness = 1.0 - abs(_dot(down_unit, turn_normal))
    if verticalness < verticalness_threshold:
        return False

    # Flag the "descends into the reversal" case: the apex sits on the side
    # opposite "down" relative to the chord (see sign note above).
    chord_mid = (
        (p_in[0] + p_out[0]) / 2.0,
        (p_in[1] + p_out[1]) / 2.0,
        (p_in[2] + p_out[2]) / 2.0,
    )
    apex_offset = _sub(p_apex, chord_mid)
    return _dot(apex_offset, down_unit) < 0.0


def _reversal_spans(
    samples: list[PathSample],
    node_size: float,
    window_nodes: float,
    angle_threshold_deg: float,
) -> list[tuple[int, int, float]]:
    """
    Find candidate near-reversals from tangents alone (no "down" needed).

    Returns (start, peak, best_angle) spans where the forward tangent turns by at
    least ``angle_threshold_deg`` within ``window_nodes`` node-lengths of travel.
    Distances drive the look-ahead window, so the result is independent of
    sampling density. This is the cheap first pass; the costly "down" probe and
    the ∪-valley test only run on these spans.
    """
    window_distance = window_nodes * node_size
    spans: list[tuple[int, int, float]] = []
    count = len(samples)

    index = 0
    while index < count:
        origin = samples[index]
        best_angle = 0.0
        best_index = index

        look = index + 1
        while (
            look < count
            and (samples[look].distance - origin.distance) <= window_distance
        ):
            angle = _angle_between_degrees(origin.tangent, samples[look].tangent)
            if angle > best_angle:
                best_angle = angle
                best_index = look
            look += 1

        if best_angle >= angle_threshold_deg and best_index > index:
            spans.append((index, best_index, best_angle))
            index = best_index  # skip past so the same reversal is not re-found
        else:
            index += 1

    return spans


def involved_reversal_indices(
    samples: list[PathSample],
    *,
    node_size: float,
    window_nodes: float,
    angle_threshold_deg: float,
) -> set[int]:
    """Sample indices belonging to any candidate reversal (for lazy down probing)."""
    indices: set[int] = set()
    for start, peak, _ in _reversal_spans(
        samples, node_size, window_nodes, angle_threshold_deg
    ):
        indices.update(range(start, peak + 1))
    return indices


def detect_direction_reversals(
    samples: list[PathSample],
    *,
    node_size: float,
    window_nodes: float,
    angle_threshold_deg: float,
    verticalness_threshold: float,
) -> list[GravityIssue]:
    """
    Flag downward ∪-valley near-reversals (hairpins) in the played path.

    Candidate reversals are found from tangents (see _reversal_spans); each is
    kept only if it is a downward valley relative to the local "down"/support
    direction (see _is_downward_valley) — the marble would roll down into the
    turn and have to climb back out, which gravity cannot drive. Sideways and
    ascending hairpins, and hairpins where "down" is unknown (closed/contained
    profiles, i.e. no accent body), are not flagged.

    The "down" field must already be populated for the samples involved in each
    candidate span (the geometry layer probes it lazily). An issue is emitted for
    every sample involved in a flagged hairpin so the whole stretch is marked.
    """
    issues: list[GravityIssue] = []
    hairpin_id = 0

    for start, peak, best_angle in _reversal_spans(
        samples, node_size, window_nodes, angle_threshold_deg
    ):
        if not _is_downward_valley(samples, start, peak, verticalness_threshold):
            continue

        hairpin_id += 1
        span_nodes = max(
            1,
            round((samples[peak].distance - samples[start].distance) / node_size),
        )
        pattern = (
            f"hairpin {hairpin_id}: reversal {best_angle:.0f}° / {span_nodes} nodes"
        )
        reason = (
            f"The path direction reverses by about {best_angle:.0f}° within "
            f"{span_nodes} node-length(s); gravity cannot roll the marble back "
            "on itself this sharply."
        )

        for involved in range(start, peak + 1):
            sample = samples[involved]
            issues.append(
                GravityIssue(
                    severity=GravityIssueSeverity.WARNING,
                    segment_main_index=PATH_LEVEL_INDEX,
                    segment_secondary_index=0,
                    profile_type=None,
                    node=Node(
                        sample.position[0],
                        sample.position[1],
                        sample.position[2],
                    ),
                    reason=reason,
                    movement_pattern=pattern,
                    category="direction-reversal",
                )
            )

    return issues
