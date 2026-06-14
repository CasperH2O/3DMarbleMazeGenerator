# puzzle/gravity_checks.py
#
# Registry of path "gravity feasibility" checks. Pure (no build123d): a check
# takes samples taken along the played path (position, forward tangent, and the
# local "down"/support direction) and returns the occurrences it flags. The
# geometry layer (assembly/pathing.py) builds the samples and turns each
# detection into a marker.
#
# Add a check by decorating a function with @gravity_check(...); it is then run
# automatically by run_gravity_checks and gets its own marker name and colour.

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

Vec3 = tuple[float, float, float]
Rgba = tuple[float, float, float, float]

# --- Tuning (validated values; intentionally not user config) ---------------
# A reversal candidate is where the forward tangent turns at least
# _REVERSAL_ANGLE_DEG within _REVERSAL_WINDOW_NODES node-lengths of travel.
_REVERSAL_WINDOW_NODES = 4
_REVERSAL_ANGLE_DEG = 170.0
# How the turn plane relates to "down" (alignment = |down . turn_normal|):
#   alignment ~0 -> down lies in the turn plane  -> vertical loop
#   alignment ~1 -> down is perpendicular to it  -> sideways loop
# The two checks partition at this value.
_REVERSAL_VERTICALNESS = 0.5  # downward valley needs (1 - alignment) >= this
_REVERSAL_HORIZONTALNESS = 0.5  # sideways turn needs alignment >= this

# A "drop": travel turns ~90° from forward to align with the local "down" within
# _DROP_ONSET_NODES, then keeps dropping for at least _DROP_SUSTAIN_NODES.
# _DROP_ALIGNMENT is cos(angle): 0.6 ~= within 53° of "down" (a generous margin
# so drops coming out of a curve still count).
_DROP_ALIGNMENT = 0.6
_DROP_ONSET_NODES = 1.5
_DROP_SUSTAIN_NODES = 3.0

# Marker transparency shared by all warning spheres.
_MARKER_ALPHA = 71 / 255


@dataclass(frozen=True)
class PathSample:
    """A point sampled along the played path with its forward tangent."""

    position: Vec3
    tangent: Vec3  # unit forward direction
    distance: float  # cumulative arc length from the start of the path
    # Resolved local "down": the unit support direction (toward the accent body,
    # i.e. the way gravity must point to seat the ball). None when unknown
    # (closed/contained profile), in which case the ball cannot escape there.
    down: Optional[Vec3] = None
    segment_main_index: int = -1
    segment_secondary_index: int = 0


@dataclass(frozen=True)
class GravityDetection:
    """One flagged occurrence: the path-sample positions it involves."""

    positions: tuple[Vec3, ...]


@dataclass(frozen=True)
class GravityCheck:
    """A registered path-feasibility check and how its markers should look."""

    key: str
    name: str  # marker display name, e.g. "Downward Hairpin"
    color: Rgba  # marker colour (RGBA, 0..1)
    detect: Callable[[list[PathSample], float], list[GravityDetection]]


# The registry. Iterate this to run every check.
GRAVITY_CHECKS: list[GravityCheck] = []


def gravity_check(*, key: str, name: str, color: Rgba):
    """Register a path-feasibility check (see module docstring for the shape)."""

    def decorator(func):
        GRAVITY_CHECKS.append(GravityCheck(key=key, name=name, color=color, detect=func))
        return func

    return decorator


# --- Vector helpers (plain tuples) ------------------------------------------
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


# --- Shared reversal detection ----------------------------------------------
def _reversal_spans(
    samples: list[PathSample], node_size: float
) -> list[tuple[int, int, float]]:
    """
    Find candidate near-reversals from tangents alone (no "down" needed).

    Returns (start, peak, best_angle) spans where the forward tangent turns by at
    least _REVERSAL_ANGLE_DEG within _REVERSAL_WINDOW_NODES node-lengths of
    travel. Distances drive the look-ahead window, so the result is independent
    of sampling density. This is the cheap shared pass for every reversal check;
    note it matches a ~180° swing between any two tangents in the window, so a
    vertical dip (down-then-up) and an S-curve (right-then-left) both qualify -
    the individual checks decide what to keep.
    """
    window_distance = _REVERSAL_WINDOW_NODES * node_size
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

        if best_angle >= _REVERSAL_ANGLE_DEG and best_index > index:
            spans.append((index, best_index, best_angle))
            index = best_index  # skip past so the same reversal is not re-found
        else:
            index += 1

    return spans


def _net_heading_reversed(samples: list[PathSample], start: int, peak: int) -> bool:
    """
    True if the path's net heading reverses across the span: the leg entering the
    maneuver and the leg leaving it (the samples just outside the span) are
    ~opposite. Distinguishes a genuine sideways U-turn (legs antiparallel) from
    an S-curve, whose legs are parallel even though its extremes swing ~180°.
    """
    count = len(samples)
    entry_tangent = samples[max(0, start - 1)].tangent
    exit_tangent = samples[min(count - 1, peak + 1)].tangent
    return _angle_between_degrees(entry_tangent, exit_tangent) >= _REVERSAL_ANGLE_DEG


def _reversal_geometry(samples: list[PathSample], start: int, peak: int):
    """
    Shared geometry for a reversal span.

    Returns (down_unit, apex_offset, alignment) where alignment = |down . N| of
    the turn plane normal N (0 = vertical loop, 1 = sideways loop) and
    apex_offset is the apex position relative to the entry->exit chord midpoint.
    Returns None if "down" is unknown (contained) or the turn is degenerate.
    """
    apex = (start + peak) // 2
    down = samples[apex].down
    if down is None:
        return None

    p_in = samples[start].position
    p_apex = samples[apex].position
    p_out = samples[peak].position

    turn_normal = _cross(_sub(p_apex, p_in), _sub(p_out, p_apex))
    normal_length = _length(turn_normal)
    if normal_length < 1e-9:
        return None  # collinear / not a real turn
    turn_normal = tuple(c / normal_length for c in turn_normal)

    down_length = _length(down)
    if down_length < 1e-9:
        return None
    down_unit = tuple(c / down_length for c in down)

    chord_mid = (
        (p_in[0] + p_out[0]) / 2.0,
        (p_in[1] + p_out[1]) / 2.0,
        (p_in[2] + p_out[2]) / 2.0,
    )
    apex_offset = _sub(p_apex, chord_mid)
    alignment = abs(_dot(down_unit, turn_normal))
    return down_unit, apex_offset, alignment


def _span_positions(samples: list[PathSample], start: int, peak: int) -> tuple[Vec3, ...]:
    return tuple(samples[index].position for index in range(start, peak + 1))


# --- Registered checks ------------------------------------------------------
@gravity_check(
    key="downward-hairpin",
    name="Downward Hairpin",
    color=(1.0, 0.35, 0.0, _MARKER_ALPHA),  # red-orange
)
def _check_downward_hairpin(
    samples: list[PathSample], node_size: float
) -> list[GravityDetection]:
    """
    Abrupt ~180° reversal in a vertical plane where the ball descends into the
    turn and would have to climb back out (a downward ∪-valley). Sideways and
    ascending reversals are left to other checks / not flagged.
    """
    detections: list[GravityDetection] = []
    for start, peak, _angle in _reversal_spans(samples, node_size):
        geometry = _reversal_geometry(samples, start, peak)
        if geometry is None:
            continue
        down_unit, apex_offset, alignment = geometry
        if (1.0 - alignment) < _REVERSAL_VERTICALNESS:
            continue  # not a vertical loop -> not this check
        # Apex on the side opposite "down" => ball descends into the reversal
        # (sign calibrated against the real model).
        if _dot(apex_offset, down_unit) < 0.0:
            detections.append(GravityDetection(_span_positions(samples, start, peak)))
    return detections


@gravity_check(
    key="sharp-sideways-turn",
    name="Sharp Sideways Turn",
    color=(1.0, 0.70, 0.15, _MARKER_ALPHA),  # amber-orange
)
def _check_sharp_sideways_turn(
    samples: list[PathSample], node_size: float
) -> list[GravityDetection]:
    """
    Abrupt ~180° turn in the horizontal plane (a tight left/right switchback):
    the turn plane is roughly perpendicular to "down". Both left and right are
    covered (the turn direction within a horizontal plane).

    Unlike a vertical dip, a sideways turn that is unplayable actually reverses
    the net heading, so we require the entry and exit legs to be ~opposite. This
    rejects S-curves (right-then-left), whose legs are parallel even though their
    extremes swing ~180°.
    """
    detections: list[GravityDetection] = []
    for start, peak, _angle in _reversal_spans(samples, node_size):
        geometry = _reversal_geometry(samples, start, peak)
        if geometry is None:
            continue
        _down_unit, _apex_offset, alignment = geometry
        if alignment < _REVERSAL_HORIZONTALNESS:
            continue  # not a horizontal turn
        if not _net_heading_reversed(samples, start, peak):
            continue  # S-curve, not a true sideways reversal
        detections.append(GravityDetection(_span_positions(samples, start, peak)))
    return detections


def _aligned_run_end(
    samples: list[PathSample], onset: int, reference_down: Vec3, threshold: float
) -> int:
    """Last index from onset onward whose tangent stays aligned with reference_down."""
    end = onset
    index = onset
    count = len(samples)
    while index < count and _dot(samples[index].tangent, reference_down) >= threshold:
        end = index
        index += 1
    return end


@gravity_check(
    key="drop",
    name="Drop",
    color=(1.0, 0.85, 0.2, _MARKER_ALPHA),  # yellow-orange
)
def _check_drop(
    samples: list[PathSample], node_size: float
) -> list[GravityDetection]:
    """
    A "drop": travel turns ~90° from forward to align with the local "down" and
    then keeps going down. At the lip "down" points along the upcoming travel, so
    we look for the tangent rotating to align with the lip's "down" within
    _DROP_ONSET_NODES and staying aligned for at least _DROP_SUSTAIN_NODES.
    """
    onset_distance = _DROP_ONSET_NODES * node_size
    sustain_distance = _DROP_SUSTAIN_NODES * node_size
    detections: list[GravityDetection] = []
    count = len(samples)

    lip = 0
    while lip < count:
        lip_down = samples[lip].down
        # The lip must currently roll forward (tangent not yet aligned with down).
        if lip_down is None or _dot(samples[lip].tangent, lip_down) >= _DROP_ALIGNMENT:
            lip += 1
            continue

        # Find where the tangent first turns to align with the lip's "down".
        onset = None
        look = lip + 1
        while look < count and (samples[look].distance - samples[lip].distance) <= onset_distance:
            if _dot(samples[look].tangent, lip_down) >= _DROP_ALIGNMENT:
                onset = look
                break
            look += 1
        if onset is None:
            lip += 1
            continue

        # Require the descent to continue for at least the sustain distance.
        end = _aligned_run_end(samples, onset, lip_down, _DROP_ALIGNMENT)
        if (samples[end].distance - samples[onset].distance) < sustain_distance:
            lip += 1
            continue

        detections.append(GravityDetection(_span_positions(samples, lip, end)))
        lip = end + 1  # skip past this drop

    return detections


def run_gravity_checks(
    samples: list[PathSample], node_size: float
) -> list[tuple[GravityCheck, list[GravityDetection]]]:
    """
    Run every registered check over the samples.

    Returns the (check, detections) pairs that produced at least one detection.
    "Down" must already be resolved on the samples (the geometry layer probes it
    before calling); checks that need it skip samples where it is unknown.
    """
    results: list[tuple[GravityCheck, list[GravityDetection]]] = []
    for check in GRAVITY_CHECKS:
        detections = check.detect(samples, node_size)
        if detections:
            results.append((check, detections))
    return results
