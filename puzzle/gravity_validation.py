# puzzle/gravity_validation.py

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from config import PathProfileType
from puzzle.node import Node

if TYPE_CHECKING:
    from cad.path_segment import PathSegment


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
    profile_type: PathProfileType
    node: Node
    reason: str
    movement_pattern: str

    @property
    def segment_label(self) -> str:
        """Return the segment index in the same main.secondary format used elsewhere."""
        return f"{self.segment_main_index}.{self.segment_secondary_index}"


OPEN_PROFILE_TYPES = {
    PathProfileType.U_SHAPE,
    PathProfileType.U_SHAPE_ADJUSTED_HEIGHT,
    PathProfileType.U_SHAPE_PATH_COLOR,
    PathProfileType.L_SHAPE,
    PathProfileType.L_SHAPE_ADJUSTED_HEIGHT,
    PathProfileType.L_SHAPE_PATH_COLOR,
    PathProfileType.L_SHAPE_MIRRORED,
    PathProfileType.L_SHAPE_MIRRORED_ADJUSTED_HEIGHT,
    PathProfileType.L_SHAPE_MIRRORED_PATH_COLOR,
    PathProfileType.V_SHAPE,
    PathProfileType.V_SHAPE_PATH_COLOR,
}

CLOSED_PROFILE_TYPES = {
    PathProfileType.O_SHAPE,
    PathProfileType.O_SHAPE_SUPPORT,
    PathProfileType.SQUARE_CLOSED_SHAPE,
    PathProfileType.SQUARE_WITH_HOLE_SHAPE,
}


def is_open_profile(profile_type: PathProfileType | None) -> bool:
    """Return True when a profile can expose the marble to gravity-related escape/trap risk."""
    if profile_type is None:
        return False
    if profile_type in CLOSED_PROFILE_TYPES:
        return False
    return profile_type in OPEN_PROFILE_TYPES


def _classify_vertical_delta(delta_z: float, significant_delta: float) -> str:
    if delta_z <= -significant_delta:
        return "down"
    if delta_z >= significant_delta:
        return "up"
    return "level"


def _issue_at_node(
    *,
    segment: "PathSegment",
    node: Node,
    reason: str,
    movement_pattern: str,
) -> GravityIssue:
    return GravityIssue(
        severity=GravityIssueSeverity.WARNING,
        segment_main_index=segment.main_index,
        segment_secondary_index=segment.secondary_index,
        profile_type=segment.path_profile_type,
        node=node,
        reason=reason,
        movement_pattern=movement_pattern,
    )


def detect_gravity_warning_issues(
    segments: list["PathSegment"],
    node_size: float,
) -> list[GravityIssue]:
    """
    Detect early gravity-playability warnings for route/profile combinations.

    This first-pass validator is deliberately conservative: it does not reject a
    model and does not try to prove full physical impossibility. Instead, it
    highlights locations where an open path profile combines with vertical route
    patterns that are likely to let the ball escape, stall, or become trapped.
    """
    significant_delta = max(node_size * 0.25, 1e-6)
    issues: list[GravityIssue] = []
    seen_issue_keys: set[tuple[int, int, float, float, float, str]] = set()

    def append_issue(issue: GravityIssue) -> None:
        issue_key = (
            issue.segment_main_index,
            issue.segment_secondary_index,
            round(issue.node.x, 6),
            round(issue.node.y, 6),
            round(issue.node.z, 6),
            issue.movement_pattern,
        )
        if issue_key in seen_issue_keys:
            return
        seen_issue_keys.add(issue_key)
        issues.append(issue)

    for segment in segments:
        if segment.is_obstacle or not is_open_profile(segment.path_profile_type):
            continue

        nodes = segment.nodes
        if len(nodes) < 2:
            continue

        vertical_steps = [
            _classify_vertical_delta(
                nodes[index + 1].z - nodes[index].z,
                significant_delta,
            )
            for index in range(len(nodes) - 1)
        ]

        for index in range(len(vertical_steps) - 1):
            current_step = vertical_steps[index]
            next_step = vertical_steps[index + 1]
            pattern = f"{current_step}-{next_step}"

            if current_step == "down" and next_step == "down":
                append_issue(
                    _issue_at_node(
                        segment=segment,
                        node=nodes[index + 2],
                        reason=(
                            "Open path profile follows two consecutive downward "
                            "moves; the marble may be carried out of the playable channel."
                        ),
                        movement_pattern=pattern,
                    )
                )
            elif current_step == "down" and next_step == "up":
                append_issue(
                    _issue_at_node(
                        segment=segment,
                        node=nodes[index + 1],
                        reason=(
                            "Open path profile forms a local low point before the "
                            "route climbs again; the marble may stall or become trapped."
                        ),
                        movement_pattern=pattern,
                    )
                )

    return issues
