from pydantic import BaseModel
from typing import List, Literal
from models.enemy import Enemy

RoomType = Literal["combat", "trap", "event", "rest", "treasure", "shrine", "boss"]

class DungeonRoom(BaseModel):
    type: RoomType
    enemy: Enemy | None = None

class Dungeon(BaseModel):
    depth: int
    risk: int
    rooms: List[DungeonRoom]
    boss_floor: bool = False
