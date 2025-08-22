import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
from uuid import uuid4

from dnd.core.values import ModifiableValue
from dnd.core.modifiers import (
    NumericalModifier,
    ContextualNumericalModifier,
    AdvantageModifier,
    CriticalModifier,
    AutoHitModifier,
    SizeModifier,
    DamageTypeModifier,
    ResistanceModifier,
    AdvantageStatus,
    CriticalStatus,
    AutoHitStatus,
    Size,
    DamageType,
    ResistanceStatus,
)


def test_validate_modifier_target_set_from_target_and_generation_chain():
    src_a = uuid4()
    src_b = uuid4()
    mv_a = ModifiableValue.create(source_entity_uuid=src_a, base_value=0, value_name="A")
    mv_b = ModifiableValue.create(source_entity_uuid=src_b, base_value=0, value_name="B")
    mv_a.set_target_entity(src_b)
    mv_b.set_target_entity(src_a)

    bad_self = NumericalModifier(source_entity_uuid=src_a, target_entity_uuid=uuid4(), value=1)
    with pytest.raises(ValueError):
        mv_a.self_static.validate_modifier_target(bad_self)
    good_self = NumericalModifier(source_entity_uuid=src_a, target_entity_uuid=src_a, value=1)
    mv_a.self_static.validate_modifier_target(good_self)

    bad_out = NumericalModifier(source_entity_uuid=src_a, target_entity_uuid=uuid4(), value=1)
    with pytest.raises(ValueError):
        mv_a.to_target_static.validate_modifier_target(bad_out)
    good_out = NumericalModifier(source_entity_uuid=src_a, target_entity_uuid=src_b, value=1)
    mv_a.to_target_static.validate_modifier_target(good_out)

    mv_b.to_target_static.add_value_modifier(
        NumericalModifier(source_entity_uuid=src_b, target_entity_uuid=src_a, value=2)
    )

    def debuff(src, tgt, ctx):
        return NumericalModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=ctx.get("debuff", 0),
        )

    mv_b.to_target_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=src_b, target_entity_uuid=src_a, callable=debuff
        )
    )
    mv_b.set_context({"debuff": 3})

    mv_a.set_from_target(mv_b)
    assert mv_a.from_target_static.score == 2
    assert mv_a.from_target_contextual.score == 3
    assert mv_a.score == 5
    mv_a.reset_from_target()
    assert mv_a.from_target_static is None and mv_a.from_target_contextual is None
    assert mv_a.score == 0

    base = uuid4()
    v1 = ModifiableValue.create(source_entity_uuid=base, base_value=1, value_name="v1")
    v2 = ModifiableValue.create(source_entity_uuid=base, base_value=2, value_name="v2")
    v3 = ModifiableValue.create(source_entity_uuid=base, base_value=3, value_name="v3")
    combo1 = v1.combine_values([v2])
    combo2 = combo1.combine_values([v3])
    chain = combo2.get_generation_chain()
    assert [v.uuid for v in chain] == [combo1.uuid, v1.uuid, v2.uuid, v3.uuid]
    assert combo2.score == 6


def test_add_remove_modifiers_self_and_target():
    src = uuid4()
    tgt = uuid4()
    mv = ModifiableValue.create(
        source_entity_uuid=src, base_value=0, value_name="mods", target_entity_uuid=tgt
    )

    adv = AdvantageModifier(source_entity_uuid=src, target_entity_uuid=src, value=AdvantageStatus.ADVANTAGE)
    adv_id = mv.self_static.add_advantage_modifier(adv)
    assert mv.advantage == AdvantageStatus.ADVANTAGE
    mv.self_static.remove_advantage_modifier(adv_id)
    assert mv.advantage == AdvantageStatus.NONE
    adv_tgt = AdvantageModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=AdvantageStatus.DISADVANTAGE)
    adv_tgt_id = mv.to_target_static.add_advantage_modifier(adv_tgt)
    assert mv.to_target_static.advantage == AdvantageStatus.DISADVANTAGE
    mv.to_target_static.remove_advantage_modifier(adv_tgt_id)
    assert mv.to_target_static.advantage == AdvantageStatus.NONE

    crit = CriticalModifier(source_entity_uuid=src, target_entity_uuid=src, value=CriticalStatus.AUTOCRIT)
    crit_id = mv.self_static.add_critical_modifier(crit)
    assert mv.critical == CriticalStatus.AUTOCRIT
    mv.self_static.remove_critical_modifier(crit_id)
    assert mv.critical == CriticalStatus.NONE
    crit_tgt = CriticalModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=CriticalStatus.NOCRIT)
    crit_tgt_id = mv.to_target_static.add_critical_modifier(crit_tgt)
    assert mv.to_target_static.critical == CriticalStatus.NOCRIT
    mv.to_target_static.remove_critical_modifier(crit_tgt_id)
    assert mv.to_target_static.critical == CriticalStatus.NONE

    autohit = AutoHitModifier(source_entity_uuid=src, target_entity_uuid=src, value=AutoHitStatus.AUTOHIT)
    autohit_id = mv.self_static.add_auto_hit_modifier(autohit)
    assert mv.auto_hit == AutoHitStatus.AUTOHIT
    mv.self_static.remove_auto_hit_modifier(autohit_id)
    assert mv.auto_hit == AutoHitStatus.NONE
    autohit_tgt = AutoHitModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=AutoHitStatus.AUTOMISS)
    autohit_tgt_id = mv.to_target_static.add_auto_hit_modifier(autohit_tgt)
    assert mv.to_target_static.auto_hit == AutoHitStatus.AUTOMISS
    mv.to_target_static.remove_auto_hit_modifier(autohit_tgt_id)
    assert mv.to_target_static.auto_hit == AutoHitStatus.NONE

    size = SizeModifier(source_entity_uuid=src, target_entity_uuid=src, value=Size.LARGE)
    size_id = mv.self_static.add_size_modifier(size)
    assert mv.size == Size.LARGE
    mv.self_static.remove_size_modifier(size_id)
    assert mv.size == Size.MEDIUM
    size_tgt = SizeModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=Size.SMALL)
    size_tgt_id = mv.to_target_static.add_size_modifier(size_tgt)
    assert mv.to_target_static.size == Size.SMALL
    mv.to_target_static.remove_size_modifier(size_tgt_id)
    assert mv.to_target_static.size == Size.MEDIUM

    dmg = DamageTypeModifier(source_entity_uuid=src, target_entity_uuid=src, value=DamageType.FIRE)
    dmg_id = mv.self_static.add_damage_type_modifier(dmg)
    assert DamageType.FIRE in mv.damage_types
    mv.self_static.remove_damage_type_modifier(dmg_id)
    assert DamageType.FIRE not in mv.damage_types
    dmg_tgt = DamageTypeModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=DamageType.COLD)
    dmg_tgt_id = mv.to_target_static.add_damage_type_modifier(dmg_tgt)
    assert DamageType.COLD in mv.to_target_static.damage_types
    mv.to_target_static.remove_damage_type_modifier(dmg_tgt_id)
    assert DamageType.COLD not in mv.to_target_static.damage_types

    res = ResistanceModifier(
        source_entity_uuid=src,
        target_entity_uuid=src,
        value=ResistanceStatus.RESISTANCE,
        damage_type=DamageType.FIRE,
    )
    res_id = mv.self_static.add_resistance_modifier(res)
    assert mv.resistance[DamageType.FIRE] == ResistanceStatus.RESISTANCE
    mv.self_static.remove_resistance_modifier(res_id)
    assert mv.resistance[DamageType.FIRE] == ResistanceStatus.NONE
    res_tgt = ResistanceModifier(
        source_entity_uuid=src,
        target_entity_uuid=tgt,
        value=ResistanceStatus.VULNERABILITY,
        damage_type=DamageType.COLD,
    )
    res_tgt_id = mv.to_target_static.add_resistance_modifier(res_tgt)
    assert mv.to_target_static.resistance[DamageType.COLD] == ResistanceStatus.VULNERABILITY
    mv.to_target_static.remove_resistance_modifier(res_tgt_id)
    assert mv.to_target_static.resistance[DamageType.COLD] == ResistanceStatus.NONE


def test_context_and_global_normalizer_toggle():
    src = uuid4()
    mv = ModifiableValue.create(
        source_entity_uuid=src,
        base_value=10,
        value_name="ctx",
        score_normalizer=lambda v: v * 2,
        global_normalizer=False,
    )

    mv.self_static.add_value_modifier(
        NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=5)
    )

    def bonus(src_uuid, tgt_uuid, ctx):
        ctx = ctx or {}
        return NumericalModifier(
            source_entity_uuid=src_uuid,
            target_entity_uuid=tgt_uuid,
            value=ctx.get("bonus", 0),
            score_normalizer=getattr(bonus, "score_normalizer", None),
        )

    mv.self_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=src, target_entity_uuid=src, callable=bonus
        )
    )

    mv.set_context({"bonus": 3})
    # With global_normalizer False only the base modifier is normalized
    assert mv.score == 18
    assert mv.normalized_score == 28

    mv.global_normalizer = True
    mv.update_normalizers()
    mv.set_context({"bonus": 3})
    assert mv.normalized_score == 36

    mv.clear_context()
    assert mv.score == 15
    assert mv.normalized_score == 30
