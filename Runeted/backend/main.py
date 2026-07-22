from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import contextvars
import json
import os
import random
import time
from typing import Any

from models.player import Player
from models.enemy import Enemy
from models.item import Item

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from services.stash import get_stash, dismantle_item, reroll_item_affix
from services.equipment import equip_item, unequip_item
from services.dungeon_run import ROOM_AFFIXES, start_interactive_dungeon, complete_interactive_dungeon
from services.auction_house import list_item, list_rune, list_currency, get_auctions, get_auction_history, buy_item, offer_items, cancel_listing
from services.currency import (
    BASE_CURRENCY,
    CURRENCIES,
    add_currency,
    ascend_item,
    ascend_rune,
    chest_key_upgrade_tier,
    currency_balance,
    is_currency,
    reroll_rune_effect,
    spend_currency,
    wallet as currency_wallet,
)
from services.currency_exchange import get_exchange_rates
from services.chest import award_battle_chest, open_chest as open_reward_chest
from services.trade_hub import all_requests as trade_all_requests, list_requests as trade_list_requests, create_request as trade_create_request, get_request as trade_get_request, update_request as trade_update_request
from services import auth, session
from services.request_scope import ContextDictProxy, ContextObjectProxy
from engine.combat import player_attack as engine_player_attack, enemy_attack as engine_enemy_attack
from engine.loot import generate_loot
from ai.gemini_client import has_api_key
from ai.item_designer import MODEL_NAME
from engine.status_effects import add_status
from engine.boss_ai import is_boss, roll_boss_intent
from utils.validators import validate_item_payload
from services.rune_system import (
    AMPLIFIER_BONUS_CAP,
    AMPLIFIER_RECIPES,
    AMPLIFIER_SELL_VALUE,
    RUNE_BUILD_RARITIES,
    RUNE_CHEST_WEIGHTS,
    RUNE_COMBINE_BONUS_CHANCE,
    RUNE_DISMANTLE_BASE,
    RUNE_EFFECT_POOL,
    RUNE_NAME_PARTS,
    RUNE_NEXT_RARITY,
    RUNE_RECIPES,
    RUNE_RELIC_INFUSE_CAP,
    RUNE_SELL_BASE,
    RUNE_UPGRADE_COSTS,
    RUNE_UPGRADE_MAX,
    amplifier_bonus,
    collect_rune_mods,
    equipped_amplifier,
    find_rune,
    generate_amplifier_rune,
    generate_build_rune,
    generate_rune_effects,
    is_amplifier,
    loadout_summary,
    remove_rune_by_id,
    roll_rune_rarity,
    rune_budget_capacity,
    rune_dismantle_value,
    rune_relic_infuse_cap,
    rune_sale_value,
    rune_slot_capacity,
    rune_upgrade_cost,
    set_equipped_amplifier,
    sync_rune_loadout,
    validate_rune_loadout,
)

app = FastAPI(title="AI Dungeon RPG", docs_url="/docs", redoc_url="/redoc")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend")), name="static")

STATE_FILE = os.path.join(BASE_DIR, "database", "game_state.json")
ACCOUNTS_DIR = os.path.join(BASE_DIR, "database", "accounts")
ACCOUNT_INDEX_FILE = os.path.join(BASE_DIR, "database", "accounts.json")

# --- Per-account request-scoped state -----------------------------------
#
# Real accounts (services/auth.py: username/password, a signed session
# token) replace the old "type any name, no password" save-slot
# switcher. Every authenticated request resolves its OWN account's
# Player via the auth middleware below, bound through this ContextVar --
# so `current_player` keeps behaving like a single live global to every
# existing call site in this file (hundreds of them), while actually
# being isolated per account. See services/request_scope.py for why a
# ContextVar -- not a plain "reassign the global" -- is what makes two
# accounts playing concurrently safe (Starlette dispatches sync `def`
# routes to a real threadpool, so two requests can genuinely run at the
# same time).
_player_ctx: "contextvars.ContextVar[Player]" = contextvars.ContextVar("player_ctx", default=Player())
current_player: Player = ContextObjectProxy(_player_ctx)  # type: ignore[assignment]

# ACTIVE_ACCOUNT was a bare string, which (unlike current_player above)
# can't be proxied the same way -- a str can't lazily recompute its own
# value on read. Every former bare reference to it in this file has been
# mechanically rewritten to call _active_account() instead.
_active_account_ctx: "contextvars.ContextVar[str]" = contextvars.ContextVar("active_account_ctx", default="default")


def _active_account() -> str:
    return _active_account_ctx.get()


TELEMETRY = {"counts": {}, "events": []}
GAME_EVENTS: list[dict] = []

ACTION_CONFIG = {
    "basic": {"cost": 0, "damage_mult": 1.0, "cooldown": 0},
    "heavy": {"cost": 30, "damage_mult": 1.5, "cooldown": 2},
    "rupture": {"cost": 24, "damage_mult": 0.75, "cooldown": 2},
    "guard": {"cost": 16, "damage_mult": 0.0, "cooldown": 1},
    "focus": {"cost": 14, "damage_mult": 0.0, "cooldown": 2},
}

MANA_REGEN_PER_TURN = 4
SKIP_TURN_MANA_BONUS = 4

RUN_MODIFIERS = [
    {
        "id": "bleeding_floors",
        "name": "Bleeding Floors",
        "desc": "Player loses HP each turn unless action is guard/focus.",
    },
    {
        "id": "arcane_suppression",
        "name": "Arcane Suppression",
        "desc": "Focus has +10 stamina cost and +1 cooldown.",
    },
    {
        "id": "volatile_shadows",
        "name": "Volatile Shadows",
        "desc": "Repeated action penalty ramps faster (+15% each repeat).",
    },
    {
        "id": "boss_wrath",
        "name": "Boss Wrath",
        "desc": "Boss room enemy damage is increased.",
    },
]


PRAYER_BOOK = {
    "hawk_eye": {
        "name": "Hawk Eye",
        "unlock": 1,
        "rune": "air",
        "runes_per_turn": 1,
        "effect": "attack_mult",
        "value": 0.12,
    },
    "stone_skin": {
        "name": "Stone Skin",
        "unlock": 10,
        "rune": "earth",
        "runes_per_turn": 1,
        "effect": "def_mult",
        "value": 0.14,
    },
    "mystic_will": {
        "name": "Mystic Will",
        "unlock": 18,
        "rune": "mind",
        "runes_per_turn": 1,
        "effect": "stamina_regen",
        "value": 10,
    },
}

SLAYER_TARGETS = [
    {"id": "brute", "label": "Brute", "unlock": 1, "min_kills": 10, "max_kills": 20},
    {"id": "caster", "label": "Caster", "unlock": 6, "min_kills": 12, "max_kills": 24},
    {"id": "skirmisher", "label": "Skirmisher", "unlock": 10, "min_kills": 14, "max_kills": 26},
    {"id": "tank", "label": "Tank", "unlock": 14, "min_kills": 16, "max_kills": 30},
    {"id": "summoner", "label": "Summoner", "unlock": 18, "min_kills": 18, "max_kills": 34},
]

OBJECTIVE_CONFIG = [
    {"id": "slay_5", "label": "Defeat 5 enemies", "counter": "enemies_defeated", "target": 5, "reward_gold": 220, "reward_chest": 1},
    {"id": "run_1", "label": "Complete 1 dungeon run", "counter": "dungeons_cleared", "target": 1, "reward_gold": 300, "reward_tonic": 1},
    {"id": "idle_15m", "label": "Accumulate 15m idle time", "counter": "idle_seconds", "target": 15 * 60, "reward_gold": 200, "reward_tonic": 1},
    {"id": "slay_25", "label": "Defeat 25 enemies", "counter": "enemies_defeated", "target": 25, "reward_gold": 800, "reward_relic": 1},
    {"id": "boss_3", "label": "Defeat 3 bosses", "counter": "bosses_defeated", "target": 3, "reward_gold": 1200, "reward_chest": 1},
    {"id": "runs_5", "label": "Complete 5 dungeon runs", "counter": "dungeons_cleared", "target": 5, "reward_gold": 1500, "reward_relic": 2},
    {"id": "idle_6h", "label": "Accumulate 6h idle time", "counter": "idle_seconds", "target": 6 * 3600, "reward_gold": 900, "reward_tonic": 1},
]

_IDLE_SKILLS_DEFAULT = {
    "woodcutting": {
        "name": "Woodcutting",
        "xp_per_hour": 62.0,
        "gold_per_hour": 28.0,
        "resource_key": "timber",
        "resource_per_hour": 18.0,
        "rare_chance_per_min": 0.0025,
        "rare_table": [
            {"kind": "resource", "key": "idle_tonic", "amount": 1, "weight": 36},
            {"kind": "resource", "key": "arcane_chest", "amount": 1, "weight": 7},
            {"kind": "resource", "key": "rune_relic", "amount": 1, "weight": 3},
            {"kind": "item", "key": "idle_wood_item", "amount": 1, "weight": 2},
        ],
    },
    "fishing": {
        "name": "Fishing",
        "xp_per_hour": 70.0,
        "gold_per_hour": 36.0,
        "resource_key": "raw_fish",
        "resource_per_hour": 22.0,
        "rare_chance_per_min": 0.0028,
        "rare_table": [
            {"kind": "resource", "key": "arcane_chest", "amount": 1, "weight": 8},
            {"kind": "resource", "key": "rune_relic", "amount": 1, "weight": 4},
            {"kind": "rune", "key": "water", "amount": 1, "weight": 6},
            {"kind": "item", "key": "idle_fish_item", "amount": 1, "weight": 2},
        ],
    },
    "mining": {
        "name": "Mining",
        "xp_per_hour": 78.0,
        "gold_per_hour": 44.0,
        "resource_key": "ore",
        "resource_per_hour": 20.0,
        "rare_chance_per_min": 0.0026,
        "rare_table": [
            {"kind": "resource", "key": "rune_essence", "amount": 4, "weight": 30},
            {"kind": "resource", "key": "arcane_chest", "amount": 1, "weight": 8},
            {"kind": "resource", "key": "rune_relic", "amount": 1, "weight": 4},
            {"kind": "item", "key": "idle_mine_item", "amount": 1, "weight": 2},
        ],
    },
    "herblore": {
        "name": "Crafting",
        "xp_per_hour": 86.0,
        "gold_per_hour": 54.0,
        "resource_key": "crafted_supplies",
        "resource_per_hour": 13.0,
        "rare_chance_per_min": 0.0030,
        "rare_table": [
            {"kind": "resource", "key": "idle_tonic", "amount": 1, "weight": 34},
            {"kind": "resource", "key": "rune_essence", "amount": 5, "weight": 24},
            {"kind": "resource", "key": "arcane_chest", "amount": 1, "weight": 8},
            {"kind": "resource", "key": "rune_relic", "amount": 1, "weight": 5},
            {"kind": "item", "key": "idle_craft_item", "amount": 1, "weight": 2},
        ],
    },
}

BATTLE_SKILL_CATALOG = {
    "quick_slash": {
        "name": "Quick Slash",
        "kind": "normal",
        "mana_cost": 2,
        "unlock_level": 1,
        "base_weight": 1.25,
        "action": "basic",
        "damage_mult": 0.95,
        "tags": ["strike"],
        "desc": "A fast, cheap strike. Counts as a BASIC action for intent counters.",
    },
    "cleave": {
        "name": "Cleave",
        "kind": "normal",
        "mana_cost": 5,
        "unlock_level": 1,
        "base_weight": 0.9,
        "action": "heavy",
        "damage_mult": 1.1,
        "tags": ["strike"],
        "desc": "A HEAVY blow with bonus damage, but it leaves you vulnerable for 2 turns and goes on cooldown.",
    },
    "rupture_strike": {
        "name": "Rupture Strike",
        "kind": "normal",
        "mana_cost": 5,
        "unlock_level": 14,
        "base_weight": 0.85,
        "action": "rupture",
        "damage_mult": 1.0,
        "tags": ["bleed", "hex"],
        "desc": "A RUPTURE attack that deals reduced hit damage but applies a 3-turn bleed to the enemy.",
    },
    "guard_stance": {
        "name": "Guard Stance",
        "kind": "normal",
        "mana_cost": 3,
        "unlock_level": 1,
        "base_weight": 1.0,
        "action": "guard",
        "damage_mult": 1.0,
        "tags": ["guard"],
        "desc": "No damage. GUARD reduces incoming damage for 2 turns. Strong answer to heavy telegraphs.",
    },
    "focus_channel": {
        "name": "Focus Channel",
        "kind": "normal",
        "mana_cost": 3,
        "unlock_level": 1,
        "base_weight": 1.0,
        "action": "focus",
        "damage_mult": 1.0,
        "tags": ["setup", "hex"],
        "desc": "No damage. FOCUS makes the enemy vulnerable for 2 turns and gives you a small guard.",
    },
    "arc_surge": {
        "name": "Arc Surge",
        "kind": "normal",
        "mana_cost": 6,
        "unlock_level": 22,
        "base_weight": 0.7,
        "action": "basic",
        "damage_mult": 1.45,
        "tags": ["burst"],
        "desc": "An expensive BASIC-type burst that hits much harder than a normal strike.",
    },
    "self_bleed": {
        "name": "Blood Pact",
        "kind": "cursed",
        "mana_cost": 1,
        "unlock_level": 1,
        "base_weight": 0.92,
        "action": "",
        "damage_mult": 0.0,
        "tags": ["self_harm", "hex"],
        "desc": "Cursed: hurt and bleed yourself to gain a reroll charge, mana, and curse charge for future damage.",
    },
    "frail_guard": {
        "name": "Frail Guard",
        "kind": "cursed",
        "mana_cost": 2,
        "unlock_level": 10,
        "base_weight": 0.95,
        "action": "",
        "damage_mult": 0.0,
        "tags": ["debuff"],
        "desc": "Cursed: gain a strong guard but become vulnerable for 2 turns. Builds curse charge.",
    },
    "blank_stumble": {
        "name": "Twisted Insight",
        "kind": "cursed",
        "mana_cost": 1,
        "unlock_level": 1,
        "base_weight": 0.82,
        "action": "",
        "damage_mult": 0.0,
        "tags": ["blank", "utility"],
        "desc": "Cursed: do nothing this turn but gain rerolls, mana, and curse charge.",
    },
}

BATTLE_TREE_CONFIG = {
    "power_training": {
        "name": "Power Training",
        "desc": "+3% rolled skill damage per level.",
        "max_level": 8,
        "base_cost_gold": 550,
        "cost_mult": 1.7,
    },
    "iron_guard": {
        "name": "Iron Guard",
        "desc": "Reduce incoming enemy damage by 3% per level.",
        "max_level": 8,
        "base_cost_gold": 620,
        "cost_mult": 1.7,
    },
    "echo_reroll": {
        "name": "Echo Reroll",
        "desc": "When same skill rolls twice in a row, gain reroll charge.",
        "max_level": 3,
        "base_cost_gold": 900,
        "cost_mult": 1.85,
    },
    "loaded_slot_one": {
        "name": "Loaded Slot One",
        "desc": "Increase roll weight of loadout slot 1.",
        "max_level": 6,
        "base_cost_gold": 700,
        "cost_mult": 1.75,
    },
    "curse_attunement": {
        "name": "Curse Attunement",
        "desc": "Cursed skills roll less often, but grant stronger charge/stamina.",
        "max_level": 6,
        "base_cost_gold": 760,
        "cost_mult": 1.75,
    },
    "affliction_mastery": {
        "name": "Affliction Mastery",
        "desc": "Deal extra damage while you are debuffed.",
        "max_level": 6,
        "base_cost_gold": 800,
        "cost_mult": 1.8,
    },
}

CORE_BATTLE_PRESETS = {
    "starter": ["quick_slash", "cleave", "guard_stance", "focus_channel", "self_bleed", "blank_stumble"],
    "striker": ["arc_surge", "cleave", "quick_slash", "guard_stance", "self_bleed", "frail_guard"],
    "affliction": ["rupture_strike", "focus_channel", "quick_slash", "guard_stance", "self_bleed", "frail_guard"],
}

BATTLE_MANA_CONFIG = {
    "min_cap": 8,
    "max_cap": 50,
    "base_cost_gold": 420,
    "cost_mult": 1.22,
}

BATTLE_MASTERY_MILESTONES = [5, 12, 25, 40, 60]

IDLE_UPGRADE_CONFIG = {
    "efficiency": {"name": "Efficiency Core", "base_cost_gold": 1400, "cost_mult": 1.55, "max_level": 60},
    "rare_find": {"name": "Rare Scanner", "base_cost_gold": 2200, "cost_mult": 1.6, "max_level": 50},
    "duration_cap": {"name": "Long-Haul Buffer", "base_cost_gold": 1800, "cost_mult": 1.45, "max_level": 24},
}

IDLE_BOOST_CONFIG = {
    "surge_2h": {
        "name": "Surge (2h)",
        "duration_sec": 2 * 60 * 60,
        "mult": 1.65,
        "cost_gold": 2400,
        "consume_resource": "",
    },
    "tonic_1h": {
        "name": "Idle Tonic (1h)",
        "duration_sec": 60 * 60,
        "mult": 1.35,
        "cost_gold": 0,
        "consume_resource": "idle_tonic",
    },
}

_IDLE_TUNING_DEFAULT = {
    # Global idle output scaler. Keep below active efficiency.
    "idle_rate_mult": 0.92,
    # Diminishing returns segments after 8h/24h.
    "diminish_mid_mult": 0.62,
    "diminish_long_mult": 0.38,
    # Rare drop global scalar.
    "rare_drop_rate_mult": 1.0,
    # Hard cap for stacked boost multipliers.
    "max_boost_mult": 3.5,
    # Idle-generated item drop chance per minute is very low.
    "item_drop_rate_mult": 1.0,
}

_IDLE_TUNING_PRESETS_DEFAULT = {
    "active_favor": {
        "idle_rate_mult": 0.75,
        "rare_drop_rate_mult": 0.9,
        "item_drop_rate_mult": 0.85,
        "diminish_mid_mult": 0.56,
        "diminish_long_mult": 0.32,
    },
    "neutral": {
        "idle_rate_mult": 0.92,
        "rare_drop_rate_mult": 1.0,
        "item_drop_rate_mult": 1.0,
        "diminish_mid_mult": 0.62,
        "diminish_long_mult": 0.38,
    },
    "idle_favor": {
        "idle_rate_mult": 1.05,
        "rare_drop_rate_mult": 1.15,
        "item_drop_rate_mult": 1.1,
        "diminish_mid_mult": 0.68,
        "diminish_long_mult": 0.45,
    },
}
CORE_IDLE_TUNING_PRESETS = {"active_favor", "neutral", "idle_favor"}

_IDLE_SKILL_TUNING_PRESETS_DEFAULT: dict[str, dict[str, dict[str, float]]] = {
    skill_id: {} for skill_id in _IDLE_SKILLS_DEFAULT.keys()
}
DEFAULT_IDLE_TUNING = dict(_IDLE_TUNING_DEFAULT)
DEFAULT_IDLE_TUNING_PRESETS = dict(_IDLE_TUNING_PRESETS_DEFAULT)
DEFAULT_IDLE_SKILLS = {sid: dict(cfg) for sid, cfg in _IDLE_SKILLS_DEFAULT.items()}
DEFAULT_IDLE_SKILL_TUNING_PRESETS = {skill_id: {} for skill_id in _IDLE_SKILLS_DEFAULT.keys()}

# Each of the four dicts above is per-account state (it's already saved
# into each account's own JSON file by _persist_state()) -- so the LIVE,
# mutable versions everything else in this file reads/writes by these
# same bare names must resolve per authenticated request too, exactly
# like current_player/SESSION below, or one account's idle-tuning tweaks
# would silently bleed into another's. Same ContextDictProxy trick, same
# zero-call-site-change property: every existing `IDLE_TUNING["x"]` /
# `IDLE_SKILLS.items()` / `.update(...)` call in this file keeps working
# unmodified. The default bound below (a copy of the factory defaults)
# only matters outside of any authenticated request.
_idle_tuning_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "idle_tuning_ctx", default=dict(_IDLE_TUNING_DEFAULT)
)
_idle_tuning_presets_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "idle_tuning_presets_ctx", default={k: dict(v) for k, v in _IDLE_TUNING_PRESETS_DEFAULT.items()}
)
_idle_skill_tuning_presets_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "idle_skill_tuning_presets_ctx", default={k: dict(v) for k, v in _IDLE_SKILL_TUNING_PRESETS_DEFAULT.items()}
)
_idle_skills_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "idle_skills_ctx", default={sid: dict(cfg) for sid, cfg in _IDLE_SKILLS_DEFAULT.items()}
)

IDLE_TUNING = ContextDictProxy(_idle_tuning_ctx)
IDLE_TUNING_PRESETS = ContextDictProxy(_idle_tuning_presets_ctx)
IDLE_SKILL_TUNING_PRESETS = ContextDictProxy(_idle_skill_tuning_presets_ctx)
IDLE_SKILLS = ContextDictProxy(_idle_skills_ctx)


def _fresh_idle_runtime_bundle() -> dict[str, dict]:
    """A brand-new account's starting idle-tuning state -- copies of the
    factory defaults, independent of any other account's live dicts."""
    return {
        "idle_tuning": dict(DEFAULT_IDLE_TUNING),
        "idle_tuning_presets": {k: dict(v) for k, v in DEFAULT_IDLE_TUNING_PRESETS.items()},
        "idle_skill_tuning_presets": {k: dict(v) for k, v in DEFAULT_IDLE_SKILL_TUNING_PRESETS.items()},
        "idle_skills": {sid: dict(cfg) for sid, cfg in DEFAULT_IDLE_SKILLS.items()},
    }



# -------------------------
# Basic
# -------------------------
@app.get("/")
def root():
    return {"status": "AI Dungeon RPG backend running"}


@app.get("/ai/status")
def ai_status():
    return {
        "enabled": has_api_key(),
        "provider": "gemini",
        "model": MODEL_NAME,
    }


@app.get("/game", response_class=HTMLResponse)
def game():
    with open(os.path.join(BASE_DIR, "frontend", "index.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.post("/telemetry/event")
def telemetry_event(payload: dict):
    event = str(payload.get("event", "") or "").strip().lower()
    if not event:
        return {"ok": False, "error": "missing event"}

    counts = TELEMETRY.setdefault("counts", {})
    counts[event] = int(counts.get(event, 0) or 0) + 1

    events = TELEMETRY.setdefault("events", [])
    events.append({
        "event": event,
        "payload": payload.get("payload", {}),
    })
    if len(events) > 200:
        del events[:-200]

    return {"ok": True, "counts": counts}


@app.get("/telemetry/summary")
def telemetry_summary():
    return {
        "counts": TELEMETRY.get("counts", {}),
        "events": TELEMETRY.get("events", [])[-30:],
    }


@app.get("/events/log")
def events_log(limit: int = 120):
    cap = max(10, min(int(limit or 120), 300))
    return {"events": list(GAME_EVENTS[-cap:])[::-1], "total": len(GAME_EVENTS)}


@app.post("/events/clear")
def events_clear():
    GAME_EVENTS.clear()
    return {"ok": True}


@app.get("/tracker/summary")
def tracker_summary():
    idle_state = _idle_state_payload(current_player, include_summary=True)
    activity = dict(idle_state.get("activity", {}) or {})
    active_skill = str(activity.get("skill", "") or "")
    skill_tuning = dict(idle_state.get("skill_tuning", {}) or {})
    active_tuning = dict(skill_tuning.get(active_skill, {}) or {})
    offline_summary = dict(idle_state.get("offline_summary", {}) or {})

    counts = dict(TELEMETRY.get("counts", {}) or {})
    turns = int(counts.get("turn_started", 0) or 0)
    fail = int(counts.get("action_failed", 0) or 0)
    dodges = int(counts.get("dodge_result", 0) or 0)
    success = int(counts.get("dodge_success", 0) or 0)
    dodge_rate = round((success / max(1, dodges)) * 100.0, 2)
    fail_rate = round((fail / max(1, turns)) * 100.0, 2)

    return {
        "combat": {
            "turns_started": turns,
            "action_failed": fail,
            "action_fail_rate_pct": fail_rate,
            "dodges": dodges,
            "dodge_success": success,
            "dodge_success_rate_pct": dodge_rate,
        },
        "idle": {
            "active": bool(idle_state.get("active", False)),
            "skill": active_skill,
            "skill_name": activity.get("skill_name", "") if active_skill else "",
            "uptime_sec": int(activity.get("uptime_sec", 0) or 0),
            "xp_per_hour": float(active_tuning.get("xp_per_hour", 0.0) or 0.0),
            "gold_per_hour": float(active_tuning.get("gold_per_hour", 0.0) or 0.0),
            "resource_per_hour": float(active_tuning.get("resource_per_hour", 0.0) or 0.0),
            "rare_chance_per_min": float(active_tuning.get("rare_chance_per_min", 0.0) or 0.0),
            "offline_cap_sec": int(idle_state.get("offline_cap_sec", 0) or 0),
            "latest_summary": offline_summary,
        },
        "economy": {
            "gold": int(current_player.gold),
            "stash_count": len(list(current_player.stash or [])),
            "rune_items": len(list(current_player.rune_items or [])),
            "arcane_chest": int(current_player.resources.get("arcane_chest", 0) or 0),
            "rune_relic": int(current_player.resources.get("rune_relic", 0) or 0),
        },
        "telemetry_counts": counts,
    }


@app.get("/codex")
def codex():
    elite_variants = {
        "brute": [
            {"id": "crusher", "name": "Crusher", "effect": "Punishes guard-heavy lines by shaving committed damage."},
            {"id": "berserker", "name": "Berserker", "effect": "Gains extra enemy-turn damage below half HP."},
        ],
        "caster": [
            {"id": "hexweaver", "name": "Hexweaver", "effect": "Applies weak pressure over time."},
            {"id": "stormcaller", "name": "Stormcaller", "effect": "Builds charge and discharges burst damage."},
        ],
        "skirmisher": [
            {"id": "shadowstep", "name": "Shadowstep", "effect": "Can slip heavy commitments and reduce the hit."},
            {"id": "venomrunner", "name": "Venomrunner", "effect": "Adds bleed pressure on enemy turns."},
        ],
        "tank": [
            {"id": "bulwark", "name": "Bulwark", "effect": "Shrugs off non-rupture damage."},
            {"id": "ironhide", "name": "Ironhide", "effect": "Can rebuild guard mid fight."},
        ],
        "summoner": [
            {"id": "broodlord", "name": "Broodlord", "effect": "Builds swarm burst cycles over time."},
            {"id": "bonecaller", "name": "Bonecaller", "effect": "Converts bleed setup into healing."},
        ],
    }
    boss_archetypes = {
        "brute": [
            "Phase quake bursts on enemy turns.",
            "Higher phases create heavier board pressure.",
        ],
        "caster": [
            "Rebuilds barrier in later phases.",
            "Late phases apply hex pressure and barrier snaps.",
        ],
        "skirmisher": [
            "Can slip committed attacks in phase play.",
            "Later phases open weak windows on the player.",
        ],
        "tank": [
            "Bastion reactions reduce incoming damage.",
            "Fortress cycles rebuild guard in later phases.",
        ],
        "summoner": [
            "Swarm pressure increases as phases rise.",
            "Enemy turns add extra unavoidable chip pressure.",
        ],
    }
    room_affixes = [
        {
            "id": str(row.get("id", "") or ""),
            "name": str(row.get("name", row.get("id", "Affix")) or "Affix"),
            "effect": str(row.get("desc", "") or ""),
        }
        for row in ROOM_AFFIXES
    ]
    support_mechanics = {
        "rest": [
            {"id": "standard", "name": "Standard Rest", "effect": "Restores HP and stamina for the next fight."},
            {"id": "camp_cache", "name": "Camp Cache", "effect": "Restores HP/stamina and can grant an idle tonic or bonus gold."},
            {"id": "cleanse", "name": "Cleanse", "effect": "Restores HP/stamina and removes negative statuses."},
        ],
        "event": [
            {"id": "gold_cache", "name": "Gold Cache", "effect": "Direct gold injection from a side cache."},
            {"id": "ancient_tablet", "name": "Ancient Tablet", "effect": "Converts the room into an EXP gain."},
            {"id": "war_altar", "name": "War Altar", "effect": "Restores stamina for immediate tempo."},
            {"id": "rune_scraps", "name": "Rune Scraps", "effect": "Awards rune essence from broken relic matter."},
            {"id": "battle_trance", "name": "Battle Trance", "effect": "Applies temporary guard heading into the next fight."},
        ],
        "shrine": [
            {"id": "healing", "name": "Healing Shrine", "effect": "Restores HP."},
            {"id": "focus", "name": "Focus Shrine", "effect": "Restores stamina."},
            {"id": "rune", "name": "Rune Shrine", "effect": "Can grant relics and bonus gold."},
            {"id": "ward", "name": "Ward Shrine", "effect": "Applies a defensive blessing."},
            {"id": "vault", "name": "Vault Shrine", "effect": "Reveals one or more Arcane Chests."},
        ],
    }
    dungeon_structure = {
        "room_types": [
            {"id": "combat", "name": "Combat Room", "effect": "Standard fight room used to build momentum and gain steady rewards."},
            {"id": "event", "name": "Event Room", "effect": "Variable utility room with gold, EXP, stamina, or guard outcomes."},
            {"id": "rest", "name": "Rest Room", "effect": "Recovery room that restores HP and stamina and can roll support outcomes."},
            {"id": "trap", "name": "Trap Room", "effect": "Hazard room that threatens HP instead of granting direct rewards."},
            {"id": "treasure", "name": "Treasure Room", "effect": "Direct payout room for gold, essence, and chest spikes."},
            {"id": "shrine", "name": "Shrine Room", "effect": "Blessing room that can restore, defend, or grant chest/relic value."},
            {"id": "boss", "name": "Boss Room", "effect": "Final room. Clearing it unlocks dungeon exit and secures rewards."},
        ],
        "cadence": [
            {"id": "opener", "name": "Opener", "effect": "Early room meant to establish momentum or a light pivot."},
            {"id": "payout_pivot", "name": "Payout Pivot", "effect": "Second room tends to lean toward reward or support value."},
            {"id": "pressure_room", "name": "Pressure Room", "effect": "Mid-run room intended to add danger and pacing."},
            {"id": "pre_boss", "name": "Pre-Boss Room", "effect": "Final setup room before the boss, often recovery or pressure-weighted by risk."},
            {"id": "boss_finish", "name": "Boss Finish", "effect": "Run-ending boss room that finalizes the route."},
        ],
    }
    battle_catalog = []
    for sid, row in BATTLE_SKILL_CATALOG.items():
        battle_catalog.append({
            "id": sid,
            "name": row.get("name", sid),
            "kind": row.get("kind", "normal"),
            "mana_cost": int(row.get("mana_cost", 0) or 0),
            "unlock_level": int(row.get("unlock_level", 1) or 1),
            "tags": list(row.get("tags", [])),
        })

    idle_rows = []
    for sid, cfg in IDLE_SKILLS.items():
        idle_rows.append({
            "id": sid,
            "name": cfg.get("name", sid.title()),
            "xp_per_hour": float(cfg.get("xp_per_hour", 0.0) or 0.0),
            "gold_per_hour": float(cfg.get("gold_per_hour", 0.0) or 0.0),
            "resource_per_hour": float(cfg.get("resource_per_hour", 0.0) or 0.0),
            "rare_chance_per_min": float(cfg.get("rare_chance_per_min", 0.0) or 0.0),
            "resource_key": str(cfg.get("resource_key", "") or ""),
        })

    rune_recipes = []
    for rid, recipe in RUNE_RECIPES.items():
        rune_recipes.append({
            "id": rid,
            "name": recipe.get("name", rid),
            "essence_cost": int(recipe.get("essence_cost", 0) or 0),
            "base_yield": list(recipe.get("base_yield", (1, 1))),
            "xp": int(recipe.get("xp", 0) or 0),
            "unlock": int(recipe.get("unlock", 1) or 1),
        })

    return {
        "drop_rates": {
            "chest_rarity_weights": dict(RUNE_CHEST_WEIGHTS),
            "combine_bonus_chance": dict(RUNE_COMBINE_BONUS_CHANCE),
            "dungeon_chest_drop_formula": "0.06 + risk*0.03 + loot_luck*0.20 (+0.15 on boss)",
            "dungeon_relic_drop_formula": "0.03 + risk*0.02 (+0.10 on boss)",
            "idle_rare_formula": "skill_rare_chance_per_min * tuning_rare_drop_rate_mult * (1 + rare_upgrade*0.08) * (1 + (skill_level-1)*0.002), capped at 0.10",
        },
        "battle_skills": battle_catalog,
        "battle_tree": dict(BATTLE_TREE_CONFIG),
        "elite_variants": elite_variants,
        "boss_archetypes": boss_archetypes,
        "room_affixes": room_affixes,
        "support_mechanics": support_mechanics,
        "dungeon_structure": dungeon_structure,
        "mechanics_learned": dict(getattr(current_player, "mechanics_learned", {}) or {}),
        "idle_skills": idle_rows,
        "rune_recipes": rune_recipes,
        "rune_build_rarities": list(RUNE_BUILD_RARITIES),
        "run_modifiers": list(RUN_MODIFIERS),
    }


@app.get("/objectives/state")
def objectives_state():
    return _objectives_state()


@app.get("/guide/state")
def guide_state():
    return _guide_state()


@app.post("/guide/dismiss")
def guide_dismiss(payload: dict | None = None):
    payload = payload or {}
    flags = dict(getattr(current_player, "guide_flags", {}) or {})
    flags["dismissed"] = bool(payload.get("dismissed", True))
    current_player.guide_flags = flags
    _persist_state()
    return {"ok": True, "guide": _guide_state()}


@app.post("/objectives/claim")
def objectives_claim(payload: dict):
    oid = str(payload.get("objective_id", "") or "").strip()
    if not oid:
        return {"error": "Missing objective_id"}

    state = _objectives_state()
    row = next((x for x in list(state.get("objectives", []) or []) if str(x.get("id", "")) == oid), None)
    if not row:
        return {"error": "Unknown objective", "objective_id": oid}
    if bool(row.get("claimed", False)):
        return {"error": "Objective already claimed", "objective_id": oid}
    if not bool(row.get("completed", False)):
        return {"error": "Objective not complete", "objective_id": oid}

    claimed = list(getattr(current_player, "objectives_claimed", []) or [])
    claimed.append(oid)
    current_player.objectives_claimed = sorted(list(set(str(x) for x in claimed)))

    reward_gold = int(row.get("reward_gold", 0) or 0)
    reward_relic = int(row.get("reward_relic", 0) or 0)
    reward_chest = int(row.get("reward_chest", 0) or 0)
    reward_tonic = int(row.get("reward_tonic", 0) or 0)

    if reward_gold > 0:
        current_player.gold += reward_gold
    if reward_relic > 0:
        current_player.add_resource("rune_relic", reward_relic)
    if reward_chest > 0:
        current_player.add_resource("arcane_chest", reward_chest)
    if reward_tonic > 0:
        current_player.add_resource("idle_tonic", reward_tonic)

    _event_log_add(
        "objective",
        "Objective claimed",
        f"{row.get('label', oid)}",
        severity="success",
        meta={"objective_id": oid},
    )
    _persist_state()
    return {
        "ok": True,
        "claimed": oid,
        "rewards": {
            "gold": reward_gold,
            "rune_relic": reward_relic,
            "arcane_chest": reward_chest,
            "idle_tonic": reward_tonic,
        },
        "state": _objectives_state(),
    }


@app.post("/objectives/claim_all")
def objectives_claim_all():
    state = _objectives_state()
    claimable = [row for row in list(state.get("objectives", []) or []) if bool(row.get("claimable", False))]
    if not claimable:
        return {"error": "No claimable objectives"}

    total_gold = 0
    total_relic = 0
    total_chest = 0
    total_tonic = 0
    claimed = list(getattr(current_player, "objectives_claimed", []) or [])

    for row in claimable:
        oid = str(row.get("id", "") or "")
        claimed.append(oid)
        total_gold += int(row.get("reward_gold", 0) or 0)
        total_relic += int(row.get("reward_relic", 0) or 0)
        total_chest += int(row.get("reward_chest", 0) or 0)
        total_tonic += int(row.get("reward_tonic", 0) or 0)

    current_player.objectives_claimed = sorted(list(set(str(x) for x in claimed)))
    if total_gold > 0:
        current_player.gold += total_gold
    if total_relic > 0:
        current_player.add_resource("rune_relic", total_relic)
    if total_chest > 0:
        current_player.add_resource("arcane_chest", total_chest)
    if total_tonic > 0:
        current_player.add_resource("idle_tonic", total_tonic)

    _event_log_add(
        "objective",
        "Objective rewards claimed",
        f"{len(claimable)} objective(s) claimed",
        severity="success",
        meta={"count": len(claimable)},
    )
    _persist_state()
    return {
        "ok": True,
        "claimed_count": len(claimable),
        "rewards": {
            "gold": total_gold,
            "rune_relic": total_relic,
            "arcane_chest": total_chest,
            "idle_tonic": total_tonic,
        },
        "state": _objectives_state(),
    }


def _safe_account_name(name: str) -> str:
    raw = str(name or "").strip().lower()
    filtered = "".join(ch for ch in raw if ch.isalnum() or ch in ("_", "-"))
    return filtered[:32] or "default"


def _state_file_for_account(account: str) -> str:
    acct = _safe_account_name(account)
    return os.path.join(ACCOUNTS_DIR, f"{acct}.json")


def _read_account_index() -> dict:
    if not os.path.exists(ACCOUNT_INDEX_FILE):
        return {"active": "default", "accounts": ["default"]}
    try:
        with open(ACCOUNT_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        active = _safe_account_name(data.get("active", "default"))
        accounts = data.get("accounts", ["default"])
        if not isinstance(accounts, list):
            accounts = ["default"]
        cleaned = sorted(list({_safe_account_name(x) for x in accounts if str(x).strip()}))
        if "default" not in cleaned:
            cleaned.append("default")
        if active not in cleaned:
            active = cleaned[0] if cleaned else "default"
        return {"active": active, "accounts": cleaned}
    except Exception:
        return {"active": "default", "accounts": ["default"]}


def _write_account_index(active: str, accounts: list[str]) -> None:
    try:
        os.makedirs(os.path.dirname(ACCOUNT_INDEX_FILE), exist_ok=True)
        cleaned = sorted(list({_safe_account_name(x) for x in (accounts or []) if str(x).strip()}))
        if "default" not in cleaned:
            cleaned.append("default")
        payload = {"active": _safe_account_name(active), "accounts": cleaned}
        with open(ACCOUNT_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)
    except Exception:
        pass


def _load_state_from_file(path: str) -> None:
    """Populates whichever player/idle-tuning objects are CURRENTLY
    bound in the ambient context with what's saved at `path` (or fresh
    defaults if there's nothing there / it fails to parse). Only called
    by _build_account_bundle below, which binds fresh placeholders
    first so this has somewhere to write, then captures the result --
    never called directly against "the" global anymore, since there
    isn't one."""
    _reset_idle_runtime_configs()
    if not os.path.exists(path):
        _player_ctx.set(Player())
        _apply_battle_defaults(current_player)
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        player_data = raw.get("player", {})
        if isinstance(player_data, dict) and player_data:
            if hasattr(Player, "model_validate"):
                _player_ctx.set(Player.model_validate(player_data))
            else:
                _player_ctx.set(Player(**player_data))
        else:
            _player_ctx.set(Player())

        idle_tuning = raw.get("idle_tuning", {})
        if isinstance(idle_tuning, dict):
            IDLE_TUNING.update({k: v for k, v in idle_tuning.items() if k in IDLE_TUNING})

        preset_data = raw.get("idle_tuning_presets", {})
        if isinstance(preset_data, dict):
            for k, v in preset_data.items():
                if isinstance(v, dict):
                    IDLE_TUNING_PRESETS[str(k)] = dict(v)

        skill_preset_data = raw.get("idle_skill_tuning_presets", {})
        if isinstance(skill_preset_data, dict):
            for skill, presets in skill_preset_data.items():
                if str(skill) not in IDLE_SKILLS or not isinstance(presets, dict):
                    continue
                IDLE_SKILL_TUNING_PRESETS[str(skill)] = {
                    str(pid): dict(pcfg)
                    for pid, pcfg in presets.items()
                    if isinstance(pcfg, dict)
                }

        skill_data = raw.get("idle_skills", {})
        if isinstance(skill_data, dict):
            for skill, cfg in skill_data.items():
                sid = str(skill)
                if sid in IDLE_SKILLS and isinstance(cfg, dict):
                    IDLE_SKILLS[sid].update(cfg)
        _apply_battle_defaults(current_player)
    except Exception:
        _player_ctx.set(Player())
        _reset_idle_runtime_configs()
        _apply_battle_defaults(current_player)


def _build_account_bundle(account_id: str) -> dict[str, Any]:
    """Everything one account's live game state needs: its Player, its
    own idle-tuning dicts, and a fresh dungeon-run session -- loaded
    once per account per process lifetime (from that account's save
    file, or defaulted if it has none yet) and cached by the auth
    middleware in _ACCOUNT_CACHE. Reuses _load_state_from_file's
    parsing/migration logic by binding scratch placeholders, running
    it, then capturing whatever it produced."""
    player_token = _player_ctx.set(Player())
    tuning_token = _idle_tuning_ctx.set({})
    presets_token = _idle_tuning_presets_ctx.set({})
    skill_presets_token = _idle_skill_tuning_presets_ctx.set({})
    skills_token = _idle_skills_ctx.set({})
    try:
        _load_state_from_file(_state_file_for_account(account_id))
        return {
            "player": _player_ctx.get(),
            "idle_tuning": _idle_tuning_ctx.get(),
            "idle_tuning_presets": _idle_tuning_presets_ctx.get(),
            "idle_skill_tuning_presets": _idle_skill_tuning_presets_ctx.get(),
            "idle_skills": _idle_skills_ctx.get(),
            "session": session.new_session_dict(),
        }
    finally:
        _player_ctx.reset(player_token)
        _idle_tuning_ctx.reset(tuning_token)
        _idle_tuning_presets_ctx.reset(presets_token)
        _idle_skill_tuning_presets_ctx.reset(skill_presets_token)
        _idle_skills_ctx.reset(skills_token)


def _reset_idle_runtime_configs() -> None:
    IDLE_TUNING.clear()
    IDLE_TUNING.update(dict(DEFAULT_IDLE_TUNING))

    IDLE_TUNING_PRESETS.clear()
    IDLE_TUNING_PRESETS.update(dict(DEFAULT_IDLE_TUNING_PRESETS))

    IDLE_SKILLS.clear()
    IDLE_SKILLS.update({sid: dict(cfg) for sid, cfg in DEFAULT_IDLE_SKILLS.items()})

    IDLE_SKILL_TUNING_PRESETS.clear()
    IDLE_SKILL_TUNING_PRESETS.update({skill_id: {} for skill_id in DEFAULT_IDLE_SKILL_TUNING_PRESETS.keys()})


def _account_state_payload() -> dict:
    # One account IS one authenticated identity now -- this used to list
    # every save slot that had ever existed on the server (a real
    # information leak once accounts are real, separate users). It now
    # only ever describes the caller's own account.
    account_id = _active_account()
    path = _state_file_for_account(account_id)
    saved_at = 0
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            saved_at = int(raw.get("saved_at", 0) or 0)
        except Exception:
            saved_at = 0
    return {
        "active": account_id,
        "accounts": [{"id": account_id, "active": True, "saved_at": saved_at}],
        "single_save_per_account": True,
    }


def _player_from_payload(player_data: dict) -> Player:
    if isinstance(player_data, dict) and player_data:
        if hasattr(Player, "model_validate"):
            return Player.model_validate(player_data)
        return Player(**player_data)
    return Player()


def _read_account_payload(account: str) -> dict:
    path = _state_file_for_account(account)
    if not os.path.exists(path):
        return {
            "player": Player().model_dump() if hasattr(Player(), "model_dump") else Player().dict(),
            "idle_tuning": dict(IDLE_TUNING),
            "idle_tuning_presets": dict(IDLE_TUNING_PRESETS),
            "idle_skill_tuning_presets": dict(IDLE_SKILL_TUNING_PRESETS),
            "idle_skills": dict(IDLE_SKILLS),
            "saved_at": 0,
            "account": _safe_account_name(account),
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            return raw
    except Exception:
        pass
    return {
        "player": {},
        "idle_tuning": dict(IDLE_TUNING),
        "idle_tuning_presets": dict(IDLE_TUNING_PRESETS),
        "idle_skill_tuning_presets": dict(IDLE_SKILL_TUNING_PRESETS),
        "idle_skills": dict(IDLE_SKILLS),
        "saved_at": 0,
        "account": _safe_account_name(account),
    }


def _load_account_player(account: str) -> tuple[dict, Player]:
    raw = _read_account_payload(account)
    player = _player_from_payload(raw.get("player", {}))
    return raw, player


def _save_account_player(account: str, raw_payload: dict, player: Player) -> None:
    path = _state_file_for_account(account)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    player_payload = player.model_dump() if hasattr(player, "model_dump") else player.dict()
    payload = dict(raw_payload or {})
    payload["player"] = player_payload
    payload["saved_at"] = int(time.time())
    payload["account"] = _safe_account_name(account)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True)


def _item_from_payload(payload: dict):
    return validate_item_payload(payload)


def _trade_request_summary(row: dict) -> dict:
    offered_items = list(row.get("offered_items", []) or [])
    requested_items = list(row.get("requested_items", []) or [])
    return {
        "id": str(row.get("id", "") or ""),
        "sender": str(row.get("sender", "") or ""),
        "target": str(row.get("target", "") or ""),
        "status": str(row.get("status", "pending") or "pending"),
        "gold_offer": int(row.get("gold_offer", 0) or 0),
        "gold_request": int(row.get("gold_request", 0) or 0),
        "currency_offer": dict(row.get("offered_currencies", {}) or {}),
        "currency_request": dict(row.get("requested_currencies", {}) or {}),
        "note": str(row.get("note", "") or ""),
        "created_at": int(row.get("created_at", 0) or 0),
        "updated_at": int(row.get("updated_at", 0) or 0),
        "expires_at": int(row.get("expires_at", 0) or 0),
        "item_count": len(offered_items),
        "requested_item_count": len(requested_items),
        "items": [
            {
                "name": str(item.get("name", "Item") or "Item"),
                "rarity": str(item.get("rarity", "common") or "common"),
                "slot": str(item.get("slot", "-") or "-"),
                "power": int(item.get("power", 0) or 0),
            }
            for item in offered_items[:6]
            if isinstance(item, dict)
        ],
        "requested_items": [
            {
                "name": str(item.get("name", "Item") or "Item"),
                "rarity": str(item.get("rarity", "common") or "common"),
                "slot": str(item.get("slot", "-") or "-"),
                "power": int(item.get("power", 0) or 0),
            }
            for item in requested_items[:6]
            if isinstance(item, dict)
        ],
    }


def _expire_pending_trades() -> int:
    now = int(time.time())
    expired = 0
    for row in trade_all_requests():
        if str(row.get("status", "pending") or "pending") != "pending":
            continue
        expires_at = int(row.get("expires_at", 0) or 0)
        if expires_at <= 0 or expires_at > now:
            continue
        sender = str(row.get("sender", "") or "")
        if not sender:
            trade_update_request(str(row.get("id", "") or ""), status="expired")
            expired += 1
            continue
        sender_raw, sender_player = _load_account_player(sender)
        offered_count = len(list(row.get("offered_items", []) or []))
        gold_return = int(row.get("gold_offer", 0) or 0)
        for item_payload in list(row.get("offered_items", []) or []):
            try:
                sender_player.stash.append(_item_from_payload(item_payload))
            except Exception:
                continue
        sender_player.gold = int(sender_player.gold or 0) + gold_return
        for cid, amount in dict(row.get("offered_currencies", {}) or {}).items():
            add_currency(sender_player, cid, int(amount or 0))
        _save_account_player(sender, sender_raw, sender_player)
        trade_id = str(row.get("id", "") or "")
        trade_update_request(trade_id, status="expired")
        _event_log_add(
            "trade",
            "Trade request expired",
            f"{sender} escrow returned • {offered_count} item(s) • {gold_return}g",
            severity="warn",
            meta={"trade_id": trade_id, "sender": sender, "expired": True},
        )
        expired += 1
    return expired


def _item_matches_snapshot(item: Item, snapshot: dict) -> bool:
    if not snapshot:
        return False
    return (
        str(getattr(item, "name", "") or "") == str(snapshot.get("name", "") or "")
        and str(getattr(item, "rarity", "") or "") == str(snapshot.get("rarity", "") or "")
        and str(getattr(item, "slot", "") or "") == str(snapshot.get("slot", "") or "")
        and int(getattr(item, "power", 0) or 0) == int(snapshot.get("power", 0) or 0)
    )


def _snapshot_trade_item(item: Item) -> dict:
    return {
        "name": str(getattr(item, "name", "") or "Item"),
        "rarity": str(getattr(item, "rarity", "") or "common"),
        "slot": str(getattr(item, "slot", "") or "-"),
        "power": int(getattr(item, "power", 0) or 0),
        "source": str(getattr(item, "source", "") or "system"),
    }


def _persist_state() -> None:
    try:
        account_id = _active_account()
        state_file = _state_file_for_account(account_id)
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        player_payload = current_player.model_dump() if hasattr(current_player, "model_dump") else current_player.dict()
        payload = {
            "player": player_payload,
            "idle_tuning": dict(IDLE_TUNING),
            "idle_tuning_presets": dict(IDLE_TUNING_PRESETS),
            "idle_skill_tuning_presets": dict(IDLE_SKILL_TUNING_PRESETS),
            "idle_skills": dict(IDLE_SKILLS),
            "saved_at": int(time.time()),
            "account": account_id,
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)
        idx = _read_account_index()
        accounts = idx.get("accounts", [])
        if account_id not in accounts:
            accounts.append(account_id)
        _write_account_index(account_id, accounts)
    except Exception:
        # Persistence errors should never break gameplay loops.
        pass


def _migrate_legacy_state_file() -> None:
    """One-time migration from the old single-save file
    (database/game_state.json, from before per-account saves existed)
    into the new per-account format, so a "default" account inherits
    whatever was there. Runs once at import; unlike the old
    _load_persisted_state, it never sets a "the" active account --
    there isn't one until a request is authenticated."""
    default_file = _state_file_for_account("default")
    if os.path.exists(default_file) or not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        raw["account"] = "default"
        raw["saved_at"] = int(time.time())
        os.makedirs(os.path.dirname(default_file), exist_ok=True)
        with open(default_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=True)
        idx = _read_account_index()
        accounts = idx.get("accounts", ["default"])
        if "default" not in accounts:
            accounts.append("default")
        _write_account_index(idx.get("active", "default"), accounts)
    except Exception:
        pass


def _now_ts() -> float:
    return float(time.time())


def _event_log_add(kind: str, title: str, detail: str = "", severity: str = "info", meta: dict | None = None) -> None:
    row = {
        "ts": int(_now_ts()),
        "kind": str(kind or "system"),
        "title": str(title or "Event"),
        "detail": str(detail or ""),
        "severity": str(severity or "info"),
        "meta": dict(meta or {}),
    }
    GAME_EVENTS.append(row)
    if len(GAME_EVENTS) > 600:
        del GAME_EVENTS[:-600]


def _counter_add(key: str, amount: float) -> None:
    if amount <= 0:
        return
    counters = dict(getattr(current_player, "progress_counters", {}) or {})
    counters[key] = float(counters.get(key, 0.0) or 0.0) + float(amount)
    current_player.progress_counters = counters


def _mark_mechanic_learned(mechanic_id: str, title: str, detail: str = "", kind: str = "codex") -> bool:
    mid = str(mechanic_id or "").strip().lower()
    if not mid:
        return False
    learned = dict(getattr(current_player, "mechanics_learned", {}) or {})
    if int(learned.get(mid, 0) or 0) > 0:
        return False
    learned[mid] = int(_now_ts())
    current_player.mechanics_learned = learned
    _event_log_add(kind, f"Mechanic learned: {title}", detail, severity="success", meta={"mechanic_id": mid})
    return True


def _objectives_state() -> dict:
    counters = dict(getattr(current_player, "progress_counters", {}) or {})
    claimed = set(str(x) for x in list(getattr(current_player, "objectives_claimed", []) or []))
    rows = []
    for row in OBJECTIVE_CONFIG:
        oid = str(row.get("id", "") or "")
        key = str(row.get("counter", "") or "")
        target = float(row.get("target", 1) or 1)
        value = float(counters.get(key, 0.0) or 0.0)
        pct = max(0.0, min(1.0, value / max(1.0, target)))
        rows.append({
            **row,
            "value": value,
            "target": target,
            "progress_pct": round(pct, 6),
            "completed": value >= target,
            "claimed": oid in claimed,
            "claimable": (value >= target) and (oid not in claimed),
        })
    return {
        "objectives": rows,
        "counters": counters,
        "claimed_count": len(claimed),
    }


def _guide_state() -> dict:
    counters = dict(getattr(current_player, "progress_counters", {}) or {})
    flags = dict(getattr(current_player, "guide_flags", {}) or {})
    dismissed = bool(flags.get("dismissed", False))
    idle_skill = str(dict(getattr(current_player, "idle_activity", {}) or {}).get("skill", "") or "").strip()
    objectives = _objectives_state()
    objective_rows = list(objectives.get("objectives", []) or [])
    claimable_count = sum(1 for row in objective_rows if bool(row.get("claimable", False)))
    claimed_count = sum(1 for row in objective_rows if bool(row.get("claimed", False)))
    learned_count = int(len(dict(getattr(current_player, "mechanics_learned", {}) or {})))

    steps = [
        {
            "id": "start_run",
            "label": "Start your first run",
            "detail": "Open Routes and start a dungeon run.",
            "tab": "areas",
            "done": float(counters.get("enemies_defeated", 0.0) or 0.0) >= 1.0,
        },
        {
            "id": "clear_boss",
            "label": "Defeat the boss and exit",
            "detail": "Runs only complete after the boss dies and you leave the dungeon.",
            "tab": "combat",
            "done": float(counters.get("dungeons_cleared", 0.0) or 0.0) >= 1.0,
        },
        {
            "id": "start_idle",
            "label": "Start an idle activity",
            "detail": "Open an idle skill and let it run for offline progress.",
            "tab": "woodcutting",
            "done": bool(idle_skill) or float(counters.get("idle_seconds", 0.0) or 0.0) >= 60.0,
        },
        {
            "id": "claim_objective",
            "label": "Claim an objective reward",
            "detail": "Objectives convert early progress into gold, chests, and relics.",
            "tab": "home",
            "done": claimed_count >= 1,
            "cta_label": claimable_count > 0 and "Claim" or "Objectives",
        },
        {
            "id": "open_codex",
            "label": "Check the codex",
            "detail": "Use the codex to read learned mechanics, affixes, and dungeon structure.",
            "tab": "codex",
            "done": learned_count >= 1,
        },
    ]
    next_step = next((step for step in steps if not bool(step.get("done", False))), None)
    return {
        "show": (not dismissed) and next_step is not None,
        "dismissed": dismissed,
        "steps": steps,
        "next_step": next_step,
        "completed_count": sum(1 for step in steps if bool(step.get("done", False))),
        "total_count": len(steps),
    }


def _idle_cap_seconds(player: Player) -> int:
    base_hours = 48
    bonus_hours = int(player.idle_upgrades.get("duration_cap", 0) or 0) * 2
    return int(min(72, base_hours + bonus_hours) * 3600)


def _idle_effective_seconds(processed_seconds: float) -> float:
    s = max(0.0, float(processed_seconds or 0.0))
    p1 = min(s, 8 * 3600.0)
    p2 = min(max(s - (8 * 3600.0), 0.0), 16 * 3600.0)
    p3 = max(s - (24 * 3600.0), 0.0)
    # Diminishing returns for long offline windows.
    mid_mult = float(IDLE_TUNING.get("diminish_mid_mult", 0.62) or 0.62)
    long_mult = float(IDLE_TUNING.get("diminish_long_mult", 0.38) or 0.38)
    return p1 + (p2 * max(0.1, min(1.0, mid_mult))) + (p3 * max(0.05, min(0.9, long_mult)))


def _idle_session_bonus(player: Player, now_ts: float, skill: str) -> float:
    activity = dict(player.idle_activity or {})
    active_skill = str(activity.get("skill", "") or "").strip().lower()
    if active_skill != str(skill or "").strip().lower():
        return 1.0
    started_at = float(activity.get("started_at", 0.0) or 0.0)
    if started_at <= 0:
        return 1.0
    uptime = max(0.0, now_ts - started_at)
    hours = uptime / 3600.0
    # Reward sustained assignment without overtaking active play.
    return min(1.18, 1.0 + (min(12.0, hours) * 0.015))


def _idle_quality_bonus(level: float, processed_seconds: float) -> float:
    lvl = max(1.0, float(level or 1.0))
    duration_hours = max(0.0, float(processed_seconds or 0.0) / 3600.0)
    level_bonus = min(0.32, max(0.0, (lvl - 1.0) * 0.0035))
    duration_bonus = min(0.18, duration_hours * 0.01)
    return 1.0 + level_bonus + duration_bonus


def _roll_idle_rare_entry(table: list[dict]) -> dict:
    if not table:
        return {}
    total = sum(max(1, int(x.get("weight", 1) or 1)) for x in table)
    pick = random.randint(1, max(1, total))
    acc = 0
    for row in table:
        w = max(1, int(row.get("weight", 1) or 1))
        acc += w
        if pick <= acc:
            return row
    return table[-1]


def _generate_idle_item_drop(skill: str, level: float) -> dict:
    lvl = max(1.0, float(level or 1.0))
    # Idle items stay below active combat farming power; avoid high-tier spikes.
    risk = 0
    depth = max(1, min(30, int(1 + (lvl / 4.0))))
    item = generate_loot(is_boss=False, risk=risk, depth=depth, luck_bonus=0.0)

    rarity_rank = {
        "common": 1,
        "rare": 2,
        "epic": 3,
        "legendary": 4,
        "mythic": 5,
        "relic": 6,
    }
    cur_rank = rarity_rank.get(str(item.rarity).lower(), 1)
    if cur_rank > 3:
        item.rarity = "epic"
        cur_rank = 3

    # Clamp power with a gentle level scale.
    cap_by_rank = {1: 18, 2: 32, 3: 48}
    base_cap = cap_by_rank.get(cur_rank, 18)
    level_cap = int(base_cap + min(90, lvl * 0.8))
    item.power = max(4, min(int(item.power), level_cap))

    # Limit passive count on idle-generated items.
    passives = list(item.passives or [])
    if len(passives) > 2:
        item.passives = passives[:2]

    item.name = f"Idle {item.name}"
    item.source = "system"
    return {
        "kind": "item",
        "skill": skill,
        "name": item.name,
        "rarity": item.rarity,
        "power": int(item.power),
        "slot": item.slot,
    }, item


def _enhance_idle_item_drop(item_obj: Item, quality_bonus: float) -> Item:
    bonus = max(1.0, float(quality_bonus or 1.0))
    current_power = int(item_obj.power or 0)
    boosted = int(round(current_power * min(1.22, bonus)))
    item_obj.power = max(current_power, boosted)
    passives = list(item_obj.passives or [])
    if bonus >= 1.18 and len(passives) < 2:
        passives.append("tempered")
    item_obj.passives = passives[:2]
    return item_obj


def _idle_boost_multiplier(player: Player, now_ts: float) -> float:
    player.clear_expired_idle_boosts(now_ts)
    mult = 1.0
    for boost in list(player.idle_boosts or []):
        expires = float(boost.get("expires_at", 0.0) or 0.0)
        if expires <= now_ts:
            continue
        mult *= max(1.0, float(boost.get("mult", 1.0) or 1.0))
    max_boost = float(IDLE_TUNING.get("max_boost_mult", 3.5) or 3.5)
    return min(max(1.0, max_boost), max(1.0, mult))


def _idle_skill_public_state(player: Player) -> dict:
    skills = {}
    for skill_id, cfg in IDLE_SKILLS.items():
        state = player.idle_skill_state(skill_id)
        lvl = int(state.get("level", 1) or 1)
        skills[skill_id] = {
            "id": skill_id,
            "name": cfg.get("name", skill_id.title()),
            "level": lvl,
            "xp": int(state.get("xp", 0) or 0),
            "xp_to_next": int(state.get("xp_to_next", 100) or 100),
            "total_xp": int(state.get("total_xp", 0) or 0),
        }
    return skills


def _apply_idle_progress(player: Player, now_ts: float | None = None) -> dict:
    now = float(now_ts or _now_ts())
    player.clear_expired_idle_boosts(now)
    activity = dict(player.idle_activity or {})
    skill = str(activity.get("skill", "") or "").strip().lower()
    if not skill or skill not in IDLE_SKILLS:
        return {}

    last_tick = float(activity.get("last_tick_at", 0.0) or 0.0)
    if last_tick <= 0:
        player.idle_activity["last_tick_at"] = now
        return {}

    elapsed = max(0.0, now - last_tick)
    if elapsed < 10:
        return {}

    cap_seconds = _idle_cap_seconds(player)
    processed_seconds = min(elapsed, float(cap_seconds))
    effective_seconds = _idle_effective_seconds(processed_seconds)
    if effective_seconds <= 0:
        player.idle_activity["last_tick_at"] = now
        return {}
    _counter_add("idle_seconds", processed_seconds)

    cfg = IDLE_SKILLS[skill]
    state = player.idle_skill_state(skill)
    level = float(state.get("level", 1.0) or 1.0)
    efficiency_upgrade = int(player.idle_upgrades.get("efficiency", 0) or 0)
    rare_upgrade = int(player.idle_upgrades.get("rare_find", 0) or 0)
    level_eff = 1.0 + ((level - 1.0) * 0.012)
    upgrade_eff = 1.0 + (efficiency_upgrade * 0.06)
    boost_eff = _idle_boost_multiplier(player, now)
    session_eff = _idle_session_bonus(player, now, skill)
    rate_mult = float(IDLE_TUNING.get("idle_rate_mult", 0.92) or 0.92)
    total_eff = min(5.0, max(0.5, (level_eff * upgrade_eff * boost_eff * session_eff) * max(0.25, min(2.0, rate_mult))))
    quality_bonus = _idle_quality_bonus(level, processed_seconds)

    hour_factor = effective_seconds / 3600.0
    xp_gain = float(cfg.get("xp_per_hour", 0.0)) * hour_factor * total_eff
    gold_gain = float(cfg.get("gold_per_hour", 0.0)) * hour_factor * total_eff
    resource_gain = float(cfg.get("resource_per_hour", 0.0)) * hour_factor * total_eff
    resource_key = str(cfg.get("resource_key", "") or "")

    levels = player.gain_idle_xp(skill, xp_gain).get("levels", 0)
    gold_added = max(0, int(gold_gain))
    player.gold += gold_added

    resources_gained: dict[str, int] = {}
    if resource_key:
        amt = max(0, int(resource_gain))
        if amt > 0:
            player.add_resource(resource_key, amt)
            resources_gained[resource_key] = resources_gained.get(resource_key, 0) + amt

    rare_entries = []
    item_entries = []
    minute_ticks = max(0, int(processed_seconds // 60))
    rare_chance = float(cfg.get("rare_chance_per_min", 0.0) or 0.0)
    rare_chance *= float(IDLE_TUNING.get("rare_drop_rate_mult", 1.0) or 1.0)
    rare_chance *= (1.0 + (rare_upgrade * 0.08))
    rare_chance *= (1.0 + max(0.0, (level - 1.0) * 0.002))
    rare_chance *= min(1.35, quality_bonus)
    rare_chance = min(0.10, max(0.0, rare_chance))
    rare_failures = 0

    for _ in range(minute_ticks):
        if random.random() > rare_chance:
            rare_failures += 1
            continue
        row = _roll_idle_rare_entry(list(cfg.get("rare_table", [])))
        if not row:
            continue
        kind = str(row.get("kind", "resource") or "resource")
        key = str(row.get("key", "") or "")
        amount = max(1, int(row.get("amount", 1) or 1))
        if kind == "rune" and key:
            player.add_rune(key, amount)
            rare_entries.append({"kind": "rune", "key": key, "amount": amount})
        elif kind == "item":
            item_rate = float(IDLE_TUNING.get("item_drop_rate_mult", 1.0) or 1.0)
            if random.random() <= min(1.0, max(0.05, item_rate * min(1.2, quality_bonus))):
                for _ in range(amount):
                    item_meta, item_obj = _generate_idle_item_drop(skill, level)
                    item_obj = _enhance_idle_item_drop(item_obj, quality_bonus)
                    item_meta["power"] = int(item_obj.power)
                    item_meta["passives"] = list(item_obj.passives or [])
                    player.stash.append(item_obj)
                    item_entries.append(item_meta)
                    rare_entries.append(item_meta)
        elif key:
            player.add_resource(key, amount)
            resources_gained[key] = resources_gained.get(key, 0) + amount
            rare_entries.append({"kind": "resource", "key": key, "amount": amount})

    # Mild pity so long sessions are less likely to whiff entirely on rare loot.
    if minute_ticks >= 90 and not rare_entries:
        pity_roll = _roll_idle_rare_entry(list(cfg.get("rare_table", [])))
        pity_kind = str(pity_roll.get("kind", "resource") or "resource")
        pity_key = str(pity_roll.get("key", "") or "")
        pity_amount = max(1, int(pity_roll.get("amount", 1) or 1))
        if pity_kind == "item":
            item_meta, item_obj = _generate_idle_item_drop(skill, level)
            item_obj = _enhance_idle_item_drop(item_obj, quality_bonus)
            item_meta["power"] = int(item_obj.power)
            item_meta["passives"] = list(item_obj.passives or [])
            player.stash.append(item_obj)
            item_entries.append(item_meta)
            rare_entries.append({**item_meta, "pity": True})
        elif pity_kind == "rune" and pity_key:
            player.add_rune(pity_key, pity_amount)
            rare_entries.append({"kind": "rune", "key": pity_key, "amount": pity_amount, "pity": True})
        elif pity_key:
            player.add_resource(pity_key, pity_amount)
            resources_gained[pity_key] = resources_gained.get(pity_key, 0) + pity_amount
            rare_entries.append({"kind": "resource", "key": pity_key, "amount": pity_amount, "pity": True})

    player.idle_activity["last_tick_at"] = now
    summary = {
        "skill": skill,
        "skill_name": cfg.get("name", skill.title()),
        "elapsed_seconds": int(elapsed),
        "processed_seconds": int(processed_seconds),
        "effective_seconds": int(effective_seconds),
        "capped": elapsed > processed_seconds,
        "overflow_seconds": max(0, int(elapsed - processed_seconds)),
        "diminished_seconds": max(0, int(processed_seconds - effective_seconds)),
        "efficiency_mult": round(total_eff, 3),
        "session_mult": round(session_eff, 3),
        "quality_mult": round(quality_bonus, 3),
        "xp_gained": int(xp_gain),
        "levels_gained": int(levels),
        "gold_gained": int(gold_added),
        "resources_gained": resources_gained,
        "items_gained": item_entries[:10],
        "rare_drops": rare_entries[:20],
        "rare_drop_count": len(rare_entries),
        "rare_miss_count": int(rare_failures),
        "at": int(now),
    }
    player.idle_last_summary = summary
    return summary


def _idle_state_payload(player: Player, include_summary: bool = True) -> dict:
    now = _now_ts()
    progress = _apply_idle_progress(player, now)
    if progress:
        _persist_state()
    activity = dict(player.idle_activity or {})
    skill_id = str(activity.get("skill", "") or "").strip().lower()
    active = skill_id in IDLE_SKILLS
    boosts = []
    player.clear_expired_idle_boosts(now)
    for b in list(player.idle_boosts or []):
        expires = float(b.get("expires_at", 0.0) or 0.0)
        if expires <= now:
            continue
        boosts.append({
            "id": str(b.get("id", "") or ""),
            "name": str(b.get("name", "") or ""),
            "mult": float(b.get("mult", 1.0) or 1.0),
            "remaining_sec": max(0, int(expires - now)),
        })

    out = {
        "active": active,
        "activity": {
            "skill": skill_id,
            "skill_name": IDLE_SKILLS.get(skill_id, {}).get("name", "") if active else "",
            "started_at": int(float(activity.get("started_at", 0.0) or 0.0)),
            "last_tick_at": int(float(activity.get("last_tick_at", 0.0) or 0.0)),
            "uptime_sec": max(0, int(now - float(activity.get("started_at", now) or now))) if active else 0,
        },
        "skills": _idle_skill_public_state(player),
        "upgrades": dict(player.idle_upgrades or {}),
        "upgrade_catalog": IDLE_UPGRADE_CONFIG,
        "boosts": boosts,
        "boost_catalog": IDLE_BOOST_CONFIG,
        "tuning": dict(IDLE_TUNING),
        "tuning_presets": dict(IDLE_TUNING_PRESETS),
        "skill_tuning": {
            sid: {
                "name": cfg.get("name", sid.title()),
                "xp_per_hour": float(cfg.get("xp_per_hour", 0.0) or 0.0),
                "gold_per_hour": float(cfg.get("gold_per_hour", 0.0) or 0.0),
                "resource_per_hour": float(cfg.get("resource_per_hour", 0.0) or 0.0),
                "rare_chance_per_min": float(cfg.get("rare_chance_per_min", 0.0) or 0.0),
            }
            for sid, cfg in IDLE_SKILLS.items()
        },
        "skill_tuning_presets": dict(IDLE_SKILL_TUNING_PRESETS),
        "resources": player.resources,
        "gold": int(player.gold),
        "latest_progress": progress,
        "offline_cap_sec": _idle_cap_seconds(player),
    }
    if include_summary:
        out["offline_summary"] = dict(player.idle_last_summary or {})
    return out


def _idle_tuning_allowed_ranges() -> dict[str, tuple[float, float]]:
    return {
        "idle_rate_mult": (0.2, 2.0),
        "diminish_mid_mult": (0.1, 1.0),
        "diminish_long_mult": (0.05, 0.9),
        "rare_drop_rate_mult": (0.25, 3.0),
        "max_boost_mult": (1.0, 6.0),
        "item_drop_rate_mult": (0.05, 2.0),
    }


def _apply_idle_tuning_patch(changes: dict) -> dict:
    allowed = _idle_tuning_allowed_ranges()
    applied = {}
    for key, val in (changes or {}).items():
        if key not in allowed:
            continue
        lo, hi = allowed[key]
        try:
            num = float(val)
        except Exception:
            continue
        num = max(lo, min(hi, num))
        IDLE_TUNING[key] = num
        applied[key] = num
    return applied


def _skill_tuning_allowed_ranges() -> dict[str, tuple[float, float]]:
    return {
        "xp_per_hour": (5.0, 600.0),
        "gold_per_hour": (0.0, 800.0),
        "resource_per_hour": (0.0, 500.0),
        "rare_chance_per_min": (0.0001, 0.05),
    }


def _apply_skill_tuning_patch(skill: str, changes: dict) -> dict:
    cfg = IDLE_SKILLS.get(skill, {})
    allowed = _skill_tuning_allowed_ranges()
    applied = {}
    for key, val in (changes or {}).items():
        if key not in allowed:
            continue
        lo, hi = allowed[key]
        try:
            num = float(val)
        except Exception:
            continue
        num = max(lo, min(hi, num))
        cfg[key] = num
        applied[key] = num
    return applied


def _battle_skill_row(skill_id: str) -> dict:
    sid = str(skill_id or "").strip().lower()
    return dict(BATTLE_SKILL_CATALOG.get(sid, {}))


def _battle_skill_unlocked(player: Player, skill_id: str) -> bool:
    row = _battle_skill_row(skill_id)
    if not row:
        return False
    req = int(row.get("unlock_level", 1) or 1)
    return int(getattr(player, "level", 1) or 1) >= req


def _apply_battle_defaults(player: Player) -> None:
    if not isinstance(getattr(player, "battle_tree", None), dict):
        player.battle_tree = {}
    for node in BATTLE_TREE_CONFIG.keys():
        player.battle_tree[node] = int(player.battle_tree.get(node, 0) or 0)

    if not isinstance(getattr(player, "battle_state", None), dict):
        player.battle_state = {}
    player.battle_state["last_roll"] = str(player.battle_state.get("last_roll", "") or "")
    player.battle_state["rerolls"] = int(player.battle_state.get("rerolls", 0) or 0)
    player.battle_state["curse_charge"] = float(player.battle_state.get("curse_charge", 0.0) or 0.0)

    if not isinstance(getattr(player, "battle_skills", None), list):
        player.battle_skills = []
    cleaned = [str(x or "").strip().lower() for x in player.battle_skills if str(x or "").strip()]
    if len(cleaned) != 6:
        cleaned = ["quick_slash", "cleave", "guard_stance", "focus_channel", "self_bleed", "blank_stumble"]
    player.battle_skills = cleaned[:6]

    min_cap = int(BATTLE_MANA_CONFIG.get("min_cap", 8) or 8)
    max_cap = int(BATTLE_MANA_CONFIG.get("max_cap", 50) or 50)
    player.mana_cap = int(max(min_cap, min(max_cap, int(getattr(player, "mana_cap", 20) or 20))))
    raw_mana = player.battle_state.get("mana", None)
    if raw_mana is None:
        player.battle_state["mana"] = int(player.mana_cap)
    else:
        player.battle_state["mana"] = int(max(0, min(int(player.mana_cap), int(raw_mana or 0))))
    if not isinstance(getattr(player, "battle_presets", None), dict):
        player.battle_presets = {}
    cleaned_presets = {}
    for pid, pskills in dict(player.battle_presets or {}).items():
        preset_id = _safe_battle_preset_id(str(pid or ""))
        if not preset_id:
            continue
        rows = [str(x or "").strip().lower() for x in (pskills or []) if str(x or "").strip()]
        if len(rows) == 6:
            cleaned_presets[preset_id] = rows[:6]
    for core_id, core_skills in CORE_BATTLE_PRESETS.items():
        if core_id not in cleaned_presets:
            cleaned_presets[core_id] = list(core_skills)
    player.battle_presets = cleaned_presets
    if not isinstance(getattr(player, "battle_mastery", None), dict):
        player.battle_mastery = {}
    cleaned_mastery = {}
    for sid, row in dict(player.battle_mastery or {}).items():
        skill_id = str(sid or "").strip().lower()
        if skill_id not in BATTLE_SKILL_CATALOG:
            continue
        if not isinstance(row, dict):
            row = {}
        cleaned_mastery[skill_id] = {
            "level": float(max(1.0, row.get("level", 1.0))),
            "xp": float(max(0.0, row.get("xp", 0.0))),
            "xp_to_next": float(max(20.0, row.get("xp_to_next", 100.0))),
            "total_xp": float(max(0.0, row.get("total_xp", 0.0))),
        }
    player.battle_mastery = cleaned_mastery


def _safe_battle_preset_id(name: str) -> str:
    raw = str(name or "").strip().lower()
    clean = "".join(ch for ch in raw if ch.isalnum() or ch in ("_", "-"))
    return clean[:32]


def _battle_mastery_state(player: Player, skill_id: str) -> dict:
    _apply_battle_defaults(player)
    sid = str(skill_id or "").strip().lower()
    if sid not in player.battle_mastery:
        player.battle_mastery[sid] = {
            "level": 1.0,
            "xp": 0.0,
            "xp_to_next": 100.0,
            "total_xp": 0.0,
        }
    return player.battle_mastery[sid]


def _battle_mastery_gain(player: Player, skill_id: str, amount: float) -> dict:
    sid = str(skill_id or "").strip().lower()
    if sid not in BATTLE_SKILL_CATALOG:
        return {"levels": 0}
    st = _battle_mastery_state(player, sid)
    amt = float(max(0.0, amount or 0.0))
    if amt <= 0:
        return {"levels": 0}
    st["xp"] += amt
    st["total_xp"] += amt
    gained = 0
    while st["xp"] >= st["xp_to_next"]:
        st["xp"] -= st["xp_to_next"]
        st["level"] += 1.0
        gained += 1
        st["xp_to_next"] = max(30.0, st["xp_to_next"] * 1.14)
    return {"levels": gained}


def _battle_mastery_tier(level: float) -> int:
    lv = float(level or 1.0)
    if lv >= 25.0:
        return 3
    if lv >= 12.0:
        return 2
    if lv >= 5.0:
        return 1
    return 0


def _battle_mastery_next_milestone(level: float) -> int:
    lv = float(level or 1.0)
    for m in BATTLE_MASTERY_MILESTONES:
        if lv < float(m):
            return int(m)
    return int(BATTLE_MASTERY_MILESTONES[-1])


def _battle_mana_upgrade_cost(current_cap: int) -> int:
    cfg = BATTLE_MANA_CONFIG
    min_cap = int(cfg.get("min_cap", 8) or 8)
    max_cap = int(cfg.get("max_cap", 50) or 50)
    base = int(cfg.get("base_cost_gold", 420) or 420)
    mult = float(cfg.get("cost_mult", 1.22) or 1.22)
    cap = int(max(min_cap, min(max_cap, int(current_cap or min_cap))))
    steps = max(0, cap - min_cap)
    return int(max(1, round(base * (mult ** steps))))


def _battle_reroll_cap(player: Player) -> int:
    _apply_battle_defaults(player)
    node = int(player.battle_tree.get("echo_reroll", 0) or 0)
    return max(1, 1 + min(2, node))


def _validate_battle_loadout(skills: list[str], mana_cap: int, player: Player | None = None, enforce_unlocks: bool = False) -> dict:
    cleaned = [str(x or "").strip().lower() for x in (skills or []) if str(x or "").strip()]
    if len(cleaned) != 6:
        return {"ok": False, "error": "Loadout must contain exactly 6 skills"}
    if len(set(cleaned)) != 6:
        return {"ok": False, "error": "Loadout cannot contain duplicate skills"}

    rows = []
    for sid in cleaned:
        row = _battle_skill_row(sid)
        if not row:
            return {"ok": False, "error": f"Unknown skill '{sid}'"}
        if enforce_unlocks and player is not None:
            req = int(row.get("unlock_level", 1) or 1)
            if int(getattr(player, "level", 1) or 1) < req:
                return {"ok": False, "error": f"Skill '{sid}' requires level {req}"}
        rows.append(row)

    normal_count = sum(1 for r in rows if str(r.get("kind", "")) == "normal")
    cursed_count = sum(1 for r in rows if str(r.get("kind", "")) == "cursed")
    if normal_count != 4 or cursed_count != 2:
        return {"ok": False, "error": "Loadout requires 4 normal and 2 cursed skills"}

    mana = sum(int(r.get("mana_cost", 0) or 0) for r in rows)
    min_cap = int(BATTLE_MANA_CONFIG.get("min_cap", 8) or 8)
    max_cap = int(BATTLE_MANA_CONFIG.get("max_cap", 50) or 50)
    cap = int(max(min_cap, min(max_cap, int(mana_cap or 20))))
    if mana > cap:
        return {"ok": False, "error": f"Mana cap exceeded ({mana}/{cap})"}

    return {"ok": True, "skills": cleaned, "mana_used": mana, "mana_cap": cap}


def _battle_loadout_state(player: Player) -> dict:
    _apply_battle_defaults(player)
    weight_rows = _battle_roll_weights(player)
    weight_map = {sid: float(w) for sid, w in weight_rows}
    total_weight = sum(max(0.01, float(w or 0.0)) for _, w in weight_rows)
    rows = []
    mana_used = 0
    for sid in list(player.battle_skills or []):
        row = _battle_skill_row(sid)
        if not row:
            continue
        mastery = _battle_mastery_state(player, sid)
        mana = int(row.get("mana_cost", 0) or 0)
        mana_used += mana
        w = float(weight_map.get(sid, 0.0) or 0.0)
        prob = (w / total_weight) if total_weight > 0 else 0.0
        req = int(row.get("unlock_level", 1) or 1)
        unlocked = int(player.level) >= req
        rows.append({
            "id": sid,
            "name": row.get("name", sid),
            "kind": row.get("kind", "normal"),
            "mana_cost": mana,
            "unlock_level": req,
            "unlocked": bool(unlocked),
            "base_weight": float(row.get("base_weight", 1.0) or 1.0),
            "effective_weight": round(w, 4),
            "roll_chance": round(prob, 6),
            "mastery": {
                "level": float(mastery.get("level", 1.0) or 1.0),
                "xp": float(mastery.get("xp", 0.0) or 0.0),
                "xp_to_next": float(mastery.get("xp_to_next", 100.0) or 100.0),
            },
            "tags": list(row.get("tags", [])),
        })
    catalog_payload = {}
    mastery_codex = {}
    for sid, row in BATTLE_SKILL_CATALOG.items():
        req = int(row.get("unlock_level", 1) or 1)
        mastery = _battle_mastery_state(player, sid)
        m_level = float(mastery.get("level", 1.0) or 1.0)
        m_xp = float(mastery.get("xp", 0.0) or 0.0)
        m_xp_to_next = float(mastery.get("xp_to_next", 100.0) or 100.0)
        next_ms = _battle_mastery_next_milestone(m_level)
        mastery_codex[sid] = {
            "level": m_level,
            "xp": m_xp,
            "xp_to_next": m_xp_to_next,
            "total_xp": float(mastery.get("total_xp", 0.0) or 0.0),
            "tier": _battle_mastery_tier(m_level),
            "next_milestone": next_ms,
            "pct_to_next_level": round((m_xp / m_xp_to_next) if m_xp_to_next > 0 else 0.0, 6),
        }
        catalog_payload[sid] = {
            **dict(row),
            "unlock_level": req,
            "unlocked": int(player.level) >= req,
        }
    return {
        "mana_cap": int(player.mana_cap),
        "mana_used": int(mana_used),
        "mana_progress": {
            "min_cap": int(BATTLE_MANA_CONFIG.get("min_cap", 8) or 8),
            "max_cap": int(BATTLE_MANA_CONFIG.get("max_cap", 50) or 50),
            "next_cap": int(min(int(BATTLE_MANA_CONFIG.get("max_cap", 50) or 50), int(player.mana_cap) + 1)),
            "next_upgrade_cost": _battle_mana_upgrade_cost(int(player.mana_cap)),
            "at_max": int(player.mana_cap) >= int(BATTLE_MANA_CONFIG.get("max_cap", 50) or 50),
        },
        "rerolls": int(player.battle_state.get("rerolls", 0) or 0),
        "reroll_cap": int(_battle_reroll_cap(player)),
        "last_roll": str(player.battle_state.get("last_roll", "") or ""),
        "curse_charge": round(float(player.battle_state.get("curse_charge", 0.0) or 0.0), 4),
        "skills": rows,
        "roll_preview": rows,
        "tree": dict(player.battle_tree or {}),
        "tree_config": dict(BATTLE_TREE_CONFIG),
        "catalog": catalog_payload,
        "mastery_codex": mastery_codex,
        "mastery_milestones": list(BATTLE_MASTERY_MILESTONES),
        "presets": {str(k): list(v) for k, v in dict(player.battle_presets or {}).items()},
        "core_presets": sorted(list(CORE_BATTLE_PRESETS.keys())),
    }


def _battle_roll_weights(player: Player) -> list[tuple[str, float]]:
    _apply_battle_defaults(player)
    out = []
    loadout = list(player.battle_skills or [])
    slot_one_bonus = int(player.battle_tree.get("loaded_slot_one", 0) or 0)
    curse_tune = int(player.battle_tree.get("curse_attunement", 0) or 0)

    for i, sid in enumerate(loadout):
        row = _battle_skill_row(sid)
        if not row:
            continue
        w = float(row.get("base_weight", 1.0) or 1.0)
        mastery = _battle_mastery_state(player, sid)
        mastery_level = float(mastery.get("level", 1.0) or 1.0)
        w *= (1.0 + min(0.25, max(0.0, (mastery_level - 1.0) * 0.01)))
        if i == 0 and slot_one_bonus > 0:
            w *= (1.0 + (0.18 * slot_one_bonus))
        if str(row.get("kind", "")) == "cursed" and curse_tune > 0:
            w *= max(0.52, 1.0 - (0.08 * curse_tune))
        out.append((sid, max(0.05, w)))
    return out


def _weighted_pick_skill(weight_rows: list[tuple[str, float]], exclude_skill: str = "") -> str:
    rows = [(sid, w) for sid, w in (weight_rows or []) if sid and sid != exclude_skill]
    if not rows:
        rows = list(weight_rows or [])
    total = sum(max(0.01, float(w or 0.0)) for _, w in rows)
    if total <= 0:
        return str(rows[0][0]) if rows else ""
    pick = random.random() * total
    acc = 0.0
    for sid, w in rows:
        acc += max(0.01, float(w or 0.0))
        if pick <= acc:
            return sid
    return str(rows[-1][0]) if rows else ""


def _has_negative_status(player: Player) -> bool:
    status = getattr(player, "status", {}) or {}
    for key in ("bleed", "burn", "vulnerable", "weak", "poison"):
        if key in status:
            return True
    return False


def _roll_battle_skill(player: Player, use_reroll: bool = False) -> dict:
    _apply_battle_defaults(player)
    weights = _battle_roll_weights(player)
    rolled = _weighted_pick_skill(weights)
    if not rolled:
        rolled = "quick_slash"
    rerolls_before = int(player.battle_state.get("rerolls", 0) or 0)
    rerolled = False
    if use_reroll and rerolls_before > 0:
        alt = _weighted_pick_skill(weights, exclude_skill=rolled)
        if alt:
            rolled = alt
            rerolled = True
            player.battle_state["rerolls"] = max(0, rerolls_before - 1)

    last = str(player.battle_state.get("last_roll", "") or "")
    granted = 0
    if int(player.battle_tree.get("echo_reroll", 0) or 0) > 0 and last and last == rolled:
        cap = _battle_reroll_cap(player)
        current = int(player.battle_state.get("rerolls", 0) or 0)
        if current < cap:
            player.battle_state["rerolls"] = min(cap, current + 1)
            granted = 1
    player.battle_state["last_roll"] = rolled
    row = _battle_skill_row(rolled)
    return {
        "id": rolled,
        "name": row.get("name", rolled),
        "kind": row.get("kind", "normal"),
        "action": row.get("action", "basic"),
        "damage_mult": float(row.get("damage_mult", 1.0) or 1.0),
        "tags": list(row.get("tags", [])),
        "rerolled": rerolled,
        "reroll_granted": granted,
        "rerolls_left": int(player.battle_state.get("rerolls", 0) or 0),
    }


def _battle_damage_multiplier(player: Player, rolled_skill: dict) -> float:
    mult = float(rolled_skill.get("damage_mult", 1.0) or 1.0)
    sid = str(rolled_skill.get("id", "") or "")
    mastery = _battle_mastery_state(player, sid)
    mastery_level = float(mastery.get("level", 1.0) or 1.0)
    mult *= (1.0 + min(0.30, max(0.0, (mastery_level - 1.0) * 0.015)))
    power = int(player.battle_tree.get("power_training", 0) or 0)
    if power > 0:
        mult *= (1.0 + (0.03 * power))
    affliction = int(player.battle_tree.get("affliction_mastery", 0) or 0)
    if affliction > 0 and _has_negative_status(player):
        mult *= (1.0 + (0.05 * affliction))
    curse_charge = float(player.battle_state.get("curse_charge", 0.0) or 0.0)
    if curse_charge > 0:
        mult *= (1.0 + min(0.35, curse_charge))
        player.battle_state["curse_charge"] = 0.0
    return max(0.1, mult)


def _apply_cursed_skill(player: Player, enemy: Enemy, rolled_skill: dict) -> dict:
    sid = str(rolled_skill.get("id", "") or "")
    mastery = _battle_mastery_state(player, sid)
    mastery_level = float(mastery.get("level", 1.0) or 1.0)
    mastery_tier = _battle_mastery_tier(mastery_level)
    curse_tune = int(player.battle_tree.get("curse_attunement", 0) or 0)
    mana_gain = 2 + max(0, curse_tune)
    if mastery_tier >= 1:
        mana_gain += 1
    _gain_mana(player, mana_gain)
    charge_gain = (0.04 + curse_tune * 0.02)
    if mastery_tier >= 2:
        charge_gain += 0.03
    if mastery_tier >= 3:
        charge_gain += 0.04
    player.battle_state["curse_charge"] = float(player.battle_state.get("curse_charge", 0.0) or 0.0) + charge_gain

    detail = {}
    perks = []
    if sid == "self_bleed":
        self_dmg = 4 + int(player.level * 0.10)
        if mastery_tier >= 1:
            self_dmg = max(1, int(round(self_dmg * 0.75)))
            perks.append("self_bleed_mitigation")
        player.hp = max(0.0, float(player.hp) - self_dmg)
        add_status(player, "bleed", turns=2, potency=max(1.0, round(self_dmg * 0.22, 2)))
        current = int(player.battle_state.get("rerolls", 0) or 0)
        reroll_gain = 1
        player.battle_state["rerolls"] = min(_battle_reroll_cap(player), current + reroll_gain)
        detail = {"self_damage": self_dmg, "effect": "blood_pact", "reroll_gain": reroll_gain}
    elif sid == "frail_guard":
        add_status(player, "vulnerable", turns=2, potency=0.12)
        add_status(player, "guard", turns=1, potency=0.18)
        if mastery_tier >= 2:
            add_status(player, "guard", turns=1, potency=0.08)
            perks.append("extra_guard")
        detail = {"effect": "vulnerable_plus_guard"}
    else:
        current = int(player.battle_state.get("rerolls", 0) or 0)
        reroll_gain = 1 + (1 if mastery_tier >= 3 else 0)
        player.battle_state["rerolls"] = min(_battle_reroll_cap(player), current + reroll_gain)
        mana_bonus = 0
        if mastery_tier >= 1:
            mana_bonus = 2
            _gain_mana(player, mana_bonus)
            perks.append("insight_mana")
        if mastery_tier >= 3:
            perks.append("blank_reroll")
        detail = {"effect": "insight_reroll", "reroll_gain": reroll_gain, "mana_gain": mana_bonus}

    return {
        "event": "player_action",
        "action": "cursed",
        "skill_roll": rolled_skill,
        "damage": 0.0,
        "enemy_hp": float(enemy.hp),
        "mana_after": _combat_mana(player),
        "player_hp": float(player.hp),
        "battle_detail": detail,
        "mastery_perks": perks,
        "cooldowns": player.action_cooldowns,
        "enemy_status": getattr(enemy, "status", {}),
        "player_status": getattr(player, "status", {}),
        "passive_triggers": {},
    }


_migrate_legacy_state_file()


# One in-memory bundle per account, populated (once, from that
# account's save file) the first time this process sees it, then
# reused every later request for that account -- the same effective
# behavior as the old single cached current_player, just one per
# account instead of one for the whole process.
_ACCOUNT_CACHE: dict[str, dict[str, Any]] = {}


def _get_or_create_account_bundle(account_id: str) -> dict[str, Any]:
    bundle = _ACCOUNT_CACHE.get(account_id)
    if bundle is None:
        bundle = _build_account_bundle(account_id)
        _ACCOUNT_CACHE[account_id] = bundle
    return bundle


# Paths reachable with no login at all: the page shells (their own JS
# calls the real data endpoints below, which DO require a token, and
# redirects to /login on a 401), the auth endpoints that issue a token
# in the first place, a status probe, and the API docs. Every other
# path 401s immediately unless the request carries a valid
# `Authorization: Bearer <token>`.
_PUBLIC_PATHS = {"/", "/game", "/login", "/ai/status", "/docs", "/redoc", "/openapi.json",
                  "/auth/register", "/auth/login"}
_PUBLIC_PREFIXES = ("/static/",)


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in _PUBLIC_PATHS or path.startswith(_PUBLIC_PREFIXES):
        return await call_next(request)

    token = auth.token_from_authorization_header(request.headers.get("authorization"))
    account_id = auth.verify_token(token) if token else None
    if account_id is None:
        return JSONResponse({"error": "Not authenticated. Log in first (POST /auth/login)."}, status_code=401)

    bundle = _get_or_create_account_bundle(account_id)
    ctx_tokens = [
        _player_ctx.set(bundle["player"]),
        _active_account_ctx.set(account_id),
        _idle_tuning_ctx.set(bundle["idle_tuning"]),
        _idle_tuning_presets_ctx.set(bundle["idle_tuning_presets"]),
        _idle_skill_tuning_presets_ctx.set(bundle["idle_skill_tuning_presets"]),
        _idle_skills_ctx.set(bundle["idle_skills"]),
        session.set_active_session(bundle["session"]),
    ]
    try:
        return await call_next(request)
    finally:
        for ctx_token in reversed(ctx_tokens):
            ctx_token.var.reset(ctx_token)


@app.get("/login", response_class=HTMLResponse)
def login_page():
    with open(os.path.join(BASE_DIR, "frontend", "login.html"), "r", encoding="utf-8") as f:
        return f.read()


# -------------------------
# Auth
# -------------------------
@app.post("/auth/register")
def auth_register(payload: dict):
    username = str(payload.get("username", "") or "")
    password = str(payload.get("password", "") or "")
    try:
        account_id = auth.register(username, password)
    except auth.AuthError as e:
        return {"error": str(e)}
    return {"ok": True, "account": account_id, "token": auth.issue_token(account_id)}


@app.post("/auth/login")
def auth_login(payload: dict):
    username = str(payload.get("username", "") or "")
    password = str(payload.get("password", "") or "")
    try:
        account_id = auth.verify_login(username, password)
    except auth.AuthError as e:
        return {"error": str(e)}
    return {"ok": True, "account": account_id, "token": auth.issue_token(account_id)}


@app.get("/auth/me")
def auth_me():
    return {"account": _active_account()}


# -------------------------
# Account
# -------------------------
@app.get("/account/state")
def account_state():
    return _account_state_payload()


@app.get("/account/list")
def account_list():
    return _account_state_payload()


# These three used to let anyone jump to any named save with zero
# ownership check -- exactly the hole real accounts close. "Account"
# now means "one authenticated login", not "one of several named save
# slots a single unauthenticated session can switch between", so
# switching/renaming/deleting someone's account no longer has a
# coherent meaning here; log in as the account you want instead.
_ACCOUNT_SWITCHING_RETIRED = (
    "This endpoint is no longer supported. Log in as a different "
    "account instead (POST /auth/login) -- each login is its own "
    "account now, not a save slot to switch between."
)


@app.post("/account/use")
def account_use(payload: dict):
    return {"error": _ACCOUNT_SWITCHING_RETIRED}


@app.post("/account/save")
def account_save():
    _persist_state()
    state = _account_state_payload()
    active = str(state.get("active", "default") or "default")
    saved_at = 0
    for row in (state.get("accounts", []) or []):
        if str(row.get("id", "") or "") == active:
            saved_at = int(row.get("saved_at", 0) or 0)
            break
    return {"ok": True, "account": active, "saved_at": saved_at, "state": state}


@app.post("/account/rename")
def account_rename(payload: dict):
    return {"error": _ACCOUNT_SWITCHING_RETIRED}


@app.post("/account/delete")
def account_delete(payload: dict):
    return {"error": _ACCOUNT_SWITCHING_RETIRED}


# -------------------------
# Player
# -------------------------
@app.get("/player/stats")
def player_stats():
    idle_state = _idle_state_payload(current_player, include_summary=True)
    return {
        "level": current_player.level,
        "depth": current_player.depth,
        "exp": current_player.exp,
        "exp_to_next": current_player.exp_to_next,
        "hp": current_player.hp,
        "max_hp": current_player.max_hp,
        "attack": current_player.attack,
        "defense": current_player.defense,
        "stat_points": current_player.stat_points,
        "prestige": current_player.prestige,
        "gold": current_player.gold,
        "stamina": current_player.stamina,
        "max_stamina": current_player.max_stamina,
        "last_action": current_player.last_action,
        "action_streak": current_player.action_streak,
        "action_cooldowns": current_player.action_cooldowns,
        "combo_windows": current_player.combo_windows,

        # raw stats (Step 11 UI needs these)
        "strength": current_player.strength,
        "dexterity": current_player.dexterity,
        "intelligence": current_player.intelligence,
        "vitality": current_player.vitality,
        "luck": current_player.luck,

        # derived helpers
        "dodge_bonus": current_player.dodge_bonus,
        "loot_luck": current_player.loot_luck,

        "equipment": current_player.equipment,
        "run_modifiers": session.SESSION.get("modifiers", []),
        "resources": current_player.resources,
        "runes": current_player.runes,
        "runecrafting": {
            "level": current_player.runecrafting_level,
            "xp": current_player.runecrafting_xp,
            "xp_to_next": current_player.runecrafting_xp_to_next,
        },
        "slayer": {
            "level": current_player.slayer_level,
            "xp": current_player.slayer_xp,
            "xp_to_next": current_player.slayer_xp_to_next,
            "task": current_player.slayer_task,
        },
        "prayer": {
            "active": current_player.active_prayer,
            "book": PRAYER_BOOK,
        },
        "build_runes": {
            "slots": {
                "capacity": _rune_slot_capacity(current_player),
                "equipped": current_player.rune_loadout,
            },
            "mods": _collect_rune_mods(current_player),
            "inventory_count": len(current_player.rune_items),
            "chests": int(current_player.resources.get("arcane_chest", 0) or 0),
            "relics": int(current_player.resources.get("rune_relic", 0) or 0),
        },
        "idle": idle_state,
        "mechanics_learned": dict(getattr(current_player, "mechanics_learned", {}) or {}),
        "account": {
            "active": _active_account(),
            "single_save_per_account": True,
        },
        "battle": _battle_loadout_state(current_player),
        "objectives": _objectives_state(),
        "guide": _guide_state(),
    }


@app.post("/player/spend_stat")
def spend_stat(stat: str, amount: int = 1):
    ok = current_player.spend_stat(stat, amount)
    if not ok:
        return {"success": False, "message": "Not enough stat points or invalid stat"}
    return {"success": True, "player": current_player}


@app.get("/battle/skills/state")
def battle_skills_state():
    return _battle_loadout_state(current_player)


@app.post("/battle/skills/equip")
def battle_skills_equip(payload: dict):
    skills = payload.get("skills", [])
    if not isinstance(skills, list):
        return {"error": "Expected object: { skills: [..6 skill ids..] }"}
    valid = _validate_battle_loadout(skills, current_player.mana_cap, player=current_player, enforce_unlocks=True)
    if not valid.get("ok"):
        return {"error": valid.get("error", "Invalid loadout")}
    current_player.battle_skills = list(valid["skills"])
    _apply_battle_defaults(current_player)
    _persist_state()
    return {"ok": True, "state": _battle_loadout_state(current_player)}


@app.get("/battle/presets")
def battle_presets_get():
    _apply_battle_defaults(current_player)
    return {
        "presets": {str(k): list(v) for k, v in dict(current_player.battle_presets or {}).items()},
        "core_presets": sorted(list(CORE_BATTLE_PRESETS.keys())),
    }


@app.post("/battle/presets/save")
def battle_presets_save(payload: dict):
    _apply_battle_defaults(current_player)
    preset_id = _safe_battle_preset_id(str(payload.get("preset", "") or ""))
    if not preset_id:
        return {"error": "Missing preset id"}
    incoming = payload.get("skills", current_player.battle_skills)
    if not isinstance(incoming, list):
        return {"error": "Expected object: { preset: 'name', skills: [...] }"}
    valid = _validate_battle_loadout(incoming, current_player.mana_cap, player=current_player, enforce_unlocks=True)
    if not valid.get("ok"):
        return {"error": valid.get("error", "Invalid loadout for preset")}

    current_player.battle_presets[preset_id] = list(valid["skills"])
    _persist_state()
    return {"ok": True, "preset": preset_id, "state": _battle_loadout_state(current_player)}


@app.post("/battle/presets/apply")
def battle_presets_apply(payload: dict):
    _apply_battle_defaults(current_player)
    preset_id = _safe_battle_preset_id(str(payload.get("preset", "") or ""))
    if not preset_id:
        return {"error": "Missing preset id"}
    skills = list(current_player.battle_presets.get(preset_id, []))
    if len(skills) != 6:
        return {"error": "Unknown preset", "preset": preset_id}
    valid = _validate_battle_loadout(skills, current_player.mana_cap, player=current_player, enforce_unlocks=True)
    if not valid.get("ok"):
        return {"error": valid.get("error", "Preset invalid for current mana cap"), "preset": preset_id}
    current_player.battle_skills = list(valid["skills"])
    _persist_state()
    return {"ok": True, "preset": preset_id, "state": _battle_loadout_state(current_player)}


@app.post("/battle/presets/delete")
def battle_presets_delete(payload: dict):
    _apply_battle_defaults(current_player)
    preset_id = _safe_battle_preset_id(str(payload.get("preset", "") or ""))
    if not preset_id:
        return {"error": "Missing preset id"}
    if preset_id in CORE_BATTLE_PRESETS:
        return {"error": "Core preset cannot be deleted", "preset": preset_id}
    if preset_id not in current_player.battle_presets:
        return {"error": "Unknown preset", "preset": preset_id}
    del current_player.battle_presets[preset_id]
    _persist_state()
    return {"ok": True, "deleted": preset_id, "state": _battle_loadout_state(current_player)}


@app.post("/battle/mana/cap")
def battle_mana_set(payload: dict):
    cap = int(payload.get("mana_cap", current_player.mana_cap) or current_player.mana_cap)
    cap = int(max(8, min(50, cap)))
    old = int(current_player.mana_cap)
    if cap == old:
        return {"ok": True, "mana_cap": cap, "state": _battle_loadout_state(current_player)}

    valid = _validate_battle_loadout(current_player.battle_skills, cap)
    if not valid.get("ok"):
        return {"error": valid.get("error", "Current loadout exceeds new cap"), "current_mana_cap": old}
    current_player.mana_cap = cap
    _persist_state()
    return {"ok": True, "mana_cap": cap, "state": _battle_loadout_state(current_player)}


@app.post("/battle/mana/upgrade")
def battle_mana_upgrade():
    _apply_battle_defaults(current_player)
    min_cap = int(BATTLE_MANA_CONFIG.get("min_cap", 8) or 8)
    max_cap = int(BATTLE_MANA_CONFIG.get("max_cap", 50) or 50)
    cur = int(max(min_cap, min(max_cap, int(current_player.mana_cap or min_cap))))
    if cur >= max_cap:
        return {"error": "Mana cap already at max", "mana_cap": cur}

    cost = _battle_mana_upgrade_cost(cur)
    gold = int(current_player.gold or 0)
    if gold < cost:
        return {"error": "Not enough gold", "required": cost, "gold": gold, "mana_cap": cur}

    current_player.gold = gold - cost
    current_player.mana_cap = cur + 1
    _persist_state()
    return {
        "ok": True,
        "mana_cap": int(current_player.mana_cap),
        "cost": cost,
        "gold": int(current_player.gold),
        "state": _battle_loadout_state(current_player),
    }


@app.post("/battle/tree/upgrade")
def battle_tree_upgrade(payload: dict):
    node = str(payload.get("node", "") or "").strip().lower()
    if node not in BATTLE_TREE_CONFIG:
        return {"error": "Unknown tree node", "available": sorted(list(BATTLE_TREE_CONFIG.keys()))}
    _apply_battle_defaults(current_player)
    row = BATTLE_TREE_CONFIG[node]
    level = int(current_player.battle_tree.get(node, 0) or 0)
    max_level = int(row.get("max_level", 1) or 1)
    if level >= max_level:
        return {"error": "Node at max level", "node": node, "level": level}

    base_cost = int(row.get("base_cost_gold", 500) or 500)
    mult = float(row.get("cost_mult", 1.7) or 1.7)
    cost = int(max(1, round(base_cost * (mult ** level))))
    if int(current_player.gold) < cost:
        return {"error": "Not enough gold", "required": cost, "gold": int(current_player.gold)}

    current_player.gold = int(current_player.gold) - cost
    current_player.battle_tree[node] = level + 1
    _persist_state()
    return {
        "ok": True,
        "node": node,
        "level": int(current_player.battle_tree.get(node, 0) or 0),
        "cost": cost,
        "gold": int(current_player.gold),
        "state": _battle_loadout_state(current_player),
    }


@app.get("/player/stash")
def player_stash():
    return {"stash": get_stash(current_player)}


@app.post("/player/equip")
def equip(stash_index: int):
    return equip_item(current_player, stash_index)


@app.post("/player/unequip")
def unequip(slot: str):
    return unequip_item(current_player, slot)


@app.post("/player/sell")
def sell_item(stash_index: int):
    idx = int(stash_index)
    if idx < 0 or idx >= len(current_player.stash):
        return {"error": "Invalid stash index"}

    item = current_player.stash.pop(idx)
    rarity_mult = {
        "common": 1.0,
        "uncommon": 1.2,
        "rare": 1.4,
        "epic": 2.0,
        "legendary": 3.0,
        "mythic": 4.0,
        "relic": 5.5,
    }
    mult = float(rarity_mult.get(str(item.rarity).lower(), 1.0))
    value = max(5, int((item.power * 9) * mult))
    current_player.gold += value

    return {
        "ok": True,
        "sold": {
            "name": item.name,
            "rarity": item.rarity,
            "slot": item.slot,
            "power": item.power,
            "value": value,
        },
        "gold": current_player.gold,
        "stash_count": len(current_player.stash),
    }


@app.post("/player/dismantle")
def dismantle_item_endpoint(stash_index: int):
    return dismantle_item(current_player, int(stash_index))


@app.post("/player/reroll_affix")
def reroll_item_affix_endpoint(payload: dict):
    stash_index = int(payload.get("stash_index", -1) or -1)
    affix_index = int(payload.get("affix_index", -1) or -1)
    return reroll_item_affix(current_player, stash_index, affix_index=affix_index)


@app.post("/player/reroll_rune_effect")
def reroll_rune_effect_endpoint(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "")
    effect_index = int(payload.get("effect_index", -1) or -1)
    out = reroll_rune_effect(current_player, rune_id, effect_index=effect_index)
    if out.get("ok"):
        _persist_state()
    return out


@app.post("/player/ascend_item")
def ascend_item_endpoint(payload: dict):
    out = ascend_item(current_player, int(payload.get("stash_index", -1) or -1))
    if out.get("ok"):
        _persist_state()
    return out


@app.post("/player/ascend_rune")
def ascend_rune_endpoint(payload: dict):
    out = ascend_rune(current_player, str(payload.get("rune_id", "") or ""))
    if out.get("ok"):
        _persist_state()
    return out


@app.get("/player/wallet")
def player_wallet():
    return {
        "wallet": currency_wallet(current_player),
        "currencies": {cid: dict(meta) for cid, meta in CURRENCIES.items()},
    }


@app.get("/player/chests")
def player_chests():
    return {"chests": dict(current_player.chests)}


@app.post("/chests/open")
def open_chest_endpoint(payload: dict):
    rarity = str(payload.get("rarity", "") or "")
    risk = int(session.SESSION.get("risk", 0) or 0)
    out = open_reward_chest(current_player, rarity, risk=risk, luck_bonus=current_player.loot_luck)
    if out.get("ok"):
        _persist_state()
    return out


@app.post("/player/prestige")
def prestige():
    current_player.prestige_reset()
    _persist_state()
    return {"message": "Prestige successful", "player": current_player, "stash": get_stash(current_player)}


@app.get("/idle/state")
def idle_state():
    return _idle_state_payload(current_player, include_summary=True)


@app.get("/idle/tuning")
def idle_tuning_get():
    return {
        "tuning": dict(IDLE_TUNING),
        "presets": dict(IDLE_TUNING_PRESETS),
        "skills": {
            sid: {
                "name": cfg.get("name", sid.title()),
                "xp_per_hour": cfg.get("xp_per_hour", 0.0),
                "gold_per_hour": cfg.get("gold_per_hour", 0.0),
                "resource_per_hour": cfg.get("resource_per_hour", 0.0),
                "rare_chance_per_min": cfg.get("rare_chance_per_min", 0.0),
            }
            for sid, cfg in IDLE_SKILLS.items()
        },
    }


@app.post("/idle/tuning")
def idle_tuning_set(payload: dict):
    changes = payload.get("tuning", {})
    if not isinstance(changes, dict):
        return {"error": "Expected object: { tuning: {...} }"}

    applied = _apply_idle_tuning_patch(changes)

    if not applied:
        return {"error": "No valid tuning keys provided", "allowed": list(_idle_tuning_allowed_ranges().keys())}

    _persist_state()
    return {"ok": True, "applied": applied, "tuning": dict(IDLE_TUNING)}


@app.post("/idle/tuning/preset")
def idle_tuning_apply_preset(payload: dict):
    preset_id = str(payload.get("preset", "") or "").strip().lower()
    preset = IDLE_TUNING_PRESETS.get(preset_id)
    if not preset:
        return {"error": "Unknown preset", "available": sorted(list(IDLE_TUNING_PRESETS.keys()))}
    applied = _apply_idle_tuning_patch(dict(preset))
    _persist_state()
    return {"ok": True, "preset": preset_id, "applied": applied, "tuning": dict(IDLE_TUNING)}


@app.post("/idle/tuning/preset/save")
def idle_tuning_save_preset(payload: dict):
    preset_id = str(payload.get("preset", "") or "").strip().lower()
    if not preset_id:
        return {"error": "Missing preset id"}
    changes = payload.get("tuning", {})
    if not isinstance(changes, dict):
        return {"error": "Expected object: { preset: 'name', tuning: {...} }"}
    cleaned = _apply_idle_tuning_patch(changes)
    if not cleaned:
        return {"error": "No valid tuning keys in preset", "allowed": list(_idle_tuning_allowed_ranges().keys())}
    IDLE_TUNING_PRESETS[preset_id] = dict(cleaned)
    _persist_state()
    return {"ok": True, "preset": preset_id, "saved": dict(cleaned), "presets": dict(IDLE_TUNING_PRESETS)}


@app.post("/idle/tuning/preset/delete")
def idle_tuning_delete_preset(payload: dict):
    preset_id = str(payload.get("preset", "") or "").strip().lower()
    if not preset_id:
        return {"error": "Missing preset id"}
    if preset_id in CORE_IDLE_TUNING_PRESETS:
        return {"error": "Core preset cannot be deleted", "preset": preset_id}
    if preset_id not in IDLE_TUNING_PRESETS:
        return {"error": "Unknown preset", "available": sorted(list(IDLE_TUNING_PRESETS.keys()))}
    del IDLE_TUNING_PRESETS[preset_id]
    _persist_state()
    return {"ok": True, "deleted": preset_id, "presets": dict(IDLE_TUNING_PRESETS)}


@app.post("/idle/tuning/preset/rename")
def idle_tuning_rename_preset(payload: dict):
    src = str(payload.get("preset", "") or "").strip().lower()
    dst = str(payload.get("new_name", "") or "").strip().lower()
    if not src or not dst:
        return {"error": "Missing preset or new_name"}
    if src not in IDLE_TUNING_PRESETS:
        return {"error": "Unknown preset", "preset": src}
    if src in CORE_IDLE_TUNING_PRESETS:
        return {"error": "Core preset cannot be renamed", "preset": src}
    if dst in IDLE_TUNING_PRESETS:
        return {"error": "Target preset already exists", "preset": dst}
    IDLE_TUNING_PRESETS[dst] = dict(IDLE_TUNING_PRESETS[src])
    del IDLE_TUNING_PRESETS[src]
    _persist_state()
    return {"ok": True, "renamed": {"from": src, "to": dst}, "presets": dict(IDLE_TUNING_PRESETS)}


@app.post("/idle/tuning/skill")
def idle_tuning_skill_set(payload: dict):
    skill = str(payload.get("skill", "") or "").strip().lower()
    if skill not in IDLE_SKILLS:
        return {"error": "Unknown skill", "available": sorted(list(IDLE_SKILLS.keys()))}

    tuning = payload.get("tuning", {})
    if not isinstance(tuning, dict):
        return {"error": "Expected object: { skill: '...', tuning: {...} }"}

    cfg = IDLE_SKILLS[skill]
    applied = _apply_skill_tuning_patch(skill, tuning)

    if not applied:
        return {"error": "No valid skill tuning keys", "allowed": list(_skill_tuning_allowed_ranges().keys())}

    _persist_state()
    return {
        "ok": True,
        "skill": skill,
        "applied": applied,
        "skill_tuning": {
            "xp_per_hour": float(cfg.get("xp_per_hour", 0.0) or 0.0),
            "gold_per_hour": float(cfg.get("gold_per_hour", 0.0) or 0.0),
            "resource_per_hour": float(cfg.get("resource_per_hour", 0.0) or 0.0),
            "rare_chance_per_min": float(cfg.get("rare_chance_per_min", 0.0) or 0.0),
        },
    }


@app.post("/idle/tuning/skill/preset")
def idle_tuning_apply_skill_preset(payload: dict):
    skill = str(payload.get("skill", "") or "").strip().lower()
    if skill not in IDLE_SKILLS:
        return {"error": "Unknown skill", "available": sorted(list(IDLE_SKILLS.keys()))}
    preset_id = str(payload.get("preset", "") or "").strip().lower()
    preset_map = IDLE_SKILL_TUNING_PRESETS.setdefault(skill, {})
    preset = preset_map.get(preset_id)
    if not preset:
        return {"error": "Unknown skill preset", "available": sorted(list(preset_map.keys()))}
    applied = _apply_skill_tuning_patch(skill, dict(preset))
    _persist_state()
    return {
        "ok": True,
        "skill": skill,
        "preset": preset_id,
        "applied": applied,
        "skill_tuning": {
            "xp_per_hour": float(IDLE_SKILLS[skill].get("xp_per_hour", 0.0) or 0.0),
            "gold_per_hour": float(IDLE_SKILLS[skill].get("gold_per_hour", 0.0) or 0.0),
            "resource_per_hour": float(IDLE_SKILLS[skill].get("resource_per_hour", 0.0) or 0.0),
            "rare_chance_per_min": float(IDLE_SKILLS[skill].get("rare_chance_per_min", 0.0) or 0.0),
        },
    }


@app.post("/idle/tuning/skill/preset/save")
def idle_tuning_save_skill_preset(payload: dict):
    skill = str(payload.get("skill", "") or "").strip().lower()
    if skill not in IDLE_SKILLS:
        return {"error": "Unknown skill", "available": sorted(list(IDLE_SKILLS.keys()))}
    preset_id = str(payload.get("preset", "") or "").strip().lower()
    if not preset_id:
        return {"error": "Missing preset id"}
    tuning = payload.get("tuning", {})
    if not isinstance(tuning, dict):
        return {"error": "Expected object: { skill: '...', preset: '...', tuning: {...} }"}
    cleaned = _apply_skill_tuning_patch(skill, tuning)
    if not cleaned:
        return {"error": "No valid skill tuning keys", "allowed": list(_skill_tuning_allowed_ranges().keys())}
    preset_map = IDLE_SKILL_TUNING_PRESETS.setdefault(skill, {})
    preset_map[preset_id] = dict(cleaned)
    _persist_state()
    return {"ok": True, "skill": skill, "preset": preset_id, "saved": dict(cleaned), "presets": dict(preset_map)}


@app.post("/idle/tuning/skill/preset/delete")
def idle_tuning_delete_skill_preset(payload: dict):
    skill = str(payload.get("skill", "") or "").strip().lower()
    if skill not in IDLE_SKILLS:
        return {"error": "Unknown skill", "available": sorted(list(IDLE_SKILLS.keys()))}
    preset_id = str(payload.get("preset", "") or "").strip().lower()
    if not preset_id:
        return {"error": "Missing preset id"}
    preset_map = IDLE_SKILL_TUNING_PRESETS.setdefault(skill, {})
    if preset_id not in preset_map:
        return {"error": "Unknown skill preset", "available": sorted(list(preset_map.keys()))}
    del preset_map[preset_id]
    _persist_state()
    return {"ok": True, "skill": skill, "deleted": preset_id, "presets": dict(preset_map)}


@app.post("/idle/tuning/skill/preset/rename")
def idle_tuning_rename_skill_preset(payload: dict):
    skill = str(payload.get("skill", "") or "").strip().lower()
    if skill not in IDLE_SKILLS:
        return {"error": "Unknown skill", "available": sorted(list(IDLE_SKILLS.keys()))}
    src = str(payload.get("preset", "") or "").strip().lower()
    dst = str(payload.get("new_name", "") or "").strip().lower()
    if not src or not dst:
        return {"error": "Missing preset or new_name"}
    preset_map = IDLE_SKILL_TUNING_PRESETS.setdefault(skill, {})
    if src not in preset_map:
        return {"error": "Unknown skill preset", "preset": src}
    if dst in preset_map:
        return {"error": "Target skill preset already exists", "preset": dst}
    preset_map[dst] = dict(preset_map[src])
    del preset_map[src]
    _persist_state()
    return {"ok": True, "skill": skill, "renamed": {"from": src, "to": dst}, "presets": dict(preset_map)}


@app.post("/idle/start")
def idle_start(payload: dict):
    skill = str(payload.get("skill", "") or "").strip().lower()
    if skill not in IDLE_SKILLS:
        return {"error": "Unknown idle skill", "available": sorted(list(IDLE_SKILLS.keys()))}

    now = _now_ts()
    _apply_idle_progress(current_player, now)
    activity = dict(current_player.idle_activity or {})
    started_at = float(activity.get("started_at", 0.0) or 0.0)
    active_skill = str(activity.get("skill", "") or "").strip().lower()

    if active_skill != skill:
        started_at = now

    current_player.idle_activity = {
        "skill": skill,
        "started_at": started_at or now,
        "last_tick_at": now,
    }
    _event_log_add("idle", "Idle started", IDLE_SKILLS[skill]["name"], meta={"skill": skill})
    _persist_state()
    return {
        "ok": True,
        "message": f"Idle activity started: {IDLE_SKILLS[skill]['name']}",
        "state": _idle_state_payload(current_player, include_summary=True),
    }


@app.post("/idle/stop")
def idle_stop():
    now = _now_ts()
    summary = _apply_idle_progress(current_player, now)
    current_player.idle_activity = {"skill": "", "started_at": 0.0, "last_tick_at": 0.0}
    if summary:
        _event_log_add(
            "idle",
            "Idle stopped",
            f"+{int(summary.get('xp_gained', 0) or 0)} XP, +{int(summary.get('gold_gained', 0) or 0)} gold",
            meta={"skill": str(summary.get("skill", "") or ""), "summary": summary},
        )
    else:
        _event_log_add("idle", "Idle stopped", "No progress recorded")
    _persist_state()
    return {
        "ok": True,
        "message": "Idle activity stopped",
        "summary": summary,
        "state": _idle_state_payload(current_player, include_summary=True),
    }


@app.post("/idle/upgrade")
def idle_upgrade(payload: dict):
    upgrade_id = str(payload.get("upgrade", "") or "").strip().lower()
    cfg = IDLE_UPGRADE_CONFIG.get(upgrade_id)
    if not cfg:
        return {"error": "Unknown upgrade", "available": sorted(list(IDLE_UPGRADE_CONFIG.keys()))}

    level = int(current_player.idle_upgrades.get(upgrade_id, 0) or 0)
    max_level = int(cfg.get("max_level", 1) or 1)
    if level >= max_level:
        return {"error": "Upgrade is already maxed", "upgrade": upgrade_id, "level": level, "max_level": max_level}

    cost = int(float(cfg.get("base_cost_gold", 1000) or 1000) * (float(cfg.get("cost_mult", 1.5) or 1.5) ** level))
    if current_player.gold < cost:
        return {"error": "Not enough gold", "required": cost, "gold": current_player.gold}

    current_player.gold -= cost
    current_player.idle_upgrades[upgrade_id] = level + 1
    _event_log_add(
        "idle",
        "Idle upgrade purchased",
        f"{upgrade_id} -> Lv {current_player.idle_upgrades[upgrade_id]}",
        meta={"upgrade": upgrade_id, "level": current_player.idle_upgrades[upgrade_id], "cost": cost},
    )
    _persist_state()
    return {
        "ok": True,
        "upgrade": upgrade_id,
        "new_level": current_player.idle_upgrades[upgrade_id],
        "cost": cost,
        "gold": current_player.gold,
        "state": _idle_state_payload(current_player, include_summary=True),
    }


@app.post("/idle/boost/use")
def idle_boost_use(payload: dict):
    boost_id = str(payload.get("boost", "") or "").strip().lower()
    cfg = IDLE_BOOST_CONFIG.get(boost_id)
    if not cfg:
        return {"error": "Unknown boost", "available": sorted(list(IDLE_BOOST_CONFIG.keys()))}

    consume_resource = str(cfg.get("consume_resource", "") or "")
    cost_gold = int(cfg.get("cost_gold", 0) or 0)
    if cost_gold > 0 and current_player.gold < cost_gold:
        return {"error": "Not enough gold", "required": cost_gold, "gold": current_player.gold}
    if consume_resource:
        cur = int(current_player.resources.get(consume_resource, 0) or 0)
        if cur <= 0:
            return {"error": "Missing required boost resource", "resource": consume_resource}

    _apply_idle_progress(current_player, _now_ts())
    if cost_gold > 0:
        current_player.gold -= cost_gold
    if consume_resource:
        current_player.resources[consume_resource] = int(current_player.resources.get(consume_resource, 0) or 0) - 1

    now = _now_ts()
    boost = {
        "id": boost_id,
        "name": str(cfg.get("name", boost_id)),
        "mult": float(cfg.get("mult", 1.0) or 1.0),
        "expires_at": now + float(cfg.get("duration_sec", 3600) or 3600),
    }
    current_player.idle_boosts.append(boost)
    _event_log_add("idle", "Idle boost used", f"{boost.get('name', boost_id)} active", meta={"boost": boost})
    _persist_state()
    return {
        "ok": True,
        "boost": boost,
        "gold": current_player.gold,
        "resources": current_player.resources,
        "state": _idle_state_payload(current_player, include_summary=True),
    }


@app.post("/idle/summary/claim")
def idle_summary_claim():
    _apply_idle_progress(current_player, _now_ts())
    summary = dict(current_player.idle_last_summary or {})
    current_player.idle_last_summary = {}
    if summary:
        _event_log_add(
            "idle",
            "Offline rewards claimed",
            f"{summary.get('skill_name', summary.get('skill', 'Idle'))}: +{int(summary.get('xp_gained', 0) or 0)} XP",
            meta={"summary": summary},
        )
    _persist_state()
    return {"ok": True, "summary": summary, "state": _idle_state_payload(current_player, include_summary=True)}


@app.get("/runecrafting/state")
def runecrafting_state():
    recipes = []
    for key, data in RUNE_RECIPES.items():
        recipes.append({
            "id": key,
            "name": data["name"],
            "essence_cost": data["essence_cost"],
            "base_yield": data["base_yield"],
            "xp": data["xp"],
            "unlock": data["unlock"],
            "owned": int(current_player.runes.get(key, 0) or 0),
            "unlocked": current_player.runecrafting_level >= int(data["unlock"]),
        })

    return {
        "level": current_player.runecrafting_level,
        "xp": current_player.runecrafting_xp,
        "xp_to_next": current_player.runecrafting_xp_to_next,
        "essence": int(current_player.resources.get("rune_essence", 0) or 0),
        "runes": current_player.runes,
        "recipes": recipes,
        "gold": current_player.gold,
        "crafted_supplies": int(current_player.resources.get("crafted_supplies", 0) or 0),
        "amplifier_recipes": [
            {
                "id": key,
                "name": r["name"],
                "tier": r["tier"],
                "cost_supplies": r["cost_supplies"],
                "cost_gold": r["cost_gold"],
                "amp_bonus": r["amp_bonus"],
                "unlock": r["unlock"],
                "xp": r["xp"],
                "unlocked": current_player.runecrafting_level >= int(r["unlock"]),
                "owned": sum(
                    1 for x in current_player.rune_items
                    if is_amplifier(x) and str(x.get("recipe", "")) == key
                ),
            }
            for key, r in AMPLIFIER_RECIPES.items()
        ],
    }


@app.post("/runecrafting/craft")
def runecrafting_craft(payload: dict):
    rune_id = str(payload.get("rune", "") or "").strip().lower()
    times = max(1, min(100, int(payload.get("times", 1) or 1)))

    recipe = RUNE_RECIPES.get(rune_id)
    if not recipe:
        return {"error": f"Unknown rune '{rune_id}'", "available": list(RUNE_RECIPES.keys())}

    unlock = int(recipe.get("unlock", 1))
    if current_player.runecrafting_level < unlock:
        return {
            "error": "Rune is locked",
            "required_level": unlock,
            "current_level": current_player.runecrafting_level,
        }

    cost_each = int(recipe.get("essence_cost", 1) or 1)
    total_cost = cost_each * times
    essence = int(current_player.resources.get("rune_essence", 0) or 0)
    if essence < total_cost:
        return {
            "error": "Not enough rune essence",
            "required": total_cost,
            "current": essence,
        }

    current_player.spend_resource("rune_essence", total_cost)

    lo, hi = recipe.get("base_yield", (1, 1))
    int_bonus = max(0, (current_player.intelligence - 5) // 5)
    luck_bonus = 1 if random.random() < current_player.loot_luck else 0

    crafted_total = 0
    for _ in range(times):
        crafted_total += random.randint(int(lo), int(hi)) + int_bonus + luck_bonus

    current_player.add_rune(rune_id, crafted_total)
    gained_xp = int(recipe.get("xp", 1)) * times
    current_player.gain_runecrafting_xp(gained_xp)

    return {
        "ok": True,
        "crafted": {
            "rune": rune_id,
            "name": recipe["name"],
            "amount": crafted_total,
            "times": times,
            "essence_spent": total_cost,
            "xp": gained_xp,
        },
        "state": runecrafting_state(),
    }


@app.post("/runecrafting/craft_amplifier")
def runecrafting_craft_amplifier(payload: dict):
    recipe_id = str(payload.get("recipe", "") or "").strip().lower()
    recipe = AMPLIFIER_RECIPES.get(recipe_id)
    if not recipe:
        return {"error": f"Unknown amplifier '{recipe_id}'", "available": list(AMPLIFIER_RECIPES.keys())}

    unlock = int(recipe.get("unlock", 1))
    if current_player.runecrafting_level < unlock:
        return {
            "error": "Amplifier is locked",
            "required_level": unlock,
            "current_level": current_player.runecrafting_level,
        }

    supplies = int(current_player.resources.get("crafted_supplies", 0) or 0)
    if supplies < int(recipe["cost_supplies"]):
        return {"error": "Not enough crafted supplies", "required": int(recipe["cost_supplies"]), "current": supplies}

    if current_player.gold < int(recipe["cost_gold"]):
        return {"error": "Not enough gold", "required": int(recipe["cost_gold"]), "current": current_player.gold}

    current_player.spend_resource("crafted_supplies", int(recipe["cost_supplies"]))
    current_player.gold -= int(recipe["cost_gold"])
    crafted = generate_amplifier_rune(recipe_id)
    current_player.rune_items.append(crafted)
    current_player.gain_runecrafting_xp(int(recipe["xp"]))

    return {
        "ok": True,
        "crafted": crafted,
        "state": runecrafting_state(),
    }


@app.get("/slayer/state")
def slayer_state():
    return {
        "level": current_player.slayer_level,
        "xp": current_player.slayer_xp,
        "xp_to_next": current_player.slayer_xp_to_next,
        "task": current_player.slayer_task,
        "targets": SLAYER_TARGETS,
    }


@app.post("/slayer/new_task")
def slayer_new_task():
    unlocked = [t for t in SLAYER_TARGETS if current_player.slayer_level >= int(t["unlock"])]
    if not unlocked:
        unlocked = [SLAYER_TARGETS[0]]

    target = random.choice(unlocked)
    kills = random.randint(int(target["min_kills"]), int(target["max_kills"]))
    current_player.slayer_task = {
        "target": target["id"],
        "target_label": target["label"],
        "remaining": kills,
        "total": kills,
        "tier": "normal",
    }
    return {"ok": True, "task": current_player.slayer_task}


@app.post("/slayer/extend_task")
def slayer_extend_task(extra: int = 10):
    task = current_player.slayer_task or {}
    if int(task.get("remaining", 0) or 0) <= 0:
        return {"error": "No active task"}
    add = max(5, min(30, int(extra)))
    task["remaining"] = int(task.get("remaining", 0) or 0) + add
    task["total"] = int(task.get("total", 0) or 0) + add
    current_player.slayer_task = task
    return {"ok": True, "task": current_player.slayer_task}


@app.get("/prayer/state")
def prayer_state():
    return {
        "active": current_player.active_prayer,
        "book": PRAYER_BOOK,
        "runes": current_player.runes,
    }


@app.post("/prayer/activate")
def prayer_activate(payload: dict):
    prayer_id = str(payload.get("prayer", "") or "").strip().lower()
    if prayer_id == "":
        current_player.active_prayer = ""
        return {"ok": True, "active": ""}

    prayer = PRAYER_BOOK.get(prayer_id)
    if not prayer:
        return {"error": f"Unknown prayer '{prayer_id}'"}

    required = int(prayer.get("unlock", 1) or 1)
    if current_player.level < required:
        return {"error": "Prayer locked", "required_level": required, "current_level": current_player.level}

    current_player.active_prayer = prayer_id
    return {"ok": True, "active": prayer_id}


def _rune_slot_capacity(player: Player) -> int:
    return int(rune_slot_capacity(player))


def _sync_rune_loadout(player: Player):
    sync_rune_loadout(player)


def _roll_rune_rarity(luck_bonus: float = 0.0) -> str:
    return roll_rune_rarity(luck_bonus)


def _generate_rune_effects(rarity: str) -> list[dict]:
    return generate_rune_effects(rarity)


def _generate_build_rune(player: Player, rarity_override: str | None = None) -> dict:
    return generate_build_rune(player, rarity_override=rarity_override)



def _find_rune(player: Player, rune_id: str) -> dict | None:
    return find_rune(player, rune_id)


def _remove_rune_by_id(player: Player, rune_id: str) -> dict | None:
    return remove_rune_by_id(player, rune_id)


def _rune_sale_value(rune: dict) -> int:
    return rune_sale_value(rune)


def _rune_dismantle_value(rune: dict) -> dict:
    return rune_dismantle_value(rune)


def _rune_upgrade_cost(rarity: str, level: int) -> int:
    return rune_upgrade_cost(rarity, level)


def _rune_relic_infuse_cap(rarity: str) -> int:
    return rune_relic_infuse_cap(rarity)


def _rune_relic_infuse_scale(rarity: str) -> float:
    rarity = str(rarity or "common").lower()
    if rarity == "relic":
        return 1.10
    if rarity == "supreme":
        return 1.09
    if rarity == "mythic":
        return 1.08
    if rarity == "legendary":
        return 1.07
    return 1.06


def _collect_rune_mods(player: Player) -> dict:
    return collect_rune_mods(player)


@app.get("/runes/state")
def rune_state():
    _sync_rune_loadout(current_player)
    summary = loadout_summary(current_player)
    return {
        "slots": {
            "capacity": summary["capacity"],
            "budget": summary["budget"],
            "total_value": summary["total_value"],
            "bonus_active": summary["bonus_active"],
            "bonus_effect": summary["bonus_effect"],
            "equipped": current_player.rune_loadout,
        },
        "chests": int(current_player.resources.get("arcane_chest", 0) or 0),
        "relics": int(current_player.resources.get("rune_relic", 0) or 0),
        "inventory": current_player.rune_items,
        "mods": _collect_rune_mods(current_player),
        "rarities": RUNE_BUILD_RARITIES,
        "loadout_summary": summary,
        "amplifier": {
            "equipped": equipped_amplifier(current_player),
            "bonus": amplifier_bonus(current_player),
            "cap": AMPLIFIER_BONUS_CAP,
            "owned": [r for r in current_player.rune_items if is_amplifier(r)],
        },
    }


@app.post("/runes/open_chest")
def rune_open_chest(payload: dict):
    count = max(1, min(50, int(payload.get("count", 1) or 1)))
    chests = int(current_player.resources.get("arcane_chest", 0) or 0)
    if chests < count:
        return {"error": "Not enough chests", "required": count, "current": chests}

    # Warden's Key upgrade mode: one key per chest shifts the roll one tier up.
    use_keys = str(payload.get("key_mode", "") or "") == "upgrade"
    if use_keys and currency_balance(current_player, "warden_key") < count:
        return {
            "error": "Not enough warden_key",
            "required": count,
            "current": currency_balance(current_player, "warden_key"),
        }

    current_player.resources["arcane_chest"] = chests - count
    if use_keys:
        spend_currency(current_player, "warden_key", count)
    created = []
    relic_found = 0
    for _ in range(count):
        if use_keys:
            rolled = _roll_rune_rarity(current_player.loot_luck)
            r = _generate_build_rune(current_player, rarity_override=chest_key_upgrade_tier(rolled))
        else:
            r = _generate_build_rune(current_player)
        current_player.rune_items.append(r)
        created.append(r)

        rarity = str(r.get("rarity", "common") or "common").lower()
        # Tiny relic trickle from chest rolls; high rarity rolls can spike it.
        if rarity == "relic":
            relic_found += random.randint(2, 4)
        elif rarity == "supreme" and random.random() < 0.35:
            relic_found += 1
        elif rarity == "mythic" and random.random() < 0.15:
            relic_found += 1
        elif random.random() < 0.02:
            relic_found += 1

    if relic_found > 0:
        current_player.add_resource("rune_relic", relic_found)

    return {
        "ok": True,
        "opened": count,
        "keys_used": count if use_keys else 0,
        "runes": created,
        "relic_found": relic_found,
        "state": rune_state(),
    }


@app.post("/runes/equip")
def rune_equip(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "")
    slot = int(payload.get("slot", 0) or 0)
    _sync_rune_loadout(current_player)
    cap = _rune_slot_capacity(current_player)
    if slot < 0 or slot >= cap:
        return {"error": "Invalid slot", "capacity": cap}

    ids = {str(r.get("id", "")) for r in current_player.rune_items}
    if rune_id not in ids:
        return {"error": "Rune not found"}

    target = _find_rune(current_player, rune_id)
    if isinstance(target, dict) and is_amplifier(target):
        return {"error": "Amplifier runes don't use rune slots. Use /runes/amplifier_equip."}

    previous = list(current_player.rune_loadout)
    current_player.rune_loadout = [None if x == rune_id else x for x in current_player.rune_loadout]
    current_player.rune_loadout[slot] = rune_id
    validation = validate_rune_loadout(current_player)
    if not validation.get("ok", False):
        current_player.rune_loadout = previous
        return {
            "error": validation.get("error", "Loadout exceeds budget"),
            "capacity": cap,
            "budget": loadout_summary(current_player)["budget"],
            "total_value": loadout_summary(current_player)["total_value"],
        }
    return {"ok": True, "state": rune_state(), "loadout": loadout_summary(current_player)}


@app.post("/runes/unequip")
def rune_unequip(payload: dict):
    slot = int(payload.get("slot", 0) or 0)
    _sync_rune_loadout(current_player)
    cap = _rune_slot_capacity(current_player)
    if slot < 0 or slot >= cap:
        return {"error": "Invalid slot", "capacity": cap}
    current_player.rune_loadout[slot] = None
    return {"ok": True, "state": rune_state()}


@app.post("/runes/amplifier_equip")
def rune_amplifier_equip(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "").strip()
    if not rune_id:
        return {"error": "Missing rune_id"}

    target = _find_rune(current_player, rune_id)
    if not isinstance(target, dict):
        return {"error": "Rune not found"}
    if not is_amplifier(target):
        return {"error": "Not an amplifier rune"}

    set_equipped_amplifier(current_player, rune_id)
    return {"ok": True, "equipped": target, "state": rune_state()}


@app.post("/runes/amplifier_unequip")
def rune_amplifier_unequip(payload: dict):
    set_equipped_amplifier(current_player, None)
    return {"ok": True, "state": rune_state()}


@app.post("/runes/combine_by_rarity")
def rune_combine_by_rarity(payload: dict):
    rarity = str(payload.get("rarity", "") or "").lower().strip()
    nxt = RUNE_NEXT_RARITY.get(rarity)
    if not nxt:
        return {"error": f"Cannot combine rarity '{rarity}'"}

    pool = [r for r in current_player.rune_items if str(r.get("rarity", "")).lower() == rarity and not is_amplifier(r)]
    if len(pool) < 4:
        return {"error": "Need at least 4 runes of same rarity", "have": len(pool)}

    consume_ids = [str(r.get("id")) for r in pool[:4]]
    current_player.rune_items = [r for r in current_player.rune_items if str(r.get("id")) not in consume_ids]

    target_rarity = nxt
    bonus_chance = float(RUNE_COMBINE_BONUS_CHANCE.get(rarity, 0.0) or 0.0)
    bonus_proc = False
    extra = RUNE_NEXT_RARITY.get(nxt)
    if extra and random.random() < bonus_chance:
        target_rarity = extra
        bonus_proc = True

    new_rune = _generate_build_rune(current_player)
    new_rune["rarity"] = target_rarity
    new_rune["effects"] = _generate_rune_effects(target_rarity)
    new_rune["name"] = f"Ascended {new_rune['name']}"
    new_rune["source"] = "combine"
    current_player.rune_items.append(new_rune)

    _sync_rune_loadout(current_player)
    return {
        "ok": True,
        "consumed_ids": consume_ids,
        "created": new_rune,
        "bonus_tier": bonus_proc,
        "bonus_chance": round(bonus_chance, 4),
        "state": rune_state(),
    }


@app.post("/runes/upgrade")
def rune_upgrade(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "").strip()
    if not rune_id:
        return {"error": "Missing rune_id"}

    target = _find_rune(current_player, rune_id)
    if not isinstance(target, dict):
        return {"error": "Rune not found"}
    if is_amplifier(target):
        return {"error": "Amplifier runes cannot be upgraded"}

    rarity = str(target.get("rarity", "common") or "common").lower()
    lvl = int(target.get("upgrade_level", 0) or 0)
    max_lvl = int(target.get("max_upgrade", RUNE_UPGRADE_MAX.get(rarity, 5)) or RUNE_UPGRADE_MAX.get(rarity, 5))
    if lvl >= max_lvl:
        return {"error": "Rune already max level", "level": lvl, "max": max_lvl}

    cost = _rune_upgrade_cost(rarity, lvl)
    relics = int(current_player.resources.get("rune_relic", 0) or 0)
    if relics < cost:
        return {"error": "Not enough rune relics", "required": cost, "current": relics}

    current_player.resources["rune_relic"] = relics - cost
    target["upgrade_level"] = lvl + 1
    target["max_upgrade"] = max_lvl

    # Base upgrade scaling: each level increases each effect by 12%.
    updated = []
    for eff in (target.get("effects", []) or []):
        et = str(eff.get("type", "") or "")
        ev = float(eff.get("value", 0.0) or 0.0)
        nv = round(ev * 1.12, 4)
        updated.append({"type": et, "value": nv})
    target["effects"] = updated

    return {
        "ok": True,
        "upgraded": {
            "id": rune_id,
            "name": target.get("name", "Rune"),
            "rarity": rarity,
            "level": target["upgrade_level"],
            "max": max_lvl,
            "cost": cost,
        },
        "state": rune_state(),
    }


@app.post("/runes/relic_infuse")
def rune_relic_infuse(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "").strip()
    if not rune_id:
        return {"error": "Missing rune_id"}

    target = _find_rune(current_player, rune_id)
    if not isinstance(target, dict):
        return {"error": "Rune not found"}
    if is_amplifier(target):
        return {"error": "Amplifier runes cannot be relic-infused"}

    rarity = str(target.get("rarity", "common") or "common").lower()
    cap = _rune_relic_infuse_cap(rarity)
    if cap <= 0:
        return {"error": "This rune rarity cannot be relic-infused", "rarity": rarity}

    infusions = int(target.get("relic_infusions", 0) or 0)
    if infusions >= cap:
        return {"error": "Relic infusion cap reached", "current": infusions, "cap": cap}

    relics = int(current_player.resources.get("rune_relic", 0) or 0)
    if relics < 1:
        return {"error": "Not enough rune relics", "required": 1, "current": relics}

    current_player.resources["rune_relic"] = relics - 1
    target["relic_infusions"] = infusions + 1

    scale = _rune_relic_infuse_scale(rarity)
    updated = []
    for eff in (target.get("effects", []) or []):
        et = str(eff.get("type", "") or "")
        ev = float(eff.get("value", 0.0) or 0.0)
        nv = round(ev * scale, 4)
        updated.append({"type": et, "value": nv})
    target["effects"] = updated

    return {
        "ok": True,
        "infused": {
            "id": rune_id,
            "name": target.get("name", "Rune"),
            "rarity": rarity,
            "infusions": target["relic_infusions"],
            "cap": cap,
            "cost": 1,
            "scale": scale,
        },
        "state": rune_state(),
    }


@app.post("/runes/sell")
def rune_sell(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "").strip()
    if not rune_id:
        return {"error": "Missing rune_id"}

    target = _find_rune(current_player, rune_id)
    if not isinstance(target, dict):
        return {"error": "Rune not found"}

    if is_amplifier(target):
        value = int(AMPLIFIER_SELL_VALUE.get(int(target.get("tier", 1) or 1), 200))
    else:
        value = _rune_sale_value(target)
    removed = _remove_rune_by_id(current_player, rune_id)
    if not removed:
        return {"error": "Rune not found"}

    current_player.gold += value
    return {
        "ok": True,
        "sold": {
            "id": rune_id,
            "name": removed.get("name", "Rune"),
            "rarity": removed.get("rarity", "common"),
            "value": value,
        },
        "gold": current_player.gold,
        "state": rune_state(),
    }


@app.post("/runes/dismantle")
def rune_dismantle(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "").strip()
    if not rune_id:
        return {"error": "Missing rune_id"}

    target = _find_rune(current_player, rune_id)
    if not isinstance(target, dict):
        return {"error": "Rune not found"}
    if is_amplifier(target):
        return {"error": "Amplifier runes cannot be dismantled. Sell them instead."}

    yields = _rune_dismantle_value(target)
    removed = _remove_rune_by_id(current_player, rune_id)
    if not removed:
        return {"error": "Rune not found"}

    crafted_gain = int(yields.get("relic", 0) or 0) + int(yields.get("essence", 0) or 0)
    current_player.add_resource("crafted_supplies", crafted_gain)
    current_player.add_resource("rune_relic", int(yields.get("relic", 0) or 0))
    current_player.add_resource("rune_essence", int(yields.get("essence", 0) or 0))
    return {
        "ok": True,
        "dismantled": {
            "id": rune_id,
            "name": removed.get("name", "Rune"),
            "rarity": removed.get("rarity", "common"),
            "crafted_supplies_gain": crafted_gain,
            "relic_gain": int(yields.get("relic", 0) or 0),
            "essence_gain": int(yields.get("essence", 0) or 0),
        },
        "state": rune_state(),
    }


# -------------------------
# Dungeon - INTERACTIVE MODE
# -------------------------
@app.post("/dungeon/start")
def dungeon_start(risk: int = 0):
    risk = max(0, min(int(risk), 5))
    payload = start_interactive_dungeon(current_player, risk=risk)
    mod_count = 0 if risk <= 1 else (1 if risk <= 3 else 2)
    modifiers = random.sample(RUN_MODIFIERS, k=min(mod_count, len(RUN_MODIFIERS)))
    cadence_ids = ["opener", "payout_pivot", "pressure_room", "pre_boss", "boss_finish"]
    for idx, room in enumerate(list(payload.get("rooms", []) or [])):
        room_type = str(room.get("type", "") or "").lower()
        if room_type:
            _mark_mechanic_learned(f"room_type:{room_type}", f"Room Type {room_type.replace('_', ' ').title()}", f"Encountered a {room_type.replace('_', ' ')} room in the dungeon route.")
        if idx < len(cadence_ids):
            cid = cadence_ids[idx]
            _mark_mechanic_learned(f"cadence:{cid}", f"Route Cadence {cid.replace('_', ' ').title()}", f"Observed the {cid.replace('_', ' ')} role in a live dungeon path.")
    for mod in modifiers:
        mod_id = str(mod.get("id", "") or "").lower()
        mod_name = str(mod.get("name", mod_id) or mod_id)
        mod_desc = str(mod.get("desc", "") or "")
        if mod_id:
            _mark_mechanic_learned(f"run_modifier:{mod_id}", f"Run Modifier {mod_name}", mod_desc)
    session.start_session(depth=payload["depth"], risk=risk, rooms=payload["rooms"], modifiers=modifiers, player=current_player)
    _event_log_add(
        "dungeon",
        "Dungeon started",
        f"Risk {risk} | Depth {payload.get('depth', 1)}",
        meta={"risk": risk, "depth": int(payload.get("depth", 1) or 1)},
    )
    return _resolve_non_combat_rooms()


@app.get("/dungeon/state")
def dungeon_state():
    return session.state(current_player)


@app.post("/dungeon/leave")
def dungeon_leave():
    if not session.SESSION.get("active", False):
        return {"error": "No active dungeon"}
    if not session.SESSION.get("can_leave", False):
        return {"error": "Cannot leave yet. Defeat the boss first.", "state": session.state(current_player)}
    _event_log_add("dungeon", "Dungeon exited", "Rewards locked. Run finished.")
    return _finalize_dungeon_clear(combat_payload=None, boss_defeated=True)


def _finalize_dungeon_clear(combat_payload: dict | None = None, boss_defeated: bool = False):
    prior_clears = int(dict(getattr(current_player, "progress_counters", {}) or {}).get("dungeons_cleared", 0.0) or 0)
    result = complete_interactive_dungeon(
        current_player,
        risk=session.SESSION["risk"],
        boss_defeated=boss_defeated,
    )
    starter_bonus = None
    if boss_defeated and prior_clears <= 0:
        starter_bonus = {
            "gold": 250,
            "arcane_chest": 1,
            "idle_tonic": 1,
            "rune_essence": 40,
        }
        current_player.gold += int(starter_bonus["gold"])
        current_player.add_resource("arcane_chest", int(starter_bonus["arcane_chest"]))
        current_player.add_resource("idle_tonic", int(starter_bonus["idle_tonic"]))
        current_player.add_resource("rune_essence", int(starter_bonus["rune_essence"]))
        _event_log_add(
            "dungeon",
            "Starter cache claimed",
            "First clear bonus: 250 gold, 1 chest, 1 tonic, 40 essence.",
            severity="success",
            meta={"starter_bonus": True},
        )
        result["starter_bonus"] = dict(starter_bonus)
    combat_state = session.state(current_player)
    session.reset_session()
    _counter_add("dungeons_cleared", 1.0)
    _event_log_add(
        "dungeon",
        "Dungeon cleared",
        f"Boss defeated. Next depth {result.get('next_depth', '-')}",
        meta={
            "boss_defeated": bool(boss_defeated),
            "next_depth": int(result.get("next_depth", 1) or 1),
            "loot_count": len(list(result.get("loot", []) or [])),
        },
    )
    return {"cleared": True, "result": result, "combat": combat_payload, "state": combat_state, "starter_bonus": starter_bonus}


def _current_support_scaling() -> dict:
    room_index = int(session.SESSION.get("room_index", 0) or 0)
    room_count = max(1, int(len(session.SESSION.get("rooms", []) or []) or 1))
    risk = int(session.SESSION.get("risk", 0) or 0)
    depth = int(session.SESSION.get("depth", 1) or 1)
    progress = min(1.0, max(0.0, room_index / room_count))
    intensity = min(0.45, round((progress * 0.28) + (max(0, risk) * 0.025) + (max(0, depth - 1) * 0.006), 3))
    return {
        "progress": round(progress, 3),
        "intensity": intensity,
        "flat_bonus": int(max(0, round(2 + (progress * 8) + (risk * 1.5)))),
        "multiplier": round(1.0 + intensity, 3),
        "late_room": progress >= 0.55,
        "pre_boss": room_index >= max(0, room_count - 2),
    }


def _resolve_non_combat_rooms():
    room_events = []
    while session.SESSION.get("active", False):
        room_type = session.current_room_type()
        enemy = session.current_enemy()
        if room_type is None:
            state = session.state(current_player)
            if session.SESSION.get("can_leave", False):
                state["boss_exit_ready"] = True
                if room_events:
                    state["room_events"] = room_events
                return state
            state["error"] = "Dungeon cannot be completed until boss is defeated."
            if room_events:
                state["room_events"] = room_events
            return state
        if enemy is not None:
            break

        event_payload = {"room_type": room_type}
        if room_type:
            _mark_mechanic_learned(f"room_type:{str(room_type).lower()}", f"Room Type {str(room_type).replace('_', ' ').title()}", f"Resolved a {str(room_type).replace('_', ' ')} room.")
        support_scale = _current_support_scaling()
        scale_mult = float(support_scale.get("multiplier", 1.0) or 1.0)
        scale_flat = int(support_scale.get("flat_bonus", 0) or 0)
        scale_tag = "pre_boss" if support_scale.get("pre_boss") else ("late" if support_scale.get("late_room") else "early")
        event_payload["support_scale"] = {
            "tier": scale_tag,
            "multiplier": scale_mult,
        }
        if room_type == "rest":
            max_hp = float(current_player.max_hp)
            max_stamina = float(current_player.max_stamina)
            heal_amount = int(max(10, ((max_hp * 0.18) + (session.SESSION["risk"] * 2) + scale_flat) * scale_mult))
            stamina_amount = int(max(20, ((max_stamina * 0.35) + scale_flat) * scale_mult))

            hp_before = float(current_player.hp)
            st_before = float(current_player.stamina)
            current_player.hp = min(max_hp, hp_before + heal_amount)
            current_player.stamina = min(max_stamina, st_before + stamina_amount)

            healed = round(float(current_player.hp) - hp_before, 2)
            stamina = round(float(current_player.stamina) - st_before, 2)
            rest_roll = random.random()
            if rest_roll < 0.28:
                _mark_mechanic_learned("support_rest:camp_cache", "Rest Camp Cache", "Rest rooms can grant an idle tonic and late-run gold.")
                current_player.add_resource("idle_tonic", 1)
                bonus_gold = int(round((8 + scale_flat) * scale_mult)) if support_scale.get("pre_boss") else 0
                if bonus_gold > 0:
                    current_player.gold += bonus_gold
                session.add_log(f"REST room: recovered {healed} HP and {stamina} stamina, found 1 idle tonic" + (f", +{bonus_gold} gold." if bonus_gold > 0 else "."))
                event_payload.update({"rest_type": "camp_cache", "heal": healed, "stamina_restore": stamina, "idle_tonic": 1, "gold": bonus_gold})
            elif rest_roll < 0.56:
                _mark_mechanic_learned("support_rest:cleanse", "Rest Cleanse", "Rest rooms can cleanse negative statuses.")
                cleared = []
                for key in ("bleed", "burn", "weak", "vulnerable"):
                    if key in (current_player.status or {}):
                        current_player.status.pop(key, None)
                        cleared.append(key)
                if support_scale.get("late_room"):
                    add_status(current_player, "guard", turns=1, potency=0.10 + (session.SESSION["risk"] * 0.01))
                session.add_log(f"REST room: recovered {healed} HP and {stamina} stamina, cleared ailments.")
                event_payload.update({"rest_type": "cleanse", "heal": healed, "stamina_restore": stamina, "cleansed": cleared, "guard": bool(support_scale.get("late_room"))})
            else:
                _mark_mechanic_learned("support_rest:standard", "Rest Standard", "Rest rooms restore HP and stamina.")
                session.add_log(f"REST room: recovered {healed} HP and {stamina} stamina.")
                event_payload.update({"rest_type": "standard", "heal": healed, "stamina_restore": stamina})

        elif room_type == "trap":
            evade_chance = min(0.45, 0.08 + float(current_player.dodge_bonus) + (session.SESSION["risk"] * 0.02))
            if random.random() < evade_chance:
                session.add_log("TRAP room: avoided damage.")
                event_payload.update({"dodged": True, "damage": 0})
            else:
                base = int(8 + (session.SESSION["depth"] * 2) + (session.SESSION["risk"] * 4))
                mitigation = int(max(0, (current_player.dexterity - 5) * 0.8 + (current_player.vitality - 5) * 0.6))
                trap_damage = max(3, base - mitigation)
                current_player.hp = max(0.0, float(current_player.hp) - trap_damage)
                session.add_log(f"TRAP room: took {trap_damage} damage.")
                event_payload.update({"dodged": False, "damage": trap_damage})

                if current_player.hp <= 0:
                    session.add_log("Player died in a trap. Dungeon failed.")
                    state = session.state(current_player)
                    session.reset_session()
                    return {"dead": True, "state": state, "room_events": room_events + [event_payload]}

        elif room_type == "event":
            roll = random.random()
            if roll < 0.25:
                _mark_mechanic_learned("support_event:gold_cache", "Event Gold Cache", "Event rooms can award direct gold.")
                gold = int((random.randint(18, 42) + (session.SESSION["risk"] * 8) + scale_flat) * scale_mult)
                current_player.gold += gold
                session.add_log(f"EVENT room: found {gold} gold.")
                event_payload.update({"event": "gold_cache", "gold": gold})
            elif roll < 0.50:
                _mark_mechanic_learned("support_event:ancient_tablet", "Event Ancient Tablet", "Event rooms can convert into EXP.")
                exp_gain = int((22 + (session.SESSION["depth"] * 9) + (session.SESSION["risk"] * 10) + scale_flat) * scale_mult)
                current_player.gain_exp(exp_gain)
                session.add_log(f"EVENT room: gained {exp_gain} EXP.")
                event_payload.update({"event": "ancient_tablet", "exp": exp_gain})
            elif roll < 0.75:
                _mark_mechanic_learned("support_event:war_altar", "Event War Altar", "Event rooms can restore stamina.")
                stamina = int((26 + (session.SESSION["risk"] * 4) + scale_flat) * scale_mult)
                current_player.stamina = min(float(current_player.max_stamina), float(current_player.stamina) + stamina)
                session.add_log(f"EVENT room: recovered {stamina} stamina.")
                event_payload.update({"event": "war_altar", "stamina_restore": stamina})
            elif roll < 0.90:
                _mark_mechanic_learned("support_event:rune_scraps", "Event Rune Scraps", "Event rooms can award rune essence.")
                essence = max(1, int(round((2 + max(0, session.SESSION["risk"]) + (scale_flat * 0.2)) * min(1.35, scale_mult))))
                current_player.add_resource("rune_essence", essence)
                session.add_log(f"EVENT room: found rune scraps (+{essence} essence).")
                event_payload.update({"event": "rune_scraps", "essence": essence})
            else:
                _mark_mechanic_learned("support_event:battle_trance", "Event Battle Trance", "Event rooms can apply temporary guard.")
                potency = 0.16 + (session.SESSION["risk"] * 0.01) + min(0.10, float(support_scale.get("intensity", 0.0) or 0.0))
                turns = 3 if support_scale.get("pre_boss") else 2
                add_status(current_player, "guard", turns=turns, potency=potency)
                session.add_log("EVENT room: battle trance formed a temporary guard.")
                event_payload.update({"event": "battle_trance", "guard": True, "turns": turns, "potency": round(potency, 3)})

        elif room_type == "treasure":
            gold = int((random.randint(30, 70) + (session.SESSION["depth"] * 3) + (session.SESSION["risk"] * 12) + scale_flat) * scale_mult)
            current_player.gold += gold
            essence = max(1, int(round((random.randint(1, 3) + max(0, session.SESSION["risk"] - 1) + (scale_flat * 0.15)) * min(1.3, scale_mult))))
            current_player.add_resource("rune_essence", essence)
            chest_found = 0
            chest_ch = 0.10 + (session.SESSION["risk"] * 0.04) + (current_player.loot_luck * 0.20) + min(0.12, float(support_scale.get("intensity", 0.0) or 0.0) * 0.30)
            if random.random() < chest_ch:
                chest_found = 1 + (1 if session.SESSION["risk"] >= 4 and random.random() < 0.25 else 0)
                current_player.add_resource("arcane_chest", chest_found)
            session.add_log(f"TREASURE room: +{gold} gold, +{essence} essence" + (f", +{chest_found} chest" if chest_found else ""))
            event_payload.update({
                "gold": gold,
                "essence": essence,
                "chests": chest_found,
            })

        elif room_type == "shrine":
            roll = random.random()
            if roll < 0.25:
                _mark_mechanic_learned("support_shrine:healing", "Shrine Healing", "Shrines can restore HP.")
                heal = int(max(12, ((current_player.max_hp * 0.22) + (session.SESSION["risk"] * 3) + scale_flat) * scale_mult))
                hp_before = float(current_player.hp)
                current_player.hp = min(float(current_player.max_hp), hp_before + heal)
                gained = round(float(current_player.hp) - hp_before, 2)
                session.add_log(f"SHRINE room: restored {gained} HP.")
                event_payload.update({"blessing": "healing", "heal": gained})
            elif roll < 0.50:
                _mark_mechanic_learned("support_shrine:focus", "Shrine Focus", "Shrines can restore stamina.")
                stamina = int(max(18, ((current_player.max_stamina * 0.40) + (session.SESSION["risk"] * 2) + scale_flat) * scale_mult))
                st_before = float(current_player.stamina)
                current_player.stamina = min(float(current_player.max_stamina), st_before + stamina)
                gained = round(float(current_player.stamina) - st_before, 2)
                session.add_log(f"SHRINE room: restored {gained} stamina.")
                event_payload.update({"blessing": "focus", "stamina_restore": gained})
            elif roll < 0.75:
                _mark_mechanic_learned("support_shrine:rune", "Shrine Rune", "Shrines can yield relic value and bonus gold.")
                relics = 1 if random.random() < (0.50 + session.SESSION["risk"] * 0.05 + min(0.10, float(support_scale.get("intensity", 0.0) or 0.0) * 0.25)) else 0
                luck_temp = round(min(0.05, 0.01 + (session.SESSION["risk"] * 0.005)), 3)
                if relics > 0:
                    current_player.add_resource("rune_relic", relics)
                shrine_gold = int((8 + session.SESSION["depth"] * 2 + scale_flat) * min(1.25, scale_mult))
                current_player.gold += shrine_gold
                session.add_log(f"SHRINE room: gained blessing residue (+{relics} rune relic, temporary luck noted).")
                event_payload.update({"blessing": "rune", "relics": relics, "gold": shrine_gold, "luck_hint": luck_temp})
            elif roll < 0.90:
                _mark_mechanic_learned("support_shrine:ward", "Shrine Ward", "Shrines can apply a defensive blessing.")
                potency = 0.18 + (session.SESSION["risk"] * 0.015) + min(0.12, float(support_scale.get("intensity", 0.0) or 0.0))
                turns = 3 if support_scale.get("late_room") else 2
                add_status(current_player, "guard", turns=turns, potency=potency)
                session.add_log("SHRINE room: ward blessing granted temporary guard.")
                event_payload.update({"blessing": "ward", "guard": True, "turns": turns, "potency": round(potency, 3)})
            else:
                _mark_mechanic_learned("support_shrine:vault", "Shrine Vault", "Shrines can reveal Arcane Chests.")
                chest_count = 2 if support_scale.get("pre_boss") and session.SESSION["risk"] >= 4 else 1
                current_player.add_resource("arcane_chest", chest_count)
                session.add_log(f"SHRINE room: vault blessing revealed {chest_count} Arcane Chest" + ("s." if chest_count != 1 else "."))
                event_payload.update({"blessing": "vault", "chests": chest_count})

        room_events.append(event_payload)
        session.advance_room()

    if session.current_room_type() is None:
        state = session.state(current_player)
        if session.SESSION.get("can_leave", False):
            state["boss_exit_ready"] = True
        else:
            state["error"] = "Dungeon cannot be completed until boss is defeated."
        if room_events:
            state["room_events"] = room_events
        return state

    current_enemy_live = session.current_enemy()
    if current_enemy_live is not None and is_boss(current_enemy_live):
        _update_boss_run_state(current_enemy_live)
        current_enemy_live.intent = roll_boss_intent(current_enemy_live, rng_seed=random.randint(1, 10_000_000))
    state = session.state(current_player)
    if room_events:
        state["room_events"] = room_events
    return state


def _current_run_gain(resource_key: str) -> int:
    snapshot = dict(session.SESSION.get("start_snapshot", {}) or {})
    if not snapshot:
        return 0
    if resource_key == "gold":
        return int(getattr(current_player, "gold", 0) or 0) - int(snapshot.get("gold", 0) or 0)
    resources = dict(getattr(current_player, "resources", {}) or {})
    return int(resources.get(resource_key, 0) or 0) - int(snapshot.get(resource_key, 0) or 0)


def _handle_enemy_defeat(enemy: Enemy, combat_payload: dict):
    session.add_log(f"{enemy.name} defeated!")
    _counter_add("enemies_defeated", 1.0)
    _event_log_add(
        "combat",
        "Enemy defeated",
        f"{enemy.name} ({str(getattr(enemy, 'tier', 'normal') or 'normal')})",
        meta={"enemy": enemy.name, "tier": str(getattr(enemy, "tier", "normal") or "normal")},
    )

    room_type = session.current_room_type()
    risk = int(session.SESSION.get("risk", 0) or 0)
    depth = int(session.SESSION.get("depth", 1) or 1)
    exp_gain = enemy.level * (20 + session.SESSION["risk"] * 10) * (2 if room_type == "boss" else 1)
    current_player.gain_exp(int(exp_gain))
    session.add_log(f"Gained {int(exp_gain)} EXP")

    gold_gain = random.randint(12, 22) + (depth * 2) + (risk * 8)
    if room_type == "boss":
        gold_gain += random.randint(45, 80) + (risk * 12)
    current_player.gold += gold_gain
    session.add_log(f"Recovered {gold_gain} gold")

    stamina_restore = 4 + max(0, risk)
    if room_type == "boss":
        stamina_restore += 8
    stamina_before = float(current_player.stamina)
    current_player.stamina = min(float(current_player.max_stamina), float(current_player.stamina) + stamina_restore)
    restored = round(float(current_player.stamina) - stamina_before, 2)
    if restored > 0:
        session.add_log(f"Recovered {restored} stamina")

    essence_gain = 1 + max(0, session.SESSION["risk"]) + (1 if float(current_player.action_streak or 0) >= 3 else 0)
    if room_type == "boss":
        essence_gain += 3
    current_player.add_resource("rune_essence", essence_gain)
    session.add_log(f"Found {essence_gain} Rune Essence")

    # Tiered chest reward (services/chest.py): the chest's own rarity is
    # driven by this specific enemy's level/tier/modifiers, independent
    # of whether a bonus currency amount also drops this victory.
    chest_award = award_battle_chest(current_player, enemy, risk=risk, room_type=str(room_type or ""))
    chest_rarity_gain = chest_award.get("chest")
    if chest_rarity_gain:
        session.add_log(f"Found a {chest_rarity_gain} chest")
    currency_award = chest_award.get("currency")
    if currency_award:
        cname = CURRENCIES.get(currency_award["currency_id"], {}).get("name", currency_award["currency_id"])
        session.add_log(f"Found {currency_award['amount']} {cname}")

    relic_chance = 0.03 + (session.SESSION["risk"] * 0.02)
    if room_type == "boss":
        relic_chance += 0.10
    relic_gain = 0
    if random.random() < relic_chance:
        relic_gain = 1 if room_type != "boss" else random.randint(1, 3)
        current_player.add_resource("rune_relic", relic_gain)
        session.add_log(f"Found {relic_gain} Rune Relic")
    elif room_type == "boss" and risk >= 4 and _current_run_gain("rune_relic") <= 0:
        relic_gain = 1
        current_player.add_resource("rune_relic", relic_gain)
        session.add_log("Boss cache yielded 1 guaranteed Rune Relic")

    task = current_player.slayer_task or {}
    target = str(task.get("target", "") or "")
    enemy_arch = str(getattr(enemy, "archetype", "") or "")
    if target and int(task.get("remaining", 0) or 0) > 0 and target == enemy_arch:
        task["remaining"] = max(0, int(task.get("remaining", 0) or 0) - 1)
        if int(task["remaining"]) == 0:
            reward = 40 + (enemy.level * 6)
            current_player.gold += reward
            slayer_xp = 30 + (enemy.level * 5)
            current_player.gain_slayer_xp(slayer_xp)
            session.add_log(f"Slayer task complete! +{reward} gold, +{slayer_xp} slayer XP")
        current_player.slayer_task = task

    was_boss = (room_type == "boss")
    session.advance_room()

    if was_boss and session.current_room_type() is None:
        session.mark_boss_defeated()
        session.add_log("Boss defeated. You may now leave the dungeon.")
        _counter_add("bosses_defeated", 1.0)
        _event_log_add(
            "combat",
            "Boss defeated",
            f"{enemy.name} at depth {session.SESSION.get('depth', 1)}",
            severity="success",
            meta={"enemy": enemy.name, "depth": int(session.SESSION.get("depth", 1) or 1)},
        )
        return {
            "boss_defeated": True,
            "can_leave": True,
            "combat": combat_payload,
            "turn": {"player": combat_payload, "enemy": None},
            "awaiting_enemy_phase": False,
            "state": session.state(current_player),
            "victory_rewards": {
                "gold": int(gold_gain),
                "stamina": restored,
                "rune_essence": int(essence_gain),
                "chest": chest_rarity_gain,
                "chest_currency": currency_award,
                "rune_relic": int(relic_gain),
            },
        }

    state_or_result = _resolve_non_combat_rooms()
    if state_or_result.get("cleared") or state_or_result.get("dead"):
        state_or_result["combat"] = combat_payload
        state_or_result["victory_rewards"] = {
            "gold": int(gold_gain),
            "stamina": restored,
            "rune_essence": int(essence_gain),
            "chest": chest_rarity_gain,
            "chest_currency": currency_award,
            "rune_relic": int(relic_gain),
        }
        return state_or_result

    return {
        "combat": combat_payload,
        "state": state_or_result,
        "victory_rewards": {
            "gold": int(gold_gain),
            "stamina": restored,
            "rune_essence": int(essence_gain),
            "chest": chest_rarity_gain,
            "chest_currency": currency_award,
            "rune_relic": int(relic_gain),
        },
    }


def _regen_stamina(player: Player, amount: int = 20):
    bonus = max(0, int((player.vitality - 5) * 0.4) + int((player.dexterity - 5) * 0.25))
    regen = max(8, min(32, amount + bonus))
    player.stamina = min(player.max_stamina, player.stamina + regen)


def _combat_mana(player: Player) -> int:
    _apply_battle_defaults(player)
    return int(player.battle_state.get("mana", 0) or 0)


def _gain_mana(player: Player, amount: int) -> int:
    _apply_battle_defaults(player)
    cur = int(player.battle_state.get("mana", 0) or 0)
    new = max(0, min(int(player.mana_cap), cur + int(amount)))
    player.battle_state["mana"] = new
    return new - cur


def _combat_resources(player: Player) -> dict:
    return {
        "mana": _combat_mana(player),
        "mana_cap": int(player.mana_cap),
        "stamina": player.stamina,
        "max_stamina": player.max_stamina,
        "action_cooldowns": player.action_cooldowns,
        "combo_windows": player.combo_windows,
    }


def _combat_loadout_payload(player: Player) -> list:
    _apply_battle_defaults(player)
    rows = []
    for sid in (player.battle_skills or []):
        row = _battle_skill_row(sid)
        action = str(row.get("action", "") or "").lower().strip()
        rows.append({
            "id": sid,
            "name": row.get("name", sid),
            "kind": row.get("kind", "normal"),
            "action": action,
            "mana_cost": int(row.get("mana_cost", 0) or 0),
            "damage_mult": float(row.get("damage_mult", 1.0) or 1.0),
            "desc": str(row.get("desc", "") or ""),
            "cooldown": int((player.action_cooldowns or {}).get(action, 0) or 0),
            "tags": list(row.get("tags", [])),
        })
    return rows


def _skill_for_action(player: Player, action: str) -> str:
    _apply_battle_defaults(player)
    action = str(action or "").lower().strip()
    if action == "skip":
        return "skip"
    for sid in (player.battle_skills or []):
        row = _battle_skill_row(sid)
        if str(row.get("kind", "normal")) == "normal" and str(row.get("action", "") or "").lower() == action:
            return sid
    for sid in (player.battle_skills or []):
        if str(_battle_skill_row(sid).get("kind", "normal")) == "normal":
            return sid
    return "quick_slash"


def _update_boss_run_state(enemy: Enemy):
    if not is_boss(enemy):
        return {}
    gains_gold = max(0, _current_run_gain("gold"))
    gains_essence = max(0, _current_run_gain("rune_essence"))
    gains_chest = max(0, _current_run_gain("arcane_chest"))
    gains_relic = max(0, _current_run_gain("rune_relic"))
    reward_score = gains_gold + (gains_essence * 18) + (gains_chest * 180) + (gains_relic * 340)
    heat = min(1.0, reward_score / 900.0)
    risk = int(session.SESSION.get("risk", 0) or 0)
    player_hp_ratio = float(current_player.hp or 0.0) / max(1.0, float(current_player.max_hp or 1.0))
    boss_hp_ratio = float(getattr(enemy, "hp", 0.0) or 0.0) / max(1.0, float(getattr(enemy, "max_hp", 1.0) or 1.0))
    state = {
        "reward_heat": round(heat, 3),
        "risk_pressure": round(min(1.0, (risk / 7.0) + max(0.0, player_hp_ratio - 0.55)), 3),
        "finisher_window": bool(player_hp_ratio >= 0.60 and boss_hp_ratio <= 0.55),
        "gains": {
            "gold": int(gains_gold),
            "essence": int(gains_essence),
            "chest": int(gains_chest),
            "relic": int(gains_relic),
        },
    }
    mods = getattr(enemy, "combat_mods", {}) or {}
    mods["boss_run_state"] = state
    enemy.combat_mods = mods
    return state


def _tick_action_cooldowns(player: Player):
    updated = {}
    for action, turns in (player.action_cooldowns or {}).items():
        n = int(turns) - 1
        if n > 0:
            updated[action] = n
    player.action_cooldowns = updated


def _tick_combo_windows(player: Player):
    updated = {}
    for key, turns in (player.combo_windows or {}).items():
        n = int(turns) - 1
        if n > 0:
            updated[key] = n
    player.combo_windows = updated


def _set_action_cooldown(player: Player, action: str):
    cd = int(ACTION_CONFIG[action].get("cooldown", 0) or 0)
    if action == "focus" and _has_modifier("arcane_suppression"):
        cd += 1
    if cd > 0:
        player.action_cooldowns[action] = cd


def _has_modifier(mod_id: str) -> bool:
    mods = session.SESSION.get("modifiers", [])
    return any((m.get("id") == mod_id) for m in mods)


def _action_cost(action: str) -> int:
    base = int(ACTION_CONFIG[action]["cost"])
    if action == "focus" and _has_modifier("arcane_suppression"):
        base += 10
    return base


def _seed_next_enemy_intent(enemy: Enemy):
    enemy.intent = session.roll_enemy_intent(enemy, risk=session.SESSION.get("risk", 0))


def _apply_room_affix_player_phase(player: Player, enemy: Enemy, player_combat: dict):
    affix = session.current_affix()
    if not isinstance(affix, dict):
        return

    affix_id = str(affix.get("id", "") or "")
    dmg = float(player_combat.get("damage", 0.0) or 0.0)

    if affix_id == "shielded" and dmg > 0:
        reduced = round(dmg * 0.25, 2)
        player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
        enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
        player_combat["enemy_hp"] = float(enemy.hp)
        player_combat["room_affix_effect"] = {"id": affix_id, "reduced": reduced}
        session.add_log(f"Room affix SHIELDED absorbs {reduced}.")

    if affix_id == "bloodbound" and dmg > 0:
        reflect = max(1.0, round(dmg * 0.12, 2))
        player.hp = max(0.0, float(player.hp) - reflect)
        player_combat["room_affix_effect"] = {"id": affix_id, "self_damage": reflect}
        session.add_log(f"Room affix BLOODBOUND reflects {reflect} to player.")


def _apply_room_affix_enemy_phase(enemy_combat: dict):
    affix = session.current_affix()
    if not isinstance(affix, dict):
        return
    if str(affix.get("id", "") or "") != "enraged":
        return

    bonus = round(float(enemy_combat.get("damage", 0.0) or 0.0) * 0.20, 2)
    if bonus <= 0:
        return
    current_player.hp = max(0.0, float(current_player.hp) - bonus)
    enemy_combat["damage"] = round(float(enemy_combat.get("damage", 0.0) or 0.0) + bonus, 2)
    enemy_combat["room_affix_effect"] = {"id": "enraged", "bonus": bonus}
    session.add_log(f"Room affix ENRAGED adds {bonus} damage.")


def _ensure_enemy_mechanics(enemy: Enemy):
    mods = getattr(enemy, "combat_mods", {}) or {}
    arch = str(getattr(enemy, "archetype", "brute") or "brute").lower()
    variant = str(mods.get("elite_variant", "") or "").lower()
    mods.setdefault("turn_counter", 0)
    if arch == "caster":
        mods.setdefault("arcane_barrier", 1)
    if arch == "summoner":
        mods.setdefault("summon_cycle", 0)
    if variant == "stormcaller":
        mods.setdefault("static_charge", 0)
    if variant == "broodlord":
        mods.setdefault("brood_cycle", 0)
    if variant == "bonecaller":
        mods.setdefault("harvest_ready", 0)
    if is_boss(enemy):
        mods.setdefault("boss_phase_burst_ready", 0)
        mods.setdefault("boss_guard_cycle", 0)
    enemy.combat_mods = mods


def _boss_phase(enemy: Enemy) -> int:
    hp = float(getattr(enemy, "hp", 0.0) or 0.0)
    max_hp = max(1.0, float(getattr(enemy, "max_hp", hp or 1.0) or (hp or 1.0)))
    ratio = hp / max_hp
    if ratio <= 0.30:
        return 2
    if ratio <= 0.70:
        return 1
    return 0


def _apply_combo_synergies(player: Player, enemy: Enemy, action: str, player_combat: dict):
    dmg = float(player_combat.get("damage", 0.0) or 0.0)
    if dmg <= 0 and action not in ("focus", "rupture"):
        return

    # Focus primes heavy for extra burst.
    if action == "focus":
        player.combo_windows["heavy_empower"] = 2
        return

    # Rupture primes basic for execute pressure.
    if action == "rupture":
        player.combo_windows["basic_execute"] = 2
        return

    if action == "heavy" and int(player.combo_windows.get("heavy_empower", 0)) > 0:
        bonus = round(dmg * 0.35, 2)
        player_combat["damage"] = round(dmg + bonus, 2)
        enemy.hp = max(0.0, float(enemy.hp) - bonus)
        player_combat["enemy_hp"] = float(enemy.hp)
        player_combat["combo"] = {"name": "heavy_empower", "bonus_damage": bonus}
        player.combo_windows.pop("heavy_empower", None)
        return

    if action == "basic" and int(player.combo_windows.get("basic_execute", 0)) > 0:
        hp = float(getattr(enemy, "hp", 0.0) or 0.0)
        max_hp = float(getattr(enemy, "max_hp", hp) or hp)
        bleed = (getattr(enemy, "status", {}) or {}).get("bleed")
        bleed_active = isinstance(bleed, dict) and int(bleed.get("turns", 0) or 0) > 0
        if max_hp > 0 and hp / max_hp <= 0.22:
            player_combat["combo"] = {"name": "basic_execute", "execute": True}
            enemy.hp = 0.0
            player_combat["enemy_hp"] = 0.0
            player.combo_windows.pop("basic_execute", None)
        elif bleed_active:
            bonus = round(dmg * 0.25, 2)
            player_combat["damage"] = round(dmg + bonus, 2)
            enemy.hp = max(0.0, float(enemy.hp) - bonus)
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["combo"] = {"name": "basic_execute", "bonus_damage": bonus}
            player.combo_windows.pop("basic_execute", None)


def _apply_enemy_archetype_reactions(player: Player, enemy: Enemy, action: str, player_combat: dict):
    _ensure_enemy_mechanics(enemy)
    arch = str(getattr(enemy, "archetype", "brute") or "brute").lower()
    variant = str((getattr(enemy, "combat_mods", {}) or {}).get("elite_variant", "") or "").lower()
    boss_phase = _boss_phase(enemy) if is_boss(enemy) else 0
    dmg = float(player_combat.get("damage", 0.0) or 0.0)
    if dmg <= 0:
        return

    if arch == "tank" and action != "rupture":
        reduced = round(dmg * 0.22, 2)
        player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
        enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
        player_combat["enemy_hp"] = float(enemy.hp)
        player_combat["archetype_reaction"] = {"type": "tank_plating", "reduced": reduced}
        return

    if arch == "skirmisher":
        evade_ch = 0.22 if action in ("heavy", "basic") else 0.12
        if random.random() < evade_ch:
            reduced = round(dmg * 0.50, 2)
            player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
            enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["archetype_reaction"] = {"type": "skirmisher_evade", "reduced": reduced}
        return

    if arch == "caster":
        barrier = int(enemy.combat_mods.get("arcane_barrier", 0) or 0)
        if barrier > 0 and action != "focus":
            reduced = round(dmg * 0.35, 2)
            player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
            enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
            player_combat["enemy_hp"] = float(enemy.hp)
            enemy.combat_mods["arcane_barrier"] = 0
            player_combat["archetype_reaction"] = {"type": "arcane_barrier", "reduced": reduced}
        elif action == "focus":
            enemy.combat_mods["arcane_barrier"] = 0
            add_status(enemy, "vulnerable", turns=2, potency=0.10)

    if variant == "crusher" and action == "guard":
        reduced = round(dmg * 0.18, 2)
        if reduced > 0:
            _mark_mechanic_learned("elite_variant:crusher", "Elite Crusher", "Crusher punishes guard-heavy lines.")
            player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
            enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["elite_variant_reaction"] = {"type": "crusher_break_guard", "reduced": reduced}
    elif variant == "shadowstep" and action in ("heavy", "rupture") and random.random() < 0.35:
        reduced = round(dmg * 0.40, 2)
        if reduced > 0:
            _mark_mechanic_learned("elite_variant:shadowstep", "Elite Shadowstep", "Shadowstep can slip committed attacks.")
            player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
            enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["elite_variant_reaction"] = {"type": "shadowstep_slip", "reduced": reduced}
    elif variant == "bulwark" and action != "rupture":
        reduced = round(dmg * 0.12, 2)
        if reduced > 0:
            _mark_mechanic_learned("elite_variant:bulwark", "Elite Bulwark", "Bulwark shrugs off non-rupture damage.")
            player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
            enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["elite_variant_reaction"] = {"type": "bulwark_shell", "reduced": reduced}
    elif variant == "bonecaller" and int((getattr(enemy, "status", {}) or {}).get("bleed", {}).get("turns", 0) or 0) > 0:
        _mark_mechanic_learned("elite_variant:bonecaller", "Elite Bonecaller", "Bonecaller turns bleed setup into healing pressure.")
        enemy.combat_mods["harvest_ready"] = 1

    if is_boss(enemy):
        if arch == "tank" and action != "rupture" and boss_phase >= 1:
            reduced = round(dmg * (0.12 + (0.06 * boss_phase)), 2)
            if reduced > 0:
                _mark_mechanic_learned("boss_archetype:tank", "Boss Tank", "Tank bosses gain bastion-style phase reduction.")
                player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
                enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
                player_combat["enemy_hp"] = float(enemy.hp)
                player_combat["boss_phase_reaction"] = {"type": "tank_bastion", "reduced": reduced, "phase": boss_phase}
        elif arch == "skirmisher" and action in ("heavy", "rupture") and boss_phase >= 1 and random.random() < (0.20 + (0.08 * boss_phase)):
            reduced = round(dmg * (0.25 + (0.10 * boss_phase)), 2)
            if reduced > 0:
                _mark_mechanic_learned("boss_archetype:skirmisher", "Boss Skirmisher", "Skirmisher bosses can slip committed attacks in phase play.")
                player_combat["damage"] = round(max(0.0, dmg - reduced), 2)
                enemy.hp = min(float(enemy.hp) + reduced, float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp))
                player_combat["enemy_hp"] = float(enemy.hp)
                player_combat["boss_phase_reaction"] = {"type": "skirmisher_phase_slip", "reduced": reduced, "phase": boss_phase}
        elif arch == "caster" and boss_phase >= 2 and action != "focus":
            _mark_mechanic_learned("boss_archetype:caster", "Boss Caster", "Caster bosses snap barriers back online in late phases.")
            enemy.combat_mods["arcane_barrier"] = 1
            player_combat["boss_phase_reaction"] = {"type": "caster_barrier_snap", "phase": boss_phase}


def _apply_enemy_archetype_turn_effects(player: Player, enemy: Enemy, enemy_combat: dict):
    _ensure_enemy_mechanics(enemy)
    arch = str(getattr(enemy, "archetype", "brute") or "brute").lower()
    mods = enemy.combat_mods
    variant = str(mods.get("elite_variant", "") or "").lower()
    boss_phase = _boss_phase(enemy) if is_boss(enemy) else 0
    mods["turn_counter"] = int(mods.get("turn_counter", 0) or 0) + 1

    if arch == "summoner":
        mods["summon_cycle"] = int(mods.get("summon_cycle", 0) or 0) + 1
        if mods["summon_cycle"] >= 2:
            swarm = 3 + max(0, session.SESSION.get("risk", 0))
            player.hp = max(0.0, float(player.hp) - swarm)
            enemy_combat["summoner_swarm"] = swarm
            mods["summon_cycle"] = 0

    if arch == "caster":
        # Caster slowly rebuilds barrier.
        if int(mods.get("arcane_barrier", 0) or 0) <= 0 and random.random() < 0.35:
            mods["arcane_barrier"] = 1
            enemy_combat["caster_barrier_refreshed"] = True

    if variant == "berserker" and float(enemy.hp or 0.0) / max(1.0, float(getattr(enemy, "max_hp", 1.0) or 1.0)) <= 0.5:
        bonus = round(float(enemy_combat.get("damage", 0.0) or 0.0) * 0.18, 2)
        if bonus > 0:
            _mark_mechanic_learned("elite_variant:berserker", "Elite Berserker", "Berserker elites gain damage below half HP.")
            current_player.hp = max(0.0, float(current_player.hp) - bonus)
            enemy_combat["damage"] = round(float(enemy_combat.get("damage", 0.0) or 0.0) + bonus, 2)
            enemy_combat["elite_variant_effect"] = {"type": "berserker_rage", "bonus": bonus}
    elif variant == "hexweaver":
        _mark_mechanic_learned("elite_variant:hexweaver", "Elite Hexweaver", "Hexweaver applies weak pressure over time.")
        add_status(player, "weak", turns=1, potency=0.06)
        enemy_combat["elite_variant_effect"] = {"type": "hexweaver_weak"}
    elif variant == "stormcaller":
        mods["static_charge"] = int(mods.get("static_charge", 0) or 0) + 1
        if int(mods.get("static_charge", 0) or 0) >= 2:
            _mark_mechanic_learned("elite_variant:stormcaller", "Elite Stormcaller", "Stormcaller stores charge then discharges burst damage.")
            shock = 4 + max(0, session.SESSION.get("risk", 0))
            current_player.hp = max(0.0, float(current_player.hp) - shock)
            enemy_combat["elite_variant_effect"] = {"type": "stormcaller_discharge", "damage": shock}
            mods["static_charge"] = 0
    elif variant == "venomrunner":
        _mark_mechanic_learned("elite_variant:venomrunner", "Elite Venomrunner", "Venomrunner adds bleed pressure on enemy turns.")
        add_status(player, "bleed", turns=2, potency=2.0 + max(0, session.SESSION.get("risk", 0) * 0.4))
        enemy_combat["elite_variant_effect"] = {"type": "venomrunner_bleed"}
    elif variant == "ironhide" and random.random() < 0.35:
        _mark_mechanic_learned("elite_variant:ironhide", "Elite Ironhide", "Ironhide can rebuild guard mid fight.")
        add_status(enemy, "guard", turns=1, potency=0.18)
        enemy_combat["elite_variant_effect"] = {"type": "ironhide_guard"}
    elif variant == "broodlord":
        mods["brood_cycle"] = int(mods.get("brood_cycle", 0) or 0) + 1
        if int(mods.get("brood_cycle", 0) or 0) >= 2:
            _mark_mechanic_learned("elite_variant:broodlord", "Elite Broodlord", "Broodlord builds swarm burst cycles.")
            swarm = 5 + max(0, session.SESSION.get("risk", 0))
            current_player.hp = max(0.0, float(current_player.hp) - swarm)
            enemy_combat["elite_variant_effect"] = {"type": "broodlord_swarm", "damage": swarm}
            mods["brood_cycle"] = 0
    elif variant == "bonecaller" and int(mods.get("harvest_ready", 0) or 0) > 0:
        _mark_mechanic_learned("elite_variant:bonecaller", "Elite Bonecaller", "Bonecaller converts bleed setup into healing.")
        heal = round(max(4.0, float(enemy_combat.get("damage", 0.0) or 0.0) * 0.20), 2)
        enemy.hp = min(float(getattr(enemy, "max_hp", enemy.hp) or enemy.hp), float(enemy.hp) + heal)
        enemy_combat["enemy_hp"] = float(enemy.hp)
        enemy_combat["elite_variant_effect"] = {"type": "bonecaller_harvest", "heal": heal}
        mods["harvest_ready"] = 0

    if is_boss(enemy):
        if arch == "brute" and boss_phase >= 1 and int(mods.get("turn_counter", 0) or 0) % 2 == 0:
            _mark_mechanic_learned("boss_archetype:brute", "Boss Brute", "Brute bosses trigger quake bursts during later phases.")
            quake = 4 + boss_phase + max(0, session.SESSION.get("risk", 0))
            current_player.hp = max(0.0, float(current_player.hp) - quake)
            enemy_combat["boss_phase_effect"] = {"type": "brute_quake", "damage": quake, "phase": boss_phase}
        elif arch == "caster":
            if boss_phase >= 1 and int(mods.get("arcane_barrier", 0) or 0) <= 0:
                _mark_mechanic_learned("boss_archetype:caster", "Boss Caster", "Caster bosses rebuild barriers during phase shifts.")
                mods["arcane_barrier"] = 1
                enemy_combat["boss_phase_effect"] = {"type": "caster_barrier_phase", "phase": boss_phase}
            if boss_phase >= 2:
                add_status(player, "vulnerable", turns=1, potency=0.10)
                enemy_combat["boss_phase_effect"] = {"type": "caster_hex_phase", "phase": boss_phase}
        elif arch == "skirmisher" and boss_phase >= 1:
            if random.random() < (0.18 + (0.06 * boss_phase)):
                _mark_mechanic_learned("boss_archetype:skirmisher", "Boss Skirmisher", "Skirmisher bosses create weak windows in later phases.")
                add_status(player, "weak", turns=1, potency=0.08 + (boss_phase * 0.02))
                enemy_combat["boss_phase_effect"] = {"type": "skirmisher_rupture_window", "phase": boss_phase}
        elif arch == "tank":
            mods["boss_guard_cycle"] = int(mods.get("boss_guard_cycle", 0) or 0) + 1
            if boss_phase >= 1 and int(mods.get("boss_guard_cycle", 0) or 0) >= 2:
                _mark_mechanic_learned("boss_archetype:tank", "Boss Tank", "Tank bosses cycle fortress guard in later phases.")
                add_status(enemy, "guard", turns=1 + boss_phase, potency=0.14 + (0.04 * boss_phase))
                enemy_combat["boss_phase_effect"] = {"type": "tank_fortress_cycle", "phase": boss_phase}
                mods["boss_guard_cycle"] = 0
        elif arch == "summoner":
            extra_swarm = boss_phase + (1 if int(mods.get("turn_counter", 0) or 0) % 2 == 0 else 0)
            if extra_swarm > 0:
                _mark_mechanic_learned("boss_archetype:summoner", "Boss Summoner", "Summoner bosses scale swarm pressure by phase.")
                current_player.hp = max(0.0, float(current_player.hp) - extra_swarm)
                enemy_combat["boss_phase_effect"] = {"type": "summoner_phase_swarm", "damage": extra_swarm, "phase": boss_phase}

    enemy.combat_mods = mods


def _apply_intent_counter(player: Player, enemy: Enemy, action: str, player_combat: dict):
    intent = getattr(enemy, "intent", None)
    if not isinstance(intent, dict):
        return

    counter_action = str(intent.get("counter_action", "") or "").lower()
    if not counter_action:
        return

    if action == counter_action:
        mana_back = _gain_mana(player, 3)
        player_combat["counter"] = {
            "success": True,
            "against": intent.get("type", "unknown"),
            "reward": "mana_refund+damage_bonus",
            "mana_gained": mana_back,
        }
        dmg = float(player_combat.get("damage", 0.0) or 0.0)
        if dmg > 0:
            bonus = round(dmg * 0.20, 2)
            player_combat["damage"] = round(dmg + bonus, 2)
            enemy.hp = max(0.0, float(enemy.hp) - bonus)
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["counter_damage_bonus"] = bonus
        add_status(enemy, "weak", turns=1, potency=0.12)
    else:
        player_combat["counter"] = {
            "success": False,
            "against": intent.get("type", "unknown"),
            "needed": counter_action,
        }
        # Only mild punishment; intent pressure is mostly strategic signal.
        if action in ("heavy", "rupture"):
            add_status(player, "vulnerable", turns=1, potency=0.08)


def _player_action_turn(player: Player, enemy: Enemy, action: str, damage_multiplier: float = 1.0):
    cfg = ACTION_CONFIG[action]
    cost = _action_cost(action)

    if int(player.action_cooldowns.get(action, 0)) > 0:
        return {
            "error": f"Action '{action}' is on cooldown",
            "cooldown": int(player.action_cooldowns.get(action, 0)),
        }

    if player.stamina < cost:
        return {
            "error": f"Not enough stamina for '{action}'",
            "required": cost,
            "current": player.stamina,
        }

    if player.last_action == action:
        player.action_streak += 1
    else:
        player.last_action = action
        player.action_streak = 1

    # Repeating same move gets less efficient (max -40%).
    repeat_step = 0.15 if _has_modifier("volatile_shadows") else 0.10
    repetition_penalty = min(0.40, max(0.0, (player.action_streak - 1) * repeat_step))
    player.stamina -= cost

    if action in ("guard", "focus"):
        vit_bonus = min(0.15, max(0.0, (player.vitality - 5) * 0.01))
        int_bonus = min(0.20, max(0.0, (player.intelligence - 5) * 0.012))
        if action == "guard":
            add_status(player, "guard", turns=2, potency=0.35 + vit_bonus)
        else:
            add_status(enemy, "vulnerable", turns=2, potency=0.25 + int_bonus)
            add_status(player, "guard", turns=1, potency=0.10 + (vit_bonus * 0.5))

        return {
            "event": "player_action",
            "action": action,
            "damage": 0.0,
            "enemy_hp": float(enemy.hp),
            "stamina_cost": cost,
            "stamina_after": player.stamina,
            "action_penalty": round(repetition_penalty, 2),
            "cooldowns": player.action_cooldowns,
            "enemy_status": getattr(enemy, "status", {}),
            "player_status": getattr(player, "status", {}),
            "passive_triggers": {},
        }

    combat = engine_player_attack(player, enemy)
    base_damage = float(combat.get("damage", 0.0) or 0.0)
    action_mult = float(cfg["damage_mult"])
    str_bonus = min(0.35, max(0.0, (player.strength - 5) * 0.012))
    dex_bonus = min(0.30, max(0.0, (player.dexterity - 5) * 0.01))
    int_bonus = min(0.20, max(0.0, (player.intelligence - 5) * 0.01))
    if action == "heavy":
        action_mult *= (1.0 + str_bonus)
    elif action == "rupture":
        action_mult *= (1.0 + dex_bonus)
    elif action == "basic":
        action_mult *= (1.0 + int_bonus * 0.4)
    final_mult = max(0.1, action_mult * (1.0 - repetition_penalty) * max(0.1, float(damage_multiplier or 1.0)))
    adjusted_damage = round(base_damage * final_mult, 2)
    delta = round(adjusted_damage - base_damage, 2)

    if abs(delta) > 0:
        enemy.hp = max(0.0, float(enemy.hp) - delta)

    combat["damage"] = adjusted_damage
    combat["enemy_hp"] = float(enemy.hp)
    combat["action"] = action
    combat["stamina_cost"] = cost
    combat["stamina_after"] = player.stamina
    combat["action_penalty"] = round(repetition_penalty, 2)
    combat["cooldowns"] = player.action_cooldowns

    if action == "heavy":
        add_status(player, "vulnerable", turns=2, potency=0.15)
    elif action == "rupture":
        bleed_tick = max(1.0, round(adjusted_damage * (0.15 + dex_bonus * 0.5), 2))
        add_status(enemy, "bleed", turns=3, potency=bleed_tick)
        combat["rupture_bleed_tick"] = bleed_tick

    return combat


@app.post("/combat/player_attack")
def player_attack():
    enemy = session.current_enemy()
    if not session.SESSION["active"] or enemy is None:
        return {"error": "No active dungeon. Start one with POST /dungeon/start"}

    combat = engine_player_attack(current_player, enemy)
    dmg = float(combat.get("damage", 0.0) or 0.0)
    session.add_log(f"Player hits {enemy.name} for {dmg} (enemy hp now {max(enemy.hp, 0)})")

    if enemy.hp <= 0:
        return _handle_enemy_defeat(enemy, combat)

    return {"combat": combat, "state": session.state(current_player)}


@app.post("/combat/enemy_attack")
def enemy_attack(payload: dict):
    enemy = session.current_enemy()
    if not session.SESSION["active"] or enemy is None:
        return {"error": "No active dungeon. Start one with POST /dungeon/start"}

    dodge_success = bool(payload.get("dodge_success", False))
    combat = engine_enemy_attack(current_player, enemy, dodge_success=dodge_success)
    if current_player.hp < 0:
        current_player.hp = 0.0

    session.add_log(
        f"{enemy.name} attacks | dmg {combat.get('damage', 0)} | player hp {current_player.hp}"
    )

    if current_player.hp <= 0:
        session.add_log("Player died. Dungeon failed.")
        state = session.state(current_player)
        session.reset_session()
        return {"dead": True, "state": state, "combat": combat}

    return {"combat": combat, "state": session.state(current_player)}


def _consume_prayer_runes(player: Player, prayer_id: str) -> bool:
    prayer = PRAYER_BOOK.get(prayer_id)
    if not prayer:
        return False
    rune = str(prayer.get("rune", "") or "")
    need = int(prayer.get("runes_per_turn", 1) or 1)
    have = int(player.runes.get(rune, 0) or 0)
    if have < need:
        return False
    player.runes[rune] = have - need
    return True


def _apply_player_prayer_bonus(player: Player, enemy: Enemy, action: str, player_combat: dict):
    prayer_id = str(getattr(player, "active_prayer", "") or "")
    if not prayer_id:
        return

    prayer = PRAYER_BOOK.get(prayer_id)
    if not prayer:
        player.active_prayer = ""
        return

    if not _consume_prayer_runes(player, prayer_id):
        player.active_prayer = ""
        player_combat["prayer"] = {"active": False, "reason": "out_of_runes"}
        return

    effect = str(prayer.get("effect", "") or "")
    if effect == "attack_mult" and action not in ("guard", "focus"):
        dmg = float(player_combat.get("damage", 0.0) or 0.0)
        bonus = round(dmg * float(prayer.get("value", 0.0) or 0.0), 2)
        if bonus > 0:
            player_combat["damage"] = round(dmg + bonus, 2)
            enemy.hp = max(0.0, float(enemy.hp) - bonus)
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["prayer_bonus_damage"] = bonus

    player_combat["prayer"] = {
        "active": True,
        "id": prayer_id,
        "name": prayer.get("name", prayer_id),
        "rune": prayer.get("rune", ""),
    }

def _run_player_phase(skill_id: str):
    enemy = session.current_enemy()
    if session.SESSION.get("active", False) and enemy is None and session.SESSION.get("can_leave", False):
        return {"error": "Boss defeated. Leave now to lock rewards and finish the run.", "can_leave": True, "state": session.state(current_player)}
    if not session.SESSION["active"] or enemy is None:
        return {"error": "No active dungeon. Start one with POST /dungeon/start"}

    enemy_tier = str(getattr(enemy, "tier", "") or "").lower()
    enemy_arch = str(getattr(enemy, "archetype", "") or "brute").lower()
    elite_variant = str((getattr(enemy, "combat_mods", {}) or {}).get("elite_variant", "") or "").lower()
    if enemy_tier == "elite" and elite_variant:
        _mark_mechanic_learned(f"elite_variant:{elite_variant}", f"Elite {elite_variant.replace('_', ' ').title()}", f"{enemy.name} used the {elite_variant.replace('_', ' ')} variant.")
    if enemy_tier == "boss":
        _mark_mechanic_learned(f"boss_archetype:{enemy_arch}", f"Boss {enemy_arch.title()}", f"{enemy.name} revealed {enemy_arch} boss phase behavior.")
    affix = session.current_affix()
    if isinstance(affix, dict):
        affix_id = str(affix.get("id", "") or "").lower()
        affix_name = str(affix.get("name", affix_id) or affix_id)
        affix_desc = str(affix.get("desc", "") or "")
        if affix_id:
            _mark_mechanic_learned(f"room_affix:{affix_id}", f"Room Affix {affix_name}", affix_desc)
    room_type = str(session.current_room_type() or "").lower()
    if room_type:
        _mark_mechanic_learned(f"room_type:{room_type}", f"Room Type {room_type.replace('_', ' ').title()}", f"Entered a {room_type.replace('_', ' ')} room.")

    if session.SESSION.get("awaiting_enemy_attack", False):
        return {
            "error": "Enemy phase pending. Complete dodge + enemy attack first.",
            "awaiting_enemy_phase": True,
            "state": session.state(current_player),
        }

    _tick_action_cooldowns(current_player)
    _tick_combo_windows(current_player)
    if is_boss(enemy):
        _update_boss_run_state(enemy)
    if not isinstance(getattr(enemy, "intent", None), dict):
        _seed_next_enemy_intent(enemy)

    _apply_battle_defaults(current_player)
    sid = str(skill_id or "").strip().lower()

    if sid == "skip":
        gained = _gain_mana(current_player, SKIP_TURN_MANA_BONUS)
        session.SESSION["awaiting_enemy_attack"] = True
        session.SESSION["pending_player_action"] = "skip"
        session.add_log(
            f"You skip the turn and recover +{gained} mana ({_combat_mana(current_player)}/{current_player.mana_cap})."
        )
        skip_combat = {
            "event": "skip_turn",
            "action": "skip",
            "damage": 0.0,
            "enemy_hp": float(enemy.hp),
            "mana_gained": gained,
            "mana_after": _combat_mana(current_player),
            "skill_roll": {"id": "skip", "name": "Skip Turn", "kind": "utility", "action": "skip", "mana_cost": 0, "chosen": True},
        }
        return {
            "combat": skip_combat,
            "turn": {"player": skip_combat, "enemy": None},
            "resources": _combat_resources(current_player),
            "awaiting_enemy_phase": True,
            "state": session.state(current_player),
        }

    if sid not in (current_player.battle_skills or []):
        return {
            "error": f"Skill '{sid or 'none'}' is not in your battle loadout",
            "loadout": list(current_player.battle_skills or []),
            "resources": _combat_resources(current_player),
            "awaiting_enemy_phase": False,
            "state": session.state(current_player),
        }

    row = _battle_skill_row(sid)
    action = str(row.get("action", "") or "").lower().strip()
    if action not in ACTION_CONFIG:
        action = "basic"
    is_cursed_skill = str(row.get("kind", "normal")) == "cursed"

    if not is_cursed_skill and int((current_player.action_cooldowns or {}).get(action, 0) or 0) > 0:
        return {
            "error": f"{row.get('name', sid)} is on cooldown",
            "cooldown": int(current_player.action_cooldowns.get(action, 0) or 0),
            "resources": _combat_resources(current_player),
            "awaiting_enemy_phase": False,
            "state": session.state(current_player),
        }

    mana_cost = int(row.get("mana_cost", 0) or 0)
    cur_mana = _combat_mana(current_player)
    if cur_mana < mana_cost:
        return {
            "error": f"Not enough mana for {row.get('name', sid)}",
            "required": mana_cost,
            "current": cur_mana,
            "resources": _combat_resources(current_player),
            "awaiting_enemy_phase": False,
            "state": session.state(current_player),
        }
    current_player.battle_state["mana"] = cur_mana - mana_cost

    rolled_skill = {
        "id": sid,
        "name": row.get("name", sid),
        "kind": row.get("kind", "normal"),
        "action": row.get("action", "basic"),
        "damage_mult": float(row.get("damage_mult", 1.0) or 1.0),
        "mana_cost": mana_cost,
        "tags": list(row.get("tags", [])),
        "chosen": True,
    }
    mastery_gain = _battle_mastery_gain(
        current_player,
        sid,
        7.0 + (float(session.SESSION.get("risk", 0) or 0) * 1.6),
    )

    if is_cursed_skill:
        player_combat = _apply_cursed_skill(current_player, enemy, rolled_skill)
    else:
        damage_mult = _battle_damage_multiplier(current_player, rolled_skill)
        player_combat = _player_action_turn(current_player, enemy, action, damage_multiplier=damage_mult)
        player_combat["battle_damage_multiplier"] = round(float(damage_mult), 3)
        if player_combat.get("error"):
            _gain_mana(current_player, mana_cost)
            player_combat["resources"] = _combat_resources(current_player)

    # Mastery milestone perks for normal skills.
    mastery_perks = []
    if str(rolled_skill.get("kind", "normal")) != "cursed":
        mastery_state_now = _battle_mastery_state(current_player, str(rolled_skill.get("id", "") or ""))
        mastery_tier = _battle_mastery_tier(float(mastery_state_now.get("level", 1.0) or 1.0))
        if mastery_tier >= 1:
            gained = _gain_mana(current_player, 2)
            if gained > 0:
                mastery_perks.append({"id": "mana_refund", "value": gained})
        if mastery_tier >= 2 and random.random() < 0.15:
            cur_rr = int(current_player.battle_state.get("rerolls", 0) or 0)
            max_rr = 1 + min(2, int(current_player.battle_tree.get("echo_reroll", 0) or 0))
            max_rr = max(1, max_rr)
            if cur_rr < max_rr:
                current_player.battle_state["rerolls"] = min(max_rr, cur_rr + 1)
                mastery_perks.append({"id": "reroll_proc", "value": 1})
        if mastery_tier >= 3:
            dmg = float(player_combat.get("damage", 0.0) or 0.0)
            bonus = round(dmg * 0.10, 2)
            if bonus > 0:
                player_combat["damage"] = round(dmg + bonus, 2)
                enemy.hp = max(0.0, float(enemy.hp) - bonus)
                player_combat["enemy_hp"] = float(enemy.hp)
                player_combat["mastery_bonus_damage"] = bonus
                mastery_perks.append({"id": "apex_damage", "value": bonus})

    rolled_skill["mastery_gain_levels"] = int(mastery_gain.get("levels", 0) or 0)
    mastery_state = _battle_mastery_state(current_player, str(rolled_skill.get("id", "") or ""))
    rolled_skill["mastery"] = {
        "level": float(mastery_state.get("level", 1.0) or 1.0),
        "xp": float(mastery_state.get("xp", 0.0) or 0.0),
        "xp_to_next": float(mastery_state.get("xp_to_next", 100.0) or 100.0),
    }
    rolled_skill["mastery_tier"] = _battle_mastery_tier(float(mastery_state.get("level", 1.0) or 1.0))
    if str(rolled_skill.get("kind", "normal")) == "cursed":
        rolled_skill["mastery_perks"] = list(player_combat.get("mastery_perks", []))
    else:
        rolled_skill["mastery_perks"] = mastery_perks
    player_combat["skill_roll"] = rolled_skill
    if player_combat.get("error"):
        return {
            "error": player_combat["error"],
            "required": player_combat.get("required"),
            "current": player_combat.get("current"),
            "cooldown": player_combat.get("cooldown"),
            "resources": _combat_resources(current_player),
            "awaiting_enemy_phase": False,
            "state": session.state(current_player),
        }

    is_cursed = str(rolled_skill.get("kind", "normal")) == "cursed"
    if not is_cursed:
        _set_action_cooldown(current_player, action)
        _apply_combo_synergies(current_player, enemy, action, player_combat)
        _apply_enemy_archetype_reactions(current_player, enemy, action, player_combat)
        _apply_intent_counter(current_player, enemy, action, player_combat)
    _apply_room_affix_player_phase(current_player, enemy, player_combat)
    if not is_cursed:
        _apply_player_prayer_bonus(current_player, enemy, action, player_combat)

    rune_mods = _collect_rune_mods(current_player)
    if (not is_cursed) and action not in ("guard", "focus"):
        dmg = float(player_combat.get("damage", 0.0) or 0.0)
        atk_bonus = round(dmg * float(rune_mods.get("attack_mult", 0.0) or 0.0), 2)
        if atk_bonus > 0:
            player_combat["damage"] = round(dmg + atk_bonus, 2)
            enemy.hp = max(0.0, float(enemy.hp) - atk_bonus)
            player_combat["enemy_hp"] = float(enemy.hp)
            player_combat["rune_attack_bonus"] = atk_bonus

        lifesteal = float(rune_mods.get("lifesteal", 0.0) or 0.0)
        if lifesteal > 0:
            heal = round(float(player_combat.get("damage", 0.0) or 0.0) * lifesteal, 2)
            if heal > 0:
                current_player.hp = min(float(current_player.max_hp), float(current_player.hp) + heal)
                player_combat["rune_lifesteal_heal"] = heal

    player_combat["rune_mods"] = rune_mods

    player_dmg = float(player_combat.get("damage", 0.0) or 0.0)
    skill_name = str(rolled_skill.get("name", action) or action)
    mana_note = f"-{mana_cost} mana, {_combat_mana(current_player)}/{current_player.mana_cap}"
    if str(rolled_skill.get("kind", "normal")) == "cursed":
        session.add_log(f"You use cursed skill {skill_name} ({mana_note}).")
    elif action in ("guard", "focus"):
        session.add_log(f"You use {skill_name} [{action.upper()}] ({mana_note}).")
    else:
        session.add_log(
            f"You use {skill_name} [{action.upper()}] for {player_dmg} damage ({mana_note}). Enemy HP {max(round(enemy.hp, 1), 0)}."
        )

    if enemy.hp <= 0:
        session.SESSION["awaiting_enemy_attack"] = False
        session.SESSION["pending_player_action"] = ""
        result = _handle_enemy_defeat(enemy, player_combat)
        result["turn"] = {"player": player_combat, "enemy": None}
        result["awaiting_enemy_phase"] = False
        return result

    session.SESSION["awaiting_enemy_attack"] = True
    session.SESSION["pending_player_action"] = action
    return {
        "combat": player_combat,
        "turn": {"player": player_combat, "enemy": None},
        "resources": _combat_resources(current_player),
        "awaiting_enemy_phase": True,
        "state": session.state(current_player),
    }


def _run_enemy_phase(dodge_success: bool):
    enemy = session.current_enemy()
    if session.SESSION.get("active", False) and enemy is None and session.SESSION.get("can_leave", False):
        return {"error": "Boss defeated. Leave now to lock rewards and finish the run.", "can_leave": True, "state": session.state(current_player)}
    if not session.SESSION["active"] or enemy is None:
        return {"error": "No active dungeon. Start one with POST /dungeon/start"}

    if not session.SESSION.get("awaiting_enemy_attack", False):
        return {
            "error": "No pending enemy phase. Use player action first.",
            "awaiting_enemy_phase": False,
            "state": session.state(current_player),
        }

    if is_boss(enemy):
        _update_boss_run_state(enemy)
    enemy_combat = engine_enemy_attack(current_player, enemy, dodge_success=dodge_success)
    pressure = {}
    enemy_mods = getattr(enemy, "combat_mods", {}) or {}
    if isinstance(enemy_mods.get("room_pressure"), dict):
        pressure = dict(enemy_mods.get("room_pressure") or {})
    phase_bonus_mult = float(pressure.get("enemy_phase_bonus", 0.0) or 0.0)
    dodge_tax = float(pressure.get("dodge_tax", 0.0) or 0.0)
    if phase_bonus_mult > 0:
        raw = float(enemy_combat.get("damage", 0.0) or 0.0)
        scaled = raw * (1.0 + phase_bonus_mult)
        if dodge_success and dodge_tax > 0:
            scaled *= (1.0 + max(0.0, dodge_tax * 0.5))
        bonus = round(max(0.0, scaled - raw), 2)
        if bonus > 0:
            current_player.hp = max(0.0, float(current_player.hp) - bonus)
            enemy_combat["damage"] = round(raw + bonus, 2)
            enemy_combat["room_pressure_bonus"] = bonus
    if pressure:
        enemy_combat["room_pressure"] = pressure

    rune_mods = _collect_rune_mods(current_player)
    reduction = float(rune_mods.get("defense_mult", 0.0) or 0.0)
    if reduction > 0:
      raw = float(enemy_combat.get("damage", 0.0) or 0.0)
      reduced = round(raw * reduction, 2)
      if reduced > 0:
          enemy_combat["damage"] = round(max(0.0, raw - reduced), 2)
          current_player.hp = min(float(current_player.max_hp), float(current_player.hp) + reduced)
          enemy_combat["rune_damage_prevented"] = reduced

    thorns = float(rune_mods.get("thorns", 0.0) or 0.0)
    if thorns > 0:
      reflected = round(float(enemy_combat.get("damage", 0.0) or 0.0) * thorns, 2)
      if reflected > 0:
          enemy.hp = max(0.0, float(enemy.hp) - reflected)
          enemy_combat["rune_thorns_reflect"] = reflected
          enemy_combat["enemy_hp"] = float(enemy.hp)

    _apply_battle_defaults(current_player)
    iron_guard = int(current_player.battle_tree.get("iron_guard", 0) or 0)
    if iron_guard > 0:
        raw = float(enemy_combat.get("damage", 0.0) or 0.0)
        reduced = round(raw * min(0.30, iron_guard * 0.03), 2)
        if reduced > 0:
            enemy_combat["damage"] = round(max(0.0, raw - reduced), 2)
            current_player.hp = min(float(current_player.max_hp), float(current_player.hp) + reduced)
            enemy_combat["tree_damage_prevented"] = reduced

    enemy_combat["rune_mods"] = rune_mods

    _apply_enemy_archetype_turn_effects(current_player, enemy, enemy_combat)
    _apply_room_affix_enemy_phase(enemy_combat)

    if _has_modifier("boss_wrath") and str(getattr(enemy, "tier", "")).lower() == "boss":
        bonus = round(float(enemy_combat.get("damage", 0.0) or 0.0) * 0.25, 2)
        if bonus > 0:
            current_player.hp = max(0.0, float(current_player.hp) - bonus)
            enemy_combat["damage"] = round(float(enemy_combat.get("damage", 0.0) or 0.0) + bonus, 2)
            enemy_combat["boss_wrath_bonus"] = bonus

    pending_action = str(session.SESSION.get("pending_player_action", "") or "").lower()
    if _has_modifier("bleeding_floors") and pending_action not in ("guard", "focus"):
        bleed = 4 + session.SESSION["risk"]
        current_player.hp = max(0.0, float(current_player.hp) - bleed)
        enemy_combat["environment_damage"] = bleed
        session.add_log(f"Bleeding Floors deals {bleed} to player.")

    mana_regen = _gain_mana(current_player, MANA_REGEN_PER_TURN)
    enemy_combat["mana_regen"] = mana_regen
    enemy_combat["mana_after"] = _combat_mana(current_player)
    active_prayer = str(getattr(current_player, "active_prayer", "") or "")
    if active_prayer == "mystic_will" and _consume_prayer_runes(current_player, active_prayer):
        prayer_mana = _gain_mana(current_player, max(1, int(PRAYER_BOOK[active_prayer].get("value", 8)) // 2))
        enemy_combat["prayer_mana_boost"] = prayer_mana
    if is_boss(enemy):
        _update_boss_run_state(enemy)
    _seed_next_enemy_intent(enemy)
    enemy_combat["next_intent"] = getattr(enemy, "intent", None)
    attack_name = str(enemy_combat.get("attack_name", "Attack") or "Attack")
    dodge_note = "dodged, " if bool(enemy_combat.get("dodge_success", False)) else ""
    session.add_log(
        f"{enemy.name} uses {attack_name} for {enemy_combat.get('damage', 0)} damage ({dodge_note}your HP {round(float(current_player.hp), 1)}). +{mana_regen} mana."
    )

    session.SESSION["awaiting_enemy_attack"] = False
    session.SESSION["pending_player_action"] = ""
    if current_player.hp <= 0:
        session.add_log("Player died. Dungeon failed.")
        state = session.state(current_player)
        session.reset_session()
        return {
            "dead": True,
            "state": state,
            "combat": enemy_combat,
            "turn": {"player": None, "enemy": enemy_combat},
            "awaiting_enemy_phase": False,
        }

    return {
        "combat": enemy_combat,
        "turn": {"player": None, "enemy": enemy_combat},
        "resources": _combat_resources(current_player),
        "awaiting_enemy_phase": False,
        "state": session.state(current_player),
    }


@app.post("/combat/player_phase")
def player_phase(payload: dict):
    skill = str(payload.get("skill", "") or "").strip().lower()
    if not skill:
        skill = _skill_for_action(current_player, str(payload.get("action", "basic") or "basic"))
    return _run_player_phase(skill)


@app.post("/combat/enemy_phase")
def enemy_phase(payload: dict):
    dodge_success = bool(payload.get("dodge_success", False))
    return _run_enemy_phase(dodge_success)


@app.post("/combat/resolve_turn")
def resolve_turn(payload: dict):
    action = str(payload.get("action", "basic") or "basic").lower().strip()
    dodge_success = bool(payload.get("dodge_success", False))
    use_reroll = bool(payload.get("use_reroll", False))

    player_result = _run_player_phase(action, use_reroll=use_reroll)
    if player_result.get("error"):
        return player_result

    if not player_result.get("awaiting_enemy_phase", False):
        return player_result

    enemy_result = _run_enemy_phase(dodge_success)
    if enemy_result.get("error"):
        return enemy_result

    return {
        "combat": enemy_result.get("combat"),
        "turn": {"player": player_result.get("combat"), "enemy": enemy_result.get("combat")},
        "resources": enemy_result.get("resources", {}),
        "awaiting_enemy_phase": False,
        "state": enemy_result.get("state", session.state(current_player)),
    }


# -------------------------
# Auction
# -------------------------
@app.get("/auction")
def view_auctions():
    return get_auctions()


@app.get("/auction/mine")
def view_my_auctions():
    return {
        "account": _active_account(),
        "listings": get_auctions(seller=_active_account()),
        "history": get_auction_history(seller=_active_account()),
    }


@app.post("/auction/list")
def auction_list(item_index: int, price: int, allow_item_offers: bool = True):
    out = list_item(current_player, item_index, price, allow_item_offers=allow_item_offers, seller=_active_account())
    if not out.get("error"):
        _event_log_add(
            "market",
            "Auction listing created",
            f"Price {int(price)} gold",
            meta={"type": "item", "price": int(price)},
        )
    return out


@app.post("/auction/list_rune")
def auction_list_rune(payload: dict):
    rune_id = str(payload.get("rune_id", "") or "").strip()
    price = int(payload.get("price", 0) or 0)
    allow_item_offers = bool(payload.get("allow_item_offers", True))
    out = list_rune(current_player, rune_id, price, allow_item_offers=allow_item_offers, seller=_active_account())
    if not out.get("error"):
        _event_log_add(
            "market",
            "Rune listed on market",
            f"{rune_id} for {int(price)} gold",
            meta={"type": "rune", "rune_id": rune_id, "price": int(price)},
        )
    return out


@app.post("/auction/list_currency")
def auction_list_currency(payload: dict):
    currency_id = str(payload.get("currency_id", "") or "").strip()
    amount = int(payload.get("amount", 0) or 0)
    price = int(payload.get("price", 0) or 0)
    out = list_currency(current_player, currency_id, amount, price, seller=_active_account())
    if not out.get("error"):
        _persist_state()
        _event_log_add(
            "market",
            "Currency listed on market",
            f"{amount} × {currency_id} for {int(price)} gold",
            meta={"type": "currency", "currency_id": currency_id, "amount": amount, "price": int(price)},
        )
    return out


@app.get("/exchange/rates")
def exchange_rates():
    return {
        "base": BASE_CURRENCY,
        "rates": get_exchange_rates(),
        "currencies": {cid: dict(meta) for cid, meta in CURRENCIES.items()},
    }


@app.post("/auction/buy")
def auction_buy(auction_id: str):
    out = buy_item(current_player, auction_id, buyer=_active_account())
    if not out.get("error"):
        _event_log_add(
            "market",
            "Auction purchase",
            f"Paid {int(out.get('paid', 0) or 0)} gold",
            meta={"auction_id": auction_id, "paid": int(out.get("paid", 0) or 0)},
        )
    return out


@app.post("/auction/offer")
def auction_offer(payload: dict):
    auction_id = str(payload.get("auction_id", "") or "").strip()
    item_indices = payload.get("item_indices", [])
    if not auction_id:
        return {"error": "Missing auction_id"}
    out = offer_items(current_player, auction_id, item_indices, buyer=_active_account())
    if not out.get("error"):
        if out.get("accepted"):
            _event_log_add(
                "market",
                "Trade offer accepted",
                f"{int(out.get('offered_count', 0) or 0)} item(s) traded",
                severity="success",
                meta={"auction_id": auction_id, "accepted": True},
            )
        else:
            _event_log_add(
                "market",
                "Trade offer rejected",
                f"{int(out.get('offered_count', 0) or 0)} item(s) offered",
                severity="warn",
                meta={"auction_id": auction_id, "accepted": False},
            )
    return out


@app.post("/auction/cancel")
def auction_cancel(payload: dict):
    auction_id = str(payload.get("auction_id", "") or "").strip()
    if not auction_id:
        return {"error": "Missing auction_id"}
    out = cancel_listing(current_player, auction_id, seller=_active_account())
    if not out.get("error"):
        _event_log_add(
            "market",
            "Listing cancelled",
            f"{auction_id} returned to stash",
            meta={"auction_id": auction_id, "account": _active_account()},
        )
    return out


@app.get("/trade/requests")
def trade_requests_view():
    _expire_pending_trades()
    idx = _read_account_index()
    accounts = [
        acc for acc in sorted(list({_safe_account_name(x) for x in idx.get("accounts", []) if str(x).strip()}))
        if acc != _active_account()
    ]
    rows = trade_list_requests(_active_account())
    return {
        "account": _active_account(),
        "targets": accounts,
        "inbox": [_trade_request_summary(row) for row in rows.get("inbox", [])],
        "outbox": [_trade_request_summary(row) for row in rows.get("outbox", [])],
        "history": [_trade_request_summary(row) for row in rows.get("history", [])],
        "summary": dict(rows.get("summary", {}) or {}),
    }


@app.get("/trade/target-preview")
def trade_target_preview(account: str):
    _expire_pending_trades()
    target = _safe_account_name(str(account or ""))
    if not target or target == _active_account():
        return {"error": "Choose another account"}
    raw, player = _load_account_player(target)
    stash = list(getattr(player, "stash", []) or [])
    return {
        "account": target,
        "stash": [_snapshot_trade_item(item) for item in stash[:24]],
        "count": len(stash),
        "saved_at": int(raw.get("saved_at", 0) or 0),
    }


@app.post("/trade/request")
def trade_request_create(payload: dict):
    _expire_pending_trades()
    target = _safe_account_name(str(payload.get("target_account", "") or ""))
    note = str(payload.get("note", "") or "").strip()
    gold_offer = max(0, int(payload.get("gold_offer", 0) or 0))
    gold_request = max(0, int(payload.get("gold_request", 0) or 0))
    item_indices = payload.get("item_indices", [])
    requested_indices = payload.get("requested_indices", [])
    if not target or target == _active_account():
        return {"error": "Choose another account"}

    known_accounts = set(_safe_account_name(x) for x in _read_account_index().get("accounts", []))
    if target not in known_accounts and not os.path.exists(_state_file_for_account(target)):
        return {"error": "Target account not found"}

    if not isinstance(item_indices, list):
        item_indices = [item_indices]
    if not isinstance(requested_indices, list):
        requested_indices = [requested_indices]
    picked = []
    for raw_idx in item_indices:
        try:
            picked.append(int(raw_idx))
        except Exception:
            continue
    picked = list(dict.fromkeys(picked))
    requested = []
    for raw_idx in requested_indices:
        try:
            requested.append(int(raw_idx))
        except Exception:
            continue
    requested = list(dict.fromkeys(requested))
    invalid = [idx for idx in picked if idx < 0 or idx >= len(current_player.stash)]
    if invalid:
        return {"error": "Invalid stash index in trade request", "invalid": invalid}
    _, target_player = _load_account_player(target)
    target_stash = list(getattr(target_player, "stash", []) or [])
    invalid_requested = [idx for idx in requested if idx < 0 or idx >= len(target_stash)]
    if invalid_requested:
        return {"error": "Invalid target stash index in trade request", "invalid_requested": invalid_requested}
    if gold_offer > int(current_player.gold or 0):
        return {"error": "Not enough gold to escrow", "gold": int(current_player.gold or 0), "required": gold_offer}

    currency_offer = {str(k): int(v) for k, v in dict(payload.get("currency_offer", {}) or {}).items() if int(v or 0) > 0}
    currency_request = {str(k): int(v) for k, v in dict(payload.get("currency_request", {}) or {}).items() if int(v or 0) > 0}
    for cid in list(currency_offer) + list(currency_request):
        if not is_currency(cid):
            return {"error": f"Unknown currency '{cid}'"}
        if cid == BASE_CURRENCY:
            return {"error": "Use gold_offer/gold_request for gold"}
    for cid, amount in currency_offer.items():
        if currency_balance(current_player, cid) < amount:
            return {"error": f"Not enough {cid} to escrow", "required": amount,
                    "current": currency_balance(current_player, cid)}

    if not picked and gold_offer <= 0 and not requested and gold_request <= 0 and not currency_offer and not currency_request:
        return {"error": "Trade must offer or request something"}

    offered_items = [current_player.stash[idx] for idx in picked]
    offered_payloads = [(item.model_dump() if hasattr(item, "model_dump") else item.dict()) for item in offered_items]
    requested_payloads = [_snapshot_trade_item(target_stash[idx]) for idx in requested]
    for idx in sorted(picked, reverse=True):
        current_player.stash.pop(idx)
    if gold_offer > 0:
        current_player.gold = int(current_player.gold or 0) - gold_offer
    for cid, amount in currency_offer.items():
        spend_currency(current_player, cid, amount)

    row = trade_create_request(
        sender=_active_account(),
        target=target,
        item_payloads=offered_payloads,
        gold_offer=gold_offer,
        gold_request=gold_request,
        requested_items=requested_payloads,
        note=note,
        offered_currencies=currency_offer,
        requested_currencies=currency_request,
    )
    _persist_state()
    _event_log_add(
        "trade",
        "Trade request sent",
        f"To {target} • {len(offered_payloads)} item(s) • {gold_offer}g offered • {gold_request}g requested",
        meta={"trade_id": row.get("id", ""), "target": target},
    )
    return {"ok": True, "trade": _trade_request_summary(row)}


@app.post("/trade/request/cancel")
def trade_request_cancel(payload: dict):
    _expire_pending_trades()
    trade_id = str(payload.get("trade_id", "") or "").strip()
    row = trade_get_request(trade_id)
    if not row:
        return {"error": "Trade request not found"}
    if str(row.get("sender", "") or "") != _active_account():
        return {"error": "Only sender can cancel this trade"}
    if str(row.get("status", "pending") or "pending") != "pending":
        return {"error": "Trade request is no longer pending"}

    for item_payload in list(row.get("offered_items", []) or []):
        try:
            current_player.stash.append(_item_from_payload(item_payload))
        except Exception:
            continue
    current_player.gold = int(current_player.gold or 0) + int(row.get("gold_offer", 0) or 0)
    for cid, amount in dict(row.get("offered_currencies", {}) or {}).items():
        add_currency(current_player, cid, int(amount or 0))
    trade_update_request(trade_id, status="cancelled")
    _persist_state()
    _event_log_add("trade", "Trade request cancelled", trade_id, meta={"trade_id": trade_id})
    return {"ok": True, "trade_id": trade_id}


@app.post("/trade/request/decline")
def trade_request_decline(payload: dict):
    _expire_pending_trades()
    trade_id = str(payload.get("trade_id", "") or "").strip()
    row = trade_get_request(trade_id)
    if not row:
        return {"error": "Trade request not found"}
    if str(row.get("target", "") or "") != _active_account():
        return {"error": "Only recipient can decline this trade"}
    if str(row.get("status", "pending") or "pending") != "pending":
        return {"error": "Trade request is no longer pending"}

    sender = str(row.get("sender", "") or "")
    sender_raw, sender_player = _load_account_player(sender)
    for item_payload in list(row.get("offered_items", []) or []):
        try:
            sender_player.stash.append(_item_from_payload(item_payload))
        except Exception:
            continue
    sender_player.gold = int(sender_player.gold or 0) + int(row.get("gold_offer", 0) or 0)
    for cid, amount in dict(row.get("offered_currencies", {}) or {}).items():
        add_currency(sender_player, cid, int(amount or 0))
    _save_account_player(sender, sender_raw, sender_player)
    trade_update_request(trade_id, status="declined")
    _event_log_add("trade", "Trade request declined", trade_id, meta={"trade_id": trade_id, "sender": sender})
    return {"ok": True, "trade_id": trade_id}


@app.post("/trade/request/accept")
def trade_request_accept(payload: dict):
    _expire_pending_trades()
    trade_id = str(payload.get("trade_id", "") or "").strip()
    row = trade_get_request(trade_id)
    if not row:
        return {"error": "Trade request not found"}
    if str(row.get("target", "") or "") != _active_account():
        return {"error": "Only recipient can accept this trade"}
    if str(row.get("status", "pending") or "pending") != "pending":
        return {"error": "Trade request is no longer pending"}

    gold_request = int(row.get("gold_request", 0) or 0)
    if int(current_player.gold or 0) < gold_request:
        return {"error": "Not enough gold to accept trade", "required": gold_request, "gold": int(current_player.gold or 0)}
    requested_currencies = dict(row.get("requested_currencies", {}) or {})
    for cid, amount in requested_currencies.items():
        if currency_balance(current_player, cid) < int(amount or 0):
            return {"error": f"Not enough {cid} to accept trade", "required": int(amount or 0),
                    "current": currency_balance(current_player, cid)}

    sender = str(row.get("sender", "") or "")
    sender_raw, sender_player = _load_account_player(sender)
    requested_items = list(row.get("requested_items", []) or [])
    requested_matches: list[tuple[int, Item]] = []
    for snapshot in requested_items:
        found_idx = -1
        found_item = None
        for idx, item in enumerate(list(current_player.stash or [])):
            if idx in [x for x, _ in requested_matches]:
                continue
            if _item_matches_snapshot(item, snapshot):
                found_idx = idx
                found_item = item
                break
        if found_idx < 0 or found_item is None:
            return {"error": "Requested item is no longer available", "requested_item": snapshot}
        requested_matches.append((found_idx, found_item))
    current_player.gold = int(current_player.gold or 0) - gold_request + int(row.get("gold_offer", 0) or 0)
    sender_player.gold = int(sender_player.gold or 0) + gold_request
    for cid, amount in requested_currencies.items():
        spend_currency(current_player, cid, int(amount or 0))
        add_currency(sender_player, cid, int(amount or 0))
    for cid, amount in dict(row.get("offered_currencies", {}) or {}).items():
        add_currency(current_player, cid, int(amount or 0))
    for item_payload in list(row.get("offered_items", []) or []):
        try:
            current_player.stash.append(_item_from_payload(item_payload))
        except Exception:
            continue
    for _, item in requested_matches:
        sender_player.stash.append(item)
    for idx, _ in sorted(requested_matches, key=lambda x: x[0], reverse=True):
        current_player.stash.pop(idx)
    _save_account_player(sender, sender_raw, sender_player)
    trade_update_request(trade_id, status="accepted")
    _persist_state()
    _event_log_add(
        "trade",
        "Trade request accepted",
        f"{len(list(row.get('offered_items', []) or []))} item(s) received",
        severity="success",
        meta={"trade_id": trade_id, "sender": sender},
    )
    return {"ok": True, "trade_id": trade_id}
