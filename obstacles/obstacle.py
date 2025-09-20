# obstacles/obstacle.py

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

import plotly.graph_objects as go
from build123d import Box, BuildPart, Location, Part, Plane, Pos, Rotation, Vector, add
from numpy import linspace
from ocp_vscode import show

import config
from cad.path_segment import PathSegment
from puzzle.casing import SphereCasing
from puzzle.node import Node
from visualization.plotly_helpers import (
    plot_casing_plotly,
    plot_node_cubes_plotly,
    plot_nodes_plotly,
    plot_raw_obstacle_path_plotly,
)


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
        # Placement attributes (to be set by the manager/placer)
        self.location: Optional[Location] = Location(Pos(Vector(0, 0, 0)))  # Position
        # Todo, origin and orientation
        # self.orientation: Optional[Vector]

        # Connection points (to be determined after CAD design)
        # Should correspond to specific nodes in the main grid
        self.entry_node: Optional[Node] = None
        self.exit_node: Optional[Node] = None

        # Cache for the generated part and occupied nodes
        self._part: Optional[Part] = None
        self.occupied_nodes: Optional[List[Node]] = None
        self.overlap_nodes: Optional[List[Node]] = None
        self.path_segment: Optional[PathSegment] = PathSegment(
            nodes=[(0, 0, 0)], main_index=0, secondary_index=0
        )

        self._raw_unit_coords = [(0, 0, 0)]

        self.node_size = config.Puzzle.NODE_SIZE

    @abstractmethod
    def create_obstacle_geometry(self):
        """
        Creates the raw 3D geometry (Part) of the obstacle, typically centered
        at the origin before placement.

        Returns:
            Part: The Build123D Part representing the obstacle's shape.
        """
        pass

    @abstractmethod
    def model_solid(self) -> Part:
        """
        Returns solid model of obstacle
        """
        pass

    def load_relative_node_coords(self):
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
            occ = [
                dict(
                    x=n.x / self.node_size,
                    y=n.y / self.node_size,
                    z=n.z / self.node_size,
                )
                for n in occ_nodes
            ]
            # 2) compute overlap_allowed in unit‐space
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

        # rebuild Node objects in world‐space
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

    def get_placed_part(self) -> Optional[Part]:
        """
        Returns the obstacle's Part, placed according to self.location.
        Caches the unplaced solid once built. The returned Part is a *located copy*,
        so the cached solid remains in local coordinates.
        # TODO reavaluate this approach long term
        """
        if self.location is None:
            return None

        # Build the local-space solid
        self._part = self.model_solid()

        # Return a located copy
        return self._part.located(self.location)

    def get_placed_node_coordinates(self, nodes: List[Node]) -> List[Node]:
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

        return nodes

    def get_relative_entry_exit_coords(self) -> Optional[Tuple[Vector, Vector]]:
        """
        Return entry/exit in *local* coordinates (before placement).
        Uses the start and end of the obstacle's path.
        """
        # Ensure the path exists even when node cache made geometry optional
        if getattr(self.path_segment, "path", None) is None:
            self.create_obstacle_geometry()
        if self.path_segment.path is None:
            return None

        start = self.path_segment.path @ 0
        end = self.path_segment.path @ 1
        return Vector(start.X, start.Y, start.Z), Vector(end.X, end.Y, end.Z)

    def get_placed_entry_exit_coords(self) -> Optional[Tuple[tuple, tuple]]:
        """
        Entry/exit in *world* coordinates after placement (self.location).
        """
        if self.location is None:
            return None

        rel = self.get_relative_entry_exit_coords()
        if rel is None:
            return None
        relative_entry, relative_exit = rel

        entry_loc = self.location * Location(relative_entry)
        exit_loc = self.location * Location(relative_exit)

        entry_coord = (entry_loc.position.X, entry_loc.position.Y, entry_loc.position.Z)
        exit_coord = (exit_loc.position.X, exit_loc.position.Y, exit_loc.position.Z)
        return entry_coord, exit_coord

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
        for t in plot_nodes_plotly(occupied_nodes):
            fig.add_trace(t)
        for t in plot_node_cubes_plotly(occupied_nodes, self.node_size):
            fig.add_trace(t)

        # Overlap nodes and cubes
        overlap_nodes = self.get_placed_node_coordinates(self.overlap_nodes)
        for t in plot_nodes_plotly(overlap_nodes):
            fig.add_trace(t)
        for t in plot_node_cubes_plotly(overlap_nodes, self.node_size):
            fig.add_trace(t)

        # Sample points along path segment edge for visualization
        self.create_obstacle_geometry()
        path = self.sample_obstacle_path()
        for trace in plot_raw_obstacle_path_plotly(path, name=f"{self.name} Raw Path"):
            fig.add_trace(trace)

        # Casing
        casing = SphereCasing(
            diameter=config.Sphere.SPHERE_DIAMETER,
            shell_thickness=config.Sphere.SHELL_THICKNESS,
        )
        for trace in plot_casing_plotly(casing):
            fig.add_trace(trace)

        fig.update_layout(title=f"{self.name} obstacle view", template="plotly_dark")
        fig.show()

    def determine_occupied_nodes(
        self,
        grid_count: int = 30,
        show_3d: bool = False,
    ) -> list[Node]:
        """
        Build a grid of `grid_count^3` cubes of side `node_size`, centered at the world origin,
        cull by the obstacle’s bounding box ±½ cube, and return the occupied nodes.

        visualize=True → show obstacle + padded bbox + tested cubes.
        print_node_xyz=True → print a 'raw_coords = [ (i,j,k), ... ]' list,
                             where i,j,k = node_center / node_size.
        """
        start_time = time.perf_counter()
        grid_count = 30
        if grid_count % 2 == 0:
            grid_count += 1

        node_size = config.Puzzle.NODE_SIZE
        half = grid_count // 2
        coords = [(i * node_size) for i in range(-half, half + 1)]

        # get obstacle solid
        obstacle_solid = self.model_solid()
        if obstacle_solid is None:
            raise RuntimeError("Obstacle not created yet")

        # fetch the raw bounding box
        bbox = obstacle_solid.bounding_box()
        orig_min = bbox.min  # Vector of (xmin, ymin, zmin)
        orig_max = bbox.max  # Vector of (xmax, ymax, zmax)

        pad = node_size / 2.0

        # manually build the padded corners
        min_pt = Vector(orig_min.X - pad, orig_min.Y - pad, orig_min.Z - pad)
        max_pt = Vector(orig_max.X + pad, orig_max.Y + pad, orig_max.Z + pad)

        occupied: list[Node] = []
        # collect cube‐positions (for visualize)
        tested_centers = []

        # cull cubes outside of bounding box, determine intersection
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
                    if (cube & obstacle_solid).solids():
                        occupied.append(Node(x, y, z, occupied=True))

        if show_3d:
            # build one combined debug Part
            with BuildPart() as dbg:
                # padded bbox as a big box
                # center + extents
                cx = (min_pt.X + max_pt.X) / 2
                cy = (min_pt.Y + max_pt.Y) / 2
                cz = (min_pt.Z + max_pt.Z) / 2
                dx = max_pt.X - min_pt.X
                dy = max_pt.Y - min_pt.Y
                dz = max_pt.Z - min_pt.Z
                add(Plane.XY * Pos(cx, cy, cz) * Box(dx, dy, dz))

            dbg.part.color = "#25F3FA36"
            show((dbg.part, obstacle_solid))

        elapsed = time.perf_counter() - start_time
        print(
            f"determine_occupied_nodes took {elapsed:.3f} s – tested {len(tested_centers)} cubes, occupied nodes: {len(occupied)}"
        )

        return occupied

    def determine_overlap_allowed_nodes(self, occupied: List[Node]) -> List[Node]:
        # cardinal 6‐neigh offsets in world coords
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

    def solid_model_node_cubes(
        self, nodes: List[Node], name="Node", color="#FFFFFF1D"
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
        samples = 50

        if self.path_segment.path is None:
            return [Vector(0, 0, 0)]
        ts = linspace(0.0, 1.0, samples)
        return [self.path_segment.path @ float(t) for t in ts]

    def sample_obstacle_path_world(self) -> list[Vector]:
        """Sample points in world coordinates ie placed location"""
        pts = self.sample_obstacle_path()
        if self.location is None:
            return pts
        placed = []
        for p in pts:
            loc = self.location * Location(p)
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
