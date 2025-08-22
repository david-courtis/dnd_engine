from uuid import uuid4, UUID
import pytest

from dnd.core.events import (
    Event,
    EventType,
    EventPhase,
    EventQueue,
    EventHandler,
    Trigger,
    SavingThrowEvent,
    D20Event,
    Range,
    RangeType,
    Damage,
)
from dnd.core.values import ModifiableValue
from dnd.core.modifiers import BaseObject, DamageType
from dnd.core.dice import AttackOutcome


@pytest.fixture(autouse=True)
def clear_event_queue():
    """Ensure EventQueue starts empty for each test."""
    EventQueue._events_by_lineage.clear()
    EventQueue._events_by_uuid.clear()
    EventQueue._events_by_type.clear()
    EventQueue._events_by_timestamp.clear()
    EventQueue._events_by_phase.clear()
    EventQueue._events_by_source.clear()
    EventQueue._events_by_target.clear()
    EventQueue._all_events.clear()
    EventQueue._event_handlers.clear()
    EventQueue._event_handlers_by_trigger.clear()
    EventQueue._event_handlers_by_simple_trigger.clear()
    EventQueue._event_handlers_by_source_entity_uuid.clear()
    yield


def test_phase_to_advances_and_preserves_lineage():
    source = uuid4()
    target = uuid4()
    event = Event(event_type=EventType.BASE_ACTION, source_entity_uuid=source, target_entity_uuid=target)
    next_event = event.phase_to()
    assert next_event.phase == EventPhase.EXECUTION
    assert next_event.lineage_uuid == event.lineage_uuid
    assert next_event.uuid != event.uuid
    history = EventQueue.get_event_history(next_event.uuid)
    assert [e.uuid for e in history] == [event.uuid, next_event.uuid]


def test_cancel_marks_event_cancelled():
    source = uuid4()
    target = uuid4()
    event = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    canceled = event.cancel(status_message="nope")
    assert canceled.canceled is True
    assert canceled.phase == EventPhase.CANCEL
    assert canceled.status_message == "nope"


def test_event_queue_registration_and_retrieval():
    source = uuid4()
    target = uuid4()
    event = Event(event_type=EventType.MOVEMENT, source_entity_uuid=source, target_entity_uuid=target)
    assert EventQueue.get_event_by_uuid(event.uuid) is event
    assert event in EventQueue.get_events_by_type(EventType.MOVEMENT)


def test_event_handler_modifies_event():
    source = uuid4()
    target = uuid4()

    def processor(evt, _):
        return evt.phase_to(EventPhase.EFFECT, status_message="processed")

    trigger = Trigger(
        event_type=EventType.MOVEMENT,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=source,
        trigger_conditions=[trigger],
        event_processor=processor,
    )
    EventQueue.add_event_handler(EventType.MOVEMENT, EventPhase.DECLARATION, source, handler)

    Event(event_type=EventType.MOVEMENT, source_entity_uuid=source, target_entity_uuid=target)
    updated = EventQueue.get_events_by_type(EventType.MOVEMENT)[-1]
    assert updated.phase == EventPhase.EFFECT
    assert updated.status_message == "processed"


def test_event_handlers_progress_through_all_phases():
    source = uuid4()
    target = uuid4()
    order = []

    def declaration(evt, _):
        order.append((evt.phase, "decl"))
        return evt.phase_to(EventPhase.EXECUTION, status_message="declared")

    def execution(evt, _):
        order.append((evt.phase, "exec"))
        return evt.phase_to(EventPhase.EFFECT, status_message="executed")

    def effect(evt, _):
        order.append((evt.phase, "effect"))
        return evt.phase_to(EventPhase.COMPLETION, status_message="resolved")

    def completion(evt, _):
        order.append((evt.phase, "complete"))
        return evt

    triggers = [
        Trigger(
            event_type=EventType.HEAL,
            event_phase=EventPhase.DECLARATION,
            event_source_entity_uuid=source,
            event_target_entity_uuid=target,
        ),
        Trigger(
            event_type=EventType.HEAL,
            event_phase=EventPhase.EXECUTION,
            event_source_entity_uuid=source,
            event_target_entity_uuid=target,
        ),
        Trigger(
            event_type=EventType.HEAL,
            event_phase=EventPhase.EFFECT,
            event_source_entity_uuid=source,
            event_target_entity_uuid=target,
        ),
    ]
    handlers = [
        EventHandler(source_entity_uuid=source, target_entity_uuid=source, trigger_conditions=[triggers[0]], event_processor=declaration),
        EventHandler(source_entity_uuid=source, target_entity_uuid=source, trigger_conditions=[triggers[1]], event_processor=execution),
        EventHandler(source_entity_uuid=source, target_entity_uuid=source, trigger_conditions=[triggers[2]], event_processor=effect),
    ]
    EventQueue.add_event_handler(EventType.HEAL, EventPhase.DECLARATION, source, handlers[0])
    EventQueue.add_event_handler(EventType.HEAL, EventPhase.EXECUTION, source, handlers[1])
    EventQueue.add_event_handler(EventType.HEAL, EventPhase.EFFECT, source, handlers[2])

    Event(event_type=EventType.HEAL, source_entity_uuid=source, target_entity_uuid=target)
    final = EventQueue.get_events_by_type(EventType.HEAL)[-1]
    assert final.phase == EventPhase.COMPLETION
    assert final.status_message == "resolved"
    assert order == [
        (EventPhase.DECLARATION, "decl"),
        (EventPhase.EXECUTION, "exec"),
        (EventPhase.EFFECT, "effect"),
    ]


def test_event_handler_cancels_event():
    source = uuid4()
    target = uuid4()

    def canceler(evt, _):
        return evt.cancel("stop")

    trigger = Trigger(
        event_type=EventType.CAST_SPELL,
        event_phase=EventPhase.EXECUTION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=source,
        trigger_conditions=[trigger],
        event_processor=canceler,
    )
    EventQueue.add_event_handler(EventType.CAST_SPELL, EventPhase.EXECUTION, source, handler)

    Event(event_type=EventType.CAST_SPELL, source_entity_uuid=source, target_entity_uuid=target).phase_to(EventPhase.EXECUTION)
    canceled = EventQueue.get_events_by_type(EventType.CAST_SPELL)[-1]
    assert canceled.canceled is True
    assert canceled.phase == EventPhase.CANCEL
    assert canceled.status_message == "stop"


def test_event_with_no_handlers_remains_unmodified():
    source = uuid4()
    target = uuid4()
    event = Event(event_type=EventType.CONDITION_REMOVAL, source_entity_uuid=source, target_entity_uuid=target)
    retrieved = EventQueue.get_event_by_uuid(event.uuid)
    assert retrieved is event
    assert retrieved.phase == EventPhase.DECLARATION


def test_nested_dispatch_and_context_propagation():
    source = uuid4()
    target = uuid4()
    contexts = []

    def child_processor(evt, ctx):
        contexts.append(ctx)
        return evt.phase_to(EventPhase.COMPLETION)

    child_trigger = Trigger(
        event_type=EventType.DICE_ROLL,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    child_handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=source,
        trigger_conditions=[child_trigger],
        event_processor=child_processor,
    )
    EventQueue.add_event_handler(EventType.DICE_ROLL, EventPhase.DECLARATION, source, child_handler)

    def parent_processor(evt, ctx):
        child = Event(event_type=EventType.DICE_ROLL, source_entity_uuid=ctx, target_entity_uuid=evt.target_entity_uuid)
        child.set_parent_event(evt)
        EventQueue.register(child)
        return evt.phase_to(EventPhase.COMPLETION)

    parent_trigger = Trigger(
        event_type=EventType.ATTACK,
        event_phase=EventPhase.EXECUTION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    parent_handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=source,
        trigger_conditions=[parent_trigger],
        event_processor=parent_processor,
    )
    EventQueue.add_event_handler(EventType.ATTACK, EventPhase.EXECUTION, source, parent_handler)

    event = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    final = event.phase_to(EventPhase.EXECUTION)
    child = EventQueue.get_events_by_type(EventType.DICE_ROLL)[-1]
    parent = child.get_parent_event()
    assert parent is not None
    assert parent.lineage_uuid == final.lineage_uuid
    assert child.uuid in final.lineage_children_events
    assert contexts and contexts[-1] == source


def test_phase_to_and_cancel_update_lineage_children():
    source = uuid4()
    target = uuid4()
    parent = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    child = Event(event_type=EventType.DICE_ROLL, source_entity_uuid=source, target_entity_uuid=target)
    child.set_parent_event(parent)
    EventQueue.register(child)

    stored_parent = EventQueue.get_event_by_uuid(parent.uuid)
    assert child.uuid in stored_parent.children_events
    assert child.uuid in stored_parent.lineage_children_events

    advanced = stored_parent.phase_to(EventPhase.EXECUTION)
    assert child.uuid in advanced.lineage_children_events
    assert advanced.children_events == []

    canceled = advanced.cancel("halted")
    assert canceled.phase == EventPhase.CANCEL
    assert child.uuid in canceled.lineage_children_events
    assert canceled.children_events == []


def test_register_populates_indices_and_handlers():
    source = uuid4()
    target = uuid4()
    event = Event(event_type=EventType.MOVEMENT, source_entity_uuid=source, target_entity_uuid=target)

    # Stored in all indices
    assert EventQueue.get_event_by_uuid(event.uuid) is event
    assert event in EventQueue.get_events_by_type(EventType.MOVEMENT)
    assert event in EventQueue.get_events_by_phase(EventPhase.DECLARATION)
    assert event in EventQueue.get_events_by_source(source)
    assert event in EventQueue.get_events_by_target(target)
    assert event in EventQueue.get_events_by_timestamp(event.timestamp)
    assert event in EventQueue.get_events_chronological()
    assert event in EventQueue.get_latest_events(1)
    assert EventQueue.get_event_history(event.uuid) == [event]

    # Register with handler modifying the event
    def processor(evt, _):
        return evt.phase_to(EventPhase.EFFECT, status_message="done")

    trigger = Trigger(
        event_type=EventType.BASE_ACTION,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=target,
        trigger_conditions=[trigger],
        event_processor=processor,
    )
    EventQueue.add_event_handler(EventType.BASE_ACTION, EventPhase.DECLARATION, source, handler)

    raw = Event(event_type=EventType.BASE_ACTION, source_entity_uuid=source, target_entity_uuid=target)
    modified = EventQueue.get_events_by_type(EventType.BASE_ACTION)[-1]
    assert modified.uuid != raw.uuid
    assert modified.phase == EventPhase.EFFECT
    assert modified.status_message == "done"


def test_add_and_remove_event_handler_methods():
    source = uuid4()
    target = uuid4()

    trigger = Trigger(
        event_type=EventType.ATTACK,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=target,
        trigger_conditions=[trigger],
        event_processor=lambda e, _: e,
    )

    EventQueue.add_event_handler(EventType.ATTACK, EventPhase.DECLARATION, source, handler)
    assert handler.uuid in EventQueue._event_handlers
    assert handler in EventQueue._event_handlers_by_trigger[trigger]
    assert handler in EventQueue._event_handlers_by_source_entity_uuid[source]

    EventQueue.remove_event_handler(handler)
    assert handler.uuid not in EventQueue._event_handlers
    assert handler not in EventQueue._event_handlers_by_trigger[trigger]
    assert handler not in EventQueue._event_handlers_by_source_entity_uuid[source]

    EventQueue.add_event_handler(EventType.ATTACK, EventPhase.DECLARATION, source, handler)
    assert handler.uuid in EventQueue._event_handlers
    EventQueue.remove_event_handlers_by_uuid(handler.uuid)
    assert handler.uuid not in EventQueue._event_handlers


def test_event_queue_retrieval_apis():
    source = uuid4()
    target = uuid4()
    move = Event(event_type=EventType.MOVEMENT, source_entity_uuid=source, target_entity_uuid=target)
    attack_decl = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    attack_exec = attack_decl.phase_to(EventPhase.EXECUTION)

    chronological = EventQueue.get_events_chronological()
    assert chronological == [move, attack_decl, attack_exec]
    assert EventQueue.get_latest_events(2) == [attack_decl, attack_exec]

    history = EventQueue.get_event_history(attack_exec.uuid)
    assert [e.uuid for e in history] == [attack_decl.uuid, attack_exec.uuid]

    assert EventQueue.get_events_by_type(EventType.ATTACK) == [attack_decl, attack_exec]
    assert EventQueue.get_events_by_phase(EventPhase.DECLARATION) == [move, attack_decl]
    assert EventQueue.get_events_by_phase(EventPhase.EXECUTION) == [attack_exec]
    assert EventQueue.get_events_by_source(source) == [move, attack_decl, attack_exec]
    assert EventQueue.get_events_by_target(target) == [move, attack_decl, attack_exec]
    assert move in EventQueue.get_events_by_timestamp(move.timestamp)


def test_set_target_entity_and_get_parent_none():
    source = uuid4()
    target1 = uuid4()
    target2 = uuid4()
    event = Event(event_type=EventType.MOVEMENT, source_entity_uuid=source, target_entity_uuid=target1)
    event.set_target_entity(target2)
    assert event.target_entity_uuid == target2
    assert event.get_parent_event() is None


def test_get_children_events_returns_instances():
    source = uuid4()
    target = uuid4()
    parent = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    child = Event(event_type=EventType.DICE_ROLL, source_entity_uuid=source, target_entity_uuid=target)
    child.set_parent_event(parent)
    EventQueue.register(child)
    stored_parent = EventQueue.get_event_by_uuid(parent.uuid)
    children = stored_parent.get_children_events()
    assert child in children


def test_phase_to_after_completion_returns_self():
    source = uuid4()
    target = uuid4()
    event = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    completed = event.phase_to(EventPhase.EXECUTION).phase_to(EventPhase.EFFECT).phase_to(EventPhase.COMPLETION)
    assert completed.phase == EventPhase.COMPLETION
    assert completed.phase_to() is completed


def test_event_get_history_method():
    source = uuid4()
    target = uuid4()
    event = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    progressed = event.phase_to(EventPhase.EXECUTION)
    history = progressed.get_history()
    assert history == [event]


def test_event_post_raises_type_error_on_wrong_type():
    source = uuid4()
    target = uuid4()

    def processor(evt, _):
        return Event(
            event_type=EventType.ATTACK,
            source_entity_uuid=evt.source_entity_uuid,
            target_entity_uuid=evt.target_entity_uuid,
            modified=True,
        )

    trigger = Trigger(
        event_type=EventType.SAVING_THROW,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=source,
        trigger_conditions=[trigger],
        event_processor=processor,
    )

    event = SavingThrowEvent(ability_name="strength", source_entity_uuid=source, target_entity_uuid=target)
    EventQueue.add_event_handler(EventType.SAVING_THROW, EventPhase.DECLARATION, source, handler)
    with pytest.raises(TypeError):
        event.post(status_message="oops")


def test_trigger_equality_and_call_branches():
    source = uuid4()
    target = uuid4()
    other = uuid4()
    event = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)

    trigger = Trigger(
        event_type=EventType.ATTACK,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )

    assert trigger != 5

    source_mismatch = Trigger(
        event_type=EventType.ATTACK,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=other,
        event_target_entity_uuid=target,
    )
    assert source_mismatch(event) is False

    target_mismatch = Trigger(
        event_type=EventType.ATTACK,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=other,
    )
    assert target_mismatch(event) is False

    type_mismatch = Trigger(
        event_type=EventType.HEAL,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    assert type_mismatch(event) is False

    simple_trigger = Trigger(event_type=EventType.MOVEMENT, event_phase=EventPhase.DECLARATION)
    assert simple_trigger.is_simple()
    st = simple_trigger.get_simple_trigger()
    assert st.event_source_entity_uuid is None and st.event_target_entity_uuid is None


def test_event_handler_call_returns_none():
    source = uuid4()
    target = uuid4()

    trigger = Trigger(
        event_type=EventType.MOVEMENT,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=target,
        trigger_conditions=[trigger],
        event_processor=lambda e, _: e,
    )
    non_matching = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    assert handler(non_matching, source) is None


def test_event_handler_remove():
    source = uuid4()

    from typing import Dict, ClassVar

    class DummyEntity(BaseObject):
        event_handlers: ClassVar[Dict[UUID, EventHandler]] = {}

        def remove_event_handler_from_dicts(self, event_handler):
            self.event_handlers.pop(event_handler.uuid, None)

    entity = DummyEntity(source_entity_uuid=source, target_entity_uuid=source)

    trigger = Trigger(event_type=EventType.ATTACK, event_phase=EventPhase.DECLARATION)
    handler = EventHandler(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        trigger_conditions=[trigger],
        event_processor=lambda e, _: e,
    )

    # not registered
    assert handler.remove() is False

    EventQueue.add_event_handler(EventType.ATTACK, EventPhase.DECLARATION, entity.uuid, handler)
    entity.event_handlers[handler.uuid] = handler
    assert handler.remove() is True
    assert handler.uuid not in entity.event_handlers


def test_register_stops_on_none_from_handler():
    source = uuid4()
    target = uuid4()

    def processor(evt, _):
        return None

    trigger = Trigger(
        event_type=EventType.HEAL,
        event_phase=EventPhase.DECLARATION,
        event_source_entity_uuid=source,
        event_target_entity_uuid=target,
    )
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=target,
        trigger_conditions=[trigger],
        event_processor=processor,
    )
    EventQueue.add_event_handler(EventType.HEAL, EventPhase.DECLARATION, source, handler)
    event = Event(event_type=EventType.HEAL, source_entity_uuid=source, target_entity_uuid=target)
    assert EventQueue.get_event_by_uuid(event.uuid) is event


def test_simple_trigger_registration_and_lookup():
    source = uuid4()

    def processor(evt, _):
        evt.status_message = "simple"
        return evt

    trigger = Trigger(event_type=EventType.ATTACK, event_phase=EventPhase.DECLARATION)
    handler = EventHandler(
        source_entity_uuid=source,
        target_entity_uuid=source,
        trigger_conditions=[trigger],
        event_processor=processor,
    )
    EventQueue.add_event_handler(EventType.ATTACK, EventPhase.DECLARATION, source, handler)
    key = trigger.get_simple_trigger()
    assert handler in EventQueue._event_handlers_by_simple_trigger[key]

    class SimpleEvent(Event):
        def get_trigger(self) -> Trigger:  # type: ignore[override]
            return Trigger(event_type=self.event_type, event_phase=self.phase)

    event = SimpleEvent(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=uuid4())
    assert event.status_message == "simple"
    EventQueue.remove_event_handler(handler)
    assert handler not in EventQueue._event_handlers_by_simple_trigger[key]


def test_chronological_filtering_and_missing_history():
    source = uuid4()
    target = uuid4()
    first = Event(event_type=EventType.MOVEMENT, source_entity_uuid=source, target_entity_uuid=target)
    second = Event(event_type=EventType.ATTACK, source_entity_uuid=source, target_entity_uuid=target)
    third = second.phase_to(EventPhase.EXECUTION)

    filtered = EventQueue.get_events_chronological(start_time=second.timestamp, end_time=third.timestamp)
    assert filtered == [second, third]
    assert EventQueue.get_events_chronological(start_time=second.timestamp) == [second, third]
    assert EventQueue.get_events_chronological(end_time=second.timestamp) == [first, second]
    assert EventQueue.get_event_history(uuid4()) == []


def test_d20_get_dc_and_range_str():
    source = uuid4()
    target = uuid4()
    dc_value = ModifiableValue.create(source_entity_uuid=source, base_value=12, value_name="DC")
    d20 = D20Event(event_type=EventType.DICE_ROLL, source_entity_uuid=source, target_entity_uuid=target, dc=dc_value)
    assert d20.get_dc() == dc_value.normalized_score

    d20_none = D20Event(event_type=EventType.DICE_ROLL, source_entity_uuid=source, target_entity_uuid=target)
    assert d20_none.get_dc() is None
    d20_int = D20Event(event_type=EventType.DICE_ROLL, source_entity_uuid=source, target_entity_uuid=target, dc=15)
    assert d20_int.get_dc() == 15

    reach = Range(type=RangeType.REACH, normal=5)
    assert str(reach) == "5 ft."
    ranged = Range(type=RangeType.RANGE, normal=20, long=60)
    assert str(ranged) == "20/60 ft."

    bonus = ModifiableValue.create(source_entity_uuid=source, base_value=0, value_name="bonus")
    dmg = Damage(
        damage_dice=6,
        dice_numbers=2,
        damage_type=DamageType.ACID,
        damage_bonus=bonus,
        source_entity_uuid=source,
        target_entity_uuid=target,
    )
    dice = dmg.get_dice(AttackOutcome.HIT)
    assert dice.count == 2 and dice.value == 6 and dice.bonus is bonus

