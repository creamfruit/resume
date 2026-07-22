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

import contextvars
import os
import random
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.battle import Battle
from core.special_events import EventOutcome, resolve_event, roll_encounter_kind, roll_event_type
from core.gauntlet import PendingPool, bank, forfeit, next_encounter_enemy
from core.intent import ARCHETYPE_DECKS, known_moves
from core.player_state import PlayerState
from core.runes import default_equipment, describe_rune
from core.skills import cooldown_of, default_loadout, describe_skill, stamina_cost_of
from core.stats import baseline_enemy, compute_player_stats
from core.wallet import Wallet, wallet_payload
from services import auth
from services.chest import grant_chest, roll_guaranteed_reward
from services.currency import add_currency
from services.request_scope import ContextDictProxy

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_v2")

app = FastAPI(title="Runeted")


def _fresh_session_bundle() -> dict[str, Any]:
    """One account's live battle-screen state: the player is one
    persistent object for as long as the account is logged in this
    process — battles read and write it directly, so level/HP/stamina
    carry over between fights and are never a client-supplied value.
    `wallet` is the persistent, banked economy; `pending` is the
    current push-your-luck run's unbanked pool (core/gauntlet.py) —
    reset to empty by every bank or forfeit, never by anything else."""
    return {
        "battle": None,
        "player": PlayerState(),
        "wallet": Wallet(),
        "pending": PendingPool(),
        # The most recently resolved non-combat event (core/special_events.py),
        # for the dedicated event page to fetch after a fresh navigation;
        # a queued shrine blessing, consumed the next time a Battle is built.
        "event": None,
        "blessing": None,
    }


# One bundle per account, not one global — resolved per authenticated
# request by the auth middleware below via a ContextVar (see
# services/request_scope.py for why: Starlette dispatches sync `def`
# routes to a real threadpool, so two accounts' requests can genuinely
# run concurrently, and a naive "reassign the global" swap would race).
# `CURRENT` keeps behaving like a single live dict to the handful of
# existing `CURRENT["x"]` call sites below — none of them needed to
# change, only this declaration.
_session_ctx: "contextvars.ContextVar[dict[str, Any]]" = contextvars.ContextVar(
    "session_ctx", default=_fresh_session_bundle()
)
CURRENT: dict[str, Any] = ContextDictProxy(_session_ctx)  # type: ignore[assignment]

# One cached bundle per account for the process lifetime — populated the
# first time each account is seen, then reused every later request for
# that account (same effective behavior as the old single global, just
# one per account). Tests reach into this directly (see tests/test_*.py's
# `client()` helpers) to set up/inspect a specific account's state
# without needing a live request in flight.
_ACCOUNT_CACHE: dict[str, dict[str, Any]] = {}


def _get_or_create_bundle(account_id: str) -> dict[str, Any]:
    bundle = _ACCOUNT_CACHE.get(account_id)
    if bundle is None:
        bundle = _fresh_session_bundle()
        _ACCOUNT_CACHE[account_id] = bundle
    return bundle


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


class ContinueRequest(BaseModel):
    """Optional body: only `seed` exists, for deterministic tests of the
    encounter roll below -- real play never supplies one."""
    seed: int | None = None


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


def _push_luck_state_without_battle() -> dict[str, Any]:
    # A fresh hub start never has a pending run to decide on -- any stale
    # one was just forfeited above, so there's nothing to bank/continue.
    return {"pending": _pending().summary(), "can_bank": False, "can_continue": False}


def _player_payload(player: PlayerState) -> dict[str, Any]:
    stats = compute_player_stats(player)
    hp = stats.max_hp if player.hp is None else float(player.hp)
    stamina = stats.max_stamina if player.stamina is None else float(player.stamina)
    return {
        "name": player.name,
        "level": player.level,
        "hp": round(hp, 2),
        "max_hp": stats.max_hp,
        "stamina": round(stamina, 2),
        "max_stamina": stats.max_stamina,
    }


def _event_payload(outcome: EventOutcome) -> dict[str, Any]:
    return {
        "type": outcome.event_type,
        "name": outcome.name,
        "description": outcome.description,
        "tier": outcome.tier,
        "gold_delta": outcome.gold_delta,
        "resource_id": outcome.resource_id,
        "resource_amount": outcome.resource_amount,
        "hp_loss_pct": outcome.hp_loss_pct,
        "chest_rarity": outcome.chest_rarity,
        "buff_rounds": outcome.buff_rounds,
        "buff_mult": outcome.buff_mult,
    }


def _apply_event_outcome(outcome: EventOutcome, player: PlayerState, wallet: Wallet) -> None:
    """Apply a resolved event's effects immediately -- events are a
    stand-alone, non-combat alternative to a fight, not a second
    at-risk reward pool, so this always lands straight on the player
    and wallet rather than going through the push-your-luck pending
    pool even when reached mid-run."""
    if outcome.gold_delta:
        add_currency(wallet, "gold", outcome.gold_delta)
    if outcome.resource_id and outcome.resource_amount:
        add_currency(wallet, outcome.resource_id, outcome.resource_amount)
    if outcome.chest_rarity:
        grant_chest(wallet, outcome.chest_rarity)
    if outcome.hp_loss_pct > 0:
        stats = compute_player_stats(player)
        current_hp = stats.max_hp if player.hp is None else float(player.hp)
        loss = stats.max_hp * outcome.hp_loss_pct
        # Never fatal outside combat -- there's no fight to show why.
        player.hp = round(max(1.0, current_hp - loss), 2)
    if outcome.buff_rounds > 0 and outcome.buff_mult > 0:
        CURRENT["blessing"] = {
            "status": "blessed",
            "attack_mult": outcome.buff_mult,
            "rounds_left": outcome.buff_rounds,
        }


def _consume_blessing() -> list[dict[str, Any]] | None:
    blessing = CURRENT.get("blessing")
    CURRENT["blessing"] = None
    return [blessing] if blessing is not None else None


def _roll_encounter(
    rng: random.Random, *, continuation: bool, streak: int,
    enemy_level: int | None = None, archetype: str | None = None,
) -> tuple[str, Any]:
    """The shared encounter-generation gate every encounter passes
    through -- a fresh hub start or a push-your-luck continuation
    alike -- before falling back to whichever enemy generator the
    caller would otherwise have used (engine/enemy_factory.py's
    enemy-variety system for a continuation, the plain per-level curve
    for a fresh start). Returns ("event", EventOutcome) or ("combat", Enemy)."""
    if roll_encounter_kind(rng) == "event":
        event_type = roll_event_type(rng)
        player = _player()
        outcome = resolve_event(event_type, player.charisma, player.luck, rng)
        return "event", outcome
    if continuation:
        return "combat", next_encounter_enemy(streak)
    return "combat", baseline_enemy(enemy_level, archetype=archetype)


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
            # The enemy's full move pool, for reference — separate from
            # "telegraph" above, which is only the specific move coming
            # up next round.
            "moves": known_moves(getattr(battle.enemy, "archetype", "brute")),
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
    rng = random.Random(req.seed)
    kind, payload = _roll_encounter(rng, continuation=False, streak=0, enemy_level=enemy_level, archetype=archetype)

    if kind == "event":
        _apply_event_outcome(payload, player, _wallet())
        CURRENT["battle"] = None
        CURRENT["event"] = _event_payload(payload)
        return {
            "kind": "event",
            "event": CURRENT["event"],
            "player": _player_payload(player),
            "wallet": wallet_payload(_wallet()),
            "push_luck": _push_luck_state_without_battle(),
        }

    battle = Battle(
        player, payload,
        loadout=default_loadout(),
        runes=default_equipment(),
        rng_seed=req.seed,
        auto=req.auto,
        initial_buffs=_consume_blessing(),
    )
    CURRENT["battle"] = battle
    return {"kind": "combat", **_state_payload(battle)}


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
    if event["outcome"] == "victory":
        # A win is always worth something -- the pending pool only ever
        # grows on a win, and the choice next (bank vs. push on) is only
        # meaningful if there's something real riding on it.
        reward = roll_guaranteed_reward(battle.enemy)
        pending.add_win(reward)
        push_luck_result = {"result": "win", "reward": reward, "pending": pending.summary()}
    elif event["outcome"] == "defeat" and not pending.is_empty():
        lost = forfeit(pending)
        push_luck_result = {"result": "forfeit", "lost": lost}

    response: dict[str, Any] = {"event": event, "state": _state_payload(battle)}
    if push_luck_result is not None:
        response["push_luck_result"] = push_luck_result
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
def continue_gauntlet(req: ContinueRequest | None = None) -> dict[str, Any]:
    """Push on: the pending pool stays at risk, and the next encounter
    is generated harder (core/gauntlet.py's escalation curve over the
    enemy-variety/modifier system) than a fresh hub-started fight --
    unless the encounter roll below lands on a non-combat event instead,
    in which case the event resolves immediately and the *same*
    finished, victorious battle stays in place, so the player lands
    back on the same bank/continue decision afterward.

    Deliberately does NOT heal the player. `Battle` picks up whatever HP
    and stamina the just-finished battle wrote back to `player` — this
    is what makes "continue" a real risk instead of a free reroll of a
    harder fight at full health. Only ending the run (a bank, or a
    defeat) and starting a fresh battle from the hub heals to full."""
    prior_battle = _require_victory_decision()
    player = _player()
    seed = req.seed if req is not None else None
    rng = random.Random(seed)
    streak = _pending().streak
    kind, payload = _roll_encounter(rng, continuation=True, streak=streak)

    if kind == "event":
        _apply_event_outcome(payload, player, _wallet())
        CURRENT["event"] = _event_payload(payload)
        return {
            "kind": "event",
            "event": CURRENT["event"],
            "player": _player_payload(player),
            "wallet": wallet_payload(_wallet()),
            "push_luck": _push_luck_payload(prior_battle),
        }

    battle = Battle(
        player, payload,
        loadout=default_loadout(),
        runes=default_equipment(),
        rng_seed=seed,
        initial_buffs=_consume_blessing(),
    )
    CURRENT["battle"] = battle
    return {"kind": "combat", **_state_payload(battle)}


@app.get("/api/player/wallet")
def get_wallet() -> dict[str, Any]:
    return wallet_payload(_wallet())


@app.get("/api/event/state")
def event_state() -> dict[str, Any]:
    """The most recently resolved event, for the dedicated /event page to
    fetch after navigating there fresh (mirroring /api/battle/state).
    Events resolve synchronously inside start/continue, so there is
    nothing left to "resolve" here -- this is a pure read."""
    event = CURRENT.get("event")
    if event is None:
        raise HTTPException(status_code=404, detail="No event to show. POST /api/battle/start or /continue first.")
    player = _player()
    battle = CURRENT.get("battle")
    return {
        "event": event,
        "player": _player_payload(player),
        "wallet": wallet_payload(_wallet()),
        "push_luck": _push_luck_payload(battle) if battle is not None else _push_luck_state_without_battle(),
    }


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


_active_account_ctx: "contextvars.ContextVar[str]" = contextvars.ContextVar("active_account_ctx", default="")

# Paths reachable with no login: the page shells (their own JS calls the
# real /api/* endpoints below, which DO require a token, and redirects
# to /login on a 401), the auth endpoints that issue a token in the
# first place, and the static mount. The placeholder pages (skills,
# runes, ...) are checked separately below since they're a single
# dynamic route, not a fixed path.
_PUBLIC_PATHS = {"/", "/battle", "/event", "/login", "/auth/register", "/auth/login"}
_PUBLIC_PREFIXES = ("/static/",)


def _is_public_path(path: str) -> bool:
    if path in _PUBLIC_PATHS or path.startswith(_PUBLIC_PREFIXES):
        return True
    return path.lstrip("/") in PLACEHOLDER_PAGES  # no game data on these, just a "not built yet" shell


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):
    if _is_public_path(request.url.path):
        return await call_next(request)

    token = auth.token_from_authorization_header(request.headers.get("authorization"))
    account_id = auth.verify_token(token) if token else None
    if account_id is None:
        return JSONResponse({"error": "Not authenticated. Log in first (POST /auth/login)."}, status_code=401)

    bundle = _get_or_create_bundle(account_id)
    ctx_tokens = [_session_ctx.set(bundle), _active_account_ctx.set(account_id)]
    try:
        return await call_next(request)
    finally:
        for ctx_token in reversed(ctx_tokens):
            ctx_token.var.reset(ctx_token)


@app.post("/auth/register")
def auth_register(payload: dict) -> dict[str, Any]:
    username = str(payload.get("username", "") or "")
    password = str(payload.get("password", "") or "")
    try:
        account_id = auth.register(username, password)
    except auth.AuthError as e:
        return {"error": str(e)}
    return {"ok": True, "account": account_id, "token": auth.issue_token(account_id)}


@app.post("/auth/login")
def auth_login(payload: dict) -> dict[str, Any]:
    username = str(payload.get("username", "") or "")
    password = str(payload.get("password", "") or "")
    try:
        account_id = auth.verify_login(username, password)
    except auth.AuthError as e:
        return {"error": str(e)}
    return {"ok": True, "account": account_id, "token": auth.issue_token(account_id)}


@app.get("/auth/me")
def auth_me() -> dict[str, Any]:
    return {"account": _active_account_ctx.get()}


@app.get("/login")
def login_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))


@app.get("/")
def home() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "home.html"))


@app.get("/battle")
def battle_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/event")
def event_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "event.html"))


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
