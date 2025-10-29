# obstacles/obstacle.py
import copy
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

import plotly.graph_objects as go
from build123d import (
    Box,
    BuildLine,
    BuildPart,
    Face,
    Location,
    Part,
    Plane,
    Polyline,
    Pos,
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
from puzzle.utils.geometry import frange, snap
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
        Solid model the obstacle, used for:
        - determining occupied nodes
        - individual obstacle preview
        - obstacle overview

        Not used for modelling obstacles for puzzle
        """
        pass

    def model_solid_extras(self) -> Part:
        """
        Returns solid model of obstacle extra's ie part's not from path sweep
        TODO Remove, keep as placeholder or create basic example implementation?
        """
        pass

    def _ensure_entry_exit_paths(self) -> None:
        """Ensure entry and exit path segments have Build123d wires assigned."""

        def _build_wire_from_nodes(segment: PathSegment) -> None:
            if segment.path is not None or len(segment.nodes) < 2:
                return

            with BuildLine() as line_builder:
                Polyline(*[(node.x, node.y, node.z) for node in segment.nodes])

            segment.path = line_builder.line

        _build_wire_from_nodes(self.entry_path_segment)
        _build_wire_from_nodes(self.exit_path_segment)

    def default_path_profile_type(self, rotation_angle: float = -90) -> Face:
        """
        Build the configured path profile shape for use in sweeps.

        Used by obstacle preview, obstacle overview and determining occupied nodes.
        """
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

            # Add nodes from entry and exit paths to ensure they are not blocked
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

        # Rebuild node grid coordinates for puzzle node size
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

    def _apply_location(self, nodes: list[Node]) -> list[Node]:
        """Apply the obstacle's placement location to the supplied nodes."""

        if self.location is None:
            return nodes

        for node in nodes:
            loc = self.location * Location(Pos(Vector(node.x, node.y, node.z)))
            node.x, node.y, node.z = (
                loc.position.X,
                loc.position.Y,
                loc.position.Z,
            )

        return nodes

    def get_placed_node_coordinates(self, nodes: list[Node] | None) -> list[Node]:
        """Return transformed *copies* of nodes expressed in local coordinates."""

        if not nodes:
            return []

        copies = [copy.deepcopy(node) for node in nodes]
        return self._apply_location(copies)

    def world_nodes(
        self, nodes: list[Node] | None, *, snap_to_grid: bool = False
    ) -> list[Node]:
        """Return placed helper nodes suitable for path splicing."""

        if not nodes:
            return []

        clones = [
            Node(
                node.x,
                node.y,
                node.z,
                occupied=node.occupied,
                overlap_allowed=node.overlap_allowed,
                in_circular_grid=node.in_circular_grid,
                in_rectangular_grid=node.in_rectangular_grid,
            )
            for node in nodes
        ]

        placed = self._apply_location(clones)

        if snap_to_grid:
            for node in placed:
                node.x = snap(round(node.x / self.node_size) * self.node_size)
                node.y = snap(round(node.y / self.node_size) * self.node_size)
                node.z = snap(round(node.z / self.node_size) * self.node_size)

        return placed

    def get_placed_entry_exit_coords(self) -> Optional[Tuple[tuple, tuple]]:
        """
        Entry/exit in *world* coordinates after placement (self.location).
        """
        placed_nodes = self.get_placed_entry_exit_nodes()
        if placed_nodes is None:
            return None

        entry_node, exit_node = placed_nodes

        entry_coord = (entry_node.x, entry_node.y, entry_node.z)
        exit_coord = (exit_node.x, exit_node.y, exit_node.z)

        return entry_coord, exit_coord

    def get_relative_entry_exit_nodes(self) -> Optional[Tuple[Node, Node]]:
        """Return the local-space entry and exit nodes for the obstacle.

        Prefer the explicit entry/exit helper segments if present; fall back
        to the main path’s start/end otherwise.
        """
        entry_nodes = self.entry_path_segment.nodes
        exit_nodes = self.exit_path_segment.nodes

        if not entry_nodes or not exit_nodes:
            # Lazily build the geometry so helper segments become available
            self.create_obstacle_geometry()
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
        logger.warning(
            "Obstacle: %s. has no proper entry and exit nodes, falling back to base geometry",
            self.name,
        )

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
        """Return the entry and exit nodes transformed into world coordinates."""

        if self.location is None:
            return None

        relative_nodes = self.get_relative_entry_exit_nodes()
        if relative_nodes is None:
            return None

        placed_nodes = self.world_nodes(list(relative_nodes))
        if len(placed_nodes) < 2:
            return None

        return placed_nodes[0], placed_nodes[1]

    def set_placement(self, location: Location):
        """
        Directly sets the obstacle's placement location.
        TODO Do more with this, handle cache etc?
        """
        self.location = location
        # Clear caches as placement changed
        self._part = None
        self._occupied_node_coords = None
        self.entry_node = None
        self.exit_node = None

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

    def determine_occupied_nodes(self) -> list[Node]:
        """
        Determine occupied nodes by scanning only lattice cells whose centers fall within
        a padded AABB (axis-aligned bounding box) of the obstacle solid.

        A node is considered occupied iff the intersection volume between the node's cube
        and the obstacle solid is >= `min_overlap_pct` percent of the cube's volume.
        """
        start_time = time.perf_counter()

        # Convert overlap percentage to fraction [0.0, 1.0]
        min_overlap_pct = self.overlap_percentage
        overlap_threshold = max(0.0, min(min_overlap_pct, 100.0)) / 100.0

        node_size = config.Puzzle.NODE_SIZE
        cube_volume = node_size**3
        eps = 1e-9 * cube_volume  # tiny tolerance to avoid floating-point chatter

        # Build the obstacle solid using the fully filled rectangle sweep
        original_profile_type = self.path_profile_type
        self.path_profile_type = PathProfileType.SQUARE_CLOSED_SHAPE
        obstacle_solid = self.model_solid()
        self.path_profile_type = original_profile_type

        # Bounding box of obstacle, padded by half a node so border cells are included
        bbox = obstacle_solid.bounding_box()
        pad = node_size / 2.0
        min_pt = Vector(bbox.min.X - pad, bbox.min.Y - pad, bbox.min.Z - pad)
        max_pt = Vector(bbox.max.X + pad, bbox.max.Y + pad, bbox.max.Z + pad)

        # Coordinates: multiples of node_size within [min_pt, max_pt]
        # frange() keeps them aligned to the global lattice (…,-2h,-h,0,h,2h,…)
        x_values = frange(min_pt.X, max_pt.X, node_size)
        y_values = frange(min_pt.Y, max_pt.Y, node_size)
        z_values = frange(min_pt.Z, max_pt.Z, node_size)

        occupied: list[Node] = []
        tested_count = 0

        for x in x_values:
            for y in y_values:
                for z in z_values:
                    tested_count += 1

                    # Lattice cell centered at (x,y,z)
                    cube = (
                        Plane.XY * Pos(x, y, z) * Box(node_size, node_size, node_size)
                    )

                    # Boolean intersect
                    inter = cube & obstacle_solid
                    if inter is None:
                        continue

                    solids = inter.solids()
                    if not solids:
                        continue

                    # Sum volumes in case the intersection yields multiple solids
                    overlap_volume = sum(s.volume for s in solids)

                    # Check threshold
                    if overlap_volume + eps >= overlap_threshold * cube_volume:
                        occupied.append(Node(x, y, z, occupied=True))

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Obstacle: %s. "
            "Determining occupied nodes took %.3f s – tested %d cubes, occupied: %d, "
            "threshold: %.2f%%",
            self.name,
            elapsed,
            tested_count,
            len(occupied),
            min_overlap_pct,
        )

        return occupied

    def determine_overlap_allowed_nodes(self, occupied: list[Node]) -> list[Node]:
        """
        Find neighbor nodes in the six cardinal directions that can overlap
        without colliding with occupied nodes.

        The search expands outward in a n-layer shell (n node sizes away)
        to provide additional flexibility for obstacle placement while
        still avoiding occupied coordinates.
        """

        shells_layer_amount = 1  # [1, 2, 3 etc] amount of shell nodes
        shell_layers = list(range(1, shells_layer_amount + 1))

        # Define the six cardinal direction unit offsets around each occupied node.
        cardinal_directions = [
            (1, 0, 0),
            (-1, 0, 0),
            (0, 1, 0),
            (0, -1, 0),
            (0, 0, 1),
            (0, 0, -1),
        ]

        # Store occupied coordinates for quick membership checks while iterating neighbors.
        occupied_coordinate_set = {(node.x, node.y, node.z) for node in occupied}

        # Explore neighbors around each occupied node to build the allowed set.
        candidate_overlap_coordinates: set[tuple[float, float, float]] = set()
        for occupied_x, occupied_y, occupied_z in occupied_coordinate_set:
            for distance_multiplier in shell_layers:
                offset_scale = self.node_size * distance_multiplier
                for direction_x, direction_y, direction_z in cardinal_directions:
                    neighbor_coordinate = (
                        occupied_x + direction_x * offset_scale,
                        occupied_y + direction_y * offset_scale,
                        occupied_z + direction_z * offset_scale,
                    )
                    if neighbor_coordinate not in occupied_coordinate_set:
                        candidate_overlap_coordinates.add(neighbor_coordinate)

        # Convert the coordinate tuples into Node instances marked as overlap-allowed.
        return [
            Node(x, y, z, occupied=False, overlap_allowed=True)
            for x, y, z in candidate_overlap_coordinates
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
        Build the obstacle solid, its occupied and overlap node cubes,
        and show them.
        """

        # Obstacles
        self.create_obstacle_geometry()
        obstacle_solid = self.model_solid()

        # Cubes
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

        # Show everything with custom group names
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
