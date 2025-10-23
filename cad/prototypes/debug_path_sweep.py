from build123d import *
from ocp_vscode import *

# Hardcoded radius
PROFILE_RADIUS = 9.999 / 2

bad_poly_pts = [
    (-40.0, 20.0, 10.0),  # <-- removing this fixes everything... :-|
    (-40.0, 20.0, 20.0),
    (-30.0, 20.0, 20.0),
    (-30.0, 30.0, 20.0),
    (-30.0, 30.0, 10.0),
    (-20.0, 30.0, 10.0),
    (-20.0, 30.0, 0.0),
    (-38.299, 30.0, 0.0),
]

fixed_poly_pts = [
    (-40.0, 20.0, 20.0),
    (-30.0, 20.0, 20.0),
    (-30.0, 30.0, 20.0),
    (-30.0, 30.0, 10.0),
    (-20.0, 30.0, 10.0),
    (-20.0, 30.0, 0.0),
    (-38.299, 30.0, 0.0),
]

# Arc
arc_start = Vector(-38.299, 30.0, 0.0)
arc_end = Vector(-10.0, 47.611, 0.0)
arc_R = (arc_start - Vector(0, 0, 0)).length  # center at (0,0,0)

# Short tail from the end of the arc
tail_pts = [
    (-10.0, 47.611, 0.0),
    (-10.0, 30.0, 0.0),
    (-10.0, 30.0, -10.0),
    (0.0, 30.0, -10.0),
]

# Segment with issues
with BuildPart() as seg_bad:
    with BuildLine() as line_bad:
        Polyline(bad_poly_pts)
        RadiusArc(arc_start, arc_end, arc_R)
        Polyline(tail_pts)  # <-- Enabling this makes sweep fail completely

    # ⌀5 mm circular profile at path start
    with BuildSketch(line_bad.line ^ 0) as seg_bad_profile:
        with Locations(
            Location((0, 0, 0), (0, 0, 180))
        ):  # positioning the seam edges as in seg_fixed
            Circle(PROFILE_RADIUS)

    sweep(transition=Transition.ROUND)
    seg_bad.part.color = "#802F2F"

# Segment working
with BuildPart() as seg_fixed:
    with BuildLine() as line_fixed:
        Polyline(fixed_poly_pts)
        RadiusArc(arc_start, arc_end, arc_R)
        Polyline(tail_pts)

    with BuildSketch(line_fixed.line ^ 0) as seg_fixed_profile:
        Circle(PROFILE_RADIUS)

    sweep(transition=Transition.ROUND)

    seg_fixed.part.color = "#579B3C"

# View
set_defaults(reset_camera=Camera.KEEP)
show_all()
