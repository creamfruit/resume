"""Minimal API server for the rebuilt game's home hub and battle screen.

Serves the frontend_v2 pages and exposes the core battle loop. This is
the new game's entry point and deliberately stays thin: every gameplay
rule lives in backend/core, and every response the UI renders is either
battle state, player state, or the structured RoundEvent stream.

The home hub (`/`) is the persistent navigation surface outside of
battle; `/battle` is the battle screen itself, reachable only from the
hub's Start Battle action (or directly, which auto-starts one). Skills,
Runes, Equipment, Inventory, Market, and Currency Exchange are still
placeholder pages — their real screens are later phases — served by one
shared template rather than a battle start.

Run from backend/:  ..\\.venv\\Scripts\\python.exe -m uvicorn battle_app:app --port 8010
Legacy main.py and run.ps1 are untouched and still serve the old game.
"""
from __future__ import annotations

import os
import random
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.battle import Battle
from core.gauntlet import PendingPool, bank, forfeit, next_encounter_enemy
from core.intent import ARCHETYPE_DECKS
from core.player_state import ATTRIBUTES, PlayerState, victory_exp
from core.runes import default_equipment, describe_rune
from core.skills import cooldown_of, default_loadout, describe_skill, stamina_cost_of
from core.stats import baseline_enemy
from core.wallet import Wallet, wallet_payload
from services.chest import roll_guaranteed_reward

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_v2")

app = FastAPI(title="Runeted")

# Single in-memory session for now; accounts/persistence arrive in a
# later phase. The player is one persistent object for the process
# lifetime — battles read and write it directly, so level/HP/stamina
# carry over between fights and are never a client-supplied value.
# `wallet` is the persistent, banked economy; `pending` is the current
# push-your-luck run's unbanked pool (core/gauntlet.py) — reset to
# empty by every bank or forfeit, never by anything else.
CURRENT: dict[str, Any] = {
    "battle": None,
    "player": PlayerState(),
    "wallet": Wallet(),
    "pending": PendingPool(),
}


def _player() -> PlayerState:
    return CURRENT["player"]


def _wallet() -> Wallet:
    return CURRENT["wallet"]


def _pending() -> PendingPool:
    return CURRENT["pending"]


class StartRequest(BaseModel):
    """Every field is optional. A battle is always built from the
    persistent player's real level, never a client-supplied one — these
    overrides exist for deterministic tests, not for a debug UI."""
    enemy_level: int | None = Field(default=None, ge=1, le=30)
    archetype: str | None = None
    seed: int | None = None
    auto: bool = False


class RoundRequest(BaseModel):
    response: str | None = None


class AutoRequest(BaseModel):
    enabled: bool


def _battle() -> Battle:
    battle = CURRENT.get("battle")
    if battle is None:
        raise HTTPException(status_code=404, detail="No active battle. POST /api/battle/start first.")
    return battle


def _skills_payload(battle: Battle) -> list[dict[str, Any]]:
    # The base strike damage an attack skill's round deals (exposed and
    # buff bonuses vary round to round and are shown in the log instead).
    strike_damage = round(max(1.0, battle.stats.attack - battle.enemy_stats.defense), 2)
    payload = []
    for skill in battle.loadout.skills.values():
        text = describe_skill(skill)
        cost = stamina_cost_of(skill)
        payload.append({
            "id": skill.id,
            "name": skill.name,
            "icon": skill.icon,  # icon id; the frontend maps ids to glyphs
            "kind": skill.kind,
            "method": skill.method,
            "damage": strike_damage if skill.kind == "attack" else 0,
            "stamina_cost": cost,
            "cooldown": cooldown_of(skill),
            "remaining_cooldown": battle.loadout.remaining_cooldown(skill.id),
            "usable": (
                not battle.finished
                and battle.loadout.can_use(skill.id)
                and cost <= battle.player_stamina
            ),
            "counters": sorted(skill.counters),
            "applies_status": (
                {
                    "status": skill.applies_status.status,
                    "duration": skill.applies_status.duration,
                    "detail": skill.applies_status.detail,
                }
                if skill.applies_status
                else None
            ),
            "description": text["short"],
            "full_text": text["full"],
        })
    return payload


def _runes_payload(battle: Battle) -> dict[str, Any]:
    equipped = []
    for rune in battle.runes.runes.values():
        text = describe_rune(rune)
        equipped.append({
            "id": rune.id,
            "name": rune.name,
            "icon": rune.icon,  # icon id; the frontend maps ids to glyphs
            "type": rune.type,
            "rarity": rune.rarity,
            "cost": rune.cost,
            "description": rune.description,
            "short": text["short"],
            "full_text": text["full"],
        })
    return {
        "equipped": equipped,
        "slots": battle.runes.slots,
        "cost_cap": battle.runes.cost_budget,
        "cost_used": battle.runes.total_cost,
    }


def _push_luck_payload(battle: Battle) -> dict[str, Any]:
    pending = _pending()
    at_decision = battle.finished and battle.outcome.value == "victory" and not pending.is_empty()
    return {
        "pending": pending.summary(),
        "can_bank": at_decision,
        "can_continue": at_decision,
    }


def _state_payload(battle: Battle) -> dict[str, Any]:
    return {
        "outcome": battle.outcome.value,
        "finished": battle.finished,
        "round_no": battle.round_no,
        "auto": battle.auto,
        "player": {
            "name": battle.player.name,
            "level": battle.player.level,
            "hp": battle.player_hp,
            "max_hp": battle.stats.max_hp,
            "stamina": battle.player_stamina,
            "max_stamina": battle.stats.max_stamina,
        },
        "enemy": {
            "name": getattr(battle.enemy, "name", "Enemy"),
            "level": getattr(battle.enemy, "level", 1),
            "archetype": getattr(battle.enemy, "archetype", "brute"),
            "hp": battle.enemy_hp,
            "max_hp": battle.enemy_stats.max_hp,
            "stamina": battle.enemy_stamina,
            "max_stamina": battle.enemy_stats.max_stamina,
            # The enemy's full move pool with live cooldown state — the
            # only view the player gets into what it might do next, now
            # that the specific upcoming move is never revealed ahead
            # of time. A move with remaining_cooldown > 0 is unusable.
            "moves": battle.movelist(),
        },
        "push_luck": _push_luck_payload(battle),
        "skills": _skills_payload(battle),
        "runes": _runes_payload(battle),
        "budget": {
            "cap": battle.loadout.value_budget,
            "used": battle.loadout.total_value,
        },
        "rounds": battle.rounds,
    }


@app.post("/api/battle/start")
def start_battle(req: StartRequest) -> dict[str, Any]:
    archetype = (req.archetype or random.choice(list(ARCHETYPE_DECKS))).lower()
    if archetype not in ARCHETYPE_DECKS:
        raise HTTPException(status_code=400, detail=f"Unknown archetype '{req.archetype}'")
    player = _player()
    player.heal_full()  # every fresh engagement starts fully rested
    # Starting a brand new encounter from the hub abandons any unresolved
    # push-your-luck decision the same way walking away without banking
    # would — the pool is forfeited, never silently carried into an
    # unrelated fresh run.
    forfeit(_pending())
    enemy_level = req.enemy_level if req.enemy_level is not None else player.level
    enemy = baseline_enemy(enemy_level, archetype=archetype)
    battle = Battle(
        player, enemy,
        loadout=default_loadout(),
        runes=default_equipment(),
        rng_seed=req.seed,
        auto=req.auto,
    )
    CURRENT["battle"] = battle
    return _state_payload(battle)


@app.get("/api/battle/state")
def battle_state() -> dict[str, Any]:
    return _state_payload(_battle())


@app.post("/api/battle/round")
def play_round(req: RoundRequest) -> dict[str, Any]:
    battle = _battle()
    try:
        event = battle.play_round(req.response)
    except ValueError as exc:  # unknown skill, cooldown, or not enough stamina
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:  # battle already resolved
        raise HTTPException(status_code=409, detail=str(exc))

    pending = _pending()
    push_luck_result: dict[str, Any] | None = None
    exp_result: dict[str, Any] | None = None
    if event["outcome"] == "victory":
        # A win is always worth something -- the pending pool only ever
        # grows on a win, and the choice next (bank vs. push on) is only
        # meaningful if there's something real riding on it.
        reward = roll_guaranteed_reward(battle.enemy)
        pending.add_win(reward)
        push_luck_result = {"result": "win", "reward": reward, "pending": pending.summary()}

        player = _player()
        exp_gained = victory_exp(getattr(battle.enemy, "level", 1))
        # gain_exp() heals to full on every level-up -- correct for that
        # method in general, but a battle victory must never grant a
        # free heal: that would undercut the very risk that continuing
        # without healing exists to create (see continue_gauntlet's
        # docstring). Restore whatever HP/stamina the battle itself just
        # wrote back before the level-up touched it.
        hp_before, stamina_before = player.hp, player.stamina
        levels_gained = player.gain_exp(exp_gained)
        if levels_gained > 0:
            player.hp = hp_before
            player.stamina = stamina_before
        exp_result = {
            "exp_gained": exp_gained,
            "levels_gained": levels_gained,
            "leveled_up": levels_gained > 0,
            "stat_points": player.stat_points,
        }
    elif event["outcome"] == "defeat" and not pending.is_empty():
        lost = forfeit(pending)
        push_luck_result = {"result": "forfeit", "lost": lost}

    response: dict[str, Any] = {"event": event, "state": _state_payload(battle)}
    if push_luck_result is not None:
        response["push_luck_result"] = push_luck_result
    if exp_result is not None:
        response["exp_result"] = exp_result
    return response


def _require_victory_decision() -> Battle:
    battle = _battle()
    if not battle.finished or battle.outcome.value != "victory" or _pending().is_empty():
        raise HTTPException(status_code=409, detail="No push-your-luck decision pending.")
    return battle


@app.post("/api/battle/bank")
def bank_pending() -> dict[str, Any]:
    """Exit the run: commit the entire pending pool into the wallet and
    close out the battle. Whatever was banked here stays banked even if
    a later run is lost outright."""
    _require_victory_decision()
    banked = bank(_pending(), _wallet())
    CURRENT["battle"] = None
    return {"banked": banked, "wallet": wallet_payload(_wallet())}


@app.post("/api/battle/continue")
def continue_gauntlet() -> dict[str, Any]:
    """Push on: the pending pool stays at risk, and the next encounter
    is generated harder (core/gauntlet.py's escalation curve over the
    enemy-variety/modifier system) than a fresh hub-started fight.

    Deliberately does NOT heal the player. `Battle` picks up whatever HP
    and stamina the just-finished battle wrote back to `player` — this
    is what makes "continue" a real risk instead of a free reroll of a
    harder fight at full health. Only ending the run (a bank, or a
    defeat) and starting a fresh battle from the hub heals to full."""
    _require_victory_decision()
    player = _player()
    enemy = next_encounter_enemy(_pending().streak)
    battle = Battle(player, enemy, loadout=default_loadout(), runes=default_equipment())
    CURRENT["battle"] = battle
    return _state_payload(battle)


@app.get("/api/player/wallet")
def get_wallet() -> dict[str, Any]:
    return wallet_payload(_wallet())


@app.post("/api/battle/auto")
def set_auto(req: AutoRequest) -> dict[str, Any]:
    battle = _battle()
    battle.auto = bool(req.enabled)
    return _state_payload(battle)


def _player_payload() -> dict[str, Any]:
    player = _player()
    return {
        "name": player.name,
        "level": player.level,
        "exp": player.exp,
        "exp_to_next": player.exp_to_next,
        "stat_points": player.stat_points,
        # Charisma is included here like every other attribute (it's a
        # real, allocatable stat) but combat never reads it — see
        # core/player_state.py's module docstring.
        "attributes": {stat: getattr(player, stat) for stat in ATTRIBUTES},
    }


@app.get("/api/player")
def get_player() -> dict[str, Any]:
    return _player_payload()


class SpendStatRequest(BaseModel):
    stat: str
    amount: int = Field(default=1, ge=1)


@app.post("/api/player/spend_stat")
def spend_stat(req: SpendStatRequest) -> dict[str, Any]:
    if req.stat not in ATTRIBUTES:
        raise HTTPException(status_code=400, detail=f"Unknown stat '{req.stat}'")
    if not _player().spend_stat(req.stat, req.amount):
        raise HTTPException(status_code=400, detail="Not enough stat points")
    return _player_payload()


@app.get("/")
def home() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "home.html"))


@app.get("/battle")
def battle_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/stats")
def stats_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "stats.html"))


# Sub-pages linked from the hub that aren't built yet — every entry
# point on the hub must lead somewhere real, even if "somewhere" is a
# placeholder until its phase arrives. One shared shell rather than six
# near-duplicate static files; each gets its own route the day it's
# actually built, which naturally shadows this fallback.
PLACEHOLDER_PAGES: dict[str, str] = {
    "skills": "Skills",
    "runes": "Runes",
    "equipment": "Equipment",
    "inventory": "Inventory",
    "market": "Market",
    "exchange": "Currency Exchange",
}

_PLACEHOLDER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Runeted — {title}</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header class="site-header">
    <a class="site-home-link" href="/">🏠 Runeted</a>
  </header>
  <main class="placeholder-page">
    <h1>{title}</h1>
    <p class="muted">This part of Runeted isn't built yet — check back in a later phase.</p>
    <a class="placeholder-back" href="/">← Back to the hub</a>
  </main>
</body>
</html>
"""


@app.get("/{slug}")
def placeholder_page(slug: str) -> HTMLResponse:
    title = PLACEHOLDER_PAGES.get(slug)
    if title is None:
        raise HTTPException(status_code=404, detail="Not found")
    return HTMLResponse(_PLACEHOLDER_HTML.format(title=title))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
