# generate.py

from puzzle.puzzle import Puzzle
from visualization import visualize_interpolated_path_plotly
import config


def main():
    """Generate the puzzle and visualize it."""

    # Create the puzzle
    puzzle = Puzzle(
        node_size=config.NODE_SIZE,
        seed=config.SEED,
        case_shape=config.CASE_SHAPE,
    )

    # Print puzzle information
    print("Puzzle Information")
    print(f"Total path length: {len(puzzle.total_path)}")
    print(f"Number of segments: {len(puzzle.interpolated_segments)}")

    # Visualize the interpolated path using plotly
    visualize_interpolated_path_plotly(puzzle.nodes, puzzle.interpolated_segments, puzzle.casing)


if __name__ == "__main__":
    main()
