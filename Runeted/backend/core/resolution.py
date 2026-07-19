"""Win/loss resolution: the single decision point for a battle's end state.

The player always acts before the enemy within a round, so a kill on the
player's strike ends the round before the enemy's move resolves — both
sides can never die simultaneously.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class Outcome(str, Enum):
    IN_PROGRESS = "in_progress"
    VICTORY = "victory"
    DEFEAT = "defeat"


def resolve(player_hp: float, enemy_hp: float) -> Outcome:
    if float(enemy_hp) <= 0.0:
        return Outcome.VICTORY
    if float(player_hp) <= 0.0:
        return Outcome.DEFEAT
    return Outcome.IN_PROGRESS


def summary(outcome: Outcome, rounds: int, player_hp: float, enemy_hp: float) -> dict[str, Any]:
    return {
        "outcome": outcome.value,
        "rounds": int(rounds),
        "player_hp": round(max(0.0, float(player_hp)), 2),
        "enemy_hp": round(max(0.0, float(enemy_hp)), 2),
    }
