"""Passive Rune system: always-on effects equipped before battle.

Runes are deliberately not Skills. A skill is the active choice the
player commits to each round and draws on the skill value budget
(core/skills.py). A rune is equipped before battle, is always active
while equipped, and draws on its own, separate equip-cost budget — a
smaller passive layer on top of skill strategy, never a replacement
for it.

A rune's effect is not a new effect system: each rune carries standard
`PassiveModel` payloads (models/passive.py) resolved by the existing
passive engine (engine/passive_system.py) — the same triggers items
already use (on_hit, on_take_hit, start_of_turn, below_hp, ...), the
same chance/threshold rules, and the same rarity/value limits
(`clamp_passives`). core/battle.py fires those triggers each round and
maps the resolved effects onto battle state, which only Battle may own.

Equip rules, enforced at construction (the only place equipment is
built): at most RUNE_SLOT_CAP runes, and their total cost may not
exceed RUNE_COST_BUDGET. Both are tunables — start small so runes stay
a garnish, and adjust once it feels right.

The legacy rune module (models/rune.py / services/rune_system.py)
remains untouched; its crafting/economy content is a later phase.
"""
from __future__ import annotations

from typing import Any, Iterable

from pydantic import BaseModel, Field

from engine.passive_system import clamp_passives
from models.passive import PassiveModel

RUNE_SLOT_CAP = 3
RUNE_COST_BUDGET = 6


class Rune(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    rarity: str = "rare"
    # Equip cost against the rune budget — a separate pool from the
    # skill value budget.
    cost: int = Field(ge=0, le=5)
    # Element or category tag ("fire", "wind", "earth", ...).
    type: str = "physical"
    icon: str = "rune"
    description: str = ""
    # Standard passive payloads consumed by engine/passive_system.py.
    passives: list[dict[str, Any]] = Field(default_factory=list)

    def clamped_passives(self) -> list[PassiveModel]:
        """This rune's passives, normalized and bounded by the shared
        passive-engine limits for its rarity."""
        return clamp_passives(list(self.passives), self.rarity)


RUNE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "emberheart", "name": "Emberheart", "rarity": "rare",
        "cost": 2, "type": "fire", "icon": "ember",
        "description": "Your strikes sear life out of the enemy: each hit heals you for a tenth of the damage dealt.",
        "passives": [{
            "name": "Emberheart Drain", "trigger": "on_hit", "chance": 1.0,
            "effects": [{"type": "lifesteal", "value": 0.10, "target": "self"}],
        }],
    },
    {
        "id": "thornmail_sigil", "name": "Thornmail Sigil", "rarity": "rare",
        "cost": 2, "type": "nature", "icon": "thorn",
        "description": "Barbs answer every blow: attackers take back a fifth of the damage they deal to you.",
        "passives": [{
            "name": "Thornmail", "trigger": "on_take_hit", "chance": 1.0,
            "effects": [{"type": "thorns", "value": 0.20, "target": "self"}],
        }],
    },
    {
        "id": "zephyr_charm", "name": "Zephyr Charm", "rarity": "rare",
        "cost": 1, "type": "wind", "icon": "zephyr",
        "description": "A restless wind nudges you aside: +5% chance to dodge each round.",
        "passives": [{
            "name": "Zephyr Step", "trigger": "start_of_turn", "chance": 1.0,
            "effects": [{"type": "dodge_mod", "value": 0.05, "target": "self"}],
        }],
    },
    {
        "id": "wardstone", "name": "Wardstone", "rarity": "epic",
        "cost": 3, "type": "earth", "icon": "ward",
        "description": "When you drop below half health, a stone ward forms each round and absorbs 6 incoming damage.",
        "passives": [{
            "name": "Stone Ward", "trigger": "below_hp", "threshold": 0.5, "chance": 1.0,
            "effects": [{"type": "shield", "value": 6.0, "target": "self"}],
        }],
    },
    {
        "id": "berserker_brand", "name": "Berserker Brand", "rarity": "epic",
        "cost": 3, "type": "blood", "icon": "brand",
        "description": "Pain feeds fury: while below 40% health your strikes deal +15% damage.",
        "passives": [{
            "name": "Berserk", "trigger": "below_hp", "threshold": 0.4, "chance": 1.0,
            "effects": [{"type": "damage_mult", "value": 0.15, "target": "self"}],
        }],
    },
]

# Default equipped set for the battle screen: cost 5 of 6, 3 of 3 slots.
DEFAULT_EQUIPPED_IDS = ["emberheart", "thornmail_sigil", "zephyr_charm"]


class RuneEquipment:
    def __init__(self, runes: Iterable[Rune], slots: int | None = None,
                 cost_budget: int | None = None):
        self.slots = int(slots if slots is not None else RUNE_SLOT_CAP)
        self.runes: dict[str, Rune] = {}
        for rune in runes:
            if len(self.runes) >= self.slots:
                raise ValueError(f"Rune equipment exceeds the {self.slots} slot cap")
            self.runes[rune.id] = rune
        self.cost_budget = int(cost_budget if cost_budget is not None else RUNE_COST_BUDGET)
        self.total_cost = sum(int(r.cost) for r in self.runes.values())
        if self.total_cost > self.cost_budget:
            raise ValueError(
                f"Rune equipment cost {self.total_cost} exceeds the {self.cost_budget} equip budget"
            )

    def get(self, rune_id: str) -> Rune | None:
        return self.runes.get(str(rune_id))

    def passives(self) -> list[PassiveModel]:
        """All equipped runes' passives, clamped by the shared engine."""
        out: list[PassiveModel] = []
        for rune in self.runes.values():
            out.extend(rune.clamped_passives())
        return out


def describe_rune(rune: Rune) -> dict[str, str]:
    """Single source of the rune text the UI shows: `short` for the
    hover popup and chip tooltip, `full` for the info modal body.

    Both are plain language only, written for the player, not the
    developer: the modal's meta line already shows type/rarity/cost as
    separate structured fields, so `full` doesn't repeat them, and
    neither string surfaces the underlying trigger/effect data
    (on_hit, damage_mult, ...) the passive engine actually runs on —
    that's implementation detail, not something a player needs to read
    to understand what the rune does."""
    short = rune.description
    full = (
        f"{rune.name}: {rune.description} Passive — always active once "
        f"equipped, never a per-turn choice like a skill."
    )
    return {"short": short, "full": full}


def catalog_runes() -> list[Rune]:
    return [Rune(**entry) for entry in RUNE_CATALOG]


def rune_by_id(rune_id: str) -> Rune | None:
    for entry in RUNE_CATALOG:
        if str(entry["id"]) == str(rune_id):
            return Rune(**entry)
    return None


def default_equipment() -> RuneEquipment:
    by_id = {str(entry["id"]): entry for entry in RUNE_CATALOG}
    runes = [Rune(**by_id[rid]) for rid in DEFAULT_EQUIPPED_IDS if rid in by_id]
    return RuneEquipment(runes)


def no_runes() -> RuneEquipment:
    return RuneEquipment(())
