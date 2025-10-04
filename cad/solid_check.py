from itertools import combinations

from build123d import Shape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer


def do_faces_intersect(shape: Shape) -> bool:
    """Return ``True`` when any pair of faces on ``shape`` intersect.

    The function examines every pair of faces on ``shape`` and uses an OCCT
    section operation to determine whether their intersection produces an
    edge that does not already belong to the original shape. It immediately
    returns ``True`` upon discovering such an intersection and ``False`` when
    none of the face pairs generate a new edge.
    """
    shape_topods_edges = [e.wrapped for e in shape.edges()]
    hashes = [hash(e) for e in shape_topods_edges]
    for faces in combinations(shape.faces(), 2):
        topods_faces = [f.wrapped for f in faces]
        section = BRepAlgoAPI_Section(*topods_faces)
        section.Build()
        if not section.IsDone():
            continue

        explorer = TopExp_Explorer(section.Shape(), TopAbs_EDGE)
        while explorer.More():
            if hash(explorer.Current()) not in hashes:
                return True
            explorer.Next()
    return False
