from uuid import uuid4
import os
import sys
from unittest.mock import patch

# Ensure repository root is on the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dnd.entity import Entity
from dnd.actions import (
    validate_line_of_sight,
    entity_action_economy_cost_evaluator,
    entity_action_economy_cost_applier,
    Attack,
    AttackEvent,
)
from dnd.core.base_actions import ActionEvent, Cost
from dnd.core.events import (
    EventType,
    EventPhase,
    WeaponSlot,
    Damage,
    EventHandler,
    Trigger,
    EventQueue,
)
from dnd.core.dice import DiceRoll, RollType, AttackOutcome
from dnd.core.values import AdvantageStatus, CriticalStatus, AutoHitStatus, ModifiableValue
from dnd.core.modifiers import DamageType


def test_validate_line_of_sight_success():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    source.senses.add_entity(target.uuid, target.position)
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        event_type=EventType.BASE_ACTION,
    )

    result = validate_line_of_sight(event, source.uuid)

    assert result is not None
    assert not result.canceled
    assert result.phase == EventPhase.DECLARATION
    assert result.status_message == "Validated line of sight for Attack"


def test_validate_line_of_sight_failure():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        event_type=EventType.BASE_ACTION,
    )

    result = validate_line_of_sight(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not in line of sight for Attack"


def test_entity_action_economy_cost_evaluator_success():
    entity = Entity.create(uuid4())
    assert entity_action_economy_cost_evaluator(entity.uuid, "actions", 1)


def test_entity_action_economy_cost_evaluator_failure():
    entity = Entity.create(uuid4())
    assert not entity_action_economy_cost_evaluator(entity.uuid, "actions", 2)
    assert not entity_action_economy_cost_evaluator(uuid4(), "actions", 1)


def test_entity_action_economy_cost_applier_deducts_cost():
    entity = Entity.create(uuid4())
    initial_actions = entity.action_economy.actions.self_static.normalized_score
    event = ActionEvent.from_costs(
        [Cost(name="Action Cost", cost_type="actions", cost=1)],
        source_entity_uuid=entity.uuid,
    )

    result = entity_action_economy_cost_applier(event, entity.uuid)

    assert not result.canceled
    assert result.phase == EventPhase.COMPLETION
    assert (
      entity.action_economy.actions.self_static.normalized_score
      == initial_actions - 1
  )


def test_validate_range_in_reach():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    target.move((0, 1))
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    result = Attack.validate_range(event, source.uuid)

    assert not result.canceled
    assert result.phase == EventPhase.DECLARATION
    assert result.range.normal == 5


def test_validate_range_out_of_reach():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    target.move((0, 2))
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    result = Attack.validate_range(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not in reach for Attack"


def _make_attack_event(source, target):
    return AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.EXECUTION,
    )


def _make_attack_roll(attacker_uuid, target_uuid, result, total, bonus, critical=CriticalStatus.NONE):
    return DiceRoll(
        dice_uuid=uuid4(),
        roll_type=RollType.ATTACK,
        results=result,
        total=total,
        bonus=bonus,
        advantage_status=AdvantageStatus.NONE,
        critical_status=critical,
        auto_hit_status=AutoHitStatus.NONE,
        source_entity_uuid=attacker_uuid,
        target_entity_uuid=target_uuid,
    )


def _make_damage_roll(attacker_uuid, target_uuid, result):
    return DiceRoll(
        dice_uuid=uuid4(),
        roll_type=RollType.DAMAGE,
        results=result,
        total=result,
        bonus=0,
        advantage_status=AdvantageStatus.NONE,
        critical_status=CriticalStatus.NONE,
        auto_hit_status=AutoHitStatus.NONE,
        source_entity_uuid=attacker_uuid,
        target_entity_uuid=target_uuid,
    )


def _make_damage(attacker_uuid, target_uuid):
    return Damage(
        source_entity_uuid=attacker_uuid,
        target_entity_uuid=target_uuid,
        damage_dice=4,
        dice_numbers=1,
        damage_bonus=None,
        damage_type=DamageType.BLUDGEONING,
    )


def test_attack_consequences_hit():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)

    attack_roll = _make_attack_roll(attacker.uuid, defender.uuid, 10, 12, 2)
    damage_roll = _make_damage_roll(attacker.uuid, defender.uuid, 3)
    damage = _make_damage(attacker.uuid, defender.uuid)

    with patch.object(Entity, "roll_d20", return_value=attack_roll), \
        patch.object(Entity, "get_damages", return_value=[damage]), \
        patch.object(Entity, "take_damage", return_value=[damage_roll]), \
        patch.object(Entity, "attack_bonus", autospec=True, side_effect=lambda self, weapon_slot=WeaponSlot.MAIN_HAND, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=2, value_name="Attack Bonus")), \
        patch.object(Entity, "ac_bonus", autospec=True, side_effect=lambda self, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=10, value_name="AC")):
        result = Attack.attack_consequences(event, attacker.uuid)

    assert result.attack_outcome == AttackOutcome.HIT
    assert result.phase == EventPhase.COMPLETION
    assert result.damage_rolls[0].total == 3
    history_phases = [e.phase for e in result.get_history()]
    assert EventPhase.EFFECT in history_phases


def test_attack_consequences_miss():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)

    miss_roll = _make_attack_roll(attacker.uuid, defender.uuid, 2, 4, 2)

    with patch.object(Entity, "roll_d20", return_value=miss_roll), \
        patch.object(Entity, "get_damages") as get_damages_mock, \
        patch.object(Entity, "take_damage") as take_damage_mock, \
        patch.object(Entity, "attack_bonus", autospec=True, side_effect=lambda self, weapon_slot=WeaponSlot.MAIN_HAND, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=2, value_name="Attack Bonus")), \
        patch.object(Entity, "ac_bonus", autospec=True, side_effect=lambda self, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=10, value_name="AC")):
        result = Attack.attack_consequences(event, attacker.uuid)

    assert result.attack_outcome == AttackOutcome.MISS
    assert result.phase == EventPhase.COMPLETION
    assert result.damage_rolls is None
    get_damages_mock.assert_not_called()
    take_damage_mock.assert_not_called()
    history_phases = [e.phase for e in result.get_history()]
    assert EventPhase.EFFECT not in history_phases


def test_attack_consequences_crit():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)

    crit_roll = _make_attack_roll(attacker.uuid, defender.uuid, 20, 22, 2)
    damage_roll = _make_damage_roll(attacker.uuid, defender.uuid, 4)
    damage = _make_damage(attacker.uuid, defender.uuid)

    with patch.object(Entity, "roll_d20", return_value=crit_roll), \
        patch.object(Entity, "get_damages", return_value=[damage]), \
        patch.object(Entity, "take_damage", return_value=[damage_roll]), \
        patch.object(Entity, "attack_bonus", autospec=True, side_effect=lambda self, weapon_slot=WeaponSlot.MAIN_HAND, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=2, value_name="Attack Bonus")), \
        patch.object(Entity, "ac_bonus", autospec=True, side_effect=lambda self, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=10, value_name="AC")):
        result = Attack.attack_consequences(event, attacker.uuid)

    assert result.attack_outcome == AttackOutcome.CRIT
    assert result.phase == EventPhase.COMPLETION
    assert result.damage_rolls[0].total == 4
    history_phases = [e.phase for e in result.get_history()]
    assert EventPhase.EFFECT in history_phases


def test_attack_consequences_canceled():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)

    handler = EventHandler(
        name="cancel_attack",
        source_entity_uuid=attacker.uuid,
        target_entity_uuid=attacker.uuid,
        trigger_conditions=[Trigger(event_type=EventType.ATTACK, event_phase=EventPhase.EXECUTION, event_source_entity_uuid=attacker.uuid, event_target_entity_uuid=defender.uuid)],
        event_processor=lambda e, _: e.cancel(status_message="Canceled"),
    )
    EventQueue.add_event_handler(EventType.ATTACK, EventPhase.EXECUTION, attacker.uuid, handler)
    try:
        with patch.object(Entity, "attack_bonus", autospec=True, side_effect=lambda self, weapon_slot=WeaponSlot.MAIN_HAND, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=2, value_name="Attack Bonus")), \
            patch.object(Entity, "ac_bonus", autospec=True, side_effect=lambda self, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=10, value_name="AC")):
            result = Attack.attack_consequences(event, attacker.uuid)
    finally:
        EventQueue.remove_event_handler(handler)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL