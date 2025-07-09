# obstacles/obstacle.py

import random
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import plotly.graph_objects as go
from build123d import Box, BuildPart, Location, Part, Plane, Pos, Rotation, Vector, add
from numpy import linspace
from ocp_vscode import show

import config
from cad.path_segment import PathSegment
from puzzle.casing import SphereCasing
from puzzle.node import Node
from puzzle.node_creator import frange, snap
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
        self.location: Optional[Location] = Location(
            Pos(Vector(0, 0, 0))
        )  # Position and orientation

        # Connection points (to be determined after placement)
        # These should correspond to specific nodes in the main grid
        self.entry_node: Optional[Node] = None
        self.exit_node: Optional[Node] = None

        # Cache for the generated part and occupied nodes
        self._part: Optional[Part] = None
        self._occupied_nodes: Optional[List[Node]] = None
        self.path_segment: Optional[PathSegment] = PathSegment(
            nodes=[(0, 0, 0)], main_index=0, secondary_index=0
        )

        self.raw_path: Optional[List[Node]] = None

        # Set the random seed for reproducibility if needed internally
        random.seed(config.Puzzle.SEED)

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
    def get_relative_occupied_coords(self, node_size: float) -> List[Vector]:
        """
        Determines the coordinates of the grid nodes that this obstacle would
        occupy, relative to its origin (0,0,0), *before* placement.

        Parameters:
            node_size (float): The spacing of the puzzle grid.

        Returns:
            List[Coordinate]: A list of (x, y, z) tuples relative to the obstacle origin.
        """
        pass

    @abstractmethod
    def get_relative_entry_exit_coords(self) -> Tuple[Vector, Vector]:
        """
        Returns the relative coordinates for the entry and exit points
        of the obstacle, before placement. These points should align with
        potential node locations in the grid.

        Returns:
            Tuple[Coordinate, Coordinate]: (entry_coord, exit_coord) relative to origin.
        """
        pass

    @abstractmethod
    def model_solid(self) -> Part:
        """
        Returns solid model of obstacle
        """
        pass

    def get_placed_part(self) -> Optional[Part]:
        """
        Returns the obstacle's Part, placed according to self.location.
        Caches the part creation.
        """
        if self.location is None:
            # print(f"Warning: Cannot get placed part for {self.name} without location.")
            return None
        if self._part is None:
            self._part = self.create_obstacle_geometry()
        # Apply the location transform
        return self._part.located(self.location)

    def get_placed_occupied_coords(self, node_size: float) -> Optional[List[Node]]:
        """
        Transforms the local Node list in-place to world coordinates.
        Updates each Node.x, Node.y, Node.z without creating new Node instances.
        """
        if self.location is None:
            return None

        # Lazy-load local Node list
        if self._occupied_nodes is None:
            self._occupied_nodes = self.get_relative_occupied_coords(node_size)

        # Update each node in-place
        for node in self._occupied_nodes:
            rel_loc = Location(Pos(Vector(node.x, node.y, node.z)))
            abs_loc = self.location * rel_loc
            node.x = abs_loc.position.X
            node.y = abs_loc.position.Y
            node.z = abs_loc.position.Z

        return self._occupied_nodes

    def get_placed_entry_exit_coords(self) -> Optional[Tuple[Vector, Vector]]:
        """Calculates the absolute world coordinates of entry/exit points after placement."""
        if self.location is None:
            # print(f"Warning: Cannot get placed entry/exit for {self.name} without location.")
            return None

        relative_entry, relative_exit = self.get_relative_entry_exit_coords()

        entry_loc = self.location * Location(relative_entry)
        exit_loc = self.location * Location(relative_exit)

        entry_coord = (entry_loc.position.X, entry_loc.position.Y, entry_loc.position.Z)
        exit_coord = (exit_loc.position.X, exit_loc.position.Y, exit_loc.position.Z)

        return entry_coord, exit_coord

    # Basic translate/rotate methods - might need more complex logic if
    # internal state depends on orientation. These just update the location.
    def set_placement(self, location: Location):
        """Directly sets the obstacle's placement location."""
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
        placed_nodes = self.get_placed_occupied_coords(config.Puzzle.NODE_SIZE)
        if not placed_nodes:
            raise RuntimeError(
                f"{self.name!r} has no placement; call set_placement() first."
            )

        fig = go.Figure()

        # Occupied nodes
        for trace in plot_nodes_plotly(placed_nodes):
            fig.add_trace(trace)

        # Occupied node cubes
        for trace in plot_node_cubes_plotly(placed_nodes, config.Puzzle.NODE_SIZE):
            fig.add_trace(trace)

        # Raw path
        if self.raw_path:
            for trace in plot_raw_obstacle_path_plotly(
                self.raw_path, name=f"{self.name} Raw Path"
            ):
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
        visualize: bool = False,
        print_node_xyz: bool = False,
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

        if visualize:
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

        # optional print of raw grid indices
        if print_node_xyz:
            # snap to clean floats, then cast to int
            raw = [
                (
                    snap(n.x / node_size),
                    snap(n.y / node_size),
                    snap(n.z / node_size),
                )
                for n in occupied
            ]
            # dedupe & sort by (z,y,x)
            unique = sorted(set(raw), key=lambda t: (t[2], t[1], t[0]))
            print("raw_coords = [")
            for x, y, z in unique:
                print(f"    ({x}, {y}, {z}),")
            print("]")

        elapsed = time.perf_counter() - start_time
        print(
            f"determine_occupied_nodes took {elapsed:.3f} s – tested {len(tested_centers)} cubes"
        )

        return occupied

    def create_occupied_node_cubes(self) -> list[Part]:
        """
        For each Node in self._occupied_nodes, build a cube of size node_size
        centered at (node.x, node.y, node.z). Tag each Part with:
        • part.label = "occupied_node"
        • part.color = semi-transparent blue (alpha = 0.2)
        Returns the list of these Parts.
        """
        if not self._occupied_nodes:
            return []

        node_size = config.Puzzle.NODE_SIZE
        cubes: list[Part] = []

        for node in self._occupied_nodes:  # Node.x, .y, .z are world coords
            # build a little cube at the node
            with BuildPart() as cube_bp:
                Box(node_size, node_size, node_size)
            cube_bp.part.position = Vector(node.x, node.y, node.z)
            cube_part = cube_bp.part
            # label & color metadata on the Part
            cube_part.label = "Occupied Node"
            cube_part.color = "#7000741C"
            cubes.append(cube_part)

        return cubes

    def sample_obstacle_path(self):
        # Sample line and get raw points
        samples = 50
        ts = linspace(0.0, 1.0, samples)
        self.raw_path: list[Vector] = [self.path_segment.path @ t for t in ts]
