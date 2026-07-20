"""Rolling currency exchange rates derived from real market activity.

No fixed rates: each non-gold currency's gold rate comes from what
players actually traded it for, via two sources —

1. Auction house: completed sales of currency listings (AUCTION_HISTORY
   rows with kind "currency") give a per-unit price of paid/amount.
2. Trade hub: accepted trade requests that exchanged exactly one
   currency against gold and nothing else (no items, no second
   currency); mixed trades cannot be attributed to a single currency
   and are excluded.

The rolling rate is the mean unit price of the most recent
RATE_MAX_SAMPLES completed trades inside RATE_WINDOW_SEC. With no
completed trades, the lowest active ask (open currency listings) is the
quote; with neither, the rate is unknown. Cross rates between two
currencies go through gold.
"""
from __future__ import annotations

import time

from services import trade_hub
from services.auction_house import AUCTION_HISTORY, AUCTIONS
from services.currency import BASE_CURRENCY, CURRENCIES

RATE_WINDOW_SEC = 24 * 60 * 60
RATE_MAX_SAMPLES = 20


def auction_sale_samples(history: list[dict] | None = None) -> dict[str, list[tuple[int, float]]]:
    """(timestamp, unit_price) samples per currency from completed auction sales."""
    rows = AUCTION_HISTORY if history is None else history
    samples: dict[str, list[tuple[int, float]]] = {}
    for row in rows:
        if str(row.get("kind", "") or "") != "currency":
            continue
        cid = str(row.get("currency_id", "") or "")
        amount = int(row.get("amount", 0) or 0)
        paid = int(row.get("paid", 0) or 0)
        if cid not in CURRENCIES or amount <= 0 or paid <= 0:
            continue
        samples.setdefault(cid, []).append((int(row.get("at", 0) or 0), paid / amount))
    return samples


def trade_sample(row: dict) -> tuple[str, int, float] | None:
    """(currency_id, timestamp, unit_price) from an accepted trade row that
    exchanged exactly one currency against gold and nothing else; None otherwise."""
    if str(row.get("status", "") or "") != "accepted":
        return None
    if list(row.get("offered_items", []) or []) or list(row.get("requested_items", []) or []):
        return None

    offered = dict(row.get("offered_currencies", {}) or {})
    requested = dict(row.get("requested_currencies", {}) or {})
    gold_offer = int(row.get("gold_offer", 0) or 0)
    gold_request = int(row.get("gold_request", 0) or 0)

    if offered and not requested and gold_request > 0 and gold_offer == 0 and len(offered) == 1:
        cid, amount = next(iter(offered.items()))
        gold = gold_request
    elif requested and not offered and gold_offer > 0 and gold_request == 0 and len(requested) == 1:
        cid, amount = next(iter(requested.items()))
        gold = gold_offer
    else:
        return None

    amount = int(amount or 0)
    if str(cid) not in CURRENCIES or amount <= 0:
        return None
    ts = int(row.get("updated_at", row.get("created_at", 0)) or 0)
    return (str(cid), ts, gold / amount)


def trade_hub_samples(rows: list[dict] | None = None) -> dict[str, list[tuple[int, float]]]:
    if rows is None:
        rows = trade_hub.all_requests()
    samples: dict[str, list[tuple[int, float]]] = {}
    for row in rows:
        parsed = trade_sample(row)
        if parsed is None:
            continue
        cid, ts, unit = parsed
        samples.setdefault(cid, []).append((ts, unit))
    return samples


def active_asks(listings=None) -> dict[str, float]:
    """Lowest per-unit asking price per currency across open listings."""
    rows = AUCTIONS if listings is None else listings
    asks: dict[str, float] = {}
    for listing in rows:
        if str(getattr(listing, "kind", "") or "") != "currency":
            continue
        cid = str(getattr(listing, "currency_id", "") or "")
        amount = int(getattr(listing, "amount", 0) or 0)
        price = int(getattr(listing, "price", 0) or 0)
        if cid not in CURRENCIES or amount <= 0 or price <= 0:
            continue
        unit = price / amount
        if cid not in asks or unit < asks[cid]:
            asks[cid] = unit
    return asks


def compute_rates(
    samples_by_currency: dict[str, list[tuple[int, float]]],
    asks: dict[str, float],
    now: int | None = None,
) -> dict[str, dict]:
    now = int(now if now is not None else time.time())
    cutoff = now - RATE_WINDOW_SEC

    rates: dict[str, dict] = {
        BASE_CURRENCY: {"rate_in_gold": 1.0, "samples": 0, "lowest_ask": None, "source": "base"},
    }
    for cid in CURRENCIES:
        if cid == BASE_CURRENCY:
            continue
        recent = sorted(
            [(ts, unit) for ts, unit in samples_by_currency.get(cid, []) if ts >= cutoff],
            key=lambda s: s[0],
            reverse=True,
        )[:RATE_MAX_SAMPLES]
        ask = asks.get(cid)
        if recent:
            rate = round(sum(unit for _, unit in recent) / len(recent), 4)
            source = "trades"
        elif ask is not None:
            rate = round(float(ask), 4)
            source = "listings"
        else:
            rate = None
            source = "none"
        rates[cid] = {
            "rate_in_gold": rate,
            "samples": len(recent),
            "lowest_ask": round(float(ask), 4) if ask is not None else None,
            "source": source,
        }
    return rates


def get_exchange_rates(now: int | None = None, trade_rows: list[dict] | None = None) -> dict[str, dict]:
    samples = auction_sale_samples()
    for cid, entries in trade_hub_samples(trade_rows).items():
        samples.setdefault(cid, []).extend(entries)
    return compute_rates(samples, active_asks(), now=now)


def rate_between(from_currency: str, to_currency: str, rates: dict[str, dict] | None = None) -> float | None:
    """Units of to_currency one unit of from_currency is worth, via gold."""
    rates = rates if rates is not None else get_exchange_rates()
    src = (rates.get(str(from_currency)) or {}).get("rate_in_gold")
    dst = (rates.get(str(to_currency)) or {}).get("rate_in_gold")
    if src is None or dst is None or not dst:
        return None
    return round(float(src) / float(dst), 4)
