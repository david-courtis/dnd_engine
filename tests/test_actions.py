from uuid import uuid4
import os
import sys

# Ensure repository root is on the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dnd.entity import Entity
from dnd.actions import (
    validate_line_of_sight,
    entity_action_economy_cost_evaluator,
    entity_action_economy_cost_applier,
)
from dnd.core.base_actions import ActionEvent, Cost
from dnd.core.events import EventType, EventPhase


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


def test_entity_action_economy_cost_evaluator_insufficient_resources():
    entity = Entity.create(uuid4())
    assert entity_action_economy_cost_evaluator(entity.uuid, "actions", 1)
    assert not entity_action_economy_cost_evaluator(entity.uuid, "actions", 2)


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