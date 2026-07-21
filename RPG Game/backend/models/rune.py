from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RuneRarity = Literal["common", "uncommon", "rare", "epic", "legendary"]
RuneElement = Literal["fire", "ice", "poison", "physical", "arcane"]
RuneMethod = Literal["offense", "defense", "utility", "drawback", "amplifier"]


class RuneEffect(BaseModel):
    trigger: str = Field(default="on_hit")
    magnitude: float = Field(default=0.0, ge=-1.0, le=2.0)
    condition: str = Field(default="")


class Rune(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    rarity: RuneRarity = "common"
    value: int = Field(ge=-3, le=5)
    element: RuneElement = "physical"
    method: RuneMethod = "utility"
    effect: RuneEffect = Field(default_factory=RuneEffect)
    counters: list[str] = Field(default_factory=list)
    budget_modifier: int | None = Field(default=None, ge=0, le=3)
    slot_modifier: int | None = Field(default=None, ge=0, le=2)
    positional_buff: dict[str, Any] | None = None

    @field_validator("rarity", mode="before")
    @classmethod
    def canonicalize_rarity(cls, value: Any) -> str:
        rarity = str(value or "common").strip().lower()
        if rarity in {"uncommon", "common", "rare", "epic", "legendary"}:
            return rarity
        if rarity in {"supreme", "relic", "mythic"}:
            return "legendary"
        return "common"
