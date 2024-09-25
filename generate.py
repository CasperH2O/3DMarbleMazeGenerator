# generate.py

from puzzle.puzzle import Puzzle
from puzzle.node_creator import SphereGridNodeCreator
from puzzle.pathfinder import AStarPathFinder
from puzzle.visualization import visualize_nodes_and_paths_plotly
from utils.config import DIAMETER, SHELL_THICKNESS, NODE_SIZE, SEED

if __name__ == "__main__":
    # Initialize the node creator and pathfinder
    node_creator = SphereGridNodeCreator()
    pathfinder = AStarPathFinder()

    # Create a Puzzle instance with the specified node creator and pathfinder
    puzzle = Puzzle(
        diameter=DIAMETER,
        shell_thickness=SHELL_THICKNESS,
        node_size=NODE_SIZE,
        seed=SEED,
        node_creator=node_creator,
        pathfinder=pathfinder
    )

    if puzzle.total_path:
        print(f"Total path length: {len(puzzle.total_path)}")
        # Visualize the nodes and the path
        visualize_nodes_and_paths_plotly(puzzle.nodes, puzzle.total_path, puzzle.inner_radius)
    else:
        print("No path could be constructed to connect all waypoints.")
