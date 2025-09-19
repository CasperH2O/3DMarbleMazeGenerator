# obstacles/obstacle_manager.py

import random
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
from build123d import Axis, Rotation, Vector

import obstacles.catalogue  # ensure registration
from config import Config
from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import get_available_obstacles, get_obstacle_class
from puzzle.node import Node


def _quantize_coord(val: float, node_size: float) -> float:
    """Snap a coordinate to the nearest grid multiple to avoid floating-point drift."""
    return round(val / node_size) * node_size


class ObstacleManager:
    """
    Manages the selection, placement, and node occupation of obstacles.
    """

    def __init__(self, nodes: List[Node]) -> None:
        """
        Initializes the obstacle manager.

        Parameters:
            puzzle nodes: puzzle nodes, for placement of the nodes.
        """
        # Store nodes and build lookup dict
        self.nodes: List[Node] = nodes
        self.node_dict: Dict[tuple, Node] = {
            (node.x, node.y, node.z): node for node in nodes
        }
        # Track placed obstacles and occupied grid positions
        self.placed_obstacles: List[Obstacle] = []
        self.occupied_positions: set = set()
        # Track placement duration
        self.placement_time: float = 0.0

        # Grid meta
        self.node_size = Config.Puzzle.NODE_SIZE
        xs = [n.x for n in nodes] or [0.0]
        ys = [n.y for n in nodes] or [0.0]
        zs = [n.z for n in nodes] or [0.0]
        self.bounds = {
            "x": (min(xs), max(xs)),
            "y": (min(ys), max(ys)),
            "z": (min(zs), max(zs)),
        }

        # Seed RNG for repeatability
        self.seed = Config.Puzzle.SEED
        random.seed(self.seed)
        np.random.seed(self.seed)

        # Place obstacles if enabled
        if Config.Puzzle.OBSTACLES:
            types = get_available_obstacles()
            num_obstacles = len(types)
            print(f"Available obstacle types ({num_obstacles}): {types}")
            start_time = time.perf_counter()
            self.place_obstacles(num_obstacles)
            end_time = time.perf_counter()
            self.placement_time = end_time - start_time
            self._print_placement_summary()
        else:
            print("Obstacle placement disabled via config.")

    def place_obstacles(
        self,
        num_obstacles: int,
        allowed_types: Optional[List[str]] = None,
        max_attempts: int = 200,
    ):
        """
        Selects and places obstacles randomly within the puzzle casing.
        Adds debug statements to trace placement logic.
        """
        if allowed_types is None:
            types = get_available_obstacles()
        else:
            types = allowed_types.copy()

        counts = Counter()
        print(f"Starting placement: Target={num_obstacles}, MaxAttempts={max_attempts}")
        for idx in range(num_obstacles):
            print(f"\nPlacing obstacle {idx + 1}/{num_obstacles}")
            attempts = 0
            placed = False
            while attempts < max_attempts and not placed:
                available_types = [t for t in types if counts[t] < 3]
                if not available_types:
                    print("No available types left (all reached max count)")
                    break

                obstacle_name = random.choice(available_types)
                cls = get_obstacle_class(obstacle_name)
                obstacle = cls()
                # Random rotation
                angles = [0, 90, 180, 270]
                ax = random.choice(angles)
                ay = random.choice(angles)
                az = random.choice(angles)
                obstacle.rotate(Rotation(Axis.X, ax))
                obstacle.rotate(Rotation(Axis.Y, ay))
                obstacle.rotate(Rotation(Axis.Z, az))
                obstacle._rotation_angles = (ax, ay, az)

                # Candidate nodes restricted to interior for this rotation
                interior_nodes, region = self._interior_candidates(obstacle)

                # Fallback if nothing fits interior (e.g., huge obstacle)
                pool = interior_nodes if interior_nodes else self.nodes

                # Random translation
                target = random.choice(pool)
                obstacle.translate(Vector(target.x, target.y, target.z))

                # Snap origin to grid
                ox = _quantize_coord(target.x, Config.Puzzle.NODE_SIZE)
                oy = _quantize_coord(target.y, Config.Puzzle.NODE_SIZE)
                oz = _quantize_coord(target.z, Config.Puzzle.NODE_SIZE)
                obstacle._origin = (ox, oy, oz)
                # Move by the delta from current position to snapped position
                p = obstacle.location.position
                obstacle.translate(Vector(ox - p.X, oy - p.Y, oz - p.Z))

                # Debug info
                if interior_nodes:
                    xmin, xmax, ymin, ymax, zmin, zmax = region
                    print(
                        f" Attempt {attempts + 1}: '{obstacle_name}' origin={obstacle._origin}, "
                        f"rot={obstacle._rotation_angles} | interior candidates={len(interior_nodes)} "
                        f"within x[{xmin},{xmax}] y[{ymin},{ymax}] z[{zmin},{zmax}]"
                    )
                else:
                    print(
                        f" Attempt {attempts + 1}: '{obstacle_name}' origin={obstacle._origin}, "
                        f"rot={obstacle._rotation_angles} | no interior fit, using full grid"
                    )

                valid = self._is_placement_valid(obstacle, debug=True)
                print(f"  -> Placement valid? {valid}")
                if valid:
                    self.placed_obstacles.append(obstacle)
                    self._occupy_nodes_for_obstacle(obstacle)
                    self._assign_entry_exit_nodes(obstacle)
                    counts[obstacle_name] += 1
                    placed = True
                else:
                    attempts += 1

            if not placed:
                print(
                    f"Warning: Could not place obstacle {idx + 1} after {max_attempts} attempts"
                )

    def _is_placement_valid(self, obstacle: Obstacle, debug: bool = False) -> bool:
        """Checks if the proposed placement is valid (inside grid, no collisions)."""
        # Transform and quantize nodes
        occ = [Node(n.x, n.y, n.z, occupied=True) for n in obstacle.occupied_nodes]
        overlap = [
            Node(n.x, n.y, n.z, overlap_allowed=True) for n in obstacle.overlap_nodes
        ]
        obstacle.get_placed_node_coordinates(occ)
        obstacle.get_placed_node_coordinates(overlap)

        # Quantize coordinates to avoid drift
        for n in occ + overlap:
            n.x = _quantize_coord(n.x, Config.Puzzle.NODE_SIZE)
            n.y = _quantize_coord(n.y, Config.Puzzle.NODE_SIZE)
            n.z = _quantize_coord(n.z, Config.Puzzle.NODE_SIZE)

        # Boundary check
        for n in occ + overlap:
            if (n.x, n.y, n.z) not in self.node_dict:
                if debug:
                    print(f"    Node {(n.x, n.y, n.z)} is outside grid.")
                return False
        # Collision check
        for n in occ:
            if (n.x, n.y, n.z) in self.occupied_positions:
                if debug:
                    print(f"    Node {(n.x, n.y, n.z)} collides.")
                return False
        return True

    def _occupy_nodes_for_obstacle(self, obstacle: Obstacle):
        """Marks grid nodes as occupied based on the obstacle's placement."""
        # Transform local to world
        occ_local = [
            Node(n.x, n.y, n.z, occupied=True) for n in (obstacle.occupied_nodes or [])
        ]
        occ_world = obstacle.get_placed_node_coordinates(occ_local)

        for n in occ_world:
            x = _quantize_coord(n.x, Config.Puzzle.NODE_SIZE)
            y = _quantize_coord(n.y, Config.Puzzle.NODE_SIZE)
            z = _quantize_coord(n.z, Config.Puzzle.NODE_SIZE)
            key = (x, y, z)
            node = self.node_dict.get(key)
            if node:
                node.occupied = True
                self.occupied_positions.add(key)

    def _assign_entry_exit_nodes(self, obstacle: Obstacle):
        """Finds closest nodes to entry/exit and marks them.
        TODO not sure if this is still required, obstacles are usually designed this way"""
        coords = obstacle.get_placed_entry_exit_coords()
        if not coords:
            print(" No entry/exit coords.")
            return
        entry, exit = coords
        ex = tuple(_quantize_coord(c, Config.Puzzle.NODE_SIZE) for c in entry)
        et = tuple(_quantize_coord(c, Config.Puzzle.NODE_SIZE) for c in exit)
        print(f" Entry quantized: {ex}, Exit quantized: {et}")
        entry_node = self._find_closest_node(ex)
        exit_node = self._find_closest_node(et)
        if entry_node:
            print(f"  Found entry node at {(entry_node.x, entry_node.y, entry_node.z)}")
        if exit_node:
            print(f"  Found exit node at {(exit_node.x, exit_node.y, exit_node.z)}")
        if entry_node:
            obstacle.entry_node = entry_node
            entry_node.waypoint = True
            entry_node.occupied = True
            entry_node.obstacle_entry = obstacle
        if exit_node and exit_node != entry_node:
            obstacle.exit_node = exit_node
            exit_node.occupied = True
            exit_node.obstacle_exit = obstacle
        elif exit_node == entry_node:
            print(f"Warning: Entry and Exit nodes are the same for {obstacle.name}")

    def _print_placement_summary(self):
        """Prints a summary of all placed obstacles including count, names, origins, rotations, and timing."""
        total = len(self.placed_obstacles)
        print("\nObstacle Placement Summary:")
        print(f"Total obstacles placed: {total}")
        print(f"Placement time: {self.placement_time:.3f} seconds")
        for obs in self.placed_obstacles:
            ox, oy, oz = obs._origin
            ax, ay, az = obs._rotation_angles
            print(
                f"- {obs.name}: Origin=({ox},{oy},{oz}), Rotation=(X:{ax}°,Y:{ay}°,Z:{az}°)"
            )

    def _find_closest_node(self, target_coord: tuple) -> Optional[Node]:
        """Finds the node in the dictionary closest to the target coordinate."""
        tx, ty, tz = target_coord
        min_sq = float("inf")
        closest = None
        for node in self.node_dict.values():
            dx, dy, dz = node.x - tx, node.y - ty, node.z - tz
            dsq = dx * dx + dy * dy + dz * dz
            if dsq < min_sq:
                min_sq = dsq
                closest = node
        return closest

    def _rotated_axis_margins(
        self, obstacle: Obstacle
    ) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        """
        For the obstacle's *current rotation* (location already has rotation applied),
        compute how far local overlap nodes extend from the origin along
        -X/+X, -Y/+Y, -Z/+Z. Returned as ((negX,posX), (negY,posY), (negZ,posZ)).
        """
        local_nodes: List[Node] = []
        if obstacle.overlap_nodes:
            local_nodes.extend(Node(n.x, n.y, n.z) for n in obstacle.overlap_nodes)

        if not local_nodes:
            return (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)

        # Apply current rotation (at this point obstacle hasn't been translated yet)
        placed = obstacle.get_placed_node_coordinates(local_nodes)
        xs = [n.x for n in placed]
        ys = [n.y for n in placed]
        zs = [n.z for n in placed]

        # Distances outward from origin in +/- directions
        posx, negx = (max(xs), -min(xs))
        posy, negy = (max(ys), -min(ys))
        posz, negz = (max(zs), -min(zs))

        return (negx, posx), (negy, posy), (negz, posz)

    def _interior_candidates(
        self,
        obstacle: Obstacle,
        inset_nodes: int = 0,
    ) -> Tuple[List[Node], Tuple[float, float, float, float, float, float]]:
        """
        Build a candidate list of nodes strictly inside the grid bounds by the
        rotation-aware margins (overlap nodes) plus an optional extra inset.
        """
        (negx, posx), (negy, posy), (negz, posz) = self._rotated_axis_margins(obstacle)
        inset = inset_nodes * self.node_size

        xmin = self.bounds["x"][0] + negx + inset
        xmax = self.bounds["x"][1] - posx - inset
        ymin = self.bounds["y"][0] + negy + inset
        ymax = self.bounds["y"][1] - posy - inset
        zmin = self.bounds["z"][0] + negz + inset
        zmax = self.bounds["z"][1] - posz - inset

        # Filter nodes to those that keep all transformed nodes inside the grid
        candidates = [
            n
            for n in self.nodes
            if (xmin <= n.x <= xmax) and (ymin <= n.y <= ymax) and (zmin <= n.z <= zmax)
        ]
        return candidates, (xmin, xmax, ymin, ymax, zmin, zmax)
