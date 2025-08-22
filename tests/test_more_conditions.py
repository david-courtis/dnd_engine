import pytest
from uuid import uuid4
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dnd.entity import Entity
from dnd.conditions import (
    Poisoned,
    Grappled,
    Invisible,
    Prone,
    Frightened,
    Incapacitated,
    Paralyzed,
    Restrained,
    Stunned,
    Unconscious,
)
from dnd.core.modifiers import AdvantageStatus, AutoHitStatus, CriticalStatus
from dnd.core.base_conditions import DurationType


def test_poisoned_applies_and_removes_disadvantage():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    condition = Poisoned(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    skill = target.skill_set.get_skill("acrobatics")
    assert skill.skill_bonus.advantage == AdvantageStatus.DISADVANTAGE
    condition.remove()
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.NONE
    assert skill.skill_bonus.advantage == AdvantageStatus.NONE


def test_grappled_sets_speed_to_zero_and_restores():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    base_speed = target.action_economy.movement.normalized_score
    condition = Grappled(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    move = target.action_economy.movement
    assert move.max == 0
    assert move.normalized_score == 0
    condition.remove()
    assert move.max is None
    assert move.normalized_score == base_speed


def test_invisible_grants_advantage_and_imposes_disadvantage():
    target = Entity.create(source_entity_uuid=uuid4(), name="Invisible")
    enemy = Entity.create(source_entity_uuid=uuid4(), name="Enemy")
    condition = Invisible(source_entity_uuid=target.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    self_mod = next(iter(target.equipment.attack_bonus.self_contextual.advantage_modifiers.values()))
    assert self_mod.callable(target.uuid, enemy.uuid, None).value == AdvantageStatus.ADVANTAGE
    to_target_mod = next(iter(target.equipment.ac_bonus.to_target_contextual.advantage_modifiers.values()))
    assert to_target_mod.callable(enemy.uuid, target.uuid, None).value == AdvantageStatus.DISADVANTAGE
    condition.remove()
    assert len(target.equipment.attack_bonus.self_contextual.advantage_modifiers) == 0
    assert len(target.equipment.ac_bonus.to_target_contextual.advantage_modifiers) == 0


def test_prone_disadvantage_and_attackers_advantage():
    target = Entity.create(source_entity_uuid=uuid4(), name="Prone")
    close_attacker = Entity.create(source_entity_uuid=uuid4(), name="Close")
    far_attacker = Entity.create(source_entity_uuid=uuid4(), name="Far")
    far_attacker.move((10, 0))
    condition = Prone(source_entity_uuid=close_attacker.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    mod = next(iter(target.equipment.ac_bonus.to_target_contextual.advantage_modifiers.values()))
    assert mod.callable(close_attacker.uuid, target.uuid, None).value == AdvantageStatus.ADVANTAGE
    assert mod.callable(far_attacker.uuid, target.uuid, None).value == AdvantageStatus.DISADVANTAGE
    condition.remove()
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.NONE
    assert len(target.equipment.ac_bonus.to_target_contextual.advantage_modifiers) == 0


def test_poisoned_does_not_stack():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    base_skill = target.skill_set.get_skill("acrobatics").skill_bonus.advantage
    first = Poisoned(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    target.add_condition(first)
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    second = Poisoned(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    target.add_condition(second)
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    assert target.active_conditions["Poisoned"].uuid == second.uuid
    target.remove_condition("Poisoned")
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.NONE
    assert target.skill_set.get_skill("acrobatics").skill_bonus.advantage == base_skill


def test_grappled_condition_duration_expires_and_restores_speed():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    base_speed = target.action_economy.movement.normalized_score
    condition = Grappled(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.duration.duration_type = DurationType.ROUNDS
    condition.duration.duration = 1
    target.add_condition(condition)
    assert target.action_economy.movement.normalized_score == 0
    removed = target.advance_duration_condition("Grappled")
    assert removed
    assert target.action_economy.movement.normalized_score == base_speed


def test_frightened_disadvantage_and_speed_zero():
    frightener = Entity.create(source_entity_uuid=uuid4(), name="Frightener")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    frightener.set_values_and_blocks_source()
    target.set_values_and_blocks_source()
    target.senses.add_entity(frightener.uuid, frightener.position)
    condition = Frightened(source_entity_uuid=frightener.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    atk = target.attack_bonus(target_entity_uuid=frightener.uuid)
    assert atk.advantage == AdvantageStatus.DISADVANTAGE
    skill = target.skill_bonus(frightener.uuid, "acrobatics")
    assert skill.advantage == AdvantageStatus.DISADVANTAGE
    assert target.action_economy.movement.max == 0
    condition.remove()
    atk = target.attack_bonus(target_entity_uuid=frightener.uuid)
    assert atk.advantage == AdvantageStatus.NONE
    skill = target.skill_bonus(frightener.uuid, "acrobatics")
    assert skill.advantage == AdvantageStatus.NONE
    assert target.action_economy.movement.max is None


def test_incapacitated_sets_actions_to_zero():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    base_speed = target.action_economy.movement.normalized_score
    condition = Incapacitated(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    ae = target.action_economy
    assert ae.actions.max == 0
    assert ae.bonus_actions.max == 0
    assert ae.reactions.max == 0
    assert ae.movement.max == 0
    condition.remove()
    assert ae.actions.max is None
    assert ae.bonus_actions.max is None
    assert ae.reactions.max is None
    assert ae.movement.max is None
    assert ae.movement.normalized_score == base_speed


def test_paralyzed_auto_fail_and_auto_crit():
    paralyzer = Entity.create(source_entity_uuid=uuid4(), name="Paralyzer")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    far_attacker = Entity.create(source_entity_uuid=uuid4(), name="Far")
    paralyzer.set_values_and_blocks_source()
    target.set_values_and_blocks_source()
    far_attacker.set_values_and_blocks_source()
    far_attacker.move((10, 0))
    condition = Paralyzed(source_entity_uuid=paralyzer.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.AUTOMISS
    assert target.saving_throws.get_saving_throw("strength").bonus.auto_hit == AutoHitStatus.AUTOMISS
    crit_mod = next(iter(target.equipment.ac_bonus.to_target_contextual.critical_modifiers.values()))
    assert crit_mod.callable(paralyzer.uuid, target.uuid, None).value == CriticalStatus.AUTOCRIT
    assert crit_mod.callable(far_attacker.uuid, target.uuid, None) is None
    condition.remove()
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.NONE
    assert target.saving_throws.get_saving_throw("strength").bonus.auto_hit == AutoHitStatus.NONE
    assert len(target.equipment.ac_bonus.to_target_contextual.critical_modifiers) == 0


def test_restrained_limits_movement_and_attackers_gain_advantage():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    attacker = Entity.create(source_entity_uuid=uuid4(), name="Attacker")
    target.set_values_and_blocks_source()
    attacker.set_values_and_blocks_source()
    base_speed = target.action_economy.movement.normalized_score
    condition = Restrained(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.action_economy.movement.max == 0
    assert target.attack_bonus(target_entity_uuid=attacker.uuid).advantage == AdvantageStatus.DISADVANTAGE
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.AUTOMISS
    mods = list(target.equipment.ac_bonus.to_target_static.advantage_modifiers.values())
    assert len(mods) == 1 and mods[0].value == AdvantageStatus.ADVANTAGE
    condition.remove()
    assert target.action_economy.movement.max is None
    assert target.action_economy.movement.normalized_score == base_speed
    assert target.attack_bonus(target_entity_uuid=attacker.uuid).advantage == AdvantageStatus.NONE
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.NONE
    assert len(target.equipment.ac_bonus.to_target_static.advantage_modifiers) == 0


def test_stunned_auto_fail_and_attackers_advantage():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    attacker = Entity.create(source_entity_uuid=uuid4(), name="Attacker")
    target.set_values_and_blocks_source()
    attacker.set_values_and_blocks_source()
    condition = Stunned(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.AUTOMISS
    assert target.saving_throws.get_saving_throw("strength").bonus.auto_hit == AutoHitStatus.AUTOMISS
    mods = list(target.equipment.ac_bonus.to_target_static.advantage_modifiers.values())
    assert len(mods) == 1 and mods[0].value == AdvantageStatus.ADVANTAGE
    condition.remove()
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.NONE
    assert target.saving_throws.get_saving_throw("strength").bonus.auto_hit == AutoHitStatus.NONE
    assert len(target.equipment.ac_bonus.to_target_static.advantage_modifiers) == 0


def test_unconscious_advantage_and_critical_within_range():
    source = Entity.create(source_entity_uuid=uuid4(), name="Source")
    target = Entity.create(source_entity_uuid=uuid4(), name="Target")
    close = Entity.create(source_entity_uuid=uuid4(), name="Close")
    far = Entity.create(source_entity_uuid=uuid4(), name="Far")
    source.set_values_and_blocks_source()
    target.set_values_and_blocks_source()
    close.set_values_and_blocks_source()
    far.set_values_and_blocks_source()
    far.move((10, 0))
    condition = Unconscious(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.AUTOMISS
    assert target.saving_throws.get_saving_throw("strength").bonus.auto_hit == AutoHitStatus.AUTOMISS
    adv_static = next(iter(target.equipment.ac_bonus.to_target_static.advantage_modifiers.values()))
    assert adv_static.value == AdvantageStatus.ADVANTAGE
    adv_context = next(iter(target.equipment.ac_bonus.to_target_contextual.advantage_modifiers.values()))
    crit_context = next(iter(target.equipment.ac_bonus.to_target_contextual.critical_modifiers.values()))
    assert adv_context.callable(close.uuid, target.uuid, None).value == AdvantageStatus.ADVANTAGE
    assert adv_context.callable(far.uuid, target.uuid, None).value == AdvantageStatus.DISADVANTAGE
    assert crit_context.callable(close.uuid, target.uuid, None).value == CriticalStatus.AUTOCRIT
    assert crit_context.callable(far.uuid, target.uuid, None) is None
    condition.remove()
    assert target.saving_throws.get_saving_throw("dexterity").bonus.auto_hit == AutoHitStatus.NONE
    assert target.saving_throws.get_saving_throw("strength").bonus.auto_hit == AutoHitStatus.NONE
    assert len(target.equipment.ac_bonus.to_target_static.advantage_modifiers) == 0
    assert len(target.equipment.ac_bonus.to_target_contextual.advantage_modifiers) == 0
    assert len(target.equipment.ac_bonus.to_target_contextual.critical_modifiers) == 0
