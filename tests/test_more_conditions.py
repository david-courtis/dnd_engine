import pytest
from uuid import uuid4
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dnd.entity import Entity
from dnd.conditions import Poisoned, Grappled, Invisible, Prone
from dnd.core.modifiers import AdvantageStatus
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
