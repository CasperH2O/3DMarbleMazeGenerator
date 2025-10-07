# obstacles/obstacle_manager.py

import math
import random
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
from build123d import Axis, Rotation, Vector

import obstacles.catalogue  # ensure registration
from config import Config
from puzzle.utils.enums import ObstacleType
from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import get_available_obstacles, get_obstacle_class
from puzzle.node import Node


def _quantize_coord(val: float, node_size: float) -> float:
    """Snap a coordinate to the nearest grid multiple to avoid floating-point drift."""
    return round(val / node_size) * node_size


def _snap_near_grid(value: float, node_size: float, *, tol: float = 1e-6) -> float:
    """Return the grid-aligned value when the input is already very close to one."""

    scaled = value / node_size
    rounded = round(scaled)
    if math.isclose(scaled, rounded, rel_tol=tol, abs_tol=tol):
        return rounded * node_size
    return value


class ObstacleManager:
    """
    Manages the selection, placement, and node occupation of obstacles.
    """

    def __init__(self, nodes: list[Node]) -> None:
        """
        Initializes the obstacle manager.

        Parameters:
            nodes: puzzle nodes, for placement of the nodes.
        """
        # Store nodes and build lookup dict
        self.nodes: list[Node] = nodes
        self.node_dict: Dict[tuple, Node] = {
            (node.x, node.y, node.z): node for node in nodes
        }
        # Track placed obstacles and occupied grid positions
        self.placed_obstacles: list[Obstacle] = []
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

        # Placement
        if Config.Obstacles.ENABLED:
            available = get_available_obstacles()
            normalized_config_types: list[str] = []
            for configured_type in Config.Obstacles.ALLOWED_TYPES:
                if isinstance(configured_type, ObstacleType):
                    normalized_config_types.append(configured_type.value)
                elif isinstance(configured_type, str):
                    normalized_config_types.append(configured_type)
                else:
                    normalized_config_types.append(str(configured_type))

            # Keep order from config; filter out unknowns gracefully.
            allowed = [t for t in normalized_config_types if t in available]
            if not allowed:
                print(
                    f"No allowed obstacle types found from config list "
                    f"{normalized_config_types}. Available: {available}"
                )
            else:
                print(f"Allowed obstacle types (ordered): {allowed}")

            start_time = time.perf_counter()
            self.place_obstacles(
                num_to_place=Config.Obstacles.MAX_TO_PLACE,
                allowed_types=allowed if allowed else available,
                attempts_per_placement=Config.Obstacles.ATTEMPTS_PER_PLACEMENT,
                per_type_limit=Config.Obstacles.PER_TYPE_LIMIT,
            )
            end_time = time.perf_counter()
            self.placement_time = end_time - start_time
            self._print_placement_summary()
        else:
            print("Obstacle placement disabled via config.")

    def place_obstacles(
        self,
        num_to_place: int,
        allowed_types: Optional[list[str]] = None,
        attempts_per_placement: int = 200,
        per_type_limit: Optional[int] = None,
    ):
        """
        Round-robin placement:
        - Cycle through allowed types in order.
        - For each type, try up to 'attempts_per_placement' random placements.
        - If placed, move to the next type; repeat cycles until number to place is reached or no progress.
        """
        types = allowed_types[:] if allowed_types else get_available_obstacles()
        if not types:
            print("No obstacle types available.")
            return

        total_target = max(0, int(num_to_place))
        counts = Counter()
        placed_total = 0
        cycle_idx = 0

        print(
            f"Starting placement: Target={total_target}, "
            f"AttemptsPerPlacement={attempts_per_placement}, "
            f"PerTypeLimit={per_type_limit}"
        )

        while placed_total < total_target:
            cycle_progress = False
            cycle_idx += 1
            print(f"\n=== Cycle {cycle_idx} ===")

            for obstacle_name in types:
                if placed_total >= total_target:
                    break

                if (
                    per_type_limit is not None
                    and counts[obstacle_name] >= per_type_limit
                ):
                    print(
                        f" Skipping '{obstacle_name}' (reached per-type limit {per_type_limit})."
                    )
                    continue

                placed = self._try_place_one(
                    obstacle_name=obstacle_name,
                    max_attempts=attempts_per_placement,
                )
                if placed:
                    counts[obstacle_name] += 1
                    placed_total += 1
                    cycle_progress = True
                    print(
                        f" -> Placed '{obstacle_name}'. Totals: placed={placed_total}/{total_target} "
                        f"(this type={counts[obstacle_name]})"
                    )
                else:
                    print(f" -> Could not place '{obstacle_name}' in this cycle.")

            if not cycle_progress:
                print("No further placements possible with current constraints.")
                break

    def _try_place_one(self, obstacle_name: str, max_attempts: int) -> bool:
        """Try to place a single obstacle instance of the given type. Returns True on success."""
        cls = get_obstacle_class(obstacle_name)
        attempts = 0

        while attempts < max_attempts:
            obstacle = cls()

            # Random rotation (grid-friendly 90° steps)
            angles = [0, 90, 180, 270]
            ax = random.choice(angles)
            ay = random.choice(angles)
            az = random.choice(angles)
            obstacle.rotate(Rotation(Axis.X, ax))
            obstacle.rotate(Rotation(Axis.Y, ay))
            obstacle.rotate(Rotation(Axis.Z, az))
            obstacle.rotation_angles_deg = (ax, ay, az)

            # Candidate nodes restricted to interior for this rotation
            interior_nodes, region = self._interior_candidates(obstacle)

            # Fallback to all nodes if nothing fits interior (e.g., huge obstacle)
            pool = interior_nodes if interior_nodes else self.nodes
            target = random.choice(pool)

            # Translate to target & snap origin to grid
            obstacle.translate(Vector(target.x, target.y, target.z))
            # Snap origin to grid
            ox = _quantize_coord(target.x, self.node_size)
            oy = _quantize_coord(target.y, self.node_size)
            oz = _quantize_coord(target.z, self.node_size)
            obstacle.grid_origin = (ox, oy, oz)

            # Move by the delta from current position to snapped position
            p = obstacle.location.position
            obstacle.translate(Vector(ox - p.X, oy - p.Y, oz - p.Z))

            # Debug info
            if interior_nodes:
                xmin, xmax, ymin, ymax, zmin, zmax = region
                print(
                    f" Attempt {attempts + 1}: '{obstacle_name}' origin={obstacle.grid_origin}, "
                    f"rot={obstacle.rotation_angles_deg} | interior candidates={len(interior_nodes)} "
                    f"within x[{xmin},{xmax}] y[{ymin},{ymax}] z[{zmin},{zmax}]"
                )
            else:
                print(
                    f" Attempt {attempts + 1}: '{obstacle_name}' origin={obstacle.grid_origin}, "
                    f"rot={obstacle.rotation_angles_deg} | no interior fit, using full grid"
                )

            valid = self._is_placement_valid(obstacle, debug=True)
            print(f"  -> Placement valid? {valid}")
            if valid:
                self.placed_obstacles.append(obstacle)
                self._occupy_nodes_for_obstacle(obstacle)
                self._assign_entry_exit_nodes(obstacle)
                return True

            attempts += 1

        # Exhausted attempts for this type instance
        return False

    def _is_placement_valid(self, obstacle: Obstacle, debug: bool = False) -> bool:
        """Checks if the proposed placement is valid (inside grid, no collisions)."""
        # Transform and quantize nodes
        occ = [
            Node(n.x, n.y, n.z, occupied=True) for n in (obstacle.occupied_nodes or [])
        ]
        overlap = [
            Node(n.x, n.y, n.z, overlap_allowed=True)
            for n in (obstacle.overlap_nodes or [])
        ]
        obstacle.get_placed_node_coordinates(occ)
        obstacle.get_placed_node_coordinates(overlap)

        # Quantize coordinates to avoid drift
        for n in occ + overlap:
            n.x = _quantize_coord(n.x, self.node_size)
            n.y = _quantize_coord(n.y, self.node_size)
            n.z = _quantize_coord(n.z, self.node_size)

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
        occ_local = [
            Node(n.x, n.y, n.z, occupied=True) for n in (obstacle.occupied_nodes or [])
        ]
        occ_world = obstacle.get_placed_node_coordinates(occ_local)

        for n in occ_world:
            x = _quantize_coord(n.x, self.node_size)
            y = _quantize_coord(n.y, self.node_size)
            z = _quantize_coord(n.z, self.node_size)
            key = (x, y, z)
            node = self.node_dict.get(key)
            if node:
                node.occupied = True
                self.occupied_positions.add(key)

    def _assign_entry_exit_nodes(self, obstacle: Obstacle):
        """Find closest nodes to entry/exit and mark them (if obstacle provides such coords)."""
        coords = obstacle.get_placed_entry_exit_coords()
        if not coords:
            print(" No entry/exit coords.")
            return
        entry, exit = coords
        ex = tuple(_quantize_coord(c, self.node_size) for c in entry)
        et = tuple(_quantize_coord(c, self.node_size) for c in exit)
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
        """Print a summary of all placed obstacles including count, names, origins, rotations, and timing."""
        total = len(self.placed_obstacles)
        by_type = Counter([o.name for o in self.placed_obstacles])
        print("\nObstacle Placement Summary:")
        print(f"Total obstacles placed: {total}  |  By type: {dict(by_type)}")
        print(f"Placement time: {self.placement_time:.3f} seconds")
        for obs in self.placed_obstacles:
            ox, oy, oz = obs.grid_origin
            ax, ay, az = obs.rotation_angles_deg
            print(
                f"- {obs.name}: Origin=({ox},{oy},{oz}), Rotation=(X:{ax}°,Y:{ay}°,Z:{az}°)"
            )

    def _find_closest_node(self, target_coord: tuple) -> Optional[Node]:
        """Find the node in the dictionary closest to the target coordinate."""
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
        For the obstacle's *current rotation*, compute how far local overlap nodes extend from the
        origin along -X/+X, -Y/+Y, -Z/+Z. Returns ((negX,posX), (negY,posY), (negZ,posZ)).
        """
        local_nodes: list[Node] = []
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
        self, obstacle: Obstacle, inset_nodes: int = 0
    ) -> Tuple[list[Node], Tuple[float, float, float, float, float, float]]:
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

        # Snap bounds that are numerically close to the grid to avoid tiny artifacts
        xmin = _snap_near_grid(xmin, self.node_size)
        xmax = _snap_near_grid(xmax, self.node_size)
        ymin = _snap_near_grid(ymin, self.node_size)
        ymax = _snap_near_grid(ymax, self.node_size)
        zmin = _snap_near_grid(zmin, self.node_size)
        zmax = _snap_near_grid(zmax, self.node_size)

        # Filter nodes to those that keep all transformed nodes inside the grid
        eps = self.node_size * 1e-6
        candidates = [
            n
            for n in self.nodes
            if (xmin - eps <= n.x <= xmax + eps)
            and (ymin - eps <= n.y <= ymax + eps)
            and (zmin - eps <= n.z <= zmax + eps)
        ]
        bounds = tuple(round(val, 6) for val in (xmin, xmax, ymin, ymax, zmin, zmax))
        return candidates, bounds
