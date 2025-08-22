import pytest
from uuid import uuid4
from types import SimpleNamespace

from app.models.skills import SkillSetSnapshot, SkillBonusCalculationSnapshot
from dnd.core.modifiers import AdvantageStatus, CriticalStatus, AutoHitStatus


def make_engine_value(score: int):
    return SimpleNamespace(
        uuid=uuid4(),
        name="value",
        source_entity_uuid=uuid4(),
        source_entity_name=None,
        target_entity_uuid=None,
        target_entity_name=None,
        score=score,
        normalized_score=score,
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


class DummySkill:
    def __init__(self, name, ability, proficiency, bonus):
        self.uuid = uuid4()
        self.name = name
        self._ability = ability
        self.proficiency = proficiency
        self.expertise = False
        self.skill_bonus = make_engine_value(bonus)

    @property
    def ability(self):
        return self._ability


class DummySkillSet:
    def __init__(self, entity_uuid):
        self.uuid = uuid4()
        self.name = "Skills"
        self.source_entity_uuid = entity_uuid
        self.source_entity_name = "Tester"
        self._skills = {
            "acrobatics": DummySkill("acrobatics", "dexterity", True, 1),
            "history": DummySkill("history", "intelligence", False, 1),
        }

    def get_skill(self, name):
        return self._skills[name]


class DummyEntity:
    def __init__(self):
        self.uuid = uuid4()
        self.proficiency_bonus = make_engine_value(2)
        self.target_entity_uuid = None
        self.skill_set = DummySkillSet(self.uuid)

    def _get_bonuses_for_skill(self, skill_name):
        if skill_name == "acrobatics":
            return (
                make_engine_value(2),
                make_engine_value(1),
                make_engine_value(3),
                make_engine_value(0),
            )
        elif skill_name == "history":
            return (
                make_engine_value(0),
                make_engine_value(1),
                make_engine_value(1),
                make_engine_value(0),
            )
        raise KeyError(skill_name)

    def skill_bonus(self, _context, skill_name):
        totals = {
            "acrobatics": make_engine_value(6),
            "history": make_engine_value(2),
        }
        return totals[skill_name]


def test_skill_set_snapshot_lists_and_effective_bonus(monkeypatch):
    entity = DummyEntity()
    monkeypatch.setattr("dnd.blocks.skills.all_skills", ["acrobatics", "history"], raising=False)
    snapshot = SkillSetSnapshot.from_engine(entity.skill_set, entity)
    assert set(snapshot.skills.keys()) == {"acrobatics", "history"}
    assert snapshot.proficient_skills == ["acrobatics"]
    assert snapshot.expertise_skills == []
    assert snapshot.skills["acrobatics"].effective_bonus == 6
    assert snapshot.skills["history"].effective_bonus == 2
    assert snapshot.skills["acrobatics"].proficiency_multiplier == 1
    assert snapshot.skills["history"].proficiency_multiplier == 0


def test_skill_bonus_calculation_trained_vs_untrained():
    entity = DummyEntity()
    trained = SkillBonusCalculationSnapshot.from_engine(entity, "acrobatics")
    untrained = SkillBonusCalculationSnapshot.from_engine(entity, "history")
    assert trained.normalized_proficiency_bonus.normalized_score == 2
    assert trained.total_bonus.normalized_score == 6
    assert trained.final_modifier == 6
    assert untrained.normalized_proficiency_bonus.normalized_score == 0
    assert untrained.total_bonus.normalized_score == 2
    assert untrained.final_modifier == 2
