import pytest
from uuid import uuid4
from unittest.mock import patch

from dnd.entity import Entity, EntityConfig
from dnd.blocks.abilities import AbilityScoresConfig
from dnd.blocks.skills import SkillSetConfig
from dnd.blocks.saving_throws import SavingThrowSetConfig
from dnd.blocks.health import HealthConfig, HitDiceConfig
from dnd.blocks.equipment import EquipmentConfig, Damage
from dnd.blocks.action_economy import ActionEconomyConfig
from dnd.core.modifiers import DamageType
from dnd.core.dice import AttackOutcome
from dnd.core.events import RangeType
from dnd.core.values import ModifiableValue


def create_basic_entity():
    entity_uuid = uuid4()
    config = EntityConfig(
        ability_scores=AbilityScoresConfig(),
        skill_set=SkillSetConfig(),
        saving_throws=SavingThrowSetConfig(),
        health=HealthConfig(
            hit_dices=[HitDiceConfig(hit_dice_value=6, hit_dice_count=1, mode="average", ignore_first_level=False)]
        ),
        equipment=EquipmentConfig(),
        action_economy=ActionEconomyConfig(),
        proficiency_bonus=2,
    )
    return Entity.create(source_entity_uuid=entity_uuid, name="Test", config=config)


def test_entity_take_damage_returns_roll_and_updates_health():
    entity = create_basic_entity()
    damage = Damage(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        damage_dice=4,
        dice_numbers=1,
        damage_bonus=ModifiableValue.create(source_entity_uuid=entity.uuid, base_value=0, value_name="Damage Bonus"),
        damage_type=DamageType.BLUDGEONING,
    )
    with patch("dnd.core.dice.random.randint", return_value=3):
        rolls = entity.take_damage([damage], AttackOutcome.HIT)
    assert len(rolls) == 1
    assert rolls[0].total == 3
    assert entity.health.damage_taken == 3


def test_health_heal_and_death_conditions():
    entity = create_basic_entity()
    max_hp = entity.get_hp()

    entity.health.take_damage(2, DamageType.BLUDGEONING, uuid4())
    assert entity.health.get_total_hit_points(0) == max_hp - 2

    entity.health.heal(1)
    assert entity.health.get_total_hit_points(0) == max_hp - 1

    entity.health.take_damage(max_hp - 1, DamageType.BLUDGEONING, uuid4())
    assert entity.health.get_total_hit_points(0) == 0

    entity.health.take_damage(max_hp, DamageType.BLUDGEONING, uuid4())
    assert entity.health.get_total_hit_points(0) < 0


def test_action_economy_can_afford_and_consume():
    entity = create_basic_entity()
    ae = entity.action_economy

    assert ae.can_afford("actions", 1)
    ae.consume("actions", 1)
    assert not ae.can_afford("actions", 1)
    with pytest.raises(ValueError):
        ae.consume("actions", 1)


def test_entity_range_and_bonuses():
    entity = create_basic_entity()

    rng = entity.get_weapon_range()
    assert rng.type == RangeType.REACH and rng.normal == 5

    assert entity.attack_bonus().normalized_score == 2
    assert entity.ac_bonus().normalized_score == 10