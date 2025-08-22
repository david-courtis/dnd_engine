import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from uuid import uuid4

from dnd.core.values import ModifiableValue
from dnd.core.modifiers import NumericalModifier, ContextualNumericalModifier


def _build_value():
    source_uuid = uuid4()
    mv = ModifiableValue.create(source_entity_uuid=source_uuid, base_value=10, value_name="test")

    # Static modifier
    static_mod = NumericalModifier(
        source_entity_uuid=source_uuid,
        target_entity_uuid=source_uuid,
        value=2,
    )
    mv.self_static.add_value_modifier(static_mod)

    # Contextual modifiers driven by context values
    def bonus(src, tgt, ctx):
        return NumericalModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=ctx.get("bonus", 0),
        )

    def penalty(src, tgt, ctx):
        return NumericalModifier(
            source_entity_uuid=src,
            target_entity_uuid=tgt,
            value=ctx.get("penalty", 0),
        )

    mv.self_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=source_uuid,
            target_entity_uuid=source_uuid,
            callable=bonus,
        )
    )
    mv.self_contextual.add_value_modifier(
        ContextualNumericalModifier(
            source_entity_uuid=source_uuid,
            target_entity_uuid=source_uuid,
            callable=penalty,
        )
    )

    mv.set_context({"bonus": 5, "penalty": -2})
    return mv


def test_modifiable_value_score_with_context():
    mv = _build_value()
    assert mv.score == 15
    assert mv.normalized_score == 15


def test_modifiable_value_to_from_dict_round_trip():
    mv = _build_value()
    mv.update_normalizers()
    data = mv.model_dump()
    rebuilt = ModifiableValue.model_validate(data)
    assert rebuilt.model_dump() == data
    assert rebuilt.score == mv.score