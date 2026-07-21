# engine/passives.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random


# ---- Passive schema (flexible) ----
# We support passives being either:
# 1) dicts: {"id": "sharpness", "value": 3} or {"id":"crit_chance", "value":0.06}
# 2) strings: "sharpness+3", "crit_chance+6%" (best-effort parse)
#
# This adapter lets you keep your existing loot format.


@dataclass
class Passive:
    id: str
    value: float = 0.0
    meta: Dict[str, Any] = None


def _parse_percent(s: str) -> Optional[float]:
    s = s.strip()
    if s.endswith("%"):
        try:
            return float(s[:-1].strip()) / 100.0
        except Exception:
            return None
    return None


def _try_parse_string_passive(p: str) -> Optional[Passive]:
    # Examples:
    # "sharpness+3"
    # "crit_chance+6%"
    # "damage_reduction+5%"
    raw = p.strip().replace(" ", "")
    if "+" in raw:
        pid, val = raw.split("+", 1)
        pct = _parse_percent(val)
        if pct is not None:
            return Passive(id=pid, value=pct, meta={"is_percent": True})
        try:
            return Passive(id=pid, value=float(val), meta={"is_percent": False})
        except Exception:
            return Passive(id=pid, value=0.0, meta={"is_percent": False})
    return Passive(id=raw, value=0.0, meta={})


def normalize_passives(passives: Any) -> List[Passive]:
    if not passives:
        return []
    out: List[Passive] = []
    if isinstance(passives, list):
        for p in passives:
            if isinstance(p, dict):
                out.append(Passive(
                    id=str(p.get("id", "")).strip(),
                    value=float(p.get("value", 0.0) or 0.0),
                    meta={k: v for k, v in p.items() if k not in ("id", "value")}
                ))
            elif isinstance(p, str):
                parsed = _try_parse_string_passive(p)
                if parsed and parsed.id:
                    out.append(parsed)
    elif isinstance(passives, dict):
        # { "sharpness": 3, "crit_chance": 0.05 } style
        for k, v in passives.items():
            out.append(Passive(id=str(k).strip(), value=float(v or 0.0), meta={}))
    return [p for p in out if p.id]


def collect_equipment_passives(player: Any) -> List[Passive]:
    """
    Tries common shapes:
      player.weapon.passives
      player.armor.passives
      player.equipment = {"weapon": {...}, "armor": {...}}
      player.equipment = [item,...]
    """
    passives: List[Passive] = []

    # weapon/armor attributes
    weapon = getattr(player, "weapon", None)
    armor = getattr(player, "armor", None)
    passives += normalize_passives(getattr(weapon, "passives", None) if weapon else None)
    passives += normalize_passives(getattr(armor, "passives", None) if armor else None)

    # equipment container
    eq = getattr(player, "equipment", None)
    if isinstance(eq, dict):
        for slot in ("weapon", "armor", "helm", "ring", "amulet", "boots", "gloves"):
            item = eq.get(slot)
            if isinstance(item, dict):
                passives += normalize_passives(item.get("passives"))
            else:
                passives += normalize_passives(getattr(item, "passives", None) if item else None)
    elif isinstance(eq, list):
        for item in eq:
            if isinstance(item, dict):
                passives += normalize_passives(item.get("passives"))
            else:
                passives += normalize_passives(getattr(item, "passives", None) if item else None)

    return passives


# ---- Supported passive IDs (you can add more anytime) ----
#
# Offense:
#   sharpness (flat dmg)
#   damage_percent (+% dmg)
#   crit_chance (+ chance, 0.05 = +5%)
#   crit_damage (+ multiplier add, 0.25 = +25% crit dmg)
#   lifesteal (portion of dealt dmg healed, 0.05 = 5%)
#   bleed_chance (chance to apply bleed)
#   bleed_damage (bleed tick percent of attacker STR-scaled or damage-based)
#
# Defense:
#   damage_reduction (0.05 = 5% less taken)
#   flat_damage_reduction (flat reduce)
#   thorns (reflect % of taken damage)
#
# Utility hooks:
#   boss_slayer (+% dmg vs bosses)
#   elite_slayer (+% dmg vs elites)


def sum_values(passives: List[Passive], pid: str) -> float:
    return sum(p.value for p in passives if p.id == pid)


def chance_roll(rng: random.Random, chance: float) -> bool:
    chance = max(0.0, min(1.0, chance))
    return rng.random() < chance


def classify_enemy(enemy: Any) -> str:
    # best effort: enemy.tier or enemy.kind
    tier = (getattr(enemy, "tier", None) or getattr(enemy, "kind", None) or "normal")
    tier = str(tier).lower()
    if "boss" in tier:
        return "boss"
    if "elite" in tier:
        return "elite"
    return "normal"
