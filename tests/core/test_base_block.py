import os
import sys
from uuid import uuid4

from pydantic import Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dnd.core.base_block import BaseBlock
from dnd.core.values import ModifiableValue


def test_create_register_unregister():
    BaseBlock._registry.clear()
    source_uuid = uuid4()
    block = BaseBlock.create(source_entity_uuid=source_uuid, name="test")
    assert BaseBlock.get(block.uuid) is block
    BaseBlock.unregister(block.uuid)
    assert BaseBlock.get(block.uuid) is None


def test_context_target_propagation_and_getters():
    BaseBlock._registry.clear()
    source_uuid = uuid4()

    class InnerBlock(BaseBlock):
        inner_value: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid,
                base_value=1,
                value_name="inner_value",
            )
        )

    class OuterBlock(BaseBlock):
        root_value: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid,
                base_value=2,
                value_name="root_value",
            )
        )
        child_block: InnerBlock = Field(
            default_factory=lambda: InnerBlock.create(
                source_entity_uuid=source_uuid,
                name="inner_block",
            )
        )

    outer = OuterBlock.create(source_entity_uuid=source_uuid, name="outer_block")

    context = {"foo": "bar"}
    outer.set_context(context)
    assert outer.context == context
    assert outer.root_value.context == context
    assert outer.child_block.context == context
    assert outer.child_block.inner_value.context == context

    outer.clear_context()
    assert outer.context is None
    assert outer.root_value.context is None
    assert outer.child_block.context is None
    assert outer.child_block.inner_value.context is None

    target_uuid = uuid4()
    outer.set_target_entity(target_uuid, "Target")
    assert outer.target_entity_uuid == target_uuid
    assert outer.root_value.target_entity_uuid == target_uuid
    assert outer.child_block.target_entity_uuid == target_uuid
    assert outer.child_block.inner_value.target_entity_uuid == target_uuid

    outer.set_context(context)
    outer.clear()
    assert outer.target_entity_uuid is None and outer.context is None
    assert outer.root_value.target_entity_uuid is None and outer.root_value.context is None
    assert outer.child_block.target_entity_uuid is None and outer.child_block.context is None
    assert (
        outer.child_block.inner_value.target_entity_uuid is None
        and outer.child_block.inner_value.context is None
    )

    assert outer.get_value_from_uuid(outer.root_value.uuid) is outer.root_value
    assert outer.get_value_from_name(outer.root_value.name) is outer.root_value
    assert outer.get_block_from_uuid(outer.child_block.uuid) is outer.child_block
    assert outer.get_block_from_name(outer.child_block.name) is outer.child_block
