from build123d import *
from ocp_vscode import show


def revolve_both(
    face: Face | Sketch, axis: Axis = Axis.Z, angle_deg: float = 180.0
) -> Part:
    """
    Revolve a given face in both directions around 'axis' by +/- angle_deg.
    """
    angle_deg = max(0, min(angle_deg, 180))  # clamp to prevent overlap

    # +angle
    with BuildPart() as pos_build:
        revolve(profiles=face, axis=axis, revolution_arc=+abs(angle_deg))
    # -angle
    with BuildPart() as neg_build:
        revolve(profiles=face, axis=axis, revolution_arc=-abs(angle_deg))
    return pos_build.part + neg_build.part


# Values
R = 20.0  # major radius (distance from axis to circle center)
r = 5.0  # minor radius (circle radius)

# Sketch
with BuildSketch(Plane.XZ) as s:  # circle drawn in XZ plane
    with Locations((R, 0)):  # offset so it doesn't cross the Z axis
        Circle(r)  # produces a face-like Sketch

# Revolve the sketch face both directions about Z by 120°
ring = revolve_both(s.sketch, axis=Axis.Z, angle_deg=120)

# Visualize end result
show(ring)
