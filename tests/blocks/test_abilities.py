from uuid import uuid4

from dnd.blocks.abilities import (
    Ability,
    AbilityConfig,
    AbilityScores,
    AbilityScoresConfig,
)
from dnd.blocks.skills import SkillSetConfig, SkillConfig
from dnd.blocks.saving_throws import SavingThrowSetConfig
from dnd.blocks.health import HealthConfig
from dnd.blocks.equipment import EquipmentConfig
from dnd.blocks.action_economy import ActionEconomyConfig
from dnd.entity import Entity, EntityConfig
from dnd.core.modifiers import AdvantageModifier, AdvantageStatus
from app.models.skills import SkillBonusCalculationSnapshot


def test_ability_creation_and_modifier():
    config = AbilityConfig(
        ability_score=16,
        modifier_bonus=1,
    )
    ability = Ability.create(source_entity_uuid=uuid4(), name="strength", config=config)

    # base ability score
    assert ability.ability_score.score == 16
    # modifier combines normalized ability score and bonus
    assert ability.modifier == 4


def test_value_retrieval():
    ability = Ability.create(source_entity_uuid=uuid4(), name="dexterity", config=AbilityConfig())
    retrieved = ability.get_value_from_name("dexterity Ability Score")
    assert retrieved is ability.ability_score


def test_ability_level_based_and_modifier_overrides():
    config = AbilityConfig(
        ability_score=15,
        ability_scores_modifiers=[("level 4", 1), ("level 8", 1)],
        modifier_bonus=1,
        modifier_bonus_modifiers=[("feat", 2)],
    )
    ability = Ability.create(source_entity_uuid=uuid4(), name="strength", config=config)

    assert ability.ability_score.score == 17
    assert ability.modifier == 7


def test_negative_modifiers_and_proficiency_bonus():
    config = AbilityConfig(
        ability_score=9,
        ability_scores_modifiers=[("curse", -2)],
        modifier_bonus_modifiers=[("proficiency", 3)],
    )
    ability = Ability.create(source_entity_uuid=uuid4(), name="wisdom", config=config)

    assert ability.ability_score.score == 7
    assert ability.modifier == 0


def test_negative_final_modifier():
    config = AbilityConfig(ability_score=8, modifier_bonus=-1)
    ability = Ability.create(source_entity_uuid=uuid4(), name="charisma", config=config)
    assert ability.modifier == -2


def test_get_combined_values_matches_modifier():
    config = AbilityConfig(ability_score=12, modifier_bonus=2)
    ability = Ability.create(source_entity_uuid=uuid4(), name="constitution", config=config)
    combined = ability.get_combined_values()

    assert combined.score == 14
    assert combined.normalized_score == ability.modifier


def test_get_by_uuid():
    ability = Ability.create(source_entity_uuid=uuid4(), name="intelligence", config=AbilityConfig())
    retrieved = Ability.get(ability.uuid)
    assert retrieved is ability


def test_ability_scores_modifier_retrieval_methods():
    config = AbilityScoresConfig(
        strength=AbilityConfig(ability_score=16),
        wisdom=AbilityConfig(ability_score=7),
    )
    scores = AbilityScores.create(source_entity_uuid=uuid4(), config=config)

    str_uuid = scores.strength.uuid
    assert scores.get_modifier(str_uuid) == 3
    assert scores.get_modifier_from_uuid(str_uuid) == 3
    assert scores.get_modifier_from_name("wisdom") == -2
    assert scores.get_ability("wisdom") is scores.wisdom
    assert scores.ability_blocks_uuid_by_name["strength"] == str_uuid
    assert scores.ability_blocks_names_by_uuid[str_uuid] == "strength"


def _make_entity(proficiency: bool, expertise: bool, advantage: AdvantageStatus | None):
    entity_config = EntityConfig(
        ability_scores=AbilityScoresConfig(
            dexterity=AbilityConfig(ability_score=14),
        ),
        skill_set=SkillSetConfig(
            acrobatics=SkillConfig(proficiency=proficiency, expertise=expertise)
        ),
        saving_throws=SavingThrowSetConfig(),
        health=HealthConfig(),
        equipment=EquipmentConfig(),
        action_economy=ActionEconomyConfig(),
        proficiency_bonus=2,
    )
    entity = Entity.create(source_entity_uuid=uuid4(), config=entity_config)
    if advantage is not None:
        entity.skill_set.acrobatics.skill_bonus.self_static.add_advantage_modifier(
            AdvantageModifier(
                source_entity_uuid=entity.uuid,
                target_entity_uuid=entity.uuid,
                value=advantage,
            )
        )
    return entity


def test_skill_bonus_and_advantage_with_proficiency_levels():
    untrained = _make_entity(False, False, None)
    proficient = _make_entity(True, False, AdvantageStatus.ADVANTAGE)
    expert = _make_entity(True, True, AdvantageStatus.DISADVANTAGE)

    untrained_calc = SkillBonusCalculationSnapshot.from_engine(untrained, "acrobatics")
    assert untrained_calc.final_modifier == 2
    assert untrained_calc.normalized_proficiency_bonus.normalized_score == 0
    assert untrained_calc.total_bonus.advantage == AdvantageStatus.NONE

    proficient_calc = SkillBonusCalculationSnapshot.from_engine(proficient, "acrobatics")
    assert proficient_calc.final_modifier == 4
    assert proficient_calc.normalized_proficiency_bonus.normalized_score == 2
    assert proficient_calc.total_bonus.advantage == AdvantageStatus.ADVANTAGE

    expert_calc = SkillBonusCalculationSnapshot.from_engine(expert, "acrobatics")
    assert expert_calc.final_modifier == 6
    assert expert_calc.normalized_proficiency_bonus.normalized_score == 4
    assert expert_calc.total_bonus.advantage == AdvantageStatus.DISADVANTAGE
