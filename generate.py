# generate.py

from puzzle.casing import *
from puzzle.puzzle import Puzzle
from puzzle.node_creator import *
from puzzle.pathfinder import AStarPathFinder
from puzzle.visualization import visualize_nodes_and_paths_plotly
from utils.config import DIAMETER, SHELL_THICKNESS, NODE_SIZE, SEED, WIDTH, HEIGHT, LENGTH

if __name__ == "__main__":
    # Initialize the casing
    casing = SphereCasing(diameter=DIAMETER, shell_thickness=SHELL_THICKNESS)
    node_creator = SphereGridNodeCreator()

    #casing = BoxCasing(width=WIDTH, height=HEIGHT, length=LENGTH)
    #node_creator = BoxGridNodeCreator()

    # Initialize the node creator and pathfinder

    pathfinder = AStarPathFinder()

    # Create the puzzle
    puzzle = Puzzle(
        node_size=NODE_SIZE,
        seed=SEED,
        casing=casing,
        node_creator=node_creator,
        pathfinder=pathfinder
    )

    if puzzle.total_path:
        print(f"Total path length: {len(puzzle.total_path)}")
        # Visualize the nodes and the path
        visualize_nodes_and_paths_plotly(puzzle.nodes, puzzle.total_path, puzzle.inner_radius)
    else:
        print("No path could be constructed to connect all waypoints.")
