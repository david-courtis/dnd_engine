from uuid import uuid4

from dnd.blocks.abilities import (
    Ability,
    AbilityConfig,
    AbilityScores,
    AbilityScoresConfig,
)


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
