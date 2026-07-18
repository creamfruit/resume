from __future__ import annotations

from typing import Any, Dict


def _summed_rune_mods(player: Any) -> Dict[str, float]:
    mods: Dict[str, float] = {
        "attack_mult": 0.0,
        "defense_mult": 0.0,
        "lifesteal": 0.0,
        "thorns": 0.0,
        "shield": 0.0,
    }
    for rune in list(getattr(player, "rune_items", []) or []):
        if not isinstance(rune, dict):
            continue
        for effect in list(rune.get("effects", []) or []):
            if not isinstance(effect, dict):
                continue
            etype = str(effect.get("type", "") or "")
            target = str(effect.get("target", "") or "")
            if target not in ("", "self"):
                continue
            value = float(effect.get("value", 0.0) or 0.0)
            if etype == "damage_mult":
                mods["attack_mult"] += value
            elif etype == "shield":
                mods["shield"] += value
            elif etype == "lifesteal":
                mods["lifesteal"] += value
            elif etype == "thorns":
                mods["thorns"] += value
            elif etype == "defense_mult":
                mods["defense_mult"] += value
    return mods


def _equipment_attack(player: Any) -> int:
    weapon = getattr(player, "equipment", {}).get("weapon") if isinstance(getattr(player, "equipment", None), dict) else None
    armor = getattr(player, "equipment", {}).get("armor") if isinstance(getattr(player, "equipment", None), dict) else None
    weapon_power = int(getattr(weapon, "power", 0) or 0)
    armor_power = int(getattr(armor, "power", 0) or 0)
    return int(getattr(player, "base_attack", 0) or 0) + weapon_power + int(getattr(player, "strength", 0) or 0) * 2 + int(getattr(player, "dexterity", 0) or 0) // 2


def _equipment_defense(player: Any) -> int:
    weapon = getattr(player, "equipment", {}).get("weapon") if isinstance(getattr(player, "equipment", None), dict) else None
    armor = getattr(player, "equipment", {}).get("armor") if isinstance(getattr(player, "equipment", None), dict) else None
    weapon_power = int(getattr(weapon, "power", 0) or 0)
    armor_power = int(getattr(armor, "power", 0) or 0)
    return int(getattr(player, "base_defense", 0) or 0) + armor_power + int(getattr(player, "vitality", 0) or 0) * 2


def compute_derived_stats(player: Any) -> Dict[str, float]:
    rune_mods = _summed_rune_mods(player)
    attack = _equipment_attack(player)
    defense = _equipment_defense(player)
    crit = min(0.35, max(0.03, 0.03 + (float(getattr(player, "luck", 0) or 0) - 5) * 0.01))
    dodge = min(0.20, max(0.0, (float(getattr(player, "dexterity", 0) or 0) - 5) * 0.01))
    return {
        "attack": int(attack * (1.0 + rune_mods["attack_mult"])),
        "defense": int(defense * (1.0 + rune_mods["defense_mult"])),
        "crit_chance": round(crit, 3),
        "dodge_bonus": round(dodge, 3),
        "lifesteal": round(rune_mods["lifesteal"], 3),
        "thorns": round(rune_mods["thorns"], 3),
        "shield": round(rune_mods["shield"], 3),
    }
