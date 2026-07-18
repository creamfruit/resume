from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class Enemy(BaseModel):
    name: str
    level: int
    hp: int
    max_hp: int = 0
    attack: int
    abilities: List[str] = Field(default_factory=list)
    elite: bool = False
    tier: str = "normal"  # "normal" | "elite" | "boss"
    defense: int = 0
    crit_chance: float = 0.03
    status: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    combat_mods: Dict[str, object] = Field(default_factory=dict)
    intent: Optional[Dict[str, object]] = None
    archetype: str = "brute"
