from __future__ import annotations

from typing import Any

from models.item import Item
from engine.passive_system import clamp_passives

ITEM_POWER_BOUNDS = {
    "common": (1, 16),
    "rare": (10, 28),
    "epic": (20, 46),
    "legendary": (35, 55),
    "mythic": (55, 80),
    "relic": (80, 105),
    "supreme": (90, 120),
}


def _normalize_rarity(rarity: Any) -> str:
    return str(rarity or "common").strip().lower() or "common"


def _normalize_slot(slot: Any) -> str:
    slot_name = str(slot or "weapon").strip().lower()
    return slot_name if slot_name in {"weapon", "armor"} else "weapon"


def _clamp_power(rarity: str, power: Any) -> int:
    lo, hi = ITEM_POWER_BOUNDS.get(rarity, ITEM_POWER_BOUNDS["common"])
    return max(lo, min(hi, int(power or 0)))


def _normalize_item_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Item payload must be a mapping")

    rarity = _normalize_rarity(payload.get("rarity"))
    slot = _normalize_slot(payload.get("slot"))
    passives = payload.get("passives", [])
    normalized = dict(payload)
    normalized["rarity"] = rarity
    normalized["slot"] = slot
    normalized["power"] = _clamp_power(rarity, normalized.get("power", 0))
    normalized["passives"] = clamp_passives(passives, rarity)
    normalized["source"] = str(normalized.get("source", "system") or "system").lower()
    if normalized["source"] not in {"system", "ai"}:
        normalized["source"] = "system"
    return normalized


def validate_item_payload(payload: Any) -> Item:
    normalized = _normalize_item_payload(payload)
    if hasattr(Item, "model_validate"):
        return Item.model_validate(normalized)
    return Item(**normalized)


def validate_item_object(item: Any) -> Item:
    if isinstance(item, Item):
        payload = item.model_dump() if hasattr(item, "model_dump") else item.dict()
        return validate_item_payload(payload)
    return validate_item_payload(item)
