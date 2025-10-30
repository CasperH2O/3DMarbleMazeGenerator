# obstacles/catalogue/gosper_curve.py

from __future__ import annotations

import math
from typing import Iterable, List, Tuple

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Part,
    Polyline,
    Transition,
    add,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle
from puzzle.node import Node
from puzzle.utils.enums import ObstacleType


def _apply_index_range(
    points_xy: List[Tuple[float, float]],
    start_index: int | None,
    end_index: int | None,
) -> List[Tuple[float, float]]:
    """
    If both indices are provided, return the contiguous slice
    points_xy[start_index : end_index + 1] (inclusive).

    - Indices are clamped to [0, len(points) - 1]
    - If start_index > end_index, the slice is reversed so the path flows
      from 'start' to 'end'
    - If start_index == end_index, we try to extend to a neighbor so that the
      result has at least 2 points (when possible)
    - Consecutive duplicates are removed
    """
    if start_index is None or end_index is None:
        return points_xy
    if not points_xy:
        return points_xy

    total = len(points_xy)
    start_index = max(0, min(start_index, total - 1))
    end_index = max(0, min(end_index, total - 1))

    if start_index == end_index:
        if end_index + 1 < total:
            end_index += 1
        elif start_index - 1 >= 0:
            start_index -= 1
        else:
            # Single point only; let downstream safety handle it
            return [points_xy[start_index]]

    if start_index <= end_index:
        subpath = points_xy[start_index : end_index + 1]
    else:
        subpath = list(reversed(points_xy[end_index : start_index + 1]))

    return _deduplicate_consecutive_points_2d(subpath)


def _apply_shortcut_by_indices(
    points_xy: List[Tuple[float, float]],
    start_index: int,
    end_index: int,
) -> List[Tuple[float, float]]:
    """
    Replace the section (start_index+1 .. end_index-1) with a single straight segment
    from points_xy[start_index] directly to points_xy[end_index].

    Indices are zero-based. For example, (3, 20) keeps:
        points_xy[0], points_xy[1], points_xy[2], points_xy[3],
        -> direct segment ->
        points_xy[20], points_xy[21], ..., points_xy[-1]

    Validations:
    - 0 <= start_index < end_index < len(points_xy)
    - If end_index == start_index + 1, nothing changes (already a direct neighbor).
    """
    total = len(points_xy)
    if total < 2:
        raise ValueError("Not enough points to apply a shortcut.")

    if start_index < 0 or end_index < 0:
        raise ValueError("Shortcut indices must be non-negative.")
    if start_index >= total or end_index >= total:
        raise ValueError(
            f"Shortcut indices out of range: 0..{total - 1} allowed, got {start_index}..{end_index}"
        )
    if start_index >= end_index:
        raise ValueError(
            f"Shortcut requires start_index < end_index, got {start_index} >= {end_index}"
        )

    # If they are consecutive, there is nothing to collapse.
    if end_index == start_index + 1:
        return points_xy[:]

    # Keep everything up to start_index (inclusive), then jump to end_index onward.
    new_points = points_xy[: start_index + 1] + points_xy[end_index:]
    return new_points


def _apply_stop_at_index(
    stop_at_index: int, points_xy: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """
    If stop_at_index is set, truncate the path at that index (inclusive).
    This runs BEFORE shortcut application.

    Several value checks to prevent issues.
    """
    if stop_at_index is None:
        return points_xy

    if stop_at_index < 0:
        raise ValueError("stop_at_index must be >= 0")

    if not points_xy:
        return points_xy

    last_index = len(points_xy) - 1
    stop_index = min(stop_at_index, last_index)

    truncated = points_xy[: stop_index + 1]
    return _deduplicate_consecutive_points_2d(truncated)


def _expand_gosper_lsystem(order: int) -> str:
    """
    Expand the Gosper curve (flowsnake) L-system to a command string.

    Grammar (one of the standard Gosper variants):
      Axiom: "A"
      Angle: 60°
      Rules:
        A -> A-B--B+A++AA+B-
        B -> +A-BB--B-A++A+B

    We interpret:
      'A' and 'B' as "move forward"
      '+' as "turn left  60°"
      '-' as "turn right 60°"
    """
    current = "A"
    for _ in range(order):
        next_symbols: List[str] = []
        for symbol in current:
            if symbol == "A":
                next_symbols.append("A-B--B+A++AA+B-")
            elif symbol == "B":
                next_symbols.append("+A-BB--B-A++A+B")
            else:
                next_symbols.append(symbol)
        current = "".join(next_symbols)
    return current


def _center_points(points_xy: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Translate all points so that the bounding box center becomes (0, 0).
    """
    xs = [x for x, _ in points_xy]
    ys = [y for _, y in points_xy]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    center_x = 0.5 * (min_x + max_x)
    center_y = 0.5 * (min_y + max_y)
    return [(x - center_x, y - center_y) for x, y in points_xy]


def _deduplicate_consecutive_points_2d(
    points_xy: Iterable[Tuple[float, float]],
    epsilon: float = 1e-9,
) -> List[Tuple[float, float]]:
    """
    Remove consecutive duplicates (within epsilon) to keep Polyline clean.
    """
    cleaned: List[Tuple[float, float]] = []
    last_x: float | None = None
    last_y: float | None = None
    for x, y in points_xy:
        if last_x is None or abs(x - last_x) > epsilon or abs(y - last_y) > epsilon:
            cleaned.append((x, y))
            last_x, last_y = x, y
    return cleaned


def _unit_direction(
    a: Tuple[float, float], b: Tuple[float, float]
) -> Tuple[float, float]:
    """
    Return the unit vector from point a to point b.
    Falls back to (1, 0) if the length is essentially zero.
    """
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    length = math.hypot(dx, dy)
    if length <= 1e-12:
        return (1.0, 0.0)
    return (dx / length, dy / length)


def _round_to_nearest_multiple(value: float, multiple: float) -> float:
    """
    Round 'value' to the nearest multiple of 'multiple' using half-up behavior
    (i.e., 0.5 goes up). Works for negative values as well.
    """
    if multiple == 0.0:
        return value
    ratio = value / multiple
    if ratio >= 0.0:
        return multiple * math.floor(ratio + 0.5)
    return -multiple * math.floor(-ratio + 0.5)


def _translate_points(
    points_xy: List[Tuple[float, float]],
    delta_x: float,
    delta_y: float,
) -> List[Tuple[float, float]]:
    """Uniformly translate all points by (delta_x, delta_y)."""
    return [(x + delta_x, y + delta_y) for (x, y) in points_xy]


def _turtle_to_points_hex(
    program: str,
    step: float,
    start_direction_index: int = 0,
) -> List[Tuple[float, float]]:
    """
    Execute the L-system using a fixed 6-direction hex lattice to minimize
    floating-point drift vs. repeatedly calling cos/sin.

    - Starts at (0, 0)
    - start_direction_index is modulo 6 and uses HEX_DIRS above
    - 'A' and 'B' move forward one 'step'
    - '+' turn left  60° (next direction)
    - '-' turn right 60° (previous direction)
    """

    SQRT3: float = math.sqrt(3.0)
    HEX_DIRS: list[tuple[float, float]] = [
        (1.0, 0.0),  # 0°   (east)
        (0.5, SQRT3 / 2.0),  # 60°
        (-0.5, SQRT3 / 2.0),  # 120°
        (-1.0, 0.0),  # 180°
        (-0.5, -SQRT3 / 2.0),  # 240°
        (0.5, -SQRT3 / 2.0),  # 300°
    ]

    direction_index: int = start_direction_index % 6
    current_x: float = 0.0
    current_y: float = 0.0
    points_xy: List[Tuple[float, float]] = [(current_x, current_y)]

    for symbol in program:
        if symbol == "+":
            direction_index = (direction_index + 1) % 6
        elif symbol == "-":
            direction_index = (direction_index - 1) % 6
        elif symbol in ("A", "B"):
            delta_x, delta_y = HEX_DIRS[direction_index]
            current_x += step * delta_x
            current_y += step * delta_y
            points_xy.append((current_x, current_y))
        else:
            continue

    return points_xy


def _snap_y_axis_if_close(
    points_xy: list[tuple[float, float]],
    grid: float,
    tolerance: float = 1e-9,
) -> list[tuple[float, float]]:
    """
    Snap coordinates on a single axis to the nearest Y grid multiple of
    the value is already extremely close. Use 'axis="y"' here.
    """
    out: list[tuple[float, float]] = []
    for x_val, y_val in points_xy:
        nearest = round(y_val / grid) * grid
        if abs(y_val - nearest) <= tolerance * max(1.0, abs(y_val)):
            y_val = nearest
        out.append((x_val, y_val))
    return out


def _snap_start_to_grid_by_translation(
    points_xy: List[Tuple[float, float]],
    grid_size: float,
) -> List[Tuple[float, float]]:
    """
    Snap the *start* point (points_xy[0]) to a grid multiple of 'grid_size' by
    translating the entire curve so geometry stays intact.
    """
    if not points_xy:
        return points_xy

    start_x, start_y = points_xy[0]

    snapped_x = _round_to_nearest_multiple(start_x, grid_size)
    snapped_y = _round_to_nearest_multiple(start_y, grid_size)

    delta_x = snapped_x - start_x
    delta_y = snapped_y - start_y
    if abs(delta_x) < 1e-12 and abs(delta_y) < 1e-12:
        return points_xy

    return _translate_points(points_xy, delta_x, delta_y)


def _horizontal_connector_farpoint(
    anchor_xy: tuple[float, float],
    direction_unit_xy: tuple[float, float],
    length: float,
    is_entry: bool,
    grid_size: float | None = None,
    snap_to_grid: bool = True,
) -> tuple[float, float]:
    """
    Compute a far-point for an entry/exit connector that is guaranteed to be horizontal.

    Rules:
      - Keep y the same as the anchor (purely horizontal segment).
      - Choose left/right based on the sign of the local path's dx.
      - Entry goes opposite the path direction; exit goes along the path.
      - If dx is ~0 (vertical tangent), use a deterministic fallback:
            entry -> left  (-x), exit -> right (+x).
      - Optionally snap far_x to the nearest node grid multiple.

    Returns:
        (far_x, far_y)
    """
    anchor_x, anchor_y = anchor_xy
    direction_unit_x, _direction_unit_y = direction_unit_xy

    # Entry goes opposite; exit goes along the path
    along_sign = 1.0 if not is_entry else -1.0

    # Horizontal sign from local dx; robust fallback when nearly zero
    if abs(direction_unit_x) <= 1e-12:
        direction_sign = (
            -1.0 if is_entry else 1.0
        )  # entry left, exit right (deterministic)
    else:
        direction_sign = 1.0 if direction_unit_x >= 0.0 else -1.0

    step = along_sign * direction_sign * length
    far_x = anchor_x + step
    far_y = anchor_y

    if snap_to_grid and grid_size:
        far_x = _round_to_nearest_multiple(far_x, grid_size)

    return (far_x, far_y)


class GosperCurve(Obstacle):
    """
    A Gosper (flowsnake) curve obstacle:
    - Builds a polyline via an L-system turtle at z=0
    - Centers the curve around the origin
    - Establishes entry/exit nodes based on the first/last segment directions
    - Sweeps using default profile
    """

    def __init__(self):
        # Name may be updated by presets via apply_preset()
        super().__init__(name="Gosper Curve")

        # Optional inclusive index range on the raw point list
        # If both are None, disabled.
        self.curve_index_range: tuple[int | None, int | None] = (None, None)

        # Optional truncate at index (only used when no range is set)
        self.stop_at_index: int | None = None

        # Optional shortcut (keep up to i, jump to j..end)
        self.shortcut_indices: tuple[int, int] | None = None

        # Allow subclasses obstacle with own name and parameters before cache/load nodes
        self.apply_preset()

        # Load nodes from cache or determine
        self.load_relative_node_coords()

    def apply_preset(self) -> None:
        """
        Hook for subclasses to tweak settings
        """
        pass

    def create_obstacle_geometry(self):
        """Generates the geometry for the Gosper curve obstacle (polyline + connectors)."""
        # Generate Gosper points (2D)
        program = _expand_gosper_lsystem(order=2)
        grid_multiplier = 2
        gosper_step: float = (2.0 * grid_multiplier * self.node_size) / math.sqrt(3.0)
        points_xy = _turtle_to_points_hex(
            program=program,
            step=gosper_step,
            start_direction_index=0,
        )

        # Apply explicit index range, optionally; when active, it supersedes stop at index.
        start_index, end_index = self.curve_index_range
        if start_index is not None and end_index is not None:
            points_xy = _apply_index_range(points_xy, start_index, end_index)
        else:
            # Stop path, optional
            points_xy = _apply_stop_at_index(
                stop_at_index=self.stop_at_index, points_xy=points_xy
            )

        # Shortcut, optional
        if self.shortcut_indices is not None:
            start_index, end_index = self.shortcut_indices
            points_xy = _apply_shortcut_by_indices(points_xy, start_index, end_index)

        # Remove duplicate points
        points_xy = _deduplicate_consecutive_points_2d(points_xy)

        # Center based on the remaining points
        if points_xy:
            points_xy = _center_points(points_xy)

        # Snap the start of the curve to the nearest node grid, accordingly translate all points
        if points_xy:
            points_xy = _snap_start_to_grid_by_translation(
                points_xy=points_xy, grid_size=self.node_size
            )

        # Snap and round Y values to nearest grid interval
        points_xy = _snap_y_axis_if_close(
            points_xy=points_xy,
            grid=self.node_size,
            tolerance=1e-9,
        )

        # Safety: ensure we have at least two segments to define directions
        if len(points_xy) < 3:
            points_xy = [(0.0, 0.0), (self.node_size, 0.0), (2.0 * self.node_size, 0.0)]

        # Determine tangents at start and end
        start_point = points_xy[0]
        second_point = points_xy[1]
        start_dir_x, start_dir_y = _unit_direction(start_point, second_point)

        end_point = points_xy[-1]
        second_last_point = points_xy[-2]
        end_dir_x, end_dir_y = _unit_direction(second_last_point, end_point)

        # Determine extension coordinates for original geometry
        connector_length = self.node_size
        entry_far_x, entry_far_y = _horizontal_connector_farpoint(
            anchor_xy=(start_point[0], start_point[1]),
            direction_unit_xy=(start_dir_x, start_dir_y),
            length=connector_length,
            is_entry=True,
            grid_size=self.node_size,
            snap_to_grid=True,
        )
        exit_far_x, exit_far_y = _horizontal_connector_farpoint(
            anchor_xy=(end_point[0], end_point[1]),
            direction_unit_xy=(end_dir_x, end_dir_y),
            length=connector_length,
            is_entry=False,
            grid_size=self.node_size,
            snap_to_grid=True,
        )

        # Extend original geometry points so it starts and ends horizontally
        points_xy_with_connectors = (
            [(entry_far_x, entry_far_y)] + points_xy + [(exit_far_x, exit_far_y)]
        )
        points_xy_with_connectors = _deduplicate_consecutive_points_2d(
            points_xy_with_connectors
        )

        # Build the main polyline
        points_xyz = [(x, y, 0.0) for (x, y) in points_xy_with_connectors]
        with BuildPart():
            with BuildLine() as obstacle_line:
                Polyline(*points_xyz)

        self.main_path_segment.path = obstacle_line.line
        self.main_path_segment.transition_type = Transition.RIGHT

        # Extend again to form external entry/exit segments
        # The new main-path endpoints are these two nodes:
        new_main_start_xy = (entry_far_x, entry_far_y)
        new_main_end_xy = (exit_far_x, exit_far_y)

        # Entry segment, determine direction and extend
        entry_farther_x, entry_farther_y = _horizontal_connector_farpoint(
            anchor_xy=new_main_start_xy,
            direction_unit_xy=(start_dir_x, start_dir_y),
            length=connector_length,
            is_entry=True,
            grid_size=self.node_size,
            snap_to_grid=True,
        )

        self.entry_path_segment.nodes = [
            Node(entry_farther_x, entry_farther_y, 0.0, occupied=True),
            Node(new_main_start_xy[0], new_main_start_xy[1], 0.0, occupied=True),
        ]
        self.entry_path_segment.transition_type = Transition.RIGHT

        # Exit segment, determine direction and extend
        exit_farther_x, exit_farther_y = _horizontal_connector_farpoint(
            anchor_xy=new_main_end_xy,
            direction_unit_xy=(end_dir_x, end_dir_y),
            length=connector_length,
            is_entry=False,
            grid_size=self.node_size,
            snap_to_grid=True,
        )

        self.exit_path_segment.nodes = [
            Node(new_main_end_xy[0], new_main_end_xy[1], 0.0, occupied=True),
            Node(exit_farther_x, exit_farther_y, 0.0, occupied=True),
        ]
        self.exit_path_segment.transition_type = Transition.RIGHT

    def model_solid(self) -> Part:
        """
        Solid model of the obstacle (used for occupancy, debug, and overview).
        """
        self._ensure_entry_exit_paths()

        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.entry_path_segment.path)
                add(self.main_path_segment.path)
                add(self.exit_path_segment.path)
            with BuildSketch(line.line ^ 0):
                add(self.default_path_profile_type())
            sweep(transition=self.main_path_segment.transition_type)

        obstacle.part.label = f"{self.name} Obstacle Solid"
        return obstacle.part


# Gospers
class GosperCurveFull(GosperCurve):
    def apply_preset(self) -> None:
        # A full order-2 curve, no truncation, no shortcut
        self.name = "Gosper Curve - Full"


class GosperCurveRange1to4(GosperCurve):
    def apply_preset(self) -> None:
        # Only render indices [1..4], inclusive
        self.name = ObstacleType.GOSPER_CURVE_RANGE_1_TO_4.value
        self.curve_index_range = (1, 4)


class GosperCurverRange6to10(GosperCurve):
    def apply_preset(self) -> None:
        # Only render indices [6..10], inclusive
        self.name = ObstacleType.GOSPER_CURVE_RANGE_6_TO_10.value
        self.curve_index_range = (6, 10)


class GosperCurverRange11to15(GosperCurve):
    def apply_preset(self) -> None:
        # Only render indices [11..15], inclusive
        self.name = ObstacleType.GOSPER_CURVE_RANGE_11_TO_15.value
        self.curve_index_range = (11, 15)


# Register the obstacle(s)
register_obstacle(ObstacleType.GOSPER_CURVE_RANGE_1_TO_4.value, GosperCurveRange1to4)
register_obstacle(ObstacleType.GOSPER_CURVE_RANGE_6_TO_10.value, GosperCurverRange6to10)
register_obstacle(
    ObstacleType.GOSPER_CURVE_RANGE_11_TO_15.value, GosperCurverRange11to15
)

if __name__ == "__main__":
    # Create
    obstacle = GosperCurveRange1to4()

    # Visualization
    # obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
