import sys
from pathlib import Path
from uuid import uuid4
from types import SimpleNamespace

# Ensure the repository root is on the import path for namespace packages
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.channels import ModifierChannelSnapshot
from app.models.modifiers import (
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
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class DummyStaticValue:
    def __init__(self):
        self.is_outgoing_modifier = True
        self.value_modifiers = {
            "v": make_modifier(value=1, normalized_value=1)
        }
        self.min_constraints = {
            "min": make_modifier(value=0, normalized_value=0)
        }
        self.max_constraints = {
            "max": make_modifier(value=10, normalized_value=10)
        }
        self.advantage_modifiers = {
            "adv": make_modifier(value=AdvantageStatus.ADVANTAGE, numerical_value=1)
        }
        self.critical_modifiers = {
            "crit": make_modifier(value=CriticalStatus.AUTOCRIT)
        }
        self.auto_hit_modifiers = {
            "hit": make_modifier(value=AutoHitStatus.AUTOHIT)
        }
        self.size_modifiers = {
            "size": make_modifier(value=Size.MEDIUM)
        }
        self.resistance_modifiers = {
            "res": make_modifier(
                value=ResistanceStatus.RESISTANCE,
                damage_type=DamageType.ACID,
                numerical_value=1,
            )
        }
        self.score = 5
        self.normalized_score = 5
        self.min = 0
        self.max = 10


class DummyContextualWrapper:
    def __init__(self, result):
        self.callable = lambda s, t, c: result


class DummyContextualValue:
    def __init__(self):
        self.is_outgoing_modifier = False
        self.source_entity_uuid = uuid4()
        self.target_entity_uuid = uuid4()
        self.context = {}
        self.value_modifiers = {
            "v": DummyContextualWrapper(make_modifier(value=2, normalized_value=2))
        }
        self.min_constraints = {
            "min": DummyContextualWrapper(make_modifier(value=1, normalized_value=1))
        }
        self.max_constraints = {
            "max": DummyContextualWrapper(make_modifier(value=9, normalized_value=9))
        }
        self.advantage_modifiers = {
            "adv": DummyContextualWrapper(
                make_modifier(value=AdvantageStatus.DISADVANTAGE, numerical_value=-1)
            )
        }
        self.critical_modifiers = {
            "crit": DummyContextualWrapper(make_modifier(value=CriticalStatus.NOCRIT))
        }
        self.auto_hit_modifiers = {
            "hit": DummyContextualWrapper(make_modifier(value=AutoHitStatus.AUTOMISS))
        }
        self.size_modifiers = {
            "size": DummyContextualWrapper(make_modifier(value=Size.SMALL))
        }
        self.resistance_modifiers = {
            "res": DummyContextualWrapper(
                make_modifier(
                    value=ResistanceStatus.IMMUNITY,
                    damage_type=DamageType.COLD,
                    numerical_value=0,
                )
            )
        }
        self.score = 3
        self.normalized_score = 3
        self.min = 1
        self.max = 9


def test_from_engine_static_transfers_modifiers_and_scores():
    static = DummyStaticValue()
    snapshot = ModifierChannelSnapshot.from_engine_static(static, "Channel")
    assert len(snapshot.value_modifiers) == len(static.value_modifiers)
    assert len(snapshot.min_constraints) == len(static.min_constraints)
    assert len(snapshot.max_constraints) == len(static.max_constraints)
    assert len(snapshot.advantage_modifiers) == len(static.advantage_modifiers)
    assert len(snapshot.critical_modifiers) == len(static.critical_modifiers)
    assert len(snapshot.auto_hit_modifiers) == len(static.auto_hit_modifiers)
    assert len(snapshot.size_modifiers) == len(static.size_modifiers)
    assert len(snapshot.resistance_modifiers) == len(static.resistance_modifiers)
    assert snapshot.score == static.score
    assert snapshot.normalized_score == static.normalized_score
    assert snapshot.min_value == static.min
    assert snapshot.max_value == static.max


def test_from_engine_contextual_transfers_modifiers_and_scores():
    ctx = DummyContextualValue()
    snapshot = ModifierChannelSnapshot.from_engine_contextual(ctx, "Channel")
    assert len(snapshot.value_modifiers) == len(ctx.value_modifiers)
    assert len(snapshot.min_constraints) == len(ctx.min_constraints)
    assert len(snapshot.max_constraints) == len(ctx.max_constraints)
    assert len(snapshot.advantage_modifiers) == len(ctx.advantage_modifiers)
    assert len(snapshot.critical_modifiers) == len(ctx.critical_modifiers)
    assert len(snapshot.auto_hit_modifiers) == len(ctx.auto_hit_modifiers)
    assert len(snapshot.size_modifiers) == len(ctx.size_modifiers)
    assert len(snapshot.resistance_modifiers) == len(ctx.resistance_modifiers)
    assert snapshot.score == ctx.score
    assert snapshot.normalized_score == ctx.normalized_score
    assert snapshot.min_value == ctx.min
    assert snapshot.max_value == ctx.max
