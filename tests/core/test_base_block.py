import os
import sys
from uuid import UUID, uuid4

from pydantic import Field
import pytest
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dnd.core.base_block import BaseBlock
from dnd.core.values import ModifiableValue
from dnd.core.modifiers import NumericalModifier, BaseObject
from dnd.core.events import EventHandler, Trigger, EventType, EventPhase, EventQueue
from dnd.core.base_conditions import BaseCondition


def test_create_register_unregister():
    BaseBlock._registry.clear()
    source_uuid = uuid4()
    block = BaseBlock.create(source_entity_uuid=source_uuid, name="test")
    assert BaseBlock.get(block.uuid) is block
    BaseBlock.unregister(block.uuid)
    assert BaseBlock.get(block.uuid) is None
    # manual register and erroneous retrieval
    BaseBlock.register(block)
    assert BaseBlock.get(block.uuid) is block
    # insert non-BaseBlock and ensure get raises
    mv = ModifiableValue.create(source_entity_uuid=source_uuid, base_value=1, value_name="mv")
    BaseBlock._registry[mv.uuid] = mv
    with pytest.raises(ValueError, match="is not a BaseBlock"):
        BaseBlock.get(mv.uuid)
    BaseBlock._registry.pop(mv.uuid, None)


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
    assert outer.get_value_from_name("missing") is None
    assert outer.get_block_from_name("missing") is None


def test_initial_context_target_propagation():
    BaseBlock._registry.clear()
    source_uuid = uuid4()
    target_uuid = uuid4()
    ctx = {"k": 1}

    class Inner(BaseBlock):
        inner: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid, base_value=1, value_name="inner"
            )
        )

    class Outer(BaseBlock):
        child: Inner = Field(
            default_factory=lambda: Inner.create(source_entity_uuid=source_uuid, name="inner")
        )
        root: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid, base_value=2, value_name="root"
            )
        )

    outer = Outer(
        source_entity_uuid=source_uuid,
        target_entity_uuid=target_uuid,
        context=ctx,
        name="outer",
    )
    outer.set_values_and_blocks_source()

    assert outer.root.context == ctx
    assert outer.child.context == ctx
    assert outer.child.inner.context == ctx
    assert outer.root.target_entity_uuid == target_uuid
    assert outer.child.target_entity_uuid == target_uuid
    assert outer.child.inner.target_entity_uuid == target_uuid


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


def test_validate_values_and_blocks_source_and_target_errors():
    BaseBlock._registry.clear()
    source_uuid = uuid4()
    block = BaseBlock.create(source_entity_uuid=source_uuid, name="root")

    mv = ModifiableValue.create(
        source_entity_uuid=uuid4(), base_value=1, value_name="mv"
    )
    block.values[mv.uuid] = mv
    with pytest.raises(ValueError, match="ModifiableValue 'mv' has mismatched source UUID"):
        block.validate_values_and_blocks_source_and_target()

    block.values.clear()
    sub_block = BaseBlock.create(source_entity_uuid=uuid4(), name="sub")
    block.blocks[sub_block.uuid] = sub_block
    with pytest.raises(ValueError, match="BaseBlock 'sub' has mismatched source UUID"):
        block.validate_values_and_blocks_source_and_target()


def test_deep_get_values_blocks_and_set_position():
    BaseBlock._registry.clear()
    source_uuid = uuid4()

    class Inner(BaseBlock):
        inner_val: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid, base_value=3, value_name="inner"
            )
        )

    class Middle(BaseBlock):
        mid_val: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid, base_value=2, value_name="middle"
            )
        )
        child: Inner = Field(
            default_factory=lambda: Inner.create(
                source_entity_uuid=source_uuid, name="inner_block"
            )
        )

    class Outer(BaseBlock):
        out_val: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid, base_value=1, value_name="outer"
            )
        )
        child: Middle = Field(
            default_factory=lambda: Middle.create(
                source_entity_uuid=source_uuid, name="mid_block"
            )
        )

    outer = Outer.create(source_entity_uuid=source_uuid, name="outer_block")

    assert [v.name for v in outer.get_values()] == ["outer"]
    assert {v.name for v in outer.get_values(deep=True)} == {"outer", "middle", "inner"}

    blocks = outer.get_blocks()
    assert len(blocks) == 1 and blocks[0].name == "mid_block"
    assert [b.name for b in blocks[0].get_blocks()] == ["inner_block"]

    outer.set_position((10, 20))
    assert outer.position == (10, 20)
    assert outer.child.position == (10, 20)
    assert outer.child.child.position == (10, 20)


def test_target_entity_validation_and_clear_methods():
    BaseBlock._registry.clear()
    source_uuid = uuid4()

    class Inner(BaseBlock):
        val: ModifiableValue = Field(
            default_factory=lambda: ModifiableValue.create(
                source_entity_uuid=source_uuid, base_value=1, value_name="val"
            )
        )

    class Outer(BaseBlock):
        child: Inner = Field(
            default_factory=lambda: Inner.create(
                source_entity_uuid=source_uuid, name="inner"
            )
        )

    block = Outer.create(source_entity_uuid=source_uuid, name="outer")

    with pytest.raises(ValueError):
        block.set_target_entity("not-a-uuid")

    target = uuid4()
    block.set_target_entity(target, "Target")
    ctx = {"foo": "bar"}
    block.set_context(ctx)

    assert block.target_entity_uuid == target
    assert block.child.target_entity_uuid == target
    assert block.child.val.target_entity_uuid == target
    assert block.context == ctx and block.child.context == ctx

    block.clear_target_entity()
    assert block.target_entity_uuid is None
    assert block.child.target_entity_uuid is None
    assert block.child.val.target_entity_uuid is None

    block.clear_context()
    assert block.context is None
    assert block.child.context is None
    assert block.child.val.context is None


def test_event_handlers_conditions_and_immunities():
    BaseBlock._registry.clear()
    EventQueue._event_handlers.clear()
    EventQueue._event_handlers_by_trigger.clear()
    EventQueue._event_handlers_by_simple_trigger.clear()
    EventQueue._event_handlers_by_source_entity_uuid.clear()

    source_uuid = uuid4()
    target_uuid = uuid4()

    class EntityBlock(BaseBlock, BaseObject):
        @classmethod
        def create(cls, source_entity_uuid: UUID, name: str = "block") -> "EntityBlock":
            return cls(
                source_entity_uuid=source_entity_uuid,
                target_entity_uuid=target_uuid,
                name=name,
            )

    block = EntityBlock.create(source_uuid)
    BaseObject.register(block)
    block.allow_events_conditions = True
    block.event_handlers_by_trigger = defaultdict(list)
    block.event_handlers_by_simple_trigger = defaultdict(list)

    def processor(evt, _):
        return evt

    trigger = Trigger(
        event_type=EventType.ATTACK,
        event_phase=EventPhase.DECLARATION,
    )
    handler = EventHandler(
        source_entity_uuid=block.uuid,
        target_entity_uuid=target_uuid,
        trigger_conditions=[trigger],
        event_processor=processor,
    )

    block.add_event_handler(handler)
    assert block.event_handlers[handler.uuid] is handler
    assert block.event_handlers_by_trigger[trigger] == [handler]
    assert block.event_handlers_by_simple_trigger[trigger] == [handler]

    EventQueue.add_event_handler(None, None, block.uuid, handler)
    block.remove_event_handler(handler)
    assert handler.uuid not in block.event_handlers
    assert block.event_handlers_by_trigger[trigger] == []
    assert block.event_handlers_by_simple_trigger[trigger] == []
    assert handler.uuid not in EventQueue._event_handlers

    class DummyCondition(BaseCondition):
        def _apply(self, declaration_event):
            _, _, _, event = super()._apply(declaration_event)
            return [], [], [], event

    condition = DummyCondition(
        name="Stunned",
        source_entity_uuid=source_uuid,
        target_entity_uuid=block.uuid,
    )

    block.add_condition(condition)
    assert block.active_conditions["Stunned"] is condition
    assert block.active_conditions_by_uuid[condition.uuid] is condition
    assert block.active_conditions_by_source[source_uuid] == ["Stunned"]

    block.remove_condition("Stunned")
    assert block.active_conditions == {}
    assert block.active_conditions_by_source[source_uuid] == []

    block.add_condition_immunity("Poison")
    assert ("Poison", None) in block.condition_immunities

    block.add_condition_immunity(
        "Fear", "Brave", lambda *_: True
    )
    assert "Fear" in block.contextual_condition_immunities

    block.remove_condition_immunity("Poison")
    block.remove_condition_immunity("Fear")
    assert block.condition_immunities == []
    assert block.contextual_condition_immunities == {}


def test_event_condition_methods_noop_when_disabled():
    BaseBlock._registry.clear()
    source_uuid = uuid4()
    target_uuid = uuid4()

    block = BaseBlock.create(source_uuid, name="blk")
    trigger = Trigger(event_type=EventType.ATTACK, event_phase=EventPhase.DECLARATION)

    def processor(evt, _):
        return evt

    handler = EventHandler(
        source_entity_uuid=source_uuid,
        target_entity_uuid=target_uuid,
        trigger_conditions=[trigger],
        event_processor=processor,
    )

    # all methods should noop when allow_events_conditions is False
    block.add_event_handler(handler)
    assert block.event_handlers == {}
    block.remove_event_handler_from_dicts(handler)
    block.remove_event_handler(handler)

    class DummyCondition(BaseCondition):
        def _apply(self, declaration_event):
            return [], [], [], declaration_event

    cond = DummyCondition(name="Cond", source_entity_uuid=source_uuid, target_entity_uuid=block.uuid)
    block.add_condition(cond)
    assert block.active_conditions == {}
    block._remove_condition_from_dicts(cond)
    block.remove_condition("Cond")

    block.add_static_condition_immunity("Poison")
    block._remove_static_condition_immunity("Poison")
    block.add_contextual_condition_immunity("Sleep", "Elf", lambda *_: True)
    block._remove_contextual_condition_immunity("Sleep")
    block.remove_condition_immunity("Poison")


def test_add_condition_branches_and_immunity_removal():
    BaseBlock._registry.clear()
    source_uuid = uuid4()
    block = BaseBlock.create(source_uuid, name="blk")
    block.allow_events_conditions = True

    class DummyCondition(BaseCondition):
        def _apply(self, declaration_event):
            return [], [], [], declaration_event

    # missing name
    nameless = DummyCondition(name=None, source_entity_uuid=source_uuid, target_entity_uuid=block.uuid)
    with pytest.raises(ValueError):
        block.add_condition(nameless)

    # context and target assignment
    ctx = {"x": 1}
    cond = DummyCondition(name="Test", source_entity_uuid=source_uuid, target_entity_uuid=None)
    block.add_condition(cond, context=ctx)
    assert cond.target_entity_uuid == block.uuid
    assert cond.context == ctx

    # duplicate condition
    c1 = DummyCondition(name="Dup", source_entity_uuid=source_uuid, target_entity_uuid=block.uuid)
    c2 = DummyCondition(name="Dup", source_entity_uuid=source_uuid, target_entity_uuid=block.uuid)
    block.add_condition(c1)
    block.add_condition(c2)
    assert block.active_conditions["Dup"] is c2
    assert block.active_conditions_by_source[source_uuid].count("Dup") == 1

    # subcondition removal
    child = DummyCondition(name="Child", source_entity_uuid=source_uuid, target_entity_uuid=block.uuid)
    parent = DummyCondition(name="Parent", source_entity_uuid=source_uuid, target_entity_uuid=block.uuid, sub_conditions=[child.uuid])
    block.add_condition(child)
    block.add_condition(parent)
    block.remove_condition("Parent")
    assert "Child" not in block.active_conditions

    # condition immunities specifics
    block.add_condition_immunity("Charm", "Amulet")
    block._remove_static_condition_immunity("Charm", "Amulet")
    block.add_condition_immunity("Sleep", "Elf", lambda *_: True)
    block._remove_contextual_condition_immunity("Sleep", "Elf")

    with pytest.raises(ValueError):
        block.add_condition_immunity("Fear", immunity_check=lambda *_: True)
