import os
import sys
from uuid import UUID, uuid4

from pydantic import Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dnd.core.base_block import BaseBlock
from dnd.core.values import ModifiableValue
from dnd.core.modifiers import NumericalModifier


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


def test_block_channels_clone_toggle_and_serialization():
    BaseBlock._registry.clear()
    source_uuid = uuid4()

    class SimpleBlock(BaseBlock):
        value: ModifiableValue

        @classmethod
        def create(
            cls,
            source_entity_uuid: UUID,
            source_entity_name: str | None = None,
            target_entity_uuid: UUID | None = None,
            target_entity_name: str | None = None,
            name: str = "simple",
        ) -> "SimpleBlock":
            mv = ModifiableValue.create(
                source_entity_uuid=source_entity_uuid,
                source_entity_name=source_entity_name,
                target_entity_uuid=target_entity_uuid,
                target_entity_name=target_entity_name,
                base_value=5,
                value_name="test_value",
            )
            return cls(
                source_entity_uuid=source_entity_uuid,
                source_entity_name=source_entity_name,
                target_entity_uuid=target_entity_uuid,
                target_entity_name=target_entity_name,
                name=name,
                value=mv,
            )

    block = SimpleBlock.create(source_entity_uuid=source_uuid, name="block")

    mv = block.value
    assert mv.self_static.score == 5
    assert mv.to_target_static.score == 0
    assert mv.self_contextual.score == 0
    assert mv.to_target_contextual.score == 0

    block.add_condition_immunity("Fear")
    assert block.condition_immunities == []
    block.allow_events_conditions = True
    block.add_condition_immunity("Fear")
    assert ("Fear", None) in block.condition_immunities
    block.allow_events_conditions = False
    block.add_condition_immunity("Poison")
    assert all(name != "Poison" for name, _ in block.condition_immunities)

    clone = block.model_copy(deep=True)
    assert clone is not block and clone.value is not block.value
    assert clone.value.score == mv.score

    modifier = NumericalModifier(
        source_entity_uuid=source_uuid,
        target_entity_uuid=source_uuid,
        value=3,
    )
    clone.value.self_static.add_value_modifier(modifier)
    assert clone.value.score == mv.score + 3
    assert block.value.score == mv.score

    clone.value.self_static.remove_modifier(modifier.uuid)
    assert clone.value.score == mv.score

    state = clone.model_dump()
    assert state["value"]["self_static"]["value_modifiers"]
    assert clone.value.model_dump()["self_static"]["value_modifiers"]
