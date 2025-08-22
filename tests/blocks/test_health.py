from uuid import uuid4

from dnd.blocks.health import Health, HealthConfig, HitDiceConfig
from dnd.core.modifiers import DamageType


def create_health():
    hd_config = HitDiceConfig(hit_dice_value=8, hit_dice_count=2, mode="maximums")
    config = HealthConfig(hit_dices=[hd_config])
    return Health.create(source_entity_uuid=uuid4(), config=config)


def test_health_creation_and_hit_points():
    health = create_health()
    # 2d8 with maximums -> 16 hit points
    assert health.hit_dices_total_hit_points == 16
    # constitution modifier 2 adds 4
    assert health.get_max_hit_dices_points(2) == 20
    assert health.get_total_hit_points(2) == 20


def test_damage_and_heal():
    health = create_health()
    source = uuid4()
    # add temporary hit points and take damage
    health.add_temporary_hit_points(5, source)
    remaining = health.take_damage(8, DamageType.SLASHING, source)
    # 5 absorbed, 3 taken
    assert remaining == 3
    assert health.damage_taken == 3
    assert health.temporary_hit_points.score == 0
    # heal some damage
    health.heal(2)
    assert health.damage_taken == 1
