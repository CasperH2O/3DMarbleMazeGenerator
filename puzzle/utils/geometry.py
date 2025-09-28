# puzzle/utils/geometry.py

from typing import List, Tuple

from puzzle.node import Node


def manhattan_distance(node_a: Node, node_b: Node) -> float:
    """
    Calculate the Manhattan distance between two nodes in 3D space.

    The Manhattan distance is the sum of the absolute differences between the x, y, and z coordinates of two nodes.
    """
    return (
        abs(node_a.x - node_b.x) + abs(node_a.y - node_b.y) + abs(node_a.z - node_b.z)
    )


def euclidean_distance(node_a: Node, node_b: Node) -> float:
    """
    Calculate the Euclidean distance between two nodes in 3D space.

    The Euclidean distance is the straight-line distance between two points in 3D space.
    """
    return (
        (node_a.x - node_b.x) ** 2
        + (node_a.y - node_b.y) ** 2
        + (node_a.z - node_b.z) ** 2
    ) ** 0.5


def frange(start: float, stop: float, step: float) -> List[float]:
    """
    Generate a range of floating-point numbers from
    start to stop inclusive with a given step
    """

    # inclusive range w/ floating guard
    values: List[float] = []

    while start <= stop + step / 2:
        values.append(round(start, 10))
        start += step

    return values


def squared_distance_xyz(
    ax: float, ay: float, az: float, bx: float, by: float, bz: float
) -> float:
    """
    Squared Euclidean distance between two coordinate triples.
    Use when only relative ordering matters (avoids sqrt in hot paths).
    """
    return (ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2


def snap(val: float, *, decimals: int = 10, zero_tol: float = 1e-9) -> float:
    """
    Round val to decimal places; if the rounded value is closer to zero
    than zero tolerance, return exactly 0.0 so that coordinates that
    should be on axis are placed there.
    """
    v = round(val, decimals)
    return 0.0 if abs(v) < zero_tol else v


def key3(
    x: float, y: float, z: float, *, decimals: int = 10
) -> Tuple[float, float, float]:
    """Return the normalised tuple used as dict-key"""
    return (round(x, decimals), round(y, decimals), round(z, decimals))
