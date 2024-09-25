# generate.py

from puzzle.puzzle import Puzzle
from puzzle.visualization import visualize_nodes_and_paths_plotly
from utils.config import DIAMETER, SHELL_THICKNESS, NODE_SIZE, SEED

if __name__ == "__main__":
    # Create a Puzzle instance
    puzzle = Puzzle(diameter=DIAMETER, shell_thickness=SHELL_THICKNESS, node_size=NODE_SIZE, seed=SEED)

    if puzzle.total_path:
        print(f"Total path length: {len(puzzle.total_path)}")
        # Visualize the nodes and the path
        visualize_nodes_and_paths_plotly(puzzle.nodes, puzzle.total_path, puzzle.inner_radius)
    else:
        print("No path could be constructed to connect all waypoints.")
