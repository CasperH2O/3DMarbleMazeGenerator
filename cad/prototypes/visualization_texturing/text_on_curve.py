from typing import Optional

from build123d import *
from ocp_vscode import *

text = Text("hello world", 12)
curve2 = Bezier((0, 5), (10, 20), (20, 20), (30, 10))


def text_on_curve(
    text: Text,
    dst_curve: Wire | Edge,
    src_curve: Optional[Wire | Edge] = None,
):
    text_bb = text.bounding_box()
    if not src_curve:
        src_curve = Line((text_bb.min.X, text_bb.min.Y), (text_bb.max.X, text_bb.min.Y))

    def face_on_curve(f: Face):
        bb = f.bounding_box()
        p0 = Vector(bb.center().X, text_bb.min.X)
        src_pt, _ = src_curve.closest_points(Vertex(p0))
        t = src_curve.param_at_point(src_pt)
        dst_pt = dst_curve.position_at(t)
        return (
            f.moved(Location(-src_pt))
            .rotate(Axis.Z, dst_curve.tangent_angle_at(t))
            .moved(Location(dst_pt))
        )

    return Compound.make_compound(map(face_on_curve, text.faces()))


show((curve2, text, text_on_curve(text, curve2)))
