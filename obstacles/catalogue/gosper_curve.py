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


class GosperCurve(Obstacle):
    """
    A Gosper (flowsnake) curve obstacle:
    - Builds a polyline via an L-system turtle at z=0
    - Centers the curve around the origin
    - Establishes entry/exit nodes based on the first/last segment directions
    - Sweeps using default profile
    """

    def __init__(self):
        super().__init__(name="Gosper Curve")

        # Gosper settings
        self.gosper_order: int = 2
        grid_multiplier = 2
        self.gosper_step: float = (2.0 * grid_multiplier * self.node_size) / math.sqrt(
            3.0
        )

        # Stop the path at certain point, optional
        self.stop_at_index: int | None = 13

        # Shortcut, optional
        self.shortcut_indices: tuple[int, int] | None = None

        # Load nodes from cache or determine
        self.load_relative_node_coords()

    def create_obstacle_geometry(self):
        """Generates the geometry for the Gosper curve obstacle (polyline + connectors)."""
        # Generate Gosper points (2D)
        program = _expand_gosper_lsystem(order=self.gosper_order)
        points_xy = _turtle_to_points_hex(
            program=program,
            step=self.gosper_step,
            start_direction_index=0,
        )

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

        if len(points_xy) < 3:
            # Safety: ensure we have at least two segments to define directions
            points_xy = [(0.0, 0.0), (self.node_size, 0.0), (2.0 * self.node_size, 0.0)]

        # Find endpoint directions for connector alignment
        start_point = points_xy[0]
        second_point = points_xy[1]
        start_dir_x, start_dir_y = _unit_direction(start_point, second_point)
        end_point = points_xy[-1]

        # Build the obstacle polyline at z = 0
        points_xyz = [(x, y, 0.0) for (x, y) in points_xy]
        with BuildPart():
            with BuildLine() as obstacle_line:
                Polyline(*points_xyz)

        self.main_path_segment.path = obstacle_line.line
        self.main_path_segment.transition_type = (
            Transition.RIGHT
        )  # Both RIGHT and ROUND work for this, TODO tbd.

        # Connectors: snap onto curve endpoints to guarantee continuity ---
        connector_length = self.node_size  # outward “lead-in/out” length

        # Entry: first node is outward from the start, second node IS the start
        entry_far_x = start_point[0] - connector_length * start_dir_x
        entry_far_y = start_point[1] - connector_length * start_dir_y
        self.entry_path_segment.nodes = [
            Node(entry_far_x, entry_far_y, 0.0, occupied=True),
            Node(start_point[0], start_point[1], 0.0, occupied=True),
        ]

        # Exit: first node is the end, second node is outward from the end,
        # intentionally made exit far horizontal, left from the final point
        exit_far_x = _round_to_nearest_multiple(
            end_point[0] - connector_length, self.node_size
        )
        exit_far_y = end_point[1]
        self.exit_path_segment.nodes = [
            Node(end_point[0], end_point[1], 0.0, occupied=True),
            Node(exit_far_x, exit_far_y, 0.0, occupied=True),
        ]

    def model_solid(self) -> Part:
        """
        Solid model of the obstacle (used for occupancy, debug, and overview).
        """
        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.main_path_segment.path)
            with BuildSketch(line.line ^ 0):
                add(self.default_path_profile_type())
            sweep(transition=self.main_path_segment.transition_type)

        obstacle.part.label = f"{self.name} Obstacle Solid"
        return obstacle.part


# Register the obstacle
register_obstacle("Gosper Curve", GosperCurve)


if __name__ == "__main__":
    # Create
    obstacle = GosperCurve()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
