from uuid import uuid4

from dnd.core.values import StaticValue, ContextualValue
from dnd.core.modifiers import (
    NumericalModifier,
    AdvantageModifier,
    ResistanceModifier,
    SizeModifier,
    AdvantageStatus,
    ResistanceStatus,
    DamageType,
    Size,
    ContextualNumericalModifier,
    ContextualAdvantageModifier,
    ContextualResistanceModifier,
    ContextualSizeModifier,
)


def test_numerical_modifier_add_remove():
    source = uuid4()
    value = StaticValue(source_entity_uuid=source, target_entity_uuid=source)

    mod1 = NumericalModifier(source_entity_uuid=source, target_entity_uuid=source, value=5)
    mod2 = NumericalModifier(source_entity_uuid=source, target_entity_uuid=source, value=3)

    id1 = value.add_value_modifier(mod1)
    id2 = value.add_value_modifier(mod2)
    assert value.score == 8

    value.remove_value_modifier(id1)
    assert value.score == 3

    value.remove_value_modifier(id2)
    assert value.score == 0


def test_advantage_modifier_stack_and_removal():
    source = uuid4()
    value = StaticValue(source_entity_uuid=source, target_entity_uuid=source)

    adv = AdvantageModifier(source_entity_uuid=source, target_entity_uuid=source, value=AdvantageStatus.ADVANTAGE)
    dis = AdvantageModifier(source_entity_uuid=source, target_entity_uuid=source, value=AdvantageStatus.DISADVANTAGE)

    value.add_advantage_modifier(adv)
    assert value.advantage == AdvantageStatus.ADVANTAGE

    value.add_advantage_modifier(dis)
    assert value.advantage == AdvantageStatus.NONE

    value.remove_advantage_modifier(adv.uuid)
    assert value.advantage == AdvantageStatus.DISADVANTAGE

    value.remove_advantage_modifier(dis.uuid)
    assert value.advantage == AdvantageStatus.NONE


def test_resistance_modifier_stack_limits():
    source = uuid4()
    value = StaticValue(source_entity_uuid=source, target_entity_uuid=source)

    res = ResistanceModifier(
        source_entity_uuid=source,
        target_entity_uuid=source,
        value=ResistanceStatus.RESISTANCE,
        damage_type=DamageType.FIRE,
    )
    vul = ResistanceModifier(
        source_entity_uuid=source,
        target_entity_uuid=source,
        value=ResistanceStatus.VULNERABILITY,
        damage_type=DamageType.FIRE,
    )

    value.add_resistance_modifier(res)
    assert value.resistance[DamageType.FIRE] == ResistanceStatus.RESISTANCE

    value.add_resistance_modifier(vul)
    assert value.resistance[DamageType.FIRE] == ResistanceStatus.NONE

    value.add_resistance_modifier(
        ResistanceModifier(
            source_entity_uuid=source,
            target_entity_uuid=source,
            value=ResistanceStatus.VULNERABILITY,
            damage_type=DamageType.FIRE,
        )
    )
    assert value.resistance[DamageType.FIRE] == ResistanceStatus.VULNERABILITY

    value.remove_resistance_modifier(res.uuid)
    assert value.resistance[DamageType.FIRE] == ResistanceStatus.VULNERABILITY

    value.remove_resistance_modifier(vul.uuid)
    assert value.resistance[DamageType.FIRE] == ResistanceStatus.VULNERABILITY


def test_size_modifier_priority_and_removal():
    source = uuid4()
    value = StaticValue(source_entity_uuid=source, target_entity_uuid=source)

    small = SizeModifier(source_entity_uuid=source, target_entity_uuid=source, value=Size.SMALL)
    large = SizeModifier(source_entity_uuid=source, target_entity_uuid=source, value=Size.LARGE)

    value.add_size_modifier(small)
    assert value.size == Size.SMALL

    value.add_size_modifier(large)
    assert value.size == Size.LARGE

    value.largest_size_priority = False
    assert value.size == Size.SMALL

    value.remove_size_modifier(small.uuid)
    assert value.size == Size.LARGE


def test_contextual_modifiers_callable_execution():
    source = uuid4()
    target = uuid4()
    value = ContextualValue(source_entity_uuid=source, target_entity_uuid=target)

    def num_func(src, tgt, context):
        return NumericalModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=7)

    def adv_func(src, tgt, context):
        return AdvantageModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=AdvantageStatus.ADVANTAGE)

    def res_func(src, tgt, context):
        return ResistanceModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=ResistanceStatus.RESISTANCE,
            damage_type=DamageType.COLD,
        )

    def size_func(src, tgt, context):
        return SizeModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=Size.HUGE)

    cnum = ContextualNumericalModifier(source_entity_uuid=source, target_entity_uuid=target, callable=num_func)
    cadv = ContextualAdvantageModifier(source_entity_uuid=source, target_entity_uuid=target, callable=adv_func)
    cres = ContextualResistanceModifier(source_entity_uuid=source, target_entity_uuid=target, callable=res_func)
    csize = ContextualSizeModifier(source_entity_uuid=source, target_entity_uuid=target, callable=size_func)

    value.add_value_modifier(cnum)
    value.add_advantage_modifier(cadv)
    value.add_resistance_modifier(cres)
    value.add_size_modifier(csize)

    assert value.score == 7
    assert value.advantage == AdvantageStatus.ADVANTAGE
    assert value.resistance[DamageType.COLD] == ResistanceStatus.RESISTANCE
    assert value.size == Size.HUGE

    value.remove_value_modifier(cnum.uuid)
    value.remove_advantage_modifier(cadv.uuid)
    value.remove_resistance_modifier(cres.uuid)
    value.remove_size_modifier(csize.uuid)

    assert value.score == 0
    assert value.advantage == AdvantageStatus.NONE
    assert value.resistance[DamageType.COLD] == ResistanceStatus.NONE
    assert value.size == Size.MEDIUM
