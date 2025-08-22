from uuid import uuid4

from dnd.blocks.abilities import AbilityConfig, AbilityScoresConfig
from dnd.blocks.saving_throws import SavingThrowConfig, SavingThrowSetConfig
from dnd.blocks.skills import SkillSetConfig
from dnd.blocks.health import HealthConfig
from dnd.blocks.equipment import EquipmentConfig
from dnd.blocks.action_economy import ActionEconomyConfig
from dnd.entity import Entity, EntityConfig
from app.models.saving_throws import (
    SavingThrowSetSnapshot,
    SavingThrowBonusCalculationSnapshot,
)


def test_saving_throw_snapshots_proficiency_and_modifiers():
    entity_config = EntityConfig(
        ability_scores=AbilityScoresConfig(
            strength=AbilityConfig(ability_score=16),
            dexterity=AbilityConfig(ability_score=14),
        ),
        saving_throws=SavingThrowSetConfig(
            strength_saving_throw=SavingThrowConfig(proficiency=True),
            dexterity_saving_throw=SavingThrowConfig(proficiency=False),
        ),
        skill_set=SkillSetConfig(),
        health=HealthConfig(),
        equipment=EquipmentConfig(),
        action_economy=ActionEconomyConfig(),
        proficiency_bonus=2,
    )
    entity = Entity.create(source_entity_uuid=uuid4(), config=entity_config)

    snapshot = SavingThrowSetSnapshot.from_engine(entity.saving_throws, entity)

    assert snapshot.saving_throws["strength"].proficiency is True
    assert snapshot.saving_throws["strength"].effective_bonus == 5

    assert snapshot.saving_throws["dexterity"].proficiency is False
    assert snapshot.saving_throws["dexterity"].effective_bonus == 2

    assert "strength" in snapshot.proficient_saving_throws
    assert "dexterity" not in snapshot.proficient_saving_throws

    strength_calc = SavingThrowBonusCalculationSnapshot.from_engine(entity, "strength")
    assert strength_calc.final_modifier == 5
    assert strength_calc.normalized_proficiency_bonus.normalized_score == 2

    dex_calc = SavingThrowBonusCalculationSnapshot.from_engine(entity, "dexterity")
    assert dex_calc.final_modifier == 2
    assert dex_calc.normalized_proficiency_bonus.normalized_score == 0
