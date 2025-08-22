from uuid import uuid4

from dnd.blocks.action_economy import ActionEconomy


def test_action_economy_spend_and_reset():
    ae = ActionEconomy.create(source_entity_uuid=uuid4())
    assert ae.can_afford("actions", 1)
    ae.consume("actions", 1)
    assert not ae.can_afford("actions", 1)
    ae.reset_all_costs()
    assert ae.can_afford("actions", 1)


def test_value_retrieval():
    ae = ActionEconomy.create(source_entity_uuid=uuid4())
    retrieved = ae.get_value_from_name("Actions")
    assert retrieved is ae.actions
