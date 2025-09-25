# generate.py

from config import Config
from puzzle.puzzle import Puzzle
from visualization.visualization import visualize_path_architect


def main() -> None:
    """
    Generate a puzzle using configuration parameters and visualize the resulting path.

    This function creates a puzzle instance with a specified node size, seed, and case shape
    as defined in the configuration. It prints the puzzle information and visualizes the generated path
    using the appropriate visualization function.
    """
    # Create the puzzle
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=Config.Puzzle.CASE_SHAPE,
    )

    # Print puzzle information
    puzzle.print_puzzle_info()

    # Visualize the path architect
    visualize_path_architect(
        puzzle.nodes,
        puzzle.path_architect.segments,
        puzzle.casing,
        puzzle.total_path,
        puzzle.obstacle_manager.placed_obstacles,
    )


if __name__ == "__main__":
    main()
