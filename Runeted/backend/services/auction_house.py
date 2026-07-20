import time
from typing import List

from models.auction import AuctionListing
from models.player import Player
from services.currency import BASE_CURRENCY, CURRENCIES, add_currency, currency_balance, is_currency, spend_currency
from services.stash import can_list_on_market
from utils.validators import validate_item_object

# In-memory auction board
AUCTIONS: List[AuctionListing] = []
AUCTION_HISTORY: List[dict] = []

RARITY_MULT = {
    "common": 1.0,
    "rare": 1.4,
    "epic": 2.0,
    "legendary": 3.0,
    "mythic": 4.0,
    "supreme": 4.8,
    "relic": 5.5,
}


def _to_int(value, fallback: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _normalize_price(price: int) -> int:
    return max(1, _to_int(price, 1))


def _barter_threshold(price: int, kind: str) -> int:
    base = max(1, int(price))
    factor = 0.9 if kind == "item" else 1.0
    return max(1, int(base * factor))


def _market_power(item: object) -> int:
    if not item:
        return 0
    rarity = str(getattr(item, "rarity", "") or "").lower()
    power = _to_int(getattr(item, "power", 0), 0)
    mult = float(RARITY_MULT.get(rarity, 1.0))
    return max(0, int(power * mult * 10))


def _grant_listing(player: Player, listing: AuctionListing):
    if str(listing.kind or "item") == "currency":
        cid = str(listing.currency_id or "")
        amount = max(0, int(listing.amount or 0))
        add_currency(player, cid, amount)
        return {"kind": "currency", "currency_id": cid, "amount": amount}
    if str(listing.kind or "item") == "rune":
        rune = dict(listing.rune or {})
        if rune:
            player.rune_items.append(rune)
            return {"kind": "rune", "rune": rune}
        return {"kind": "rune", "rune": None}

    item = listing.item
    if item is not None:
        safe_item = validate_item_object(item)
        player.stash.append(safe_item)
        item = safe_item
    return {"kind": "item", "item": item}


def _find_listing(auction_id: str):
    for listing in AUCTIONS:
        if listing.id == auction_id:
            return listing
    return None


def _record_sale(listing: AuctionListing, method: str, paid: int = 0, offered_power: int = 0, buyer: str = ""):
    label = ""
    if str(listing.kind or "item") == "rune":
        label = str((listing.rune or {}).get("name", "") or "Rune")
    elif str(listing.kind or "item") == "currency":
        meta = CURRENCIES.get(str(listing.currency_id or ""), {})
        label = str(meta.get("name", "") or listing.currency_id or "Currency")
    else:
        label = str(getattr(listing.item, "name", "") or "Item")
    AUCTION_HISTORY.append({
        "auction_id": str(listing.id or ""),
        "seller": str(listing.seller or "player"),
        "buyer": str(buyer or ""),
        "kind": str(listing.kind or "item"),
        "name": label,
        "currency_id": str(listing.currency_id or ""),
        "amount": int(listing.amount or 0),
        "method": str(method or "gold"),
        "price": int(listing.price or 0),
        "paid": int(paid or 0),
        "offered_power": int(offered_power or 0),
        "at": int(time.time()),
    })
    if len(AUCTION_HISTORY) > 120:
        del AUCTION_HISTORY[:-120]


def _parse_offer_indices(item_indices) -> List[int]:
    if isinstance(item_indices, list):
        raw = item_indices
    else:
        raw = [item_indices]
    out: List[int] = []
    for v in raw:
        try:
            out.append(int(v))
        except Exception:
            continue
    # Keep insertion order while removing duplicates.
    seen = set()
    uniq = []
    for idx in out:
        if idx in seen:
            continue
        seen.add(idx)
        uniq.append(idx)
    return uniq


def list_item(player: Player, item_index: int, price: int, allow_item_offers: bool = True, seller: str = "player"):
    item_index = _to_int(item_index, -1)
    if item_index < 0 or item_index >= len(player.stash):
        return {"error": "Invalid item index"}

    item = player.stash[item_index]
    if not can_list_on_market(item):
        return {"error": "Item rarity is below the market floor and cannot be listed"}

    price = _normalize_price(price)
    item = player.stash.pop(item_index)
    listing = AuctionListing.create(
        item=item,
        price=price,
        seller=str(seller or "player"),
        allow_item_offers=bool(allow_item_offers),
        min_offer_power=_barter_threshold(price, "item"),
    )

    AUCTIONS.append(listing)
    return listing.model_dump()


def list_rune(player: Player, rune_id: str, price: int, allow_item_offers: bool = True, seller: str = "player"):
    rid = str(rune_id or "").strip()
    if not rid:
        return {"error": "Missing rune_id"}

    rune = None
    kept = []
    for r in (player.rune_items or []):
        if rune is None and str(r.get("id", "")) == rid:
            rune = r
        else:
            kept.append(r)
    if rune is None:
        return {"error": "Rune not found"}

    rarity = str(rune.get("rarity", "common") or "common").lower()
    if rarity in {"common", "uncommon"}:
        return {"error": "Rune rarity is below the market floor and cannot be listed"}

    player.rune_items = kept
    player.rune_loadout = [None if str(x or "") == rid else x for x in (player.rune_loadout or [])]
    player.sync_rune_loadout()

    price = _normalize_price(price)
    listing = AuctionListing.create_rune(
        rune=rune,
        price=price,
        seller=str(seller or "player"),
        allow_item_offers=bool(allow_item_offers),
        min_offer_power=_barter_threshold(price, "rune"),
    )
    AUCTIONS.append(listing)
    return listing.model_dump()

def list_currency(player: Player, currency_id: str, amount: int, price: int, seller: str = "player"):
    cid = str(currency_id or "").strip()
    if not is_currency(cid):
        return {"error": "Unknown currency"}
    if cid == BASE_CURRENCY:
        return {"error": "Gold is the trade medium and cannot be listed"}

    amount = _to_int(amount, 0)
    if amount <= 0:
        return {"error": "Amount must be positive"}
    if currency_balance(player, cid) < amount:
        return {"error": "Not enough currency", "required": amount, "current": currency_balance(player, cid)}

    price = _normalize_price(price)
    spend_currency(player, cid, amount)
    listing = AuctionListing.create_currency(
        currency_id=cid,
        amount=amount,
        price=price,
        seller=str(seller or "player"),
    )
    AUCTIONS.append(listing)
    return listing.model_dump()


def get_auctions(seller: str | None = None):
    seller_id = str(seller or "").strip().lower()
    rows = AUCTIONS
    if seller_id:
        rows = [a for a in AUCTIONS if str(a.seller or "").strip().lower() == seller_id]
    return [a.model_dump() for a in rows]


def get_auction_history(seller: str | None = None):
    seller_id = str(seller or "").strip().lower()
    rows = list(AUCTION_HISTORY)
    if seller_id:
        rows = [row for row in rows if str(row.get("seller", "")).strip().lower() == seller_id]
    rows = sorted(rows, key=lambda row: int(row.get("at", 0) or 0), reverse=True)
    total_gold = sum(int(row.get("paid", 0) or 0) for row in rows if str(row.get("method", "") or "") == "gold")
    total_trades = len(rows)
    return {
        "sales": rows[:12],
        "total_gold": total_gold,
        "total_trades": total_trades,
    }


def cancel_listing(player: Player, auction_id: str, seller: str = ""):
    listing = _find_listing(auction_id)
    if not listing:
        return {"error": "Auction not found"}
    if seller and str(listing.seller or "").strip().lower() != str(seller or "").strip().lower():
        return {"error": "Cannot cancel another account's listing"}
    returned = _grant_listing(player, listing)
    AUCTIONS.remove(listing)
    return {"ok": True, "cancelled": listing.model_dump(), "returned": returned}

def buy_item(player: Player, auction_id: str, buyer: str = ""):
    listing = _find_listing(auction_id)
    if not listing:
        return {"error": "Auction not found"}
    if buyer and str(listing.seller or "").strip().lower() == str(buyer or "").strip().lower():
        return {"error": "Cannot buy your own listing"}

    price = max(1, _to_int(listing.price, 1))
    if int(player.gold) < price:
        return {"error": "Not enough gold", "required": price, "current": int(player.gold)}

    player.gold = int(player.gold) - price
    received = _grant_listing(player, listing)
    AUCTIONS.remove(listing)
    _record_sale(listing, method="gold", paid=price, buyer=buyer)
    return {"success": True, "method": "gold", "paid": price, "gold": int(player.gold), "received": received}


def offer_items(player: Player, auction_id: str, item_indices, buyer: str = ""):
    listing = _find_listing(auction_id)
    if not listing:
        return {"error": "Auction not found"}
    if buyer and str(listing.seller or "").strip().lower() == str(buyer or "").strip().lower():
        return {"error": "Cannot offer on your own listing"}

    if not bool(getattr(listing, "allow_item_offers", False)):
        return {"error": "Item offers disabled for this listing"}

    indices = _parse_offer_indices(item_indices)
    if not indices:
        return {"error": "No offer items selected"}

    invalid = [i for i in indices if i < 0 or i >= len(player.stash)]
    if invalid:
        return {"error": "Invalid stash index in offer", "invalid": invalid}

    offered_items = [player.stash[i] for i in indices]
    offered_power = sum(_market_power(it) for it in offered_items)
    required = max(1, _to_int(getattr(listing, "min_offer_power", 0), 1))
    if offered_power < required:
        return {
            "ok": False,
            "accepted": False,
            "required_offer_power": required,
            "offered_power": offered_power,
        }

    # Remove offered items from stash (descending to keep indices stable).
    for idx in sorted(indices, reverse=True):
        player.stash.pop(idx)

    received = _grant_listing(player, listing)
    AUCTIONS.remove(listing)
    _record_sale(listing, method="item_offer", offered_power=offered_power, buyer=buyer)
    return {
        "ok": True,
        "accepted": True,
        "method": "item_offer",
        "offered_count": len(offered_items),
        "offered_power": offered_power,
        "received": received,
    }
