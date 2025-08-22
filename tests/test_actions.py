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
    attack_factory,
)
from dnd.core.base_actions import ActionEvent, Cost, StructuredAction
from dnd.core.events import (
    EventType,
    EventPhase,
    WeaponSlot,
    Damage,
    EventHandler,
    Trigger,
    EventQueue,
    RangeType,
    Range,
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


def test_entity_action_economy_cost_applier_missing_entity():
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=uuid4(),
        target_entity_uuid=None,
        costs=[Cost(name="Action Cost", cost_type="actions", cost=1)],
    )
    result = entity_action_economy_cost_applier(event, uuid4())
    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Entity not found for Attack"


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
    assert history_phases[0] == EventPhase.EXECUTION
    assert attacker.target_entity_uuid is None
    assert defender.target_entity_uuid is None


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


def test_validate_line_of_sight_missing_source_entity():
    missing_uuid = uuid4()
    target = Entity.create(uuid4(), name="Target")
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=missing_uuid,
        target_entity_uuid=target.uuid,
        event_type=EventType.BASE_ACTION,
    )

    result = validate_line_of_sight(event, missing_uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Source entity not found for Attack"


def test_validate_line_of_sight_missing_target_entity():
    source = Entity.create(uuid4(), name="Source")
    missing_uuid = uuid4()
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=missing_uuid,
        event_type=EventType.BASE_ACTION,
    )

    result = validate_line_of_sight(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not found for Attack"


def test_validate_line_of_sight_missing_target_uuid():
    source = Entity.create(uuid4(), name="Source")
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=None,
        event_type=EventType.BASE_ACTION,
    )

    result = validate_line_of_sight(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity uuid not present for Attack"


def test_validate_line_of_sight_source_not_entity():
    source_uuid = uuid4()
    target = Entity.create(uuid4(), name="Target")
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=source_uuid,
        target_entity_uuid=target.uuid,
        event_type=EventType.BASE_ACTION,
    )

    with patch.object(Entity, "get", side_effect=lambda u: {} if u == source_uuid else target):
        result = validate_line_of_sight(event, source_uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Source entity not found for Attack"


def test_validate_line_of_sight_target_not_entity():
    source = Entity.create(uuid4(), name="Source")
    target_uuid = uuid4()
    event = ActionEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target_uuid,
        event_type=EventType.BASE_ACTION,
    )

    with patch.object(Entity, "get", side_effect=lambda u: source if u == source.uuid else {}):
        result = validate_line_of_sight(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not found for Attack"


def test_validate_range_in_range():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    target.move((2, 0))
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    with patch.object(Entity, "get_weapon_range", return_value=Range(type=RangeType.RANGE, normal=3)):
        result = Attack.validate_range(event, source.uuid)

    assert not result.canceled
    assert result.phase == EventPhase.DECLARATION
    assert result.range.type == RangeType.RANGE


def test_validate_range_out_of_range():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    target.move((3, 0))
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    with patch.object(Entity, "get_weapon_range", return_value=Range(type=RangeType.RANGE, normal=2)):
        result = Attack.validate_range(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not in range for Attack"


def test_validate_range_missing_source_entity():
    target = Entity.create(uuid4(), name="Target")
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=uuid4(),
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    result = Attack.validate_range(event, uuid4())

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Source entity not found for Attack"


def test_validate_range_source_not_entity():
    source_uuid = uuid4()
    target = Entity.create(uuid4(), name="Target")
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source_uuid,
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    with patch.object(Entity, "get", side_effect=lambda u: {} if u == source_uuid else target):
        result = Attack.validate_range(event, source_uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Source entity not found for Attack"


def test_validate_range_missing_target_uuid():
    source = Entity.create(uuid4(), name="Source")
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=None,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    result = Attack.validate_range(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity uuid not present for Attack"


def test_validate_range_missing_target_entity():
    source = Entity.create(uuid4(), name="Source")
    missing_uuid = uuid4()
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=missing_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    result = Attack.validate_range(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not found for Attack"


def test_validate_range_weapon_range_not_found():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source.uuid,
        target_entity_uuid=target.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
    )

    with patch.object(Entity, "get_weapon_range", return_value=None):
        result = Attack.validate_range(event, source.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Weapon range not found for Attack"


def test_attack_consequences_missing_source_entity():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)

    result = Attack.attack_consequences(event, uuid4())

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Source entity not found for Attack"


def test_attack_consequences_missing_target_entity():
    attacker = Entity.create(uuid4(), name="Attacker")
    missing_uuid = uuid4()
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=attacker.uuid,
        target_entity_uuid=missing_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.EXECUTION,
    )

    result = Attack.attack_consequences(event, attacker.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not found for Attack"


def test_attack_consequences_missing_target_uuid():
    attacker = Entity.create(uuid4(), name="Attacker")
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=attacker.uuid,
        target_entity_uuid=None,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.EXECUTION,
    )

    result = Attack.attack_consequences(event, attacker.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity uuid not present for Attack"


def test_attack_consequences_source_not_entity():
    source_uuid = uuid4()
    defender = Entity.create(uuid4(), name="Defender")
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=source_uuid,
        target_entity_uuid=defender.uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.EXECUTION,
    )

    with patch.object(Entity, "get", side_effect=lambda u: {} if u == source_uuid else defender):
        result = Attack.attack_consequences(event, source_uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Source entity not found for Attack"


def test_attack_consequences_target_not_entity():
    attacker = Entity.create(uuid4(), name="Attacker")
    target_uuid = uuid4()
    event = AttackEvent(
        name="Attack",
        source_entity_uuid=attacker.uuid,
        target_entity_uuid=target_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.EXECUTION,
    )

    with patch.object(Entity, "get", side_effect=lambda u: attacker if u == attacker.uuid else {}):
        result = Attack.attack_consequences(event, attacker.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL
    assert result.status_message == "Target entity not found for Attack"


def test_attack_consequences_canceled_after_roll():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)

    handler = EventHandler(
        name="cancel_after_roll",
        source_entity_uuid=attacker.uuid,
        target_entity_uuid=attacker.uuid,
        trigger_conditions=[Trigger(event_type=EventType.ATTACK, event_phase=EventPhase.EXECUTION, event_source_entity_uuid=attacker.uuid, event_target_entity_uuid=defender.uuid)],
        event_processor=lambda e, _: e.cancel(status_message="Canceled after roll") if e.dice_roll else e,
    )
    EventQueue.add_event_handler(EventType.ATTACK, EventPhase.EXECUTION, attacker.uuid, handler)
    try:
        with patch.object(Entity, "roll_d20", return_value=_make_attack_roll(attacker.uuid, defender.uuid, 10, 12, 2)), \
            patch.object(Entity, "get_damages", return_value=[]), \
            patch.object(Entity, "take_damage"), \
            patch.object(Entity, "attack_bonus", autospec=True, side_effect=lambda self, weapon_slot=WeaponSlot.MAIN_HAND, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=2, value_name="Attack Bonus")), \
            patch.object(Entity, "ac_bonus", autospec=True, side_effect=lambda self, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=10, value_name="AC")):
            result = Attack.attack_consequences(event, attacker.uuid)
    finally:
        EventQueue.remove_event_handler(handler)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL


def test_attack_consequences_canceled_after_damage_phase():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)
    damage = _make_damage(attacker.uuid, defender.uuid)
    damage_roll = _make_damage_roll(attacker.uuid, defender.uuid, 3)

    original_post = AttackEvent.post

    def cancel_on_effect(self, **updates):
        result = original_post(self, **updates)
        if updates.get("new_phase") == EventPhase.EFFECT and "damages" in updates:
            return result.cancel(status_message="Canceled in effect")
        return result

    with patch.object(AttackEvent, "post", new=cancel_on_effect), \
        patch.object(Entity, "roll_d20", return_value=_make_attack_roll(attacker.uuid, defender.uuid, 10, 12, 2)), \
        patch.object(Entity, "get_damages", return_value=[damage]), \
        patch.object(Entity, "take_damage", return_value=[damage_roll]), \
        patch.object(Entity, "attack_bonus", autospec=True, side_effect=lambda self, weapon_slot=WeaponSlot.MAIN_HAND, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=2, value_name="Attack Bonus")), \
        patch.object(Entity, "ac_bonus", autospec=True, side_effect=lambda self, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=10, value_name="AC")):
        result = Attack.attack_consequences(event, attacker.uuid)

    assert result.canceled
    assert result.phase == EventPhase.CANCEL


def test_attack_consequences_no_attack_outcome():
    attacker = Entity.create(uuid4(), name="Attacker")
    defender = Entity.create(uuid4(), name="Defender")
    event = _make_attack_event(attacker, defender)
    attack_roll = _make_attack_roll(attacker.uuid, defender.uuid, 10, 10, 0)
    damage = _make_damage(attacker.uuid, defender.uuid)

    with patch.object(Entity, "roll_d20", return_value=attack_roll), \
        patch.object(Entity, "get_damages", return_value=[damage]), \
        patch.object(Entity, "take_damage") as take_damage_mock, \
        patch("dnd.actions.determine_attack_outcome", return_value=None), \
        patch.object(Entity, "attack_bonus", autospec=True, side_effect=lambda self, weapon_slot=WeaponSlot.MAIN_HAND, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=2, value_name="Attack Bonus")), \
        patch.object(Entity, "ac_bonus", autospec=True, side_effect=lambda self, target_entity_uuid=None: ModifiableValue.create(source_entity_uuid=self.uuid, target_entity_uuid=target_entity_uuid, base_value=10, value_name="AC")):
        result = Attack.attack_consequences(event, attacker.uuid)

    assert result.phase == EventPhase.COMPLETION
    assert result.damage_rolls is None
    take_damage_mock.assert_not_called()


def test_attack_create_declaration_event():
    source = Entity.create(uuid4(), name="Source")
    target = Entity.create(uuid4(), name="Target")
    action = Attack(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid, weapon_slot=WeaponSlot.MAIN_HAND)
    event = action._create_declaration_event()
    assert isinstance(event, AttackEvent)
    assert event.phase == EventPhase.DECLARATION
    assert event.source_entity_uuid == source.uuid
    assert event.target_entity_uuid == target.uuid


def test_attack_validate_range_returns_none():
    action = Attack(source_entity_uuid=uuid4(), target_entity_uuid=uuid4(), weapon_slot=WeaponSlot.MAIN_HAND)
    declaration_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.DECLARATION,
    )
    with patch.object(Attack, "validate_range", return_value=None):
        result = action._validate(declaration_event)
    assert result.canceled
    assert result.status_message == f"Range validation returned None for {action.name}"


def test_attack_validate_range_canceled():
    action = Attack(source_entity_uuid=uuid4(), target_entity_uuid=uuid4(), weapon_slot=WeaponSlot.MAIN_HAND)
    declaration_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.DECLARATION,
    )
    canceled_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.DECLARATION,
    ).cancel(status_message="Canceled")
    with patch.object(Attack, "validate_range", return_value=canceled_event):
        result = action._validate(declaration_event)
    assert result is canceled_event


def test_attack_validate_line_of_sight_returns_none():
    action = Attack(source_entity_uuid=uuid4(), target_entity_uuid=uuid4(), weapon_slot=WeaponSlot.MAIN_HAND)
    declaration_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.DECLARATION,
    )
    with patch.object(Attack, "validate_range", return_value=declaration_event), \
        patch("dnd.actions.validate_line_of_sight", return_value=None):
        result = action._validate(declaration_event)
    assert result.canceled
    assert result.status_message == f"Line of sight validation returned None for {action.name}"


def test_attack_validate_line_of_sight_canceled():
    action = Attack(source_entity_uuid=uuid4(), target_entity_uuid=uuid4(), weapon_slot=WeaponSlot.MAIN_HAND)
    declaration_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.DECLARATION,
    )
    canceled_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.DECLARATION,
    ).cancel(status_message="Canceled LOS")
    with patch.object(Attack, "validate_range", return_value=declaration_event), \
        patch("dnd.actions.validate_line_of_sight", return_value=canceled_event):
        result = action._validate(declaration_event)
    assert result is canceled_event


def test_attack_validate_success():
    action = Attack(source_entity_uuid=uuid4(), target_entity_uuid=uuid4(), weapon_slot=WeaponSlot.MAIN_HAND)
    declaration_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.DECLARATION,
    )
    with patch.object(Attack, "validate_range", return_value=declaration_event), \
        patch("dnd.actions.validate_line_of_sight", return_value=declaration_event):
        result = action._validate(declaration_event)
    assert not result.canceled
    assert result.phase == EventPhase.EXECUTION


def test_attack_apply_delegates_to_attack_consequences():
    action = Attack(source_entity_uuid=uuid4(), target_entity_uuid=uuid4(), weapon_slot=WeaponSlot.MAIN_HAND)
    execution_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.EXECUTION,
    )
    sentinel = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.EXECUTION,
    )
    with patch.object(Attack, "attack_consequences", return_value=sentinel) as mock_conseq:
        result = action._apply(execution_event)
    mock_conseq.assert_called_once_with(execution_event, action.source_entity_uuid)
    assert result is sentinel


def test_attack_apply_costs_delegates():
    action = Attack(source_entity_uuid=uuid4(), target_entity_uuid=uuid4(), weapon_slot=WeaponSlot.MAIN_HAND)
    completion_event = AttackEvent(
        name="Attack",
        source_entity_uuid=action.source_entity_uuid,
        target_entity_uuid=action.target_entity_uuid,
        weapon_slot=WeaponSlot.MAIN_HAND,
        phase=EventPhase.COMPLETION,
    )
    with patch("dnd.actions.entity_action_economy_cost_applier", return_value=completion_event) as mock_applier:
        result = action._apply_costs(completion_event)
    mock_applier.assert_called_once_with(completion_event, action.source_entity_uuid)
    assert result is completion_event


def test_attack_factory_creates_structured_action():
    source_uuid = uuid4()
    target_uuid = uuid4()
    action = attack_factory(source_uuid, target_uuid)
    assert isinstance(action, StructuredAction)
    assert "validate_range" in action.prerequisites
    assert "attack_consequences" in action.consequences
