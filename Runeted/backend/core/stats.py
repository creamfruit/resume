"""Derived-stats pipeline.

Combat reads DerivedStats exclusively; it never touches raw player or
enemy fields. Later phases (equipment, runes) plug in via
StatContribution instead of combat growing special cases.

Both sides scale with the same per-level growth base, so an equal-level
fight plays the same at every level and a level advantage is worth the
same multiplier everywhere. baseline_enemy() is the canonical statline
for a given level; phase 3's encounter generation is expected to build
on these curves rather than invent a second set.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

GROWTH_PER_LEVEL = 1.7

# Player base curve (at default attributes of 5).
PLAYER_BASE_ATTACK = 10.0
PLAYER_BASE_DEFENSE = 4.0
PLAYER_BASE_HP = 70.0
ATTACK_PER_STRENGTH = 1.6
DEFENSE_PER_VITALITY = 0.8
HP_PER_VITALITY = 6.0
CRIT_BASE = 0.05
CRIT_PER_LUCK = 0.01
CRIT_CAP = 0.35
DODGE_PER_DEXTERITY = 0.01
DODGE_CAP = 0.20

# Stamina is scale-free: it does not grow with level, and neither do
# action costs, so the pacing pressure is identical at every level.
PLAYER_BASE_STAMINA = 10.0
STAMINA_PER_INTELLIGENCE = 0.5
PLAYER_STAMINA_REGEN = 2.0

# Enemy baseline curve.
ENEMY_BASE_ATTACK = 9.0
ENEMY_BASE_DEFENSE = 3.0
ENEMY_BASE_HP = 46.0
ENEMY_BASE_CRIT = 0.03
ENEMY_BASE_STAMINA = 20.0
ENEMY_STAMINA_REGEN = 2.0


def level_scale(level: int) -> float:
    return GROWTH_PER_LEVEL ** (max(1, int(level)) - 1)


@dataclass(frozen=True)
class DerivedStats:
    attack: float
    defense: float
    max_hp: float
    crit_chance: float
    dodge_chance: float
    max_stamina: float
    stamina_regen: float


@dataclass(frozen=True)
class StatContribution:
    """One source's additive share of derived stats (equipment in phase 2,
    runes in phase 4). Flat values apply after level scaling."""
    source: str = "unknown"
    attack_flat: float = 0.0
    attack_mult: float = 0.0
    defense_flat: float = 0.0
    defense_mult: float = 0.0
    max_hp_flat: float = 0.0
    max_hp_mult: float = 0.0
    crit_flat: float = 0.0
    dodge_flat: float = 0.0
    stamina_flat: float = 0.0


def compute_player_stats(state: Any, contributions: Iterable[StatContribution] = ()) -> DerivedStats:
    scale = level_scale(getattr(state, "level", 1))
    strength = float(getattr(state, "strength", 5))
    vitality = float(getattr(state, "vitality", 5))
    luck = float(getattr(state, "luck", 5))
    dexterity = float(getattr(state, "dexterity", 5))
    intelligence = float(getattr(state, "intelligence", 5))

    attack = (PLAYER_BASE_ATTACK + ATTACK_PER_STRENGTH * (strength - 5)) * scale
    defense = (PLAYER_BASE_DEFENSE + DEFENSE_PER_VITALITY * (vitality - 5)) * scale
    max_hp = (PLAYER_BASE_HP + HP_PER_VITALITY * (vitality - 5)) * scale
    crit = CRIT_BASE + CRIT_PER_LUCK * (luck - 5)
    dodge = DODGE_PER_DEXTERITY * (dexterity - 5)
    max_stamina = PLAYER_BASE_STAMINA + STAMINA_PER_INTELLIGENCE * (intelligence - 5)

    attack_mult = defense_mult = hp_mult = 0.0
    attack_flat = defense_flat = hp_flat = stamina_flat = 0.0
    for c in contributions:
        attack_mult += c.attack_mult
        defense_mult += c.defense_mult
        hp_mult += c.max_hp_mult
        attack_flat += c.attack_flat
        defense_flat += c.defense_flat
        hp_flat += c.max_hp_flat
        crit += c.crit_flat
        dodge += c.dodge_flat
        stamina_flat += c.stamina_flat

    return DerivedStats(
        attack=round(max(1.0, attack * (1.0 + attack_mult) + attack_flat), 2),
        defense=round(max(0.0, defense * (1.0 + defense_mult) + defense_flat), 2),
        max_hp=round(max(1.0, max_hp * (1.0 + hp_mult) + hp_flat), 2),
        crit_chance=round(min(CRIT_CAP, max(0.0, crit)), 3),
        dodge_chance=round(min(DODGE_CAP, max(0.0, dodge)), 3),
        max_stamina=round(max(1.0, max_stamina + stamina_flat), 2),
        stamina_regen=PLAYER_STAMINA_REGEN,
    )


def derive_enemy_stats(enemy: Any) -> DerivedStats:
    """Normalize any enemy-like object into the derived view combat uses."""
    hp = float(getattr(enemy, "max_hp", None) or getattr(enemy, "hp", 1.0) or 1.0)
    return DerivedStats(
        attack=round(max(1.0, float(getattr(enemy, "attack", 1.0) or 1.0)), 2),
        defense=round(max(0.0, float(getattr(enemy, "defense", 0.0) or 0.0)), 2),
        max_hp=round(max(1.0, hp), 2),
        crit_chance=round(min(CRIT_CAP, max(0.0, float(getattr(enemy, "crit_chance", ENEMY_BASE_CRIT) or 0.0))), 3),
        dodge_chance=0.0,
        max_stamina=round(max(1.0, float(getattr(enemy, "max_stamina", None) or ENEMY_BASE_STAMINA)), 2),
        stamina_regen=ENEMY_STAMINA_REGEN,
    )


@dataclass
class BaselineEnemy:
    """Minimal enemy-shaped combatant on the canonical level curve.
    Phase 3 replaces construction of these with real encounter generation;
    the curve itself stays authoritative."""
    level: int
    archetype: str = "brute"
    name: str = "Baseline Foe"
    hp: float = field(default=0.0)
    max_hp: float = field(default=0.0)
    attack: float = field(default=0.0)
    defense: float = field(default=0.0)
    crit_chance: float = ENEMY_BASE_CRIT
    stamina: float = ENEMY_BASE_STAMINA
    max_stamina: float = ENEMY_BASE_STAMINA


def baseline_enemy(level: int, archetype: str = "brute", name: str | None = None) -> BaselineEnemy:
    scale = level_scale(level)
    hp = round(ENEMY_BASE_HP * scale, 2)
    return BaselineEnemy(
        level=max(1, int(level)),
        archetype=archetype,
        name=name or f"Level {level} {archetype.title()}",
        hp=hp,
        max_hp=hp,
        attack=round(ENEMY_BASE_ATTACK * scale, 2),
        defense=round(ENEMY_BASE_DEFENSE * scale, 2),
        crit_chance=ENEMY_BASE_CRIT,
    )
