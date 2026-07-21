from typing import List, Literal

from pydantic import BaseModel, Field, model_validator

from models.passive import PassiveModel

RARITY_DAMAGE_BOUNDS = {
    "legendary": (35, 55),
    "mythic": (55, 80),
    "relic": (80, 105),
}


class AIDesignedItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    slot: Literal["weapon", "armor"]
    rarity: Literal["legendary", "mythic", "relic"]
    damage: int = Field(ge=1, le=105)
    passives: List[PassiveModel] = Field(default_factory=list)
    flavor: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def _enforce_damage_bounds(self):
        lo, hi = RARITY_DAMAGE_BOUNDS[self.rarity]
        if not (lo <= self.damage <= hi):
            raise ValueError(f"damage must be between {lo} and {hi} for rarity {self.rarity}")
        return self
