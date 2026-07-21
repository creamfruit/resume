"""The single system that generates and tracks enemy moves.

The enemy's move for the round is decided by the engine and resolved
immediately — it is never announced to the player ahead of time (that
"telegraph" design was dropped: once the specific next move is known a
round ahead, every fight becomes a solved puzzle of picking the exact
counter). What the player *can* see is the enemy's full move pool with
live cooldown state (`IntentTracker.movelist()`): a move just used is
briefly unavailable, so the player reasons about what the enemy could
plausibly do next, not what it will do. No other module may create or
mutate intents — the old codebase split this between boss_ai.py and
session.py and paid for it.

An intent's damage has two parts:
- contact_mult: the graze that always lands (scaled by attack, reduced
  by defense),
- effect_mult: the move's full effect, negated by a correct counter.

A response counters an intent when the responding skill's `counters`
tags intersect the intent's `countered_by` set (the enemy's archetype,
plus the intent kind so future content can counter e.g. all heavies).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

INTENT_LIBRARY: dict[str, dict[str, object]] = {
    "basic": {
        "name": "Measured Strike",
        "description": "A measured strike is coming.",
        "contact_mult": 0.7,
        "effect_mult": 0.5,
        "hits": 1,
        "stamina_cost": 1,
        "cooldown": 1,
    },
    "heavy": {
        "name": "Brutal Swing",
        "description": "A slow heavy blow is winding up.",
        "contact_mult": 0.7,
        "effect_mult": 1.4,
        "hits": 1,
        "stamina_cost": 3,
        "cooldown": 2,
    },
    "multi": {
        "name": "Rapid Combo",
        "description": "The enemy shifts into a rapid combo stance.",
        "contact_mult": 0.7,
        "effect_mult": 1.7,
        "hits": 3,
        "stamina_cost": 3,
        "cooldown": 3,
    },
    "guard_break": {
        "name": "Guard Break",
        "description": "A guard-breaking blow is being prepared.",
        "contact_mult": 0.8,
        "effect_mult": 1.2,
        "hits": 1,
        "stamina_cost": 2,
        "cooldown": 2,
    },
}

# Per-archetype move pools, carried over from the proven grammar in the
# reference inventory. Order defines display order (movelist) and, via
# repeated entries, historical flavor; selection itself is now
# cooldown/stamina-gated random choice among the distinct kinds, not a
# fixed cyclic read of this list.
ARCHETYPE_DECKS: dict[str, list[str]] = {
    "brute": ["heavy", "basic", "heavy", "multi"],
    "caster": ["basic", "guard_break", "multi", "basic"],
    "skirmisher": ["multi", "basic", "multi", "heavy"],
    "tank": ["guard_break", "basic", "heavy", "basic"],
    "summoner": ["basic", "multi", "guard_break", "basic"],
}
DEFAULT_ARCHETYPE = "brute"


@dataclass(frozen=True)
class Intent:
    kind: str
    name: str
    description: str
    contact_mult: float
    effect_mult: float
    hits: int
    stamina_cost: int
    countered_by: frozenset[str]
    # Set to "cooldown" or "stamina" when every pool move was unusable
    # and the enemy fell back to the cheapest move in the whole library
    # as an emergency legal-action guarantee (mirrors the player's
    # 0-cost recovery skill). None on a normal pick.
    downgraded_from: str | None = None


def build_intent(kind: str, archetype: str, downgraded_from: str | None = None) -> Intent:
    template = INTENT_LIBRARY.get(kind, INTENT_LIBRARY["basic"])
    return Intent(
        kind=kind,
        name=str(template["name"]),
        description=str(template["description"]),
        contact_mult=float(template["contact_mult"]),
        effect_mult=float(template["effect_mult"]),
        hits=int(template["hits"]),
        stamina_cost=int(template["stamina_cost"]),
        countered_by=frozenset({archetype, kind}),
        downgraded_from=downgraded_from,
    )


def cheapest_kind() -> str:
    return min(INTENT_LIBRARY, key=lambda k: (int(INTENT_LIBRARY[k]["stamina_cost"]), k != "basic"))


def _distinct_pool(archetype: str) -> list[str]:
    deck = ARCHETYPE_DECKS.get(archetype, ARCHETYPE_DECKS[DEFAULT_ARCHETYPE])
    pool: list[str] = []
    for kind in deck:
        if kind not in pool:
            pool.append(kind)
    return pool


class IntentTracker:
    """Owns move selection and per-move cooldowns for one battle.

    `current` is the move about to resolve this round -- decided by the
    engine, never exposed to the player before it resolves. `advance()`
    resolves it into history, puts it on cooldown, ticks every other
    cooldown down, and rolls the next one. The cooldown state lives
    here, not on the enemy.
    """

    def __init__(self, archetype: str, rng: random.Random | None = None, stamina_budget: float | None = None):
        self.archetype = str(archetype or DEFAULT_ARCHETYPE).lower()
        self._pool = _distinct_pool(self.archetype)
        self.rng = rng or random.Random()
        self._cooldowns: dict[str, int] = {}
        self.history: list[Intent] = []
        self.current: Intent = self._roll(stamina_budget)

    def remaining_cooldown(self, kind: str) -> int:
        return max(0, int(self._cooldowns.get(str(kind), 0)))

    def _roll(self, stamina_budget: float | None = None) -> Intent:
        off_cooldown = [k for k in self._pool if self.remaining_cooldown(k) == 0]
        if stamina_budget is None:
            legal = off_cooldown
        else:
            legal = [k for k in off_cooldown if int(INTENT_LIBRARY[k]["stamina_cost"]) <= stamina_budget]
        if legal:
            return build_intent(self.rng.choice(legal), self.archetype)
        # Emergency fallback: every pool move is either on cooldown or
        # unaffordable. Fall back to the cheapest move in the whole
        # library (ignoring cooldown/pool) so the enemy always has a
        # legal move this round.
        reason = "cooldown" if not off_cooldown else "stamina"
        return build_intent(cheapest_kind(), self.archetype, downgraded_from=reason)

    def advance(self, stamina_budget: float | None = None) -> Intent:
        """Resolve the current move into history, start its cooldown,
        tick every cooldown down by one (the round it started included,
        matching the player skill-cooldown timing), and roll the next
        move."""
        used = self.current
        self._cooldowns[used.kind] = int(INTENT_LIBRARY[used.kind]["cooldown"])
        for kind in list(self._cooldowns):
            self._cooldowns[kind] = max(0, self._cooldowns[kind] - 1)
            if self._cooldowns[kind] == 0:
                del self._cooldowns[kind]
        self.history.append(used)
        self.current = self._roll(stamina_budget)
        return self.current

    def movelist(self) -> list[dict[str, object]]:
        """The enemy's full move pool for display, each annotated with
        its live cooldown state -- what the player can actually reason
        about now that the specific next move is never announced in
        advance. A move with `remaining_cooldown` > 0 cannot be used
        this round."""
        return [
            {
                "kind": kind,
                "name": str(INTENT_LIBRARY[kind]["name"]),
                "description": str(INTENT_LIBRARY[kind]["description"]),
                "cooldown": int(INTENT_LIBRARY[kind]["cooldown"]),
                "remaining_cooldown": self.remaining_cooldown(kind),
            }
            for kind in self._pool
        ]


def is_counter(counter_tags: list[str] | tuple[str, ...] | frozenset[str], intent: Intent) -> bool:
    return bool(frozenset(str(t).lower() for t in counter_tags) & intent.countered_by)
