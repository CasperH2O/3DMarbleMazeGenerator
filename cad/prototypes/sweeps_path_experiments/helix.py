from math import atan, cos, degrees, log, sin, sqrt, tau

from build123d import *
from ocp_vscode import show

# --- controls ---
r0 = 10.0  # start radius
r1 = 30.0  # end radius (target for cone helix)
H = 100.0  # total height
N = 10.0  # number of turns over height H
tube_r = 1.0  # swept circle radius
samples = 1200  # for the constant-slope spiral path

# --- constant-slope (ds/dz) spiral path (for comparison) ---
a = (r1 - r0) / H
c = (tau * N * a) / log(r1 / r0)
m = sqrt(1 + a * a + c * c)  # constant ds/dz just FYI

pts = []
for i in range(samples):
    z = H * i / (samples - 1)
    r = r0 + a * z
    theta = (c / a) * log(r / r0)
    pts.append((r * cos(theta), r * sin(theta), z))

with BuildPart() as part:
    # --- spiral built from Spline + Frenet sweep ---
    with BuildLine() as spiral_path:
        Spline(*pts)
    with BuildSketch(spiral_path.line ^ 0) as spiral_profile:
        Circle(tube_r)
    sweep(is_frenet=True)

with BuildPart() as part2:
    # --- tapered helix on a cone (same H and turns as above) ---
    pitch = H / N
    cone_deg = degrees(
        atan((r1 - r0) / H)
    )  # cone angle so radius grows r0 -> r1 over H

    # first strand
    with BuildLine() as cone_path_1:
        Helix(pitch=pitch, height=H, radius=r0, cone_angle=cone_deg)
    with BuildSketch(cone_path_1.line ^ 0) as cone_prof_1:
        Circle(tube_r)
    sweep(is_frenet=True)

    # OPTIONAL: second strand 180° out of phase (double-helix look)
    with BuildLine() as cone_path_2:
        Rotation(0, 0, 180) * Helix(
            pitch=pitch, height=H, radius=r0, cone_angle=cone_deg
        )
    with BuildSketch(cone_path_2.line ^ 0) as cone_prof_2:
        Circle(tube_r)
    sweep(is_frenet=True)

part2.part.position += (50, 0, 0)

print(
    f"cone helix: pitch={pitch:.3f}, cone_angle={cone_deg:.3f}°  |  constant-slope ds/dz={m:.4f}"
)
show(spiral_path, spiral_profile, part, part2)
