# solid_modeller.py

import os

from config import Config
from config import CaseShape
from puzzle.puzzle import Puzzle
from ocp_vscode import show_object, status, set_viewer_config, set_defaults, Camera
from build123d import BuildPart, Pos, Sphere, BuildLine, Polyline, BuildSketch, Circle, sweep, Transition
from cad.path_builder import PathBuilder
from cad.case_sphere import CaseSphere
from cad.case_box import CaseBox
from cad.case_sphere_with_flange import CaseSphereWithFlange
from cad.case_sphere_with_flange_enclosed_two_sides import CaseSphereWithFlangeEnclosedTwoSides


def main() -> None:
    """
    Main function to generate a puzzle and export it to STEP format.
    """

    # Create the puzzle
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=Config.Puzzle.CASE_SHAPE
    )

    # Create the case and retrieve case objects and cut shape
    case, case_objects, cut_shape, mounting_ring = puzzle_casing()

    # Build paths associated with the puzzle and cut them from the case
    standard_path, support_path, coloring_path = path(puzzle, cut_shape, mounting_ring)
    #standard_path, support_path, coloring_path = None, None, None

    # Create the ball and ball path
    ball, ball_path = ball_and_path_indicators(puzzle)

    # Display all relevant objects
    display_objects(case_objects, standard_path, support_path, coloring_path, mounting_ring, ball, ball_path)

    # Set viewer configuration
    set_viewer()

    # Retrieve dome parts if they exist
    dome_top = case_objects.get("Dome Top", None)
    dome_bottom = case_objects.get("Dome Bottom", None)
    
    # path_body was originally commented out, we will assume path_body = standard_path
    path_body = standard_path

    # Export relevant objects, including those previously commented out
    export(ball, mounting_ring, dome_top, dome_bottom, path_body)


def puzzle_casing():
    """
    Create the puzzle case based on the configuration and return:
    - case: The instantiated case object
    - case_objects: A dictionary of objects belonging to the case
    - cut_shape: The shape used to cut paths from the case
    - mounting_ring: The mounting ring object if applicable, else None
    """
    mounting_ring = None

    # Create the appropriate case
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

    # Get the case objects
    case_objects = case.get_cad_objects()

    # Display the case objects and identify mounting ring if present
    for name, value in case_objects.items():
        if isinstance(value, tuple):
            obj, options = value
            if name == 'Mounting Ring' and (Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE or Config.Puzzle.CASE_SHAPE == CaseShape.SPHERE_WITH_FLANGE_ENCLOSED_TWO_SIDES):
                # Store for later use
                mounting_ring = obj
            else:
                show_object(obj, name=name, options=options)
        else:
            obj = value
            show_object(obj, name=name)

    # Obtain the shape that will be used to cut paths
    cut_shape = case.cut_shape

    return case, case_objects, cut_shape, mounting_ring


def path(puzzle, cut_shape, mounting_ring):
    """
    Generate the path objects, cut them from the case where needed, and return:
    - standard_path
    - support_path
    - coloring_path
    """

    # Initialize the PathBuilder
    path_builder = PathBuilder(puzzle)

    # Path bodies
    path_bodies = path_builder.final_path_bodies
    start_area = path_builder.start_area

    standard_path = None
    support_path = None
    coloring_path = None

    if path_bodies['standard']:
        # Get all standard path bodies
        standard_path = path_bodies['standard']
        
        # Combine path and start area
        standard_path = standard_path + start_area[0].part
        
        # Cut any shapes outside the case
        standard_path = standard_path - cut_shape.part

    if path_bodies['support']:
        # Get all support path bodies
        support_path = path_bodies['support']
        
        # Cut any shapes outside the case
        support_path = support_path - cut_shape.part

    if path_bodies['coloring']:
        # Get all coloring path bodies
        coloring_path = path_bodies['coloring']
        
        # Combine coloring path and second part of start area
        coloring_path = coloring_path + start_area[1].part
        
        # Cut any shapes outside the case
        coloring_path = coloring_path - cut_shape.part

    # If a mounting ring is present (sphere with flange), cut it from the standard_path
    if mounting_ring and standard_path:
        mounting_ring.part = mounting_ring.part - standard_path

    return standard_path, support_path, coloring_path


def ball_and_path_indicators(puzzle):
    """
    Create and return the ball and the ball path objects based on the puzzle's nodes.
    """
    cad_nodes = puzzle.total_path
    node_positions = [(node.x, node.y, node.z) for node in cad_nodes]

    # Create the ball at the start node (node_positions[1])
    with BuildPart(Pos(node_positions[1])) as ball:
        Sphere(Config.Puzzle.BALL_DIAMETER / 2)

    # Create a ball path indicator line
    with BuildPart() as ball_path:
        with BuildLine() as ball_path_line:
            Polyline(node_positions[1:])  # Exclude the first node
        with BuildSketch(ball_path_line.line^0):
            Circle(Config.Puzzle.BALL_DIAMETER / 10)
        sweep(transition=Transition.RIGHT)

    return ball, ball_path


def display_objects(case_objects, standard_path, support_path, coloring_path, mounting_ring, ball, ball_path):
    """
    Display all puzzle physical objects.
    """
    # Show the final standard path
    if standard_path:
        show_object(standard_path, name="Standard Path", options={"color": Config.Puzzle.PATH_COLOR})

    # Show the support path, if it exists
    if support_path:
        show_object(support_path, name="Support Path", options={"alpha": 0.1, "color": (1, 1, 1)})

    # Show the coloring path, if it exists
    if coloring_path:
        show_object(coloring_path, name="Coloring Path", options={"color": Config.Puzzle.PATH_ACCENT_COLOR})

    # Show the mounting ring if applicable
    if mounting_ring:
        show_object(mounting_ring, name="Mounting Ring", options={"color": Config.Puzzle.MOUNTING_RING_COLOR})

    # Show ball and ball path
    show_object(ball, name="Ball", options={"color": Config.Puzzle.BALL_COLOR})
    show_object(ball_path, name="Ball Path", options={"color": Config.Puzzle.BALL_COLOR})


def set_viewer():
    # Fetch current states from the viewer
    current_states = status()["states"]

    # Initialize a dictionary to hold the new configuration
    new_config = {}

    # Iterate through each group in the current states
    for group, viewer_config in current_states.items():
        # If the group is "Standard Path", retain its current configuration
        if group == "/Group/Standard Path":
            new_config[group] = viewer_config
        else:
            # Set other groups to [1, 0]
            new_config[group] = [1, 0]

    # Apply the new configuration
    set_viewer_config(states=new_config)

    # Restore the commented-out lines for reference:
    set_defaults(reset_camera=Camera.KEEP)
    #set_defaults(reset_camera=Camera.RESET)


def export(ball, mounting_ring, dome_top, dome_bottom, path_body):
    """
    Export puzzle components for manufacturing.
    """

    # Check if we want to export STL files
    if not Config.Manufacturing.EXPORT_STL:
        return

    # Construct folder name and path
    folder_name = f"Case-{Config.Puzzle.CASE_SHAPE}-Seed-{Config.Puzzle.SEED}"
    export_path = os.path.join("..", "CAD", "STEP", folder_name)

    # Check if path exists, if not create the folder
    if not os.path.exists(export_path):
        os.makedirs(export_path)

    # Define objects we want to export
    objects_to_export = {
        "Ball": ball
    }

    # Conditionally add objects if they exist
    if mounting_ring is not None:
        objects_to_export["Mounting Ring"] = mounting_ring

    if dome_top is not None:
        objects_to_export["Dome Top"] = dome_top

    if dome_bottom is not None:
        objects_to_export["Dome Bottom"] = dome_bottom

    if path_body is not None:
        objects_to_export["Path"] = path_body

    # Export each object to STL and STEP
    for name, obj in objects_to_export.items():
        stl_file_path = os.path.join(export_path, f"{name}.stl")
        step_file_path = os.path.join(export_path, f"{name}.step")
        obj.val().exportStl(stl_file_path)
        obj.val().exportStep(step_file_path)
        

if __name__ == "__main__":
    main()