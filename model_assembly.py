# model_assembly.py

from assembly.casing import merge_standard_paths_with_case, puzzle_casing
from assembly.exporting import export_all
from assembly.pathing import (
    ball_and_path_indicators,
    build_obstacle_path_body_extras,
    path,
)
from assembly.viewer import display_parts, set_viewer
from config import Config
from puzzle.puzzle import Puzzle


def main() -> None:
    """Generate the puzzle, assemble its parts, and export printable models."""
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=Config.Puzzle.CASE_SHAPE,
    )

    case_parts, base_parts, cut_shape = puzzle_casing()
    standard_paths, support_path, coloring_path = path(puzzle, cut_shape)
    obstacle_extras = build_obstacle_path_body_extras(puzzle)
    ball, ball_path, ball_path_direction = ball_and_path_indicators(puzzle)

    merge_standard_paths_with_case(case_parts, standard_paths or [])

    display_parts(
        case_parts,
        base_parts,
        standard_paths,
        support_path,
        coloring_path,
        obstacle_extras,
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
