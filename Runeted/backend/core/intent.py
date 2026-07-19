"""The single system that generates and tracks enemy intent/telegraphs.

Every enemy move is announced one round ahead: the tracker's current
intent is what the enemy will do this round, visible before the player
acts. No other module may create or mutate intents — the old codebase
split this between boss_ai.py and session.py and paid for it.

An intent's damage has two parts:
- contact_mult: the graze that always lands (scaled by attack, reduced
  by defense),
- effect_mult: the telegraphed effect, fully negated by a correct
  counter response.

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
    },
    "heavy": {
        "name": "Brutal Swing",
        "description": "A slow heavy blow is winding up.",
        "contact_mult": 0.7,
        "effect_mult": 1.4,
        "hits": 1,
        "stamina_cost": 3,
    },
    "multi": {
        "name": "Rapid Combo",
        "description": "The enemy shifts into a rapid combo stance.",
        "contact_mult": 0.7,
        "effect_mult": 1.7,
        "hits": 3,
        "stamina_cost": 3,
    },
    "guard_break": {
        "name": "Guard Break",
        "description": "A guard-breaking blow is being prepared.",
        "contact_mult": 0.8,
        "effect_mult": 1.2,
        "hits": 1,
        "stamina_cost": 2,
    },
}

# Per-archetype move cycles, carried over from the proven grammar in the
# reference inventory.
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
    # Set when the deck's intended move was unaffordable and the enemy
    # fell back to a cheaper one.
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


class IntentTracker:
    """Owns intent generation and the telegraph timeline for one battle.

    `current` is the move about to resolve this round (telegraphed to the
    player before they act). `advance()` resolves it into history and
    telegraphs the next one. The deck index lives here, not on the enemy.
    """

    def __init__(self, archetype: str, rng: random.Random | None = None, stamina_budget: float | None = None):
        self.archetype = str(archetype or DEFAULT_ARCHETYPE).lower()
        self._deck = ARCHETYPE_DECKS.get(self.archetype, ARCHETYPE_DECKS[DEFAULT_ARCHETYPE])
        rng = rng or random.Random()
        self._index = rng.randrange(len(self._deck))
        self.history: list[Intent] = []
        self.current: Intent = self._roll(stamina_budget)

    def _roll(self, stamina_budget: float | None = None) -> Intent:
        kind = self._deck[self._index % len(self._deck)]
        self._index += 1
        if stamina_budget is not None and int(INTENT_LIBRARY[kind]["stamina_cost"]) > stamina_budget:
            return build_intent(cheapest_kind(), self.archetype, downgraded_from=kind)
        return build_intent(kind, self.archetype)

    def advance(self, stamina_budget: float | None = None) -> Intent:
        """Resolve the current move into history and telegraph the next.
        When a stamina budget is given, an unaffordable deck move is
        downgraded to the cheapest one (the deck still cycles)."""
        self.history.append(self.current)
        self.current = self._roll(stamina_budget)
        return self.current

    def telegraph(self) -> dict[str, str]:
        """UI-facing view of the announced move: a name and a short
        effect description."""
        return {"name": self.current.name, "description": self.current.description}


def is_counter(counter_tags: list[str] | tuple[str, ...] | frozenset[str], intent: Intent) -> bool:
    return bool(frozenset(str(t).lower() for t in counter_tags) & intent.countered_by)
