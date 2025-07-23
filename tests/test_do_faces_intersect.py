import pytest
from build123d import Compound, Cone, Edge, Face, Plane

from cad.solid_check import do_faces_intersect


@pytest.fixture
def positive_shape():
    # two orthogonal unit‐squares whose faces do intersect
    return Compound(
        [
            Face.make_rect(1, 1, plane=Plane.XY),
            Face.make_rect(1, 1, plane=Plane.XZ),
        ]
    )


@pytest.fixture
def negative_shape():
    # a single cone has no two faces intersecting in a new edge
    return Cone(2, 1, 2)


def test_do_faces_intersect_positive(positive_shape):
    result = do_faces_intersect(positive_shape)
    # should return an Edge instance, not False
    assert isinstance(result, Edge), f"Expected an Edge, got {result!r}"


def test_do_faces_intersect_negative(negative_shape):
    result = do_faces_intersect(negative_shape)
    # should return False
    assert result is False
