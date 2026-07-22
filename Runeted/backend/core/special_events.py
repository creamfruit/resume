"""Non-combat special events: an alternative encounter outcome rolled
alongside a fight, built on the same encounter-generation step
push-your-luck already uses (core/gauntlet.py's escalation curve over
engine/enemy_factory.py's enemy-variety system) rather than a second,
parallel system. Every encounter roll -- a fresh hub start or a
push-your-luck continuation alike -- can land on an event instead of a
fight; `roll_encounter_kind` is the one gate both call through.

An event never auto-resolves. Landing on one only ever presents a
choice -- engage or walk away (battle_app.py's `/api/event/engage` and
`/api/event/walk_away`) -- and nothing about the outcome is decided
until the player opts in. Only `engage` rolls the outcome; `walk_away`
ends the encounter with no effect at all, good or bad.

Which single stat governs an event's outcome depends on its flavor,
not one blended formula: social events (`merchant`, a trade
negotiation) resolve on charisma -- a person to persuade. Environmental
/ risk events (`shrine`, `hazard`, `treasure` -- no other party
involved) resolve on luck instead. `EVENT_GOVERNING_STAT` is the one
place that mapping lives; `roll_outcome_tier`/`stat_bonus` read it
rather than ever blending both stats into a single roll.

The roll itself is always deterministic and seeded, exactly like
encounter generation -- once a player engages, the tier is drawn from
the same seeded `random.Random` the encounter roll already started,
never a fresh unseeded one. No live/generative call ever decides it:
the only generative call anywhere in encounter generation is
engine/enemy_factory.py's flavor-text designer for *combat* encounters,
and events never touch it. Each event type's reward at each tier is a
fixed, declared value (never itself scaled further by charisma/luck)
so its bounds are a simple, testable property, exactly like
services/chest.py's tiered contents bounds.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Outcome tiers
# ---------------------------------------------------------------------------

OUTCOME_FAIL = "fail"
OUTCOME_PARTIAL = "partial"
OUTCOME_SUCCESS = "success"
OUTCOME_GREAT = "great"
OUTCOME_TIERS = (OUTCOME_FAIL, OUTCOME_PARTIAL, OUTCOME_SUCCESS, OUTCOME_GREAT)

# score = rng.random() [0, 1) + stat_bonus; the first cutoff a score is
# strictly below wins.
TIER_CUTOFFS = (
    (0.35, OUTCOME_FAIL),
    (0.65, OUTCOME_PARTIAL),
    (0.90, OUTCOME_SUCCESS),
)
# score >= the last cutoff (0.90) is OUTCOME_GREAT.

# PlayerState's default stat value; bonuses are relative to this, so a
# freshly-rolled character (every stat at baseline) sees zero bonus.
BASELINE_STAT = 0
CHARISMA_WEIGHT = 0.045
MAX_CHARISMA_BONUS = 0.22
LUCK_WEIGHT = 0.028
MAX_LUCK_BONUS = 0.22
# Each stat's cap is kept below the fail cutoff on its own -- since only
# one stat ever applies to a given event (never both at once, see
# EVENT_GOVERNING_STAT below), that's what actually has to hold; even a
# maxed-out governing stat can only ever improve the odds, never remove
# the chance of failure outright (a roll of 0.0 plus the max bonus still
# lands below 0.35).
assert MAX_CHARISMA_BONUS < TIER_CUTOFFS[0][0], "charisma bonus cap must leave failure possible"
assert MAX_LUCK_BONUS < TIER_CUTOFFS[0][0], "luck bonus cap must leave failure possible"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# Which event fires, and which single stat governs it
# ---------------------------------------------------------------------------

# Flat chance any given encounter roll lands on an event instead of a
# fight -- the same for a fresh hub start and a push-your-luck
# continuation, so this is a general encounter-generation capability,
# not something tied to escalating risk.
EVENT_CHANCE = 0.22

EVENT_TYPES = ("merchant", "shrine", "hazard", "treasure")
# Equal odds among the four starter types; a future type just adds an
# entry here (and to EVENT_GOVERNING_STAT below).
EVENT_WEIGHTS: dict[str, int] = {"merchant": 1, "shrine": 1, "hazard": 1, "treasure": 1}

STAT_CHARISMA = "charisma"
STAT_LUCK = "luck"

# The one place that decides which stat an event type resolves on.
# `merchant` is the sole social encounter (haggling with a trader) --
# charisma-gated. The other three never involve another party (a
# shrine, a trap, a half-buried cache) and resolve on luck instead.
EVENT_GOVERNING_STAT: dict[str, str] = {
    "merchant": STAT_CHARISMA,
    "shrine": STAT_LUCK,
    "hazard": STAT_LUCK,
    "treasure": STAT_LUCK,
}

EVENT_FLAVOR: dict[str, dict[str, str]] = {
    "merchant": {
        "name": "Wandering Merchant",
        "description": "A traveling merchant offers a trade before you move on.",
    },
    "shrine": {
        "name": "Shrine of Blessing",
        "description": "A quiet shrine hums with old power.",
    },
    "hazard": {
        "name": "Hidden Hazard",
        "description": "Something in this path is rigged to hurt whoever trips it.",
    },
    "treasure": {
        "name": "Treasure Cache",
        "description": "A half-buried cache sits just off the path.",
    },
}


def event_flavor(event_type: str) -> dict[str, str]:
    """The player-facing name/description/governing-stat for an event
    type -- everything battle_app.py needs to present the choice point
    before anything has resolved."""
    event_type = str(event_type).lower()
    if event_type not in EVENT_FLAVOR:
        raise ValueError(f"Unknown event type '{event_type}'")
    flavor = EVENT_FLAVOR[event_type]
    return {
        "name": flavor["name"],
        "description": flavor["description"],
        "governing_stat": EVENT_GOVERNING_STAT[event_type],
    }


def stat_bonus(event_type: str, charisma: int, luck: int) -> float:
    """The bonus this event type's roll gets from whichever single stat
    governs it (EVENT_GOVERNING_STAT) -- the other stat is never read.
    Zero at baseline, and can never go negative even if a stat somehow
    dropped below baseline."""
    stat = EVENT_GOVERNING_STAT[str(event_type).lower()]
    if stat == STAT_CHARISMA:
        return _clamp((int(charisma) - BASELINE_STAT) * CHARISMA_WEIGHT, 0.0, MAX_CHARISMA_BONUS)
    return _clamp((int(luck) - BASELINE_STAT) * LUCK_WEIGHT, 0.0, MAX_LUCK_BONUS)


def roll_outcome_tier(event_type: str, charisma: int, luck: int, rng: random.Random) -> str:
    score = rng.random() + stat_bonus(event_type, charisma, luck)
    for cutoff, tier in TIER_CUTOFFS:
        if score < cutoff:
            return tier
    return OUTCOME_GREAT


def roll_encounter_kind(rng: random.Random) -> str:
    """"event" or "combat" -- the one gate every encounter roll passes
    through before falling back to whichever enemy generator the
    caller would otherwise have used."""
    return "event" if rng.random() < EVENT_CHANCE else "combat"


def roll_event_type(rng: random.Random) -> str:
    types = list(EVENT_WEIGHTS)
    weights = [EVENT_WEIGHTS[t] for t in types]
    return rng.choices(types, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Declared, fixed reward/penalty bounds per event type and tier
# ---------------------------------------------------------------------------

MERCHANT_REWARDS = {
    OUTCOME_FAIL:    {"gold": 0,  "resource_id": None,               "resource_amount": 0},
    OUTCOME_PARTIAL: {"gold": 0,  "resource_id": "crafted_supplies", "resource_amount": 1},
    OUTCOME_SUCCESS: {"gold": 0,  "resource_id": "crafted_supplies", "resource_amount": 3},
    OUTCOME_GREAT:   {"gold": 15, "resource_id": "ascension_sigil",  "resource_amount": 1},
}
SHRINE_REWARDS = {
    OUTCOME_FAIL:    {"gold": 0,  "buff_rounds": 0, "buff_mult": 0.00},
    OUTCOME_PARTIAL: {"gold": 8,  "buff_rounds": 0, "buff_mult": 0.00},
    OUTCOME_SUCCESS: {"gold": 0,  "buff_rounds": 3, "buff_mult": 0.15},
    OUTCOME_GREAT:   {"gold": 10, "buff_rounds": 4, "buff_mult": 0.30},
}
HAZARD_OUTCOMES = {
    OUTCOME_FAIL:    {"hp_loss_pct": 0.18, "gold": 0},
    OUTCOME_PARTIAL: {"hp_loss_pct": 0.08, "gold": 0},
    OUTCOME_SUCCESS: {"hp_loss_pct": 0.00, "gold": 0},
    OUTCOME_GREAT:   {"hp_loss_pct": 0.00, "gold": 6},
}
TREASURE_REWARDS = {
    OUTCOME_FAIL:    {"chest": None},
    OUTCOME_PARTIAL: {"chest": "common"},
    OUTCOME_SUCCESS: {"chest": "rare"},
    OUTCOME_GREAT:   {"chest": "epic"},
}
REWARD_TABLES = {
    "merchant": MERCHANT_REWARDS,
    "shrine": SHRINE_REWARDS,
    "hazard": HAZARD_OUTCOMES,
    "treasure": TREASURE_REWARDS,
}


@dataclass
class EventOutcome:
    event_type: str
    tier: str
    name: str
    description: str
    governing_stat: str = ""
    gold_delta: int = 0
    resource_id: str | None = None
    resource_amount: int = 0
    hp_loss_pct: float = 0.0
    chest_rarity: str | None = None
    buff_rounds: int = 0
    buff_mult: float = 0.0


def resolve_event(event_type: str, charisma: int, luck: int, rng: random.Random) -> EventOutcome:
    """Roll one event's outcome tier -- weighted only by whichever
    single stat this event type is gated on (EVENT_GOVERNING_STAT) --
    and look up its fixed reward from the declared table. Only ever
    called once the player has chosen to engage (battle_app.py's
    `/api/event/engage`); walking away never reaches this at all."""
    event_type = str(event_type).lower()
    table = REWARD_TABLES.get(event_type)
    if table is None:
        raise ValueError(f"Unknown event type '{event_type}'")

    tier = roll_outcome_tier(event_type, charisma, luck, rng)
    reward = table[tier]
    flavor = EVENT_FLAVOR[event_type]
    outcome = EventOutcome(
        event_type=event_type, tier=tier,
        name=flavor["name"], description=flavor["description"],
        governing_stat=EVENT_GOVERNING_STAT[event_type],
    )
    if event_type == "merchant":
        outcome.gold_delta = int(reward["gold"])
        outcome.resource_id = reward["resource_id"]
        outcome.resource_amount = int(reward["resource_amount"])
    elif event_type == "shrine":
        outcome.gold_delta = int(reward["gold"])
        outcome.buff_rounds = int(reward["buff_rounds"])
        outcome.buff_mult = float(reward["buff_mult"])
    elif event_type == "hazard":
        outcome.gold_delta = int(reward["gold"])
        outcome.hp_loss_pct = float(reward["hp_loss_pct"])
    elif event_type == "treasure":
        outcome.chest_rarity = reward["chest"]
    return outcome
