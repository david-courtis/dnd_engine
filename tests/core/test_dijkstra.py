import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from dnd.core.dijkstra import dijkstra


def test_dijkstra_diagonal_paths():
    width = height = 3
    is_walkable = lambda x, y: True
    start = (0, 0)

    distances, paths = dijkstra(start, is_walkable, width, height, diagonal=True)

    assert distances[(2, 2)] == 2
    assert paths[(2, 2)] == [
        (0, 0),
        (1, 1),
        (2, 2),
    ]
    assert distances[(0, 2)] == 2
    assert paths[(0, 2)] == [
        (0, 0),
        (0, 1),
        (0, 2),
    ]


def test_dijkstra_max_distance_limits_reach():
    width = height = 3
    is_walkable = lambda x, y: True
    start = (0, 0)

    distances, _ = dijkstra(
        start,
        is_walkable,
        width,
        height,
        diagonal=True,
        max_distance=1,
    )
    assert (1, 1) not in distances

    distances, _ = dijkstra(
        start,
        is_walkable,
        width,
        height,
        diagonal=True,
        max_distance=2,
    )
    assert (1, 1) in distances
    assert distances[(1, 1)] == 1