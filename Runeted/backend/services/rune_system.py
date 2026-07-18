from __future__ import annotations

import random
from typing import Any

from models.player import Player
from models.rune import Rune

DEFAULT_RUNE_SLOT_CAPACITY = 6
DEFAULT_RUNE_BUDGET_CAP = 10
RUNE_SLOT_CAPACITY_BASE = 6
RUNE_BUDGET_CAP_BASE = 10

RUNE_BUILD_RARITIES = ["common", "rare", "epic", "legendary", "mythic", "supreme", "relic"]
RUNE_NEXT_RARITY = {
    "common": "rare",
    "rare": "epic",
    "epic": "legendary",
    "legendary": "mythic",
    "mythic": "supreme",
    "supreme": "relic",
}
RUNE_CHEST_WEIGHTS = {
    "common": 760,
    "rare": 185,
    "epic": 42,
    "legendary": 10,
    "mythic": 0,
    "supreme": 0,
    "relic": 0,
}
RUNE_COMBINE_BONUS_CHANCE = {
    "common": 0.10,
    "rare": 0.08,
    "epic": 0.06,
    "legendary": 0.04,
    "mythic": 0.02,
    "supreme": 0.0,
}
RUNE_UPGRADE_COSTS = {
    "common": 1,
    "rare": 2,
    "epic": 4,
    "legendary": 8,
    "mythic": 16,
    "supreme": 28,
    "relic": 45,
}
RUNE_UPGRADE_MAX = {
    "common": 5,
    "rare": 6,
    "epic": 7,
    "legendary": 8,
    "mythic": 9,
    "supreme": 10,
    "relic": 12,
}
RUNE_RELIC_INFUSE_CAP = {
    "common": 0,
    "rare": 1,
    "epic": 2,
    "legendary": 4,
    "mythic": 6,
    "supreme": 8,
    "relic": 12,
}
RUNE_SELL_BASE = {
    "common": 35,
    "rare": 90,
    "epic": 230,
    "legendary": 750,
    "mythic": 2100,
    "supreme": 5600,
    "relic": 14500,
}
RUNE_DISMANTLE_BASE = {
    "common": {"relic": 1, "essence": 1},
    "rare": {"relic": 2, "essence": 2},
    "epic": {"relic": 4, "essence": 3},
    "legendary": {"relic": 8, "essence": 4},
    "mythic": {"relic": 14, "essence": 6},
    "supreme": {"relic": 24, "essence": 8},
    "relic": {"relic": 40, "essence": 10},
}
RUNE_EFFECT_POOL = {
    "common": [("attack_mult", 0.02, 0.04), ("defense_mult", 0.02, 0.04), ("dodge_flat", 0.005, 0.01)],
    "rare": [("attack_mult", 0.04, 0.07), ("defense_mult", 0.04, 0.07), ("lifesteal", 0.01, 0.02)],
    "epic": [("attack_mult", 0.07, 0.12), ("defense_mult", 0.07, 0.12), ("dodge_flat", 0.01, 0.02), ("thorns", 0.01, 0.02)],
    "legendary": [("attack_mult", 0.12, 0.18), ("defense_mult", 0.12, 0.18), ("lifesteal", 0.02, 0.04), ("crit_bonus", 0.03, 0.06)],
    "mythic": [("attack_mult", 0.18, 0.28), ("defense_mult", 0.18, 0.28), ("lifesteal", 0.04, 0.06), ("thorns", 0.03, 0.05)],
    "supreme": [("attack_mult", 0.28, 0.38), ("defense_mult", 0.28, 0.38), ("lifesteal", 0.06, 0.09), ("dodge_flat", 0.03, 0.05)],
    "relic": [("attack_mult", 0.38, 0.55), ("defense_mult", 0.38, 0.55), ("lifesteal", 0.10, 0.16), ("thorns", 0.07, 0.12)],
}
RUNE_NAME_PARTS = {
    "prefix": ["Ash", "Void", "Storm", "Blood", "Iron", "Rune", "Aether", "Dusk", "Solar", "Frost"],
    "core": ["Sigil", "Glyph", "Core", "Mark", "Shard", "Seal", "Ember", "Oath", "Pulse", "Eye"],
    "suffix": ["of Fury", "of Ward", "of Echoes", "of Hunger", "of Flux", "of Dominion", "of Echo"],
}
RUNE_RECIPES = {
    "air": {"name": "Air Rune", "essence_cost": 1, "base_yield": (1, 2), "xp": 8, "unlock": 1},
    "mind": {"name": "Mind Rune", "essence_cost": 1, "base_yield": (1, 2), "xp": 9, "unlock": 1},
    "water": {"name": "Water Rune", "essence_cost": 2, "base_yield": (1, 3), "xp": 12, "unlock": 8},
    "earth": {"name": "Earth Rune", "essence_cost": 2, "base_yield": (1, 3), "xp": 13, "unlock": 12},
    "fire": {"name": "Fire Rune", "essence_cost": 2, "base_yield": (1, 3), "xp": 14, "unlock": 18},
    "body": {"name": "Body Rune", "essence_cost": 3, "base_yield": (1, 3), "xp": 20, "unlock": 26},
    "chaos": {"name": "Chaos Rune", "essence_cost": 4, "base_yield": (1, 2), "xp": 30, "unlock": 40},
    "nature": {"name": "Nature Rune", "essence_cost": 4, "base_yield": (1, 2), "xp": 32, "unlock": 44},
    "death": {"name": "Death Rune", "essence_cost": 5, "base_yield": (1, 2), "xp": 45, "unlock": 62},
    "blood": {"name": "Blood Rune", "essence_cost": 6, "base_yield": (1, 2), "xp": 60, "unlock": 75},
}

AMPLIFIER_KIND = "amplifier"
AMPLIFIER_BONUS_CAP = 0.25
AMPLIFIER_RECIPES = {
    "amp_minor": {"name": "Minor Amplifier Rune", "tier": 1, "cost_supplies": 25,
                  "cost_gold": 400, "amp_bonus": 0.10, "unlock": 5, "xp": 40},
    "amp_major": {"name": "Major Amplifier Rune", "tier": 2, "cost_supplies": 75,
                  "cost_gold": 1500, "amp_bonus": 0.20, "unlock": 15, "xp": 120},
}
AMPLIFIER_SELL_VALUE = {1: 300, 2: 1100}

RUNE_POOL: list[dict[str, Any]] = [
    {
        "id": "ember_drive",
        "name": "Ember Drive",
        "rarity": "common",
        "value": 2,
        "element": "fire",
        "method": "offense",
        "effect": {"trigger": "on_hit", "magnitude": 0.12, "condition": "hit enemy"},
        "counters": ["brute"],
    },
    {
        "id": "frost_guard",
        "name": "Frost Guard",
        "rarity": "uncommon",
        "value": 1,
        "element": "ice",
        "method": "defense",
        "effect": {"trigger": "on_take_hit", "magnitude": 0.10, "condition": "when damaged"},
        "counters": ["skirmisher"],
    },
    {
        "id": "venom_hex",
        "name": "Venom Hex",
        "rarity": "rare",
        "value": 3,
        "element": "poison",
        "method": "offense",
        "effect": {"trigger": "on_hit", "magnitude": 0.18, "condition": "poisoned target"},
        "counters": ["caster"],
    },
    {
        "id": "stone_steadfast",
        "name": "Stone Steadfast",
        "rarity": "rare",
        "value": 2,
        "element": "physical",
        "method": "defense",
        "effect": {"trigger": "start_of_turn", "magnitude": 0.08, "condition": "if hp below 50%"},
        "counters": ["tank"],
    },
    {
        "id": "arcane_resonance",
        "name": "Arcane Resonance",
        "rarity": "epic",
        "value": 4,
        "element": "arcane",
        "method": "utility",
        "effect": {"trigger": "start_of_turn", "magnitude": 0.14, "condition": "on your turn"},
        "counters": ["summoner"],
    },
    {
        "id": "weight_of_fear",
        "name": "Weight of Fear",
        "rarity": "common",
        "value": -2,
        "element": "physical",
        "method": "drawback",
        "effect": {"trigger": "on_hit", "magnitude": -0.10, "condition": "cannot dodge"},
        "counters": ["skirmisher"],
    },
    {
        "id": "blood_pact",
        "name": "Blood Pact",
        "rarity": "uncommon",
        "value": 4,
        "element": "physical",
        "method": "amplifier",
        "effect": {"trigger": "on_hit", "magnitude": 0.20, "condition": "if you already have Weight of Fear equipped"},
        "counters": ["brute"],
        "budget_modifier": 1,
    },
    {
        "id": "void_anchor",
        "name": "Void Anchor",
        "rarity": "epic",
        "value": -3,
        "element": "arcane",
        "method": "drawback",
        "effect": {"trigger": "on_take_hit", "magnitude": -0.15, "condition": "cannot guard"},
        "counters": ["caster"],
    },
    {
        "id": "lattice_of_stars",
        "name": "Lattice of Stars",
        "rarity": "legendary",
        "value": 5,
        "element": "arcane",
        "method": "amplifier",
        "effect": {"trigger": "start_of_turn", "magnitude": 0.25, "condition": "if you already carry a drawback rune"},
        "counters": ["summoner"],
        "budget_modifier": 2,
    },
    {
        "id": "shatter_chain",
        "name": "Shatter Chain",
        "rarity": "legendary",
        "value": -1,
        "element": "poison",
        "method": "drawback",
        "effect": {"trigger": "on_hit", "magnitude": -0.05, "condition": "cannot trigger criticals"},
        "counters": ["tank"],
    },
    {
        "id": "starlit_serpent",
        "name": "Starlit Serpent",
        "rarity": "rare",
        "value": 3,
        "element": "poison",
        "method": "offense",
        "effect": {"trigger": "on_hit", "magnitude": 0.16, "condition": "against summoned enemies"},
        "counters": ["summoner"],
    },
    {
        "id": "bastion_slot",
        "name": "Bastion Slot",
        "rarity": "rare",
        "value": 1,
        "element": "physical",
        "method": "utility",
        "effect": {"trigger": "always", "magnitude": 0.0, "condition": "adds one slot"},
        "slot_modifier": 1,
    },
]


def _spawn_rune_from_pool(seed: int | None = None) -> Rune:
    rng = random.Random(seed)
    template = rng.choice(RUNE_POOL)
    return Rune(**template)


def get_default_rune_slots() -> int:
    return DEFAULT_RUNE_SLOT_CAPACITY


def get_default_rune_budget() -> int:
    return DEFAULT_RUNE_BUDGET_CAP


def calculate_rune_value(rune: dict[str, Any]) -> int:
    if isinstance(rune, Rune):
        return int(rune.value or 0)
    if isinstance(rune, dict):
        if "value" in rune and rune.get("value") is not None:
            return int(rune.get("value", 0) or 0)
        effects = rune.get("effects", []) or []
        if isinstance(effects, list):
            return int(sum(float(e.get("value", 0.0) or 0.0) for e in effects if isinstance(e, dict)))
    return 0


def _slot_modifier_total(player: Player) -> int:
    total = 0
    rune_items = list(getattr(player, "rune_items", []) or [])
    by_id = {str(r.get("id", "")): r for r in rune_items}
    for rid in list(getattr(player, "rune_loadout", []) or []):
        if not rid:
            continue
        rune = by_id.get(str(rid))
        if not isinstance(rune, dict):
            continue
        total += int(rune.get("slot_modifier", 0) or 0)
    return total


def rune_slot_capacity(player: Player | None = None) -> int:
    cap = RUNE_SLOT_CAPACITY_BASE
    if player is not None:
        cap += _slot_modifier_total(player)
    return max(cap, DEFAULT_RUNE_SLOT_CAPACITY)


def rune_budget_capacity(player: Player | None = None) -> int:
    base = RUNE_BUDGET_CAP_BASE
    if player is not None:
        rune_items = list(getattr(player, "rune_items", []) or [])
        loadout = list(getattr(player, "rune_loadout", []) or [])
        by_id = {str(r.get("id", "")): r for r in rune_items}
        for rid in loadout:
            if not rid:
                continue
            rune = by_id.get(str(rid))
            if not isinstance(rune, dict):
                continue
            base += int(rune.get("budget_modifier", 0) or 0)
    return base


def _loadout_value(loadout: list[str | None], rune_items: list[dict[str, Any]]) -> int:
    by_id = {str(r.get("id", "")): r for r in rune_items}
    total = 0
    for rid in loadout:
        if not rid:
            continue
        rune = by_id.get(str(rid))
        if not isinstance(rune, dict):
            continue
        total += calculate_rune_value(rune)
    return total


def sync_rune_loadout(player: Player) -> list[str | None]:
    player.sync_rune_loadout()
    ids = {str(r.get("id", "")) for r in (player.rune_items or [])}
    cleaned = []
    for rid in player.rune_loadout:
        rid_s = str(rid) if rid else None
        cleaned.append(rid_s if rid_s in ids else None)
    player.rune_loadout = cleaned
    return list(player.rune_loadout)


def loadout_summary(player: Player) -> dict[str, Any]:
    slot_cap = rune_slot_capacity(player)
    loadout = list(getattr(player, "rune_loadout", []) or [])[:slot_cap]
    rune_items = list(getattr(player, "rune_items", []) or [])
    total_value = _loadout_value(loadout, rune_items)
    budget_cap = rune_budget_capacity(player)
    bonus_active = total_value >= budget_cap
    return {
        "capacity": slot_cap,
        "budget": budget_cap,
        "total_value": total_value,
        "bonus_active": bonus_active,
        "bonus_effect": "Overloaded Sigil: +5% crit chance" if bonus_active else "",
        "loadout": loadout,
    }


def validate_rune_loadout(player: Player) -> dict[str, Any]:
    slot_cap = rune_slot_capacity(player)
    loadout = list(getattr(player, "rune_loadout", []) or [])[:slot_cap]
    rune_items = list(getattr(player, "rune_items", []) or [])

    if len(loadout) > slot_cap:
        return {"ok": False, "error": f"Loadout exceeds the {slot_cap} slot cap"}

    total_value = _loadout_value(loadout, rune_items)
    budget_cap = rune_budget_capacity(player)
    if total_value > budget_cap:
        return {"ok": False, "error": f"Loadout value {total_value} exceeds cap {budget_cap}"}

    if total_value == budget_cap:
        return {"ok": True, "bonus_active": True, "bonus_effect": "Overloaded Sigil: +5% crit chance", "total_value": total_value}

    return {"ok": True, "bonus_active": False, "total_value": total_value}


def collect_rune_mods(player: Player) -> dict[str, Any]:
    sync_rune_loadout(player)
    by_id = {str(r.get("id", "")): r for r in (player.rune_items or [])}
    mods = {
        "attack_mult": 0.0,
        "defense_mult": 0.0,
        "dodge_flat": 0.0,
        "lifesteal": 0.0,
        "thorns": 0.0,
        "crit_bonus": 0.0,
    }
    for rid in (player.rune_loadout or []):
        if not rid:
            continue
        rune = by_id.get(str(rid))
        if not isinstance(rune, dict):
            continue
        for eff in rune.get("effects", []) or []:
            t = str(eff.get("type", "") or "")
            v = float(eff.get("value", 0.0) or 0.0)
            if t in mods:
                mods[t] += v

    amp = amplifier_bonus(player)
    if amp > 0:
        for key in list(mods.keys()):
            if mods[key] > 0:
                mods[key] = round(mods[key] * (1.0 + amp), 4)

    mods["attack_mult"] = min(2.0, mods["attack_mult"])
    mods["defense_mult"] = min(1.5, mods["defense_mult"])
    mods["dodge_flat"] = min(0.20, mods["dodge_flat"])
    mods["lifesteal"] = min(0.30, mods["lifesteal"])
    mods["thorns"] = min(0.25, mods["thorns"])
    mods["crit_bonus"] = min(0.25, mods["crit_bonus"])
    mods["amp_bonus"] = amp
    return mods


def roll_rune_rarity(luck_bonus: float = 0.0) -> str:
    weights = dict(RUNE_CHEST_WEIGHTS)
    lb = max(0.0, float(luck_bonus))
    if lb > 0:
        weights["rare"] += int(40 * lb)
        weights["epic"] += int(20 * lb)
        weights["legendary"] += int(8 * lb)
        weights["mythic"] += int(2 * lb)
    weights["relic"] = max(0, int(weights.get("relic", 0)))

    total = sum(max(0, int(v)) for v in weights.values())
    pick = random.randint(1, max(1, total))
    run = 0
    for rarity in RUNE_BUILD_RARITIES:
        w = max(0, int(weights.get(rarity, 0)))
        run += w
        if pick <= run:
            return rarity
    return "common"


def generate_rune_effects(rarity: str) -> list[dict[str, Any]]:
    pool = list(RUNE_EFFECT_POOL.get(rarity, RUNE_EFFECT_POOL["common"]))
    random.shuffle(pool)
    count = 1
    if rarity in ("epic", "legendary"):
        count = random.randint(1, 2)
    elif rarity in ("mythic", "supreme", "relic"):
        count = random.randint(2, 3)

    effects = []
    for eff, lo, hi in pool[:count]:
        effects.append({
            "type": eff,
            "value": round(random.uniform(float(lo), float(hi)), 4),
        })
    return effects


def generate_build_rune(player: Player) -> dict[str, Any]:
    rarity = roll_rune_rarity(player.loot_luck)
    rid = f"rune_{random.randint(100000, 999999)}_{random.randint(10, 99)}"
    name = f"{random.choice(RUNE_NAME_PARTS['prefix'])} {random.choice(RUNE_NAME_PARTS['core'])} {random.choice(RUNE_NAME_PARTS['suffix'])}"

    base = {
        "id": rid,
        "name": name,
        "rarity": rarity,
        "effects": generate_rune_effects(rarity),
        "source": "chest",
        "upgrade_level": 0,
        "max_upgrade": int(RUNE_UPGRADE_MAX.get(rarity, 5)),
        "value": 1,
        "element": "physical",
        "method": "utility",
        "effect": {"trigger": "always", "magnitude": 0.0, "condition": ""},
        "counters": [],
        "budget_modifier": None,
        "slot_modifier": None,
        "positional_buff": None,
    }
    if rarity == "legendary":
        base["value"] = 3
        base["element"] = "arcane"
        base["method"] = "amplifier"
        base["budget_modifier"] = 1
    elif rarity == "rare":
        base["value"] = 1
        base["element"] = "ice"
    elif rarity == "epic":
        base["value"] = 2
        base["element"] = "fire"
    return base


def is_amplifier(rune: dict[str, Any]) -> bool:
    return isinstance(rune, dict) and str(rune.get("kind", "") or "") == AMPLIFIER_KIND


def generate_amplifier_rune(recipe_id: str) -> dict[str, Any] | None:
    key = str(recipe_id or "").strip().lower()
    recipe = AMPLIFIER_RECIPES.get(key)
    if not recipe:
        return None
    return {
        "id": f"amp_{random.randint(100000, 999999)}_{random.randint(10, 99)}",
        "kind": AMPLIFIER_KIND,
        "recipe": key,
        "name": recipe["name"],
        "tier": int(recipe["tier"]),
        "amp_bonus": float(recipe["amp_bonus"]),
        "equipped": False,
        "rarity": "rare" if int(recipe["tier"]) == 1 else "epic",
        "effects": [],
        "source": "runecrafting",
    }


def equipped_amplifier(player: Player) -> dict[str, Any] | None:
    for rune in (player.rune_items or []):
        if is_amplifier(rune) and bool(rune.get("equipped", False)):
            return rune
    return None


def amplifier_bonus(player: Player) -> float:
    amp = equipped_amplifier(player)
    if not amp:
        return 0.0
    return min(AMPLIFIER_BONUS_CAP, max(0.0, float(amp.get("amp_bonus", 0.0) or 0.0)))


def set_equipped_amplifier(player: Player, rune_id: str | None) -> dict[str, Any] | None:
    target = None
    for rune in (player.rune_items or []):
        if not is_amplifier(rune):
            continue
        rune["equipped"] = False
        if rune_id and str(rune.get("id", "")) == str(rune_id):
            target = rune
    if target is not None:
        target["equipped"] = True
    return target


def find_rune(player: Player, rune_id: str) -> dict[str, Any] | None:
    rid = str(rune_id or "").strip()
    if not rid:
        return None
    for rune in player.rune_items:
        if str(rune.get("id", "")) == rid:
            return rune
    return None


def remove_rune_by_id(player: Player, rune_id: str) -> dict[str, Any] | None:
    rid = str(rune_id or "").strip()
    if not rid:
        return None
    found = None
    kept = []
    for rune in (player.rune_items or []):
        if found is None and str(rune.get("id", "")) == rid:
            found = rune
        else:
            kept.append(rune)
    if found is None:
        return None
    player.rune_items = kept
    sync_rune_loadout(player)
    player.rune_loadout = [None if str(x or "") == rid else x for x in (player.rune_loadout or [])]
    sync_rune_loadout(player)
    return found


def rune_sale_value(rune: dict[str, Any]) -> int:
    rarity = str(rune.get("rarity", "common") or "common").lower()
    base = int(RUNE_SELL_BASE.get(rarity, 25) or 25)
    eff_count = len(rune.get("effects", []) or [])
    upgrade_level = int(rune.get("upgrade_level", 0) or 0)
    infusions = int(rune.get("relic_infusions", 0) or 0)
    mult = 1.0 + (eff_count * 0.10) + (upgrade_level * 0.14) + (infusions * 0.10)
    return max(1, int(base * mult))


def rune_dismantle_value(rune: dict[str, Any]) -> dict[str, int]:
    rarity = str(rune.get("rarity", "common") or "common").lower()
    base = dict(RUNE_DISMANTLE_BASE.get(rarity, {"relic": 1, "essence": 1}))
    relics = int(base.get("relic", 1) or 1)
    essence = int(base.get("essence", 1) or 1)
    upgrade_level = int(rune.get("upgrade_level", 0) or 0)
    infusions = int(rune.get("relic_infusions", 0) or 0)
    relics += max(0, int(upgrade_level * 0.85)) + max(0, int(infusions * 0.7))
    essence += max(0, int(upgrade_level * 0.55))
    return {"relic": max(1, relics), "essence": max(1, essence)}


def rune_upgrade_cost(rarity: str, level: int) -> int:
    base_cost = int(RUNE_UPGRADE_COSTS.get(rarity, 1) or 1)
    return max(1, int(base_cost * (1 + (int(level) * 0.85))))


def rune_relic_infuse_cap(rarity: str) -> int:
    return int(RUNE_RELIC_INFUSE_CAP.get(str(rarity or "common").lower(), 0) or 0)


def catalog_runes() -> list[dict[str, Any]]:
    return [dict(r) for r in RUNE_POOL]
