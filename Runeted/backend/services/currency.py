"""Multi-currency crafting economy (Path-of-Exile style).

Every currency is an inventory-held quantity, not a stat: non-gold
currencies live in `player.resources[currency_id]`, the same quantity map
that already holds crafting materials. Gold predates this module as
`player.gold` and is already the auction house's buy/sell medium
(AuctionListing.price, buy_item), so it is registered here as the base
currency rather than duplicated; the wallet API routes it to that field.

The reroll currency deliberately reuses the existing `crafted_supplies`
sink from the dismantle system (services/stash.py) instead of adding a
parallel material — dismantled gear keeps feeding rerolls.

Skills (core/skills.py) are a fixed catalog with no per-player instances
or random affixes yet, so reroll/ascend currently target items and runes;
skill support slots in when skills gain rollable affixes.
"""
from __future__ import annotations

import random
from typing import Any

from engine.affixes import roll_single_affix
from models.item import Item
from models.player import Player
from services.rune_system import (
    RUNE_EFFECT_POOL,
    RUNE_NEXT_RARITY,
    RUNE_UPGRADE_MAX,
    find_rune,
    is_amplifier,
)

BASE_CURRENCY = "gold"

CURRENCIES: dict[str, dict[str, Any]] = {
    "gold": {
        "name": "Gold",
        "base": True,
        "use": "Primary buy/sell medium on the auction house and trade hub.",
    },
    "crafted_supplies": {
        "name": "Flux Sigil",
        "base": False,
        "use": "Rerolls one affix on an item or one effect on a rune.",
    },
    "ascension_sigil": {
        "name": "Ascension Sigil",
        "base": False,
        "use": "Raises an item or rune one rarity tier.",
    },
    "warden_key": {
        "name": "Warden's Key",
        "base": False,
        "use": "Chest key: upgrades a chest one tier when opening it, or guarantees a specific content type instead of a random roll.",
    },
}

REROLL_COST = 1
ASCEND_COST = 1

ITEM_RARITY_LADDER = ["common", "uncommon", "rare", "epic", "legendary", "mythic", "supreme", "relic"]

# Chest content types the guarantee mode can force. The current chest
# only rolls runes; the chest phase extends this set.
CHEST_CONTENT_TYPES = {"rune"}


# ---------- Wallet ----------

def is_currency(currency_id: str) -> bool:
    return str(currency_id or "") in CURRENCIES


def currency_balance(player: Player, currency_id: str) -> int:
    cid = str(currency_id or "")
    if cid == BASE_CURRENCY:
        return int(player.gold or 0)
    return int(player.resources.get(cid, 0) or 0)


def add_currency(player: Player, currency_id: str, amount: int) -> None:
    amount = int(amount)
    if amount <= 0 or not is_currency(currency_id):
        return
    cid = str(currency_id)
    if cid == BASE_CURRENCY:
        player.gold = int(player.gold or 0) + amount
    else:
        player.resources[cid] = int(player.resources.get(cid, 0) or 0) + amount


def spend_currency(player: Player, currency_id: str, amount: int) -> bool:
    amount = int(amount)
    if amount <= 0:
        return True
    if not is_currency(currency_id):
        return False
    if currency_balance(player, currency_id) < amount:
        return False
    cid = str(currency_id)
    if cid == BASE_CURRENCY:
        player.gold = int(player.gold or 0) - amount
    else:
        player.resources[cid] = int(player.resources.get(cid, 0) or 0) - amount
    return True


def wallet(player: Player) -> dict[str, int]:
    return {cid: currency_balance(player, cid) for cid in CURRENCIES}


# ---------- Reroll currency (crafted_supplies / Flux Sigil) ----------

def reroll_item_affix(player: Player, stash_index: int, affix_index: int = -1) -> dict:
    if stash_index < 0 or stash_index >= len(player.stash):
        return {"ok": False, "error": "Invalid stash index"}

    item = player.stash[stash_index]
    passives = list(getattr(item, "passives", []) or [])
    if not passives:
        return {"ok": False, "error": "Item has no affixes to reroll"}

    if affix_index < 0:
        affix_index = random.randrange(len(passives))
    if affix_index >= len(passives):
        return {"ok": False, "error": "Invalid affix index"}

    if not spend_currency(player, "crafted_supplies", REROLL_COST):
        return {"ok": False, "error": f"Need at least {REROLL_COST} crafted_supplies to reroll an affix"}

    new_affix = roll_single_affix(str(getattr(item, "rarity", "common") or "common"))
    passives[affix_index] = new_affix
    if isinstance(item, Item):
        item.passives = passives
    return {
        "ok": True,
        "affix_rerolled": True,
        "affix_index": affix_index,
        "new_affix": new_affix.name,
        "crafted_supplies": currency_balance(player, "crafted_supplies"),
        "item": getattr(item, "name", "Unknown"),
    }


def reroll_rune_effect(player: Player, rune_id: str, effect_index: int = -1) -> dict:
    rune = find_rune(player, rune_id)
    if rune is None:
        return {"ok": False, "error": "Rune not found"}
    if is_amplifier(rune):
        return {"ok": False, "error": "Amplifier runes have no rollable effects"}

    effects = list(rune.get("effects", []) or [])
    if not effects:
        return {"ok": False, "error": "Rune has no effects to reroll"}

    if effect_index < 0:
        effect_index = random.randrange(len(effects))
    if effect_index >= len(effects):
        return {"ok": False, "error": "Invalid effect index"}

    if not spend_currency(player, "crafted_supplies", REROLL_COST):
        return {"ok": False, "error": f"Need at least {REROLL_COST} crafted_supplies to reroll an effect"}

    rarity = str(rune.get("rarity", "common") or "common").lower()
    pool = RUNE_EFFECT_POOL.get(rarity, RUNE_EFFECT_POOL["common"])
    eff_type, lo, hi = random.choice(pool)
    effects[effect_index] = {"type": eff_type, "value": round(random.uniform(float(lo), float(hi)), 4)}
    rune["effects"] = effects
    return {
        "ok": True,
        "effect_rerolled": True,
        "effect_index": effect_index,
        "new_effect": dict(effects[effect_index]),
        "crafted_supplies": currency_balance(player, "crafted_supplies"),
        "rune": str(rune.get("name", "") or "Rune"),
    }


# ---------- Upgrade currency (ascension_sigil) ----------

def ascend_item(player: Player, stash_index: int) -> dict:
    if stash_index < 0 or stash_index >= len(player.stash):
        return {"ok": False, "error": "Invalid stash index"}

    item = player.stash[stash_index]
    rarity = str(getattr(item, "rarity", "common") or "common").lower()
    try:
        next_rarity = ITEM_RARITY_LADDER[ITEM_RARITY_LADDER.index(rarity) + 1]
    except (ValueError, IndexError):
        return {"ok": False, "error": f"Cannot ascend rarity '{rarity}'"}

    if not spend_currency(player, "ascension_sigil", ASCEND_COST):
        return {"ok": False, "error": f"Need at least {ASCEND_COST} ascension_sigil to ascend"}

    item.rarity = next_rarity
    return {
        "ok": True,
        "ascended": True,
        "from": rarity,
        "to": next_rarity,
        "ascension_sigil": currency_balance(player, "ascension_sigil"),
        "item": getattr(item, "name", "Unknown"),
    }


def ascend_rune(player: Player, rune_id: str) -> dict:
    rune = find_rune(player, rune_id)
    if rune is None:
        return {"ok": False, "error": "Rune not found"}
    if is_amplifier(rune):
        return {"ok": False, "error": "Amplifier rune tiers are fixed by their recipe"}

    rarity = str(rune.get("rarity", "common") or "common").lower()
    next_rarity = RUNE_NEXT_RARITY.get(rarity)
    if not next_rarity:
        return {"ok": False, "error": f"Cannot ascend rarity '{rarity}'"}

    if not spend_currency(player, "ascension_sigil", ASCEND_COST):
        return {"ok": False, "error": f"Need at least {ASCEND_COST} ascension_sigil to ascend"}

    rune["rarity"] = next_rarity
    rune["max_upgrade"] = int(RUNE_UPGRADE_MAX.get(next_rarity, rune.get("max_upgrade", 5)))
    return {
        "ok": True,
        "ascended": True,
        "from": rarity,
        "to": next_rarity,
        "ascension_sigil": currency_balance(player, "ascension_sigil"),
        "rune": str(rune.get("name", "") or "Rune"),
    }


# ---------- Chest-key currency (warden_key) ----------

def chest_key_upgrade_tier(rarity: str) -> str:
    """Upgrade mode: shift a chest roll's rarity one tier up (top tier stays)."""
    rarity = str(rarity or "common").lower()
    return RUNE_NEXT_RARITY.get(rarity, rarity)


def chest_key_guarantee(content_type: str) -> dict:
    """Guarantee mode: force a specific content type instead of a random roll.

    The current chest only rolls runes; the chest phase extends
    CHEST_CONTENT_TYPES and consumes this from its open flow.
    """
    content = str(content_type or "").strip().lower()
    if content not in CHEST_CONTENT_TYPES:
        return {"ok": False, "error": f"Unknown chest content type '{content}'",
                "known": sorted(CHEST_CONTENT_TYPES)}
    return {"ok": True, "guaranteed": content}
