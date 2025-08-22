from uuid import uuid4

from dnd.blocks.equipment import (
    Equipment,
    BodyArmor,
    ArmorType,
    Weapon,
    WeaponSlot,
)
from dnd.core.events import Range, RangeType
from dnd.core.modifiers import DamageType


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
