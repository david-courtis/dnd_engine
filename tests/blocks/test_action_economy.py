from uuid import uuid4

import pytest

from dnd.blocks.action_economy import ActionEconomy, ActionEconomyConfig


@pytest.mark.parametrize(
    "cost_type, amount",
    [
        ("actions", 1),
        ("bonus_actions", 1),
        ("reactions", 1),
        ("movement", 30),
    ],
)
def test_action_economy_spend_and_reset(cost_type, amount):
    ae = ActionEconomy.create(source_entity_uuid=uuid4())
    assert ae.can_afford(cost_type, amount)
    ae.consume(cost_type, amount, cost_name="test")
    assert not ae.can_afford(cost_type, 1)

    cost_mods = ae.get_cost_modifiers(cost_type)
    assert len(cost_mods) == 1
    assert cost_mods[0].name == "test_cost"
    assert cost_mods[0].value == -amount

    with pytest.raises(ValueError):
        ae.consume(cost_type, 1)

    ae.reset_all_costs()
    assert ae.can_afford(cost_type, amount)
    assert ae.get_cost_modifiers(cost_type) == []


def test_value_retrieval():
    ae = ActionEconomy.create(source_entity_uuid=uuid4())
    retrieved = ae.get_value_from_name("Actions")
    assert retrieved is ae.actions


def test_invalid_cost_types():
    ae = ActionEconomy.create(source_entity_uuid=uuid4())
    with pytest.raises(ValueError):
        ae.get_base_value("invalid")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ae.get_cost_modifiers("invalid")  # type: ignore[arg-type]


def test_action_economy_full_flow():
    config = ActionEconomyConfig(
        actions=1,
        actions_modifiers=[("extra_action", 1)],
        bonus_actions=1,
        bonus_actions_modifiers=[("extra_bonus", 1)],
        reactions=1,
        reactions_modifiers=[("extra_react", 1)],
        movement=30,
        movement_modifiers=[("boots", 10)],
    )
    ae = ActionEconomy.create(source_entity_uuid=uuid4(), config=config)

    # Actions
    assert ae.can_afford("actions", 2)
    ae.consume("actions", 1, cost_name="attack")
    assert ae.actions.self_static.normalized_score == 1
    assert ae.can_afford("actions", 1)
    assert not ae.can_afford("actions", 2)
    with pytest.raises(ValueError):
        ae.consume("actions", 2)
    assert len(ae.get_cost_modifiers("actions")) == 1
    assert ae.get_base_value("actions") == 1

    # Bonus Actions
    assert ae.can_afford("bonus_actions", 2)
    ae.consume("bonus_actions", 1, cost_name="dash")
    assert ae.bonus_actions.self_static.normalized_score == 1
    assert ae.can_afford("bonus_actions", 1)
    assert not ae.can_afford("bonus_actions", 2)
    with pytest.raises(ValueError):
        ae.consume("bonus_actions", 2)
    assert len(ae.get_cost_modifiers("bonus_actions")) == 1
    assert ae.get_base_value("bonus_actions") == 1

    # Reactions
    assert ae.can_afford("reactions", 2)
    ae.consume("reactions", 1, cost_name="opportunity")
    assert ae.reactions.self_static.normalized_score == 1
    assert ae.can_afford("reactions", 1)
    assert not ae.can_afford("reactions", 2)
    with pytest.raises(ValueError):
        ae.consume("reactions", 2)
    assert len(ae.get_cost_modifiers("reactions")) == 1
    assert ae.get_base_value("reactions") == 1

    # Movement
    assert ae.can_afford("movement", 40)
    ae.consume("movement", 35, cost_name="run")
    assert ae.movement.self_static.normalized_score == 5
    assert ae.can_afford("movement", 5)
    assert not ae.can_afford("movement", 10)
    with pytest.raises(ValueError):
        ae.consume("movement", 10)
    assert len(ae.get_cost_modifiers("movement")) == 1
    assert ae.get_base_value("movement") == 30

    # Modifier counts before reset
    assert len(ae.get_cost_modifiers("actions")) == 1
    assert len(ae.get_cost_modifiers("bonus_actions")) == 1
    assert len(ae.get_cost_modifiers("reactions")) == 1
    assert len(ae.get_cost_modifiers("movement")) == 1

    ae.reset_all_costs()

    for cost_type, expected in [
        ("actions", 2),
        ("bonus_actions", 2),
        ("reactions", 2),
        ("movement", 40),
    ]:
        assert ae.get_cost_modifiers(cost_type) == []
        assert ae.can_afford(cost_type, expected)
        value = getattr(ae, cost_type)
        assert value.self_static.normalized_score == expected
