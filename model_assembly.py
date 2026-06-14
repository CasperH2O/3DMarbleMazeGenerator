# model_assembly.py

from assembly.casing import merge_standard_paths_with_case, puzzle_casing
from assembly.exporting import export_all
from assembly.pathing import (
    ball_and_path_indicators,
    build_ball_roll_indicators,
    build_gravity_warning_spheres,
    build_ideal_gravity_indicators,
    build_obstacle_path_body_extras,
    path,
)
from assembly.viewer import display_parts, set_viewer
from config import Config
from puzzle.puzzle import Puzzle


def build_components(puzzle: Puzzle):
    """Construct parts and paths for the provided puzzle."""

    case_parts, base_parts, cut_shape = puzzle_casing()
    standard_paths, support_path, coloring_path = path(puzzle, cut_shape)
    obstacle_extras = build_obstacle_path_body_extras(puzzle)
    gravity_warning_spheres = build_gravity_warning_spheres(puzzle)
    ball_roll_indicators = build_ball_roll_indicators(puzzle)
    ideal_gravity_indicators = build_ideal_gravity_indicators(puzzle)
    ball, ball_path, ball_path_direction = ball_and_path_indicators(puzzle)

    merge_standard_paths_with_case(case_parts, standard_paths or [])

    return (
        case_parts,
        base_parts,
        standard_paths,
        support_path,
        coloring_path,
        obstacle_extras,
        gravity_warning_spheres,
        ball_roll_indicators,
        ideal_gravity_indicators,
        ball,
        ball_path,
        ball_path_direction,
    )


def export_components(puzzle: Puzzle, apply_manufacturing_preparation: bool = True) -> str | None:
    """Export STL files for the puzzle when enabled in configuration.

    Args:
        puzzle: The puzzle to export.
        apply_manufacturing_preparation: If True, apply rotations and other tweaks for optimal 3D printing.
                                        If False, export in original model orientation (for visualization).
    """

    (
        case_parts,
        base_parts,
        standard_paths,
        support_path,
        coloring_path,
        *_,
    ) = build_components(puzzle)

    additional_parts = [standard_paths, support_path, coloring_path]

    return export_all(case_parts, base_parts, additional_parts, apply_manufacturing_preparation)


def main() -> None:
    """Generate the puzzle, assemble its parts, and export printable models."""
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=Config.Puzzle.CASE_SHAPE,
    )

    (
        case_parts,
        base_parts,
        standard_paths,
        support_path,
        coloring_path,
        obstacle_extras,
        gravity_warning_spheres,
        ball_roll_indicators,
        ideal_gravity_indicators,
        ball,
        ball_path,
        ball_path_direction,
    ) = build_components(puzzle)

    display_parts(
        case_parts,
        base_parts,
        standard_paths,
        support_path,
        coloring_path,
        obstacle_extras,
        gravity_warning_spheres,
        ball_roll_indicators,
        ideal_gravity_indicators,
        ball,
        ball_path,
        ball_path_direction,
    )

    set_viewer()

    additional_parts = [
        standard_paths,
        support_path,
        coloring_path,
    ]

    export_all(case_parts, base_parts, additional_parts)


if __name__ == "__main__":
    main()
