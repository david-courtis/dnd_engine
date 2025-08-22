from uuid import uuid4
from unittest.mock import patch

from dnd.blocks.abilities import AbilityConfig, AbilityScoresConfig
from dnd.blocks.saving_throws import SavingThrowConfig, SavingThrowSetConfig
from dnd.blocks.skills import SkillSetConfig
from dnd.blocks.health import HealthConfig
from dnd.blocks.equipment import EquipmentConfig
from dnd.blocks.action_economy import ActionEconomyConfig
from dnd.entity import Entity, EntityConfig
from dnd.core.modifiers import AdvantageModifier, AdvantageStatus


def build_entity(proficient: bool) -> Entity:
    entity_config = EntityConfig(
        ability_scores=AbilityScoresConfig(
            dexterity=AbilityConfig(ability_score=14),
        ),
        saving_throws=SavingThrowSetConfig(
            dexterity_saving_throw=SavingThrowConfig(proficiency=proficient),
        ),
        skill_set=SkillSetConfig(),
        health=HealthConfig(),
        equipment=EquipmentConfig(),
        action_economy=ActionEconomyConfig(),
        proficiency_bonus=2,
    )
    return Entity.create(source_entity_uuid=uuid4(), config=entity_config)


def test_saving_throw_without_proficiency_no_advantage():
    entity = build_entity(proficient=False)

    total_bonus = entity.saving_throw_bonus(None, "dexterity")
    assert total_bonus.normalized_score == 2  # ability modifier only

    source = build_entity(proficient=False)
    request = source.create_saving_throw_request(entity.uuid, "dexterity", 10)

    with patch("dnd.core.dice.random.randint", return_value=10):
        outcome, roll, success = entity.saving_throw(request)

    assert roll.bonus == 2
    assert roll.total == 12
    assert roll.advantage_status == AdvantageStatus.NONE


def test_saving_throw_with_proficiency_and_advantage():
    entity = build_entity(proficient=True)

    adv_mod = AdvantageModifier(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        value=AdvantageStatus.ADVANTAGE,
    )
    entity.saving_throws.dexterity_saving_throw.bonus.self_static.add_advantage_modifier(adv_mod)

    total_bonus = entity.saving_throw_bonus(None, "dexterity")
    assert total_bonus.normalized_score == 4  # ability modifier + proficiency

    source = build_entity(proficient=False)
    request = source.create_saving_throw_request(entity.uuid, "dexterity", 10)

    with patch("dnd.core.dice.random.randint", return_value=10):
        outcome, roll, success = entity.saving_throw(request)

    assert roll.bonus == 4
    assert roll.total == 14
    assert roll.advantage_status == AdvantageStatus.ADVANTAGE
