from uuid import uuid4

import pytest

from dnd.blocks.health import Health, HealthConfig, HitDiceConfig, HitDice
from dnd.core.modifiers import DamageType, ResistanceStatus
from dnd.core.values import ModifiableValue
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


def test_hit_dice_invalid_mode_and_validation():
    hd = HitDice.create(source_entity_uuid=uuid4())
    hd.mode = "invalid"
    with pytest.raises(ValueError):
        _ = hd.hit_points

    with pytest.raises(ValueError):
        HitDice(
            source_entity_uuid=uuid4(),
            hit_dice_value=ModifiableValue.create(
                source_entity_uuid=uuid4(), base_value=5, value_name="Hit Dice Value"
            ),
        )

    with pytest.raises(ValueError):
        HitDice(
            source_entity_uuid=uuid4(),
            hit_dice_count=ModifiableValue.create(
                source_entity_uuid=uuid4(), base_value=0, value_name="Hit Dice Count"
            ),
        )


def test_take_damage_with_resistances_immunities_and_vulnerabilities():
    source = uuid4()
    config = HealthConfig(
        hit_dices=[HitDiceConfig(hit_dice_value=10, hit_dice_count=1, mode="maximums")],
        temporary_hit_points=5,
        damage_reduction=2,
        vulnerabilities=[DamageType.FIRE],
        resistances=[DamageType.COLD],
        immunities=[DamageType.POISON],
    )
    health = Health.create(source_entity_uuid=uuid4(), config=config)

    assert health.get_resistance(DamageType.FIRE) is ResistanceStatus.VULNERABILITY
    assert health.get_resistance(DamageType.COLD) is ResistanceStatus.RESISTANCE
    assert health.get_resistance(DamageType.POISON) is ResistanceStatus.IMMUNITY

    assert health.get_total_hit_points(0) == 15

    remaining = health.take_damage(7, DamageType.POISON, source)
    assert remaining == 0
    assert health.damage_taken == 0
    assert health.temporary_hit_points.score == 5
    assert health.get_total_hit_points(0) == 15

    remaining = health.take_damage(10, DamageType.COLD, source)
    assert remaining == 0
    assert health.damage_taken == 0
    assert health.temporary_hit_points.score == 2
    assert health.get_total_hit_points(0) == 12

    remaining = health.take_damage(4, DamageType.FIRE, source)
    assert remaining == 4
    assert health.damage_taken == 4
    assert health.temporary_hit_points.score == 0
    assert health.get_total_hit_points(0) == 6


def test_temp_hp_add_remove_and_heal():
    health = create_health()
    source = uuid4()

    health.add_temporary_hit_points(5, source)
    assert health.temporary_hit_points.score == 5

    health.remove_temporary_hit_points(2, source)
    assert health.temporary_hit_points.score == 3

    remaining = health.take_damage(5, DamageType.SLASHING, source)
    assert remaining == 2
    assert health.temporary_hit_points.score == 0
    assert health.damage_taken == 2
    assert health.get_total_hit_points(2) == 21

    health.heal(1)
    assert health.damage_taken == 1
    assert health.get_total_hit_points(2) == 22


def test_roll_death_save_outcomes():
    source = uuid4()

    h1 = create_health()
    h1.take_damage(23, DamageType.SLASHING, source)
    assert h1.get_total_hit_points(2) == 0
    assert h1.roll_death_save(1) is False
    assert h1.death_save_failures == 2
    assert h1.roll_death_save(5) is False
    assert h1.death_save_failures == 3
    assert h1.is_dead

    h2 = create_health()
    h2.take_damage(23, DamageType.SLASHING, source)
    assert h2.get_total_hit_points(2) == 0
    assert h2.roll_death_save(20) is True
    assert h2.is_stable
    assert h2.death_save_failures == 0
    assert h2.death_save_successes == 0
    assert h2.get_total_hit_points(2) == 1

    h3 = create_health()
    h3.take_damage(23, DamageType.SLASHING, source)
    assert h3.roll_death_save(15) is True
    assert h3.death_save_successes == 1
    assert h3.death_save_failures == 0

    h4 = create_health()
    h4.take_damage(23, DamageType.SLASHING, source)
    assert h4.roll_death_save(8) is False
    assert h4.death_save_failures == 1
