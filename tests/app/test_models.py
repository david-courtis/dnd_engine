import sys
from pathlib import Path

import pytest
from uuid import uuid4
from pydantic import ValidationError

# Ensure the repository root is on the import path for namespace packages
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.abilities import AbilitySnapshot, AbilityScoresSnapshot
from app.models.values import ModifiableValueSnapshot
from app.models.equipment import AttackBonusCalculationSnapshot, RangeSnapshot
from app.models.entity import EntitySummary
from app.models.sensory import SensesSnapshot

from dnd.core.modifiers import (
    AdvantageStatus,
    CriticalStatus,
    AutoHitStatus,
)
from dnd.core.events import RangeType, WeaponSlot


def make_value(score: int, normalized: int | None = None) -> ModifiableValueSnapshot:
    """Helper to create a minimal ModifiableValueSnapshot."""
    return ModifiableValueSnapshot(
        uuid=uuid4(),
        name="value",
        source_entity_uuid=uuid4(),
        score=score,
        normalized_score=normalized if normalized is not None else score,
        advantage=AdvantageStatus.NONE,
        outgoing_advantage=AdvantageStatus.NONE,
        critical=CriticalStatus.NONE,
        outgoing_critical=CriticalStatus.NONE,
        auto_hit=AutoHitStatus.NONE,
        outgoing_auto_hit=AutoHitStatus.NONE,
    )


def test_ability_snapshot_valid_and_computed():
    ability_score = make_value(15)
    modifier_bonus = make_value(1)
    expected = (ability_score.normalized_score - 10) // 2 + modifier_bonus.normalized_score
    ability = AbilitySnapshot(
        uuid=uuid4(),
        name="strength",
        ability_score=ability_score,
        modifier_bonus=modifier_bonus,
        modifier=expected,
    )
    assert ability.modifier == expected


def test_ability_snapshot_model_validate_error():
    ability_score = make_value(10).model_dump()
    modifier_bonus = make_value(0).model_dump()
    data = {
        "uuid": "not-a-uuid",
        "name": "strength",
        "ability_score": ability_score,
        "modifier_bonus": modifier_bonus,
        "modifier": 0,
    }
    with pytest.raises(ValidationError):
        AbilitySnapshot.model_validate(data)


def test_ability_scores_snapshot_defaults():
    def ability(name: str) -> AbilitySnapshot:
        score = make_value(10)
        return AbilitySnapshot(
            uuid=uuid4(),
            name=name,
            ability_score=score,
            modifier_bonus=make_value(0),
            modifier=(score.normalized_score - 10) // 2,
        )

    scores = AbilityScoresSnapshot(
        uuid=uuid4(),
        name="Abilities",
        source_entity_uuid=uuid4(),
        strength=ability("strength"),
        dexterity=ability("dexterity"),
        constitution=ability("constitution"),
        intelligence=ability("intelligence"),
        wisdom=ability("wisdom"),
        charisma=ability("charisma"),
    )
    assert scores.abilities == []


def test_attack_bonus_calculation_snapshot_defaults_and_computed():
    total = make_value(7)
    calc = AttackBonusCalculationSnapshot(
        weapon_slot=WeaponSlot.MAIN_HAND,
        proficiency_bonus=make_value(2),
        weapon_bonus=make_value(1),
        attack_bonuses=[make_value(1)],
        ability_bonuses=[make_value(3)],
        range=RangeSnapshot(type=RangeType.REACH, normal=5),
        total_bonus=total,
        final_modifier=total.normalized_score,
    )
    assert calc.weapon_name is None
    assert calc.properties == []
    assert calc.final_modifier == total.normalized_score


def test_attack_bonus_calculation_snapshot_model_validate_error():
    base = make_value(0).model_dump()
    data = {
        "weapon_slot": "INVALID",
        "proficiency_bonus": base,
        "weapon_bonus": base,
        "attack_bonuses": [base],
        "ability_bonuses": [base],
        "range": {"type": RangeType.REACH, "normal": 5},
        "total_bonus": base,
        "final_modifier": 0,
    }
    with pytest.raises(ValidationError):
        AttackBonusCalculationSnapshot.model_validate(data)


def test_entity_summary_defaults_and_computed():
    senses = SensesSnapshot(position=(0, 0))
    summary = EntitySummary(
        uuid=uuid4(),
        name="Bob",
        current_hp=8,
        max_hp=10,
        position=(1, 2),
        senses=senses,
    )
    assert summary.armor_class is None
    assert summary.target_entity_uuid is None
    assert summary.max_hp - summary.current_hp == 2


def test_entity_summary_model_validate_error():
    senses = SensesSnapshot(position=(0, 0)).model_dump()
    data = {
        "uuid": str(uuid4()),
        "name": "Bob",
        "current_hp": 5,
        "max_hp": 10,
        "position": "invalid",
        "senses": senses,
    }
    with pytest.raises(ValidationError):
        EntitySummary.model_validate(data)


def test_modifiable_value_snapshot_defaults_and_computed():
    value = ModifiableValueSnapshot(
        uuid=uuid4(),
        name="HP",
        source_entity_uuid=uuid4(),
        score=12,
        normalized_score=12,
        min_value=0,
        max_value=20,
        advantage=AdvantageStatus.NONE,
        outgoing_advantage=AdvantageStatus.NONE,
        critical=CriticalStatus.NONE,
        outgoing_critical=CriticalStatus.NONE,
        auto_hit=AutoHitStatus.NONE,
        outgoing_auto_hit=AutoHitStatus.NONE,
    )
    assert value.resistances == {}
    assert value.channels == []
    assert value.min_value <= value.normalized_score <= value.max_value


def test_modifiable_value_snapshot_model_validate_error():
    data = {
        "uuid": str(uuid4()),
        "name": "HP",
        "source_entity_uuid": str(uuid4()),
        "score": "high",
        "normalized_score": 10,
        "advantage": AdvantageStatus.NONE,
        "outgoing_advantage": AdvantageStatus.NONE,
        "critical": CriticalStatus.NONE,
        "outgoing_critical": CriticalStatus.NONE,
        "auto_hit": AutoHitStatus.NONE,
        "outgoing_auto_hit": AutoHitStatus.NONE,
    }
    with pytest.raises(ValidationError):
        ModifiableValueSnapshot.model_validate(data)
