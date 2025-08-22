import sys
from pathlib import Path
from uuid import uuid4

import pytest

# Ensure the repository root is on the Python path so ``dnd`` can be imported
sys.path.append(str(Path(__file__).resolve().parents[2]))

from dnd.core.values import ModifiableValue
from dnd.core.modifiers import (
    NumericalModifier,
    AdvantageModifier,
    AdvantageStatus,
    ResistanceModifier,
    ResistanceStatus,
    DamageType,
)


def create_base_value(base: int = 10) -> ModifiableValue:
    """Helper to create a simple ModifiableValue."""
    source_uuid = uuid4()
    return ModifiableValue.create(source_entity_uuid=source_uuid, base_value=base, value_name="Test Value")


def test_numerical_modifier_and_advantage_effects():
    value = create_base_value()

    # Apply numerical modifier and ensure score changes
    num_mod = NumericalModifier(
        name="bonus",
        source_entity_uuid=value.source_entity_uuid,
        target_entity_uuid=value.source_entity_uuid,
        value=5,
    )
    value.self_static.add_value_modifier(num_mod)
    assert value.score == 15

    # Remove modifier and ensure score reverts
    value.self_static.remove_value_modifier(num_mod.uuid)
    assert value.score == 10

    # Apply advantage and check influence
    adv_mod = AdvantageModifier(
        name="adv",
        source_entity_uuid=value.source_entity_uuid,
        target_entity_uuid=value.source_entity_uuid,
        value=AdvantageStatus.ADVANTAGE,
    )
    value.self_static.add_advantage_modifier(adv_mod)
    assert value.advantage is AdvantageStatus.ADVANTAGE

    # Replace with disadvantage
    value.self_static.remove_advantage_modifier(adv_mod.uuid)
    dis_mod = AdvantageModifier(
        name="disadv",
        source_entity_uuid=value.source_entity_uuid,
        target_entity_uuid=value.source_entity_uuid,
        value=AdvantageStatus.DISADVANTAGE,
    )
    value.self_static.add_advantage_modifier(dis_mod)
    assert value.advantage is AdvantageStatus.DISADVANTAGE


def test_resistance_and_vulnerability_effects():
    value = create_base_value()

    # Apply resistance and ensure it is reflected
    res_mod = ResistanceModifier(
        name="fire_res",
        source_entity_uuid=value.source_entity_uuid,
        target_entity_uuid=value.source_entity_uuid,
        value=ResistanceStatus.RESISTANCE,
        damage_type=DamageType.FIRE,
    )
    value.self_static.add_resistance_modifier(res_mod)
    assert value.resistance[DamageType.FIRE] is ResistanceStatus.RESISTANCE

    # Remove resistance and ensure it resets
    value.self_static.remove_resistance_modifier(res_mod.uuid)
    assert value.resistance[DamageType.FIRE] is ResistanceStatus.NONE

    # Apply vulnerability
    vul_mod = ResistanceModifier(
        name="fire_vul",
        source_entity_uuid=value.source_entity_uuid,
        target_entity_uuid=value.source_entity_uuid,
        value=ResistanceStatus.VULNERABILITY,
        damage_type=DamageType.FIRE,
    )
    value.self_static.add_resistance_modifier(vul_mod)
    assert value.resistance[DamageType.FIRE] is ResistanceStatus.VULNERABILITY
