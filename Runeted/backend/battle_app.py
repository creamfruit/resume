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
from core.intent import ARCHETYPE_DECKS
from core.player_state import PlayerState
from core.runes import default_equipment, describe_rune
from core.skills import cooldown_of, default_loadout, describe_skill, stamina_cost_of
from core.stats import baseline_enemy

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_v2")

app = FastAPI(title="Runeted")

# Single in-memory session for now; accounts/persistence arrive in a
# later phase. The player is one persistent object for the process
# lifetime — battles read and write it directly, so level/HP/stamina
# carry over between fights and are never a client-supplied value.
CURRENT: dict[str, Any] = {"battle": None, "player": PlayerState()}


def _player() -> PlayerState:
    return CURRENT["player"]


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


def _state_payload(battle: Battle) -> dict[str, Any]:
    return {
        "outcome": battle.outcome.value,
        "finished": battle.finished,
        "round_no": battle.round_no,
        "auto": battle.auto,
        "telegraph": None if battle.finished else battle.telegraph(),
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
        },
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
    return {"event": event, "state": _state_payload(battle)}


@app.post("/api/battle/auto")
def set_auto(req: AutoRequest) -> dict[str, Any]:
    battle = _battle()
    battle.auto = bool(req.enabled)
    return _state_payload(battle)


@app.get("/api/player")
def get_player() -> dict[str, Any]:
    player = _player()
    return {
        "name": player.name,
        "level": player.level,
        "exp": player.exp,
        "exp_to_next": player.exp_to_next,
        "stat_points": player.stat_points,
    }


@app.get("/")
def home() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "home.html"))


@app.get("/battle")
def battle_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


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
