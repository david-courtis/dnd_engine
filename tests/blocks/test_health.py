from uuid import uuid4

from dnd.blocks.health import Health, HealthConfig, HitDiceConfig
from dnd.core.modifiers import DamageType
from app.models.health import HealthSnapshot


def create_health():
    hd_config = HitDiceConfig(hit_dice_value=8, hit_dice_count=2, mode="maximums")
    # include a max hit points bonus to exercise serialization
    config = HealthConfig(hit_dices=[hd_config], max_hit_points_bonus=3)
    return Health.create(source_entity_uuid=uuid4(), config=config)


def test_health_creation_and_hit_points():
    health = create_health()
    # 2d8 with maximums -> 16 hit points
    assert health.hit_dices_total_hit_points == 16
    # constitution modifier 2 adds 4
    assert health.get_max_hit_dices_points(2) == 20
    # max hit points bonus adds another 3
    assert health.get_total_hit_points(2) == 23


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

    class EntityStub:
        class ability_scores:
            class constitution:
                modifier = 2

    snapshot = HealthSnapshot.from_engine(health, EntityStub())
    assert snapshot.max_hit_points == 23
    assert snapshot.current_hit_points == 22
    assert snapshot.damage_taken == 1


def test_thresholds_death_saves_and_temporary_hp():
    health = create_health()
    source = uuid4()

    # add temporary hit points and take damage across them
    health.add_temporary_hit_points(5, source)
    assert health.get_total_hit_points(2) == 28

    health.take_damage(10, DamageType.SLASHING, source)
    assert health.get_total_hit_points(2) == 18
    assert health.death_save_failures == 0

    # heal some damage
    health.heal(3)
    assert health.get_total_hit_points(2) == 21

    # drop to 0 hit points
    health.take_damage(21, DamageType.SLASHING, source)
    assert health.get_total_hit_points(2) == 0
    assert health.death_save_failures == 0

    # taking damage at 0 HP causes a death save failure
    health.take_damage(1, DamageType.SLASHING, source)
    assert health.death_save_failures == 1
    assert not health.is_dead

    # roll one success and two failures to trigger death
    assert health.roll_death_save(15) is True
    health.roll_death_save(5)
    health.roll_death_save(5)
    assert health.is_dead
