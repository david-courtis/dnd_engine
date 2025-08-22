import sys
from pathlib import Path

import pytest
from uuid import uuid4
from pydantic import ValidationError
from types import SimpleNamespace

# Ensure the repository root is on the import path for namespace packages
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.action_economy import ActionEconomySnapshot
from app.models.abilities import AbilitySnapshot, AbilityScoresSnapshot
from app.models.values import ModifiableValueSnapshot
from app.models.equipment import (
    AttackBonusCalculationSnapshot,
    RangeSnapshot,
    EquipmentSnapshot,
    ACBonusCalculationSnapshot,
)
from app.models.entity import EntitySummary, EntitySnapshot
from app.models.sensory import SensesSnapshot
from app.models.skills import SkillSetSnapshot, SkillBonusCalculationSnapshot
from app.models.health import HealthSnapshot
from app.models.action_economy import ActionEconomySnapshot
from app.models.saving_throws import SavingThrowSetSnapshot, SavingThrowBonusCalculationSnapshot

from dnd.core.modifiers import (
    AdvantageStatus,
    CriticalStatus,
    AutoHitStatus,
    DamageType,
    ResistanceStatus,
)
from dnd.core.events import RangeType, WeaponSlot, SkillName
from dnd.core.base_conditions import DurationType

class DummyNumericalModifier:
    """Minimal stand-in for a NumericalModifier."""

    def __init__(self, value: int):
        self.uuid = uuid4()
        self.name = "modifier"
        self.source_entity_uuid = uuid4()
        self.source_entity_name = None
        self.target_entity_uuid = None
        self.target_entity_name = None
        self.value = value
        self.normalized_value = value


class DummyModifiableValue:
    """Minimal stand-in for a ModifiableValue."""

    def __init__(self, score: int, normalized: int | None = None):
        self.uuid = uuid4()
        self.name = "value"
        self.source_entity_uuid = uuid4()
        self.source_entity_name = None
        self.target_entity_uuid = None
        self.target_entity_name = None
        self.score = score
        self.normalized_score = normalized if normalized is not None else score
        self.min = None
        self.max = None
        self.advantage = AdvantageStatus.NONE
        self.outgoing_advantage = AdvantageStatus.NONE
        self.critical = CriticalStatus.NONE
        self.outgoing_critical = CriticalStatus.NONE
        self.auto_hit = AutoHitStatus.NONE
        self.outgoing_auto_hit = AutoHitStatus.NONE
        self.resistance = {}


class DummyActionEconomy:
    """Lightweight stand-in for the engine ActionEconomy object."""

    def __init__(self):
        self.uuid = uuid4()
        self.name = "ActionEconomy"
        self.source_entity_uuid = uuid4()
        self.source_entity_name = "Tester"
        self.actions = DummyModifiableValue(1)
        self.bonus_actions = DummyModifiableValue(1)
        self.reactions = DummyModifiableValue(1)
        self.movement = DummyModifiableValue(30)
        self._base_values = {
            "actions": 1,
            "bonus_actions": 1,
            "reactions": 1,
            "movement": 30,
        }
        self._cost_mods = {
            "actions": [DummyNumericalModifier(1)],
            "bonus_actions": [DummyNumericalModifier(1)],
            "reactions": [DummyNumericalModifier(1)],
            "movement": [DummyNumericalModifier(5)],
        }

    def get_base_value(self, key: str) -> int:
        return self._base_values[key]

    def get_cost_modifiers(self, key: str):
        return self._cost_mods[key]


def make_modifier(**kwargs):
    base = {
        "uuid": uuid4(),
        "name": "mod",
        "source_entity_uuid": uuid4(),
        "source_entity_name": "source",
        "target_entity_uuid": uuid4(),
        "target_entity_name": "target",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class DummyStaticChannel:
    def __init__(self):
        self.is_outgoing_modifier = False
        self.value_modifiers = {"v": DummyNumericalModifier(1)}
        self.min_constraints = {"min": DummyNumericalModifier(0)}
        self.max_constraints = {"max": DummyNumericalModifier(10)}
        self.advantage_modifiers = {}
        self.critical_modifiers = {}
        self.auto_hit_modifiers = {}
        self.size_modifiers = {}
        self.resistance_modifiers = {
            "res": make_modifier(
                value=ResistanceStatus.RESISTANCE,
                damage_type=DamageType.ACID,
                numerical_value=1,
            )
        }
        self.score = 5
        self.normalized_score = 5
        self.min = 0
        self.max = 10


class DummyContextualWrapper:
    def __init__(self, result):
        self.callable = lambda s, t, c: result


class DummyContextualChannel:
    def __init__(self):
        self.is_outgoing_modifier = True
        self.source_entity_uuid = uuid4()
        self.target_entity_uuid = uuid4()
        self.context = {}
        self.value_modifiers = {
            "v": DummyContextualWrapper(DummyNumericalModifier(2))
        }
        self.min_constraints = {
            "min": DummyContextualWrapper(DummyNumericalModifier(1))
        }
        self.max_constraints = {
            "max": DummyContextualWrapper(DummyNumericalModifier(9))
        }
        self.advantage_modifiers = {}
        self.critical_modifiers = {}
        self.auto_hit_modifiers = {}
        self.size_modifiers = {}
        self.resistance_modifiers = {
            "res": DummyContextualWrapper(
                make_modifier(
                    value=ResistanceStatus.IMMUNITY,
                    damage_type=DamageType.COLD,
                    numerical_value=0,
                )
            )
        }
        self.score = 3
        self.normalized_score = 3
        self.min = 1
        self.max = 9


class MockModifiableValue:
    """Engine-like ModifiableValue with channels and constraints."""

    def __init__(self):
        self.uuid = uuid4()
        self.name = "value"
        self.source_entity_uuid = uuid4()
        self.source_entity_name = "source"
        self.target_entity_uuid = uuid4()
        self.target_entity_name = "target"
        self.score = 5
        self.normalized_score = 5
        self.min = 0
        self.max = 10
        self.advantage = AdvantageStatus.NONE
        self.outgoing_advantage = AdvantageStatus.NONE
        self.critical = CriticalStatus.NONE
        self.outgoing_critical = CriticalStatus.NONE
        self.auto_hit = AutoHitStatus.NONE
        self.outgoing_auto_hit = AutoHitStatus.NONE
        self.resistance = {DamageType.ACID: ResistanceStatus.RESISTANCE}
        self.self_static = DummyStaticChannel()
        self.self_contextual = DummyContextualChannel()

    def get_base_modifier(self):
        return DummyNumericalModifier(3)


def make_value(score: int, normalized: int | None = None) -> ModifiableValueSnapshot:
    """Helper to create a minimal ModifiableValueSnapshot."""
    return ModifiableValueSnapshot(
        uuid=uuid4(),
        name="value",
        source_entity_uuid=uuid4(),
        score=score,
        normalized_score=normalized if normalized is not None else score,
        advantage=AdvantageStatus.NONE,
        outgoing_advantage=AdvantageStatus.NONE,
        critical=CriticalStatus.NONE,
        outgoing_critical=CriticalStatus.NONE,
        auto_hit=AutoHitStatus.NONE,
        outgoing_auto_hit=AutoHitStatus.NONE,
    )


def make_engine_value(score: int, normalized: int | None = None):
    """Create a minimal engine-like modifiable value object."""
    return SimpleNamespace(
        uuid=uuid4(),
        name="value",
        source_entity_uuid=uuid4(),
        source_entity_name=None,
        target_entity_uuid=None,
        target_entity_name=None,
        score=score,
        normalized_score=normalized if normalized is not None else score,
        min=0,
        max=20,
        advantage=AdvantageStatus.NONE,
        outgoing_advantage=AdvantageStatus.NONE,
        critical=CriticalStatus.NONE,
        outgoing_critical=CriticalStatus.NONE,
        auto_hit=AutoHitStatus.NONE,
        outgoing_auto_hit=AutoHitStatus.NONE,
        resistance={},
    )


def make_engine_ability(name: str, score: int, bonus: int = 0):
    ability_score = make_engine_value(score)
    modifier_bonus = make_engine_value(bonus)
    modifier = (ability_score.normalized_score - 10) // 2 + modifier_bonus.normalized_score
    return SimpleNamespace(
        uuid=uuid4(),
        name=name,
        ability_score=ability_score,
        modifier_bonus=modifier_bonus,
        modifier=modifier,
    )


def test_ability_snapshot_valid_and_computed():
    ability_score = make_value(15)
    modifier_bonus = make_value(1)
    expected = (ability_score.normalized_score - 10) // 2 + modifier_bonus.normalized_score
    ability = AbilitySnapshot(
        uuid=uuid4(),
        name="strength",
        ability_score=ability_score,
        modifier_bonus=modifier_bonus,
        modifier=expected,
    )
    assert ability.modifier == expected


def test_ability_snapshot_model_validate_error():
    ability_score = make_value(10).model_dump()
    modifier_bonus = make_value(0).model_dump()
    data = {
        "uuid": "not-a-uuid",
        "name": "strength",
        "ability_score": ability_score,
        "modifier_bonus": modifier_bonus,
        "modifier": 0,
    }
    with pytest.raises(ValidationError):
        AbilitySnapshot.model_validate(data)


def test_ability_scores_snapshot_defaults():
    def ability(name: str) -> AbilitySnapshot:
        score = make_value(10)
        return AbilitySnapshot(
            uuid=uuid4(),
            name=name,
            ability_score=score,
            modifier_bonus=make_value(0),
            modifier=(score.normalized_score - 10) // 2,
        )

    scores = AbilityScoresSnapshot(
        uuid=uuid4(),
        name="Abilities",
        source_entity_uuid=uuid4(),
        strength=ability("strength"),
        dexterity=ability("dexterity"),
        constitution=ability("constitution"),
        intelligence=ability("intelligence"),
        wisdom=ability("wisdom"),
        charisma=ability("charisma"),
    )
    assert scores.abilities == []


def test_ability_snapshot_from_engine():
    ability = make_engine_ability("strength", 15, 1)
    snapshot = AbilitySnapshot.from_engine(ability)
    assert snapshot.uuid == ability.uuid
    assert snapshot.name == ability.name
    assert snapshot.modifier == ability.modifier


def test_ability_scores_snapshot_from_engine():
    abilities = {
        "strength": make_engine_ability("strength", 15, 1),
        "dexterity": make_engine_ability("dexterity", 10),
        "constitution": make_engine_ability("constitution", 12),
        "intelligence": make_engine_ability("intelligence", 8, -1),
        "wisdom": make_engine_ability("wisdom", 14, 2),
        "charisma": make_engine_ability("charisma", 10),
    }
    ability_scores = SimpleNamespace(
        uuid=uuid4(),
        name="Abilities",
        source_entity_uuid=uuid4(),
        source_entity_name="Bob",
        **abilities,
    )
    snapshot = AbilityScoresSnapshot.from_engine(ability_scores)
    assert snapshot.uuid == ability_scores.uuid
    assert snapshot.name == ability_scores.name
    for key, ability in abilities.items():
        ability_snapshot = getattr(snapshot, key)
        assert ability_snapshot.uuid == ability.uuid
        assert ability_snapshot.name == ability.name
        assert ability_snapshot.modifier == ability.modifier


def test_attack_bonus_calculation_snapshot_defaults_and_computed():
    total = make_value(7)
    calc = AttackBonusCalculationSnapshot(
        weapon_slot=WeaponSlot.MAIN_HAND,
        proficiency_bonus=make_value(2),
        weapon_bonus=make_value(1),
        attack_bonuses=[make_value(1)],
        ability_bonuses=[make_value(3)],
        range=RangeSnapshot(type=RangeType.REACH, normal=5),
        total_bonus=total,
        final_modifier=total.normalized_score,
    )
    assert calc.weapon_name is None
    assert calc.properties == []
    assert calc.final_modifier == total.normalized_score


def test_attack_bonus_calculation_snapshot_model_validate_error():
    base = make_value(0).model_dump()
    data = {
        "weapon_slot": "INVALID",
        "proficiency_bonus": base,
        "weapon_bonus": base,
        "attack_bonuses": [base],
        "ability_bonuses": [base],
        "range": {"type": RangeType.REACH, "normal": 5},
        "total_bonus": base,
        "final_modifier": 0,
    }
    with pytest.raises(ValidationError):
        AttackBonusCalculationSnapshot.model_validate(data)


def test_senses_snapshot_from_engine_serialization():
    entity_id = uuid4()
    senses = SimpleNamespace(
        position=(1, 2),
        visible_tiles={(1, 2): True},
        entities={entity_id: (3, 4)},
    )
    snapshot = SensesSnapshot.from_engine(senses)
    data = snapshot.model_dump()
    assert data["position"] == (1, 2)
    assert data["entities"] == {entity_id: (3, 4)}


def test_entity_summary_defaults_and_computed():
    senses = SensesSnapshot(position=(0, 0))
    summary = EntitySummary(
        uuid=uuid4(),
        name="Bob",
        current_hp=8,
        max_hp=10,
        position=(1, 2),
        senses=senses,
    )
    assert summary.armor_class is None
    assert summary.target_entity_uuid is None
    assert summary.max_hp - summary.current_hp == 2


def test_entity_summary_model_validate_error():
    senses = SensesSnapshot(position=(0, 0)).model_dump()
    data = {
        "uuid": str(uuid4()),
        "name": "Bob",
        "current_hp": 5,
        "max_hp": 10,
        "position": "invalid",
        "senses": senses,
    }
    with pytest.raises(ValidationError):
        EntitySummary.model_validate(data)


def test_modifiable_value_snapshot_defaults_and_computed():
    value = ModifiableValueSnapshot(
        uuid=uuid4(),
        name="HP",
        source_entity_uuid=uuid4(),
        score=12,
        normalized_score=12,
        min_value=0,
        max_value=20,
        advantage=AdvantageStatus.NONE,
        outgoing_advantage=AdvantageStatus.NONE,
        critical=CriticalStatus.NONE,
        outgoing_critical=CriticalStatus.NONE,
        auto_hit=AutoHitStatus.NONE,
        outgoing_auto_hit=AutoHitStatus.NONE,
    )
    assert value.resistances == {}
    assert value.channels == []
    assert value.min_value <= value.normalized_score <= value.max_value


def test_modifiable_value_snapshot_model_validate_error():
    data = {
        "uuid": str(uuid4()),
        "name": "HP",
        "source_entity_uuid": str(uuid4()),
        "score": "high",
        "normalized_score": 10,
        "advantage": AdvantageStatus.NONE,
        "outgoing_advantage": AdvantageStatus.NONE,
        "critical": CriticalStatus.NONE,
        "outgoing_critical": CriticalStatus.NONE,
        "auto_hit": AutoHitStatus.NONE,
        "outgoing_auto_hit": AutoHitStatus.NONE,
    }
    with pytest.raises(ValidationError):
        ModifiableValueSnapshot.model_validate(data)


def test_modifiable_value_snapshot_from_engine_with_channels():
    mv = MockModifiableValue()
    snapshot = ModifiableValueSnapshot.from_engine(mv)

    assert snapshot.uuid == mv.uuid
    assert snapshot.name == mv.name
    assert snapshot.source_entity_uuid == mv.source_entity_uuid
    assert snapshot.source_entity_name == mv.source_entity_name
    assert snapshot.target_entity_uuid == mv.target_entity_uuid
    assert snapshot.target_entity_name == mv.target_entity_name
    assert snapshot.score == mv.score
    assert snapshot.normalized_score == mv.normalized_score
    assert snapshot.min_value == mv.min
    assert snapshot.max_value == mv.max
    assert snapshot.advantage == mv.advantage
    assert snapshot.outgoing_advantage == mv.outgoing_advantage
    assert snapshot.critical == mv.critical
    assert snapshot.outgoing_critical == mv.outgoing_critical
    assert snapshot.auto_hit == mv.auto_hit
    assert snapshot.outgoing_auto_hit == mv.outgoing_auto_hit
    assert snapshot.resistances == mv.resistance
    assert snapshot.base_modifier.value == mv.get_base_modifier().value

    assert len(snapshot.channels) == 2

    static = next(c for c in snapshot.channels if c.name == "self_static")
    assert static.score == mv.self_static.score
    assert static.min_value == mv.self_static.min
    assert static.max_value == mv.self_static.max
    assert static.value_modifiers[0].value == mv.self_static.value_modifiers["v"].value
    assert static.min_constraints[0].value == mv.self_static.min_constraints["min"].value
    assert static.max_constraints[0].value == mv.self_static.max_constraints["max"].value
    assert (
        static.resistance_modifiers[0].value
        == mv.self_static.resistance_modifiers["res"].value
    )

    ctx = next(c for c in snapshot.channels if c.name == "self_contextual")
    assert ctx.score == mv.self_contextual.score
    assert ctx.min_value == mv.self_contextual.min
    assert ctx.max_value == mv.self_contextual.max
    expected_vm = mv.self_contextual.value_modifiers["v"].callable(None, None, None)
    assert ctx.value_modifiers[0].value == expected_vm.value
    expected_min = mv.self_contextual.min_constraints["min"].callable(None, None, None)
    assert ctx.min_constraints[0].value == expected_min.value
    expected_max = mv.self_contextual.max_constraints["max"].callable(None, None, None)
    assert ctx.max_constraints[0].value == expected_max.value
    expected_res = mv.self_contextual.resistance_modifiers["res"].callable(None, None, None)
    assert ctx.resistance_modifiers[0].value == expected_res.value


class ModVal:
    def __init__(self, score: int):
        self.uuid = uuid4()
        self.name = "value"
        self.source_entity_uuid = uuid4()
        self.source_entity_name = "source"
        self.target_entity_uuid = None
        self.target_entity_name = None
        self.score = score
        self.normalized_score = score
        self.min = None
        self.max = None
        self.advantage = AdvantageStatus.NONE
        self.outgoing_advantage = AdvantageStatus.NONE
        self.critical = CriticalStatus.NONE
        self.outgoing_critical = CriticalStatus.NONE
        self.auto_hit = AutoHitStatus.NONE
        self.outgoing_auto_hit = AutoHitStatus.NONE
        self.resistance = {}


class Ability:
    def __init__(self, name: str, score: int):
        self.uuid = uuid4()
        self.name = name
        self.ability_score = ModVal(score)
        self.modifier_bonus = ModVal(0)
        self.modifier = (score - 10) // 2

    def get_combined_values(self):
        return type("Bonus", (), {"normalized_score": self.modifier})()


class AbilityScores:
    def __init__(self, scores: dict, entity_uuid):
        self.uuid = uuid4()
        self.name = "Abilities"
        self.source_entity_uuid = entity_uuid
        self.source_entity_name = None
        self.strength = Ability("strength", scores.get("strength", 10))
        self.dexterity = Ability("dexterity", scores.get("dexterity", 10))
        self.constitution = Ability("constitution", scores.get("constitution", 10))
        self.intelligence = Ability("intelligence", scores.get("intelligence", 10))
        self.wisdom = Ability("wisdom", scores.get("wisdom", 10))
        self.charisma = Ability("charisma", scores.get("charisma", 10))

    def get_ability(self, name: str):
        return getattr(self, name)


class Health:
    def __init__(self, base_hp: int, entity_uuid):
        self.uuid = uuid4()
        self.name = "Health"
        self.source_entity_uuid = entity_uuid
        self.source_entity_name = None
        self.base_hp = base_hp
        self.hit_dices = []
        self.hit_dices_total_hit_points = base_hp
        self.total_hit_dices_number = 0
        self.max_hit_points_bonus = ModVal(0)
        self.temporary_hit_points = ModVal(0)
        self.damage_taken = 0
        self.damage_reduction = ModVal(0)

    def get_max_hit_dices_points(self, constitution_modifier):
        return self.base_hp + constitution_modifier

    def get_total_hit_points(self, constitution_modifier):
        return self.get_max_hit_dices_points(constitution_modifier) - self.damage_taken


class Senses:
    def __init__(self, position):
        self.entities = {}
        self.visible = {}
        self.walkable = {}
        self.paths = {}
        self.extra_senses = []
        self.position = position


class Duration:
    def __init__(self, duration_type, duration):
        self.duration_type = duration_type
        self.duration = duration


class Condition:
    def __init__(self, name: str):
        self.uuid = uuid4()
        self.name = name
        self.description = "desc"
        self.duration = Duration(DurationType.ROUNDS, 2)
        self.source_entity_name = "source"
        self.source_entity_uuid = uuid4()
        self.applied = True


class EntityStub:
    def __init__(self):
        self.uuid = uuid4()
        self.name = "Stub"
        self.description = None
        self.target_entity_uuid = None
        self.position = (0, 0)
        self.sprite_name = "sprite"
        self.ability_scores = AbilityScores(
            {
                "strength": 10,
                "dexterity": 10,
                "constitution": 14,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 10,
            },
            self.uuid,
        )
        self.health = Health(10, self.uuid)
        self.senses = Senses(self.position)
        self.proficiency_bonus = ModVal(2)
        self.skill_set = object()
        self.equipment = object()
        self.saving_throws = object()
        self.action_economy = object()
        self.active_conditions = {"Poisoned": Condition("Poisoned")}

    def ac_bonus(self):
        return ModVal(15)


def test_entity_summary_and_snapshot_from_engine(monkeypatch):
    entity = EntityStub()
    con_mod = entity.ability_scores.get_ability("constitution").get_combined_values().normalized_score
    expected_hp = entity.health.get_total_hit_points(con_mod)
    expected_ac = entity.ac_bonus().normalized_score

    def fake_skill_set_from_engine(skill_set, entity=None):
        return SkillSetSnapshot(uuid=uuid4(), name="Skills", source_entity_uuid=entity.uuid)

    def fake_equipment_from_engine(equipment, entity=None):
        val = make_value(0)
        return EquipmentSnapshot(
            uuid=uuid4(),
            name="Equipment",
            source_entity_uuid=entity.uuid,
            unarmored_ac_type="NONE",
            unarmored_ac=val,
            ac_bonus=val,
            damage_bonus=val,
            attack_bonus=val,
            melee_attack_bonus=val,
            ranged_attack_bonus=val,
            melee_damage_bonus=val,
            ranged_damage_bonus=val,
            unarmed_attack_bonus=val,
            unarmed_damage_bonus=val,
            unarmed_damage_type=DamageType.BLUDGEONING,
            unarmed_damage_dice=1,
            unarmed_dice_numbers=1,
            unarmed_properties=[],
            armor_class=expected_ac,
        )

    def fake_saving_throw_set_from_engine(st, entity=None):
        return SavingThrowSetSnapshot(uuid=uuid4(), name="Saves", source_entity_uuid=entity.uuid)

    def fake_health_from_engine(health, entity=None):
        con = entity.ability_scores.get_ability("constitution").get_combined_values().normalized_score
        return HealthSnapshot(
            uuid=uuid4(),
            name="Health",
            source_entity_uuid=entity.uuid,
            hit_dices=[],
            max_hit_points_bonus=make_value(0),
            temporary_hit_points=make_value(0),
            damage_taken=0,
            damage_reduction=make_value(0),
            resistances=[],
            hit_dices_total_hit_points=health.base_hp,
            total_hit_dices_number=0,
            current_hit_points=health.get_total_hit_points(con),
            max_hit_points=health.get_max_hit_dices_points(con),
        )

    def fake_action_economy_from_engine(ae, entity=None):
        val = make_value(1)
        return ActionEconomySnapshot(
            uuid=uuid4(),
            name="AE",
            source_entity_uuid=entity.uuid,
            actions=val,
            bonus_actions=val,
            reactions=val,
            movement=val,
            base_actions=1,
            base_bonus_actions=1,
            base_reactions=1,
            base_movement=30,
            action_costs=[],
            bonus_action_costs=[],
            reaction_costs=[],
            movement_costs=[],
            available_actions=1,
            available_bonus_actions=1,
            available_reactions=1,
            available_movement=30,
        )

    monkeypatch.setattr(SkillSetSnapshot, "from_engine", fake_skill_set_from_engine)
    monkeypatch.setattr(EquipmentSnapshot, "from_engine", fake_equipment_from_engine)
    monkeypatch.setattr(SavingThrowSetSnapshot, "from_engine", fake_saving_throw_set_from_engine)
    monkeypatch.setattr(HealthSnapshot, "from_engine", fake_health_from_engine)
    monkeypatch.setattr(ActionEconomySnapshot, "from_engine", fake_action_economy_from_engine)

    def fake_skill_calc(entity, skill_name):
        return SkillBonusCalculationSnapshot(
            skill_name=skill_name,
            ability_name="dexterity",
            proficiency_bonus=make_value(0),
            normalized_proficiency_bonus=make_value(0),
            skill_bonus=make_value(0),
            ability_bonus=make_value(0),
            ability_modifier_bonus=make_value(0),
            total_bonus=make_value(0),
            final_modifier=0,
        )

    def fake_attack_calc(entity, slot):
        return AttackBonusCalculationSnapshot(
            weapon_slot=slot,
            proficiency_bonus=make_value(0),
            weapon_bonus=make_value(0),
            attack_bonuses=[make_value(0)],
            ability_bonuses=[make_value(0)],
            range=RangeSnapshot(type=RangeType.REACH, normal=5),
            total_bonus=make_value(0),
            final_modifier=0,
        )

    def fake_ac_calc(entity):
        return ACBonusCalculationSnapshot(
            is_unarmored=True,
            total_bonus=make_value(0),
            final_ac=expected_ac,
            outgoing_advantage=AdvantageStatus.NONE,
            outgoing_critical="NONE",
            outgoing_auto_hit="NONE",
        )

    monkeypatch.setattr(SkillBonusCalculationSnapshot, "from_engine", fake_skill_calc)
    monkeypatch.setattr(AttackBonusCalculationSnapshot, "from_engine", fake_attack_calc)
    monkeypatch.setattr(ACBonusCalculationSnapshot, "from_engine", fake_ac_calc)
    def fake_save_calc(entity, ability_name):
        return SavingThrowBonusCalculationSnapshot(
            ability_name=ability_name,
            proficiency_bonus=make_value(0),
            normalized_proficiency_bonus=make_value(0),
            saving_throw_bonus=make_value(0),
            ability_bonus=make_value(0),
            ability_modifier_bonus=make_value(0),
            total_bonus=make_value(0),
            final_modifier=0,
        )

    monkeypatch.setattr(
        SavingThrowBonusCalculationSnapshot,
        "from_engine",
        fake_save_calc,
    )

    monkeypatch.setattr("dnd.blocks.skills.all_skills", ["acrobatics"], raising=False)

    summary = EntitySummary.from_engine(entity)
    assert summary.current_hp == expected_hp
    assert summary.max_hp == expected_hp
    assert summary.armor_class == expected_ac

    snapshot = EntitySnapshot.from_engine(
        entity,
        include_skill_calculations=True,
        include_attack_calculations=True,
        include_ac_calculation=True,
        include_saving_throw_calculations=True,
    )

    assert snapshot.health.current_hit_points == expected_hp
    assert snapshot.equipment.armor_class == expected_ac
    assert snapshot.skill_calculations
    assert snapshot.attack_calculations
    assert snapshot.ac_calculation.final_ac == expected_ac
    assert snapshot.saving_throw_calculations
    assert "Poisoned" in snapshot.active_conditions
    cond = snapshot.active_conditions["Poisoned"]
    assert cond.duration_type == DurationType.ROUNDS
    assert cond.duration_value == 2
