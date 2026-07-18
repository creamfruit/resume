from typing import List, Literal

from pydantic import BaseModel, Field

Archetype = Literal["brute", "caster", "skirmisher", "tank", "summoner"]


class AIEnemyDesign(BaseModel):
    name: str = Field(min_length=3, max_length=48)
    archetype: Archetype
    abilities: List[str] = Field(default_factory=list, max_length=6)
    trait: str = Field(default="", max_length=80)
