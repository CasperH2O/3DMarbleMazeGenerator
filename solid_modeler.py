# solid_modeller.py

import os
from typing import Optional

import numpy as np
from build123d import (
    Align,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Cone,
    Locations,
    Part,
    Polyline,
    Pos,
    SortBy,
    Sphere,
    Transition,
    Vector,
    export_stl,
    sweep,
)
from ocp_vscode import (
    Animation,
    Camera,
    set_defaults,
    set_viewer_config,
    show_object,
    status,
)

from cad.base import create_box_base, create_circular_base
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

    # Create the base, it's either a box or any of the sphere shapes
    if puzzle.case_shape == CaseShape.BOX:
        base_parts = create_box_base()
    else:
        base_parts = create_circular_base()

    if standard_paths:
        for idx, part in enumerate(case_parts):
            # Subtract the standard path for physical bridge
            if part.label == CasePart.MOUNTING_RING.value:
                # TODO improve this, need all objects to be same type, then it should remember label and color
                label = part.label
                color = part.color

                # Subtract all paths from the mounting ring
                case_parts[idx] = case_parts[idx] - standard_paths

                # Extract and sort the solids by volume
                sorted_solids = case_parts[idx].solids().sort_by(SortBy.VOLUME)

                # Get the largest solid (last one in ascending volume sort)
                largest_solid = sorted_solids[-1]

                # Convert it to a Part
                case_parts[idx] = largest_solid
                case_parts[idx].label = label
                case_parts[idx].color = color

            # Cut internal path bridges to be flush with paths,
            # merge each flush‐bridge fragment with it's respective connected path
            if part.label == CasePart.INTERNAL_PATH_BRIDGES.value:
                # Use bridge solids separate
                bridge_solids = case_parts[idx].solids()

                # Match bridge with standard path
                for bridge in bridge_solids:
                    matched_sp_idx = None
                    for standard_path_idx, standard_path in enumerate(standard_paths):
                        # Check overlap, can only be with one, break once found
                        overlap = standard_path & bridge
                        if overlap is None:
                            continue  # Check next combination
                        if overlap.solids():
                            matched_sp_idx = standard_path_idx
                            break

                    # If we can't find a match, something went wrong
                    # and bridge does not connect to path.
                    # Probably a path profile at a wrong orientation
                    if matched_sp_idx is None:
                        print("Unable to match bridge with standard path segment.")
                        continue

                    # Subtract the standard path from the bridge, to make it flush
                    # Sort by volume, as we later use the smallest of the two
                    fragments = (
                        (bridge - standard_paths[matched_sp_idx])
                        .solids()
                        .sort_by(SortBy.VOLUME)
                    )

                    if not fragments:
                        continue  # nothing left once subtracted

                    # Take the smallest remaining fragment and merge it back
                    smallest_fragment = fragments[0]
                    standard_paths[matched_sp_idx] = (
                        standard_paths[matched_sp_idx] + smallest_fragment
                    )

                # Remove the original bridge part from case_parts,
                # since its absorbed into standard_paths
                case_parts.pop(idx)
                break

    # Display all case, puzzle and additional parts
    display_parts(
        case_parts,
        base_parts,
        standard_paths,
        support_path,
        coloring_path,
        ball,
        ball_path,
    )

    # Set viewer configuration
    set_viewer()

    # Export all case and additional parts
    additional_parts = [
        standard_paths,
        support_path,
        coloring_path,
    ]
    export_all(case_parts, base_parts, additional_parts)


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
        support_path = Part(path_bodies[PathTypes.SUPPORT])
        support_path = support_path - cut_shape.part
        support_path.label = PathTypes.SUPPORT.value
        support_path.color = Config.Puzzle.SUPPORT_MATERIAL_COLOR

    if path_bodies[PathTypes.ACCENT_COLOR]:
        accent_seg = path_bodies[PathTypes.ACCENT_COLOR]
        funnel_part = start_area[1].part - cut_shape.part
        combined = accent_seg + funnel_part
        coloring_path = Part(combined)
        coloring_path.label = PathTypes.ACCENT_COLOR.value
        coloring_path.color = Config.Puzzle.PATH_ACCENT_COLOR

    return standard_path_bodies, support_path, coloring_path


def ball_and_path_indicators(puzzle):
    """
    Create and return a ball, its swept path, and
    directional cones every n nodes along that path.
    """

    cad_nodes = puzzle.total_path
    node_positions = [(node.x, node.y, node.z) for node in cad_nodes]

    # Ball at the start
    with BuildPart(Pos(node_positions[2])) as ball:
        Sphere(Config.Puzzle.BALL_DIAMETER / 2)
    ball.part.label = "Ball"
    ball.part.color = Config.Puzzle.BALL_COLOR

    # Puzzle path with direction indication
    with BuildPart() as ball_path:
        # Path
        with BuildLine() as ball_path_line:
            Polyline(node_positions[1:])
        # Small circle for sweep
        with BuildSketch(ball_path_line.line ^ 0):
            Circle(Config.Puzzle.BALL_DIAMETER / 10)
        sweep(transition=Transition.RIGHT)

        # Insert cones every n nodes for direction indication
        total_pts = len(node_positions)
        step = 3
        for idx in range(1, total_pts, step):
            # parameterize position along polyline: 0 at first, 1 at last
            t = (idx - 1) / (total_pts - 2)
            loc = ball_path_line.line ^ t
            # place a cone whose base sits at the node and
            # whose tip points forward along the path tangent
            with Locations(loc):
                Cone(
                    bottom_radius=Config.Puzzle.BALL_DIAMETER / 3,
                    top_radius=0,
                    height=Config.Puzzle.BALL_DIAMETER,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )

    ball_path.part.label = "Ball Path"
    ball_path.part.color = Config.Puzzle.BALL_COLOR

    return ball.part, ball_path.part


def display_parts(
    case_parts, base_parts, standard_paths, support_path, coloring_path, ball, ball_path
):
    """
    Display all puzzle physical objects.
    """
    # Set the default camera position, to not adjust on new show
    set_defaults(reset_camera=Camera.KEEP)

    # Display each part from the case
    for part in case_parts:
        show_object(part)

    # Display each part from the base
    for part in base_parts:
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

    # Rotating animation
    animation = Animation(Part())
    times = np.linspace(0, 6, 33)  # 4 seconds split in 0.2 intervals
    values = np.linspace(0, -360, 33)  # as many positions as times

    # Get all the groups for animation
    all_groups = current_states.keys()
    # add all groups to animation tracks except for the base
    for grp in all_groups:
        if grp == "/Group/Base":
            continue  # skip the Base group
        animation.add_track(grp, "rz", times, values)

    animation.animate(1)


def export_all(case_parts: list[Part], base_parts: list[Part], additional_parts=None):
    """
    Export all case parts as STLs for 3D print manufacturing.
    """
    if not Config.Manufacturing.EXPORT_STL:
        return

    # root export folder
    folder_name = f"Case-{Config.Puzzle.CASE_SHAPE.value}-Seed-{Config.Puzzle.SEED}"
    export_root = os.path.join("export", "stl", folder_name)
    os.makedirs(export_root, exist_ok=True)

    # create the four categories for folder sorting
    folders = {
        "Puzzle": os.path.join(export_root, "Puzzle"),
        "Mounting": os.path.join(export_root, "Mounting"),
        "Base": os.path.join(export_root, "Base"),
        "Extra": os.path.join(export_root, "Extra"),
    }
    for p in folders.values():
        os.makedirs(p, exist_ok=True)

    # export each case part to STL format
    puzzle_case = {
        CasePart.MOUNTING_RING.value,
        CasePart.INTERNAL_PATH_BRIDGES.value,
    }
    mounting_case = {
        CasePart.MOUNTING_RING_TOP.value,
        CasePart.MOUNTING_RING_BOTTOM.value,
        CasePart.MOUNTING_RING_CLIP_START.value,
        CasePart.MOUNTING_RING_CLIP_SINGLE.value,
        CasePart.START_INDICATOR.value,
    }
    extra_case = {
        CasePart.DOME_TOP.value,
        CasePart.DOME_BOTTOM.value,
        CasePart.CASING.value,
        CasePart.MOUNTING_RING_CLIPS.value,
    }

    # Adjust some orienation to prepare for 3D printing plate
    for part in case_parts:
        match part.label:
            # Rotate mounting ring top upside down
            case CasePart.MOUNTING_RING_TOP.value:
                part.orientation = Vector(0, 180, 0)
            # Rotate mounting clips
            case (
                CasePart.START_INDICATOR.value
                | CasePart.MOUNTING_RING_CLIP_START.value
                | CasePart.MOUNTING_RING_CLIP_SINGLE.value
            ):
                part.orientation = Vector(90, 0, 0)

    for part in case_parts:
        label = part.label
        if label in puzzle_case:
            dst = folders["Puzzle"]
        elif label in mounting_case:
            dst = folders["Mounting"]
        elif label in extra_case:
            dst = folders["Extra"]
        else:
            # anything un‐matched goes to Extra
            dst = folders["Extra"]
        export_stl(to_export=part, file_path=os.path.join(dst, f"{label}.stl"))

    # export puzzle stand base
    for part in base_parts:
        label = part.label
        dst = folders["Base"]
        export_stl(to_export=part, file_path=os.path.join(dst, f"{label}.stl"))

    # export additional objects, the paths, if any.
    if additional_parts:
        # flatten nested lists, for split body paths
        def _flatten(parts):
            for item in parts:
                if isinstance(item, list):
                    yield from _flatten(item)
                else:
                    yield item

        # all these go into the puzzle folder
        for part in _flatten(additional_parts):
            label = part.label
            dst = folders["Puzzle"]
            export_stl(to_export=part, file_path=os.path.join(dst, f"{label}.stl"))


if __name__ == "__main__":
    main()
