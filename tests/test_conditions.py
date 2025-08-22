from uuid import uuid4

from dnd.entity import Entity
from dnd.conditions import Blinded, Charmed, Dashing
from dnd.core.values import AdvantageStatus, AutoHitStatus


def make_entities():
    e1 = Entity.create(source_entity_uuid=uuid4())
    e2 = Entity.create(source_entity_uuid=uuid4())
    e1.set_values_and_blocks_source()
    e2.set_values_and_blocks_source()
    return e1, e2


def test_blinded_applies_and_removes_modifiers():
    source, target = make_entities()
    condition = Blinded(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    event = condition.apply()
    assert event and not event.canceled
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.DISADVANTAGE
    skill = target.skill_set.get_skill("perception")
    assert skill.skill_bonus.auto_hit == AutoHitStatus.AUTOMISS
    condition.remove_condition_modifiers()
    assert target.equipment.attack_bonus.advantage == AdvantageStatus.NONE
    assert skill.skill_bonus.auto_hit == AutoHitStatus.NONE


def test_dashing_increases_movement_and_resets():
    source, target = make_entities()
    base_speed = target.action_economy.movement.normalized_score
    condition = Dashing(source_entity_uuid=source.uuid, target_entity_uuid=target.uuid)
    condition.apply()
    assert target.action_economy.movement.normalized_score == base_speed * 2
    condition.remove_condition_modifiers()
    assert target.action_economy.movement.normalized_score == base_speed


def test_charmed_modifiers_attack_and_skills():
    charmer, charmed = make_entities()
    condition = Charmed(source_entity_uuid=charmer.uuid, target_entity_uuid=charmed.uuid)
    condition.apply()
    atk_bonus = charmed.attack_bonus(target_entity_uuid=charmer.uuid)
    assert atk_bonus.auto_hit == AutoHitStatus.AUTOMISS
    skill_bonus = charmer.skill_bonus(charmed.uuid, "persuasion")
    assert skill_bonus.advantage == AdvantageStatus.ADVANTAGE
    condition.remove_condition_modifiers()
    atk_bonus = charmed.attack_bonus(target_entity_uuid=charmer.uuid)
    assert atk_bonus.auto_hit == AutoHitStatus.NONE
    skill_bonus = charmer.skill_bonus(charmed.uuid, "persuasion")
    assert skill_bonus.advantage == AdvantageStatus.NONE