"""Push-your-luck reward flow.

After a battle win, the player picks: bank the run's pending rewards
and return to the hub, or continue into a harder encounter for a bigger
pending reward. Rewards from a continued run accumulate in a
`PendingPool` rather than being granted immediately; banking commits
the whole pool into the wallet, and losing while continuing forfeits
it entirely (the wallet only ever grows through a bank, never through
a loss). Whatever was already banked from an earlier exit is untouched
either way -- only the *current, unbanked* run is ever at risk.

This reuses two existing systems rather than inventing new ones:
- Encounter escalation reuses `engine/enemy_factory.py`'s archetype +
  modifier system (colossal/volatile/runic/swift, elite variants) --
  one of the pre-approved "enemy modifier stacking" building blocks
  carried over from the old repo -- instead of the plain per-level
  `baseline_enemy()` curve a fresh hub-started fight uses. Only
  continuation encounters swap generators; the first fight of a
  session is unaffected.
- Reward tiering reuses `services/chest.py::roll_guaranteed_reward`,
  itself built on `roll_chest_tier`/`roll_rarity` and the shared
  currency pool. The escalation lives entirely in the *enemy*: a
  streak-scaled encounter carries a higher enemy-risk score, and that
  alone is what pushes the reward roll upward -- there is no second,
  parallel reward curve here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.enemy_factory import create_enemy
from models.enemy import Enemy
from services.chest import grant_chest
from services.currency import add_currency

# Consecutive wins escalate at full strength through this streak; past
# it the curve flattens sharply (diminishing returns) rather than
# stopping outright, and both depth and risk are additionally clamped
# to an absolute ceiling so a very long run can't grow unbounded even
# asymptotically.
SOFT_CAP_STREAK = 6
POST_CAP_RISK_STEP = 0.35
POST_CAP_DEPTH_STEP = 0.18
MAX_RISK = 30
MAX_DEPTH = 12

# Auto-battle's safety net for the continue decision below: continuing
# never heals (see battle_app.continue_gauntlet's docstring), so pushing
# on with an unattended auto-battle indefinitely would eventually walk
# it into a defeat it never needed to risk. Below this fraction of max
# HP, auto-battle banks the run instead of pushing on into a harder,
# escalated encounter.
AUTO_BANK_HP_THRESHOLD = 0.3


def should_auto_bank(hp_pct: float, threshold: float = AUTO_BANK_HP_THRESHOLD) -> bool:
    """Whether auto-battle should bank the pending run instead of
    continuing, given the player's HP as a fraction of max HP carried
    into the next encounter. `hp_pct` uses the *current* HP, since
    continuing never heals -- so this is the actual risk being weighed,
    not an optimistic one."""
    return hp_pct < threshold


def escalation_for_streak(streak: int) -> tuple[int, int]:
    """(depth, risk) fed to `engine.enemy_factory.create_enemy` for a
    continuation encounter after `streak` consecutive wins this run.
    Linear through the soft cap, then a much shallower slope, then a
    hard ceiling -- difficulty keeps moving but never runs away."""
    streak = max(0, int(streak))
    capped = min(streak, SOFT_CAP_STREAK)
    overflow = streak - capped

    risk = capped + overflow * POST_CAP_RISK_STEP
    depth = 1 + (capped // 2) + overflow * POST_CAP_DEPTH_STEP

    return min(MAX_DEPTH, max(1, int(round(depth)))), min(MAX_RISK, max(0, int(round(risk))))


def next_encounter_enemy(streak: int) -> Enemy:
    """The next continuation encounter: same variety/modifier generator
    as every other enemy in the game, scaled by the escalation curve."""
    depth, risk = escalation_for_streak(streak)
    return create_enemy(depth=depth, risk=risk)


@dataclass
class PendingPool:
    """Rewards won during an in-progress push-your-luck run, held here
    instead of being granted immediately. `streak` is both the win
    counter and the escalation input for the next encounter."""
    streak: int = 0
    chests: dict[str, int] = field(default_factory=dict)
    gold: int = 0
    resources: dict[str, int] = field(default_factory=dict)

    def add_win(self, reward: dict[str, Any]) -> None:
        self.streak += 1
        rarity = str(reward["chest_rarity"])
        self.chests[rarity] = int(self.chests.get(rarity, 0)) + 1

        currency_id = str(reward["currency_id"])
        amount = int(reward["currency_amount"])
        if currency_id == "gold":
            self.gold += amount
        else:
            self.resources[currency_id] = int(self.resources.get(currency_id, 0)) + amount

    def is_empty(self) -> bool:
        return self.streak <= 0

    def summary(self) -> dict[str, Any]:
        return {
            "streak": self.streak,
            "chests": dict(self.chests),
            "gold": self.gold,
            "resources": dict(self.resources),
        }

    def reset(self) -> None:
        self.streak = 0
        self.chests = {}
        self.gold = 0
        self.resources = {}


def bank(pool: PendingPool, wallet: Any) -> dict[str, Any]:
    """Commit every pending entry into `wallet` via the same functions
    every other chest/currency award uses (`grant_chest`, `add_currency`),
    then clear the pool. Returns what was banked, for the response."""
    banked = pool.summary()
    for rarity, count in pool.chests.items():
        for _ in range(count):
            grant_chest(wallet, rarity)
    if pool.gold:
        add_currency(wallet, "gold", pool.gold)
    for currency_id, amount in pool.resources.items():
        add_currency(wallet, currency_id, amount)
    pool.reset()
    return banked


def forfeit(pool: PendingPool) -> dict[str, Any]:
    """Discard the pending pool entirely -- the wallet never sees it."""
    lost = pool.summary()
    pool.reset()
    return lost
