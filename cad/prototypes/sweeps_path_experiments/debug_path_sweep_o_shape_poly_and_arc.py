from build123d import *
from ocp_vscode import Camera, set_defaults, show_all

# Note: this worked fine, issue lied with orientation of the O face seam orientation (again)

# Points
p0 = Vector(-67.5, 0, 0)
p1 = Vector(-62.5, 0, 0)  # arc start
p2 = Vector(-61.69481, 10, 0)  # arc end
p3 = Vector(-40, 10, 0)

# Arc defined by center at the origin
center = Vector(0, 0, 0)
R = (p1 - center).length  # 62.5

PROFILE_RADIUS = 9.999 / 2  # just a sample Ø9.999 profile to sweep

with BuildPart() as model:
    # Build the path
    with BuildLine() as path:
        Polyline([p0, p1])  # first straight
        RadiusArc(p1, p2, R)  # arc (radius = |p1 - origin|)
        Polyline([p2, p3])  # second straight
        Bezier(p3, (-30, 10, 0), (-30, 10, 10))
        Polyline([(-30, 10, 10), (-30, 10, 30), (-25, 10, 30)])

    # Sketch a circular profile with hole at the path start and sweep it
    with BuildSketch(path.line ^ 0):  # place at path start
        Circle(PROFILE_RADIUS)
        Circle(radius=PROFILE_RADIUS - 1, mode=Mode.SUBTRACT)

    sweep(transition=Transition.ROUND)
    model.part.color = "#579B3C"

# View
set_defaults(reset_camera=Camera.KEEP)
show_all()
