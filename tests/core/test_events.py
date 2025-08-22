from uuid import uuid4

from dnd.core.events import (
    Event,
    EventType,
    EventPhase,
    EventQueue,
    EventHandler,
    Trigger,
)


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

