import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))
from dnd.core.base_tiles import Tile


@pytest.fixture(autouse=True)
def clear_tiles():
    Tile._tile_registry = {}
    Tile._tile_by_position = {}
    yield
    Tile._tile_registry = {}
    Tile._tile_by_position = {}


def test_create_and_lookup():
    positions = [(x, y) for x in range(2) for y in range(2)]
    for pos in positions:
        Tile.create(pos)

    assert len(Tile.get_all_tiles()) == len(positions)
    tile = Tile.get_tile_at_position((1, 1))
    assert tile is not None and tile.position == (1, 1)


def test_fov_with_blocking_tile():
    for x in range(3):
        for y in range(3):
            Tile.create((x, y))
    Tile.create((1, 0), can_walk=False, can_see=False)

    visible = set(Tile.get_fov((0, 0)))
    grid_positions = {(x, y) for x in range(3) for y in range(3)}
    visible_inside = visible & grid_positions

    assert (2, 0) not in visible_inside
    assert (2, 1) in visible_inside


def test_get_paths_with_obstacles_and_limits():
    for x in range(3):
        for y in range(3):
            Tile.create((x, y))
    Tile.create((1, 0), can_walk=False, can_see=False)

    distances, paths = Tile.get_paths((0, 0))
    assert distances[(2, 0)] == 2
    assert paths[(2, 0)] == [(0, 0), (1, 1), (2, 0)]

    limited_distances, _ = Tile.get_paths((0, 0), max_distance=1)
    assert (2, 0) not in limited_distances