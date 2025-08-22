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
