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
from core.special_events import EventOutcome, event_flavor, resolve_event, roll_encounter_kind, roll_event_type
from core.gauntlet import PendingPool, bank, forfeit, next_encounter_enemy, should_auto_bank
from core.intent import ARCHETYPE_DECKS
from core.loadout import LoadoutSelection
from core.player_state import ATTRIBUTES, PlayerState, victory_exp
from core.runes import catalog_runes, describe_rune, rune_by_id
from core.skills import catalog_skills, cooldown_of, describe_skill, skill_by_id, stamina_cost_of
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
        # The most recently rolled non-combat event (core/special_events.py),
        # for the dedicated event page to fetch after a fresh navigation --
        # holds whichever shape is current: an unresolved choice awaiting
        # engage/walk_away, or a resolved (engaged or walked-away) outcome.
        "event": None,
        # Set only while an event's choice is unresolved: the event type
        # plus the *same* seeded rng the encounter roll already started,
        # kept alive across requests so engaging draws the next value in
        # that one deterministic sequence rather than a fresh unseeded one.
        "pending_event": None,
        "pending_event_rng": None,
        # a queued shrine blessing, consumed the next time a Battle is built.
        "blessing": None,
        # What the Skills/Runes pages build and edit outside of battle;
        # every new Battle is built from this, so a loadout change here
        # is exactly what's active in the next fight (core/loadout.py).
        "loadout": LoadoutSelection(),
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


def _loadout() -> LoadoutSelection:
    return CURRENT["loadout"]


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
        "governing_stat": outcome.governing_stat,
        "resolved": True,
        "walked_away": False,
        "tier": outcome.tier,
        "gold_delta": outcome.gold_delta,
        "resource_id": outcome.resource_id,
        "resource_amount": outcome.resource_amount,
        "hp_loss_pct": outcome.hp_loss_pct,
        "chest_rarity": outcome.chest_rarity,
        "buff_rounds": outcome.buff_rounds,
        "buff_mult": outcome.buff_mult,
    }


# Fields every event payload carries whether or not it has resolved yet,
# so the frontend can render one shape at every stage instead of
# branching on which keys happen to be present.
_UNRESOLVED_EVENT_FIELDS: dict[str, Any] = {
    "tier": None, "gold_delta": 0, "resource_id": None, "resource_amount": 0,
    "hp_loss_pct": 0.0, "chest_rarity": None, "buff_rounds": 0, "buff_mult": 0.0,
}


def _queue_pending_event(event_type: str, rng: random.Random) -> dict[str, Any]:
    """Land on an event, but don't resolve it -- store the event type and
    the *same* seeded rng the encounter roll already started, so the
    player faces an explicit choice (POST /api/event/engage or
    /api/event/walk_away) before anything about the outcome is decided.
    Returns the unresolved payload the caller hands back to the client."""
    flavor = event_flavor(event_type)
    pending = {
        "type": event_type,
        "name": flavor["name"],
        "description": flavor["description"],
        "governing_stat": flavor["governing_stat"],
        "resolved": False,
        "walked_away": False,
        **_UNRESOLVED_EVENT_FIELDS,
    }
    CURRENT["pending_event"] = {"event_type": event_type}
    CURRENT["pending_event_rng"] = rng
    CURRENT["event"] = pending
    return pending


def _discard_stale_pending_event() -> None:
    """A fresh encounter roll always supersedes whatever choice the
    player hadn't made yet -- mirrors forfeiting a stale push-your-luck
    pool on a fresh start. Nothing resolves and nothing is granted or
    lost; the abandoned choice simply stops being reachable. Also
    clears the stale unresolved payload itself (unless the caller is
    about to immediately replace it with a new one via
    _queue_pending_event) so /api/event/state doesn't keep showing a
    choice that can no longer be acted on."""
    CURRENT["pending_event"] = None
    CURRENT["pending_event_rng"] = None
    stale = CURRENT.get("event")
    if stale is not None and not stale.get("resolved", True):
        CURRENT["event"] = None


def _apply_event_outcome(outcome: EventOutcome, player: PlayerState, wallet: Wallet) -> None:
    """Apply an engaged event's effects immediately -- events are a
    stand-alone, non-combat alternative to a fight, not a second
    at-risk reward pool, so this always lands straight on the player
    and wallet rather than going through the push-your-luck pending
    pool even when reached mid-run. Only ever called after the player
    has chosen to engage; walking away never reaches here."""
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
    for a fresh start). Returns ("event", event_type) or ("combat", Enemy).
    An event type is never resolved here -- resolving requires the
    player to choose to engage first (see _queue_pending_event)."""
    if roll_encounter_kind(rng) == "event":
        return "event", roll_event_type(rng)
    if continuation:
        return "combat", next_encounter_enemy(streak)
    return "combat", baseline_enemy(enemy_level, archetype=archetype)


def _next_gauntlet_encounter(
    player: PlayerState, streak: int, seed: int | None, *, auto: bool,
) -> tuple[str, Any]:
    """Roll and build the next push-your-luck encounter after a continue
    -- manual (the `/continue` endpoint below) or automatic (auto-battle's
    own bank-or-continue decision, `_maybe_auto_advance`). Returns
    `("event", pending_event_payload)` with `CURRENT["battle"]` left
    untouched (an event is never auto-resolved -- every event is an
    explicit choice, see core/special_events.py), or `("combat", the new
    Battle)` with `CURRENT["battle"]` already pointed at it."""
    rng = random.Random(seed)
    _discard_stale_pending_event()
    kind, payload = _roll_encounter(rng, continuation=True, streak=streak)
    if kind == "event":
        return "event", _queue_pending_event(payload, rng)
    battle = Battle(
        player, payload,
        loadout=_loadout().build_skill_loadout(),
        runes=_loadout().build_rune_equipment(),
        rng_seed=seed,
        auto=auto,
        initial_buffs=_consume_blessing(),
    )
    CURRENT["battle"] = battle
    return "combat", battle


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
            # The enemy's full move pool with live cooldown state -- the
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
    # unrelated fresh run. An unresolved event choice is abandoned the
    # same way -- it simply stops being reachable.
    forfeit(_pending())
    _discard_stale_pending_event()

    enemy_level = req.enemy_level if req.enemy_level is not None else player.level
    rng = random.Random(req.seed)
    kind, payload = _roll_encounter(rng, continuation=False, streak=0, enemy_level=enemy_level, archetype=archetype)

    if kind == "event":
        CURRENT["battle"] = None
        pending_event = _queue_pending_event(payload, rng)
        return {
            "kind": "event",
            "event": pending_event,
            "player": _player_payload(player),
            "wallet": wallet_payload(_wallet()),
            "push_luck": _push_luck_state_without_battle(),
        }

    battle = Battle(
        player, payload,
        loadout=_loadout().build_skill_loadout(),
        runes=_loadout().build_rune_equipment(),
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
    exp_result: dict[str, Any] | None = None
    auto_advance: dict[str, Any] | None = None
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
        # Auto-battle skips the manual bank/continue decision entirely --
        # see _maybe_auto_advance. No-op (returns the same battle, None)
        # when auto-battle is off.
        battle, auto_advance = _maybe_auto_advance(battle)
    elif event["outcome"] == "defeat" and not pending.is_empty():
        lost = forfeit(pending)
        push_luck_result = {"result": "forfeit", "lost": lost}

    response: dict[str, Any] = {"event": event, "state": _state_payload(battle)}
    if push_luck_result is not None:
        response["push_luck_result"] = push_luck_result
    if exp_result is not None:
        response["exp_result"] = exp_result
    if auto_advance is not None:
        response["auto_advance"] = auto_advance
    return response


def _require_victory_decision() -> Battle:
    battle = _battle()
    if not battle.finished or battle.outcome.value != "victory" or _pending().is_empty():
        raise HTTPException(status_code=409, detail="No push-your-luck decision pending.")
    return battle


def _maybe_auto_advance(battle: Battle) -> tuple[Battle, dict[str, Any] | None]:
    """Auto-battle's own answer to the push-your-luck decision: skip the
    manual bank/continue choice and make the call itself the moment a
    fight is won, rather than stopping the loop to wait for a click.

    Below `core.gauntlet.AUTO_BANK_HP_THRESHOLD` of max HP it banks the
    run outright -- continuing never heals (see continue_gauntlet's
    docstring below), so that's the real risk an unattended auto-battle
    would otherwise walk straight into a defeat over. Otherwise it
    continues into the next escalated encounter immediately. A
    non-combat event on that continuation roll is never auto-resolved
    (every event is its own explicit choice -- core/special_events.py);
    the caller's response flags it so the frontend can hand the player
    that choice instead of looping another round.

    Called right after a winning round, and again whenever auto-battle
    is switched on while a decision is already sitting unresolved (so
    turning auto on at a bank/continue prompt acts on it immediately
    instead of leaving it stuck until the next round). A no-op --
    `(battle, None)` -- whenever there's nothing to decide: auto is off,
    the battle isn't a just-finished victory, or the pool is empty."""
    pending = _pending()
    if not (battle.auto and battle.finished and battle.outcome.value == "victory" and not pending.is_empty()):
        return battle, None
    hp_pct = battle.player_hp / battle.stats.max_hp if battle.stats.max_hp else 0.0
    if should_auto_bank(hp_pct):
        banked = bank(pending, _wallet())
        CURRENT["battle"] = None
        return battle, {"action": "bank", "hp_pct": round(hp_pct, 4), "banked": banked}
    kind, result = _next_gauntlet_encounter(_player(), pending.streak, None, auto=True)
    if kind == "event":
        return battle, {"action": "event", "hp_pct": round(hp_pct, 4), "event": result}
    return result, {"action": "continue", "hp_pct": round(hp_pct, 4)}


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
    defeat) and starting a fresh battle from the hub heals to full.

    This is the manual half of the decision -- reachable when auto-battle
    is off, or when it auto-continued into an event and is waiting on
    that choice first. Auto-battle's own version of this same roll is
    `_maybe_auto_advance`, which fires straight from a winning round
    instead of waiting for this endpoint."""
    prior_battle = _require_victory_decision()
    player = _player()
    seed = req.seed if req is not None else None
    kind, result = _next_gauntlet_encounter(player, _pending().streak, seed, auto=False)

    if kind == "event":
        return {
            "kind": "event",
            "event": result,
            "player": _player_payload(player),
            "wallet": wallet_payload(_wallet()),
            "push_luck": _push_luck_payload(prior_battle),
        }

    return {"kind": "combat", **_state_payload(result)}


@app.get("/api/player/wallet")
def get_wallet() -> dict[str, Any]:
    return wallet_payload(_wallet())


@app.get("/api/event/state")
def event_state() -> dict[str, Any]:
    """The most recently rolled event, for the dedicated /event page to
    fetch after navigating there fresh (mirroring /api/battle/state).
    Reflects whichever stage is current: an unresolved choice awaiting
    engage/walk_away (`event.resolved == false`, so a page reload at
    the decision point still shows it, mirroring push_luck's pattern),
    or a resolved outcome (engaged or walked away) -- this is always a
    pure read, it never itself resolves anything."""
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


def _require_pending_event() -> dict[str, Any]:
    pending = CURRENT.get("pending_event")
    if pending is None:
        raise HTTPException(
            status_code=409,
            detail="No event choice pending. POST /api/battle/start or /continue first.",
        )
    return pending


def _event_choice_response(resolved_event: dict[str, Any]) -> dict[str, Any]:
    battle = CURRENT.get("battle")
    return {
        "event": resolved_event,
        "player": _player_payload(_player()),
        "wallet": wallet_payload(_wallet()),
        "push_luck": _push_luck_payload(battle) if battle is not None else _push_luck_state_without_battle(),
    }


@app.post("/api/event/engage")
def engage_event() -> dict[str, Any]:
    """The explicit choice to go through with a pending event -- opening
    the chest, approaching the shrine, trading with the merchant. Only
    now does the outcome tier actually roll, from the same seeded rng
    the encounter roll already started (never a fresh one), weighted by
    whichever single stat this event type is gated on
    (core/special_events.py::EVENT_GOVERNING_STAT)."""
    pending = _require_pending_event()
    rng = CURRENT.get("pending_event_rng")
    player = _player()
    outcome = resolve_event(pending["event_type"], player.charisma, player.luck, rng)
    _apply_event_outcome(outcome, player, _wallet())
    CURRENT["pending_event"] = None
    CURRENT["pending_event_rng"] = None
    CURRENT["event"] = _event_payload(outcome)
    return _event_choice_response(CURRENT["event"])


@app.post("/api/event/walk_away")
def walk_away_event() -> dict[str, Any]:
    """The explicit choice to decline a pending event -- nothing
    resolves, nothing is rolled, and nothing is granted or lost. This
    is the other half of every event's choice point: engaging is never
    the only option, and neither option is automatic."""
    pending = _require_pending_event()
    flavor = event_flavor(pending["event_type"])
    CURRENT["pending_event"] = None
    CURRENT["pending_event_rng"] = None
    CURRENT["event"] = {
        "type": pending["event_type"],
        "name": flavor["name"],
        "description": flavor["description"],
        "governing_stat": flavor["governing_stat"],
        "resolved": True,
        "walked_away": True,
        **_UNRESOLVED_EVENT_FIELDS,
    }
    return _event_choice_response(CURRENT["event"])


@app.post("/api/battle/auto")
def set_auto(req: AutoRequest) -> dict[str, Any]:
    battle = _battle()
    battle.auto = bool(req.enabled)
    # Switching auto on while a bank/continue decision is already
    # sitting unresolved (the player won manually, then flips auto on
    # instead of clicking) acts on it immediately -- see
    # _maybe_auto_advance. A no-op in every other case.
    battle, auto_advance = _maybe_auto_advance(battle)
    response = _state_payload(battle)
    if auto_advance is not None:
        response["auto_advance"] = auto_advance
    return response


def _player_progression_payload() -> dict[str, Any]:
    player = _player()
    return {
        "name": player.name,
        "level": player.level,
        "exp": player.exp,
        "exp_to_next": player.exp_to_next,
        "stat_points": player.stat_points,
        # Charisma is included here like every other attribute (it's a
        # real, allocatable stat) but combat never reads it -- it feeds
        # core/special_events.py instead. See core/player_state.py.
        "attributes": {stat: getattr(player, stat) for stat in ATTRIBUTES},
    }


@app.get("/api/player")
def get_player() -> dict[str, Any]:
    return _player_progression_payload()


class SpendStatRequest(BaseModel):
    stat: str
    amount: int = Field(default=1, ge=1)


@app.post("/api/player/spend_stat")
def spend_stat(req: SpendStatRequest) -> dict[str, Any]:
    if req.stat not in ATTRIBUTES:
        raise HTTPException(status_code=400, detail=f"Unknown stat '{req.stat}'")
    if not _player().spend_stat(req.stat, req.amount):
        raise HTTPException(status_code=400, detail="Not enough stat points")
    return _player_progression_payload()


# ---------- Skills page: build the loadout outside of battle ----------
#
# Reads and writes the exact same LoadoutSelection a battle is built
# from (_loadout()), so a change made here is what's active in the next
# fight -- there is no separate "saved build" to sync. Equip/unequip/
# swap enforce the loadout's value budget by literally building a
# SkillLoadout (core/loadout.py), the same object battle itself uses.

def _skill_dict(skill) -> dict[str, Any]:
    text = describe_skill(skill)
    return {
        "id": skill.id,
        "name": skill.name,
        "icon": skill.icon,
        "rarity": skill.rarity,
        "kind": skill.kind,
        "method": skill.method,
        "value": skill.value,
        "stamina_cost": stamina_cost_of(skill),
        "cooldown": cooldown_of(skill),
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
    }


def _skills_catalog_payload() -> dict[str, Any]:
    selection = _loadout()
    equipped_ids = {sid for sid in selection.skill_slots if sid is not None}
    catalog = []
    for skill in catalog_skills():
        entry = _skill_dict(skill)
        entry["equipped"] = skill.id in equipped_ids
        catalog.append(entry)
    slots = [
        {"index": i, "skill": _skill_dict(skill_by_id(sid)) if sid is not None else None}
        for i, sid in enumerate(selection.skill_slots)
    ]
    loadout = selection.build_skill_loadout()
    return {
        "slots": slots,
        "catalog": catalog,
        "budget": {
            "cap": loadout.value_budget,
            "used": loadout.total_value,
            "slots_cap": len(selection.skill_slots),
            "slots_used": len(loadout.skills),
        },
        "recommended_id": selection.recommended_skill_id(),
    }


@app.get("/api/skills")
def get_skills() -> dict[str, Any]:
    return _skills_catalog_payload()


class EquipSkillRequest(BaseModel):
    slot: int = Field(ge=0)
    skill_id: str


class SkillSlotRequest(BaseModel):
    slot: int = Field(ge=0)


class SwapSkillSlotsRequest(BaseModel):
    slot_a: int = Field(ge=0)
    slot_b: int = Field(ge=0)


@app.post("/api/skills/equip")
def equip_skill(req: EquipSkillRequest) -> dict[str, Any]:
    try:
        _loadout().equip_skill(req.slot, req.skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _skills_catalog_payload()


@app.post("/api/skills/unequip")
def unequip_skill(req: SkillSlotRequest) -> dict[str, Any]:
    try:
        _loadout().unequip_skill(req.slot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _skills_catalog_payload()


@app.post("/api/skills/swap")
def swap_skills(req: SwapSkillSlotsRequest) -> dict[str, Any]:
    try:
        _loadout().swap_skill_slots(req.slot_a, req.slot_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _skills_catalog_payload()


# ---------- Runes page: equip/unequip into the rune equipment ----------

def _rune_dict(rune) -> dict[str, Any]:
    text = describe_rune(rune)
    return {
        "id": rune.id,
        "name": rune.name,
        "icon": rune.icon,
        "type": rune.type,
        "rarity": rune.rarity,
        "cost": rune.cost,
        "description": rune.description,
        "short": text["short"],
        "full_text": text["full"],
    }


def _runes_catalog_payload() -> dict[str, Any]:
    selection = _loadout()
    equipped_ids = {rid for rid in selection.rune_slots if rid is not None}
    catalog = []
    for rune in catalog_runes():
        entry = _rune_dict(rune)
        entry["equipped"] = rune.id in equipped_ids
        catalog.append(entry)
    slots = [
        {"index": i, "rune": _rune_dict(rune_by_id(rid)) if rid is not None else None}
        for i, rid in enumerate(selection.rune_slots)
    ]
    equipment = selection.build_rune_equipment()
    return {
        "slots": slots,
        "catalog": catalog,
        "budget": {
            "cap": equipment.cost_budget,
            "used": equipment.total_cost,
            "slots_cap": len(selection.rune_slots),
            "slots_used": len(equipment.runes),
        },
        "recommended_id": selection.recommended_rune_id(),
    }


@app.get("/api/runes")
def get_runes() -> dict[str, Any]:
    return _runes_catalog_payload()


class EquipRuneRequest(BaseModel):
    slot: int = Field(ge=0)
    rune_id: str


class RuneSlotRequest(BaseModel):
    slot: int = Field(ge=0)


class SwapRuneSlotsRequest(BaseModel):
    slot_a: int = Field(ge=0)
    slot_b: int = Field(ge=0)


@app.post("/api/runes/equip")
def equip_rune(req: EquipRuneRequest) -> dict[str, Any]:
    try:
        _loadout().equip_rune(req.slot, req.rune_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _runes_catalog_payload()


@app.post("/api/runes/unequip")
def unequip_rune(req: RuneSlotRequest) -> dict[str, Any]:
    try:
        _loadout().unequip_rune(req.slot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _runes_catalog_payload()


@app.post("/api/runes/swap")
def swap_runes(req: SwapRuneSlotsRequest) -> dict[str, Any]:
    try:
        _loadout().swap_rune_slots(req.slot_a, req.slot_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _runes_catalog_payload()


_active_account_ctx: "contextvars.ContextVar[str]" = contextvars.ContextVar("active_account_ctx", default="")

# Paths reachable with no login: the page shells (their own JS calls the
# real /api/* endpoints below, which DO require a token, and redirects
# to /login on a 401), the auth endpoints that issue a token in the
# first place, and the static mount. The remaining placeholder pages
# (equipment, inventory, ...) are checked separately below since
# they're a single dynamic route, not a fixed path.
_PUBLIC_PATHS = {"/", "/battle", "/event", "/stats", "/skills", "/runes", "/login", "/auth/register", "/auth/login"}
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


@app.get("/stats")
def stats_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "stats.html"))


@app.get("/skills")
def skills_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "skills.html"))


@app.get("/runes")
def runes_page() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIR, "runes.html"))


# Sub-pages linked from the hub that aren't built yet — every entry
# point on the hub must lead somewhere real, even if "somewhere" is a
# placeholder until its phase arrives. One shared shell rather than six
# near-duplicate static files; each gets its own route the day it's
# actually built, which naturally shadows this fallback. Skills and
# Runes graduated out of this dict once their real pages landed.
PLACEHOLDER_PAGES: dict[str, str] = {
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
