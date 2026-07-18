from pydantic import BaseModel, Field
from typing import List, Literal

RoomType = Literal["combat", "trap", "event", "rest"]
Archetype = Literal["brute", "caster", "skirmisher", "tank", "summoner"]

class EnemyAI(BaseModel):
    name: str
    archetype: Archetype
    abilities: List[str] = Field(max_items=4)

class RoomAI(BaseModel):
    type: RoomType
    theme: str
    enemies: List[EnemyAI] | None = None
    trap: str | None = None
    event: str | None = None

class DungeonAI(BaseModel):
    dungeon_theme: str
    rooms: List[RoomAI] = Field(min_items=3, max_items=7)
