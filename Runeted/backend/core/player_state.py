"""Lean player runtime model: identity and progression only.

Equipment, stash, and runes live in their own modules. Anything combat
reads (attack, defense, max HP) comes from the derived-stats pipeline in
core/stats.py, never from raw fields here.

Six attributes exist on the model, but only five feed combat through
core/stats.py::compute_player_stats: strength (attack), vitality
(defense/HP), luck (crit), dexterity (dodge), intelligence (stamina).
`charisma` is deliberately excluded from that pipeline -- it feeds
core/special_events.py's event resolution instead, not combat.

Every attribute starts at 0 (a freshly-rolled character has invested
nothing yet) and only ever grows by spending `stat_points` -- there is
no hidden non-zero baseline stacked underneath 0, so the derived-stats
pipeline's per-point contributions are the entire story.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.stats import level_scale

LEVEL_UP_STAT_POINTS = 3
EXP_CURVE_MULT = 1.5

# XP a battle victory grants, scaled by the defeated enemy's level on
# the same per-level growth curve combat stats already use (level_scale)
# -- one canonical curve, not a second one invented just for XP. A
# tougher (higher-level) win is worth proportionally more.
BASE_VICTORY_EXP = 20

ATTRIBUTES = ("strength", "dexterity", "intelligence", "vitality", "luck", "charisma")


def victory_exp(enemy_level: int) -> int:
    return max(1, int(round(BASE_VICTORY_EXP * level_scale(enemy_level))))


class PlayerState(BaseModel):
    # Identity
    name: str = Field(default="Adventurer", min_length=1, max_length=60)

    # Progression
    level: int = Field(default=1, ge=1)
    exp: int = Field(default=0, ge=0)
    exp_to_next: int = Field(default=100, ge=1)
    stat_points: int = Field(default=0, ge=0)
    strength: int = Field(default=0, ge=0)
    dexterity: int = Field(default=0, ge=0)
    intelligence: int = Field(default=0, ge=0)
    vitality: int = Field(default=0, ge=0)
    luck: int = Field(default=0, ge=0)
    charisma: int = Field(default=0, ge=0)

    # Runtime resources. None means "full"; the concrete ceilings are
    # DerivedStats.max_hp / max_stamina, which only core/stats.py may compute.
    hp: float | None = Field(default=None, ge=0)
    stamina: float | None = Field(default=None, ge=0)

    def gain_exp(self, amount: int) -> int:
        """Add experience, applying level-ups. Returns levels gained."""
        gained = 0
        self.exp += max(0, int(amount))
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level += 1
            self.stat_points += LEVEL_UP_STAT_POINTS
            self.exp_to_next = int(self.exp_to_next * EXP_CURVE_MULT)
            self.hp = None  # level-up restores to full
            self.stamina = None
            gained += 1
        return gained

    def spend_stat(self, stat: str, amount: int = 1) -> bool:
        if amount <= 0 or self.stat_points < amount:
            return False
        if stat not in ATTRIBUTES:
            return False
        setattr(self, stat, getattr(self, stat) + amount)
        self.stat_points -= amount
        return True

    def heal_full(self) -> None:
        self.hp = None
        self.stamina = None
