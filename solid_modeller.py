# solid_modeller.py

import os
from typing import Optional

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Part,
    Polyline,
    Pos,
    SortBy,
    Sphere,
    Transition,
    export_stl,
    sweep,
)
from ocp_vscode import Camera, set_defaults, set_viewer_config, show_object, status

from cad.cases.case import CasePart
from cad.cases.case_box import CaseBox
from cad.cases.case_sphere import CaseSphere
from cad.cases.case_sphere_with_flange import CaseSphereWithFlange
from cad.cases.case_sphere_with_flange_enclosed_two_sides import (
    CaseSphereWithFlangeEnclosedTwoSides,
)
from cad.path_builder import PathBuilder, PathTypes
from config import CaseShape, Config
from puzzle.puzzle import Puzzle


def main() -> None:
    """
    Generate a puzzle, visualize the 3D models and export them to STL format for 3D printing.
    """

    # Create the puzzle
    puzzle = Puzzle(
        node_size=Config.Puzzle.NODE_SIZE,
        seed=Config.Puzzle.SEED,
        case_shape=Config.Puzzle.CASE_SHAPE,
    )

    # Create the case and retrieve its parts and the cut shape
    case_parts, cut_shape = puzzle_casing()

    # Build paths associated with the puzzle and cut them from the case
    standard_paths, support_path, coloring_path = path(puzzle, cut_shape)

    # Create the ball and ball path
    ball, ball_path = ball_and_path_indicators(puzzle)

    if standard_paths:
        for idx, part in enumerate(case_parts):
            # Subtract the standard path for physical bridge
            if part.label == CasePart.MOUNTING_RING.value:
                # TODO improve this, need all objects to be same type, then it should remember label and color
                label = part.label
                color = part.color

                # TODO, combine all paths into one object, then subtract the cut shape from it
                case_parts[idx] = part - standard_paths[0]
                # Extract and sort the solids by volume
                sorted_solids = case_parts[idx].solids().sort_by(SortBy.VOLUME)

                # Get the largest solid (last one in ascending volume sort)
                largest_solid = sorted_solids[-1]

                # Convert it to a Part
                case_parts[idx] = largest_solid
                case_parts[idx].label = label
                case_parts[idx].color = color
            # Cut internal patch bridges to be flush with paths
            if part.label == CasePart.INTERNAL_PATH_BRIDGES.value:
                label = part.label
                color = part.color

                # TODO, combine all paths into one object, then subtract the cut shape from it
                case_parts[idx] = part - standard_paths[0]
                # Extract and sort the solids by volume
                sorted_solids = case_parts[idx].solids().sort_by(SortBy.VOLUME)

                # Get the n mounting points path amount smallest solids
                remaining_path_bridge_pieces = sorted_solids[
                    : Config.Sphere.NUMBER_OF_MOUNTING_POINTS - 1
                ]

                # Convert it to a Part
                case_parts[idx] = remaining_path_bridge_pieces
                case_parts[idx].label = label
                case_parts[idx].color = color
                break

    # Display all case, puzzle and additional parts
    display_parts(
        case_parts, standard_paths, support_path, coloring_path, ball, ball_path
    )

    # Set viewer configuration
    set_viewer()

    # Export all case and additional parts
    additional_parts = [
        standard_paths,
        support_path,
        coloring_path,
    ]
    export_all(case_parts, additional_parts)


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
        raise ValueError(
            f"Unknown CASE_SHAPE '{Config.Puzzle.CASE_SHAPE}' specified in config.py."
        )

    # Retrieve parts from the case.
    case_parts = case.get_parts()

    # Obtain the shape used to cut paths from the case
    cut_shape = case.cut_shape

    return case_parts, cut_shape


def path(puzzle, cut_shape: Part):
    """
    Generate the path objects, cut them from the case where needed, and return:
      - standard_paths: a list of standard path bodies with proper labeling and colors
      - support_path: a single support path body
      - coloring_path: a single accent/coloring path body
    """
    # Initialize the PathBuilder (which internally builds and stores the final path bodies)
    path_builder = PathBuilder(puzzle)

    standard_path_bodies: Optional[Part] = None
    support_path: Optional[Part] = None
    coloring_path: Optional[Part] = None

    # Retrieve the path bodies and the start area
    path_bodies = path_builder.final_path_bodies
    start_area = path_builder.start_area

    # Process standard paths:
    standard_path_bodies = []
    if path_bodies.get(PathTypes.STANDARD):
        # Available standard colors from the configuration (roll over if more segments than colors)
        standard_colors = Config.Puzzle.PATH_COLORS
        standard_parts = path_bodies[PathTypes.STANDARD]
        # Loop through each standard path part; use a counter for labeling and color assignment.
        for idx, part in enumerate(standard_parts, start=1):
            # For the first body, combine it with the start area
            if idx == 1:
                combined = part + (
                    start_area[0].part - cut_shape.part
                )  # merge with the first start area element
            else:
                combined = part
            # Subtract the cut shape from the combined (or single) object. #FIXME
            final_obj = combined  # - cut_shape.part
            # Assign a label with a counter (e.g., "Standard Path 1", "Standard Path 2", etc.)
            final_obj.label = f"Standard Path {idx}"
            # Use the color from the list, rolling over if necessary.
            final_obj.color = standard_colors[(idx - 1) % len(standard_colors)]
            standard_path_bodies.append(final_obj)

    if path_bodies[PathTypes.SUPPORT]:
        support_path = path_bodies[PathTypes.SUPPORT]
        support_path = support_path - cut_shape.part
        support_path.label = PathTypes.SUPPORT.value
        support_path.color = Config.Puzzle.SUPPORT_MATERIAL_COLOR

    if path_bodies[PathTypes.ACCENT_COLOR]:
        coloring_path = path_bodies[PathTypes.ACCENT_COLOR]
        coloring_path = coloring_path + (
            start_area[1].part - cut_shape.part
        )  # combine with second start area
        coloring_path.label = PathTypes.ACCENT_COLOR.value
        coloring_path.color = Config.Puzzle.PATH_ACCENT_COLOR

    return standard_path_bodies, support_path, coloring_path


def ball_and_path_indicators(puzzle):
    """
    Create and return a ball and ball path object based on the puzzle's path.
    """

    cad_nodes = puzzle.total_path
    node_positions = [(node.x, node.y, node.z) for node in cad_nodes]

    # Create the ball at the start of the track
    with BuildPart(Pos(node_positions[1])) as ball:
        Sphere(Config.Puzzle.BALL_DIAMETER / 2)

    ball.part.label = "Ball"
    ball.part.color = Config.Puzzle.BALL_COLOR

    # Create a ball path indicator line
    with BuildPart() as ball_path:
        with BuildLine() as ball_path_line:
            Polyline(node_positions[1:])
        with BuildSketch(ball_path_line.line ^ 0):
            Circle(Config.Puzzle.BALL_DIAMETER / 10)
        sweep(transition=Transition.RIGHT)

    ball_path.part.label = "Ball Path"
    ball_path.part.color = Config.Puzzle.BALL_COLOR

    return ball.part, ball_path.part


def display_parts(
    case_parts, standard_paths, support_path, coloring_path, ball, ball_path
):
    """
    Display all puzzle physical objects.
    """
    # Set the default camera position, to not adjust on new show
    set_defaults(reset_camera=Camera.KEEP)

    # Display each part from the case
    for part in case_parts:
        show_object(part)

    # The paths, standard paths, support path and coloring path
    for standard_path in standard_paths:
        show_object(standard_path)

    if support_path:
        show_object(support_path)

    if coloring_path:
        show_object(coloring_path)

    # Display the ball and its path
    show_object(ball)
    show_object(ball_path)


def set_viewer():
    """
    Set the viewer configuration.
    """

    # Do not draw lines on the following groups
    groups_to_reset = {
        f"/Group/{CasePart.CASING.value}",
        f"/Group/{CasePart.DOME_TOP.value}",
        f"/Group/{CasePart.DOME_BOTTOM.value}",
        "/Group/Ball Path",
        "/Group/Ball",
    }
    current_states = status()["states"]

    # Update the viewer configuration so that the specified groups do not draw lines
    new_config = {
        group: ([1, 0] if group in groups_to_reset else viewer_config)
        for group, viewer_config in current_states.items()
    }

    set_viewer_config(states=new_config)


def export_all(case_parts, additional_parts=None):
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
    for case_part in case_parts:
        stl_file_path = os.path.join(export_path, f"{case_part.label}.stl")
        export_stl(to_export=case_part, file_path=stl_file_path)

    # Export additional objects, if any.
    if additional_parts:
        # flatten nested lists,  for split body paths
        def _flatten(parts):
            for item in parts:
                if isinstance(item, list):
                    yield from _flatten(item)
                else:
                    yield item

        for part in _flatten(additional_parts):
            stl_file_path = os.path.join(export_path, f"{part.label}.stl")
            export_stl(to_export=part, file_path=stl_file_path)


if __name__ == "__main__":
    main()
