"""Non-combat special events: an alternative encounter outcome rolled
alongside a fight, built on the same encounter-generation step
push-your-luck already uses (core/gauntlet.py's escalation curve over
engine/enemy_factory.py's enemy-variety system) rather than a second,
parallel system. Every encounter roll -- a fresh hub start or a
push-your-luck continuation alike -- can land on an event instead of a
fight; `roll_encounter_kind` is the one gate both call through.

An event's outcome is always a deterministic, seeded roll weighted by
the player's charisma and luck (core/player_state.py's leveling
attributes) into one of four fixed tiers -- fail, partial, success,
great. No live/generative call ever decides it: the only generative
call anywhere in encounter generation is engine/enemy_factory.py's
flavor-text designer for *combat* encounters, and events never touch
it. Each event type's reward at each tier is a fixed, declared value
(never itself scaled further by charisma/luck) so its bounds are a
simple, testable property, exactly like services/chest.py's tiered
contents bounds.
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
BASELINE_STAT = 5
CHARISMA_WEIGHT = 0.025
LUCK_WEIGHT = 0.015
MAX_CHARISMA_BONUS = 0.22
MAX_LUCK_BONUS = 0.13
# The combined bonus is additionally capped here, and that cap is kept
# below the fail cutoff above -- so even a maxed-out charisma and luck
# can only ever improve the odds, never remove the chance of failure
# outright (a roll of 0.0 plus the max bonus still lands below 0.35).
MAX_TOTAL_STAT_BONUS = 0.30
assert MAX_TOTAL_STAT_BONUS < TIER_CUTOFFS[0][0], "stat bonus cap must leave failure possible"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def stat_bonus(charisma: int, luck: int) -> float:
    """The combined, capped nudge charisma and luck give an event roll.
    Charisma is the primary lever (per the design brief), luck a
    smaller secondary one; both are zero at baseline stats and can
    never go negative even if a stat somehow dropped below baseline."""
    charisma_bonus = _clamp((int(charisma) - BASELINE_STAT) * CHARISMA_WEIGHT, 0.0, MAX_CHARISMA_BONUS)
    luck_bonus = _clamp((int(luck) - BASELINE_STAT) * LUCK_WEIGHT, 0.0, MAX_LUCK_BONUS)
    return min(MAX_TOTAL_STAT_BONUS, charisma_bonus + luck_bonus)


def roll_outcome_tier(charisma: int, luck: int, rng: random.Random) -> str:
    score = rng.random() + stat_bonus(charisma, luck)
    for cutoff, tier in TIER_CUTOFFS:
        if score < cutoff:
            return tier
    return OUTCOME_GREAT


# ---------------------------------------------------------------------------
# Which event fires
# ---------------------------------------------------------------------------

# Flat chance any given encounter roll lands on an event instead of a
# fight -- the same for a fresh hub start and a push-your-luck
# continuation, so this is a general encounter-generation capability,
# not something tied to escalating risk.
EVENT_CHANCE = 0.22

EVENT_TYPES = ("merchant", "shrine", "hazard", "treasure")
# Equal odds among the four starter types; a future type just adds an
# entry here.
EVENT_WEIGHTS: dict[str, int] = {"merchant": 1, "shrine": 1, "hazard": 1, "treasure": 1}

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
    gold_delta: int = 0
    resource_id: str | None = None
    resource_amount: int = 0
    hp_loss_pct: float = 0.0
    chest_rarity: str | None = None
    buff_rounds: int = 0
    buff_mult: float = 0.0


def resolve_event(event_type: str, charisma: int, luck: int, rng: random.Random) -> EventOutcome:
    """Roll one event's outcome tier (charisma/luck-weighted) and look up
    its fixed reward from the declared table -- the roll only ever picks
    *which* tier is reached, never how large that tier's reward is."""
    event_type = str(event_type).lower()
    table = REWARD_TABLES.get(event_type)
    if table is None:
        raise ValueError(f"Unknown event type '{event_type}'")

    tier = roll_outcome_tier(charisma, luck, rng)
    reward = table[tier]
    flavor = EVENT_FLAVOR[event_type]
    outcome = EventOutcome(
        event_type=event_type, tier=tier,
        name=flavor["name"], description=flavor["description"],
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
