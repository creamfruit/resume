"""Structured per-round battle events.

This is the contract the frontend renders from — battle log lines,
damage-number popups, HP/stamina bars — without guessing. One RoundEvent
is produced per round and carries, for each side: the move/intent used,
the response chosen, the HP delta, the stamina delta, and any status
effects applied or removed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResourceDelta:
    before: float
    after: float

    def to_dict(self) -> dict[str, float]:
        return {
            "before": round(self.before, 2),
            "after": round(self.after, 2),
            "delta": round(self.after - self.before, 2),
        }


@dataclass(frozen=True)
class StatusChange:
    target: str  # "player" | "enemy"
    status: str  # e.g. "exposed"
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"target": self.target, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class PlayerTurn:
    action: str                   # skill kind used, or "strike" when holding
    response: str | None          # skill id used, or None (held)
    response_name: str | None
    matched: bool                 # response countered the telegraphed move
    exposed_bonus_applied: bool
    damage_dealt: float
    stamina_spent: float
    stamina_regen: float
    hp: ResourceDelta
    stamina: ResourceDelta
    stamina_restored: float = 0.0  # recovery skills only

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "response": self.response,
            "response_name": self.response_name,
            "matched": self.matched,
            "exposed_bonus_applied": self.exposed_bonus_applied,
            "damage_dealt": round(self.damage_dealt, 2),
            "stamina_spent": round(self.stamina_spent, 2),
            "stamina_restored": round(self.stamina_restored, 2),
            "stamina_regen": round(self.stamina_regen, 2),
            "hp": self.hp.to_dict(),
            "stamina": self.stamina.to_dict(),
        }


@dataclass(frozen=True)
class EnemyTurn:
    intent_kind: str
    intent_name: str
    intent_description: str
    downgraded_from: str | None   # deck move skipped for lack of stamina
    resolved: bool                # False when the enemy died before acting
    effect_negated: bool
    dodged: bool
    damage_dealt: float
    stamina_spent: float
    stamina_regen: float
    hp: ResourceDelta
    stamina: ResourceDelta

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": {
                "kind": self.intent_kind,
                "name": self.intent_name,
                "description": self.intent_description,
                "downgraded_from": self.downgraded_from,
            },
            "resolved": self.resolved,
            "effect_negated": self.effect_negated,
            "dodged": self.dodged,
            "damage_dealt": round(self.damage_dealt, 2),
            "stamina_spent": round(self.stamina_spent, 2),
            "stamina_regen": round(self.stamina_regen, 2),
            "hp": self.hp.to_dict(),
            "stamina": self.stamina.to_dict(),
        }


@dataclass(frozen=True)
class RoundEvent:
    round_no: int
    outcome: str
    player: PlayerTurn
    enemy: EnemyTurn
    statuses_applied: tuple[StatusChange, ...] = field(default=())
    statuses_removed: tuple[StatusChange, ...] = field(default=())
    # Passive rune hooks that fired this round (trigger, passive, type,
    # value, applied amount) — resolved by the shared passive engine.
    rune_events: tuple[dict[str, Any], ...] = field(default=())
    next_telegraph: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round_no,
            "outcome": self.outcome,
            "player": self.player.to_dict(),
            "enemy": self.enemy.to_dict(),
            "statuses_applied": [s.to_dict() for s in self.statuses_applied],
            "statuses_removed": [s.to_dict() for s in self.statuses_removed],
            "rune_events": [dict(e) for e in self.rune_events],
            "next_telegraph": self.next_telegraph,
        }
