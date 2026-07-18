from __future__ import annotations

from typing import Any, Dict, List, Optional
import random

from models.passive import PassiveModel, PassiveEffect

# ---- Limits ----
MAX_PASSIVES_BY_RARITY = {
    "common": 0,
    "rare": 1,
    "epic": 2,
    "legendary": 4,
    "mythic": 6,
    "relic": 10,
}

MAX_EFFECTS_PER_PASSIVE = 3

CURSED_EFFECT_TYPES = {"self_damage", "stat_drain", "enemy_buff"}

# value bounds by effect type
EFFECT_VALUE_BOUNDS = {
    "damage_mult": (0.02, 0.60),
    "shield": (5, 60),
    "lifesteal": (0.02, 0.15),
    "bleed": (0.02, 0.25),
    "dot": (2, 15),
    "thorns": (0.02, 0.35),
    "dodge_mod": (-0.15, 0.20),
    "self_damage": (1, 12),
    "stat_drain": (1, 6),
    "enemy_buff": (0.05, 0.35),
}

PASSIVE_CHANCE_BOUNDS = (0.0, 1.0)
EFFECT_CHANCE_BOUNDS = (0.0, 1.0)
DURATION_BOUNDS = (0, 4)
STACK_BOUNDS = (1, 5)
THRESHOLD_BOUNDS = (0.10, 0.60)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _ensure_mods(entity: Any) -> Dict[str, Any]:
    mods = getattr(entity, "combat_mods", None)
    if not isinstance(mods, dict):
        mods = {}
    mods.setdefault("damage_mult", 0.0)
    mods.setdefault("damage_taken_mult", 0.0)
    mods.setdefault("dodge_mod", 0.0)
    mods.setdefault("lifesteal", 0.0)
    mods.setdefault("thorns", 0.0)
    mods.setdefault("shield", 0.0)
    mods.setdefault("stat_drains", [])
    mods.setdefault("enemy_buffs", [])
    setattr(entity, "combat_mods", mods)
    return mods


def chance_roll(rng: random.Random, chance: float) -> bool:
    chance = _clamp(float(chance), 0.0, 1.0)
    return rng.random() < chance


def normalize_passives(passives: Any) -> List[PassiveModel]:
    if not passives:
        return []
    out: List[PassiveModel] = []
    if isinstance(passives, list):
        for p in passives:
            if isinstance(p, PassiveModel):
                out.append(p)
            elif isinstance(p, dict):
                out.append(PassiveModel(**p))
    elif isinstance(passives, dict):
        out.append(PassiveModel(**passives))
    return out


def is_cursed(passive: PassiveModel) -> bool:
    for e in passive.effects:
        if e.type in CURSED_EFFECT_TYPES:
            return True
    return False


def clamp_passives(passives: Any, rarity: str) -> List[PassiveModel]:
    rarity = str(rarity).lower().strip()
    max_count = MAX_PASSIVES_BY_RARITY.get(rarity, 0)

    normalized = normalize_passives(passives)[:max_count]

    for p in normalized:
        p.effects = p.effects[:MAX_EFFECTS_PER_PASSIVE]

        p.chance = _clamp(float(p.chance or 0.0), *PASSIVE_CHANCE_BOUNDS)
        if p.trigger == "below_hp":
            p.threshold = _clamp(float(p.threshold or 0.0), *THRESHOLD_BOUNDS)
        else:
            p.threshold = 0.0

        for e in p.effects:
            bounds = EFFECT_VALUE_BOUNDS.get(e.type)
            if bounds:
                e.value = _clamp(float(e.value), bounds[0], bounds[1])

            e.chance = _clamp(float(e.chance or 0.0), *EFFECT_CHANCE_BOUNDS)
            e.duration = int(_clamp(int(e.duration or 0), *DURATION_BOUNDS))
            e.stacks = int(_clamp(int(e.stacks or 1), *STACK_BOUNDS))

            if e.type == "enemy_buff":
                e.target = "enemy"
            if e.type == "self_damage":
                e.target = "self"

            if e.type in ("damage_mult", "lifesteal", "thorns", "dodge_mod", "enemy_buff", "bleed"):
                e.scaling = "percent"
            else:
                e.scaling = "flat"

            if e.type in ("bleed", "dot", "stat_drain", "enemy_buff") and e.duration <= 0:
                e.duration = 2

            if e.type == "stat_drain" and not e.stat:
                e.stat = "str"

        p.cursed = is_cursed(p)

    return normalized


def collect_equipment_passives(player: Any) -> List[PassiveModel]:
    passives: List[PassiveModel] = []

    weapon = getattr(player, "weapon", None)
    armor = getattr(player, "armor", None)

    if weapon:
        passives += normalize_passives(getattr(weapon, "passives", None))
    if armor:
        passives += normalize_passives(getattr(armor, "passives", None))

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


def resolve_triggered_effects(
    passives: List[PassiveModel],
    trigger: str,
    source: Any,
    target: Any,
    context: Optional[Dict[str, Any]] = None,
    rng: Optional[random.Random] = None,
) -> List[Dict[str, Any]]:
    rng = rng or random.Random()
    context = context or {}
    trigger = str(trigger).lower().strip()

    effects: List[Dict[str, Any]] = []

    for p in passives:
        if p.trigger != trigger:
            continue

        if p.trigger == "below_hp":
            source_hp = float(context.get("source_hp", getattr(source, "hp", 0.0)) or 0.0)
            source_max = float(context.get("source_max_hp", getattr(source, "max_hp", source_hp)) or source_hp)
            if source_max <= 0:
                continue
            if (source_hp / source_max) > float(p.threshold or 0.0):
                continue

        if not chance_roll(rng, p.chance):
            continue

        for e in p.effects:
            if not chance_roll(rng, e.chance):
                continue
            effects.append({
                "passive_name": p.name,
                "cursed": bool(p.cursed),
                "type": e.type,
                "target": e.target,
                "value": float(e.value),
                "duration": int(e.duration or 0),
                "stacks": int(e.stacks or 1),
                "stat": e.stat,
                "scaling": e.scaling,
            })

    return effects


def apply_effects(
    source: Any,
    target: Any,
    effects: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from engine.status_effects import add_status

    context = context or {}
    applied: List[Dict[str, Any]] = []
    total_self_damage = 0.0

    for e in effects:
        etype = e["type"]
        tgt = source if e["target"] == "self" else target
        mods = _ensure_mods(tgt)

        if etype == "damage_mult":
            if e["target"] == "self":
                mods["damage_mult"] += e["value"]
            else:
                mods["damage_taken_mult"] += e["value"]
        elif etype == "shield":
            mods["shield"] += e["value"]
        elif etype == "lifesteal":
            mods["lifesteal"] += e["value"]
        elif etype == "thorns":
            mods["thorns"] += e["value"]
        elif etype == "dodge_mod":
            mods["dodge_mod"] += e["value"]
        elif etype == "bleed":
            base = float(context.get("damage", 0.0) or 0.0)
            potency = base * e["value"] if e["scaling"] == "percent" else e["value"]
            add_status(tgt, "bleed", turns=max(1, e["duration"]), potency=potency)
        elif etype == "dot":
            add_status(tgt, "burn", turns=max(1, e["duration"]), potency=e["value"])
        elif etype == "self_damage":
            if e["scaling"] == "percent":
                max_hp = float(getattr(source, "max_hp", 1.0) or 1.0)
                dmg = max_hp * e["value"]
            else:
                dmg = e["value"]
            if dmg > 0:
                hp = float(getattr(source, "hp", 1.0) or 1.0)
                new_hp = max(0.0, hp - dmg)
                setattr(source, "hp", new_hp)
                total_self_damage += dmg
        elif etype == "stat_drain":
            mods["stat_drains"].append({
                "stat": e["stat"] or "str",
                "value": e["value"],
                "duration": max(1, e["duration"]),
            })
        elif etype == "enemy_buff":
            mods["enemy_buffs"].append({
                "value": e["value"],
                "duration": max(1, e["duration"]),
            })

        applied.append(e)

    return {
        "effects_applied": applied,
        "total_self_damage": round(total_self_damage, 2),
        "source_mods": getattr(source, "combat_mods", {}),
        "target_mods": getattr(target, "combat_mods", {}),
    }


def resolve_and_apply(
    passives: List[PassiveModel],
    trigger: str,
    source: Any,
    target: Any,
    context: Optional[Dict[str, Any]] = None,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    effects = resolve_triggered_effects(
        passives=passives,
        trigger=trigger,
        source=source,
        target=target,
        context=context,
        rng=rng,
    )
    applied = apply_effects(source, target, effects, context=context)
    return {
        "trigger": trigger,
        "effects": effects,
        "applied": applied,
    }
