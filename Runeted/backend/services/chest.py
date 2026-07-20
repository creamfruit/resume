"""Chest reward system.

A chest has its own rarity tier, separate from the rarity of whatever it
contains. Both decisions — the chest's own tier (decided the moment a
battle is won, from the defeated enemy's level/tier/modifiers) and its
contents' rarity (decided the moment it's opened, clamped to a window
around the chest's tier) — reuse the one weighted roll `engine.loot`
already has (`roll_rarity`) rather than a second probability system.
`generate_loot`/`generate_build_rune` then do their normal, unchanged
generation work off that decided rarity, via each one's existing
"pin the rarity" parameter (`forced_rarity` / `rarity_override`) — so an
item or rune coming out of a chest is exactly as internally consistent
(power, passives, effects all match its label) as one rolled anywhere
else in the game.

Skills (core/skills.py) are a fixed catalog with no per-player unlock
state yet — the same constraint noted in services/currency.py for
reroll/ascend — so chest contents are runes, items, and currency only.
"skill" slots into CONTENT_KIND_WEIGHTS the day a skill-unlock system
exists; nothing else here needs to change for that.
"""
from __future__ import annotations

import random
from typing import Any

from engine.loot import generate_loot, roll_rarity
from models.enemy import Enemy
from models.player import Player
from services.currency import add_currency
from services.rune_system import generate_build_rune

# The six tiers engine.loot.roll_rarity can produce. A chest's own tier
# and its contents' tier are both points on this one ladder, which is
# what makes comparing them (floor/ceiling, "one tier below/above")
# meaningful instead of arbitrary.
CHEST_RARITY_ORDER = ["common", "rare", "epic", "legendary", "mythic", "relic"]

# What a chest can hand out, and how often each kind is picked once the
# "does a chest even have contents worth naming" question is settled by
# the rarity roll above. Flat across chest tiers — the *rarity* of the
# pick is what scales with tier, not which kind gets picked.
CONTENT_KIND_WEIGHTS: dict[str, int] = {"item": 45, "rune": 35, "currency": 20}

# warden_key is deliberately excluded: it's the currency that opens/
# upgrades chests, not something a chest should hand back out.
CHEST_CURRENCY_POOL: list[tuple[str, int]] = [
    ("gold", 50), ("crafted_supplies", 30), ("ascension_sigil", 20),
]
_CHEST_CURRENCY_BASE = {"gold": 15, "crafted_supplies": 1, "ascension_sigil": 1}


def _tier_index(rarity: str) -> int:
    rarity = str(rarity or "common").lower()
    try:
        return CHEST_RARITY_ORDER.index(rarity)
    except ValueError:
        return 0


def _clamp_rarity(rarity: str, floor: str, ceiling: str) -> str:
    lo, hi = _tier_index(floor), _tier_index(ceiling)
    return CHEST_RARITY_ORDER[max(lo, min(hi, _tier_index(rarity)))]


def chest_content_bounds(chest_rarity: str) -> tuple[str, str]:
    """The floor/ceiling a chest of this tier may roll for its contents:
    a window from one tier below to one tier above the chest's own tier,
    clamped to the ladder's ends. A common chest (index 0) therefore
    windows to [common, rare] and can never roll a legendary weapon; a
    legendary chest (index 3) windows to [epic, mythic] and can never
    roll pure junk."""
    i = _tier_index(chest_rarity)
    floor = CHEST_RARITY_ORDER[max(0, i - 1)]
    ceiling = CHEST_RARITY_ORDER[min(len(CHEST_RARITY_ORDER) - 1, i + 1)]
    return floor, ceiling


def _enemy_risk_score(enemy: Enemy) -> int:
    """How tough the defeated enemy was, folded into a single number
    `roll_rarity`'s `risk` input already knows how to bias with: level
    above 1, a flat bump for elite/boss tier, and one point per
    modifier it carried (engine/enemy_factory.py's colossal/volatile/
    runic/swift stack from the encounter-generation phase)."""
    level_bonus = max(0, int(getattr(enemy, "level", 1) or 1) - 1)
    tier = str(getattr(enemy, "tier", "normal") or "normal")
    tier_bonus = 6 if tier == "boss" else (3 if tier == "elite" or bool(getattr(enemy, "elite", False)) else 0)
    modifier_bonus = len(list(getattr(enemy, "modifiers", []) or []))
    return level_bonus + tier_bonus + modifier_bonus


def roll_chest_tier(enemy: Enemy, luck_bonus: float = 0.0) -> str:
    """The chest's own rarity, decided once at battle victory. Reuses
    `roll_rarity` directly — a tougher fight biases the weighted roll
    upward, it never hand-picks a tier from enemy stats."""
    is_boss = str(getattr(enemy, "tier", "normal") or "normal") == "boss"
    return roll_rarity(is_boss=is_boss, risk=_enemy_risk_score(enemy), luck_bonus=luck_bonus)


def grant_chest(player: Player, rarity: str) -> str:
    rarity = _clamp_rarity(rarity, CHEST_RARITY_ORDER[0], CHEST_RARITY_ORDER[-1])
    player.chests[rarity] = int(player.chests.get(rarity, 0) or 0) + 1
    return rarity


def _roll_content_kind() -> str:
    kinds = list(CONTENT_KIND_WEIGHTS)
    weights = [CONTENT_KIND_WEIGHTS[k] for k in kinds]
    return random.choices(kinds, weights=weights, k=1)[0]


def _roll_currency_reward(rarity: str) -> tuple[str, int]:
    kinds = [c for c, _ in CHEST_CURRENCY_POOL]
    weights = [w for _, w in CHEST_CURRENCY_POOL]
    currency_id = random.choices(kinds, weights=weights, k=1)[0]
    tier_mult = 1 + _tier_index(rarity)
    base = _CHEST_CURRENCY_BASE.get(currency_id, 1)
    amount = max(1, int(base * tier_mult * random.uniform(0.8, 1.4)))
    return currency_id, amount


def open_chest(player: Player, chest_rarity: str, risk: int = 0, luck_bonus: float = 0.0) -> dict[str, Any]:
    """Consume one chest of `chest_rarity` and roll its contents
    immediately — the single action the task calls for: no separate
    peek step, no partial consumption, nothing left pending."""
    chest_rarity = _clamp_rarity(chest_rarity, CHEST_RARITY_ORDER[0], CHEST_RARITY_ORDER[-1])
    held = int(player.chests.get(chest_rarity, 0) or 0)
    if held <= 0:
        return {"ok": False, "error": f"No {chest_rarity} chest to open"}
    player.chests[chest_rarity] = held - 1

    floor, ceiling = chest_content_bounds(chest_rarity)
    # A higher chest tier also biases the underlying roll upward (not
    # just the hard clamp below), so "better average contents" holds
    # even for the tier-below/tier-above overlap two adjacent chest
    # tiers share.
    biased_risk = _tier_index(chest_rarity) * 3 + risk
    content_rarity = _clamp_rarity(
        roll_rarity(is_boss=False, risk=biased_risk, luck_bonus=luck_bonus), floor, ceiling
    )

    kind = _roll_content_kind()
    result: dict[str, Any] = {
        "ok": True, "chest_rarity": chest_rarity, "kind": kind, "rarity": content_rarity,
    }

    if kind == "item":
        item = generate_loot(is_boss=False, risk=biased_risk, luck_bonus=luck_bonus, forced_rarity=content_rarity)
        player.stash.append(item)
        result["item"] = {"name": item.name, "rarity": item.rarity, "power": item.power, "slot": item.slot}
    elif kind == "rune":
        rune = generate_build_rune(player, rarity_override=content_rarity)
        player.rune_items.append(rune)
        result["rune"] = {"id": rune["id"], "name": rune["name"], "rarity": rune["rarity"]}
    else:  # currency
        currency_id, amount = _roll_currency_reward(content_rarity)
        add_currency(player, currency_id, amount)
        result["currency"] = {"currency_id": currency_id, "amount": amount}

    return result


def award_battle_chest(player: Player, enemy: Enemy, risk: int = 0, room_type: str = "combat") -> dict[str, Any]:
    """What a battle victory hands out beyond the baseline gold/exp
    already granted elsewhere: a chest (tier from the defeated enemy's
    level/tier/modifiers), a bonus currency amount, both, or neither.
    Two independent rolls, so every combination is reachable — a chest
    "instead of, or alongside" currency."""
    is_boss = str(room_type or "") == "boss"
    luck = float(getattr(player, "loot_luck", 0.0) or 0.0)

    chest_chance = 0.10 + (max(0, risk) * 0.03) + (luck * 0.20) + (0.35 if is_boss else 0.0)
    currency_chance = 0.18 + (max(0, risk) * 0.02) + (luck * 0.15) + (0.15 if is_boss else 0.0)

    result: dict[str, Any] = {"chest": None, "currency": None}

    if random.random() < chest_chance:
        result["chest"] = grant_chest(player, roll_chest_tier(enemy, luck_bonus=luck))

    if random.random() < currency_chance:
        rarity = roll_chest_tier(enemy, luck_bonus=luck)
        currency_id, amount = _roll_currency_reward(rarity)
        add_currency(player, currency_id, amount)
        result["currency"] = {"currency_id": currency_id, "amount": amount}

    return result
