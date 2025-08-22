import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from uuid import uuid4

from dnd.core.values import ModifiableValue
from dnd.core.modifiers import (
    NumericalModifier,
    ContextualNumericalModifier,
    AdvantageModifier,
    CriticalModifier,
    ResistanceModifier,
    AdvantageStatus,
    CriticalStatus,
    ResistanceStatus,
    DamageType,
)


def _build_value():
    source_uuid = uuid4()
    mv = ModifiableValue.create(source_entity_uuid=source_uuid, base_value=10, value_name="test")

    # Static modifier
    static_mod = NumericalModifier(
        source_entity_uuid=source_uuid,
        target_entity_uuid=source_uuid,
        value=2,
    )
    mv.self_static.add_value_modifier(static_mod)

    # Contextual modifiers driven by context values
    def bonus(src, tgt, ctx):
        return NumericalModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=ctx.get("bonus", 0),
        )

    def penalty(src, tgt, ctx):
        return NumericalModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=ctx.get("penalty", 0),
        )

    mv.self_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=source_uuid,
            target_entity_uuid=source_uuid,
            callable=bonus,
        )
    )
    mv.self_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=source_uuid,
            target_entity_uuid=source_uuid,
            callable=penalty,
        )
    )

    mv.set_context({"bonus": 5, "penalty": -2})
    return mv


def test_modifiable_value_score_with_context():
    mv = _build_value()
    assert mv.score == 15
    assert mv.normalized_score == 15


def test_modifiable_value_to_from_dict_round_trip():
    mv = _build_value()
    mv.update_normalizers()
    data = mv.model_dump()
    rebuilt = ModifiableValue.model_validate(data)
    assert rebuilt.model_dump() == data
    assert rebuilt.score == mv.score


def test_modifiable_value_constraints_channels_and_normalization():
    src = uuid4()
    tgt = uuid4()

    mv = ModifiableValue.create(
        source_entity_uuid=src,
        base_value=10,
        value_name="constrained",
        score_normalizer=lambda v: v // 2,
    )

    # Add modifiers in different channels
    mv.self_static.add_value_modifier(
        NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=5)
    )
    mv.to_target_static.add_value_modifier(
        NumericalModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=3)
    )

    def ctx_bonus(s, t, c):
        return NumericalModifier(
            source_entity_uuid=s,
            target_entity_uuid=t,
            value=c.get("bonus", 0),
            score_normalizer=getattr(ctx_bonus, "score_normalizer", None),
        )

    def out_ctx(s, t, c):
        return NumericalModifier(
            source_entity_uuid=s,
            target_entity_uuid=t,
            value=1,
            score_normalizer=getattr(out_ctx, "score_normalizer", None),
        )

    mv.self_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=src, target_entity_uuid=src, callable=ctx_bonus
        )
    )
    mv.to_target_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=src, target_entity_uuid=tgt, callable=out_ctx
        )
    )

    # Apply min/max constraints
    mv.self_static.add_min_constraint(
        NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=5)
    )
    mv.self_static.add_max_constraint(
        NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=18)
    )

    mv.set_context({"bonus": 8})
    mv.update_normalizers()

    assert mv.min == 5
    assert mv.max == 18
    assert mv.score == 18  # base(10)+static(5)+ctx(8)=23 -> max 18
    assert mv.normalized_score == 11  # (10->5)+(5->2)+(8->4)

    # Outgoing channels don't affect score
    assert mv.to_target_static.score == 3
    assert mv.to_target_contextual.score == 1


def test_modifiable_value_statuses_context_and_reset():
    src = uuid4()
    tgt = uuid4()

    mv = ModifiableValue.create(
        source_entity_uuid=src,
        base_value=0,
        value_name="status",
        score_normalizer=lambda v: v * 2,
    )
    mv.set_target_entity(tgt)

    # Advantage, critical and resistances
    mv.self_static.add_advantage_modifier(
        AdvantageModifier(
            source_entity_uuid=src, target_entity_uuid=src, value=AdvantageStatus.ADVANTAGE
        )
    )
    mv.self_static.add_critical_modifier(
        CriticalModifier(
            source_entity_uuid=src, target_entity_uuid=src, value=CriticalStatus.AUTOCRIT
        )
    )
    mv.self_static.add_resistance_modifier(
        ResistanceModifier(
            source_entity_uuid=src,
            target_entity_uuid=src,
            value=ResistanceStatus.RESISTANCE,
            damage_type=DamageType.FIRE,
        )
    )
    mv.self_static.add_resistance_modifier(
        ResistanceModifier(
            source_entity_uuid=src,
            target_entity_uuid=src,
            value=ResistanceStatus.VULNERABILITY,
            damage_type=DamageType.COLD,
        )
    )

    add_uuid = mv.self_static.add_value_modifier(
        NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=4)
    )

    mv.update_normalizers()

    assert mv.score == 4
    assert mv.normalized_score == 8

    # Remove modifier (subtraction)
    mv.self_static.remove_value_modifier(add_uuid)
    assert mv.score == 0

    # Context-aware modifier
    def ctx_mod(src_uuid, tgt_uuid, ctx):
        return NumericalModifier(
            source_entity_uuid=src_uuid,
            target_entity_uuid=tgt_uuid,
            value=ctx.get("bonus", 0),
            score_normalizer=getattr(ctx_mod, "score_normalizer", None),
        )

    mv.self_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=src, target_entity_uuid=src, callable=ctx_mod
        )
    )

    mv.update_normalizers()

    mv.set_context({"bonus": 1})
    assert mv.score == 1
    mv.set_context({"bonus": 3})
    assert mv.score == 3
    assert mv.normalized_score == 6

    # Apply modifiers from a target then reset
    target_mv = ModifiableValue.create(source_entity_uuid=tgt, base_value=0, value_name="t")
    target_mv.set_target_entity(src)
    target_mv.to_target_static.add_value_modifier(
        NumericalModifier(source_entity_uuid=tgt, target_entity_uuid=src, value=2)
    )
    def tgt_ctx(s, t, c):
        return NumericalModifier(
            source_entity_uuid=s,
            target_entity_uuid=t,
            value=c.get("debuff", 0),
            score_normalizer=getattr(tgt_ctx, "score_normalizer", None),
        )

    target_mv.to_target_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=tgt, target_entity_uuid=src, callable=tgt_ctx
        )
    )
    target_mv.set_context({"debuff": 1})
    target_mv.update_normalizers()

    mv.set_from_target(target_mv)
    assert mv.score == 3 + 2 + 1
    mv.reset_from_target()
    assert mv.score == 3

    assert mv.advantage == AdvantageStatus.ADVANTAGE
    assert mv.critical == CriticalStatus.AUTOCRIT
    resistance = mv.resistance
    assert resistance[DamageType.FIRE] == ResistanceStatus.RESISTANCE
    assert resistance[DamageType.COLD] == ResistanceStatus.VULNERABILITY