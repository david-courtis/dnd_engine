import random
from uuid import uuid4

import pytest

from dnd.core.values import BaseValue, StaticValue, ContextualValue, ModifiableValue, identity
from dnd.core.modifiers import (
    NumericalModifier,
    AdvantageModifier,
    CriticalModifier,
    AutoHitModifier,
    SizeModifier,
    DamageTypeModifier,
    ResistanceModifier,
    ContextualNumericalModifier,
    ContextualAdvantageModifier,
    ContextualCriticalModifier,
    ContextualAutoHitModifier,
    ContextualSizeModifier,
    ContextualDamageTypeModifier,
    ContextualResistanceModifier,
    AdvantageStatus,
    CriticalStatus,
    AutoHitStatus,
    Size,
    DamageType,
    ResistanceStatus,
)


def test_basevalue_registry_and_cycle():
    src = uuid4()
    a = StaticValue(source_entity_uuid=src)
    b = StaticValue(source_entity_uuid=src, generated_from=[a.uuid])
    a.generated_from.append(b.uuid)
    BaseValue._registry[a.uuid] = a
    BaseValue._registry[b.uuid] = b

    assert BaseValue.get(a.uuid) is a
    assert BaseValue.get(uuid4()) is None

    fake_uuid = uuid4()
    BaseValue._registry[fake_uuid] = object()
    with pytest.raises(ValueError):
        BaseValue.get(fake_uuid)
    BaseValue._registry.pop(fake_uuid, None)

    chain = a.get_generation_chain()
    assert [v.uuid for v in chain] == [b.uuid]
    assert identity(7) == 7


def test_staticvalue_validators_and_constraints():
    src = uuid4()

    bad_mod = NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=1)
    with pytest.raises(ValueError):
        StaticValue(
            source_entity_uuid=src,
            is_outgoing_modifier=True,
            value_modifiers={bad_mod.uuid: bad_mod},
        )

    cv = ContextualValue(source_entity_uuid=src)
    StaticValue._registry[cv.uuid] = cv
    with pytest.raises(ValueError):
        StaticValue.get(cv.uuid)
    StaticValue._registry.pop(cv.uuid, None)

    mod = NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=1)
    min_con = NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=5)
    max_con = NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=3)
    sv_min = StaticValue(source_entity_uuid=src)
    sv_min.add_value_modifier(mod)
    min_id = sv_min.add_min_constraint(min_con)
    assert sv_min.score == 5
    sv_min.remove_min_constraint(min_id)
    assert sv_min.min is None

    sv_max = StaticValue(source_entity_uuid=src)
    sv_max.add_value_modifier(mod)
    max_id = sv_max.add_max_constraint(max_con)
    assert sv_max.score == 1 if sv_max.max is None else 3
    sv_max.remove_max_constraint(max_id)
    assert sv_max.max is None

    both_min = NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=2)
    both_max = NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=4)
    sv_both = StaticValue(source_entity_uuid=src)
    sv_both.add_value_modifier(NumericalModifier(source_entity_uuid=src, target_entity_uuid=src, value=1))
    sv_both.add_min_constraint(both_min)
    sv_both.add_max_constraint(both_max)
    assert sv_both.score == 2

    adv = AdvantageModifier(source_entity_uuid=src, target_entity_uuid=src, value=AdvantageStatus.ADVANTAGE)
    crit = CriticalModifier(source_entity_uuid=src, target_entity_uuid=src, value=CriticalStatus.AUTOCRIT)
    dmg = DamageTypeModifier(source_entity_uuid=src, target_entity_uuid=src, value=DamageType.FIRE)
    res1 = ResistanceModifier(
        source_entity_uuid=src,
        target_entity_uuid=src,
        value=ResistanceStatus.RESISTANCE,
        damage_type=DamageType.COLD,
    )
    res2 = ResistanceModifier(
        source_entity_uuid=src,
        target_entity_uuid=src,
        value=ResistanceStatus.RESISTANCE,
        damage_type=DamageType.COLD,
    )
    sv = StaticValue(source_entity_uuid=src)
    sv.add_value_modifier(mod)
    adv_id = sv.add_advantage_modifier(adv)
    crit_id = sv.add_critical_modifier(crit)
    dmg_id = sv.add_damage_type_modifier(dmg)
    sv.add_resistance_modifier(res1)
    sv.add_resistance_modifier(res2)
    uuids = sv.get_all_modifier_uuids()
    assert set([mod.uuid, adv_id, crit_id, dmg_id]).issubset(set(uuids))
    assert sv.resistance[DamageType.COLD] == ResistanceStatus.IMMUNITY
    random.seed(0)
    assert sv.damage_type == DamageType.FIRE
    sv.remove_critical_modifier(crit_id)
    sv.remove_damage_type_modifier(dmg_id)
    sv.remove_all_modifiers()
    assert sv.get_all_modifier_uuids() == []


def test_contextualvalue_properties_and_errors():
    src = uuid4()
    cv = ContextualValue(source_entity_uuid=src)
    ContextualValue._registry[cv.uuid] = cv
    assert ContextualValue.get(cv.uuid) is cv
    fake_uuid = uuid4()
    BaseValue._registry[fake_uuid] = StaticValue(source_entity_uuid=src)
    with pytest.raises(ValueError):
        ContextualValue.get(fake_uuid)
    BaseValue._registry.pop(fake_uuid, None)

    def min_call(s, t, c):
        return NumericalModifier(source_entity_uuid=s, target_entity_uuid=s, value=2)

    def max_call(s, t, c):
        return NumericalModifier(source_entity_uuid=s, target_entity_uuid=s, value=4)

    min_id = cv.add_min_constraint(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=min_call))
    max_id = cv.add_max_constraint(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=max_call))

    def val_call(s, t, c):
        return NumericalModifier(source_entity_uuid=s, target_entity_uuid=s, value=1)

    def none_call(s, t, c):
        return None

    cv.add_value_modifier(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=val_call))
    cv.add_value_modifier(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=none_call))
    assert cv.score == 2
    cv.remove_min_constraint(min_id)
    cv.remove_max_constraint(max_id)

    bad_cv = ContextualValue(source_entity_uuid=src)
    bad_cv.add_value_modifier(
        ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=lambda s, t, c: 5)
    )
    with pytest.raises(ValueError):
        bad_cv.score

    err_cv = ContextualValue(source_entity_uuid=src)
    def raise_call(s, t, c):
        raise RuntimeError("boom")
    err_cv.add_value_modifier(
        ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=raise_call)
    )
    with pytest.raises(ValueError):
        err_cv.score

    adv_cv = ContextualValue(source_entity_uuid=src)
    def adv_call(s, t, c):
        return AdvantageModifier(source_entity_uuid=s, target_entity_uuid=s, value=AdvantageStatus.DISADVANTAGE)
    adv_cv.add_advantage_modifier(ContextualAdvantageModifier(source_entity_uuid=src, target_entity_uuid=src, callable=adv_call))
    assert adv_cv.advantage == AdvantageStatus.DISADVANTAGE

    def auto_crit_call(s, t, c):
        return CriticalModifier(source_entity_uuid=s, target_entity_uuid=s, value=CriticalStatus.AUTOCRIT)
    def no_crit_call(s, t, c):
        return CriticalModifier(source_entity_uuid=s, target_entity_uuid=s, value=CriticalStatus.NOCRIT)
    crit_cv = ContextualValue(source_entity_uuid=src)
    crit_cv.add_critical_modifier(ContextualCriticalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=no_crit_call))
    assert crit_cv.critical == CriticalStatus.NOCRIT
    crit_cv2 = ContextualValue(source_entity_uuid=src)
    crit_id = crit_cv2.add_critical_modifier(ContextualCriticalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=auto_crit_call))
    assert crit_cv2.critical == CriticalStatus.AUTOCRIT
    crit_cv2.remove_critical_modifier(crit_id)
    assert crit_cv2.critical == CriticalStatus.NONE

    hit_cv = ContextualValue(source_entity_uuid=src)
    def autohit_call(s, t, c):
        return AutoHitModifier(source_entity_uuid=s, target_entity_uuid=s, value=AutoHitStatus.AUTOHIT)
    hit_cv.add_auto_hit_modifier(ContextualAutoHitModifier(source_entity_uuid=src, target_entity_uuid=src, callable=autohit_call))
    assert hit_cv.auto_hit == AutoHitStatus.AUTOHIT

    size_cv = ContextualValue(source_entity_uuid=src, largest_size_priority=False)
    def size_big(s, t, c):
        return SizeModifier(source_entity_uuid=s, target_entity_uuid=s, value=Size.LARGE)
    def size_small(s, t, c):
        return SizeModifier(source_entity_uuid=s, target_entity_uuid=s, value=Size.SMALL)
    size_cv.add_size_modifier(ContextualSizeModifier(source_entity_uuid=src, target_entity_uuid=src, callable=size_big))
    size_cv.add_size_modifier(ContextualSizeModifier(source_entity_uuid=src, target_entity_uuid=src, callable=size_small))
    assert size_cv.size == Size.SMALL

    dmg_cv = ContextualValue(source_entity_uuid=src)
    def fire_call(s, t, c):
        return DamageTypeModifier(source_entity_uuid=s, target_entity_uuid=s, value=DamageType.FIRE)
    def cold_call(s, t, c):
        return DamageTypeModifier(source_entity_uuid=s, target_entity_uuid=s, value=DamageType.COLD)
    dmg_id1 = dmg_cv.add_damage_type_modifier(ContextualDamageTypeModifier(source_entity_uuid=src, target_entity_uuid=src, callable=fire_call))
    dmg_id2 = dmg_cv.add_damage_type_modifier(ContextualDamageTypeModifier(source_entity_uuid=src, target_entity_uuid=src, callable=cold_call))
    types = dmg_cv.damage_types
    assert set(types) == {DamageType.FIRE, DamageType.COLD}
    random.seed(0)
    assert dmg_cv.damage_type in types
    dmg_cv.remove_damage_type_modifier(dmg_id1)

    res_cv = ContextualValue(source_entity_uuid=src)
    def res1_call(s, t, c):
        return ResistanceModifier(source_entity_uuid=s, target_entity_uuid=s, value=ResistanceStatus.RESISTANCE, damage_type=DamageType.FIRE)
    def res2_call(s, t, c):
        return ResistanceModifier(source_entity_uuid=s, target_entity_uuid=s, value=ResistanceStatus.RESISTANCE, damage_type=DamageType.FIRE)
    def resv_call(s, t, c):
        return ResistanceModifier(source_entity_uuid=s, target_entity_uuid=s, value=ResistanceStatus.VULNERABILITY, damage_type=DamageType.COLD)
    res_cv.add_resistance_modifier(ContextualResistanceModifier(source_entity_uuid=src, target_entity_uuid=src, callable=res1_call))
    res_cv.add_resistance_modifier(ContextualResistanceModifier(source_entity_uuid=src, target_entity_uuid=src, callable=res2_call))
    res_cv.add_resistance_modifier(ContextualResistanceModifier(source_entity_uuid=src, target_entity_uuid=src, callable=resv_call))
    res = res_cv.resistance
    assert res[DamageType.FIRE] == ResistanceStatus.IMMUNITY
    assert res[DamageType.COLD] == ResistanceStatus.VULNERABILITY

    uuids_before = dmg_cv.get_all_modifier_uuids()
    assert len(uuids_before) == 1  # one remaining after removal
    dmg_cv.remove_all_modifiers()
    assert dmg_cv.get_all_modifier_uuids() == []

    cv_max_only = ContextualValue(source_entity_uuid=src)
    cv_max_only.add_value_modifier(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=val_call))
    cv_max_only.add_max_constraint(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=lambda s, t, c: NumericalModifier(source_entity_uuid=s, target_entity_uuid=s, value=0)))
    assert cv_max_only.score == 0

    cv_min_only = ContextualValue(source_entity_uuid=src)
    cv_min_only.add_value_modifier(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=val_call))
    cv_min_only.add_min_constraint(ContextualNumericalModifier(source_entity_uuid=src, target_entity_uuid=src, callable=lambda s, t, c: NumericalModifier(source_entity_uuid=s, target_entity_uuid=s, value=3)))
    assert cv_min_only.score == 3


def test_modifiablevalue_additional_behaviors():
    src = uuid4()
    tgt = uuid4()
    mv = ModifiableValue.create(source_entity_uuid=src, base_value=0)

    fake_uuid = uuid4()
    BaseValue._registry[fake_uuid] = StaticValue(source_entity_uuid=src)
    with pytest.raises(ValueError):
        ModifiableValue.get(fake_uuid)
    BaseValue._registry.pop(fake_uuid, None)

    with pytest.raises(ValueError):
        mv.set_target_entity("bad")

    mv.set_target_entity(tgt)
    cv_no_target = ContextualValue(source_entity_uuid=tgt)
    with pytest.raises(ValueError):
        mv.set_from_target_contextual(cv_no_target)

    from_static = StaticValue(source_entity_uuid=tgt, is_outgoing_modifier=True)
    from_static.add_size_modifier(SizeModifier(source_entity_uuid=tgt, target_entity_uuid=src, value=Size.LARGE))
    from_static.add_damage_type_modifier(
        DamageTypeModifier(source_entity_uuid=tgt, target_entity_uuid=src, value=DamageType.FIRE)
    )
    from_static.add_resistance_modifier(
        ResistanceModifier(
            source_entity_uuid=tgt,
            target_entity_uuid=src,
            value=ResistanceStatus.RESISTANCE,
            damage_type=DamageType.COLD,
        )
    )
    from_static.add_resistance_modifier(
        ResistanceModifier(
            source_entity_uuid=tgt,
            target_entity_uuid=src,
            value=ResistanceStatus.RESISTANCE,
            damage_type=DamageType.COLD,
        )
    )

    def ctx_size(s, t, c):
        return SizeModifier(source_entity_uuid=s, target_entity_uuid=t, value=Size.SMALL)
    def ctx_dmg(s, t, c):
        return DamageTypeModifier(source_entity_uuid=s, target_entity_uuid=t, value=DamageType.COLD)
    def ctx_res(s, t, c):
        return ResistanceModifier(source_entity_uuid=s, target_entity_uuid=t, value=ResistanceStatus.VULNERABILITY, damage_type=DamageType.FIRE)
    from_ctx = ContextualValue(source_entity_uuid=tgt, is_outgoing_modifier=True)
    from_ctx.add_size_modifier(ContextualSizeModifier(source_entity_uuid=tgt, target_entity_uuid=src, callable=ctx_size))
    from_ctx.add_damage_type_modifier(ContextualDamageTypeModifier(source_entity_uuid=tgt, target_entity_uuid=src, callable=ctx_dmg))
    from_ctx.add_resistance_modifier(ContextualResistanceModifier(source_entity_uuid=tgt, target_entity_uuid=src, callable=ctx_res))
    from_ctx.set_target_entity(src)

    mv.set_from_target_static(from_static)
    mv.set_from_target_contextual(from_ctx)
    mv.self_static.largest_size_priority = False
    assert mv.size == Size.SMALL
    assert set(mv.damage_types) == {DamageType.FIRE, DamageType.COLD}
    res = mv.resistance
    assert res[DamageType.COLD] == ResistanceStatus.IMMUNITY
    assert res[DamageType.FIRE] == ResistanceStatus.VULNERABILITY
    random.seed(0)
    assert mv.damage_type in {DamageType.FIRE, DamageType.COLD}

    uuids = mv.get_all_modifier_uuids()
    assert len(uuids) >= 3
    mv.remove_all_modifiers()
    assert mv.get_all_modifier_uuids() == []

    mv_pos = ModifiableValue.create(source_entity_uuid=src, base_value=0)
    mv_pos.to_target_static.add_advantage_modifier(
        AdvantageModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=AdvantageStatus.ADVANTAGE)
    )
    mv_pos.to_target_static.add_critical_modifier(
        CriticalModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=CriticalStatus.AUTOCRIT)
    )
    mv_pos.to_target_static.add_auto_hit_modifier(
        AutoHitModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=AutoHitStatus.AUTOHIT)
    )
    assert mv_pos.outgoing_advantage == AdvantageStatus.ADVANTAGE
    assert mv_pos.outgoing_critical == CriticalStatus.AUTOCRIT
    assert mv_pos.outgoing_auto_hit == AutoHitStatus.AUTOHIT

    mv_neg = ModifiableValue.create(source_entity_uuid=src, base_value=0)
    mv_neg.to_target_static.add_advantage_modifier(
        AdvantageModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=AdvantageStatus.DISADVANTAGE)
    )
    mv_neg.to_target_static.add_critical_modifier(
        CriticalModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=CriticalStatus.NOCRIT)
    )
    mv_neg.to_target_static.add_auto_hit_modifier(
        AutoHitModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=AutoHitStatus.AUTOMISS)
    )
    assert mv_neg.outgoing_advantage == AdvantageStatus.DISADVANTAGE
    assert mv_neg.outgoing_critical == CriticalStatus.NOCRIT
    assert mv_neg.outgoing_auto_hit == AutoHitStatus.AUTOMISS
