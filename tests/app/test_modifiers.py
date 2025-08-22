import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

# Ensure repository root on path for namespace packages
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.modifiers import (
    NumericalModifierSnapshot,
    AdvantageModifierSnapshot,
    CriticalModifierSnapshot,
    AutoHitModifierSnapshot,
    ResistanceModifierSnapshot,
    SizeModifierSnapshot,
    AdvantageStatus,
    AutoHitStatus,
    CriticalStatus,
    ResistanceStatus,
    DamageType,
    Size,
)


def make_modifier(**kwargs):
    base = {
        "uuid": uuid4(),
        "name": "mod",
        "source_entity_uuid": uuid4(),
        "source_entity_name": "source",
        "target_entity_uuid": uuid4(),
        "target_entity_name": "target",
        "is_outgoing_modifier": kwargs.pop("is_outgoing_modifier", False),
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def assert_base_fields(snapshot, mod):
    assert snapshot.uuid == mod.uuid
    assert snapshot.name == mod.name
    assert snapshot.source_entity_uuid == mod.source_entity_uuid
    assert snapshot.source_entity_name == mod.source_entity_name
    assert snapshot.target_entity_uuid == mod.target_entity_uuid
    assert snapshot.target_entity_name == mod.target_entity_name


@pytest.mark.parametrize("value,normalized,is_outgoing", [(5, 5, True), (-3, -3, False)])
def test_numerical_modifier_snapshot_from_engine(value, normalized, is_outgoing):
    mod = make_modifier(value=value, normalized_value=normalized, is_outgoing_modifier=is_outgoing)
    snapshot = NumericalModifierSnapshot.from_engine(mod)
    assert_base_fields(snapshot, mod)
    assert snapshot.value == value
    assert snapshot.normalized_value == normalized


@pytest.mark.parametrize(
    "status,num,is_outgoing",
    [
        (AdvantageStatus.ADVANTAGE, 1, True),
        (AdvantageStatus.DISADVANTAGE, -1, False),
    ],
)
def test_advantage_modifier_snapshot_from_engine(status, num, is_outgoing):
    mod = make_modifier(value=status, numerical_value=num, is_outgoing_modifier=is_outgoing)
    snapshot = AdvantageModifierSnapshot.from_engine(mod)
    assert_base_fields(snapshot, mod)
    assert snapshot.value == status
    assert snapshot.numerical_value == num


@pytest.mark.parametrize(
    "status,is_outgoing",
    [
        (CriticalStatus.AUTOCRIT, True),
        (CriticalStatus.NOCRIT, False),
    ],
)
def test_critical_modifier_snapshot_from_engine(status, is_outgoing):
    mod = make_modifier(value=status, is_outgoing_modifier=is_outgoing)
    snapshot = CriticalModifierSnapshot.from_engine(mod)
    assert_base_fields(snapshot, mod)
    assert snapshot.value == status


@pytest.mark.parametrize(
    "status,is_outgoing",
    [
        (AutoHitStatus.AUTOHIT, True),
        (AutoHitStatus.AUTOMISS, False),
    ],
)
def test_auto_hit_modifier_snapshot_from_engine(status, is_outgoing):
    mod = make_modifier(value=status, is_outgoing_modifier=is_outgoing)
    snapshot = AutoHitModifierSnapshot.from_engine(mod)
    assert_base_fields(snapshot, mod)
    assert snapshot.value == status


@pytest.mark.parametrize(
    "status,num,is_outgoing",
    [
        (ResistanceStatus.RESISTANCE, 1, True),
        (ResistanceStatus.VULNERABILITY, -1, False),
    ],
)
def test_resistance_modifier_snapshot_from_engine(status, num, is_outgoing):
    mod = make_modifier(
        value=status,
        damage_type=DamageType.ACID,
        numerical_value=num,
        is_outgoing_modifier=is_outgoing,
    )
    snapshot = ResistanceModifierSnapshot.from_engine(mod)
    assert_base_fields(snapshot, mod)
    assert snapshot.value == status
    assert snapshot.damage_type == DamageType.ACID
    assert snapshot.numerical_value == num


@pytest.mark.parametrize(
    "size,is_outgoing",
    [
        (Size.SMALL, True),
        (Size.HUGE, False),
    ],
)
def test_size_modifier_snapshot_from_engine(size, is_outgoing):
    mod = make_modifier(value=size, is_outgoing_modifier=is_outgoing)
    snapshot = SizeModifierSnapshot.from_engine(mod)
    assert_base_fields(snapshot, mod)
    assert snapshot.value == size
