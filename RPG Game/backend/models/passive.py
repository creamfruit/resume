from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Literal, Optional

PassiveTrigger = Literal[
    "on_hit",
    "on_take_hit",
    "on_kill",
    "on_dodge",
    "below_hp",
    "start_of_turn",
    "end_of_turn",
]

PassiveEffectType = Literal[
    "damage_mult",
    "shield",
    "lifesteal",
    "bleed",
    "dot",
    "thorns",
    "dodge_mod",
    "self_damage",
    "stat_drain",
    "enemy_buff",
]

EffectTarget = Literal["self", "enemy"]
StatId = Literal["str", "dex", "int", "vit", "luck"]
Scaling = Literal["flat", "percent"]


class PassiveEffect(BaseModel):
    type: PassiveEffectType
    value: float
    target: EffectTarget = "self"
    chance: float = 1.0
    duration: int = 0
    stacks: int = 1
    stat: Optional[StatId] = None
    scaling: Scaling = "flat"


class PassiveModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    trigger: PassiveTrigger
    effects: List[PassiveEffect] = Field(default_factory=list)
    chance: float = 1.0
    threshold: float = 0.0
    cursed: bool = False
