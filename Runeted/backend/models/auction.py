import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field

from models.item import Item

class AuctionListing(BaseModel):
    id: str
    kind: Literal["item", "rune", "currency"] = "item"
    item: Optional[Item] = None
    rune: Optional[dict] = None
    currency_id: Optional[str] = None
    amount: int = 0
    price: int
    seller: str
    allow_item_offers: bool = True
    min_offer_power: int = 0

    @staticmethod
    def create(item: Item, price: int, seller: str, allow_item_offers: bool = True, min_offer_power: int = 0):
        return AuctionListing(
            id=str(uuid.uuid4()),
            kind="item",
            item=item,
            rune=None,
            price=price,
            seller=seller,
            allow_item_offers=allow_item_offers,
            min_offer_power=max(0, int(min_offer_power or 0)),
        )

    @staticmethod
    def create_currency(currency_id: str, amount: int, price: int, seller: str):
        # Currency sells for gold only: item barter would muddy the
        # exchange-rate samples derived from these sales.
        return AuctionListing(
            id=str(uuid.uuid4()),
            kind="currency",
            item=None,
            rune=None,
            currency_id=str(currency_id),
            amount=max(1, int(amount or 1)),
            price=price,
            seller=seller,
            allow_item_offers=False,
            min_offer_power=0,
        )

    @staticmethod
    def create_rune(rune: dict, price: int, seller: str, allow_item_offers: bool = True, min_offer_power: int = 0):
        return AuctionListing(
            id=str(uuid.uuid4()),
            kind="rune",
            item=None,
            rune=dict(rune or {}),
            price=price,
            seller=seller,
            allow_item_offers=allow_item_offers,
            min_offer_power=max(0, int(min_offer_power or 0)),
        )
