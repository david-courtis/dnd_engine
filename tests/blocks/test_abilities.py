from uuid import uuid4

from dnd.blocks.abilities import Ability, AbilityConfig


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
