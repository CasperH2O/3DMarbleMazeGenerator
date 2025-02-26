# solid_modeller.py

import os

from config import Config
from config import CaseShape
from puzzle.puzzle import Puzzle
from ocp_vscode import show_object, status, set_viewer_config, set_defaults, Camera
from build123d import BuildPart, Pos, Sphere, BuildLine, Polyline, BuildSketch, Circle, sweep, Transition, export_stl
from cad.path_builder import PathBuilder
from cad.cases.case_sphere import CaseSphere
from cad.cases.case_box import CaseBox
from cad.cases.case_sphere_with_flange import CaseSphereWithFlange
from cad.cases.case_sphere_with_flange_enclosed_two_sides import CaseSphereWithFlangeEnclosedTwoSides


def main() -> None:
    """
    Generate a puzzle, visualize the 3D models and export them to STL format for 3D printing.
    """

    # Create the puzzle
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=Config.Puzzle.CASE_SHAPE
    )

    # Create the case and retrieve its parts and the cut shape
    case_parts, cut_shape = puzzle_casing()

    # Build paths associated with the puzzle and cut them from the case
    standard_path, support_path, coloring_path = path(puzzle, cut_shape)

    # Create the ball and ball path
    ball, ball_path = ball_and_path_indicators(puzzle)

    # If a mounting ring is one of the parts, adjust its geometry by subtracting the standard path.
    if "Mounting Ring" in case_parts and standard_path:
        case_parts["Mounting Ring"].obj.part = case_parts["Mounting Ring"].obj.part - standard_path
        
    # Display all parts and additional objects
    display_parts(case_parts, standard_path, support_path, coloring_path, ball, ball_path)

    # Set viewer configuration
    set_viewer()

    # Export all parts along with additional objects (paths)
    additional_objs = {
        "Path": standard_path,
        "Support Path": support_path,
        "Coloring Path": coloring_path,
    }
    export_all(case_parts, additional_objs)

def puzzle_casing():
    """
    Create the puzzle case based on the configuration and return:
      - case: The instantiated case object
      - case_parts: A dictionary of CasePart instances belonging to the case
      - cut_shape: The shape used to cut paths from the case
    """
    # Create the appropriate case based on configuration
    if Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE:
        case = CaseSphere()
    elif Config.Puzzle.CASE_SHAPE == CaseShape.BOX:
        case = CaseBox()
    elif Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE:
        case = CaseSphereWithFlange()
    elif Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES:
        case = CaseSphereWithFlangeEnclosedTwoSides()
    else:
        raise ValueError(f"Unknown CASE_SHAPE '{Config.Puzzle.CASE_SHAPE}' specified in config.py.")

    # Retrieve parts from the case.
    case_parts = case.get_parts()

    # Obtain the shape used to cut paths from the case
    cut_shape = case.cut_shape

    return case_parts, cut_shape

def path(puzzle, cut_shape):
    """
    Generate the path objects, cut them from the case where needed, and return:
      - standard_path
      - support_path
      - coloring_path
    """
    # Initialize the PathBuilder
    path_builder = PathBuilder(puzzle)

    # Retrieve the path bodies and the start area
    path_bodies = path_builder.final_path_bodies
    start_area = path_builder.start_area

    standard_path = None
    support_path = None
    coloring_path = None

    if path_bodies['standard']:
        standard_path = path_bodies['standard']
        standard_path = standard_path + start_area[0].part  # combine with start area
        standard_path = standard_path - cut_shape.part       # subtract the cut shape

    if path_bodies['support']:
        support_path = path_bodies['support']
        support_path = support_path - cut_shape.part

    if path_bodies['coloring']:
        coloring_path = path_bodies['coloring']
        coloring_path = coloring_path + start_area[1].part  # combine with second start area
        coloring_path = coloring_path - cut_shape.part

    return standard_path, support_path, coloring_path

def ball_and_path_indicators(puzzle):
    """
    Create and return a ball and ball path object based on the puzzle's path.
    """

    cad_nodes = puzzle.total_path
    node_positions = [(node.x, node.y, node.z) for node in cad_nodes]

    # Create the ball at the start of the track
    with BuildPart(Pos(node_positions[1])) as ball:
        Sphere(Config.Puzzle.BALL_DIAMETER / 2)

    # Create a ball path indicator line
    with BuildPart() as ball_path:
        with BuildLine() as ball_path_line:
            Polyline(node_positions[1:])
        with BuildSketch(ball_path_line.line^0):
            Circle(Config.Puzzle.BALL_DIAMETER / 10)
        sweep(transition=Transition.RIGHT)

    return ball, ball_path

def display_parts(case_parts, standard_path, support_path, coloring_path, ball, ball_path):
    """
    Display all puzzle physical objects.
    """

    # Set the default camera position, to not adjust on new show
    set_defaults(reset_camera=Camera.KEEP)

    # Display each part from the case
    for part in case_parts.values():
        show_object(part.obj, name=part.name, options=part.options)

    # Display the various paths if they exist
    if standard_path:
        show_object(standard_path, name="Standard Path", options={"color": Config.Puzzle.PATH_COLOR})
    if support_path:
        show_object(support_path, name="Support Path", options={"alpha": 0.1, "color": (1, 1, 1)})
    if coloring_path:
        show_object(coloring_path, name="Coloring Path", options={"color": Config.Puzzle.PATH_ACCENT_COLOR})

    # Display the ball and its path
    show_object(ball, name="Ball", options={"color": Config.Puzzle.BALL_COLOR})
    show_object(ball_path, name="Ball Path", options={"color": Config.Puzzle.BALL_COLOR})

def set_viewer():
    """
    Set the viewer configuration.
    """

    # Do not draw lines on the following groups
    groups_to_reset = {"/Group/Dome Top", "/Group/Dome Bottom", "/Group/Ball Path", "/Group/Ball"}
    current_states = status()["states"]
    
    # Update the viewer configuration so that the specified groups do not draw lines
    new_config = {
        group: ([1, 0] if group in groups_to_reset else viewer_config)
        for group, viewer_config in current_states.items()
    }

    set_viewer_config(states=new_config)

def export_all(case_parts, additional_objects=None):
    """
    Export all case parts as STLs for 3D print manufacturing.
    """
    if not Config.Manufacturing.EXPORT_STL:
        return

    folder_name = f"Case-{Config.Puzzle.CASE_SHAPE}-Seed-{Config.Puzzle.SEED}"
    export_path = os.path.join("export", "stl", folder_name)

    if not os.path.exists(export_path):
        os.makedirs(export_path)

    # Export each case part to STL format
    for case_part in case_parts.values():
        stl_file_path = os.path.join(export_path, f"{case_part.name}.stl")
        export_stl(to_export = case_part.obj.part, file_path = stl_file_path)

    # Export additional objects, if any
    if additional_objects:
        for name, obj in additional_objects.items():
            stl_file_path = os.path.join(export_path, f"{name}.stl")
            export_stl(to_export = obj, file_path = stl_file_path)

if __name__ == "__main__":
    main()
