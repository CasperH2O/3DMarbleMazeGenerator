# obstacles/catalogue/overhand_knot.py

from math import acos, atan2, cos, degrees, pi, sin

from build123d import (
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Part,
    Spline,
    Vector,
    add,
    sweep,
)

from obstacles.obstacle import Obstacle
from obstacles.obstacle_registry import register_obstacle


class OverhandKnotObstacle(Obstacle):
    """An overhand knot shaped obstacle."""

    def __init__(self):
        super().__init__(name="Overhand Knot")

        # Load occupied nodes from cache or determine
        self.load_relative_node_coords()

    def create_obstacle_geometry(self):
        """Generates the geometry for the overhand knot with spline leads to grid."""
        # Knot spline
        t0 = pi / 3
        t1 = 4 * pi / 3
        samples = 200
        scale = self.node_size * 1
        knot_points = [
            Vector(
                scale * (sin(t / samples) + 2 * sin(2 * t / samples)),
                scale * (cos(t / samples) - 2 * cos(2 * t / samples)),
                scale * (-sin(3 * t / samples)),
            )
            for t in range(int(t0), int(t1 * samples))
        ]
        with BuildLine() as knot_only:
            knot_edge = Spline(knot_points)
        knot_wire = knot_only.line

        # Start for extended lines, use for rotation
        d_start = -(knot_edge % 0)
        d_end = knot_edge % 1

        # Orientate knot parallel to cardinal axis
        knot_rot = self._orient_equal_error(knot_wire, d_start, d_end)

        # Sample endpoints/tangents after rotation
        p0 = knot_rot @ 0
        p1 = knot_rot @ 1
        t0v = knot_rot % 0  # along-knot tangent at start
        t1v = knot_rot % 1  # along-knot tangent at end

        # Translation from the endpoints of the ORIGINAL extended Lines
        # (i.e., use end.X, start.Y, start.Z but taken from the *line ends*)
        node_size = float(self.node_size)

        def snap_delta(val, step):
            return round(val / step) * step - val

        # Virtual line endpoints, 2 node sizes long
        start_line_end = p0 - 2 * node_size * t0v  # start line: p0 -> p0 - 2*s*t0
        end_line_end = p1 + 2 * node_size * t1v  # end   line: p1 -> p1 + 2*s*t1

        dx = snap_delta(end_line_end.X, node_size)  # end.X   -> grid
        dy = snap_delta(start_line_end.Y, node_size)  # start.Y -> grid
        dz = snap_delta(start_line_end.Z, node_size)  # start.Z -> grid

        # Move knot to found delta's based on straight extensions
        knot_moved = knot_rot.translate(Vector(dx, dy, dz))

        # Sample endpoints/tangents after translation
        p0 = knot_moved @ 0
        p1 = knot_moved @ 1
        t0u = knot_moved % 0
        t1u = knot_moved % 1

        # outward handle directions (used only for finding G0/G1)
        h0 = -t0u
        h1 = t1u

        # find nearest grid points with infinite straight handles
        node_size = float(self.node_size)
        G0 = self._nearest_grid_point_to_line(p0, h0, node_size, span=2)
        G1 = self._nearest_grid_point_to_line(p1, h1, node_size, span=2)

        def _cardinal_axis_tangent(
            point_to_other: Vector, prefer_dir: Vector
        ) -> Vector:
            """
            Choose the cardinal axis (±X, ±Y, ±Z) most aligned with `prefer_dir`,
            then set its sign so it points TOWARD `point_to_other`.
            Returns a unit Vector along that axis.
            """
            # Pick axis by biggest component in prefer_dir
            comps = (abs(prefer_dir.X), abs(prefer_dir.Y), abs(prefer_dir.Z))
            axis_idx = comps.index(max(comps))
            if axis_idx == 0:
                base = Vector(1, 0, 0)
                sign = 1.0 if point_to_other.X >= 0 else -1.0
            elif axis_idx == 1:
                base = Vector(0, 1, 0)
                sign = 1.0 if point_to_other.Y >= 0 else -1.0
            else:
                base = Vector(0, 0, 1)
                sign = 1.0 if point_to_other.Z >= 0 else -1.0
            return base * sign  # already unit length

        # Grid-end tangents: choose axis & sign so they head toward the other endpoint
        tg0_axis = _cardinal_axis_tangent(
            point_to_other=(p0 - G0), prefer_dir=h0
        )  # at G0
        tg1_axis = _cardinal_axis_tangent(
            point_to_other=(G1 - p1), prefer_dir=h1
        )  # at G1

        # Build the final path:
        # [node grid→start lead] + [knot] + [end lean→ node grid]
        with BuildLine() as full_path:
            # Start lead
            Spline([G0, p0], tangents=[tg0_axis, t0u])

            # Knot
            add(knot_moved)

            # End lead
            Spline([p1, G1], tangents=[t1u, tg1_axis])

        self.path_segment.path = full_path.line

    def model_solid(self) -> Part:
        """
        Solid model the obstacle, but used for, determining
        occupied nodes, debug and overview.
        """

        with BuildPart() as obstacle:
            with BuildLine() as line:
                add(self.path_segment.path)
            with BuildSketch(line.line ^ 0):
                add(self.default_path_profile_type())
            sweep()

        obstacle.part.label = f"{self.name} Obstacle Solid"

        return obstacle.part

    @staticmethod
    def _orient_equal_error(path_wire, d0: Vector, d1: Vector):
        """Rotate `path_wire` so d0 & d1 have equal misalignment to X & Y axes."""

        def clamp(x, lo=-1.0, hi=1.0):
            return max(lo, min(hi, x))

        def unit(v: Vector) -> Vector:
            length = v.length
            return v if length == 0 else v / length

        # Treat lines as undirected: flip d1 to make the angle acute
        d0 = unit(d0)
        d1 = unit(d1 if d0.dot(d1) >= 0 else -d1)

        # Plane normal
        n = d0.cross(d1)
        n_len = n.length

        # Nearly parallel? Put them at 45° between X & Y (best equal-error you can do)
        if n_len < 1e-12:
            # align d0 -> X
            cross1 = d0.cross(Vector(1, 0, 0))
            if cross1.length > 1e-12:
                axis1 = Axis((0, 0, 0), unit(cross1))
                ang1 = degrees(acos(clamp(d0.dot(Vector(1, 0, 0)))))
                path_wire = path_wire.rotate(axis=axis1, angle=ang1)
            else:
                # anti-parallel
                if d0.dot(Vector(1, 0, 0)) < 0:
                    path_wire = path_wire.rotate(axis=Axis.Y, angle=180.0)
            # equalize: spin to 45°
            return path_wire.rotate(axis=Axis.Z, angle=45.0)

        # Rotate plane normal to +Z
        n_hat = n / n_len
        z = Vector(0, 0, 1)
        axis_a_vec = n_hat.cross(z)
        if axis_a_vec.length < 1e-12:
            # already aligned or exactly opposite
            axis_a = Axis((0, 0, 0), Vector(1, 0, 0))  # any axis ⟂ Z
            ang_a = 0.0 if n_hat.dot(z) > 0 else 180.0
        else:
            axis_a = Axis((0, 0, 0), unit(axis_a_vec))
            ang_a = degrees(acos(clamp(n_hat.dot(z))))
        path_wire = path_wire.rotate(axis=axis_a, angle=ang_a)

        # Rotate the direction vectors by the same axis-angle (Rodrigues, radians)
        ang_a_rad = ang_a * pi / 180.0
        k = unit(axis_a_vec) if axis_a_vec.length >= 1e-12 else Vector(1, 0, 0)

        def rodrigues(v: Vector) -> Vector:
            # v_rot = v*cosθ + (k×v)*sinθ + k*(k·v)*(1−cosθ)
            c, s = (acos(-1.0) and None, None)  # dummy to keep locals distinct
            c = __import__("math").cos(ang_a_rad)
            s = __import__("math").sin(ang_a_rad)
            return v * c + k.cross(v) * s + k * (k.dot(v)) * (1.0 - c)

        v0 = rodrigues(d0)
        v1 = rodrigues(d1)

        # Project to XY (should already be near-plane) and get polar angles
        v0 = Vector(v0.X, v0.Y, 0).normalized()
        v1 = Vector(v1.X, v1.Y, 0).normalized()
        theta0 = atan2(v0.Y, v0.X)
        theta1 = atan2(v1.Y, v1.X)

        # Perform in-plane spin so both have equal error to X & Y
        phi = (pi / 4) - 0.5 * (theta0 + theta1)  # radians
        path_wire = path_wire.rotate(axis=Axis.Z, angle=degrees(phi))
        return path_wire

    def _best_grid_translation(self, path_wire):
        """
        Return Vector(dx, dy, dz) that determines certain X Y Z from start or end of path,
        determines a shift to the grid and applies that single shift to the whole path.
        """
        s = float(self.node_size)
        p0 = path_wire @ 0  # start
        p1 = path_wire @ 1  # end

        # delta to nearest k * s
        def snap_delta(val, step):
            k = round(val / step)  # nearest integer multiple
            return k * step - val

        dx = snap_delta(p1.X, s)  # end.X   -> grid
        dy = snap_delta(p0.Y, s)  # start.Y -> grid
        dz = snap_delta(p0.Z, s)  # start.Z -> grid

        return Vector(dx, dy, dz)

    def _nearest_grid_point_to_line(
        self, p: Vector, d: Vector, step: float, span: int = 2
    ) -> Vector:
        """
        Nearest lattice point (i*step, j*step, k*step) to the infinite line L(t)=p + t*d.
        Searches a small cube around round(p/step). Increase span if needed.
        """
        if d.length == 0:
            return Vector(
                round(p.X / step) * step,
                round(p.Y / step) * step,
                round(p.Z / step) * step,
            )
        dn = d / d.length
        i0, j0, k0 = round(p.X / step), round(p.Y / step), round(p.Z / step)
        best = (float("inf"), None)
        for i in range(i0 - span, i0 + span + 1):
            for j in range(j0 - span, j0 + span + 1):
                for k in range(k0 - span, k0 + span + 1):
                    G = Vector(i * step, j * step, k * step)
                    t = dn.dot(G - p)  # closest point on line to G (dn is unit)
                    C = p + dn * t
                    d2 = (C - G).length ** 2
                    if d2 < best[0]:
                        best = (d2, G)
        return best[1]


# Register obstacle
register_obstacle("OverhandKnot", OverhandKnotObstacle)

if __name__ == "__main__":
    # Create
    obstacle = OverhandKnotObstacle()

    # Visualization
    obstacle.visualize()

    # Solid model
    obstacle.show_solid_model()
