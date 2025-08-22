import pytest
from uuid import uuid4

from dnd.core.values import StaticValue
from dnd.core.modifiers import NumericalModifier, BaseObject


@pytest.fixture(autouse=True)
def clear_registry():
    BaseObject._registry.clear()
    yield
    BaseObject._registry.clear()


def test_validate_modifier_target_non_outgoing():
    source = uuid4()
    target = uuid4()
    value = StaticValue(source_entity_uuid=source, target_entity_uuid=target)

    good = NumericalModifier(source_entity_uuid=source, target_entity_uuid=source, value=1)
    value.validate_modifier_target(good)

    bad = NumericalModifier(source_entity_uuid=source, target_entity_uuid=target, value=1)
    with pytest.raises(ValueError):
        value.validate_modifier_target(bad)


def test_validate_modifier_target_outgoing():
    source = uuid4()
    target = uuid4()
    value = StaticValue(source_entity_uuid=source, target_entity_uuid=target, is_outgoing_modifier=True)

    good = NumericalModifier(source_entity_uuid=source, target_entity_uuid=target, value=1)
    value.validate_modifier_target(good)

    bad = NumericalModifier(source_entity_uuid=source, target_entity_uuid=source, value=1)
    with pytest.raises(ValueError):
        value.validate_modifier_target(bad)
