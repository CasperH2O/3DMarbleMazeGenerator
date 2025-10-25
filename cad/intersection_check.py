from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterator, List, Sequence, Tuple

from build123d import Face, Shape
from OCP.Bnd import Bnd_Box
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepBndLib import BRepBndLib
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer


@dataclass(frozen=True)
class BBox:
    """Axis-aligned bounding box.

    Coordinates are (xmin, ymin, zmin, xmax, ymax, zmax).
    """

    xmin: float
    ymin: float
    zmin: float
    xmax: float
    ymax: float
    zmax: float

    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.xmin + self.xmax) * 0.5,
            (self.ymin + self.ymax) * 0.5,
            (self.zmin + self.zmax) * 0.5,
        )

    @property
    def extents(self) -> Tuple[float, float, float]:
        return (
            self.xmax - self.xmin,
            self.ymax - self.ymin,
            self.zmax - self.zmin,
        )

    def longest_axis(self) -> int:
        ex = self.extents
        return 0 if ex[0] >= ex[1] and ex[0] >= ex[2] else (1 if ex[1] >= ex[2] else 2)

    def union(self, other: "BBox") -> "BBox":
        return BBox(
            xmin=min(self.xmin, other.xmin),
            ymin=min(self.ymin, other.ymin),
            zmin=min(self.zmin, other.zmin),
            xmax=max(self.xmax, other.xmax),
            ymax=max(self.ymax, other.ymax),
            zmax=max(self.zmax, other.zmax),
        )

    def overlaps(self, other: "BBox", tol: float = 0.0) -> bool:
        # Separating axis test with tolerance
        return not (
            self.xmax < other.xmin - tol
            or other.xmax < self.xmin - tol
            or self.ymax < other.ymin - tol
            or other.ymax < self.ymin - tol
            or self.zmax < other.zmin - tol
            or other.zmax < self.zmin - tol
        )


def face_bbox(face: Face) -> BBox:
    """Compute a tight-ish OCCT bounding box for a single face.

    Args:
        face: build123d Face to bound.
    """
    box = Bnd_Box()
    use_triangulation = True

    BRepBndLib.Add_s(face.wrapped, box, use_triangulation)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return BBox(xmin, ymin, zmin, xmax, ymax, zmax)


@dataclass
class BVHNode:
    """Node in a Bounding Volume Hierarchy (BVH) over face bounding boxes."""

    bbox: BBox
    idxs: List[int]  # leaf indices (faces) when non-empty
    left: "BVHNode | None" = None
    right: "BVHNode | None" = None
    count: int = 0  # number of faces under this node (leaf or subtree)

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


def _union_all(bboxes: Sequence[BBox], idxs: Sequence[int]) -> BBox:
    bb = bboxes[idxs[0]]
    for i in idxs[1:]:
        bb = bb.union(bboxes[i])
    return bb


def build_bvh(
    bboxes: Sequence[BBox], idxs: Sequence[int] | None = None, leaf_size: int = 4
) -> BVHNode:
    """Recursively build a median-split Bounding Volume Hierarchy (BVH).

    Splits by the longest axis using the median of face centers.
    """
    if not bboxes:
        raise ValueError("build_bvh: 'bboxes' must be non-empty")

    if idxs is None:
        idxs = list(range(len(bboxes)))
    else:
        idxs = list(idxs)  # copy (we sort)

    node_bb = _union_all(bboxes, idxs)

    if len(idxs) <= leaf_size:
        return BVHNode(
            bbox=node_bb, idxs=list(idxs), left=None, right=None, count=len(idxs)
        )

    # split by largest axis of the node bbox, median on centers
    axis = node_bb.longest_axis()
    idxs.sort(key=lambda i: bboxes[i].center[axis])
    mid = len(idxs) // 2

    left = build_bvh(bboxes, idxs[:mid], leaf_size)
    right = build_bvh(bboxes, idxs[mid:], leaf_size)

    return BVHNode(
        bbox=node_bb, idxs=[], left=left, right=right, count=left.count + right.count
    )


def _pairs_within_node(node: BVHNode) -> Iterator[Tuple[int, int]]:
    """Generate candidate pairs where boxes overlap (self-traversal)."""
    if node.is_leaf:
        # all pairs in the leaf (i < j by construction from combinations)
        yield from combinations(node.idxs, 2)
        return

    # pairs from children individually
    if node.left is not None:
        yield from _pairs_within_node(node.left)
    if node.right is not None:
        yield from _pairs_within_node(node.right)

    # cross pairs: recurse with overlap pruning
    if node.left is not None and node.right is not None:
        yield from _cross_pairs(node.left, node.right)


def _cross_pairs(a: BVHNode, b: BVHNode) -> Iterator[Tuple[int, int]]:
    """Iteratively traverse two BVH subtrees and yield overlapping leaf pairs.

    Uses a heuristic to descend the larger subtree first and avoids Python
    recursion depth limits.
    """
    stack: List[Tuple[BVHNode, BVHNode]] = [(a, b)]
    while stack:
        na, nb = stack.pop()
        if not na.bbox.overlaps(nb.bbox):
            continue

        if na.is_leaf and nb.is_leaf:
            for i in na.idxs:
                for j in nb.idxs:
                    if i < j:
                        yield (i, j)
            continue

        # Descend the larger subtree to keep traversal shallow
        if (not na.is_leaf) and (nb.is_leaf or na.count >= nb.count):
            stack.append((na.left, nb))
            stack.append((na.right, nb))
        else:
            stack.append((na, nb.left))
            stack.append((na, nb.right))


def do_faces_intersect(shape: Shape) -> bool:
    """Return True if *any* pair of faces in the shape intersect.

    Used to confirm swept spline path segments do not have any
    self intersections and can thus be properly 3D printed.

    Check works in two phases, first determine
    which faces cannot intersect at all so these don't have to be considered,
    then the remaining faces are actually checked for intersection.

    Broad-phase uses an axis-aligned Bounding Volume Hierarchy (BVH);
    narrow-phase uses OCCT's ``BRepAlgoAPI_Section``. Edges already present on
    the source shape are ignored to avoid reporting clean shared edges.
    """
    faces = list(shape.faces())
    if len(faces) < 2:
        return False

    bboxes = [face_bbox(f) for f in faces]

    # BVH broad-phase
    leaf_size = 4
    root = build_bvh(bboxes, leaf_size=leaf_size)
    candidate_pairs = _pairs_within_node(root)

    # Hash the original edges so we can skip shared edges later
    edge_hashes = {hash(e.wrapped) for e in shape.edges()}

    # Hardcoded AABB overlap tolerance for narrow-phase precheck
    aabb_tol = 1e-9

    # Narrow-phase: exact test only on candidates whose AABBs overlap
    for i, j in candidate_pairs:
        bi, bj = bboxes[i], bboxes[j]
        if not bi.overlaps(bj, aabb_tol):
            continue

        fi, fj = faces[i].wrapped, faces[j].wrapped
        sec = BRepAlgoAPI_Section(fi, fj)
        sec.Build()
        if not sec.IsDone():
            continue

        exp = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
        while exp.More():
            if hash(exp.Current()) not in edge_hashes:
                return True
            exp.Next()

    return False
