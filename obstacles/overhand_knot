# obstacles/overhand_knot.py

from build123d import *
from math import sin, cos, pi
from ocp_vscode import *

def points(t0, t1, samples):
    sa = 10
    return [
        Vector(
            sa * (sin(t / samples) + 2 * sin(2 * t / samples)),
            sa * (cos(t / samples) - 2 * cos(2 * t / samples)),
            sa * (-sin(3 * t / samples)),
        )
        for t in range(int(t0), int(t1 * samples))
    ]

zz = points(pi / 3, 4 * pi / 3, 200)
ibeam_hh = 5
ibeam_th = 1

with BuildPart() as p:
    with BuildLine() as l:
        m1 = Spline(zz)
        m2 = Line(m1 @ 1, m1 @ 1 + 40 * (m1 % 1))
        m3 = Line(m1 @ 0, m1 @ 0 - 40 * (m1 % 0))

    height_width = 10
    wall_thickness = 1.2

    half_width = height_width / 2
    inner_half_width = half_width - wall_thickness

    l_shape_points = [
        (-half_width,  half_width),      # 1
        (-inner_half_width,  half_width),# 2
        (-inner_half_width, -inner_half_width), # 3
        ( half_width, -inner_half_width),# 4
        ( half_width, -half_width),      # 5
        (-half_width, -half_width),      # 6
        (-half_width,  half_width)       # close
    ]

    with BuildSketch(l.line ^ 0) as l_shape_sketch:
        with BuildLine(Rot(Z=-90)):
            Polyline(l_shape_points)
        make_face()
    sweep()

show_object(p)
