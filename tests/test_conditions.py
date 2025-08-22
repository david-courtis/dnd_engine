from uuid import uuid4

import pytest
from dnd.entity import Entity
from dnd.conditions import (
    Blinded,
    Charmed,
    Dashing,
    Poisoned,
    Deafened,
    Dodging,
    Frightened,
    Grappled,
    Invisible,
    Incapacitated,
    Paralyzed,
    Prone,
    Restrained,
    Stunned,
    Unconscious,
    ConditionType,
    create_condition,
)
from dnd.core.values import AdvantageStatus, AutoHitStatus
from dnd.core.base_conditions import DurationType
from dnd.blocks.sensory import SensesType


def make_entities():
    e1 = Entity.create(source_entity_uuid=uuid4())
    e2 = Entity.create(source_entity_uuid=uuid4())
    e1.set_values_and_blocks_source()
    e2.set_values_and_blocks_source()
    return e1, e2


def test_blinded_applies_and_removes_modifiers():
    source, target = make_entities()
    condition = Blinded(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    event = condition.apply()
    assert event and not event.canceled
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    skill = target.skill_set.get_skill("perception")
    assert skill.skill_bonus.auto_hit == AutoHitStatus.AUTOMISS
    condition.remove_condition_modifiers()
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.NONE
    assert skill.skill_bonus.auto_hit == AutoHitStatus.NONE


def test_dashing_increases_movement_and_resets():
    source, target = make_entities()
    base_speed = target.action_economy.movement.normalized_score
    condition = Dashing(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.action_economy.movement.normalized_score == base_speed * 2
    condition.remove_condition_modifiers()
    assert target.action_economy.movement.normalized_score == base_speed


def test_charmed_modifiers_attack_and_skills():
    charmer, charmed = make_entities()
    condition = Charmed(source_entity_uuid=charmer.uuid, target_entity_uuid=charmed.uuid)
    condition.apply()
    atk_bonus = charmed.attack_bonus(target_entity_uuid=charmer.uuid)
    assert atk_bonus.auto_hit == AutoHitStatus.AUTOMISS
    skill_bonus = charmer.skill_bonus(charmed.uuid, "persuasion")
    assert skill_bonus.advantage == AdvantageStatus.ADVANTAGE
    condition.remove_condition_modifiers()
    atk_bonus = charmed.attack_bonus(target_entity_uuid=charmer.uuid)
    assert atk_bonus.auto_hit == AutoHitStatus.NONE
    skill_bonus = charmer.skill_bonus(charmed.uuid, "persuasion")
    assert skill_bonus.advantage == AdvantageStatus.NONE


def test_dashing_condition_does_not_stack():
    source, target = make_entities()
    base_speed = target.action_economy.movement.normalized_score
    first = Dashing(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    target.add_condition(first)
    assert target.action_economy.movement.normalized_score == base_speed * 2
    second = Dashing(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    target.add_condition(second)
    assert target.action_economy.movement.normalized_score == base_speed * 2
    assert target.active_conditions["Dashing"].uuid == second.uuid


def test_poisoned_condition_duration_counts_down_and_expires():
    source, target = make_entities()
    condition = Poisoned(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.duration.duration_type = DurationType.ROUNDS
    condition.duration.duration = 2
    target.add_condition(condition)
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    acrobatics = target.skill_set.get_skill("acrobatics")
    assert acrobatics.skill_bonus.advantage == AdvantageStatus.DISADVANTAGE
    removed = target.advance_duration_condition("Poisoned")
    assert not removed
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    removed = target.advance_duration_condition("Poisoned")
    assert removed
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.NONE
    assert acrobatics.skill_bonus.advantage == AdvantageStatus.NONE


def test_deafened_auto_miss_skills_and_remove():
    source, target = make_entities()
    condition = Deafened(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    event = condition.apply()
    assert event and not event.canceled
    skill = target.skill_set.get_skill("perception")
    assert skill.skill_bonus.auto_hit == AutoHitStatus.AUTOMISS
    condition.remove_condition_modifiers()
    assert skill.skill_bonus.auto_hit == AutoHitStatus.NONE


def test_dodging_disadvantage_and_dex_save_advantage():
    attacker, dodger = make_entities()
    condition = Dodging(source_entity_uuid=attacker.uuid, target_entity_uuid=dodger.uuid)
    condition.apply()
    dex_save = dodger.saving_throws.get_saving_throw("dexterity")
    assert dex_save.bonus.advantage == AdvantageStatus.ADVANTAGE
    mods = list(dodger.equipment.ac_bonus.to_target_static.advantage_modifiers.values())
    assert len(mods) == 1 and mods[0].value == AdvantageStatus.DISADVANTAGE
    condition.remove_condition_modifiers()
    assert dex_save.bonus.advantage == AdvantageStatus.NONE
    assert len(dodger.equipment.ac_bonus.to_target_static.advantage_modifiers) == 0


def test_charmed_attack_and_skill_callables():
    charmer, charmed = make_entities()
    atk_mod = Charmed.charmed_attack_check(charmer.uuid, charmed.uuid, target_entity_uuid=charmer.uuid)
    assert atk_mod and atk_mod.value == AutoHitStatus.AUTOMISS
    assert Charmed.charmed_attack_check(charmer.uuid, charmed.uuid, target_entity_uuid=uuid4()) is None
    skill_mod = Charmed.charmed_skill_check(charmer.uuid, charmed.uuid, charmed.uuid, target_entity_uuid=charmer.uuid)
    assert skill_mod and skill_mod.value == AdvantageStatus.ADVANTAGE
    assert Charmed.charmed_skill_check(charmer.uuid, charmed.uuid, charmer.uuid, target_entity_uuid=charmed.uuid) is None


ALL_CONDITIONS = [
    Blinded,
    Charmed,
    Dashing,
    Deafened,
    Dodging,
    Frightened,
    Grappled,
    Incapacitated,
    Invisible,
    Paralyzed,
    Poisoned,
    Prone,
    Restrained,
    Stunned,
    Unconscious,
]


def test_dashing_without_base_speed_raises():
    source, target = make_entities()
    target.action_economy.movement.self_static.value_modifiers = {}
    condition = Dashing(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    with pytest.raises(ValueError):
        condition.apply()


def test_frightened_helper_functions():
    frightener, target = make_entities()
    assert Frightened.frightener_in_senses_disadvantage(frightener.uuid, target.uuid) is None
    assert Frightened.frigthener_in_senses_zero_max_speed(frightener.uuid, target.uuid) is None
    target.senses.add_entity(frightener.uuid, frightener.position)
    mod = Frightened.frightener_in_senses_disadvantage(frightener.uuid, target.uuid, target.uuid)
    assert mod and mod.value == AdvantageStatus.DISADVANTAGE
    num = Frightened.frigthener_in_senses_zero_max_speed(frightener.uuid, target.uuid, target.uuid)
    assert num and num.value == 0
    cond = Frightened(source_entity_uuid=frightener.uuid, target_entity_uuid=target.uuid)
    cond.target_entity_uuid = None
    with pytest.raises(ValueError):
        cond.get_frightener_in_senses_disadvantage()
    cond2 = Frightened(source_entity_uuid=frightener.uuid, target_entity_uuid=target.uuid)
    cond2.target_entity_uuid = None
    with pytest.raises(ValueError):
        cond2.get_frigthener_in_senses_zero_max_speed()


def test_paralyzed_subcondition_skipped_when_immune():
    paralyzer, target = make_entities()
    target.condition_immunities.append(("Incapacitated", None))
    condition = Paralyzed(source_entity_uuid=paralyzer.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert "Incapacitated" not in target.active_conditions


def test_stunned_subcondition_skipped_when_immune():
    source, target = make_entities()
    target.condition_immunities.append(("Incapacitated", None))
    condition = Stunned(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert "Incapacitated" not in target.active_conditions


def test_unconscious_subcondition_skipped_when_immune():
    source, target = make_entities()
    target.condition_immunities.append(("Incapacitated", None))
    condition = Unconscious(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert "Incapacitated" not in target.active_conditions


def test_invisible_callables_return_none_for_seer():
    invisible, observer = make_entities()
    observer.senses.extra_senses.append(SensesType.TRUESIGHT)
    condition = Invisible(source_entity_uuid=invisible.uuid, target_entity_uuid=invisible.uuid)
    condition.apply()
    self_mod = next(iter(invisible.equipment.attack_bonus.self_contextual.advantage_modifiers.values()))
    to_target_mod = next(iter(invisible.equipment.ac_bonus.to_target_contextual.advantage_modifiers.values()))
    assert self_mod.callable(invisible.uuid, observer.uuid, None) is None
    assert to_target_mod.callable(observer.uuid, observer.uuid, None) is None
    assert Invisible.target_can_not_see_invisible_advantage(invisible.uuid) is None
    assert Invisible.target_can_not_see_invisible_disadvantage(invisible.uuid) is None


def test_prone_distance_advantage_none_when_no_target():
    attacker, target = make_entities()
    assert Prone.prone_distance_advantage(attacker.uuid) is None


def test_create_condition_rounds_duration():
    source, target = make_entities()
    cond = create_condition(
        ConditionType.POISONED,
        source.uuid,
        target.uuid,
        duration_type=DurationType.ROUNDS,
        duration_rounds=3,
    )
    assert isinstance(cond, Poisoned)
    assert cond.duration.duration_type == DurationType.ROUNDS
    assert cond.duration.duration == 3


def test_create_condition_default_duration():
    source, target = make_entities()
    cond = create_condition(ConditionType.DASHING, source.uuid, target.uuid)
    assert isinstance(cond, Dashing)
    assert cond.duration.duration_type == DurationType.PERMANENT
    assert cond.duration.duration is None


@pytest.mark.parametrize("condition_cls", ALL_CONDITIONS)
def test_condition_apply_missing_target_cancels(condition_cls):
    source = Entity.create(source_entity_uuid=uuid4())
    condition = condition_cls(source_entity_uuid=source.uuid, target_entity_uuid=uuid4())
    event = condition.apply()
    assert event and event.canceled


@pytest.mark.parametrize("condition_cls", ALL_CONDITIONS)
def test_condition_apply_invalid_target_type_cancels(condition_cls):
    source = Entity.create(source_entity_uuid=uuid4())
    fake_uuid = uuid4()
    Entity._entity_registry[fake_uuid] = "not-entity"
    try:
        condition = condition_cls(source_entity_uuid=source.uuid, target_entity_uuid=fake_uuid)
        event = condition.apply()
        assert event and event.canceled
    finally:
        del Entity._entity_registry[fake_uuid]


@pytest.mark.parametrize("condition_cls", ALL_CONDITIONS)
def test_condition_apply_without_target_uuid_raises(condition_cls):
    source, target = make_entities()
    condition = condition_cls(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.target_entity_uuid = None
    with pytest.raises(ValueError):
        condition.apply()

