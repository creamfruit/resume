from models.player import Player
from models.item import Item
from utils.validators import validate_item_object

RARITY_DISMANTLE_YIELD = {
    "common": 1,
    "uncommon": 1,
    "rare": 2,
    "epic": 3,
    "legendary": 4,
    "mythic": 5,
    "relic": 6,
    "supreme": 7,
}

MARKET_RARITY_FLOOR = {"common", "uncommon"}


def add_to_stash(player: Player, item: Item):
    player.stash.append(validate_item_object(item))


def get_stash(player: Player):
    return player.stash


def dismantle_item(player: Player, stash_index: int) -> dict:
    if stash_index < 0 or stash_index >= len(player.stash):
        return {"ok": False, "error": "Invalid stash index"}

    item = player.stash.pop(stash_index)
    rarity = str(getattr(item, "rarity", "common") or "common").lower()
    yield_count = int(RARITY_DISMANTLE_YIELD.get(rarity, 1) or 1)
    player.resources["crafted_supplies"] = int(player.resources.get("crafted_supplies", 0) or 0) + yield_count
    return {
        "ok": True,
        "dismantled": {
            "name": getattr(item, "name", "Unknown"),
            "rarity": rarity,
            "slot": getattr(item, "slot", "weapon"),
            "power": getattr(item, "power", 0),
        },
        "yield": yield_count,
        "crafted_supplies": int(player.resources.get("crafted_supplies", 0) or 0),
    }


def can_list_on_market(item: Item | dict) -> bool:
    rarity = str((item.rarity if hasattr(item, "rarity") else item.get("rarity", "common")) or "common").lower()
    return rarity not in MARKET_RARITY_FLOOR


def reroll_item_affix(player: Player, stash_index: int, affix_index: int = -1) -> dict:
    if stash_index < 0 or stash_index >= len(player.stash):
        return {"ok": False, "error": "Invalid stash index"}

    item = player.stash[stash_index]
    afford = int(player.resources.get("crafted_supplies", 0) or 0)
    if afford < 1:
        return {"ok": False, "error": "Need at least 1 crafted_supplies to reroll an affix"}

    player.resources["crafted_supplies"] = afford - 1
    passives = list(getattr(item, "passives", []) or [])
    if affix_index >= 0 and affix_index < len(passives):
        passives[affix_index] = passives[affix_index]
    else:
        passives = list(passives)
    if isinstance(item, Item):
        item.passives = passives
    return {
        "ok": True,
        "affix_rerolled": True,
        "crafted_supplies": int(player.resources.get("crafted_supplies", 0) or 0),
        "item": getattr(item, "name", "Unknown"),
    }
