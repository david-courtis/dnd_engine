from collections import OrderedDict
from uuid import uuid4

from dnd.core.base_actions import BaseAction, StructuredAction, Cost
from dnd.core.events import EventQueue, EventType, EventPhase


def test_action_cost_check_prevents_apply_when_failing():
    def evaluator(source, cost_type, amount):
        return False

    action = BaseAction(
        name="TestAction",
        description="desc",
        source_entity_uuid=uuid4(),
        target_entity_uuid=uuid4(),
        costs=[Cost(cost_type="actions", cost=1, evaluator=evaluator)],
    )
    assert action.apply() is None
    assert EventQueue.get_events_by_type(EventType.BASE_ACTION) == []


def test_structured_action_runs_pipeline():
    calls = []

    def cost_check(source, cost_type, amount):
        calls.append("cost_check")
        return True

    def prereq(event, source_uuid):
        calls.append("prereq")
        return event

    def consequence(event, source_uuid):
        calls.append("consequence")
        return event

    def cost_apply(event, source_uuid):
        calls.append("cost_apply")
        return event

    action = StructuredAction(
        name="Structured",
        description="desc",
        source_entity_uuid=uuid4(),
        target_entity_uuid=uuid4(),
        costs=[Cost(cost_type="actions", cost=1, evaluator=cost_check)],
        prerequisites=OrderedDict([("p", prereq)]),
        consequences=OrderedDict([("c", consequence)]),
        cost_applier=cost_apply,
        revalidate_prerequisites=False,
    )

    final_event = action.apply()
    assert calls == ["cost_check", "prereq", "consequence", "cost_apply"]
    assert final_event.phase == EventPhase.COMPLETION


def test_structured_action_failing_prerequisite_cancels():
    def fail_prereq(event, source_uuid):
        return None

    action = StructuredAction(
        name="Failing",
        description="desc",
        source_entity_uuid=uuid4(),
        target_entity_uuid=uuid4(),
        prerequisites=OrderedDict([("fail", fail_prereq)]),
        consequences=OrderedDict(),
        revalidate_prerequisites=False,
    )

    result = action.apply()
    assert result.canceled is True
    assert result.phase == EventPhase.CANCEL