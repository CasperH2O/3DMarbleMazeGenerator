# cad/spline_occupancy.py

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from build123d import Spline, Vector

from cad.path_segment import PathSegment
from config import PathSegmentDesignStrategy
from puzzle.node import Node

logger = logging.getLogger(__name__)


@dataclass
class RejectedSpline:
    """A SPLINE segment demoted to COMPOUND because it intruded into occupied space.

    ``overlap_fraction`` is the deepest single-cube volumetric overlap found.
    ``spline_points`` are the sampled (x, y, z) positions of the approximate
    (option-1) spline that was evaluated ie the rejected curve. 

    ``intersection_points`` are the centres of the occupied cubes the spline 
    intruded on, so the collision spots can be marked.
    """

    segment: PathSegment
    overlap_fraction: float
    spline_points: list[tuple[float, float, float]] = field(default_factory=list)
    intersection_points: list[tuple[float, float, float]] = field(
        default_factory=list
    )


@dataclass
class SplineVoxelDebug:
    """Per-spline voxelization, for the cube overlay in the visualization.

    ``voxel_centers`` are the centres of the free-floating cubes sampled along the
    spline; ``foreign_voxel_centers`` are the subset that overlapped an occupied
    cube beyond the threshold. ``overlap_fraction`` is the deepest overlap found.
    """

    segment: PathSegment
    voxel_centers: list[tuple[float, float, float]] = field(default_factory=list)
    foreign_voxel_centers: list[tuple[float, float, float]] = field(
        default_factory=list
    )
    overlap_fraction: float = 0.0
    demoted: bool = False


@dataclass
class SplineOccupancyResult:
    """Outcome of :func:`evaluate_spline_occupancy`."""

    rejected: list[RejectedSpline] = field(default_factory=list)
    # Per-spline sample cubes, for the visualization's cube overlay.
    voxel_debug: list[SplineVoxelDebug] = field(default_factory=list)


class _SpatialHash:
    """Buckets positioned items into ``cell_size`` cubes for neighbourhood queries.

    Items need not lie on a regular lattice (circular-grid nodes do not). A query
    returns every item in the 3x3x3 block of cells around a point, which covers all
    items whose ``cell_size`` cube can overlap a cube centred at that point.
    """

    def __init__(self, cell_size: float) -> None:
        self._cell_size = cell_size
        self._cells: dict[
            tuple[int, int, int], list[tuple[tuple[float, float, float], object]]
        ] = {}

    def cell_of(self, x: float, y: float, z: float) -> tuple[int, int, int]:
        size = self._cell_size
        return (round(x / size), round(y / size), round(z / size))

    def add(self, position: tuple[float, float, float], owner: object = None) -> None:
        self._cells.setdefault(self.cell_of(*position), []).append((position, owner))

    def candidates(self, x: float, y: float, z: float):
        """Yield (position, owner) for every item in the 3x3x3 cells around (x, y, z)."""
        cx, cy, cz = self.cell_of(x, y, z)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    yield from self._cells.get((cx + dx, cy + dy, cz + dz), ())


def _cube_overlap_fraction(
    center_a: tuple[float, float, float],
    center_b: tuple[float, float, float],
    side: float,
) -> float:
    """Volumetric overlap of two axis-aligned cubes of equal ``side``, as a fraction
    of one cube's volume. 1.0 = coincident centres, 0.0 = no overlap."""
    volume = 1.0
    for axis in range(3):
        extent = side - abs(center_a[axis] - center_b[axis])
        if extent <= 0.0:
            return 0.0
        volume *= extent
    return volume / (side**3)


def _safe_direction(vector: Vector, fallback: Vector) -> Vector:
    """Normalize ``vector``; fall back when it is effectively zero length."""
    return vector.normalized() if vector.length > 1e-9 else fallback


def _direction_between(start: Node, end: Node) -> Vector:
    return Vector(end.x - start.x, end.y - start.y, end.z - start.z)


def _approximate_tangents(
    segment: PathSegment,
    previous_segment: PathSegment | None,
    next_segment: PathSegment | None,
) -> tuple[Vector, Vector]:
    """Approximate the tangents the builder would derive from neighbour paths.

    The real builder uses ``previous_segment.path % 1`` / ``next_segment.path % 0``, 
    which do not exist yet at architect time. We reconstruct the route direction at 
    each joint from node positions, handling single-node "stitch" neighbours, 
    and fall back to the segment's own internal direction when there is no usable neighbour.
    """

    _DEFAULT_DIRECTION = Vector(1, 0, 0) # Last resort fall back
    nodes = segment.nodes

    internal_start = _safe_direction(
        _direction_between(nodes[0], nodes[1]), _DEFAULT_DIRECTION
    )
    internal_end = _safe_direction(
        _direction_between(nodes[-2], nodes[-1]), internal_start
    )

    if previous_segment and len(previous_segment.nodes) >= 2:
        start_tangent = _safe_direction(
            _direction_between(
                previous_segment.nodes[-2], previous_segment.nodes[-1]
            ),
            internal_start,
        )
    elif previous_segment and previous_segment.nodes:
        start_tangent = _safe_direction(
            _direction_between(previous_segment.nodes[-1], nodes[0]), internal_start
        )
    else:
        start_tangent = internal_start

    if next_segment and len(next_segment.nodes) >= 2:
        end_tangent = _safe_direction(
            _direction_between(next_segment.nodes[0], next_segment.nodes[1]),
            internal_end,
        )
    elif next_segment and next_segment.nodes:
        end_tangent = _safe_direction(
            _direction_between(nodes[-1], next_segment.nodes[0]), internal_end
        )
    else:
        end_tangent = internal_end

    return start_tangent, end_tangent


def _trim_spline_ends(spline, trim_length: float):
    """Trim ``trim_length`` (mm) off each end of ``spline`` and return the result.

    Trimming uses a length ratio; the end trim is recomputed from the length left
    after the start trim, so both ends lose the same arc length. Returns ``None``
    when the spline is too short to trim both ends (length <= 2 * trim_length)."""
    length = spline.length
    if length <= 2.0 * trim_length:
        return None
    trimmed = spline.trim(trim_length / length, 1.0)
    return trimmed.trim(0.0, 1.0 - trim_length / trimmed.length)


def _sample_option1_spline(
    segment: PathSegment,
    previous_segment: PathSegment | None,
    next_segment: PathSegment | None,
    node_size: float,
) -> tuple[list[Vector], list[Vector]] | None:
    """Sample the approximate option-1 spline, or ``None`` if it cannot be built.

    Returns ``(trimmed_samples, full_samples)``:

    - ``trimmed_samples`` are along the spline with half a node removed at each end,
      so the shared joints with the neighbouring segments -- where the spline
      legitimately overlaps them -- are never voxelized. These drive the check. A
      spline too short to trim both ends is sampled whole (rare).
    - ``full_samples`` trace the whole untrimmed curve, for drawing the rejected
      spline in the debug overlay.

    Each curve is sampled every half node along its length, so the sample count
    follows the length: adjacent node_size cubes then overlap by half and tile the
    curve with no gaps.

    An option 1 spline is a strategy of the PathBuilder, creating a spline based on
    its start and end node with tangents only.
    """
    nodes = segment.nodes
    first = Vector(nodes[0].x, nodes[0].y, nodes[0].z)
    last = Vector(nodes[-1].x, nodes[-1].y, nodes[-1].z)
    start_tangent, end_tangent = _approximate_tangents(
        segment, previous_segment, next_segment
    )
    spacing = node_size / 2.0

    def _sample(curve) -> list[Vector]:
        intervals = max(1, round(curve.length / spacing))
        return [curve @ (index / intervals) for index in range(intervals + 1)]

    try:
        spline = Spline([first, last], tangents=[start_tangent, end_tangent])
        full_samples = _sample(spline)
        trimmed = _trim_spline_ends(spline, node_size / 2.0)
        trimmed_samples = _sample(trimmed if trimmed is not None else spline)
        return trimmed_samples, full_samples
    except Exception as error:  # build123d/OCCT can fail on degenerate inputs
        logger.warning(
            "Spline occupancy: could not build approximate spline for segment "
            "%s.%s (%s); leaving strategy unchanged.",
            segment.main_index,
            segment.secondary_index,
            error,
        )
        return None


def evaluate_spline_occupancy(
    segments: list[PathSegment],
    nodes: list[Node],
    *,
    node_size: float,
    max_overlap: float,
) -> SplineOccupancyResult:
    """Demote SPLINE segments that intrude into occupied space.

    Each spline is sampled into free-floating cubes centred on
    points along its option-1 curve, one every half node. A spline is demoted when
    one sample cube overlaps an occupied node's cube, or a cube reserved by an
    earlier accepted spline, by more than ``max_overlap`` of a cube's volume.
    Overlap is measured per occupied node (not unioned), so a sample straddling two
    nodes shallowly is tolerated; only a single deep intrusion rejects. Every sample
    is scanned (no early exit) and recorded on ``voxel_debug`` for the cube overlay.

    Args:
        segments: All path segments, in path order. Demoted SPLINE segments are
            mutated in place to ``PathSegmentDesignStrategy.COMPOUND``.
        nodes: The occupied path nodes (the architect's ``total_path``).
        node_size: Grid spacing in mm; the cube side used for overlap, and (halved)
            the spacing between sample cubes along the spline.
        max_overlap: Volumetric overlap fraction (0-1) of a single sample cube with
            an occupied cube above which the spline is demoted.

    Returns:
        A :class:`SplineOccupancyResult` with the demoted segments and debug data.
    """
    result = SplineOccupancyResult()
    occupied = _SpatialHash(node_size)
    for node in nodes:
        occupied.add((node.x, node.y, node.z), node)
    # Cubes claimed by earlier accepted splines, for the spline-vs-spline case.
    reserved = _SpatialHash(node_size)

    for index, segment in enumerate(segments):
        if segment.design_strategy != PathSegmentDesignStrategy.SPLINE:
            continue
        if len(segment.nodes) < 2:
            continue

        previous_segment = segments[index - 1] if index > 0 else None
        next_segment = segments[index + 1] if index + 1 < len(segments) else None

        sampled = _sample_option1_spline(
            segment, previous_segment, next_segment, node_size
        )
        if sampled is None:
            continue
        trimmed_points, full_points = sampled

        # Nodes that legitimately belong to this spline, never a collision. The
        # connection to the previous/next segment is handled by trimming the spline
        # ends.
        excluded_nodes: set[Node] = set(segment.nodes)

        # The trimmed samples drive the check; the full curve is kept for display.
        sample_centers = [(point.X, point.Y, point.Z) for point in trimmed_points]
        full_centers = [(point.X, point.Y, point.Z) for point in full_points]
        colliding_centers: list[tuple[float, float, float]] = []
        intersection_points: set[tuple[float, float, float]] = set()
        max_fraction = 0.0

        for center in sample_centers:
            sample_collides = False
            # Occupied route nodes, then cubes reserved by earlier accepted splines.
            for source in (occupied, reserved):
                for position, owner in source.candidates(*center):
                    if owner is not None and owner in excluded_nodes:
                        continue
                    fraction = _cube_overlap_fraction(center, position, node_size)
                    if fraction > max_fraction:
                        max_fraction = fraction
                    if fraction > max_overlap:
                        sample_collides = True
                        intersection_points.add(position)
            if sample_collides:
                colliding_centers.append(center)

        demoted = len(colliding_centers) > 0

        result.voxel_debug.append(
            SplineVoxelDebug(
                segment=segment,
                voxel_centers=sample_centers,
                foreign_voxel_centers=colliding_centers,
                overlap_fraction=max_fraction,
                demoted=demoted,
            )
        )

        if demoted:
            segment.design_strategy = PathSegmentDesignStrategy.COMPOUND
            result.rejected.append(
                RejectedSpline(
                    segment,
                    max_fraction,
                    full_centers,  # draw the whole spline, not the trimmed one
                    list(intersection_points),
                )
            )
            logger.warning(
                "Spline occupancy: segment %s.%s intrudes %.0f%% into an occupied "
                "cube (> %.0f%% threshold); demoting SPLINE -> COMPOUND.",
                segment.main_index,
                segment.secondary_index,
                max_fraction * 100.0,
                max_overlap * 100.0,
            )
        else:
            # Accepted: reserve the cubes it sweeps so later splines see it too.
            for center in sample_centers:
                reserved.add(center)
            logger.debug(
                "Spline occupancy: segment %s.%s accepted (max overlap %.0f%%).",
                segment.main_index,
                segment.secondary_index,
                max_fraction * 100.0,
            )

    if result.rejected:
        logger.info(
            "Spline occupancy: demoted %d SPLINE segment(s) to COMPOUND.",
            len(result.rejected),
        )
    return result
