from uuid import uuid4

import pytest

from dnd.blocks.action_economy import ActionEconomy


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
