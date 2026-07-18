from pydantic import BaseModel, Field
from typing import List, Literal
from models.passive import PassiveModel

class AIDesignedItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    slot: Literal["weapon", "armor"]
    rarity: Literal["legendary", "mythic", "relic"]
    damage: int
    passives: List[PassiveModel] = Field(default_factory=list)
    flavor: str = Field(default="", max_length=200)
