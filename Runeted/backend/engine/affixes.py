"""Item affix pool, shared by loot generation and the reroll currency.

Kept free of the AI imports that live in engine/loot.py so the crafting
economy (services/currency.py) and its tests can import the pool directly.
"""
from __future__ import annotations

import random

from engine.passive_system import MAX_PASSIVES_BY_RARITY, clamp_passives
from models.passive import PassiveEffect, PassiveModel


def make_passive(
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


def affix_templates(scale: float) -> list:
    return [
        lambda: make_passive("Sharpened Edge", "on_hit", "damage_mult", round(0.05 * scale, 3), "self", 1.0, 0, "percent"),
        lambda: make_passive("Blood Draw", "on_hit", "lifesteal", round(0.03 * scale, 3), "self", 0.65, 0, "percent"),
        lambda: make_passive("Bramble Skin", "on_take_hit", "thorns", round(0.05 * scale, 3), "self", 0.70, 0, "percent"),
        lambda: make_passive("Side Step", "on_dodge", "dodge_mod", round(0.05 * scale, 3), "self", 0.70, 0, "percent"),
        lambda: make_passive("Guard Matrix", "start_of_turn", "shield", round(6 * scale, 2), "self", 0.45, 0, "flat"),
        lambda: make_passive("Hemorrhage Cut", "on_hit", "bleed", round(0.10 * scale, 3), "enemy", 0.45, 2, "percent"),
        lambda: make_passive("Scorch Brand", "on_hit", "dot", round(3 * scale, 2), "enemy", 0.35, 2, "flat"),
    ]


AFFIX_NAMES = {
    "Sharpened Edge", "Blood Draw", "Bramble Skin", "Side Step",
    "Guard Matrix", "Hemorrhage Cut", "Scorch Brand",
}


def roll_system_passives(rarity: str, risk: int, luck_bonus: float, is_boss: bool) -> list[PassiveModel]:
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
    templates = affix_templates(scale)
    random.shuffle(templates)
    passives = [maker() for maker in templates[:budget]]
    return clamp_passives(passives, rarity)


def roll_single_affix(rarity: str, scale: float = 1.0) -> PassiveModel:
    """One fresh affix at baseline strength, value-clamped for the rarity.

    clamp_passives truncates by rarity affix count; a reroll replaces an
    affix the item already legitimately has, so fall back to a 1-affix
    rarity for the value clamp when the count map would drop it.
    """
    passive = random.choice(affix_templates(scale))()
    clamp_rarity = rarity if MAX_PASSIVES_BY_RARITY.get(str(rarity).lower(), 0) >= 1 else "rare"
    return clamp_passives([passive], clamp_rarity)[0]
