from wynnsource import WynnSourceItem
from wynnsource.common.components_pb2 import (
    CraftedIdentification,
    CraftedMeta,
    DamageRange,
    Durability,
    Powder,
    PowderSlot,
    Requirements,
)
from wynnsource.common.enums_pb2 import ClassType, Element, Rarity
from wynnsource.item.gear_pb2 import AttackSpeed, CraftedGear, Gear, GearType, WeaponStats


def test_proto_codegen():
    item = WynnSourceItem(
        name="The Great Fire Spear",
        count=1,
        level=30,
        rarity=Rarity.RARITY_CRAFTED,
        gear=Gear(
            type=GearType.GEAR_TYPE_SPEAR,
            requirements=Requirements(level=30, class_req=ClassType.CLASS_TYPE_WARRIOR, defense_req=20),
            crafted=CraftedGear(
                crafted_meta=CraftedMeta(author="TestCrafter"),
                durability=Durability(current=232, max=235),
                powders=[
                    PowderSlot(powder=Powder(element=Element.ELEMENT_FIRE, level=6)),
                    PowderSlot(powder=Powder(element=Element.ELEMENT_FIRE, level=6)),
                    PowderSlot(),
                ],
                identifications=[
                    CraftedIdentification(id=35, current_val=29, max_val=30),
                    CraftedIdentification(id=36, current_val=15, max_val=15),
                ],
            ),
            weapon_stats=WeaponStats(
                attack_speed=AttackSpeed.ATTACK_SPEED_FAST,
                damages=[
                    DamageRange(element=Element.ELEMENT_NEUTRAL, min=50, max=70),
                    DamageRange(element=Element.ELEMENT_FIRE, min=250, max=360),
                ],
            ),
        ),
    )

    encoded = item.SerializeToString()
    decoded = WynnSourceItem()
    decoded.ParseFromString(encoded)
    assert item == decoded
    return encoded
