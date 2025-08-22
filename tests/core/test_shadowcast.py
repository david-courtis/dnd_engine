import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dnd.core.shadowcast import Quadrant, compute_fov


def test_compute_fov_respects_walls_and_max_distance():
    width, height = 5, 5
    origin = (2, 2)
    walls = {(3, 2)}
    visible = set()

    def is_blocking(x: int, y: int) -> bool:
        return (x, y) in walls or x < 0 or y < 0 or x >= width or y >= height

    def mark_visible(x: int, y: int) -> None:
        visible.add((x, y))

    compute_fov(origin, is_blocking, mark_visible, max_distance=2)

    assert origin in visible
    assert (3, 2) in visible
    assert (4, 2) not in visible
    assert (2, 4) in visible
    assert (4, 4) not in visible


def test_quadrant_raises_for_invalid_cardinal():
    with pytest.raises(ValueError):
        Quadrant(4, (0, 0))
