from pydantic import BaseModel, Field
from typing import List, Literal, Union
from models.passive import PassiveModel

ItemSlot = Literal["weapon", "armor"]
ItemSource = Literal["system", "ai"]

class Item(BaseModel):
    name: str
    rarity: str
    power: int
    passives: List[Union[PassiveModel, str]] = Field(default_factory=list)
    slot: ItemSlot
    source: ItemSource = "system"
