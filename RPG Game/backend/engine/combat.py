# engine/combat.py
from __future__ import annotations

from typing import Any, Dict
import random

from engine.boss_ai import is_boss, roll_boss_intent
from engine.passive_system import collect_equipment_passives, resolve_and_apply
from engine.status_effects import (
    add_status,
    apply_incoming_multiplier,
    apply_outgoing_multiplier,
    tick_statuses,
)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _clear_temp_mods(entity: Any) -> None:
    setattr(entity, "combat_mods", {})


def _enemy_base_attack(enemy: Any) -> float:
    return max(1.0, float(getattr(enemy, "attack", 1.0) or 1.0))


def _enemy_base_defense(enemy: Any) -> float:
    return max(0.0, float(getattr(enemy, "defense", 0.0) or 0.0))


def _player_base_attack(player: Any) -> float:
    # Prefer model-derived attack stat; fallback to STR if needed.
    atk = float(getattr(player, "attack", 0.0) or 0.0)
    if atk > 0:
        return atk
    str_ = float(getattr(player, "strength", 1.0) or 1.0)
    return max(1.0, str_)


def _player_base_defense(player: Any) -> float:
    d = float(getattr(player, "defense", 0.0) or 0.0)
    if d > 0:
        return d
    vit = float(getattr(player, "vitality", 0.0) or 0.0)
    return max(0.0, vit * 0.6)


def _apply_shield(entity: Any, dmg: float) -> tuple[float, float]:
    mods = getattr(entity, "combat_mods", {}) or {}
    shield = float(mods.get("shield", 0.0) or 0.0)
    if shield <= 0:
        return dmg, 0.0

    absorbed = min(dmg, shield)
    mods["shield"] = max(0.0, shield - absorbed)
    entity.combat_mods = mods
    return max(0.0, dmg - absorbed), round(absorbed, 2)


def player_attack(player: Any, enemy: Any, rng_seed: int | None = None) -> Dict:
    rng = random.Random(rng_seed)
    passives = collect_equipment_passives(player)
    _clear_temp_mods(player)
    _clear_temp_mods(enemy)

    enemy_tick = tick_statuses(enemy)

    start_fx = resolve_and_apply(passives, "start_of_turn", player, enemy, rng=rng)
    below_hp_fx = resolve_and_apply(
        passives,
        "below_hp",
        player,
        enemy,
        context={
            "source_hp": float(getattr(player, "hp", 0.0) or 0.0),
            "source_max_hp": float(getattr(player, "max_hp", 1.0) or 1.0),
        },
        rng=rng,
    )

    pmods = getattr(player, "combat_mods", {}) or {}
    emods = getattr(enemy, "combat_mods", {}) or {}

    dmg = _player_base_attack(player)
    dmg *= (1.0 + float(pmods.get("damage_mult", 0.0) or 0.0))

    enemy_def = _enemy_base_defense(enemy)
    dmg = max(0.0, dmg - enemy_def)

    dmg, outgoing_notes = apply_outgoing_multiplier(player, dmg)

    crit_chance = _clamp(0.05, 0.0, 0.60)
    did_crit = rng.random() < crit_chance
    if did_crit:
        dmg *= 1.5

    dmg *= (1.0 + float(emods.get("damage_taken_mult", 0.0) or 0.0))
    dmg, incoming_notes = apply_incoming_multiplier(enemy, dmg)

    dmg = round(max(1.0, dmg), 2)

    enemy_hp = float(getattr(enemy, "hp", 1.0) or 1.0)
    new_enemy_hp = max(0.0, enemy_hp - dmg)
    setattr(enemy, "hp", new_enemy_hp)

    on_hit_fx = resolve_and_apply(passives, "on_hit", player, enemy, context={"damage": dmg}, rng=rng)

    # Lifesteal supports both direct passive effect and combat_mod buff.
    pmods = getattr(player, "combat_mods", {}) or {}
    lifesteal = _clamp(float(pmods.get("lifesteal", 0.0) or 0.0), 0.0, 0.40)
    healed = round(dmg * lifesteal, 2) if lifesteal > 0 else 0.0
    if healed > 0:
        php = float(getattr(player, "hp", 1.0) or 1.0)
        pmax = float(getattr(player, "max_hp", php) or php)
        setattr(player, "hp", min(pmax, php + healed))

    on_kill_fx = {"trigger": "on_kill", "effects": [], "applied": {}}
    if new_enemy_hp <= 0:
        on_kill_fx = resolve_and_apply(passives, "on_kill", player, enemy, context={"damage": dmg}, rng=rng)

    end_fx = resolve_and_apply(passives, "end_of_turn", player, enemy, context={"damage": dmg}, rng=rng)

    return {
        "event": "player_attack",
        "enemy_start_of_turn_ticks": enemy_tick,
        "damage": dmg,
        "crit": did_crit,
        "lifesteal_heal": healed,
        "enemy_hp": new_enemy_hp,
        "enemy_def": enemy_def,
        "outgoing_mods": outgoing_notes,
        "incoming_mods": incoming_notes,
        "passive_triggers": {
            "start_of_turn": start_fx,
            "below_hp": below_hp_fx,
            "on_hit": on_hit_fx,
            "on_kill": on_kill_fx,
            "end_of_turn": end_fx,
        },
        "enemy_status": getattr(enemy, "status", {}),
        "player_status": getattr(player, "status", {}),
    }


def enemy_attack(player: Any, enemy: Any, dodge_success: bool, rng_seed: int | None = None) -> Dict:
    rng = random.Random(rng_seed)
    passives = collect_equipment_passives(player)
    _clear_temp_mods(player)
    _clear_temp_mods(enemy)

    player_tick = tick_statuses(player)

    start_fx = resolve_and_apply(passives, "start_of_turn", player, enemy, rng=rng)
    below_hp_fx = resolve_and_apply(
        passives,
        "below_hp",
        player,
        enemy,
        context={
            "source_hp": float(getattr(player, "hp", 0.0) or 0.0),
            "source_max_hp": float(getattr(player, "max_hp", 1.0) or 1.0),
        },
        rng=rng,
    )

    base = _enemy_base_attack(enemy)

    intent = getattr(enemy, "intent", None)
    if is_boss(enemy):
        if not isinstance(intent, dict):
            intent = roll_boss_intent(enemy, rng_seed=rng.randint(1, 10_000_000))
    else:
        if not isinstance(intent, dict):
            intent = {"type": "basic", "name": "Basic Attack", "damage_mult": 1.0, "hits": 1, "telegraph": ""}

    hits = int(intent.get("hits", 1) or 1)
    dmg_mult = float(intent.get("damage_mult", 1.0) or 1.0)

    total_dmg = 0.0
    did_crit_any = False
    pdef = _player_base_defense(player)
    absorbed_total = 0.0

    for _ in range(hits):
        dmg = base * dmg_mult
        dmg, outgoing_notes_enemy = apply_outgoing_multiplier(enemy, dmg)

        if dodge_success:
            dodge_fx = resolve_and_apply(passives, "on_dodge", player, enemy, rng=rng)
            pmods = getattr(player, "combat_mods", {}) or {}
            dodge_mod = float(pmods.get("dodge_mod", 0.0) or 0.0)
            reduction = _clamp(0.55 + dodge_mod, 0.15, 0.90)
            dmg *= (1.0 - reduction)
        else:
            dodge_fx = {"trigger": "on_dodge", "effects": [], "applied": {}}

        dmg = max(0.0, dmg - pdef)
        if not dodge_success:
            # Failed dodge still takes chip damage even with high DEF.
            dmg = max(1.0, dmg)

        pmods = getattr(player, "combat_mods", {}) or {}
        dmg *= (1.0 + float(pmods.get("damage_taken_mult", 0.0) or 0.0))
        dmg, incoming_notes_player = apply_incoming_multiplier(player, dmg)

        enemy_crit = _clamp(float(getattr(enemy, "crit_chance", 0.03) or 0.03), 0.0, 0.25)
        did_crit = rng.random() < enemy_crit
        if did_crit:
            dmg *= 1.5
            did_crit_any = True

        dmg = round(max(0.0, dmg), 2)
        dmg, absorbed = _apply_shield(player, dmg)
        absorbed_total += absorbed
        total_dmg += dmg

    total_dmg = round(total_dmg, 2)

    # Ensure enemy turns still pressure the player when dodge fails,
    # but do not bypass explicit shielding.
    if not dodge_success and total_dmg <= 0.0 and absorbed_total <= 0.0:
        total_dmg = 1.0

    php = float(getattr(player, "hp", 1.0) or 1.0)
    new_php = max(0.0, php - total_dmg)
    setattr(player, "hp", new_php)

    on_take_hit_fx = resolve_and_apply(passives, "on_take_hit", player, enemy, context={"damage": total_dmg}, rng=rng)

    pmods = getattr(player, "combat_mods", {}) or {}
    thorns = _clamp(float(pmods.get("thorns", 0.0) or 0.0), 0.0, 0.60)
    reflected = round(total_dmg * thorns, 2) if thorns > 0 else 0.0
    if reflected > 0:
        ehp = float(getattr(enemy, "hp", 0.0) or 0.0)
        setattr(enemy, "hp", max(0.0, ehp - reflected))

    status_applied = None
    if is_boss(enemy):
        t = str(intent.get("type", "basic"))
        if t == "heavy":
            status_applied = add_status(player, "vulnerable", turns=2, potency=0.20)
        elif t == "multi":
            status_applied = add_status(player, "weak", turns=2, potency=0.15)

    next_intent = None
    if is_boss(enemy):
        next_intent = roll_boss_intent(enemy, rng_seed=rng.randint(1, 10_000_000))
        setattr(enemy, "intent", next_intent)

    end_fx = resolve_and_apply(passives, "end_of_turn", player, enemy, context={"damage": total_dmg}, rng=rng)

    return {
        "event": "enemy_attack",
        "player_start_of_turn_ticks": player_tick,
        "attack_name": intent.get("name", "Attack"),
        "hits": hits,
        "damage": total_dmg,
        "crit": did_crit_any,
        "dodge_success": dodge_success,
        "player_hp": new_php,
        "player_def": pdef,
        "shield_absorbed": round(absorbed_total, 2),
        "reflected_to_enemy": reflected,
        "enemy_hp": float(getattr(enemy, "hp", 0.0) or 0.0),
        "status_applied_to_player": status_applied,
        "next_intent": next_intent,
        "passive_triggers": {
            "start_of_turn": start_fx,
            "below_hp": below_hp_fx,
            "on_dodge": dodge_fx,
            "on_take_hit": on_take_hit_fx,
            "end_of_turn": end_fx,
        },
        "enemy_status": getattr(enemy, "status", {}),
        "player_status": getattr(player, "status", {}),
    }
