"""
Standalone build123d demo: binormal guide-wire approaches for swept accent bodies.

Context
-------
In a 3D marble maze generator, each path segment is a swept solid. Most segments
use a compound approach (straight / arc sub-segments). Some use a SPLINE, sweeping
a cross-section profile from start to end. The segment has:

  - Main body   — the structural channel wall (L-shape, U-shape, V-shape, …)
  - Accent body — a thin colour stripe that sits on the *inner* wall of the channel

The accent profile shares a vertex with the main profile at the inner corner of the
channel.  When the main body works fine (e.g. angle changes by ~399°, a common
edge case), the naïve multi-section sweep for the accent body self-intersects
because the accent stripe is far off-centre and the sweep folds it back on itself.

Two alternative approaches are compared:

  A. Use an actual edge from the already-swept main body as the OCCT auxiliary spine.
     That edge is the literal 3D curve the inner-corner vertex traced during the
     main sweep — structurally the most accurate guide.

  B. Compute the inner corner's 3D position at t=0 and t=1 from the profile's
     definition geometry + the path frame, then build a Spline through those
     two points.  Fully self-contained; does not require the main body at all.

All three approaches (failing baseline, A, B) are shown in ocp_vscode.
"""

from __future__ import annotations

import math

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    FrameMethod,
    Plane,
    Polyline,
    Rot,
    Spline,
    Transition,
    Vector,
    Vertex,
    add,
    make_face,
    sweep,
)
from ocp_vscode import show_object

# Profile functions, could be simplified but are based on actual puzzle code
def create_l_shape_adjusted_height(
    height_width: float = 9.9999,
    wall_thickness: float = 2.0,
    lower_distance: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """L-shaped cross-section with a reduced top height."""
    if height_width - lower_distance < wall_thickness:
        lower_distance = height_width - wall_thickness
    adjusted_top_y   = height_width / 2 - lower_distance
    half_width       = height_width / 2
    inner_half_width = half_width - wall_thickness
    pts = [
        ( half_width,        -half_width),
        ( half_width,         adjusted_top_y),
        ( inner_half_width,   adjusted_top_y),
        ( inner_half_width,  -inner_half_width),
        (-half_width,        -inner_half_width),
        (-half_width,        -half_width),
        ( half_width,        -half_width),   # close
    ]
    with BuildSketch(Plane.XY) as sk:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(pts)
        make_face()
    return sk


def create_l_shape_path_color(
    height: float = 9.9999,
    width: float = 9.9999,
    wall_thickness: float = 2.0,
    rotation_angle: float = -90,
) -> BuildSketch:
    """Thin accent stripe that sits on the inner floor of the L-channel."""
    inner_half_width  = width  / 2 - wall_thickness
    inner_half_height = height / 2 - wall_thickness
    accent_height     = 2 * 0.4          # 2 × nozzle diameter
    pts = [
        ( inner_half_width,  -inner_half_height + accent_height),
        ( inner_half_width,  -inner_half_height),                   # ← inner corner
        (-width / 2,         -inner_half_height),
        (-width / 2,         -inner_half_height + accent_height),
        ( inner_half_width,  -inner_half_height + accent_height),   # close
    ]
    with BuildSketch(Plane.XY) as sk:
        with BuildLine(Rot(Z=rotation_angle)):
            Polyline(pts)
        make_face()
    return sk

# Helpers
def do_faces_intersect(shape) -> bool:
    """True if any two faces of *shape* intersect in a new edge (self-intersection)."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer

    faces = list(shape.faces())
    if len(faces) < 2:
        return False
    edge_hashes = {hash(e.wrapped) for e in shape.edges()}
    for i in range(len(faces)):
        for j in range(i + 1, len(faces)):
            sec = BRepAlgoAPI_Section(faces[i].wrapped, faces[j].wrapped)
            sec.Build()
            if not sec.IsDone():
                continue
            exp = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
            while exp.More():
                if hash(exp.Current()) not in edge_hashes:
                    return True
                exp.Next()
    return False


def find_shared_vertex(sketch_a: BuildSketch, sketch_b: BuildSketch,
                       tol: float = 0.01) -> Vector | None:
    """Return the first vertex shared by both placed sketches (within tol mm)."""
    for va in sketch_a.sketch.vertices():
        pos_a: Vector = va.center()  # type: ignore[operator]
        for vb in sketch_b.sketch.vertices():
            if (pos_a - vb.center()).length < tol:  # type: ignore[operator]
                return pos_a
    return None


def overlap_pct(body_a, body_b) -> float:
    """Return what % of body_a's volume is inside body_b (0 when separate)."""
    try:
        vol_a = body_a.volume
        return (body_a & body_b).volume / vol_a * 100 if vol_a > 0 else 0.0
    except Exception as exc:
        print(f"  [overlap check failed: {exc}]")
        return float("nan")


def inner_corner_world_l_path_color(kw: dict, angle_deg: float, loc) -> Vector:
    """
    Compute the 3D world-space position of the inner corner of create_l_shape_path_color.

    The inner corner in the profile's definition frame (before Rot(Z=angle_deg)) is:
        x_def = width/2  - wall_thickness   (inner_half_width)
        y_def = -(height/2 - wall_thickness) (−inner_half_height)

    Steps:
      1. Rotate by angle_deg in the profile's local XY plane.
      2. Transform to world space through the CORRECTED path frame `loc`.
    """
    x_def = kw["width"]  / 2 - kw["wall_thickness"]
    y_def = -(kw["height"] / 2 - kw["wall_thickness"])

    a     = math.radians(angle_deg)
    x_pth = x_def * math.cos(a) - y_def * math.sin(a)
    y_pth = x_def * math.sin(a) + y_def * math.cos(a)

    return (loc.position
            + x_pth * loc.x_axis.direction
            + y_pth * loc.y_axis.direction)


def report(label: str, body: BuildPart | None, main_part=None) -> None:
    """Print a one-line result summary for a swept body."""
    if body is None or body.part is None:
        print(f"  {label:<30}: FAILED (no body)")
        return
    valid = body.part.is_valid
    si    = do_faces_intersect(body.part)
    pct   = overlap_pct(body.part, main_part) if main_part is not None else float("nan")
    pct_s = f"  overlap={pct:.2f}%" if not math.isnan(pct) else ""
    flag  = "  *** OVERLAP > 1%" if (not math.isnan(pct) and pct > 1.0) else ""
    print(f"  {label:<30}: valid={valid}  self-intersects={si}{pct_s}{flag}")


# Geometry

# This case is representative of segments where the computed profile twist exceeds
# 360°. The main body sweeps correctly (OCCT resolves the short rotation), but the
# offset accent stripe folds back on itself and self-intersects.

CTRL_PTS   = [(35.0, 10.0, -20.0), (10.0, 0.0, -25.0)]
TAN_START  = Vector(-1.0,  0.0,  0.0)
TAN_END    = Vector( 0.0,  0.0, -1.0)
ANGLE_S    = -219.80557109226504   # profile rotation at path start
ANGLE_E    =  178.82769961215035   # profile rotation at path end

MAIN_KW   = {"height_width": 9.999, "wall_thickness": 1.2, "lower_distance": 3.5}
ACCENT_KW = {"height": 9.999, "width": 9.999, "wall_thickness": 1.2}

# Display colours
C_MAIN       = {"color": "#FFFFFF"}   # white  — main body
C_BASELINE   = {"color": "#FF4444"}   # red    — baseline (self-intersects)
C_APPROACH_A = {"color": "#44BB44"}   # green  — Approach A (edge guide)
C_APPROACH_B = {"color": "#FF8800"}   # orange — Approach B (geometric guide)
C_APPROACH_C = {"color": "#CC44CC"}   # purple — Approach C (guide for both bodies)
C_APPROACH_D = {"color": "#00BBCC"}   # teal   — Approach D (main vertex, no accent comparison)

# Build geometry
spline     = Spline(CTRL_PTS, tangents=[TAN_START, TAN_END])
loc_t0 = spline.location_at(0, frame_method=FrameMethod.CORRECTED)
loc_t1 = spline.location_at(1, frame_method=FrameMethod.CORRECTED)

show_object(spline, name="[path] spline")

# Profiles
p_main_s  = create_l_shape_adjusted_height(**MAIN_KW,   rotation_angle=ANGLE_S)
p_main_e  = create_l_shape_adjusted_height(**MAIN_KW,   rotation_angle=ANGLE_E)
p_acc_s   = create_l_shape_path_color(**ACCENT_KW,       rotation_angle=ANGLE_S)
p_acc_e   = create_l_shape_path_color(**ACCENT_KW,       rotation_angle=ANGLE_E)

with BuildSketch(loc_t0) as sk_acc_s:
    add(p_acc_s)
with BuildSketch(loc_t1) as sk_acc_e:
    add(p_acc_e)

show_object(sk_acc_s.sketch, name="[ref] accent profile at t=0")
show_object(sk_acc_e.sketch, name="[ref] accent profile at t=1")

# Main path body
print("\n[main path body]")
with BuildPart() as main_path_body:
    with BuildLine() as pl:
        add(spline)
    with BuildSketch(loc_t0) as ss:
        add(p_main_s)
    with BuildSketch(loc_t1) as se:
        add(p_main_e)
    sweep(sections=[ss.sketch, se.sketch], path=pl.line, multisection=True)
report("main body", main_path_body)
show_object(main_path_body.part, name="[main] body", options=C_MAIN)

# Baseline: multisection, self-intersects
print("\n[baseline — CORRECTED multisection]")

with BuildPart() as acc_baseline:
    with BuildLine() as pl:
        add(spline)
    with BuildSketch(loc_t0) as ss:
        add(p_acc_s)
    with BuildSketch(loc_t1) as se:
        add(p_acc_e)
    sweep(sections=[ss.sketch, se.sketch], path=pl.line, multisection=True)
report("accent baseline", acc_baseline,
        main_path_body.part if main_path_body else None)
show_object(acc_baseline.part,
            name="[baseline] accent CORRECTED (self-intersects)", options=C_BASELINE)
    
# Approach A: shared-vertex edge from the swept main body

# Place the main and accent profiles at t=0 in the same frame and find the vertex
# they share (inner corner of the channel). Then find the longitudinal edge in the
# main body whose endpoint sits at that vertex — that edge is the actual 3D curve
# the inner corner traced during the sweep. Use it as the OCCT auxiliary spine.

print("\n[Approach A — shared-vertex main body edge]")
guide_edge_A = None

p_main_s_cmp = create_l_shape_adjusted_height(**MAIN_KW, rotation_angle=ANGLE_S)
with BuildSketch(loc_t0) as sk_main_cmp:
    add(p_main_s_cmp)
with BuildSketch(loc_t0) as sk_acc_cmp:
    add(p_acc_s)

shared_v = find_shared_vertex(sk_main_cmp, sk_acc_cmp)
print(f"  shared vertex at t=0: {shared_v}")

path_len  = spline.length
best_dist = float("inf")
for e in main_path_body.part.edges():
    if e.length <= 0.5 * path_len:
        continue
    for ev in e.vertices():
        d = (ev.center() - shared_v).length
        if d < best_dist:
            best_dist = d
            guide_edge_A = e

print(f"  guide edge length: {guide_edge_A.length:.2f} mm  "
      f"(endpoint dist: {best_dist:.3f} mm)")
show_object(guide_edge_A, name="[A] guide edge (inner-corner trace)")

with BuildPart() as acc_A:
    with BuildLine():
        add(spline)
    with BuildSketch(loc_t0):
        add(p_acc_s)
    sweep(binormal=guide_edge_A, transition=Transition.RIGHT)
report("accent A", acc_A, main_path_body.part)
show_object(acc_A.part, name="[A] accent (edge guide)", options=C_APPROACH_A)

# Approach B: geometric guide wire from computed inner-corner positions

# Compute the accent profile's inner corner in 3D world space at t=0 and t=1
# without touching the main body: look up the corner in the profile's definition
# frame, rotate by the profile angle, then map through the CORRECTED path frame.
# Build a Spline through those two points and use it as the auxiliary spine.

print("\n[Approach B — geometric guide wire]")

corner_t0 = inner_corner_world_l_path_color(ACCENT_KW, ANGLE_S, loc_t0)
corner_t1 = inner_corner_world_l_path_color(ACCENT_KW, ANGLE_E, loc_t1)

print(f"  inner corner at t=0: {corner_t0}")
print(f"  inner corner at t=1: {corner_t1}")
print(f"  guide wire span (straight): {(corner_t1 - corner_t0).length:.2f} mm")

show_object(Vertex(corner_t0.X, corner_t0.Y, corner_t0.Z),
            name="[B] inner corner t=0")
show_object(Vertex(corner_t1.X, corner_t1.Y, corner_t1.Z),
            name="[B] inner corner t=1")

guide_B = Spline([corner_t0, corner_t1], tangents=[spline % 0, spline % 1])
show_object(guide_B, name="[B] guide wire (spline through inner corners)")

with BuildPart() as acc_B:
    with BuildLine():
        add(spline)
    with BuildSketch(loc_t0):
        add(p_acc_s)
    sweep(binormal=guide_B, transition=Transition.RIGHT)
report("accent B", acc_B, main_path_body.part)
show_object(acc_B.part, name="[B] accent (geometric guide)", options=C_APPROACH_B)

# Approach C: same geometric guide wire for BOTH main body and accent body
#
# The inner corner is shared by both profiles, so using the same guide wire
# constrains that shared point to exactly the same 3D curve in both sweeps.
# They should meet flush at the corner with zero overlap — no alignment mismatch
# is possible by construction.  Both bodies use only the start-angle profile
# (single-section sweep), so the end orientation is determined by the guide wire,
# not by an explicit end profile.
print("\n[Approach C — geometric guide wire for both main and accent]")

# The inner corner of the main L-shape in its definition frame:
#   (inner_half_width, -inner_half_width) = (hw/2 - wt, -(hw/2 - wt))
# This equals the accent inner corner when height == width (which is the case here),
# so guide_B already represents the shared corner for both profiles.
# (Confirmed: MAIN_KW height_width=9.999 → inner = 3.7995; ACCENT_KW width=height=9.999 → same)

with BuildPart() as main_C:
    with BuildLine():
        add(spline)
    with BuildSketch(loc_t0):
        add(p_main_s)
    sweep(binormal=guide_B, transition=Transition.RIGHT)
report("main C", main_C)
show_object(main_C.part, name="[C] main body (geometric guide)", options=C_APPROACH_C)

with BuildPart() as acc_C:
    with BuildLine():
        add(spline)
    with BuildSketch(loc_t0):
        add(p_acc_s)
    sweep(binormal=guide_B, transition=Transition.RIGHT)
report("accent C", acc_C, main_C.part)
show_object(acc_C.part, name="[C] accent (geometric guide)", options=C_APPROACH_C)

print(f"  main C / accent C overlap: {overlap_pct(acc_C.part, main_C.part):.2f}%"
      "  (expect ~0 — shared vertex is the boundary, not inside either body)")

# Approach D: first vertex of placed main profile (no accent comparison)
#
# Hypothesis: OCCT only needs *a* consistent binormal anchor, not specifically
# the shared inner-corner vertex.  Skip the nested vertex comparison entirely —
# just place the main profile at t=0 and t=1 and pick vertices()[0] from each.
# Saves the O(n²) vertex search; works if the selected vertex happens to be on
# the shared boundary (or close enough that OCCT resolves the orientation correctly).

print("\n[Approach D — main profile vertex[0], no accent comparison]")

with BuildSketch(loc_t0) as sk_main_D_s:
    add(p_main_s)
with BuildSketch(loc_t1) as sk_main_D_e:
    add(p_main_e)

vt_s: Vector = sk_main_D_s.sketch.vertices()[-1].center()  # type: ignore[operator]
vt_e: Vector = sk_main_D_e.sketch.vertices()[-1].center()  # type: ignore[operator]
print(f"  vertex[0] at t=0: {vt_s}")
print(f"  vertex[0] at t=1: {vt_e}")
print(f"  shared vertex was: {shared_v}  (from Approach A)")

guide_D = Spline([vt_s, vt_e], tangents=[spline % 0, spline % 1])
show_object(guide_D, name="[D] guide wire (main vertex[0])")

with BuildPart() as main_D:
    with BuildLine():
        add(spline)
    with BuildSketch(loc_t0):
        add(p_main_s)
    sweep(binormal=guide_D, transition=Transition.RIGHT)
report("main D", main_D)
show_object(main_D.part, name="[D] main body (main vertex[0] guide)", options=C_APPROACH_D)

with BuildPart() as acc_D:
    with BuildLine():
        add(spline)
    with BuildSketch(loc_t0):
        add(p_acc_s)
    sweep(binormal=guide_D, transition=Transition.RIGHT)
report("accent D", acc_D, main_D.part)
show_object(acc_D.part, name="[D] accent (main vertex[0] guide)", options=C_APPROACH_D)

# Summary
print(f"""
{'═' * 60}
Summary  (case: seed4_seg6_0 — L-shape adjusted, Δangle ≈ 399°)
{'─' * 60}
  angle_start = {ANGLE_S:.3f}°
  angle_end   = {ANGLE_E:.3f}°
  Δangle      = {ANGLE_E - ANGLE_S:.3f}°  (≈ one full revolution + 39°)
{'─' * 60}
""")
report("Main body",                    main_path_body)
report("Baseline (CORRECTED)",         acc_baseline,  main_path_body.part)
report("Approach A (edge)",            acc_A,          main_path_body.part)
report("Approach B (geometric)",       acc_B,          main_path_body.part)
report("Approach C main  (both)",      main_C)
report("Approach C accent (both)",     acc_C,          main_C.part)
report("Approach D main  (both)",       main_D)
report("Approach D accent (both)",     acc_D,          main_D.part)
print(f"{'═' * 60}")
