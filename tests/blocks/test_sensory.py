from uuid import uuid4

from dnd.entity import Entity


def test_visibility_with_limited_vision_range():
    """Entity senses should only return paths for targets within vision range."""
    watcher = Entity.create(uuid4())
    target_visible = Entity.create(uuid4())
    target_hidden = Entity.create(uuid4())

    watcher.senses.update_senses(
        entities={
            target_visible.uuid: (2, 0),  # 10 ft away
            target_hidden.uuid: (8, 0),  # 40 ft away
        },
        visible={(2, 0): True},
        walkable={},
        paths={
            (2, 0): [(1, 0), (2, 0)],
            (8, 0): [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0)],
        },
    )

    vision_limit_tiles = 4  # 20 ft vision range

    assert watcher.senses.get_path_to_entity(target_visible.uuid, max_path_length=vision_limit_tiles) == [
        (1, 0),
        (2, 0),
    ]
    assert watcher.senses.get_path_to_entity(target_hidden.uuid, max_path_length=vision_limit_tiles) == []

    assert watcher.senses.visible.get((2, 0), False)
    assert not watcher.senses.visible.get((8, 0), False)

    assert watcher.senses.get_feet_distance((2, 0)) == 10
    assert watcher.senses.get_feet_distance((8, 0)) == 40
