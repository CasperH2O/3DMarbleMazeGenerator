# obstacles/obstacle.py


import random
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import plotly.graph_objects as go
from build123d import Location, Part, Pos, Rotation, Vector

import config
from puzzle.casing import SphereCasing
from puzzle.node import Node
from visualization.plotly_helpers import plot_casing_plotly, plot_nodes_plotly


class Obstacle(ABC):
    # TODO crazy idea, make a segment object part of the obstacle and let it handle sweeping and connections?

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

        # Set the random seed for reproducibility if needed internally
        random.seed(config.Puzzle.SEED)

    @abstractmethod
    def create_obstacle_geometry(self) -> Part:
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
        Plot this obstacle's occupied nodes and the puzzle casing
        using Plotly helper functions.
        """
        placed_nodes = self.get_placed_occupied_coords(config.Puzzle.NODE_SIZE)
        if not placed_nodes:
            raise RuntimeError(
                f"{self.name!r} has no placement; call set_placement() first."
            )

        fig = go.Figure()
        for trace in plot_nodes_plotly(placed_nodes):
            fig.add_trace(trace)

        casing = SphereCasing(
            diameter=config.Sphere.SPHERE_DIAMETER,
            shell_thickness=config.Sphere.SHELL_THICKNESS,
        )
        for trace in plot_casing_plotly(casing):
            fig.add_trace(trace)

        fig.update_layout(title=f"{self.name} obstacle view", template="plotly_dark")
        fig.show()
