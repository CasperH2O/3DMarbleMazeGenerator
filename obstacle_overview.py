import logging
import math

from build123d import Location, Pos, Vector
from ocp_vscode import Camera, set_defaults, show

import config
from logging_config import configure_logging
from obstacles.obstacle_registry import get_available_obstacles, get_obstacle_class

configure_logging()
logger = logging.getLogger(__name__)


def show_obstacles_overview() -> None:
    """
    Display all registered obstacles in a compact grid, sorted by their
    occupied node counts, rendered in the primary path color.
    """
    names = get_available_obstacles()
    if not names:
        logger.warning("No obstacles registered.")
        return

    # Instantiate & sort by occupied node count (smallest first)
    obstacles = [get_obstacle_class(name)() for name in names]
    obstacles.sort(key=lambda ob: len(ob.occupied_nodes))

    # Prepare viewer defaults, keep orientation across runs, enable edges
    set_defaults(reset_camera=Camera.KEEP, black_edges=True)

    # Build geometry and collect bounding boxes
    obstacle_color = config.Puzzle.PATH_COLORS[0]
    built = []
    max_width = max_height = 0.0

    for obstacle in obstacles:
        obstacle.create_obstacle_geometry()
        solid = obstacle.model_solid()

        bbox = solid.bounding_box()  # -> has .min/.max vectors with X/Y/Z
        width = bbox.max.X - bbox.min.X
        height = bbox.max.Y - bbox.min.Y
        max_width = max(max_width, width)
        max_height = max(max_height, height)

        built.append((obstacle, solid, bbox, width, height))

    # Grid parameters
    n = len(built)
    cols = math.ceil(math.sqrt(n))  # roughly square grid

    # Use node_size as a natural scale for padding
    base_pad = obstacles[0].node_size
    pad_x = base_pad * 0.5
    pad_y = base_pad * 0.5

    cell_width = max_width + 2 * pad_x
    cell_height = max_height + 2 * pad_y

    parts = []
    for idx, (obstacle, solid, bbox, width, height) in enumerate(built):
        # Target cell center
        cell = idx % cols
        row = idx // cols
        cell_cx = cell * cell_width + cell_width * 0.5
        cell_cy = -(
            row * cell_height + cell_height * 0.5
        )  # go "down" in -Y to avoid overlap with origin lines

        # Current bbox center
        bx_cx = 0.5 * (bbox.min.X + bbox.max.X)
        by_cy = 0.5 * (bbox.min.Y + bbox.max.Y)

        # Translate to center inside the cell
        dx = cell_cx - bx_cx
        dy = cell_cy - by_cy
        solid.locate(Location(Pos(Vector(dx, dy, 0))))  # absolute move

        # Label/color for viewer tree & appearance
        solid.label = f"{obstacle.name}"
        solid.color = obstacle_color
        parts.append(solid)

    show(*parts)


if __name__ == "__main__":
    show_obstacles_overview()
