# assembly/pathing.py

import logging
from dataclasses import replace
from typing import Optional

from build123d import (
    Align,
    BuildPart,
    Color,
    Cone,
    Edge,
    Location,
    Locations,
    Part,
    Plane,
    Sphere,
    Vector,
    Wire,
    add,
)

from config import Config
from cad.path_builder import PathBuilder, PathTypes
from puzzle.gravity_validation import (
    PathSample,
    detect_direction_reversals,
    involved_reversal_indices,
)
from puzzle.utils.enums import PathSegmentDesignStrategy
from puzzle.puzzle import Puzzle

logger = logging.getLogger(__name__)

# Gravity hairpin check tuning - validated values, intentionally not exposed as
# user config. Samples are taken one node length apart; a reversal is flagged
# when the path turns >= _REVERSAL_ANGLE_DEG within _REVERSAL_WINDOW_NODES node
# lengths and is a downward valley (turn plane contains "down" by at least
# _REVERSAL_VERTICALNESS, apex on the low side).
_REVERSAL_WINDOW_NODES = 4
_REVERSAL_ANGLE_DEG = 150.0
_REVERSAL_VERTICALNESS = 0.5


def path(puzzle: Puzzle, cut_shape: Part):
    """
    Generate the path objects, cut them from the case where needed, and return:
      - standard_paths: a list of standard path bodies with proper labeling and colors
      - support_path: a single support path body
      - coloring_path: a single accent/coloring path body
    """
    # Initialize the PathBuilder (which internally builds and stores the final path bodies)
    path_builder = PathBuilder(puzzle)

    standard_path_bodies: Optional[list[Part]] = None
    support_path: Optional[Part] = None
    coloring_path: Optional[Part] = None

    # Retrieve the path bodies and the start area
    path_bodies = path_builder.final_path_bodies
    start_area = path_builder.start_area

    # Process standard paths:
    standard_path_bodies = []
    if path_bodies.get(PathTypes.STANDARD):
        # Available standard colors from the configuration (roll over if more segments than colors)
        standard_colors = Config.Puzzle.PATH_COLORS
        standard_parts = path_bodies[PathTypes.STANDARD]
        # Loop through each standard path part; use a counter for labeling and color assignment.
        for idx, part in enumerate(standard_parts, start=1):
            # For the first body, combine it with the start area
            if idx == 1:
                combined = part + (
                    start_area[0].part - cut_shape.part
                )  # merge with the first start area element
            else:
                combined = part
            # Subtract the cut shape from the combined (or single) object. #FIXME
            final_obj = combined  # - cut_shape.part
            # Assign a label with a counter (e.g., "Standard Path 1", "Standard Path 2", etc.)
            final_obj.label = f"Standard Path {idx}"
            # Use the color from the list, rolling over if necessary.
            final_obj.color = standard_colors[(idx - 1) % len(standard_colors)]
            standard_path_bodies.append(final_obj)

    if path_bodies[PathTypes.SUPPORT]:
        support_path = Part() + [path_bodies[PathTypes.SUPPORT]]
        support_path = support_path - cut_shape.part
        support_path.label = PathTypes.SUPPORT.value
        support_path.color = Config.Puzzle.SUPPORT_MATERIAL_COLOR

    if path_bodies[PathTypes.ACCENT_COLOR]:
        accent_seg = path_bodies[PathTypes.ACCENT_COLOR]
        funnel_part = start_area[1].part - cut_shape.part
        coloring_path = Part() + [accent_seg, funnel_part]
        coloring_path.label = PathTypes.ACCENT_COLOR.value
        coloring_path.color = Config.Puzzle.PATH_ACCENT_COLOR

    return standard_path_bodies, support_path, coloring_path


def build_obstacle_path_body_extras(puzzle: Puzzle) -> list[Part]:
    """
    Obstacle path body extras that are not part of sweep
    """
    parts: list[Part] = []

    for idx, obstacle in enumerate(puzzle.obstacle_manager.placed_obstacles, start=1):
        placed_part = obstacle.get_placed_obstacle_extras()

        # Obstacle extra's are optional, don't add
        if placed_part is None:
            continue

        # Label and color individually
        part = Part(placed_part)
        part.label = f"Obstacle {idx} - {obstacle.name} extra's"
        part.color = Config.Puzzle.PATH_COLORS[0]

        parts.append(part)

    return parts


def build_gravity_warning_spheres(puzzle: Puzzle) -> list[Part]:
    """
    Build transparent warning spheres for gravity feasibility issues.

    Currently the only check is the hairpin detector: it samples the played path
    wire (splines and obstacle paths included) and flags the nodes involved in a
    near-reversal of direction. The per-node findings of each detection are
    combined into a single sphere at their average location, sized to enclose the
    involved nodes. Each sphere gets a clean incrementing name (no "/", which the
    viewer treats as a tree separator) so they list properly under the group.
    These markers are diagnostic only; they do not reject or alter the puzzle.
    """
    logger.info("Performing gravity hairpin check...")

    samples = build_oriented_path_samples(puzzle)

    # Cheap first pass: find candidate reversals from tangents only, then probe
    # the costly "down" direction (accent body) just for the samples involved.
    candidate_indices = involved_reversal_indices(
        samples,
        node_size=Config.Puzzle.NODE_SIZE,
        window_nodes=_REVERSAL_WINDOW_NODES,
        angle_threshold_deg=_REVERSAL_ANGLE_DEG,
    )
    samples = fill_sample_down(puzzle, samples, candidate_indices)

    issues = detect_direction_reversals(
        samples,
        node_size=Config.Puzzle.NODE_SIZE,
        window_nodes=_REVERSAL_WINDOW_NODES,
        angle_threshold_deg=_REVERSAL_ANGLE_DEG,
        verticalness_threshold=_REVERSAL_VERTICALNESS,
    )
    if not issues:
        return []

    # Group the per-node findings by detection (movement_pattern is unique per
    # hairpin, e.g. "hairpin 1: ...").
    grouped: dict[str, list] = {}
    for issue in issues:
        grouped.setdefault(issue.movement_pattern, []).append(issue)

    node_size = Config.Puzzle.NODE_SIZE
    warning_color = Color(1.0, 0.55, 0.0, 71 / 255)

    spheres: list[Part] = []
    for index, (_pattern, group) in enumerate(grouped.items(), start=1):
        points = [Vector(issue.node.x, issue.node.y, issue.node.z) for issue in group]
        centroid = sum(points, Vector(0, 0, 0)) * (1.0 / len(points))

        # Size the sphere to sit over the involved nodes, with a sensible floor.
        spread = max((point - centroid).length for point in points)
        radius = max(spread + node_size * 0.5, node_size * 0.6) * 0.8

        with BuildPart() as sphere_builder:
            Sphere(radius)

        sphere = sphere_builder.part
        sphere.position = centroid
        # Clean incrementing name only — no "/" (the viewer's tree separator).
        sphere.label = f"Gravity Warning {index}"
        sphere.color = warning_color
        spheres.append(sphere)

    logger.warning(
        "Gravity hairpin check: found %d potential hairpin reversal(s) where "
        "gravity cannot drive the marble through the turn.",
        len(spheres),
    )
    return spheres


def build_ball_path_wire(puzzle: Puzzle) -> Optional[Wire]:
    """
    Build the playable ball-path wire (the "Path Indicator").

    Collects the resolved path edges of every segment except the start ramp,
    including spline paths and obstacle paths, and trims half a node off the end
    so it finishes nicely in the finish box. Returns None when there are no
    usable edges. This single source is sampled for direction arrows and reused
    for the visual Path Indicator.
    """
    path_edges: list[Edge] = []

    # Append edges from different data types and sources
    # TODO Could probably be improved if all path segment
    # paths were more consistently converted to one type
    def _append_edges_from(source) -> None:
        if source is None:
            return
        if isinstance(source, Wire):
            for edge in source.edges():
                _append_edges_from(edge)
        elif isinstance(source, Edge):
            if source.length > 0:
                path_edges.append(source)
        elif isinstance(source, (list, tuple)):
            for sub_source in source:
                _append_edges_from(sub_source)
        elif hasattr(source, "edges"):
            for edge in source.edges():
                _append_edges_from(edge)

    # Collect edges that represent the playable path
    for segment in puzzle.path_architect.segments:
        # Skip start segment
        if any(node.puzzle_start for node in segment.nodes):
            continue

        _append_edges_from(segment.path)

    if not path_edges:
        return None

    ball_path_wire = Wire(path_edges)

    # Trim path with half a node size to nicely end in the finish box
    # Derive a normalized parameter [0..1] from lengths
    reduced_length = 0.5 * Config.Puzzle.NODE_SIZE
    if ball_path_wire.length <= reduced_length:
        return ball_path_wire
    end_parameter = 1.0 - (reduced_length / ball_path_wire.length)
    return ball_path_wire.trim(0, end_parameter)


def _is_swept_geometry_segment(segment) -> bool:
    """
    True for segments whose shape lives BETWEEN the nodes and so must be sampled
    along the swept wire: splines and obstacles. Regular (standard/compound)
    segments are well represented by their node locations.
    """
    if getattr(segment, "is_obstacle", False):
        return True
    return segment.design_strategy in (
        PathSegmentDesignStrategy.SPLINE,
        PathSegmentDesignStrategy.OBSTACLE,
    )


def build_oriented_path_samples(puzzle: Puzzle) -> list[PathSample]:
    """
    Sample the path, combining two strategies for the best of both worlds:

      - regular (standard/compound) segments contribute their node locations,
        which line up cleanly with the grid corners;
      - splines and obstacles are sampled along the swept wire at the configured
        spacing, because their shape is not captured by node positions alone.

    Forward-difference tangents and cumulative arc length are then computed over
    the combined, de-duplicated, in-order point list, so reversals that span
    segment boundaries are still seen. "Down" is cheap-omitted here and filled in
    lazily by fill_sample_down() only where it is needed.
    """
    spacing = Config.Puzzle.NODE_SIZE  # one sample per node length
    if spacing <= 0:
        return []

    # 1) Collect ordered (position, segment) points along the whole path.
    points = []
    for segment in puzzle.path_architect.segments:
        if any(node.puzzle_start for node in segment.nodes):
            continue
        path = segment.path
        if path is None:
            continue

        if _is_swept_geometry_segment(segment):
            try:
                length = path.length
            except Exception:  # noqa: BLE001 - skip anything not 1D-sampleable
                continue
            if length <= 0:
                continue
            fine_steps = max(int(length / (spacing * 0.25)), 8)
            since_last = spacing  # emit the first point of the segment
            previous = None
            for step in range(fine_steps + 1):
                position = path @ (step / fine_steps)
                if previous is not None:
                    since_last += (position - previous).length
                previous = position
                if since_last >= spacing or step == fine_steps:
                    since_last = 0.0
                    points.append((position, segment))
        else:
            for node in segment.nodes:
                points.append((Vector(node.x, node.y, node.z), segment))

    # 2) Drop consecutive duplicates (adjacent segments share boundary nodes).
    ordered = []
    for position, segment in points:
        if ordered and (position - ordered[-1][0]).length < 1e-6:
            continue
        ordered.append((position, segment))

    # 3) Forward-difference tangents + cumulative arc length over the point list.
    samples: list[PathSample] = []
    count = len(ordered)
    cumulative = 0.0
    for index in range(count):
        position, segment = ordered[index]
        if index > 0:
            cumulative += (position - ordered[index - 1][0]).length

        if index < count - 1:
            tangent = ordered[index + 1][0] - position
        elif index > 0:
            tangent = position - ordered[index - 1][0]
        else:
            tangent = Vector(1, 0, 0)
        tangent = tangent.normalized() if tangent.length > 0 else Vector(1, 0, 0)

        samples.append(
            PathSample(
                position=(position.X, position.Y, position.Z),
                tangent=(tangent.X, tangent.Y, tangent.Z),
                distance=cumulative,
                down=None,
                segment_main_index=segment.main_index,
                segment_secondary_index=segment.secondary_index,
            )
        )

    return samples


def _probe_down(segment, point: Vector) -> Optional[tuple]:
    """
    Resolve the local "down" at a path point by probing the accent body.

    The accent ("path color") body is always built on the down side of the ball,
    so the closest point on it from the path centerline points into the support.
    This reads the real built geometry, so it is exact for every segment type
    (standard, arc, spline) with no frame reconstruction. O/closed profiles have
    no accent body, which correctly yields None (the ball is contained there).
    Uses a single closest-point query (BRepExtrema) rather than a plane-boolean.
    """
    accent = getattr(segment, "accent_body", None)
    if accent is None:
        return None
    solid = getattr(accent, "part", accent)
    try:
        on_accent, _ = solid.closest_points(point)
        down = on_accent - point
        if down.length <= 0:
            return None
        down = down.normalized()
        return (down.X, down.Y, down.Z)
    except Exception as error:  # noqa: BLE001 - geometry kernel can raise
        logger.debug("Accent-based down probe failed: %s", error)
        return None


def fill_sample_down(
    puzzle: Puzzle, samples: list[PathSample], indices
) -> list[PathSample]:
    """
    Return a copy of ``samples`` with "down" resolved for the given indices.

    "Down" is probed from the accent body of each sample's segment. This is the
    costly step, so callers pass only the indices they need (e.g. the samples
    involved in a candidate reversal, or all of them when drawing debug arrows).
    """
    if not indices:
        return samples

    segment_by_id = {
        (segment.main_index, segment.secondary_index): segment
        for segment in puzzle.path_architect.segments
    }

    filled = list(samples)
    for index in indices:
        sample = filled[index]
        segment = segment_by_id.get(
            (sample.segment_main_index, sample.segment_secondary_index)
        )
        if segment is None:
            continue
        down = _probe_down(segment, Vector(*sample.position))
        if down is not None:
            filled[index] = replace(sample, down=down)

    return filled


def _make_arrow_prototype() -> Part:
    """Reusable thin cone pointing along its local +Z axis."""
    with BuildPart() as arrow_builder:
        Cone(
            bottom_radius=Config.Puzzle.BALL_DIAMETER / 10,
            top_radius=0,
            height=Config.Puzzle.BALL_DIAMETER / 2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    return arrow_builder.part


def _make_arrow_prototype() -> Part:
    """Reusable thin cone pointing along its local +Z axis."""
    with BuildPart() as arrow_builder:
        Cone(
            bottom_radius=Config.Puzzle.BALL_DIAMETER / 10,
            top_radius=0,
            height=Config.Puzzle.BALL_DIAMETER / 2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    return arrow_builder.part


def _direction_arrows(samples, get_vector, color, label_prefix: str) -> list[Part]:
    """Build one cone arrow per sample, oriented along get_vector(sample)."""
    arrow_proto = _make_arrow_prototype()
    arrows: list[Part] = []
    for sample_index, sample in enumerate(samples, start=1):
        vector = get_vector(sample)
        if vector is None or vector.length == 0:
            continue
        arrow = arrow_proto.located(
            Plane(origin=Vector(*sample.position), z_dir=vector).location
        )
        arrow.label = f"{label_prefix} {sample_index}"
        arrow.color = color
        arrows.append(arrow)
    return arrows


def build_ball_roll_indicators(puzzle: Puzzle) -> list[Part]:
    """
    Debug arrows showing the marble's forward roll/travel direction.

    Red arrows along the local forward path tangent. Enabled with
    Config.Puzzle.SHOW_BALL_ROLL_INDICATORS. Diagnostic only.
    """
    if not getattr(Config.Puzzle, "SHOW_BALL_ROLL_INDICATORS", False):
        return []
    samples = build_oriented_path_samples(puzzle)
    if not samples:
        return []
    return _direction_arrows(
        samples,
        lambda sample: Vector(*sample.tangent),
        Color(1.0, 0.0, 0.0, 1.0),
        "Ball Roll",
    )


def build_ideal_gravity_indicators(puzzle: Puzzle) -> list[Part]:
    """
    Debug arrows showing the ideal gravity-down (ball-seat) direction.

    Blue arrows along the resolved profile "down"/support direction (the way the
    puzzle should be tilted so gravity seats the ball). This is the way to
    visually verify the support model that gates the hairpin warning. Enabled
    with Config.Puzzle.SHOW_IDEAL_GRAVITY_INDICATORS. Diagnostic only.

    Resolving "down" for every sample is costly (accent probe per sample), so it
    is only paid for when these arrows are requested.
    """
    if not getattr(Config.Puzzle, "SHOW_IDEAL_GRAVITY_INDICATORS", False):
        return []
    samples = build_oriented_path_samples(puzzle)
    if not samples:
        return []
    samples = fill_sample_down(puzzle, samples, range(len(samples)))
    return _direction_arrows(
        samples,
        lambda sample: Vector(*sample.down) if sample.down is not None else None,
        Color(0.0, 0.3, 1.0, 1.0),
        "Ideal Gravity",
    )


def ball_and_path_indicators(puzzle: Puzzle):
    """
    Create and return a ball, its path, and
    directional cones along that path.
    """

    ball_path_wire = build_ball_path_wire(puzzle)

    ball_path_wire.label = "Ball Path"
    ball_path_wire.color = Config.Puzzle.BALL_COLOR

    # Ball at the start
    with BuildPart() as ball:
        Sphere(Config.Puzzle.BALL_DIAMETER / 2)

    ball.part = ball.part.translate(ball_path_wire @ 0)

    ball.part.label = "Ball"
    ball.part.color = Config.Puzzle.BALL_COLOR

    # Reusable direction indicator cone
    cone_bottom_radius = Config.Puzzle.BALL_DIAMETER / 8
    cone_height = Config.Puzzle.BALL_DIAMETER / 3

    with BuildPart() as direction_indicator:
        Cone(
            bottom_radius=cone_bottom_radius,
            top_radius=0,
            height=cone_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    indicator_cone = direction_indicator.part

    # Puzzle path direction indicators, evenly spaced
    with BuildPart() as ball_path_direction:
        indicator_locations: list[Location] = []
        wire_length = ball_path_wire.length

        spacing = Config.Puzzle.NODE_SIZE * 1.5
        distance = spacing
        while distance < wire_length:
            parameter = min(1.0, distance / wire_length)
            indicator_locations.append(ball_path_wire ^ parameter)
            distance += spacing

        with Locations(*indicator_locations):
            add(indicator_cone)

    ball_path_direction.part.label = "Ball Path Direction"
    ball_path_direction.part.color = "#000000"

    return (
        ball.part,
        ball_path_wire,
        ball_path_direction.part,
    )
