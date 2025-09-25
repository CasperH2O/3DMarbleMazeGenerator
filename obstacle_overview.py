from build123d import Location, Pos, Vector
from ocp_vscode import Camera, set_defaults, show

import config
from obstacles.obstacle_registry import get_available_obstacles, get_obstacle_class


def show_obstacles_overview() -> None:
    """
    Display all registered obstacles side by side, sorted by their occupied node counts,
    rendered in the primary path color.
    """
    # Retrieve all registered obstacle names
    names = get_available_obstacles()
    if not names:
        print("No obstacles registered. Did you import the catalogue modules?")
        return

    # Instantiate all obstacles
    obstacles = [get_obstacle_class(name)() for name in names]

    # Sort by occupied node count
    obstacles.sort(key=lambda obstacle: len(obstacle.occupied_nodes))

    # Prepare variables
    spacing = obstacles[0].node_size
    parts = []
    current_x = 0.0
    obstacle_color = config.Puzzle.PATH_COLORS[0]

    # Build obstacle solids
    for obstacle in obstacles:
        obstacle.create_obstacle_geometry()
        obstacle_solid = obstacle.model_solid()

        # Compute bounding box for positioning
        bbox = obstacle_solid.bounding_box()
        min_x = bbox.min.X
        max_x = bbox.max.X

        # Translate so that this obstacle's min X aligns to current_x
        translate_x = current_x - min_x
        obstacle_solid.locate(Location(Pos(Vector(translate_x, 0, 0))))
        obstacle_solid.label = f"{obstacle.name}"
        obstacle_solid.color = obstacle_color

        parts.append(obstacle_solid)

        # Update spacing for next obstacle
        current_x = translate_x + max_x + spacing

    # Keep camera steady across views, show obstacles
    set_defaults(reset_camera=Camera.KEEP)
    show(*parts)


if __name__ == "__main__":
    show_obstacles_overview()
