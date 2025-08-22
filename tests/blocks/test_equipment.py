from uuid import UUID, uuid4

import pytest

from dnd.blocks.equipment import (
    Equipment,
    BodyArmor,
    ArmorType,
    Weapon,
    WeaponSlot,
    WeaponProperty,
    Ring,
    RingSlot,
    BodyPart,
    Shield,
    EquipmentConfig,
    UnarmoredAc,
)
from dnd.core.events import Range, RangeType, EventQueue, EventType, EventPhase
from dnd.core.modifiers import DamageType
from dnd.core.values import ModifiableValue
from dnd.entity import Entity
from app.models.equipment import (
    AttackBonusCalculationSnapshot,
    ArmorSnapshot,
    WeaponSnapshot,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_mock_ranged_weapon(source: UUID | None = None) -> Weapon:
    """Create a simple ranged weapon with explicit bonuses and properties."""
    source = source or uuid4()
    return Weapon(
        source_entity_uuid=source,
        name="Longbow",
        damage_dice=8,
        dice_numbers=1,
        damage_type=DamageType.PIERCING,
        range=Range(type=RangeType.RANGE, normal=30, long=120),
        properties=[WeaponProperty.RANGED, WeaponProperty.MARTIAL],
        attack_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=2, value_name="Attack Bonus"
        ),
        damage_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=3, value_name="Damage Bonus"
        ),
    )


def make_mock_finesse_weapon(source: UUID | None = None) -> Weapon:
    """Create a melee finesse weapon used to test property handling."""
    source = source or uuid4()
    return Weapon(
        source_entity_uuid=source,
        name="Rapier",
        damage_dice=8,
        dice_numbers=1,
        damage_type=DamageType.PIERCING,
        range=Range(type=RangeType.REACH, normal=5),
        properties=[WeaponProperty.FINESSE, WeaponProperty.LIGHT],
        attack_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=1, value_name="Attack Bonus"
        ),
        damage_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=2, value_name="Damage Bonus"
        ),
    )


def make_mock_armor(source: UUID | None = None) -> BodyArmor:
    """Create a simple piece of armor with base AC and dex bonus."""
    source = source or uuid4()
    return BodyArmor(
        source_entity_uuid=source,
        name="Chain Shirt",
        type=ArmorType.MEDIUM,
        ac=ModifiableValue.create(
            source_entity_uuid=source, base_value=13, value_name="Armor Class"
        ),
        max_dex_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=2, value_name="Max Dex Bonus"
        ),
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ranged_weapon():
    return make_mock_ranged_weapon()


@pytest.fixture
def finesse_weapon():
    return make_mock_finesse_weapon()


@pytest.fixture
def weapon_no_properties():
    source = uuid4()
    return Weapon(
        source_entity_uuid=source,
        name="Club",
        damage_dice=4,
        dice_numbers=1,
        damage_type=DamageType.BLUDGEONING,
        range=Range(type=RangeType.REACH, normal=5),
        properties=[],
        attack_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=0, value_name="Attack Bonus"
        ),
        damage_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=1, value_name="Damage Bonus"
        ),
    )


@pytest.fixture
def medium_armor():
    return make_mock_armor()


@pytest.fixture
def heavy_armor():
    source = uuid4()
    return BodyArmor(
        source_entity_uuid=source,
        name="Plate",
        type=ArmorType.HEAVY,
        ac=ModifiableValue.create(
            source_entity_uuid=source, base_value=16, value_name="Armor Class"
        ),
        max_dex_bonus=ModifiableValue.create(
            source_entity_uuid=source, base_value=0, value_name="Max Dex Bonus"
        ),
    )


@pytest.fixture
def dual_wield_equipment(weapon_no_properties, ranged_weapon):
    eq = Equipment.create(uuid4())
    eq.equip(weapon_no_properties, WeaponSlot.MAIN_HAND)
    eq.equip(ranged_weapon, WeaponSlot.OFF_HAND)
    return eq


@pytest.fixture
def aligned_entity():
    """Return an entity with all sub-block sources aligned for combination operations."""
    entity = Entity.create(uuid4())
    entity.equipment.source_entity_uuid = entity.source_entity_uuid
    for value in entity.equipment.get_values():
        value.set_source_entity(entity.source_entity_uuid)
    entity.proficiency_bonus.set_source_entity(entity.source_entity_uuid)
    entity.ability_scores.source_entity_uuid = entity.source_entity_uuid
    for ability in [
        entity.ability_scores.strength,
        entity.ability_scores.dexterity,
        entity.ability_scores.constitution,
        entity.ability_scores.intelligence,
        entity.ability_scores.wisdom,
        entity.ability_scores.charisma,
    ]:
        ability.source_entity_uuid = entity.source_entity_uuid
        for value in ability.get_values():
            value.set_source_entity(entity.source_entity_uuid)
    return entity


def test_equipping_items():
    source = uuid4()
    equipment = Equipment.create(source)

    armor = BodyArmor(source_entity_uuid=uuid4(), name="Leather", type=ArmorType.LIGHT)
    equipment.equip(armor)
    assert equipment.body_armor is armor
    assert armor.source_entity_uuid == equipment.source_entity_uuid

    weapon = Weapon(
        source_entity_uuid=uuid4(),
        name="Dagger",
        damage_dice=4,
        dice_numbers=1,
        damage_type=DamageType.PIERCING,
        range=Range(type=RangeType.REACH, normal=5),
    )
    equipment.equip(weapon, WeaponSlot.MAIN_HAND)
    assert equipment.weapon_main_hand is weapon
    assert weapon.source_entity_uuid == equipment.source_entity_uuid

    equipment.unequip(WeaponSlot.MAIN_HAND)
    assert equipment.weapon_main_hand is None


def test_value_retrieval():
    equipment = Equipment.create(uuid4())
    retrieved = equipment.get_value_from_name("Armor Class Bonus")
    assert retrieved is equipment.ac_bonus


def test_weapon_and_armor_from_engine_snapshot(ranged_weapon, medium_armor):
    """WeaponSnapshot and ArmorSnapshot should mirror engine objects."""
    weapon = ranged_weapon
    armor = medium_armor

    weapon_snapshot = WeaponSnapshot.from_engine(weapon)
    armor_snapshot = ArmorSnapshot.from_engine(armor)

    # Range snapshot should match weapon range
    assert weapon_snapshot.range.type == weapon.range.type
    assert weapon_snapshot.range.normal == weapon.range.normal
    assert weapon_snapshot.range.long == weapon.range.long

    # Properties and bonuses
    assert set(weapon_snapshot.properties) == {p.value for p in weapon.properties}
    assert (
        weapon_snapshot.attack_bonus.normalized_score
        == weapon.attack_bonus.normalized_score
    )
    assert armor_snapshot.ac.normalized_score == armor.ac.normalized_score


def test_attack_bonus_calculation_from_engine():
    """AttackBonusCalculationSnapshot should aggregate bonuses correctly."""
    entity = Entity.create(uuid4())
    # Align equipment values to the entity so bonuses combine cleanly
    entity.equipment.source_entity_uuid = entity.source_entity_uuid
    for value in entity.equipment.get_values():
        value.set_source_entity(entity.source_entity_uuid)
    entity.proficiency_bonus.set_source_entity(entity.source_entity_uuid)
    entity.ability_scores.source_entity_uuid = entity.source_entity_uuid
    for ability in [
        entity.ability_scores.strength,
        entity.ability_scores.dexterity,
        entity.ability_scores.constitution,
        entity.ability_scores.intelligence,
        entity.ability_scores.wisdom,
        entity.ability_scores.charisma,
    ]:
        ability.source_entity_uuid = entity.source_entity_uuid
        for value in ability.get_values():
            value.set_source_entity(entity.source_entity_uuid)

    # Equip mock weapon and set equipment bonuses
    weapon = make_mock_ranged_weapon(entity.source_entity_uuid)
    entity.equipment.equip(weapon, WeaponSlot.MAIN_HAND)

    entity.equipment.attack_bonus = ModifiableValue.create(
        source_entity_uuid=entity.source_entity_uuid,
        base_value=1,
        value_name="Attack Bonus",
    )
    entity.equipment.ranged_attack_bonus = ModifiableValue.create(
        source_entity_uuid=entity.source_entity_uuid,
        base_value=3,
        value_name="Ranged Attack Bonus",
    )

    calc = AttackBonusCalculationSnapshot.from_engine(entity, WeaponSlot.MAIN_HAND)

    # Verify range snapshot
    assert calc.range.normal == weapon.range.normal
    assert calc.range.type == weapon.range.type

    # Proficiency should be carried over
    assert (
        calc.proficiency_bonus.normalized_score
        == entity.proficiency_bonus.normalized_score
    )

    # Aggregated total equals sum of components
    expected = (
        calc.proficiency_bonus.normalized_score
        + calc.weapon_bonus.normalized_score
        + sum(b.normalized_score for b in calc.attack_bonuses)
        + sum(b.normalized_score for b in calc.ability_bonuses)
    )
    assert calc.total_bonus.normalized_score == expected


def test_range_normalization_unarmed(aligned_entity):
    """Unarmed attacks should normalize to reach with no long range."""
    calc = AttackBonusCalculationSnapshot.from_engine(aligned_entity, WeaponSlot.MAIN_HAND)
    assert calc.range.type == RangeType.REACH
    assert calc.range.normal == 5
    assert calc.range.long is None


def test_property_flags(ranged_weapon, weapon_no_properties, aligned_entity):
    """Attack calculations expose correct property flags."""
    entity = aligned_entity
    entity.equipment.equip(ranged_weapon, WeaponSlot.MAIN_HAND)
    calc = AttackBonusCalculationSnapshot.from_engine(entity, WeaponSlot.MAIN_HAND)
    assert calc.is_ranged is True
    assert WeaponProperty.RANGED.value in calc.properties

    # Swap to a weapon with no special properties
    entity.equipment.equip(weapon_no_properties, WeaponSlot.MAIN_HAND)
    calc = AttackBonusCalculationSnapshot.from_engine(entity, WeaponSlot.MAIN_HAND)
    assert calc.is_ranged is False
    assert calc.properties == []


def test_damage_combination(aligned_entity):
    """Weapon damage should combine weapon, equipment, and extra bonuses."""
    entity = aligned_entity

    # Equip weapon with extra damage
    weapon = Weapon(
        source_entity_uuid=uuid4(),
        name="Flaming Sword",
        damage_dice=6,
        dice_numbers=1,
        damage_type=DamageType.SLASHING,
        range=Range(type=RangeType.REACH, normal=5),
        properties=[],
        damage_bonus=ModifiableValue.create(
            source_entity_uuid=entity.source_entity_uuid, base_value=1, value_name="Damage Bonus"
        ),
        attack_bonus=ModifiableValue.create(
            source_entity_uuid=entity.source_entity_uuid, base_value=0, value_name="Attack Bonus"
        ),
        extra_damage_dices=[4],
        extra_damage_dices_numbers=[1],
        extra_damage_bonus=[ModifiableValue.create(
            source_entity_uuid=entity.source_entity_uuid, base_value=2, value_name="Fire Bonus"
        )],
        extra_damage_type=[DamageType.FIRE],
    )
    entity.equipment.damage_bonus = ModifiableValue.create(
        source_entity_uuid=entity.source_entity_uuid, base_value=2, value_name="Damage Bonus"
    )
    entity.equipment.melee_damage_bonus = ModifiableValue.create(
        source_entity_uuid=entity.source_entity_uuid, base_value=1, value_name="Melee Damage Bonus"
    )
    entity.equipment.equip(weapon, WeaponSlot.MAIN_HAND)

    damages = weapon.get_all_weapon_damages(entity.equipment, entity.ability_scores)
    assert len(damages) == 2
    main_damage = damages[0]
    extra_damage = damages[1]

    assert main_damage.damage_bonus.normalized_score == 4  # 1 weapon +2 equip +1 melee
    assert extra_damage.damage_bonus.normalized_score == 2
    assert extra_damage.damage_type == DamageType.FIRE


def test_invalid_equipment_state_returns_none(aligned_entity):
    """Attack calculations gracefully handle invalid equipment states."""
    entity = aligned_entity
    # Corrupt the weapon slot with a non-weapon object
    entity.equipment.weapon_main_hand = BodyArmor(source_entity_uuid=uuid4(), name="Hat", type=ArmorType.LIGHT)
    calc = AttackBonusCalculationSnapshot.from_engine(entity, WeaponSlot.MAIN_HAND)
    assert calc is None


def test_switching_slots(dual_wield_equipment, finesse_weapon):
    """Equipping a new weapon should replace the existing one in that slot."""
    dual_wield_equipment.equip(finesse_weapon, WeaponSlot.MAIN_HAND)
    assert dual_wield_equipment.weapon_main_hand is finesse_weapon


def test_armor_ac_calculation(medium_armor, heavy_armor, aligned_entity):
    """Armor class uses correct dexterity adjustments for different armor types."""
    entity = aligned_entity
    # Increase dexterity to test max dex bonus behaviour
    from dnd.blocks.abilities import ability_score_normalizer
    entity.ability_scores.dexterity.ability_score = ModifiableValue.create(
        source_entity_uuid=entity.source_entity_uuid,
        base_value=16,
        value_name="Dexterity Ability Score",
        score_normalizer=ability_score_normalizer,
    )

    entity.equipment.equip(medium_armor)
    ac_medium = entity.ac_bonus().normalized_score

    # Switching to heavy armor should override previous armor and cap dex bonus
    entity.equipment.equip(heavy_armor)
    ac_heavy = entity.ac_bonus().normalized_score

    assert ac_medium == 15  # 13 base + max 2 dex
    assert ac_heavy == 16  # 16 base, no dex bonus


def test_weapon_flags_and_damage_types(aligned_entity, ranged_weapon, weapon_no_properties):
    """Verify weapon state helpers and damage calculations for both hands and unarmed."""
    equipment = aligned_entity.equipment

    # Initially unarmed
    assert equipment.is_unarmed(WeaponSlot.MAIN_HAND)
    assert equipment.is_unarmed(WeaponSlot.OFF_HAND)
    assert equipment.is_ranged(WeaponSlot.MAIN_HAND) is False
    assert (
        equipment.get_main_damage_type(WeaponSlot.MAIN_HAND)
        == equipment.unarmed_damage_type
    )
    unarmed_damage = equipment.get_damages(
        WeaponSlot.MAIN_HAND, aligned_entity.ability_scores
    )[0]
    assert unarmed_damage.damage_type == equipment.unarmed_damage_type
    assert unarmed_damage.damage_bonus.normalized_score == 0

    # Equip weapons in both hands
    equipment.equip(weapon_no_properties, WeaponSlot.MAIN_HAND)
    equipment.equip(ranged_weapon, WeaponSlot.OFF_HAND)

    assert not equipment.is_unarmed(WeaponSlot.MAIN_HAND)
    assert not equipment.is_unarmed(WeaponSlot.OFF_HAND)
    assert equipment.is_ranged(WeaponSlot.MAIN_HAND) is False
    assert equipment.is_ranged(WeaponSlot.OFF_HAND) is True

    assert (
        equipment.get_main_damage_type(WeaponSlot.MAIN_HAND)
        == DamageType.BLUDGEONING
    )
    assert equipment.get_main_damage_type(WeaponSlot.OFF_HAND) == DamageType.PIERCING

    main_damage = equipment.get_damages(
        WeaponSlot.MAIN_HAND, aligned_entity.ability_scores
    )[0]
    off_damage = equipment.get_damages(
        WeaponSlot.OFF_HAND, aligned_entity.ability_scores
    )[0]
    assert main_damage.damage_type == DamageType.BLUDGEONING
    assert main_damage.damage_bonus.normalized_score == 1
    assert off_damage.damage_type == DamageType.PIERCING
    assert off_damage.damage_bonus.normalized_score == 3


def test_ac_value_functions_with_and_without_shield(medium_armor):
    """Check AC calculations for unarmored and armored states with optional shields."""
    equipment = Equipment.create(uuid4())

    # Unarmored, no shield
    assert equipment.get_unarmored_ac_values() == [
        equipment.ac_bonus,
        equipment.unarmored_ac,
    ]
    assert equipment.get_armored_ac_values() == [equipment.ac_bonus]
    assert equipment.get_armored_max_dex_bonus() is None

    # Add a shield
    shield = Shield(
        source_entity_uuid=uuid4(),
        name="Shield",
        ac_bonus=ModifiableValue.create(
            source_entity_uuid=uuid4(), base_value=2, value_name="Shield AC"
        ),
    )
    equipment.equip(shield, WeaponSlot.OFF_HAND)
    unarmored_with_shield = equipment.get_unarmored_ac_values()
    assert shield.ac_bonus in unarmored_with_shield
    armored_with_shield = equipment.get_armored_ac_values()
    assert shield.ac_bonus in armored_with_shield

    # Add body armor
    equipment.equip(medium_armor)
    armored_values = equipment.get_armored_ac_values()
    assert armored_values[1] is medium_armor.ac
    assert shield.ac_bonus in armored_values
    assert equipment.get_armored_max_dex_bonus() is medium_armor.max_dex_bonus

    # Remove shield
    equipment.unequip(WeaponSlot.OFF_HAND)
    armored_no_shield = equipment.get_armored_ac_values()
    assert armored_no_shield == [equipment.ac_bonus, medium_armor.ac]
    assert shield.ac_bonus not in equipment.get_unarmored_ac_values()


def test_equip_unequip_events_and_slots(aligned_entity, ranged_weapon, medium_armor):
    """Equipping and unequipping items should trigger events and clear slots."""

    def assert_event_phases(ev):
        phases = [e.phase for e in EventQueue.get_event_history(ev.uuid)]
        assert phases == [
            EventPhase.DECLARATION,
            EventPhase.EXECUTION,
            EventPhase.EFFECT,
            EventPhase.COMPLETION,
        ]

    equipment = aligned_entity.equipment

    ring = Ring(source_entity_uuid=uuid4(), name="Ring", type=ArmorType.CLOTH)
    shield = Shield(
        source_entity_uuid=uuid4(),
        name="Shield",
        ac_bonus=ModifiableValue.create(
            source_entity_uuid=uuid4(), base_value=2, value_name="Shield AC"
        ),
    )

    # Ring equip/unequip
    equipment.equip(ring, RingSlot.LEFT)
    ring_eq = EventQueue.get_events_by_type(EventType.ARMOR_EQUIP)[-1]
    assert ring_eq.slot == RingSlot.LEFT
    assert equipment.ring_left is ring
    assert_event_phases(ring_eq)

    equipment.unequip(RingSlot.LEFT)
    ring_uneq = EventQueue.get_events_by_type(EventType.ARMOR_UNEQUIP)[-1]
    assert ring_uneq.slot == RingSlot.LEFT
    assert equipment.ring_left is None
    assert_event_phases(ring_uneq)

    # Weapon equip/unequip
    equipment.equip(ranged_weapon, WeaponSlot.MAIN_HAND)
    weq = EventQueue.get_events_by_type(EventType.WEAPON_EQUIP)[-1]
    assert weq.slot == WeaponSlot.MAIN_HAND
    assert equipment.weapon_main_hand is ranged_weapon
    assert_event_phases(weq)

    equipment.unequip(WeaponSlot.MAIN_HAND)
    wuneq = EventQueue.get_events_by_type(EventType.WEAPON_UNEQUIP)[-1]
    assert wuneq.slot == WeaponSlot.MAIN_HAND
    assert equipment.weapon_main_hand is None
    assert_event_phases(wuneq)

    # Shield equip/unequip
    equipment.equip(shield, WeaponSlot.OFF_HAND)
    seq = EventQueue.get_events_by_type(EventType.SHIELD_EQUIP)[-1]
    assert seq.slot == WeaponSlot.OFF_HAND
    assert equipment.weapon_off_hand is shield
    assert_event_phases(seq)

    equipment.unequip(WeaponSlot.OFF_HAND)
    suneq = EventQueue.get_events_by_type(EventType.SHIELD_UNEQUIP)[-1]
    assert suneq.slot == WeaponSlot.OFF_HAND
    assert equipment.weapon_off_hand is None
    assert_event_phases(suneq)

    # Armor equip/unequip
    equipment.equip(medium_armor)
    aeq = EventQueue.get_events_by_type(EventType.ARMOR_EQUIP)[-1]
    assert aeq.slot == BodyPart.BODY
    assert equipment.body_armor is medium_armor
    assert_event_phases(aeq)

    equipment.unequip(BodyPart.BODY)
    auneq = EventQueue.get_events_by_type(EventType.ARMOR_UNEQUIP)[-1]
    assert auneq.slot == BodyPart.BODY
    assert equipment.body_armor is None
    assert_event_phases(auneq)


def test_equipment_create_applies_config_modifiers():
    """Equipment created from config should apply all modifiers and settings."""
    config = EquipmentConfig(
        unarmored_ac_type=UnarmoredAc.MONK,
        unarmored_ac=10,
        unarmored_ac_modifiers=[("amulet", 2)],
        ac_bonus=1,
        ac_bonus_modifiers=[("ring", 1)],
        damage_bonus=2,
        damage_bonus_modifiers=[("feat", 1)],
        attack_bonus=1,
        attack_bonus_modifiers=[("magic", 2)],
        melee_attack_bonus=1,
        melee_attack_bonus_modifiers=[("style", 1)],
        ranged_attack_bonus=1,
        ranged_attack_bonus_modifiers=[("archery", 2)],
        melee_damage_bonus=1,
        melee_damage_bonus_modifiers=[("rage", 1)],
        ranged_damage_bonus=1,
        ranged_damage_bonus_modifiers=[("dex", 2)],
        unarmed_attack_bonus=1,
        unarmed_attack_bonus_modifiers=[("training", 1)],
        unarmed_damage_bonus=1,
        unarmed_damage_bonus_modifiers=[("monk", 1)],
        unarmed_damage_type=DamageType.FIRE,
        unarmed_damage_dice=6,
        unarmed_dice_numbers=2,
    )

    equipment = Equipment.create(uuid4(), config=config)

    assert equipment.unarmored_ac.normalized_score == 12
    assert equipment.ac_bonus.normalized_score == 2
    assert equipment.damage_bonus.normalized_score == 3
    assert equipment.attack_bonus.normalized_score == 3
    assert equipment.melee_attack_bonus.normalized_score == 2
    assert equipment.ranged_attack_bonus.normalized_score == 3
    assert equipment.melee_damage_bonus.normalized_score == 2
    assert equipment.ranged_damage_bonus.normalized_score == 3
    assert equipment.unarmed_attack_bonus.normalized_score == 2
    assert equipment.unarmed_damage_bonus.normalized_score == 2
    assert equipment.unarmored_ac_type == UnarmoredAc.MONK
