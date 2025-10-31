# obstacles/catalogue/signal_generator.py

from __future__ import annotations

import logging
import math
from typing import Iterable, Tuple

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

from logging_config import configure_logging
from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle
from puzzle.node import Node
from puzzle.utils.enums import ObstacleType

configure_logging()
logger = logging.getLogger(__name__)


def _center_points(points_xy: list[Tuple[float, float]]) -> list[Tuple[float, float]]:
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
) -> list[Tuple[float, float]]:
    """
    Remove consecutive duplicates (within epsilon) to keep Polyline clean.
    """
    cleaned: list[Tuple[float, float]] = []
    last_x: float | None = None
    last_y: float | None = None
    for x, y in points_xy:
        if last_x is None or abs(x - last_x) > epsilon or abs(y - last_y) > epsilon:
            cleaned.append((x, y))
            last_x, last_y = x, y
    return cleaned


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
    points_xy: list[Tuple[float, float]],
    delta_x: float,
    delta_y: float,
) -> list[Tuple[float, float]]:
    """Uniformly translate all points by (delta_x, delta_y)."""
    return [(x + delta_x, y + delta_y) for (x, y) in points_xy]


def _snap_start_to_grid_by_translation(
    points_xy: list[Tuple[float, float]],
    grid_size: float,
) -> list[Tuple[float, float]]:
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


import math
from typing import List, Tuple

# --- Point generators ---------------------------------------------------------


def _generate_zig_zag_points(
    amplitude: float,
    period_length: float,
    cycles: int,
    start_at_peak: bool = False,
    start_direction_up: bool = True,
    vertical_offset: float = 0.0,
) -> list[Tuple[float, float]]:
    """
    Generate a triangle wave (zig-zag) with exact linear segments.
    The wave ranges from -amplitude to +amplitude (peak-to-peak = 2 * amplitude).

    Parameters
    ----------
    amplitude : float
        Half of peak-to-peak height. Output y will be in [-amplitude, +amplitude] plus vertical_offset.
    period_length : float
        Length along X for one full cycle.
    cycles : int
        Number of full cycles to generate.
    start_at_peak : bool
        If True, start exactly at a peak (+/- amplitude) instead of a slope mid-edge.
    start_direction_up : bool
        Initial slope direction. Only relevant when start_at_peak=True. If False, first slope goes down.
    vertical_offset : float
        Offset added to all Y values.

    Returns
    -------
    list[Tuple[float, float]]
        XY vertices suitable for a Polyline. Uses 3 points per period (start, mid-peak, end),
        plus an initial extra point if starting at a peak.
    """
    points_xy: list[Tuple[float, float]] = []

    # Local helpers to append without duplicating consecutive points
    def _append_point(x: float, y: float):
        nonlocal points_xy
        if points_xy and points_xy[-1] == (x, y):
            return
        points_xy.append((x, y))

    # Decide starting Y and the first half-cycle direction
    x_cursor = 0.0
    if start_at_peak:
        start_y = (amplitude if start_direction_up else -amplitude) + vertical_offset
        _append_point(x_cursor, start_y)
        # From peak we go to the opposite peak in half a period
        half_period = period_length * 0.5
        next_y = (-amplitude if start_direction_up else amplitude) + vertical_offset
        x_cursor += half_period
        _append_point(x_cursor, next_y)
        # Complete the period returning to the starting peak
        x_cursor += half_period
        _append_point(x_cursor, start_y)
        # We already created 1 cycle above. Reduce remaining cycles by one.
        remaining_cycles = max(0, cycles - 1)
        # Subsequent cycles just alternate peaks each half period
        for _ in range(remaining_cycles):
            # half up
            x_cursor += half_period
            _append_point(x_cursor, next_y)
            # half down
            x_cursor += half_period
            _append_point(x_cursor, start_y)
        return points_xy

    # Start on a slope at the minimum y, go up first (canonical triangle)
    # Start at (x=0, y=-A) -> (x=period/2, y=+A) -> (x=period, y=-A) for each period
    start_y = -amplitude + vertical_offset
    peak_y = +amplitude + vertical_offset
    end_y = start_y

    for cycle_index in range(cycles):
        period_start_x = cycle_index * period_length
        mid_x = period_start_x + (period_length * 0.5)
        end_x = period_start_x + period_length

        if cycle_index == 0:
            _append_point(period_start_x, start_y)  # start of the very first period
        _append_point(mid_x, peak_y)  # mid-peak
        _append_point(end_x, end_y)  # period end

    return points_xy


def _generate_sine_points(
    amplitude: float,
    period_length: float,
    cycles: int,
    samples_per_period: int = 64,
    phase_radians: float = 0.0,
    vertical_offset: float = 0.0,
) -> list[Tuple[float, float]]:
    """
    Generate a sine wave by sampling.

    y(x) = vertical_offset + amplitude * sin(2π * x / period_length + phase)

    Parameters
    ----------
    amplitude : float
        Half of peak-to-peak height.
    period_length : float
        Length along X for one full cycle.
    cycles : int
        Number of full cycles to generate.
    samples_per_period : int
        Number of sample points per full cycle (>= 2). Higher = smoother.
    phase_radians : float
        Phase shift applied to the sine in radians.
    vertical_offset : float
        Offset added to all Y values.

    Returns
    -------
    list[Tuple[float, float]]
        Sampled sine points from x=0 to x=cycles*period_length inclusive.
    """
    if samples_per_period < 2:
        samples_per_period = 2

    total_periods_length = cycles * period_length
    total_samples = cycles * samples_per_period

    # Include the last point (end of the last cycle)
    points_xy: list[Tuple[float, float]] = []
    for sample_index in range(total_samples + 1):
        # Compactly: x
        x = sample_index * (period_length / samples_per_period)
        y = vertical_offset + amplitude * math.sin(
            (2.0 * math.pi * x / period_length) + phase_radians
        )
        points_xy.append((x, y))

    # Guard for floating rounding to avoid tiny spillover after the last sample
    if points_xy[-1][0] > total_periods_length:
        points_xy[-1] = (total_periods_length, points_xy[-1][1])

    return points_xy


def _generate_pulse_points(
    amplitude: float,
    period_length: float,
    cycles: int,
    duty_cycle: float = 0.5,
    vertical_offset: float = 0.0,
    start_high: bool = True,
) -> list[Tuple[float, float]]:
    """
    Generate a square/pulse wave with crisp vertical transitions.

    Parameters
    ----------
    amplitude : float
        Half of peak-to-peak height. High = +amplitude, Low = -amplitude (both plus vertical_offset).
    period_length : float
        Length along X for one full cycle.
    cycles : int
        Number of full cycles to generate.
    duty_cycle : float
        Fraction of the period spent HIGH in [0, 1]. 0.5 = symmetric square.
    vertical_offset : float
        Offset added to all Y values.
    start_high : bool
        If True, the first state is HIGH; otherwise LOW.

    Returns
    -------
    list[Tuple[float, float]]
        XY vertices with only the corners and transitions (minimal points).
    """
    if duty_cycle < 0.0:
        duty_cycle = 0.0
    if duty_cycle > 1.0:
        duty_cycle = 1.0

    high_y = +amplitude + vertical_offset
    low_y = -amplitude + vertical_offset

    points_xy: list[Tuple[float, float]] = []

    def _append_point(x: float, y: float):
        nonlocal points_xy
        if points_xy and points_xy[-1] == (x, y):
            return
        points_xy.append((x, y))

    for cycle_index in range(cycles):
        period_start_x = cycle_index * period_length
        transition_x = period_start_x + duty_cycle * period_length
        period_end_x = period_start_x + period_length

        # Determine level order for this cycle
        first_level_y = high_y if start_high else low_y
        second_level_y = low_y if start_high else high_y

        # Start edge
        if cycle_index == 0:
            _append_point(period_start_x, first_level_y)
        else:
            # At new period start, ensure continuity with previous end level
            # If the previous end level equals first_level_y, only add the X change; else add a vertical edge.
            last_y = points_xy[-1][1]
            if last_y != first_level_y:
                _append_point(period_start_x, last_y)  # vertical start
                _append_point(period_start_x, first_level_y)

        # Transition edge within the period (vertical change)
        _append_point(transition_x, first_level_y)
        _append_point(transition_x, second_level_y)

        # Period end at constant level
        _append_point(period_end_x, second_level_y)

    return points_xy


class SignalGenerator(Obstacle):
    """
    A signal generator base clase to create various signal shaped obstacles
    """

    def __init__(self):
        # Name may be updated by presets via apply_preset()
        super().__init__(name="Signal Generator")
        self.signal_type = None

        # --- Common signal parameters (can be overridden by presets/subclasses)
        self.amplitude: float = self.node_size * 1.0  # half of peak-to-peak
        self.period_length: float = self.node_size * 6.0
        self.cycles: int = 2

        # Sine-specific
        self.samples_per_period: int = 64
        self.phase_radians: float = 0.0
        self.vertical_offset: float = 0.0

        # Pulse-specific
        self.duty_cycle: float = 0.5
        self.start_high: bool = True

        # Zig-zag-specific
        self.zigzag_start_at_peak: bool = False
        self.zigzag_start_direction_up: bool = True

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
        """Generates the geometry for the obstacle (polyline + connectors)."""

        # TODO Generate points based on types
        points_xy: list[Tuple[float, float]] | None = None
        if self.signal_type == ObstacleType.ZIG_ZAG.value:
            points_xy = _generate_zig_zag_points(
                amplitude=self.amplitude,
                period_length=self.period_length,
                cycles=self.cycles,
                start_at_peak=self.zigzag_start_at_peak,
                start_direction_up=self.zigzag_start_direction_up,
                vertical_offset=self.vertical_offset,
            )
        elif self.signal_type == ObstacleType.SINE.value:
            points_xy = _generate_sine_points(
                amplitude=self.amplitude,
                period_length=self.period_length,
                cycles=self.cycles,
                samples_per_period=self.samples_per_period,
                phase_radians=self.phase_radians,
                vertical_offset=self.vertical_offset,
            )
        elif self.signal_type == ObstacleType.PULSE.value:
            points_xy = _generate_pulse_points(
                amplitude=self.amplitude,
                period_length=self.period_length,
                cycles=self.cycles,
                duty_cycle=self.duty_cycle,
                vertical_offset=self.vertical_offset,
                start_high=self.start_high,
            )
        else:
            logging.warning("Unsupported signal type: %s", self.signal_type)

        # Remove duplicate points # TODO Determine if really required
        points_xy = _deduplicate_consecutive_points_2d(points_xy or [])

        # Center based on the remaining points
        if points_xy:
            points_xy = _center_points(points_xy)

        # Snap the start of the curve to the nearest node grid, accordingly translate all points
        if points_xy:
            points_xy = _snap_start_to_grid_by_translation(
                points_xy=points_xy, grid_size=self.node_size
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


class ZigZag(SignalGenerator):
    def apply_preset(self) -> None:
        self.name = ObstacleType.ZIG_ZAG.value
        self.signal_type = ObstacleType.ZIG_ZAG.value
        # Example preset tuning (optional):
        # self.cycles = 3
        # self.period_length = self.node_size * 5.0


class Sine(SignalGenerator):
    def apply_preset(self) -> None:
        self.name = ObstacleType.SINE.value
        self.signal_type = ObstacleType.SINE.value
        # self.samples_per_period = 96


class Pulse(SignalGenerator):
    def apply_preset(self) -> None:
        self.name = ObstacleType.PULSE.value
        self.signal_type = ObstacleType.PULSE.value
        # self.duty_cycle = 0.4
        # self.start_high = True


# Register the obstacle(s)
register_obstacle(ObstacleType.ZIG_ZAG.value, ZigZag)
register_obstacle(ObstacleType.SINE.value, Sine)
register_obstacle(ObstacleType.PULSE.value, Pulse)

if __name__ == "__main__":
    # Create
    obstacle = Pulse()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
