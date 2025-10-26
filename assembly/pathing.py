# assembly/pathing.py

from typing import Optional

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
    Sphere,
    Transition,
    Vector,
    add,
    sweep,
)

from cad.path_builder import PathBuilder, PathTypes
from config import Config
from puzzle.puzzle import Puzzle


def path(puzzle: Puzzle, cut_shape: Part):
    """
    Generate the path objects, cut them from the case where needed, and return:
      - standard_paths: a list of standard path bodies with proper labeling and colors
      - support_path: a single support path body
      - coloring_path: a single accent/coloring path body
    """
    # Initialize the PathBuilder (which internally builds and stores the final path bodies)
    path_builder = PathBuilder(puzzle)

    standard_path_bodies: Optional[list[Part]] = None
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
        support_path = Part() + [path_bodies[PathTypes.SUPPORT]]
        support_path = support_path - cut_shape.part
        support_path.label = PathTypes.SUPPORT.value
        support_path.color = Config.Puzzle.SUPPORT_MATERIAL_COLOR

    if path_bodies[PathTypes.ACCENT_COLOR]:
        accent_seg = path_bodies[PathTypes.ACCENT_COLOR]
        funnel_part = start_area[1].part - cut_shape.part
        coloring_path = Part() + [accent_seg, funnel_part]
        coloring_path.label = PathTypes.ACCENT_COLOR.value
        coloring_path.color = Config.Puzzle.PATH_ACCENT_COLOR

    return standard_path_bodies, support_path, coloring_path


def build_obstacle_path_body_extras(puzzle: Puzzle) -> list[Part]:
    """
    Obstacle path body extras that are not part of sweep
    """
    parts: list[Part] = []

    for idx, obstacle in enumerate(puzzle.obstacle_manager.placed_obstacles, start=1):
        placed_part = obstacle.get_placed_obstacle_extras()

        # Label and color individually
        part = Part(placed_part)
        part.label = f"Obstacle {idx} - {obstacle.name} extra's"
        part.color = Config.Puzzle.PATH_COLORS[0]

        parts.append(part)

    return parts


def ball_and_path_indicators(puzzle: Puzzle):
    """
    Create and return a ball, its swept path, and
    directional cones every n nodes along that path.
    """

    cad_nodes = puzzle.total_path
    node_positions = [(node.x, node.y, node.z) for node in cad_nodes]

    # Ball at the start
    with BuildPart() as ball:
        Sphere(Config.Puzzle.BALL_DIAMETER / 2)
    ball.part = ball.part.translate(Vector(*node_positions[2]))
    ball.part.label = "Ball"
    ball.part.color = Config.Puzzle.BALL_COLOR

    # Prepare a reusable direction indicator cone that can be instanced along the path
    cone_bottom_radius = Config.Puzzle.BALL_DIAMETER / 3
    cone_height = Config.Puzzle.BALL_DIAMETER

    with BuildPart() as direction_indicator:
        Cone(
            bottom_radius=cone_bottom_radius,
            top_radius=0,
            height=cone_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
    indicator_solid = direction_indicator.part

    # Puzzle path with direction indication
    with BuildPart() as ball_path:
        # Path
        with BuildLine() as ball_path_line:
            Polyline(node_positions[1:])
        # Small circle for sweep
        with BuildSketch(ball_path_line.line ^ 0):
            Circle(Config.Puzzle.BALL_DIAMETER / 10)
        sweep(transition=Transition.ROUND)

        # Insert cones every n nodes for direction indication
        total_pts = len(node_positions)
        indicator_step = 3
        indicator_locations: list = []
        if total_pts > 2:
            for idx in range(1, total_pts, indicator_step):
                # parameterize position along polyline: 0 at first, 1 at last
                t = (idx - 1) / (total_pts - 2)
                loc = ball_path_line.line ^ t
                indicator_locations.append(loc)

        if indicator_locations:
            with Locations(*indicator_locations):
                add(indicator_solid)

    ball_path.part.label = "Ball Path"
    ball_path.part.color = Config.Puzzle.BALL_COLOR

    return ball.part, ball_path.part
