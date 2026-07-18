# engine/boss_ai.py
from __future__ import annotations
from typing import Any, Dict
import random


def _hp_ratio(enemy: Any) -> float:
    hp = float(getattr(enemy, "hp", 1.0) or 1.0)
    mhp = float(getattr(enemy, "max_hp", hp) or hp)
    return 0.0 if mhp <= 0 else hp / mhp


def _ensure_fields(enemy: Any) -> None:
    if getattr(enemy, "max_hp", None) is None:
        setattr(enemy, "max_hp", float(getattr(enemy, "hp", 1.0) or 1.0))
    if getattr(enemy, "phase", None) is None:
        setattr(enemy, "phase", 0)
    if getattr(enemy, "intent", None) is None:
        setattr(enemy, "intent", {"type": "basic", "name": "Basic Attack"})


def _boss_run_state(enemy: Any) -> Dict[str, Any]:
    mods = getattr(enemy, "combat_mods", {}) or {}
    state = mods.get("boss_run_state", {}) if isinstance(mods.get("boss_run_state"), dict) else {}
    return dict(state or {})


def update_boss_phase(enemy: Any) -> int:
    _ensure_fields(enemy)
    r = _hp_ratio(enemy)
    if r <= 0.30:
        enemy.phase = 2
    elif r <= 0.70:
        enemy.phase = 1
    else:
        enemy.phase = 0
    return int(enemy.phase)


def roll_boss_intent(enemy: Any, rng_seed: int | None = None) -> Dict:
    """
    Decide what boss will do NEXT enemy turn.
    Store on enemy.intent. Returned intent is for UI telegraphing.
    """
    _ensure_fields(enemy)
    rng = random.Random(rng_seed)
    phase = update_boss_phase(enemy)
    run_state = _boss_run_state(enemy)
    reward_heat = float(run_state.get("reward_heat", 0.0) or 0.0)
    risk_pressure = float(run_state.get("risk_pressure", 0.0) or 0.0)
    finisher_window = bool(run_state.get("finisher_window", False))

    if phase == 0:
        weights = {"basic": 70, "heavy": 20, "multi": 10}
    elif phase == 1:
        weights = {"basic": 55, "heavy": 25, "multi": 20}
    else:
        weights = {"basic": 40, "heavy": 30, "multi": 30}

    if reward_heat > 0:
        weights["heavy"] += int(round(reward_heat * 24))
        weights["multi"] += int(round(reward_heat * 18))
        weights["basic"] = max(12, int(weights["basic"] - round(reward_heat * 20)))
    if risk_pressure > 0:
        weights["heavy"] += int(round(risk_pressure * 10))
        weights["multi"] += int(round(risk_pressure * 8))
    if finisher_window:
        weights["heavy"] += 10
        weights["multi"] += 8

    pick = rng.uniform(0, sum(weights.values()))
    running = 0.0
    choice = "basic"
    for k, w in weights.items():
        running += w
        if pick <= running:
            choice = k
            break

    if choice == "basic":
        intent = {
            "type": "basic",
            "name": "Basic Attack",
            "damage_mult": 1.0 + (reward_heat * 0.08),
            "dodge_difficulty_mult": 1.0,
            "hits": 1,
            "telegraph": "The boss raises its weapon.",
        }
    elif choice == "heavy":
        intent = {
            "type": "heavy",
            "name": "Heavy Slam",
            "damage_mult": 1.6 + (reward_heat * 0.18) + (0.10 if finisher_window else 0.0),
            "dodge_difficulty_mult": 1.35 + (reward_heat * 0.12),
            "hits": 1,
            "telegraph": "Charging a heavy slam... (harder to dodge)",
        }
    else:
        intent = {
            "type": "multi",
            "name": "Flurry",
            "damage_mult": 0.75 + (reward_heat * 0.08),
            "dodge_difficulty_mult": 1.15 + (reward_heat * 0.10),
            "hits": 4 if finisher_window else 3,
            "telegraph": "A fast flurry is coming... (multiple hits)",
        }

    mood = "calm"
    if reward_heat >= 0.66:
        mood = "predatory"
    elif reward_heat >= 0.33 or risk_pressure >= 0.40:
        mood = "hunting"
    if finisher_window:
        mood = "desperate"

    if mood == "predatory":
        intent["telegraph"] = f"{intent.get('telegraph', '')} The boss is feeding on your momentum."
    elif mood == "hunting":
        intent["telegraph"] = f"{intent.get('telegraph', '')} The boss senses an opening."
    elif mood == "desperate":
        intent["telegraph"] = f"{intent.get('telegraph', '')} Desperation is pushing the tempo."

    intent["boss_temper"] = {
        "mood": mood,
        "reward_heat": round(reward_heat, 3),
        "risk_pressure": round(risk_pressure, 3),
        "finisher_window": finisher_window,
    }

    enemy.intent = intent
    return intent


def is_boss(enemy: Any) -> bool:
    tier = str(getattr(enemy, "tier", "") or "").lower()
    return "boss" in tier
