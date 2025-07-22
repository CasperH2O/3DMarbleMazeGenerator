from itertools import combinations

from build123d import Edge, Part, Shape, Vertex
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer


def do_faces_intersect(shape: Shape) -> bool:
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
                return Edge(explorer.Current())
            explorer.Next()
    return False
