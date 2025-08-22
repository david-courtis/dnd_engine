from uuid import uuid4
import pytest

from dnd.core.values import StaticValue, ContextualValue
from dnd.core.modifiers import (
    BaseObject,
    NumericalModifier,
    AdvantageModifier,
    CriticalModifier,
    AutoHitModifier,
    ResistanceModifier,
    SizeModifier,
    DamageTypeModifier,
    AdvantageStatus,
    CriticalStatus,
    AutoHitStatus,
    ResistanceStatus,
    DamageType,
    Size,
    ContextualModifier,
    ContextualNumericalModifier,
    ContextualAdvantageModifier,
    ContextualCriticalModifier,
    ContextualAutoHitModifier,
    ContextualSizeModifier,
    ContextualDamageTypeModifier,
    ContextualResistanceModifier,
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


def test_base_object_registry_and_validation():
    BaseObject._registry.clear()
    source = uuid4()
    target = uuid4()
    obj = BaseObject(source_entity_uuid=source, target_entity_uuid=target)

    assert BaseObject.get(obj.uuid) is obj

    BaseObject.unregister(obj.uuid)
    assert BaseObject.get(obj.uuid) is None

    BaseObject.register(obj)
    assert BaseObject.get(obj.uuid) is obj

    obj.validate_source_id(source)
    with pytest.raises(ValueError):
        obj.validate_source_id(uuid4())

    obj.validate_target_id(target)
    with pytest.raises(ValueError):
        obj.validate_target_id(uuid4())


def test_target_context_helpers():
    source = uuid4()
    target = uuid4()
    obj = BaseObject(source_entity_uuid=source, target_entity_uuid=target)

    new_source = uuid4()
    obj.set_source_entity(new_source, "Alice")
    assert obj.source_entity_uuid == new_source
    assert obj.source_entity_name == "Alice"

    new_target = uuid4()
    obj.set_target_entity(new_target, "Bob")
    assert obj.target_entity_uuid == new_target
    assert obj.target_entity_name == "Bob"

    obj.clear_target_entity()
    assert obj.target_entity_uuid is None
    assert obj.target_entity_name is None

    ctx = {"foo": 1}
    obj.set_context(ctx)
    assert obj.context == ctx

    obj.clear_context()
    assert obj.context is None


def test_contextual_modifiers_context_add_remove():
    source = uuid4()
    target = uuid4()
    value = ContextualValue(
        source_entity_uuid=source,
        target_entity_uuid=target,
        context={"bonus": True, "adv": True},
    )

    def bonus_func(src, tgt, context):
        if context.get("bonus"):
            return NumericalModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=5)
        return None

    def advantage_func(src, tgt, context):
        if context.get("adv"):
            return AdvantageModifier(
                source_entity_uuid=src,
                target_entity_uuid=tgt,
                value=AdvantageStatus.ADVANTAGE,
            )
        return None

    cnum = ContextualNumericalModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=bonus_func
    )
    cadv = ContextualAdvantageModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=advantage_func
    )

    value.add_value_modifier(cnum)
    value.add_advantage_modifier(cadv)

    assert value.score == 5
    assert value.advantage == AdvantageStatus.ADVANTAGE

    value.set_context({"bonus": False, "adv": False})
    assert value.score == 0
    assert value.advantage == AdvantageStatus.NONE

    value.remove_value_modifier(cnum.uuid)
    value.remove_advantage_modifier(cadv.uuid)

    assert value.score == 0
    assert value.advantage == AdvantageStatus.NONE


def test_contextual_modifier_execute_callable_and_validation():
    source = uuid4()
    target = uuid4()

    def num_callable(src, tgt, context):
        return NumericalModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=3)

    cmod = ContextualNumericalModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=num_callable
    )

    with pytest.raises(ValueError):
        cmod.execute_callable()

    with pytest.raises(ValueError):
        cmod.setup_callable_arguments(uuid4())

    cmod.setup_callable_arguments(target, target)
    result = cmod.execute_callable()
    assert isinstance(result, NumericalModifier)
    assert result.value == 3

    def bad_callable(src, tgt, context):
        return AdvantageModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=AdvantageStatus.ADVANTAGE,
        )

    bad_mod = ContextualNumericalModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=bad_callable
    )
    bad_mod.setup_callable_arguments(target, target)
    with pytest.raises(ValueError):
        bad_mod.execute_callable()

    def adv_callable(src, tgt, context):
        return AdvantageModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=AdvantageStatus.ADVANTAGE,
        )

    cadv = ContextualAdvantageModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=adv_callable
    )
    cadv.setup_callable_arguments(target, target)
    assert isinstance(cadv.execute_callable(), AdvantageModifier)

    def crit_callable(src, tgt, context):
        return CriticalModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=CriticalStatus.AUTOCRIT,
        )

    ccrit = ContextualCriticalModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=crit_callable
    )
    ccrit.setup_callable_arguments(target, target)
    assert isinstance(ccrit.execute_callable(), CriticalModifier)

    def auto_callable(src, tgt, context):
        return AutoHitModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=AutoHitStatus.AUTOHIT,
        )

    cauto = ContextualAutoHitModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=auto_callable
    )
    cauto.setup_callable_arguments(target, target)
    assert isinstance(cauto.execute_callable(), AutoHitModifier)

    def size_callable(src, tgt, context):
        return SizeModifier(source_entity_uuid=src, target_entity_uuid=tgt, value=Size.HUGE)

    csize = ContextualSizeModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=size_callable
    )
    csize.setup_callable_arguments(target, target)
    assert isinstance(csize.execute_callable(), SizeModifier)

    def dtype_callable(src, tgt, context):
        return DamageTypeModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=DamageType.COLD,
        )

    cdtype = ContextualDamageTypeModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=dtype_callable
    )
    cdtype.setup_callable_arguments(target, target)
    assert isinstance(cdtype.execute_callable(), DamageTypeModifier)

    def res_callable(src, tgt, context):
        return ResistanceModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=ResistanceStatus.RESISTANCE,
            damage_type=DamageType.FIRE,
        )

    cres = ContextualResistanceModifier(
        source_entity_uuid=source, target_entity_uuid=target, callable=res_callable
    )
    cres.setup_callable_arguments(target, target)
    with pytest.raises(ValueError):
        cres.execute_callable()

    class WeirdContextual(ContextualModifier):
        pass

    weird = WeirdContextual(
        source_entity_uuid=source, target_entity_uuid=target, callable=num_callable
    )
    weird.setup_callable_arguments(target, target)
    with pytest.raises(ValueError):
        weird.execute_callable()


def test_numerical_modifier_normalized_value_and_create():
    source = uuid4()
    target = uuid4()
    mod = NumericalModifier(source_entity_uuid=source, target_entity_uuid=target, value=5)
    assert mod.normalized_value == 5
    mod2 = NumericalModifier(
        source_entity_uuid=source,
        target_entity_uuid=target,
        value=5,
        score_normalizer=lambda x: x // 2,
    )
    assert mod2.normalized_value == 2
    created = NumericalModifier.create(
        source_entity_uuid=source, target_entity_uuid=target, value=7
    )
    assert isinstance(created, NumericalModifier)
    assert created.value == 7


def test_advantage_modifier_numerical_value():
    source = uuid4()
    target = uuid4()
    mod = AdvantageModifier(
        source_entity_uuid=source,
        target_entity_uuid=target,
        value=AdvantageStatus.ADVANTAGE,
    )
    assert mod.numerical_value == 1
    mod.value = AdvantageStatus.DISADVANTAGE
    assert mod.numerical_value == -1
    mod.value = AdvantageStatus.NONE
    assert mod.numerical_value == 0


def test_resistance_modifier_numerical_value():
    source = uuid4()
    target = uuid4()
    mod = ResistanceModifier(
        source_entity_uuid=source,
        target_entity_uuid=target,
        value=ResistanceStatus.IMMUNITY,
        damage_type=DamageType.FIRE,
    )
    assert mod.numerical_value == 2
    mod.value = ResistanceStatus.RESISTANCE
    assert mod.numerical_value == 1
    mod.value = ResistanceStatus.VULNERABILITY
    assert mod.numerical_value == -1
    mod.value = ResistanceStatus.NONE
    assert mod.numerical_value == 0


def test_base_object_get_invalid_type():
    BaseObject._registry.clear()
    source = uuid4()
    target = uuid4()

    class OtherObject(BaseObject):
        pass

    base = BaseObject(source_entity_uuid=source, target_entity_uuid=target)
    other = OtherObject(source_entity_uuid=source, target_entity_uuid=target)
    assert OtherObject.get(other.uuid) is other
    with pytest.raises(ValueError):
        OtherObject.get(base.uuid)


@pytest.mark.parametrize(
    "cls, extra",
    [
        (NumericalModifier, {"value": 1}),
        (AdvantageModifier, {"value": AdvantageStatus.ADVANTAGE}),
        (CriticalModifier, {"value": CriticalStatus.AUTOCRIT}),
        (AutoHitModifier, {"value": AutoHitStatus.AUTOHIT}),
        (
            ContextualModifier,
            {"callable": lambda s, t, c: NumericalModifier(source_entity_uuid=s, target_entity_uuid=t, value=1)},
        ),
        (
            ContextualAdvantageModifier,
            {
                "callable": lambda s, t, c: AdvantageModifier(
                    source_entity_uuid=s, target_entity_uuid=t, value=AdvantageStatus.ADVANTAGE
                )
            },
        ),
        (
            ContextualCriticalModifier,
            {
                "callable": lambda s, t, c: CriticalModifier(
                    source_entity_uuid=s, target_entity_uuid=t, value=CriticalStatus.AUTOCRIT
                )
            },
        ),
        (
            ContextualAutoHitModifier,
            {
                "callable": lambda s, t, c: AutoHitModifier(
                    source_entity_uuid=s, target_entity_uuid=t, value=AutoHitStatus.AUTOHIT
                )
            },
        ),
        (
            ContextualNumericalModifier,
            {"callable": lambda s, t, c: NumericalModifier(source_entity_uuid=s, target_entity_uuid=t, value=1)},
        ),
        (SizeModifier, {"value": Size.SMALL}),
        (DamageTypeModifier, {"value": DamageType.COLD}),
        (
            ContextualSizeModifier,
            {"callable": lambda s, t, c: SizeModifier(source_entity_uuid=s, target_entity_uuid=t, value=Size.SMALL)},
        ),
        (
            ContextualDamageTypeModifier,
            {
                "callable": lambda s, t, c: DamageTypeModifier(
                    source_entity_uuid=s, target_entity_uuid=t, value=DamageType.COLD
                )
            },
        ),
        (
            ResistanceModifier,
            {"value": ResistanceStatus.RESISTANCE, "damage_type": DamageType.FIRE},
        ),
        (
            ContextualResistanceModifier,
            {
                "callable": lambda s, t, c: ResistanceModifier(
                    source_entity_uuid=s,
                    target_entity_uuid=t,
                    value=ResistanceStatus.RESISTANCE,
                    damage_type=DamageType.FIRE,
                )
            },
        ),
    ],
)
def test_modifier_get_methods(cls, extra):
    BaseObject._registry.clear()
    source = uuid4()
    target = uuid4()
    base = BaseObject(source_entity_uuid=source, target_entity_uuid=target)
    kwargs = {"source_entity_uuid": source, "target_entity_uuid": target}
    kwargs.update(extra)
    obj = cls(**kwargs)
    assert cls.get(obj.uuid) is obj
    with pytest.raises(ValueError):
        cls.get(base.uuid)
    assert cls.get(uuid4()) is None
