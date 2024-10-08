# generate.py

from puzzle.puzzle import Puzzle
from visualization import *
import config

if __name__ == "__main__":
    # Create the puzzle
    puzzle = Puzzle(
        node_size=config.NODE_SIZE,
        seed=config.SEED,
        case_shape=config.CASE_SHAPE,
    )

    print(f"Total path length: {len(puzzle.total_path)}")
    #Visualize the nodes and the path
    #visualize_nodes_and_paths(puzzle.nodes, puzzle.total_path, puzzle.casing)
    #visualize_nodes_and_paths_curve_fit(puzzle.nodes, puzzle.total_path, puzzle.casing)
    #visualize_nodes_and_paths_nurbs(puzzle.nodes, puzzle.total_path, puzzle.casing)
    #visualize_nodes_and_paths_spline(puzzle.nodes, puzzle.total_path, puzzle.casing)
    #visualize_nodes_and_paths_plotly(puzzle.nodes, puzzle.total_path, puzzle.casing)
    #visualize_nodes_and_paths_curve_fit_plotly(puzzle.nodes, puzzle.total_path, puzzle.casing)
    visualize_interpolated_path_plotly(puzzle.nodes, puzzle.interpolated_segments, puzzle.casing)

    if not True:
        print('# Define the points for the spline path')
        print('pts = [')
        for node in puzzle.total_path:
            coords = f'    ({node.x}, {node.y}, {node.z}),'
            comment = ''
            if node.start:
                comment = '  # Start point'
            elif node.end:
                comment = '  # End point'
            elif node.waypoint:
                comment = '  # Waypoint'
            print(coords + comment)
        print(']')
