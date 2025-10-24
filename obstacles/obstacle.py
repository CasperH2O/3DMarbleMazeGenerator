# obstacles/obstacle.py

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

import plotly.graph_objects as go
from build123d import (
    Box,
    BuildPart,
    Face,
    Location,
    Part,
    Plane,
    Pos,
    Rotation,
    Transition,
    Vector,
)
from numpy import linspace
from ocp_vscode import Camera, set_defaults, show

import config
from cad.path_profile_type_shapes import (
    PROFILE_TYPE_FUNCTIONS,
    PathProfileType,
)
from cad.path_segment import PathSegment
from logging_config import configure_logging
from puzzle.grid_layouts.grid_layout_sphere import SphereCasing
from puzzle.node import Node
from visualization.visualization_helpers import (
    plot_casing,
    plot_node_cubes,
    plot_nodes,
    plot_raw_obstacle_path,
    plot_segments,
)

configure_logging()
logger = logging.getLogger(__name__)


class Obstacle(ABC):
    """
    Abstract base class for obstacles in the 3D dexterity puzzle.

    Each obstacle defines its 3D geometry and how it occupies the node grid.
    Obstacles are intended to be integrated into the main puzzle path via
    designated entry and exit nodes.
    """

    def __init__(self, name: str = "Generic Obstacle") -> None:
        """
        Initializes an obstacle instance.
        """
        self.name: str = name
        self.node_size = config.Puzzle.NODE_SIZE

        # Placement attributes (to be set by the manager/placer)
        self.location: Optional[Location] = Location(Pos(Vector(0, 0, 0)))  # Position
        self.grid_origin: tuple[float, float, float] | None = None
        self.rotation_angles_deg: tuple[int, int, int] | None = None

        # Cache for the generated part and occupied nodes
        self._part: Optional[Part] = None
        self._part_extras: Optional[Part] = None
        self.overlap_percentage = 5  # Can be adjusted on a per obstacle basis
        self.occupied_nodes: Optional[list[Node]] = None
        self.overlap_nodes: Optional[list[Node]] = None

        # Path profile selections for visualization and debugging
        self.path_profile_type: PathProfileType = PathProfileType.U_SHAPE

        # Connection path segment (to be determined during obstacle design)
        self.entry_path_segment: PathSegment = PathSegment(
            nodes=[], main_index=0, secondary_index=0
        )
        self.main_path_segment: PathSegment = PathSegment(
            nodes=[], main_index=0, secondary_index=1
        )
        self.main_path_segment.transition_type = Transition.TRANSFORMED
        self.exit_path_segment: PathSegment = PathSegment(
            nodes=[], main_index=0, secondary_index=2
        )

    @abstractmethod
    def create_obstacle_geometry(self):
        """
        Creates the raw 3D geometry (Part) of the obstacle, typically centered
        at the origin before placement.
        """
        pass

    @abstractmethod
    def model_solid(self) -> Part:
        """
        Returns solid model of obstacle, swept path
        """
        pass

    def model_solid_extras(self) -> Part:
        """
        Returns solid model of obstacle extra's ie part's not from path sweep
        """
        pass

    def default_path_profile_type(self, rotation_angle: float = -90) -> Face:
        """Build the configured path profile shape for use in sweeps."""
        profile_type = self.path_profile_type
        profile_params = config.Path.PATH_PROFILE_TYPE_PARAMETERS.get(
            profile_type.value, {}
        )
        profile_factory = PROFILE_TYPE_FUNCTIONS.get(profile_type)

        return profile_factory(**profile_params, rotation_angle=rotation_angle)

    def load_relative_node_coords(self) -> list[Node]:
        """
        Load relative node coordinates from cached json file,
        if not present, determine and store
        """
        cache_dir = Path("obstacles/catalogue/cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        fn = cache_dir / f"{self.name.replace(' ', '_').lower()}_nodes.json"

        if fn.exists():
            with open(fn) as f:
                data = json.load(f)
            occ = data.get("occupied_nodes", [])
            overlap = data.get("overlap_allowed", [])
        else:
            self.create_obstacle_geometry()

            occ_nodes = self.determine_occupied_nodes()

            # TODO add nodes from entry and exit path to ensure they are not blocked
            entry_exit_nodes = self.get_relative_entry_exit_nodes()
            if entry_exit_nodes is not None:
                existing = {(n.x, n.y, n.z) for n in occ_nodes}
                for node in entry_exit_nodes:
                    if (node.x, node.y, node.z) not in existing:
                        occ_nodes.append(node)
                        existing.add((node.x, node.y, node.z))

            occ = [
                dict(
                    x=n.x / self.node_size,
                    y=n.y / self.node_size,
                    z=n.z / self.node_size,
                )
                for n in occ_nodes
            ]
            # Compute overlap_allowed in unit‐space
            overlap_nodes = self.determine_overlap_allowed_nodes(occ_nodes)
            overlap = [
                dict(
                    x=n.x / self.node_size,
                    y=n.y / self.node_size,
                    z=n.z / self.node_size,
                )
                for n in overlap_nodes
            ]
            with open(fn, "w") as f:
                json.dump(
                    {"occupied_nodes": occ, "overlap_allowed": overlap}, f, indent=2
                )

        # rebuild node grid coordinates for puzzle node size
        self.occupied_nodes = [
            Node(
                c["x"] * self.node_size,
                c["y"] * self.node_size,
                c["z"] * self.node_size,
                occupied=True,
            )
            for c in occ
        ]

        self.overlap_nodes = [
            Node(
                c["x"] * self.node_size,
                c["y"] * self.node_size,
                c["z"] * self.node_size,
                overlap_allowed=True,
            )
            for c in overlap
        ]

        return self.occupied_nodes

    def get_placed_obstacle_extras(self) -> Optional[Part]:
        """
        Returns the obstacle's extras, placed according to self.location.
        Caches the unplaced solid once built. The returned Part is a *located copy*,
        so the cached solid remains in local coordinates.
        # TODO reavaluate this approach long term once obstacles are integrated part of puzzle for optimization
        """
        if self.location is None:
            return None

        # Build the local-space solid
        self._part_extras = self.model_solid_extras()

        # Not all obstacles have extra's
        if self._part_extras is None:
            return None

        # Return a located copy
        return self._part_extras.located(self.location)

    def get_placed_node_coordinates(self, nodes: list[Node]) -> list[Node]:
        """
        Transforms the local Node list in-place to world coordinates.
        Updates each Node.x, Node.y, Node.z without creating new Node instances.
        """
        if self.location is None:
            return nodes

        # Update each node in-place
        for n in nodes:
            loc = self.location * Location(Pos(Vector(n.x, n.y, n.z)))
            n.x, n.y, n.z = loc.position.X, loc.position.Y, loc.position.Z
            # TODO, perhaps snap here to grid?

        return nodes

    def get_placed_entry_exit_coords(self) -> Optional[Tuple[tuple, tuple]]:
        """
        Entry/exit in *world* coordinates after placement (self.location).
        """
        if self.location is None:
            return None

        relative_nodes = self.get_relative_entry_exit_nodes()
        if relative_nodes is None:
            return None

        entry_node, exit_node = relative_nodes
        entry_loc = self.location * Location(
            Pos(Vector(entry_node.x, entry_node.y, entry_node.z))
        )
        exit_loc = self.location * Location(
            Pos(Vector(exit_node.x, exit_node.y, exit_node.z))
        )

        entry_coord = (entry_loc.position.X, entry_loc.position.Y, entry_loc.position.Z)
        exit_coord = (exit_loc.position.X, exit_loc.position.Y, exit_loc.position.Z)

        return entry_coord, exit_coord

    def get_relative_entry_exit_nodes(self) -> Optional[Tuple[Node, Node]]:
        """Return the local-space entry and exit nodes for the obstacle.

        Prefer the explicit entry/exit helper segments if present; fall back
        to the main path’s start/end otherwise.
        """
        entry_nodes = self.entry_path_segment.nodes
        exit_nodes = self.exit_path_segment.nodes

        def _snap(v: float) -> float:
            return round(v / self.node_size) * self.node_size

        if entry_nodes and exit_nodes:
            e0 = entry_nodes[0]
            x1 = exit_nodes[-1]
            entry_node = Node(_snap(e0.x), _snap(e0.y), _snap(e0.z), occupied=True)
            exit_node = Node(_snap(x1.x), _snap(x1.y), _snap(x1.z), occupied=True)
            return entry_node, exit_node

        # Fallback to main path start/end if helpers are missing
        if self.main_path_segment.path is None:
            self.create_obstacle_geometry()
        if self.main_path_segment.path is None:
            return None

        start = self.main_path_segment.path @ 0
        end = self.main_path_segment.path @ 1
        entry_node = Node(_snap(start.X), _snap(start.Y), _snap(start.Z), occupied=True)
        exit_node = Node(_snap(end.X), _snap(end.Y), _snap(end.Z), occupied=True)
        return entry_node, exit_node

    def get_placed_entry_exit_nodes(self) -> Optional[Tuple[Node, Node]]:
        """
        Return the entry and exit nodes transformed into world coordinates.
        # TODO some akward recreation of nodes going on here
        """

        if self.location is None:
            return None

        relative_nodes = self.get_relative_entry_exit_nodes()
        if relative_nodes is None:
            return None

        entry_node, exit_node = relative_nodes
        entry_loc = self.location * Location(
            Pos(Vector(entry_node.x, entry_node.y, entry_node.z))
        )
        exit_loc = self.location * Location(
            Pos(Vector(exit_node.x, exit_node.y, exit_node.z))
        )

        placed_entry = Node(
            entry_loc.position.X,
            entry_loc.position.Y,
            entry_loc.position.Z,
            occupied=True,
        )

        placed_exit = Node(
            exit_loc.position.X,
            exit_loc.position.Y,
            exit_loc.position.Z,
            occupied=True,
        )

        return placed_entry, placed_exit

    def set_placement(self, location: Location):
        """TODO Directly sets the obstacle's placement location."""
        self.location = location
        # Clear caches as placement changed
        self._part = None
        self._occupied_node_coords = None
        self.entry_node = None
        self.exit_node = None

    def rotate(self, rotation: Rotation):
        """Rotates the obstacle around its current origin."""
        if self.location:
            self.location *= rotation
            # Clear caches
            self._part = None
            self._occupied_node_coords = None
            self.entry_node = None
            self.exit_node = None
        else:
            # If not placed yet, initialize location with rotation
            self.location = Location(rotation)

    def translate(self, vector: Vector):
        """Translates the obstacle."""
        if self.location:
            self.location *= Pos(vector)
            # Clear caches
            self._part = None
            self._occupied_node_coords = None
            self.entry_node = None
            self.exit_node = None
        else:
            # If not placed yet, initialize location with translation
            self.location = Location(Pos(vector))

    def visualize(self):
        """
        Plot this obstacle's occupied nodes, basic puzzle casing and raw path
        using Plotly helper functions.
        """
        fig = go.Figure()
        # Occupied nodes and cubes
        occupied_nodes = self.get_placed_node_coordinates(self.occupied_nodes)
        for t in plot_nodes(nodes=occupied_nodes, group_name="Occupied Nodes"):
            fig.add_trace(t)
        for t in plot_node_cubes(
            nodes=occupied_nodes, node_size=self.node_size, group_name="Occupied Nodes"
        ):
            fig.add_trace(t)

        # Overlap nodes and cubes
        overlap_nodes = self.get_placed_node_coordinates(self.overlap_nodes)
        for t in plot_nodes(nodes=overlap_nodes, group_name="Overlap Nodes"):
            fig.add_trace(t)
        for t in plot_node_cubes(
            nodes=overlap_nodes, node_size=self.node_size, group_name="Overlap Nodes"
        ):
            fig.add_trace(t)

        # Sample points along path segment edge for visualization
        self.create_obstacle_geometry()
        path = self.sample_obstacle_path()
        for trace in plot_raw_obstacle_path(path, name=f"{self.name} Raw Path"):
            fig.add_trace(trace)

        # Entry and exit path visualization
        for trace in plot_segments([self.entry_path_segment, self.exit_path_segment]):
            fig.add_trace(trace)

        # Casing, for reference only
        casing = SphereCasing(
            diameter=config.Sphere.SPHERE_DIAMETER,
            shell_thickness=config.Sphere.SHELL_THICKNESS,
        )
        for trace in plot_casing(casing):
            fig.add_trace(trace)

        fig.update_layout(title=f"{self.name} obstacle view", template="plotly_dark")
        fig.show()

    def determine_occupied_nodes(self, grid_count: int = 30) -> list[Node]:
        """
        Determine occupied nodes by testing a `grid_count^3` cube grid around the origin.

        A node is considered occupied iff the intersection volume between the node's cube
        and the obstacle solid is >= `min_overlap_pct` percent of the cube's volume.

        Parameters:
            grid_count (int): Number of cubes to evaluate along each axis. The value is
                coerced to an odd count so the origin is sampled.
            min_overlap_pct (float): Minimum % of cube volume that must be overlapped by
                the obstacle for the node to be marked occupied. Example: 5.0 -> 5%.

        Returns:
            list[Node]: Nodes whose cube volume overlaps the obstacle geometry
                        by at least `min_overlap_pct` percent.
        """
        start_time = time.perf_counter()

        # Convert overlap percentage to fraction [0.0, 1.0]
        min_overlap_pct = self.overlap_percentage
        overlap_threshold = max(0.0, min(min_overlap_pct, 100.0)) / 100.0

        # Prepare node grid
        node_size = config.Puzzle.NODE_SIZE
        if grid_count % 2 == 0:
            grid_count += 1
        half = grid_count // 2
        coords = [(i * node_size) for i in range(-half, half + 1)]

        # Create obstacle solid with fully filled rectangle sweep
        # Swap back and forth the original type
        original_profile_type = self.path_profile_type  # Store
        self.path_profile_type = PathProfileType.SQUARE_CLOSED_SHAPE
        obstacle_solid = self.model_solid()
        self.path_profile_type = original_profile_type  # Restore

        # fetch the raw bounding box and pad by half a node so we don't miss border cells
        bbox = obstacle_solid.bounding_box()
        orig_min = bbox.min  # Vector(xmin, ymin, zmin)
        orig_max = bbox.max  # Vector(xmax, ymax, zmax)

        pad = node_size / 2.0
        min_pt = Vector(orig_min.X - pad, orig_min.Y - pad, orig_min.Z - pad)
        max_pt = Vector(orig_max.X + pad, orig_max.Y + pad, orig_max.Z + pad)

        occupied: list[Node] = []
        tested_centers: list[tuple[float, float, float]] = []

        cube_volume = node_size**3
        # tiny tolerance to avoid floating-point chatter around the threshold
        eps = 1e-9 * cube_volume

        for x in coords:
            if x < min_pt.X or x > max_pt.X:
                continue
            for y in coords:
                if y < min_pt.Y or y > max_pt.Y:
                    continue
                for z in coords:
                    if z < min_pt.Z or z > max_pt.Z:
                        continue

                    tested_centers.append((x, y, z))
                    cube = (
                        Plane.XY * Pos(x, y, z) * Box(node_size, node_size, node_size)
                    )

                    # Boolean intersect
                    inter = cube & obstacle_solid

                    if inter is None:
                        continue

                    solids = inter.solids()
                    if not solids:
                        if x == 0.0 and y == 0.0 and z == 0.0:
                            logger.debug(
                                "No intersection solids at cube center (%.3f, %.3f, %.3f)",
                                x,
                                y,
                                z,
                            )
                        continue

                    # Sum volumes in case the intersection yields multiple solids
                    overlap_volume = 0.0
                    for s in solids:
                        overlap_volume += s.volume

                    # Check the treshold
                    if overlap_volume + eps >= overlap_threshold * cube_volume:
                        occupied.append(Node(x, y, z, occupied=True))

        elapsed = time.perf_counter() - start_time
        logger.info(
            "determine_occupied_nodes took %.3f s – tested %d cubes, occupied nodes: %d, threshold: %.2f%%",
            elapsed,
            len(tested_centers),
            len(occupied),
            min_overlap_pct,
        )

        return occupied

    def determine_overlap_allowed_nodes(self, occupied: list[Node]) -> list[Node]:
        """cardinal 6‐neigh offsets in world coords"""
        offs = [
            (self.node_size, 0, 0),
            (-self.node_size, 0, 0),
            (0, self.node_size, 0),
            (0, -self.node_size, 0),
            (0, 0, self.node_size),
            (0, 0, -self.node_size),
        ]
        s = {(n.x, n.y, n.z) for n in occupied}
        shell = set()
        for x, y, z in s:
            for dx, dy, dz in offs:
                nb = (x + dx, y + dy, z + dz)
                if nb not in s:
                    shell.add(nb)
        return [
            Node(x, y, z, occupied=False, overlap_allowed=True) for x, y, z in shell
        ]

    @staticmethod
    def solid_model_node_cubes(
        nodes: list[Node], name="Node", color="#FFFFFF1D"
    ) -> list[Part]:
        """
        For each Node provided, build a cube Part of size node_size
        centered at (node.x, node.y, node.z).

        Tag each Part with label and color
        Returns the list of these Parts.
        """
        if not nodes:
            return []

        node_size = config.Puzzle.NODE_SIZE
        cubes: list[Part] = []

        # Create each cube
        for idx, node in enumerate(nodes, start=1):
            with BuildPart() as cube_bp:
                Box(node_size, node_size, node_size)
            cube = cube_bp.part
            cube.position = Vector(node.x, node.y, node.z)
            cube.label = f"{name} {idx}"
            cube.color = color
            cubes.append(cube)

        return cubes

    def sample_obstacle_path(self) -> list[Vector]:
        """Local (not placed) sample points along obstacle path"""
        samples = 35

        if self.main_path_segment.path is None:
            self.create_obstacle_geometry()

        if self.main_path_segment.path is None:
            return [Vector(0, 0, 0)]
        ts = linspace(0.0, 1.0, samples)
        return [self.main_path_segment.path @ float(t) for t in ts]

    def sample_obstacle_path_world(self) -> list[Vector]:
        """Sample points in world coordinates ie placed location"""
        pts = self.sample_obstacle_path()
        if self.location is None:
            return pts

        # TODO fix this properly with improved local and world position get methods
        # When PathArchitect locks the main path segment after applying the
        # obstacle's world transform, sampling already returns world-space
        # coordinates. Skip reapplying the placement transform in that case to
        # avoid rotating/translating twice in visualizations.
        if self.main_path_segment.lock_path and self.main_path_segment.path is not None:
            return pts

        placed: list[Vector] = []
        for point in pts:
            loc = self.location * Location(point)

            placed.append(Vector(loc.position.X, loc.position.Y, loc.position.Z))
        return placed

    def show_solid_model(self):
        """
        Build the obstacle solid, its occupied and
        overlap node cubes, and show them.
        """
        self.create_obstacle_geometry()
        obstacle_solid = self.model_solid()

        # cubes
        occupied_cubes = self.solid_model_node_cubes(
            nodes=self.occupied_nodes,
            name="Occupied Node",
            color="#40004947",
        )
        overlap_cubes = self.solid_model_node_cubes(
            nodes=self.overlap_nodes,
            name="Overlap Node",
            color="#00444900",
        )

        set_defaults(reset_camera=Camera.KEEP)

        # show everything with custom group names
        show(
            obstacle_solid,
            occupied_cubes,
            overlap_cubes,
            names=[
                f"{self.name} Solid",
                "Occupied Nodes",
                "Overlap Nodes",
            ],
        )
