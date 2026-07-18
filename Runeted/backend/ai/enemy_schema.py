from typing import List, Literal

from pydantic import BaseModel, Field

Archetype = Literal["brute", "caster", "skirmisher", "tank", "summoner"]


class AIEnemyDesign(BaseModel):
    name: str = Field(min_length=3, max_length=48)
    archetype: Archetype
    abilities: List[str] = Field(default_factory=list, max_length=6)
    trait: str = Field(default="", max_length=80)
    level: int = Field(default=1, ge=1, le=120)
    hp: int = Field(default=1, ge=1, le=5000)
    attack: int = Field(default=1, ge=1, le=500)
    defense: int = Field(default=0, ge=0, le=200)
    crit_chance: float = Field(default=0.03, ge=0.0, le=0.35)
