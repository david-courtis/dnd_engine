import pytest
from uuid import uuid4
from unittest.mock import patch

from dnd.entity import Entity, EntityConfig
from dnd.blocks.abilities import AbilityScoresConfig, AbilityConfig
from dnd.blocks.skills import SkillSetConfig
from dnd.blocks.saving_throws import SavingThrowSetConfig
from dnd.blocks.health import HealthConfig, HitDiceConfig
from dnd.blocks.equipment import EquipmentConfig, Weapon, WeaponProperty, Range
from dnd.blocks.action_economy import ActionEconomyConfig
from dnd.core.events import RangeType, SavingThrowEvent, SkillCheckEvent, WeaponSlot
from dnd.core.modifiers import DamageType
from dnd.core.values import ModifiableValue
from dnd.core.base_conditions import BaseCondition
from dnd.core.events import Event, EventPhase
from dnd.core.base_tiles import Tile
from dnd.conditions import Dodging

from tests.test_entity import create_basic_entity, clean_entity_registry


class SavingThrowCondition(BaseCondition):
    name: str = "SavingThrowCondition"

    def _apply(self, declaration_event: Event):
        return [], [], [], declaration_event.phase_to(EventPhase.EFFECT, update={"condition": self})


class NoEventCondition(BaseCondition):
    name: str = "NoEvent"

    def declare_event(self, parent_event: Event | None = None):
        return None

def test_register_entity_and_get_all_entities(clean_entity_registry):
    entity = create_basic_entity()
    Entity._entity_registry.pop(entity.uuid)
    Entity.register_entity(entity)
    assert Entity.get(entity.uuid) is entity
    assert entity in Entity.get_all_entities()


def test_create_with_proficiency_bonus_modifiers(clean_entity_registry):
    config = EntityConfig(
        ability_scores=AbilityScoresConfig(),
        skill_set=SkillSetConfig(),
        saving_throws=SavingThrowSetConfig(),
        health=HealthConfig(
            hit_dices=[HitDiceConfig(hit_dice_value=6, hit_dice_count=1, mode="average", ignore_first_level=False)]
        ),
        equipment=EquipmentConfig(),
        action_economy=ActionEconomyConfig(),
        proficiency_bonus=2,
        proficiency_bonus_modifiers=[("extra", 1)],
    )
    entity = Entity.create(source_entity_uuid=uuid4(), name="Test", config=config)
    assert entity.proficiency_bonus.normalized_score == 3


def test_check_condition_immunity_static_and_contextual(clean_entity_registry):
    entity = create_basic_entity()

    entity.add_condition_immunity("Poison")
    assert entity.check_condition_immunity("Poison")

    def always_true(_self, _target, _context):
        return True

    entity.add_condition_immunity("Sleep", "sleep", always_true)
    assert entity.check_condition_immunity("Sleep")
    assert not entity.check_condition_immunity("Fear")


def test_add_condition_requires_name(clean_entity_registry):
    entity = create_basic_entity()
    cond = Dodging(source_entity_uuid=entity.uuid, target_entity_uuid=entity.uuid)
    cond.name = None
    with pytest.raises(ValueError):
        entity.add_condition(cond)


def test_add_condition_sets_target_and_context(clean_entity_registry):
    entity = create_basic_entity()
    cond = Dodging(source_entity_uuid=entity.uuid, target_entity_uuid=None)
    event = entity.add_condition(cond, context={"a": 1}, check_save_throw=False)
    assert cond.target_entity_uuid == entity.uuid
    assert cond.context == {"a": 1}
    assert event is not None


def test_add_condition_immunity_returns_none(clean_entity_registry):
    entity = create_basic_entity()
    entity.add_condition_immunity("NoEvent")
    cond = NoEventCondition(source_entity_uuid=entity.uuid, target_entity_uuid=None)
    assert entity.add_condition(cond) is None

def test_add_condition_application_save_cancels_condition(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    cond = SavingThrowCondition(source_entity_uuid=attacker.uuid, target_entity_uuid=target.uuid)
    cond.application_saving_throw = SavingThrowEvent(
        source_entity_uuid=attacker.uuid, target_entity_uuid=target.uuid, ability_name="dexterity", dc=10
    )
    with patch("dnd.core.dice.random.randint", return_value=20):
        event = target.add_condition(cond)
    assert event.canceled
    assert cond.name not in target.active_conditions


def test_advance_duration_condition_removal_save_success(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    cond = SavingThrowCondition(source_entity_uuid=attacker.uuid, target_entity_uuid=target.uuid)
    cond.removal_saving_throw = SavingThrowEvent(
        source_entity_uuid=attacker.uuid, target_entity_uuid=target.uuid, ability_name="dexterity", dc=10
    )
    target.add_condition(cond, check_save_throw=False)
    assert cond.name in target.active_conditions
    with patch("dnd.core.dice.random.randint", return_value=20):
        removed = target.advance_duration_condition(cond.name)
    assert removed
    assert cond.name not in target.active_conditions


def test_get_attack_bonuses_off_hand(clean_entity_registry):
    entity = create_basic_entity()
    _, weapon_bonus, _, _, _ = entity._get_attack_bonuses(WeaponSlot.OFF_HAND)
    assert weapon_bonus is entity.equipment.unarmed_attack_bonus


def test_get_attack_bonuses_finesse_strength_vs_dex(clean_entity_registry):
    entity = create_basic_entity()
    weapon = Weapon(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        damage_dice=6,
        dice_numbers=1,
        damage_type=DamageType.SLASHING,
        range=Range(type=RangeType.REACH, normal=5),
        properties=[WeaponProperty.FINESSE],
    )
    entity.equipment.weapon_main_hand = weapon
    _, _, _, abilities, _ = entity._get_attack_bonuses()
    strength = entity.ability_scores.get_ability("strength").ability_score
    assert strength in abilities

    config = EntityConfig(
        ability_scores=AbilityScoresConfig(
            strength=AbilityConfig(ability_score=8), dexterity=AbilityConfig(ability_score=14)
        ),
        skill_set=SkillSetConfig(),
        saving_throws=SavingThrowSetConfig(),
        health=HealthConfig(
            hit_dices=[HitDiceConfig(hit_dice_value=6, hit_dice_count=1, mode="average", ignore_first_level=False)]
        ),
        equipment=EquipmentConfig(),
        action_economy=ActionEconomyConfig(),
        proficiency_bonus=2,
    )
    entity2 = Entity.create(source_entity_uuid=uuid4(), name="Test2", config=config)
    weapon2 = Weapon(
        source_entity_uuid=entity2.uuid,
        target_entity_uuid=entity2.uuid,
        damage_dice=6,
        dice_numbers=1,
        damage_type=DamageType.SLASHING,
        range=Range(type=RangeType.REACH, normal=5),
        properties=[WeaponProperty.FINESSE],
    )
    entity2.equipment.weapon_main_hand = weapon2
    _, _, _, abilities2, _ = entity2._get_attack_bonuses()
    dex = entity2.ability_scores.get_ability("dexterity").ability_score
    assert dex in abilities2

def test_saving_throw_bonus_sets_and_clears_target(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    bonus = target.saving_throw_bonus(attacker.uuid, "dexterity")
    assert isinstance(bonus, ModifiableValue)
    assert target.target_entity_uuid is None


def test_skill_bonus_cross_clears_targets(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    source_bonus, target_bonus = attacker.skill_bonus_cross(target.uuid, "stealth")
    assert isinstance(source_bonus, ModifiableValue)
    assert isinstance(target_bonus, ModifiableValue)
    assert attacker.target_entity_uuid is None
    assert target.target_entity_uuid is None


def test_ac_bonus_with_target_clears(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    bonus = attacker.ac_bonus(target.uuid)
    assert isinstance(bonus, ModifiableValue)
    assert attacker.target_entity_uuid is None


def test_get_damages_with_target_clears(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    damages = attacker.get_damages(target_entity_uuid=target.uuid)
    assert isinstance(damages, list)
    assert attacker.target_entity_uuid is None


def test_get_weapon_range_with_weapon(clean_entity_registry):
    entity = create_basic_entity()
    weapon = Weapon(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        damage_dice=6,
        dice_numbers=1,
        damage_type=DamageType.SLASHING,
        range=Range(type=RangeType.REACH, normal=5),
    )
    entity.equipment.weapon_main_hand = weapon
    rng = entity.get_weapon_range()
    assert rng is weapon.range


def test_create_skill_check_request_existing_target(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    dc_value = ModifiableValue.create(
        source_entity_uuid=attacker.uuid, target_entity_uuid=target.uuid, base_value=10, value_name="DC"
    )
    req = attacker.create_skill_check_request(target.uuid, "stealth", dc_value.uuid)
    assert req.dc == 10 and attacker.target_entity_uuid is None


def test_saving_throw_missing_dc_raises(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    event = SavingThrowEvent(source_entity_uuid=attacker.uuid, target_entity_uuid=target.uuid, ability_name="dexterity")
    with pytest.raises(ValueError):
        target.saving_throw(event)


def test_skill_check_missing_dc_raises(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    event = SkillCheckEvent(source_entity_uuid=attacker.uuid, target_entity_uuid=target.uuid, skill_name="stealth")
    with pytest.raises(ValueError):
        target.skill_check(event)


def test_update_all_entities_senses(clean_entity_registry):
    Tile.create((0, 0))
    Tile.create((1, 0))
    observer = create_basic_entity(position=(0, 0))
    seen = create_basic_entity(position=(1, 0))
    Entity.update_all_entities_senses(max_distance=5)
    assert seen.uuid in observer.senses.entities
    assert observer.senses.entities[seen.uuid] == (1, 0)
