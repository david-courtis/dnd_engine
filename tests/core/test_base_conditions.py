import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from uuid import uuid4

from dnd.core.base_conditions import (
    Duration,
    DurationType,
    BaseCondition,
    ConditionApplicationEvent,
    ConditionRemovalEvent,
)
from dnd.core.events import EventQueue, EventPhase, EventType
from dnd.core.modifiers import BaseObject


@pytest.fixture(autouse=True)
def clear_registries():
    BaseObject._registry.clear()
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
    BaseObject._registry.clear()
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


# ---------------------------------------------------------------------------
# Duration validation and behavior
# ---------------------------------------------------------------------------

def dummy_condition(source, target, context):
    return True


@pytest.mark.parametrize(
    "dtype,value,valid",
    [
        (DurationType.ROUNDS, 1, True),
        (DurationType.ROUNDS, None, False),
        (DurationType.PERMANENT, None, True),
        (DurationType.PERMANENT, 1, False),
        (DurationType.UNTIL_LONG_REST, None, True),
        (DurationType.UNTIL_LONG_REST, 1, False),
    ],
)
def test_duration_validation(dtype, value, valid):
    if valid:
        Duration(duration=value, duration_type=dtype)
    else:
        with pytest.raises(ValueError):
            Duration(duration=value, duration_type=dtype)


def test_duration_on_condition_validation():
    with pytest.raises(TypeError):
        Duration(duration=dummy_condition, duration_type=DurationType.ON_CONDITION)
    with pytest.raises(TypeError):
        Duration(duration=1, duration_type=DurationType.ON_CONDITION)


def test_rounds_duration_initial_not_expired_and_decrements():
    duration = Duration(duration=2, duration_type=DurationType.ROUNDS)
    assert duration.is_expired is False
    assert duration.progress() is False  # one round remaining
    assert duration.is_expired is False
    assert duration.progress() is True  # expires after second round
    assert duration.is_expired is True


def test_duration_progress_and_long_rest():
    rounds = Duration(duration=1, duration_type=DurationType.ROUNDS)
    assert rounds.progress() is True
    assert rounds.is_expired is True

    until_rest = Duration(duration=None, duration_type=DurationType.UNTIL_LONG_REST)
    assert until_rest.is_expired is False
    until_rest.long_rest()
    assert until_rest.is_expired is True


# ---------------------------------------------------------------------------
# BaseCondition application/removal event phases
# ---------------------------------------------------------------------------


class DummyCondition(BaseCondition):
    def _apply(self, declaration_event):
        _, _, _, event = super()._apply(declaration_event)
        return [], [uuid4()], [], event


def test_condition_application_and_removal_phases():
    condition = DummyCondition(
        name="dummy",
        source_entity_uuid=uuid4(),
        target_entity_uuid=uuid4(),
    )

    apply_event = condition.apply()
    assert isinstance(apply_event, ConditionApplicationEvent)
    history = EventQueue.get_event_history(apply_event.uuid)
    assert [e.phase for e in history] == [
        EventPhase.DECLARATION,
        EventPhase.EXECUTION,
        EventPhase.EFFECT,
        EventPhase.COMPLETION,
    ]

    assert condition.remove() is True
    removal_event = EventQueue.get_events_by_type(EventType.CONDITION_REMOVAL)[-1]
    assert isinstance(removal_event, ConditionRemovalEvent)
    removal_history = EventQueue.get_event_history(removal_event.uuid)
    assert [e.phase for e in removal_history] == [
        EventPhase.DECLARATION,
        EventPhase.EXECUTION,
        EventPhase.EFFECT,
        EventPhase.COMPLETION,
    ]


# ---------------------------------------------------------------------------
# Apply/unapply and tick behavior across Duration types
# ---------------------------------------------------------------------------


def _make_condition(duration: Duration) -> DummyCondition:
    return DummyCondition(
        name="dummy",
        source_entity_uuid=uuid4(),
        target_entity_uuid=uuid4(),
        duration=duration,
    )


def test_rounds_duration_apply_tick_and_expire():
    condition = _make_condition(Duration(duration=2, duration_type=DurationType.ROUNDS))

    assert isinstance(condition.apply(), ConditionApplicationEvent)
    assert condition.applied is True

    assert condition.progress() is False  # 1 round left
    assert condition.duration.duration == 1

    assert condition.progress() is True  # expires and removes
    assert condition.applied is False
    removal_event = EventQueue.get_events_by_type(EventType.CONDITION_REMOVAL)[-1]
    assert removal_event.expired is True


def test_permanent_duration_apply_unapply_and_tick():
    condition = _make_condition(Duration(duration=None, duration_type=DurationType.PERMANENT))

    condition.apply()
    assert condition.applied is True
    assert condition.progress() is False  # no expiration

    assert condition.remove() is True
    assert condition.applied is False
    removal_event = EventQueue.get_events_by_type(EventType.CONDITION_REMOVAL)[-1]
    assert removal_event.expired is False


def test_on_condition_duration_apply_tick_and_manual_unapply(monkeypatch):
    import collections.abc
    monkeypatch.setattr(
        "dnd.core.base_conditions.ContextAwareCondition", collections.abc.Callable
    )

    trigger = {"expired": False}

    def end_condition(source, target, context):
        return context["expired"]

    duration = Duration(
        duration=end_condition,
        duration_type=DurationType.ON_CONDITION,
        context=trigger,
    )

    condition = _make_condition(duration)

    condition.apply()
    assert condition.applied is True
    assert condition.progress() is False

    trigger["expired"] = True
    assert end_condition(None, None, trigger) is True
    assert condition.progress() is False  # does not auto-remove
    assert condition.applied is True

    assert condition.remove(expire=True) is True
    removal_event = EventQueue.get_events_by_type(EventType.CONDITION_REMOVAL)[-1]
    assert removal_event.expired is True
