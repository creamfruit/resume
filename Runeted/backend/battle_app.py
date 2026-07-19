"""Minimal API server for the rebuilt game's battle screen.

Serves the frontend_v2 battle screen and exposes the core battle loop.
This is the new game's entry point and deliberately stays thin: every
gameplay rule lives in backend/core, and every response the UI renders
is either battle state or the structured RoundEvent stream.

Run from backend/:  ..\\.venv\\Scripts\\python.exe -m uvicorn battle_app:app --port 8010
Legacy main.py and run.ps1 are untouched and still serve the old game.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.battle import Battle
from core.intent import ARCHETYPE_DECKS
from core.player_state import PlayerState
from core.runes import default_equipment, describe_rune
from core.skills import cooldown_of, default_loadout, describe_skill, stamina_cost_of
from core.stats import baseline_enemy

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_v2")

app = FastAPI(title="Runeted — battle screen")

# Single in-memory battle for now; sessions/accounts arrive in a later phase.
CURRENT: dict[str, Any] = {"battle": None}


class StartRequest(BaseModel):
    player_level: int = Field(default=1, ge=1, le=30)
    enemy_level: int = Field(default=1, ge=1, le=30)
    archetype: str = Field(default="brute")
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
        "budget": {
            "cap": battle.loadout.value_budget,
            "used": battle.loadout.total_value,
        },
        "rounds": battle.rounds,
    }


@app.post("/api/battle/start")
def start_battle(req: StartRequest) -> dict[str, Any]:
    archetype = req.archetype.lower()
    if archetype not in ARCHETYPE_DECKS:
        raise HTTPException(status_code=400, detail=f"Unknown archetype '{req.archetype}'")
    player = PlayerState(level=req.player_level)
    enemy = baseline_enemy(req.enemy_level, archetype=archetype)
    battle = Battle(player, enemy, loadout=default_loadout(), rng_seed=req.seed, auto=req.auto)
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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
