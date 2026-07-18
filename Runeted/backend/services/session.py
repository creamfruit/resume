from typing import Dict, Any, Optional
import math
import random
from models.enemy import Enemy
from engine.boss_ai import is_boss, roll_enemy_intent

# Single-player in-memory session (for now)
SESSION: Dict[str, Any] = {
    "active": False,
    "risk": 0,
    "depth": 1,
    "room_index": 0,
    "rooms": [],          # list of dicts: {"type": room_type, "enemy": Enemy|None}
    "current_enemy": None,
    "modifiers": [],
    "log": [],
    "awaiting_enemy_attack": False,
    "pending_player_action": "",
    "boss_defeated": False,
    "can_leave": False,
    "start_snapshot": {},
}

def reset_session():
    SESSION["active"] = False
    SESSION["risk"] = 0
    SESSION["depth"] = 1
    SESSION["room_index"] = 0
    SESSION["rooms"] = []
    SESSION["current_enemy"] = None
    SESSION["modifiers"] = []
    SESSION["log"] = []
    SESSION["awaiting_enemy_attack"] = False
    SESSION["pending_player_action"] = ""
    SESSION["boss_defeated"] = False
    SESSION["can_leave"] = False
    SESSION["start_snapshot"] = {}

def start_session(depth: int, risk: int, rooms: list, modifiers: list | None = None, player: Any | None = None):
    reset_session()
    SESSION["active"] = True
    SESSION["risk"] = risk
    SESSION["depth"] = depth
    SESSION["rooms"] = rooms
    SESSION["modifiers"] = modifiers or []
    SESSION["room_index"] = 0
    SESSION["awaiting_enemy_attack"] = False
    SESSION["pending_player_action"] = ""
    SESSION["boss_defeated"] = False
    SESSION["can_leave"] = False
    if player is not None:
        resources = dict(getattr(player, "resources", {}) or {})
        SESSION["start_snapshot"] = {
            "gold": int(getattr(player, "gold", 0) or 0),
            "rune_essence": int(resources.get("rune_essence", 0) or 0),
            "arcane_chest": int(resources.get("arcane_chest", 0) or 0),
            "rune_relic": int(resources.get("rune_relic", 0) or 0),
        }
    SESSION["log"].append(f"Started dungeon depth {depth} (risk {risk})")
    if SESSION["modifiers"]:
        names = ", ".join([m.get("name", "Unknown") for m in SESSION["modifiers"]])
        SESSION["log"].append(f"Run modifiers: {names}")
    _load_current_enemy()

def _load_current_enemy():
    idx = SESSION["room_index"]
    if idx >= len(SESSION["rooms"]):
        SESSION["current_enemy"] = None
        return
    room = SESSION["rooms"][idx]
    enemy = room.get("enemy")
    room_type = str(room.get("type", "unknown")).lower()

    if isinstance(enemy, Enemy):
        _apply_room_pressure(enemy, room_type)
        SESSION["current_enemy"] = enemy
        _seed_enemy_intent(SESSION["current_enemy"], SESSION["risk"])
        SESSION["log"].append(f"Room {idx+1}: {room_type.upper()} vs {SESSION['current_enemy'].name}")
        return

    SESSION["current_enemy"] = None
    SESSION["log"].append(f"Room {idx+1}: {room_type.upper()}")

def _room_pressure_profile(room_index: int, total_rooms: int, risk: int, room_type: str) -> Dict[str, Any]:
    total = max(1, int(total_rooms or 1))
    idx = max(0, int(room_index or 0))
    progress = idx / total
    base = (max(0, int(risk or 0)) * 0.03) + (progress * 0.12)
    room_key = str(room_type or "combat").lower()
    if room_key == "boss":
        base += 0.10 + (max(0, int(risk or 0)) * 0.015)
    elif room_key == "combat":
        base += 0.03
    intensity = min(0.38, round(base, 3))
    return {
        "intensity": intensity,
        "hp_mult": round(intensity * (1.10 if room_key == "boss" else 0.80), 3),
        "attack_mult": round(intensity * (0.85 if room_key == "boss" else 0.65), 3),
        "defense_bonus": max(0, int(math.ceil(intensity * (4 if room_key == "boss" else 3)))),
        "crit_bonus": round(min(0.10, intensity * 0.18), 3),
        "intent_shift": 2 if intensity >= 0.24 else (1 if intensity >= 0.12 else 0),
        "enemy_phase_bonus": round(intensity * (0.35 if room_key == "boss" else 0.22), 3),
        "dodge_tax": round(intensity * (0.30 if room_key == "boss" else 0.18), 3),
        "label": "High" if intensity >= 0.24 else ("Medium" if intensity >= 0.12 else "Low"),
    }


def _apply_room_pressure(enemy: Enemy, room_type: str):
    mods = getattr(enemy, "combat_mods", {}) or {}
    if mods.get("room_pressure_applied"):
        enemy.combat_mods = mods
        return

    profile = _room_pressure_profile(
        room_index=int(SESSION.get("room_index", 0) or 0),
        total_rooms=len(list(SESSION.get("rooms", []) or [])),
        risk=int(SESSION.get("risk", 0) or 0),
        room_type=str(room_type or "combat"),
    )
    hp_mult = float(profile.get("hp_mult", 0.0) or 0.0)
    if hp_mult > 0:
        hp_before = float(getattr(enemy, "hp", 0.0) or 0.0)
        max_before = float(getattr(enemy, "max_hp", hp_before) or hp_before)
        hp_gain = max(1.0, round(max_before * hp_mult, 2))
        enemy.max_hp = int(round(max_before + hp_gain))
        enemy.hp = int(round(hp_before + hp_gain))
    attack_mult = float(profile.get("attack_mult", 0.0) or 0.0)
    if attack_mult > 0:
        enemy.attack = max(1, int(round(float(getattr(enemy, "attack", 1) or 1) * (1.0 + attack_mult))))
    defense_bonus = int(profile.get("defense_bonus", 0) or 0)
    if defense_bonus > 0:
        enemy.defense = int(getattr(enemy, "defense", 0) or 0) + defense_bonus
    crit_bonus = float(profile.get("crit_bonus", 0.0) or 0.0)
    if crit_bonus > 0:
        enemy.crit_chance = min(0.35, float(getattr(enemy, "crit_chance", 0.03) or 0.03) + crit_bonus)

    mods["room_pressure_applied"] = True
    mods["room_pressure"] = profile
    enemy.combat_mods = mods


def _seed_enemy_intent(enemy: Enemy, risk: int):
    if not isinstance(getattr(enemy, "intent", None), dict):
        enemy.intent = roll_enemy_intent(enemy, risk=risk)


def current_enemy() -> Optional[Enemy]:
    return SESSION["current_enemy"]

def current_room_type() -> Optional[str]:
    idx = SESSION["room_index"]
    if idx >= len(SESSION["rooms"]):
        return None
    return SESSION["rooms"][idx]["type"]

def advance_room():
    SESSION["room_index"] += 1
    _load_current_enemy()

def state(player: Any | None = None) -> Dict[str, Any]:
    enemy = SESSION["current_enemy"]
    room = current_room()
    affix = room.get("affix") if isinstance(room, dict) else None
    preview = []
    start = int(SESSION.get("room_index", 0) or 0)
    rooms = list(SESSION.get("rooms", []) or [])
    for idx, row in enumerate(rooms[start:start + 6], start=start):
        if not isinstance(row, dict):
            continue
        room_type = str(row.get("type", "unknown") or "unknown")
        affix_row = row.get("affix") if isinstance(row.get("affix"), dict) else None
        enemy_row = row.get("enemy")
        preview.append({
            "index": idx,
            "offset": idx - start,
            "type": room_type,
            "affix": affix_row.get("name", "") if affix_row else "",
            "has_enemy": isinstance(enemy_row, Enemy),
            "is_current": idx == start,
        })
    gains = {}
    boss_preview = {}
    current_pressure = {}
    boss_temper = {}
    cadence = {
        "next_boss_offset": None,
        "next_reward_offset": None,
        "next_recovery_offset": None,
        "next_hazard_offset": None,
        "remaining_combat_rooms": 0,
        "remaining_support_rooms": 0,
    }
    next_boss = None
    next_reward = None
    next_recovery = None
    next_hazard = None
    remaining_combat = 0
    remaining_support = 0
    for row in preview:
        room_type = str(row.get("type", "") or "").lower()
        if room_type in {"combat", "boss"}:
            remaining_combat += 1
        else:
            remaining_support += 1
        if row.get("is_current"):
            continue
        if next_boss is None and room_type == "boss":
            next_boss = int(row.get("offset", 0) or 0)
        if next_reward is None and room_type in {"treasure", "event"}:
            next_reward = int(row.get("offset", 0) or 0)
        if next_recovery is None and room_type in {"rest", "shrine"}:
            next_recovery = int(row.get("offset", 0) or 0)
        if next_hazard is None and room_type in {"trap", "boss"}:
            next_hazard = int(row.get("offset", 0) or 0)
    cadence = {
        "next_boss_offset": next_boss,
        "next_reward_offset": next_reward,
        "next_recovery_offset": next_recovery,
        "next_hazard_offset": next_hazard,
        "remaining_combat_rooms": remaining_combat,
        "remaining_support_rooms": remaining_support,
    }
    snapshot = dict(SESSION.get("start_snapshot", {}) or {})
    if snapshot and player is not None:
        resources = dict(getattr(player, "resources", {}) or {})
        risk = int(SESSION.get("risk", 0) or 0)
        depth = int(SESSION.get("depth", 1) or 1)
        gains = {
            "gold": int(getattr(player, "gold", 0) or 0) - int(snapshot.get("gold", 0) or 0),
            "rune_essence": int(resources.get("rune_essence", 0) or 0) - int(snapshot.get("rune_essence", 0) or 0),
            "arcane_chest": int(resources.get("arcane_chest", 0) or 0) - int(snapshot.get("arcane_chest", 0) or 0),
            "rune_relic": int(resources.get("rune_relic", 0) or 0) - int(snapshot.get("rune_relic", 0) or 0),
        }
        boss_preview = {
            "gold_floor": int(60 + (depth * 2) + (risk * 20)),
            "essence_floor": int(4 + max(0, risk)),
            "chest_floor": 1 if int(gains.get("arcane_chest", 0) or 0) <= 0 else 0,
            "relic_floor": 1 if risk >= 4 and int(gains.get("rune_relic", 0) or 0) <= 0 else 0,
            "chest_pity_live": int(gains.get("arcane_chest", 0) or 0) <= 0,
            "relic_pity_live": risk >= 4 and int(gains.get("rune_relic", 0) or 0) <= 0,
            "projected_gold_if_clear": int(gains.get("gold", 0) or 0) + int(60 + (depth * 2) + (risk * 20)),
            "projected_essence_if_clear": int(gains.get("rune_essence", 0) or 0) + int(4 + max(0, risk)),
        }
    if isinstance(enemy, Enemy):
        mods = getattr(enemy, "combat_mods", {}) or {}
        if isinstance(mods.get("room_pressure"), dict):
            current_pressure = dict(mods.get("room_pressure") or {})
        if isinstance(mods.get("boss_run_state"), dict):
            boss_temper = dict(mods.get("boss_run_state") or {})
    return {
        "active": SESSION["active"],
        "risk": SESSION["risk"],
        "depth": SESSION["depth"],
        "room_index": SESSION["room_index"],
        "room_count": len(SESSION["rooms"]),
        "room_type": current_room_type(),
        "current_affix": affix,
        "modifiers": SESSION["modifiers"],
        "enemy": enemy.model_dump() if enemy else None,
        "log": SESSION["log"][-50:],  # keep last 50 lines
        "awaiting_enemy_attack": bool(SESSION.get("awaiting_enemy_attack", False)),
        "pending_player_action": str(SESSION.get("pending_player_action", "") or ""),
        "boss_defeated": bool(SESSION.get("boss_defeated", False)),
        "can_leave": bool(SESSION.get("can_leave", False)),
        "room_preview": preview,
        "run_cadence": cadence,
        "room_pressure": current_pressure,
        "boss_temper": boss_temper,
        "run_gains": gains,
        "boss_preview": boss_preview,
    }

def add_log(line: str):
    SESSION["log"].append(line)


def mark_boss_defeated():
    SESSION["boss_defeated"] = True
    SESSION["can_leave"] = True
    SESSION["awaiting_enemy_attack"] = False
    SESSION["pending_player_action"] = ""


def current_room() -> Optional[Dict[str, Any]]:
    idx = SESSION["room_index"]
    if idx >= len(SESSION["rooms"]):
        return None
    room = SESSION["rooms"][idx]
    return room if isinstance(room, dict) else None


def current_affix() -> Optional[Dict[str, Any]]:
    room = current_room()
    if not isinstance(room, dict):
        return None
    a = room.get("affix")
    return a if isinstance(a, dict) else None
