import random
from models.item import Item
from models.passive import PassiveModel, PassiveEffect

from ai.item_designer import design_item_with_ai
from engine.passive_system import clamp_passives
from models.passive import PassiveEffect, PassiveModel

NAME_PREFIX = [
    "Rustbound", "Ashen", "Grim", "Moonlit", "Bone", "Iron", "Storm", "Dread",
    "Hollow", "Runed", "Feral", "Thorn", "Gilded", "Blackglass",
]
WEAPON_CORES = ["Blade", "Axe", "Mace", "Spear", "Dagger", "Hammer", "Pike", "Edge"]
ARMOR_CORES = ["Plate", "Mail", "Vest", "Guard", "Shell", "Cuirass", "Mantle", "Aegis"]
NAME_SUFFIX = [
    "of Cinders", "of Echoes", "of Hunger", "of the Mire", "of Warding",
    "of Sparks", "of Ruin", "of Dawn", "of Venom",
]


def _roll_item_name(slot: str, rarity: str) -> str:
    core_pool = WEAPON_CORES if str(slot) == "weapon" else ARMOR_CORES
    base = f"{random.choice(NAME_PREFIX)} {random.choice(core_pool)}"
    # Higher rarity more likely to get a suffix.
    suffix_ch = {
        "common": 0.08,
        "rare": 0.22,
        "epic": 0.45,
        "legendary": 0.75,
        "mythic": 0.90,
        "relic": 0.98,
    }.get(str(rarity).lower(), 0.20)
    if random.random() < suffix_ch:
        base = f"{base} {random.choice(NAME_SUFFIX)}"
    return base


def _make_passive(
    name: str,
    trigger: str,
    effect_type: str,
    value: float,
    target: str = "self",
    chance_value: float = 1.0,
    duration: int = 0,
    scaling: str = "flat",
) -> PassiveModel:
    return PassiveModel(
        name=name,
        trigger=trigger,
        chance=min(1.0, max(0.05, chance_value)),
        effects=[
            PassiveEffect(
                type=effect_type,
                value=value,
                target=target,
                chance=1.0,
                duration=duration,
                scaling=scaling,
            )
        ],
    )


def _roll_innate_weapon_abilities(rarity: str, risk: int, luck_bonus: float) -> list[PassiveModel]:
    rarity = str(rarity).lower()
    if rarity not in {"rare", "epic", "legendary", "mythic", "relic"}:
        return []

    count = {
        "rare": 1,
        "epic": 1,
        "legendary": 2,
        "mythic": 2,
        "relic": 3,
    }.get(rarity, 1)

    if rarity == "mythic" and random.random() < 0.45:
        count += 1
    if rarity == "relic" and random.random() < 0.70:
        count = min(3, count + 1)

    templates = [
        ("Razor Edge", "on_hit", "damage_mult", 0.05, "self", 1.0),
        ("Storm Lunge", "on_hit", "dot", 2.5, "enemy", 0.45),
        ("Guard Bloom", "start_of_turn", "shield", 6.0, "self", 0.55),
        ("Swift Refrain", "on_dodge", "dodge_mod", 0.04, "self", 0.75),
        ("Blood Tap", "on_hit", "lifesteal", 0.03, "self", 0.60),
        ("Aether Siphon", "on_hit", "enemy_buff", 0.08, "enemy", 0.40),
    ]
    random.shuffle(templates)

    abilities = []
    for idx in range(count):
        name, trigger, effect_type, value, target, chance_value = templates[idx % len(templates)]
        roll_mult = 1.0 + (risk * 0.06) + (luck_bonus * 0.15)
        value = round(float(value) * roll_mult, 3)
        ability = PassiveModel(
            name=name,
            trigger=trigger,
            chance=min(1.0, max(0.25, chance_value)),
            effects=[PassiveEffect(type=effect_type, value=value, target=target, chance=1.0, duration=2 if effect_type in {"dot", "bleed", "enemy_buff"} else 0, scaling="percent" if effect_type in {"damage_mult", "lifesteal", "dodge_mod", "enemy_buff"} else "flat")],
        )
        abilities.append(ability)

    return clamp_passives(abilities, rarity)


def _roll_system_passives(rarity: str, risk: int, luck_bonus: float, is_boss: bool) -> list[PassiveModel]:
    rarity = str(rarity).lower()
    # Conservative baseline; clamp_passives remains the final safety net.
    chance_map = {
        "common": 0.0,
        "rare": 0.10,
        "epic": 0.28,
        "legendary": 0.55,
        "mythic": 0.72,
        "relic": 0.88,
    }
    if random.random() > chance_map.get(rarity, 0.0):
        return []

    budget = {
        "rare": 1,
        "epic": 1 if random.random() < 0.65 else 2,
        "legendary": random.randint(1, 2),
        "mythic": random.randint(2, 3),
        "relic": random.randint(2, 4),
    }.get(rarity, 0)
    if budget <= 0:
        return []

    scale = 1.0 + (risk * 0.08) + (0.10 if is_boss else 0.0) + (luck_bonus * 0.25)
    templates = [
        lambda: _make_passive("Sharpened Edge", "on_hit", "damage_mult", round(0.05 * scale, 3), "self", 1.0, 0, "percent"),
        lambda: _make_passive("Blood Draw", "on_hit", "lifesteal", round(0.03 * scale, 3), "self", 0.65, 0, "percent"),
        lambda: _make_passive("Bramble Skin", "on_take_hit", "thorns", round(0.05 * scale, 3), "self", 0.70, 0, "percent"),
        lambda: _make_passive("Side Step", "on_dodge", "dodge_mod", round(0.05 * scale, 3), "self", 0.70, 0, "percent"),
        lambda: _make_passive("Guard Matrix", "start_of_turn", "shield", round(6 * scale, 2), "self", 0.45, 0, "flat"),
        lambda: _make_passive("Hemorrhage Cut", "on_hit", "bleed", round(0.10 * scale, 3), "enemy", 0.45, 2, "percent"),
        lambda: _make_passive("Scorch Brand", "on_hit", "dot", round(3 * scale, 2), "enemy", 0.35, 2, "flat"),
    ]
    random.shuffle(templates)
    passives = [maker() for maker in templates[:budget]]
    return clamp_passives(passives, rarity)


def roll_rarity(is_boss: bool, risk: int, luck_bonus: float) -> str:
    r = random.random()

    # Relic: extremely rare (your "almost impossible" tier)
    relic = (0.000002 + risk * 0.000003 + (0.00002 if is_boss else 0.0)) * (1 + luck_bonus)
    if r < relic:
        return "relic"

    # Mythic
    mythic = (0.004 + risk * 0.003 + (0.01 if is_boss else 0.0)) * (1 + luck_bonus * 0.8)
    if r < mythic:
        return "mythic"

    # Legendary
    legendary = (0.03 + risk * 0.02 + (0.05 if is_boss else 0.0)) * (1 + luck_bonus * 0.6)
    if r < legendary:
        return "legendary"

    # Epic
    epic = (0.12 + risk * 0.03) * (1 + luck_bonus * 0.4)
    if r < epic:
        return "epic"

    # Rare
    rare = 0.30 * (1 + luck_bonus * 0.2)
    if r < rare:
        return "rare"

    return "common"


def generate_loot(
    is_boss: bool = False,
    risk: int = 0,
    depth: int = 1,
    luck_bonus: float = 0.0
) -> Item:
    slot = random.choice(["weapon", "armor"])
    rarity = roll_rarity(is_boss=is_boss, risk=risk, luck_bonus=luck_bonus)

    # Use AI only for top rarities
    if rarity in ("legendary", "mythic", "relic"):
        try:
            ai_item = design_item_with_ai(
                slot=slot,
                rarity=rarity,
                risk=risk,
                depth=depth,
                luck_bonus=luck_bonus,
            )
            return Item(
                name=ai_item.name,
                rarity=ai_item.rarity,
                power=int(ai_item.damage),
                passives=[p for p in ai_item.passives],
                slot=ai_item.slot,
                source="ai",
            )
        except Exception:
            # Fallback (never crash loot)
            pass

    # Normal (non-AI) loot for lower tiers
    base = random.randint(5, 15)
    mult = 1.0 + risk * 0.15 + (0.25 if is_boss else 0.0)

    rarity_bonus = {
        "common": 0,
        "rare": 6,
        "epic": 14,
        "legendary": 25,
        "mythic": 40,
        "relic": 60,
    }[rarity]

    power = int((base + rarity_bonus) * mult)

    passives = _roll_system_passives(rarity=rarity, risk=risk, luck_bonus=luck_bonus, is_boss=is_boss)
    innate_abilities = _roll_innate_weapon_abilities(rarity=rarity, risk=risk, luck_bonus=luck_bonus) if slot == "weapon" else []

    return Item(
        name=_roll_item_name(slot=slot, rarity=rarity),
        rarity=rarity,
        power=power,
        passives=passives,
        innate_abilities=innate_abilities,
        slot=slot,
        source="system",
    )
