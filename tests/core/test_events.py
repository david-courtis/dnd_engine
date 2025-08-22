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

    event = Event(event_type=EventType.MOVEMENT, source_entity_uuid=source, target_entity_uuid=target)
    updated = EventQueue.get_events_by_type(EventType.MOVEMENT)[-1]
    assert updated.phase == EventPhase.EFFECT
    assert updated.status_message == "processed"