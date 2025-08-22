import pytest
from uuid import uuid4
from unittest.mock import patch

from dnd.entity import Entity, EntityConfig
from dnd.blocks.abilities import AbilityScoresConfig
from dnd.blocks.skills import SkillSetConfig
from dnd.blocks.saving_throws import SavingThrowSetConfig
from dnd.blocks.health import HealthConfig, HitDiceConfig
from dnd.blocks.equipment import (
    EquipmentConfig,
    Damage,
    Ring,
    ArmorType,
    Weapon,
    Shield,
    WeaponProperty,
)
from dnd.blocks.action_economy import ActionEconomyConfig
from dnd.core.modifiers import DamageType
from dnd.core.dice import AttackOutcome
from dnd.core.events import RangeType, Range, WeaponSlot
from dnd.core.values import ModifiableValue
from dnd.conditions import Dodging
from dnd.core.base_tiles import Tile


def create_basic_entity(position: tuple[int, int] | tuple = (0, 0)):
    entity_uuid = uuid4()
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
        position=position,
    )
    return Entity.create(source_entity_uuid=entity_uuid, name="Test", config=config)


@pytest.fixture
def clean_entity_registry():
    Entity._entity_registry.clear()
    Entity._entity_by_position.clear()
    Tile._tile_registry.clear()
    Tile._tile_by_position.clear()
    yield
    Entity._entity_registry.clear()
    Entity._entity_by_position.clear()
    Tile._tile_registry.clear()
    Tile._tile_by_position.clear()


def test_entity_take_damage_returns_roll_and_updates_health():
    entity = create_basic_entity()
    damage = Damage(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        damage_dice=4,
        dice_numbers=1,
        damage_bonus=ModifiableValue.create(source_entity_uuid=entity.uuid, base_value=0, value_name="Damage Bonus"),
        damage_type=DamageType.BLUDGEONING,
    )
    with patch("dnd.core.dice.random.randint", return_value=3):
        rolls = entity.take_damage([damage], AttackOutcome.HIT)
    assert len(rolls) == 1
    assert rolls[0].total == 3
    assert entity.health.damage_taken == 3


def test_health_heal_and_death_conditions():
    entity = create_basic_entity()
    max_hp = entity.get_hp()

    entity.health.take_damage(2, DamageType.BLUDGEONING, uuid4())
    assert entity.health.get_total_hit_points(0) == max_hp - 2

    entity.health.heal(1)
    assert entity.health.get_total_hit_points(0) == max_hp - 1

    entity.health.take_damage(max_hp - 1, DamageType.BLUDGEONING, uuid4())
    assert entity.health.get_total_hit_points(0) == 0

    entity.health.take_damage(max_hp, DamageType.BLUDGEONING, uuid4())
    assert entity.health.get_total_hit_points(0) < 0


def test_action_economy_can_afford_and_consume():
    entity = create_basic_entity()
    ae = entity.action_economy

    assert ae.can_afford("actions", 1)
    ae.consume("actions", 1)
    assert not ae.can_afford("actions", 1)
    with pytest.raises(ValueError):
        ae.consume("actions", 1)

    assert ae.can_afford("bonus_actions", 1)
    ae.consume("bonus_actions", 1)
    with pytest.raises(ValueError):
        ae.consume("bonus_actions", 1)


def test_entity_range_and_bonuses():
    entity = create_basic_entity()

    rng = entity.get_weapon_range()
    assert rng.type == RangeType.REACH and rng.normal == 5

    assert entity.attack_bonus().normalized_score == 2
    assert entity.ac_bonus().normalized_score == 10


def test_target_selection_and_clearing():
    attacker = create_basic_entity()
    target = create_basic_entity()

    assert attacker.get_target_entity() is None

    attacker.set_target_entity(target.uuid)
    assert attacker.get_target_entity() is target

    attacker.clear_target_entity()
    assert attacker.get_target_entity() is None


def test_condition_application_and_removal_affects_equipment():
    entity = create_basic_entity()
    condition = Dodging(source_entity_uuid=entity.uuid, target_entity_uuid=entity.uuid)

    assert len(entity.equipment.ac_bonus.to_target_static.advantage_modifiers) == 0

    entity.add_condition(condition)
    assert "Dodging" in entity.active_conditions
    assert len(entity.equipment.ac_bonus.to_target_static.advantage_modifiers) == 1

    entity.remove_condition("Dodging")
    assert "Dodging" not in entity.active_conditions
    assert len(entity.equipment.ac_bonus.to_target_static.advantage_modifiers) == 0


def test_equipment_invalid_ring_slot():
    entity = create_basic_entity()
    ring = Ring(source_entity_uuid=entity.uuid, target_entity_uuid=entity.uuid, type=ArmorType.CLOTH)

    with pytest.raises(ValueError):
        entity.equipment.equip(ring)


def test_get_attack_bonuses_unarmed(clean_entity_registry):
    entity = create_basic_entity()
    _, weapon_bonus, attack_bonuses, ability_bonuses, range_obj = entity._get_attack_bonuses()
    assert weapon_bonus is entity.equipment.unarmed_attack_bonus
    assert entity.equipment.melee_attack_bonus in attack_bonuses
    strength = entity.ability_scores.get_ability("strength").ability_score
    assert strength in ability_bonuses
    assert range_obj.type == RangeType.REACH and range_obj.normal == 5


def test_get_attack_bonuses_melee_weapon(clean_entity_registry):
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
    _, weapon_bonus, attack_bonuses, ability_bonuses, range_obj = entity._get_attack_bonuses()
    assert weapon_bonus is weapon.attack_bonus
    assert entity.equipment.melee_attack_bonus in attack_bonuses
    strength = entity.ability_scores.get_ability("strength").ability_score
    assert strength in ability_bonuses
    assert range_obj.type == RangeType.REACH


def test_get_attack_bonuses_ranged_weapon(clean_entity_registry):
    entity = create_basic_entity()
    weapon = Weapon(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        damage_dice=6,
        dice_numbers=1,
        damage_type=DamageType.PIERCING,
        range=Range(type=RangeType.RANGE, normal=30, long=120),
        properties=[WeaponProperty.RANGED],
    )
    entity.equipment.weapon_main_hand = weapon
    _, weapon_bonus, attack_bonuses, ability_bonuses, range_obj = entity._get_attack_bonuses()
    assert weapon_bonus is weapon.attack_bonus
    assert entity.equipment.ranged_attack_bonus in attack_bonuses
    dexterity = entity.ability_scores.get_ability("dexterity").ability_score
    assert dexterity in ability_bonuses
    assert range_obj.type == RangeType.RANGE


def test_get_weapon_range_with_shield_defaults_to_reach(clean_entity_registry):
    entity = create_basic_entity()
    shield = Shield(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        ac_bonus=ModifiableValue.create(source_entity_uuid=entity.uuid, base_value=2, value_name="Shield AC"),
    )
    entity.equipment.weapon_off_hand = shield
    rng = entity.get_weapon_range(WeaponSlot.OFF_HAND)
    assert rng.type == RangeType.REACH and rng.normal == 5


def test_take_damage_multiple_damages_updates_health(clean_entity_registry):
    entity = create_basic_entity()
    dmg1 = Damage(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        damage_dice=4,
        dice_numbers=1,
        damage_bonus=ModifiableValue.create(source_entity_uuid=entity.uuid, base_value=0, value_name="db1"),
        damage_type=DamageType.BLUDGEONING,
    )
    dmg2 = Damage(
        source_entity_uuid=entity.uuid,
        target_entity_uuid=entity.uuid,
        damage_dice=4,
        dice_numbers=1,
        damage_bonus=ModifiableValue.create(source_entity_uuid=entity.uuid, base_value=0, value_name="db2"),
        damage_type=DamageType.BLUDGEONING,
    )
    with patch("dnd.core.dice.random.randint", side_effect=[3, 2]):
        rolls = entity.take_damage([dmg1, dmg2], AttackOutcome.HIT)
    assert len(rolls) == 2
    assert entity.health.damage_taken == 5


def test_create_saving_throw_request_int_and_uuid_dc(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    req = attacker.create_saving_throw_request(target.uuid, "dexterity", 10)
    assert req.dc == 10 and attacker.target_entity_uuid is None
    dc_value = ModifiableValue.create(source_entity_uuid=attacker.uuid, base_value=12, value_name="DC")
    req_uuid = attacker.create_saving_throw_request(target.uuid, "dexterity", dc_value.uuid)
    assert req_uuid.dc == 12 and attacker.target_entity_uuid is None
    bad_dc = ModifiableValue.create(source_entity_uuid=uuid4(), base_value=10, value_name="bad")
    with pytest.raises(ValueError):
        attacker.create_saving_throw_request(target.uuid, "dexterity", bad_dc.uuid)
    with pytest.raises(ValueError):
        attacker.create_saving_throw_request(target.uuid, "dexterity", uuid4())


def test_create_skill_check_request_int_and_uuid_dc(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    req = attacker.create_skill_check_request(target.uuid, "stealth", 10)
    assert req.dc == 10 and attacker.target_entity_uuid is None
    dc_value = ModifiableValue.create(source_entity_uuid=attacker.uuid, base_value=13, value_name="DC")
    req_uuid = attacker.create_skill_check_request(target.uuid, "stealth", dc_value.uuid)
    assert req_uuid.dc == 13 and attacker.target_entity_uuid is None
    bad_dc = ModifiableValue.create(source_entity_uuid=uuid4(), base_value=5, value_name="bad")
    with pytest.raises(ValueError):
        attacker.create_skill_check_request(target.uuid, "stealth", bad_dc.uuid)
    with pytest.raises(ValueError):
        attacker.create_skill_check_request(target.uuid, "stealth", uuid4())


def test_saving_throw_mismatch_and_outcomes(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    request = attacker.create_saving_throw_request(target.uuid, "dexterity", 10)
    other = create_basic_entity()
    with pytest.raises(ValueError):
        other.saving_throw(request)
    with patch("dnd.core.dice.random.randint", return_value=15):
        outcome, roll, success = target.saving_throw(request)
    assert outcome == AttackOutcome.HIT and success and target.target_entity_uuid is None
    request_fail = attacker.create_saving_throw_request(target.uuid, "dexterity", 15)
    with patch("dnd.core.dice.random.randint", return_value=5):
        outcome, roll, success = target.saving_throw(request_fail)
    assert outcome == AttackOutcome.MISS and not success and target.target_entity_uuid is None


def test_skill_check_mismatch_and_outcomes(clean_entity_registry):
    attacker = create_basic_entity()
    target = create_basic_entity()
    request = attacker.create_skill_check_request(target.uuid, "stealth", 10)
    other = create_basic_entity()
    with pytest.raises(ValueError):
        other.skill_check(request)
    with patch("dnd.core.dice.random.randint", return_value=15):
        outcome, roll, success = target.skill_check(request)
    assert outcome == AttackOutcome.HIT and success and target.target_entity_uuid is None
    request_fail = attacker.create_skill_check_request(target.uuid, "stealth", 15)
    with patch("dnd.core.dice.random.randint", return_value=5):
        outcome, roll, success = target.skill_check(request_fail)
    assert outcome == AttackOutcome.MISS and not success and target.target_entity_uuid is None


def test_update_entity_position_and_move_updates_registry(clean_entity_registry):
    entity = create_basic_entity(position=(0, 0))
    assert entity in Entity.get_all_entities_at_position((0, 0))
    Entity.update_entity_position(entity, (1, 0))
    assert entity.position == (1, 0) and entity.senses.position == (1, 0)
    assert entity in Entity.get_all_entities_at_position((1, 0))
    assert entity not in Entity.get_all_entities_at_position((0, 0))
    entity.move((2, 0))
    assert entity.position == (2, 0) and entity.senses.position == (2, 0)
    assert entity in Entity.get_all_entities_at_position((2, 0))
    assert entity not in Entity.get_all_entities_at_position((1, 0))


def test_update_entity_senses(clean_entity_registry):
    Tile.create((0, 0))
    Tile.create((1, 0))
    observer = create_basic_entity(position=(0, 0))
    seen = create_basic_entity(position=(1, 0))
    observer.update_entity_senses(max_distance=5)
    assert seen.uuid in observer.senses.entities
    assert observer.senses.entities[seen.uuid] == (1, 0)
    assert (1, 0) in observer.senses.visible
    assert observer.senses.walkable[(1, 0)]

