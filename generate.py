# generate.py

from puzzle.puzzle import Puzzle
from config import Config
from visualization import visualize_interpolated_path_plotly
from visualization.plotly_visualization import visualize_path_architect


def main():
    """Generate the puzzle and visualize it."""

    # Create the puzzle
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=Config.Puzzle.CASE_SHAPE,
    )

    # Print puzzle information
    print("Puzzle Information")
    print(f"Total path length: {len(puzzle.total_path)}")
    print(f"Number of segments: {len(puzzle.path_architect.segments)}")

    # Collect the used path profile types
    profile_types_used = set(segment.profile_type for segment in puzzle.path_architect.segments)
    print(f"Profile types used: {len(profile_types_used)}, {', '.join(pt.value for pt in profile_types_used)}")

    # Collect the used path curve models
    curve_models_used = set(segment.curve_model for segment in puzzle.path_architect.segments)
    print(f"Number of different curve models used: {len(curve_models_used)}")
#    print(f"Curve models used: {', '.join(cm.value for cm in curve_models_used)}")

    # Collect the used curve types
    curve_types_used = set(segment.curve_type for segment in puzzle.path_architect.segments if segment.curve_type is not None)
    print(f"Different curves used: {len(curve_types_used)}, {', '.join(ct.value for ct in curve_types_used)}")

    # Visualize the interpolated path
    #visualize_interpolated_path_plotly(puzzle.nodes, puzzle.interpolated_segments, puzzle.casing)
    visualize_path_architect(puzzle.nodes, puzzle.path_architect.segments, puzzle.casing)

if __name__ == "__main__":
    main()
