"""Multi-currency crafting economy regression tests.

Covers: the currency catalog and wallet contract (inventory-held
quantities, gold routed to the pre-existing base field), each currency's
crafting effect (reroll via the reused crafted_supplies sink, ascension,
chest-key tier upgrade / content guarantee), currency listings on the
auction house, and the rolling exchange-rate derivation from real trade
activity rather than fixed rates.
"""
import random
import unittest

from engine.affixes import AFFIX_NAMES
from models.item import Item
from models.passive import PassiveModel
from models.player import Player
from services import auction_house
from services.auction_house import AUCTION_HISTORY, AUCTIONS, buy_item, list_currency
from services.currency import (
    ASCEND_COST,
    BASE_CURRENCY,
    CURRENCIES,
    REROLL_COST,
    add_currency,
    ascend_item,
    ascend_rune,
    chest_key_guarantee,
    chest_key_upgrade_tier,
    currency_balance,
    is_currency,
    reroll_item_affix,
    reroll_rune_effect,
    spend_currency,
    wallet,
)
from services.currency_exchange import (
    RATE_MAX_SAMPLES,
    RATE_WINDOW_SEC,
    active_asks,
    auction_sale_samples,
    compute_rates,
    get_exchange_rates,
    rate_between,
    trade_sample,
    trade_hub_samples,
)
from services.rune_system import RUNE_EFFECT_POOL, RUNE_UPGRADE_MAX
from services.stash import reroll_item_affix as stash_reroll_item_affix

NOW = 1_000_000_000


def make_item(rarity="rare", passives=None):
    return Item(
        name="Test Blade",
        rarity=rarity,
        power=10,
        passives=list(passives if passives is not None else []),
        slot="weapon",
    )


def make_affix(name="Old Affix"):
    return PassiveModel(
        name=name,
        trigger="on_hit",
        chance=1.0,
        effects=[{"type": "damage_mult", "value": 0.05, "target": "self", "chance": 1.0}],
    )


def make_rune(rarity="epic", effects=None):
    return {
        "id": "rune_test_1",
        "name": "Test Sigil",
        "rarity": rarity,
        "effects": list(effects if effects is not None else [{"type": "attack_mult", "value": 0.08}]),
        "upgrade_level": 0,
        "max_upgrade": int(RUNE_UPGRADE_MAX.get(rarity, 5)),
    }


class CurrencyCatalogAndWalletTests(unittest.TestCase):
    def test_starter_currency_set_registered(self):
        for cid in ("gold", "crafted_supplies", "ascension_sigil", "warden_key"):
            self.assertTrue(is_currency(cid))
            self.assertTrue(CURRENCIES[cid]["name"])
            self.assertTrue(CURRENCIES[cid]["use"])
        self.assertEqual(BASE_CURRENCY, "gold")
        self.assertTrue(CURRENCIES["gold"]["base"])
        self.assertFalse(is_currency("no_such_currency"))

    def test_non_gold_currencies_are_inventory_held_quantities(self):
        player = Player()
        for cid in CURRENCIES:
            if cid == BASE_CURRENCY:
                continue
            add_currency(player, cid, 3)
            # Held in the resources quantity map, not a model field/stat.
            self.assertEqual(player.resources[cid], 3)
            self.assertEqual(currency_balance(player, cid), 3)

    def test_gold_routes_to_existing_base_field(self):
        player = Player()
        add_currency(player, "gold", 25)
        self.assertEqual(player.gold, 25)
        self.assertTrue(spend_currency(player, "gold", 10))
        self.assertEqual(currency_balance(player, "gold"), 15)

    def test_spend_fails_without_balance_and_leaves_state_unchanged(self):
        player = Player()
        add_currency(player, "warden_key", 2)
        self.assertFalse(spend_currency(player, "warden_key", 3))
        self.assertEqual(currency_balance(player, "warden_key"), 2)
        self.assertFalse(spend_currency(player, "no_such_currency", 1))

    def test_wallet_lists_every_currency(self):
        player = Player()
        player.gold = 7
        add_currency(player, "ascension_sigil", 2)
        w = wallet(player)
        self.assertEqual(set(w), set(CURRENCIES))
        self.assertEqual(w["gold"], 7)
        self.assertEqual(w["ascension_sigil"], 2)
        self.assertEqual(w["warden_key"], 0)


class RerollCurrencyTests(unittest.TestCase):
    """crafted_supplies: the reroll currency, reusing the dismantle sink."""

    def test_item_affix_reroll_spends_supplies_and_replaces_affix(self):
        random.seed(11)
        player = Player()
        player.resources["crafted_supplies"] = 2
        old = make_affix()
        player.stash.append(make_item(passives=[old]))

        out = reroll_item_affix(player, 0, affix_index=0)

        self.assertTrue(out["ok"])
        self.assertEqual(out["crafted_supplies"], 2 - REROLL_COST)
        new_affix = player.stash[0].passives[0]
        self.assertIsInstance(new_affix, PassiveModel)
        self.assertIn(new_affix.name, AFFIX_NAMES)
        self.assertIsNot(new_affix, old)
        self.assertEqual(out["new_affix"], new_affix.name)

    def test_item_affix_reroll_requires_supplies(self):
        player = Player()
        player.resources["crafted_supplies"] = 0
        player.stash.append(make_item(passives=[make_affix()]))
        out = reroll_item_affix(player, 0, affix_index=0)
        self.assertFalse(out["ok"])
        self.assertIn("crafted_supplies", out["error"])
        self.assertEqual(player.stash[0].passives[0].name, "Old Affix")

    def test_item_without_affixes_cannot_reroll(self):
        player = Player()
        player.resources["crafted_supplies"] = 5
        player.stash.append(make_item(passives=[]))
        out = reroll_item_affix(player, 0)
        self.assertFalse(out["ok"])
        self.assertEqual(currency_balance(player, "crafted_supplies"), 5)

    def test_stash_module_delegates_to_currency_effect(self):
        random.seed(12)
        player = Player()
        player.resources["crafted_supplies"] = 1
        player.stash.append(make_item(passives=[make_affix()]))
        out = stash_reroll_item_affix(player, 0, affix_index=0)
        self.assertTrue(out["ok"])
        self.assertIn(player.stash[0].passives[0].name, AFFIX_NAMES)

    def test_rune_effect_reroll_draws_from_rarity_pool(self):
        random.seed(13)
        player = Player()
        player.resources["crafted_supplies"] = 1
        player.rune_items.append(make_rune(rarity="epic"))

        out = reroll_rune_effect(player, "rune_test_1", effect_index=0)

        self.assertTrue(out["ok"])
        self.assertEqual(currency_balance(player, "crafted_supplies"), 0)
        new_effect = player.rune_items[0]["effects"][0]
        pool = {entry[0]: (entry[1], entry[2]) for entry in RUNE_EFFECT_POOL["epic"]}
        self.assertIn(new_effect["type"], pool)
        lo, hi = pool[new_effect["type"]]
        self.assertGreaterEqual(new_effect["value"], lo)
        self.assertLessEqual(new_effect["value"], hi)

    def test_rune_effect_reroll_requires_supplies(self):
        player = Player()
        player.rune_items.append(make_rune())
        out = reroll_rune_effect(player, "rune_test_1", effect_index=0)
        self.assertFalse(out["ok"])


class UpgradeCurrencyTests(unittest.TestCase):
    """ascension_sigil: raises an item or rune one rarity tier."""

    def test_item_ascends_one_tier_and_spends_sigil(self):
        player = Player()
        player.resources["ascension_sigil"] = 2
        player.stash.append(make_item(rarity="common"))

        out = ascend_item(player, 0)

        self.assertTrue(out["ok"])
        self.assertEqual(out["from"], "common")
        self.assertEqual(out["to"], "uncommon")
        self.assertEqual(player.stash[0].rarity, "uncommon")
        self.assertEqual(currency_balance(player, "ascension_sigil"), 2 - ASCEND_COST)

    def test_top_tier_item_cannot_ascend(self):
        player = Player()
        player.resources["ascension_sigil"] = 1
        player.stash.append(make_item(rarity="relic"))
        out = ascend_item(player, 0)
        self.assertFalse(out["ok"])
        self.assertEqual(currency_balance(player, "ascension_sigil"), 1)

    def test_item_ascend_requires_sigil(self):
        player = Player()
        player.stash.append(make_item(rarity="rare"))
        out = ascend_item(player, 0)
        self.assertFalse(out["ok"])
        self.assertEqual(player.stash[0].rarity, "rare")

    def test_rune_ascends_one_tier_and_updates_upgrade_cap(self):
        player = Player()
        player.resources["ascension_sigil"] = 1
        player.rune_items.append(make_rune(rarity="epic"))

        out = ascend_rune(player, "rune_test_1")

        self.assertTrue(out["ok"])
        self.assertEqual(player.rune_items[0]["rarity"], "legendary")
        self.assertEqual(player.rune_items[0]["max_upgrade"], RUNE_UPGRADE_MAX["legendary"])
        self.assertEqual(currency_balance(player, "ascension_sigil"), 0)

    def test_top_tier_rune_cannot_ascend(self):
        player = Player()
        player.resources["ascension_sigil"] = 1
        player.rune_items.append(make_rune(rarity="relic"))
        out = ascend_rune(player, "rune_test_1")
        self.assertFalse(out["ok"])


class ChestKeyCurrencyTests(unittest.TestCase):
    """warden_key: chest tier upgrade or guaranteed content type."""

    def test_upgrade_mode_shifts_roll_one_tier(self):
        self.assertEqual(chest_key_upgrade_tier("common"), "rare")
        self.assertEqual(chest_key_upgrade_tier("legendary"), "mythic")
        # Top tier has nowhere to go.
        self.assertEqual(chest_key_upgrade_tier("relic"), "relic")

    def test_guarantee_mode_validates_content_type(self):
        out = chest_key_guarantee("rune")
        self.assertTrue(out["ok"])
        self.assertEqual(out["guaranteed"], "rune")
        bad = chest_key_guarantee("mount")
        self.assertFalse(bad["ok"])
        self.assertIn("rune", bad["known"])


class CurrencyAuctionTests(unittest.TestCase):
    def setUp(self):
        AUCTIONS.clear()
        AUCTION_HISTORY.clear()

    def test_currency_listing_escrows_stack_and_sells_for_gold(self):
        seller = Player()
        seller.resources["ascension_sigil"] = 10
        listing = list_currency(seller, "ascension_sigil", 4, 100, seller="alice")
        self.assertNotIn("error", listing)
        self.assertEqual(currency_balance(seller, "ascension_sigil"), 6)
        self.assertFalse(listing["allow_item_offers"])

        buyer = Player()
        buyer.gold = 150
        out = buy_item(buyer, listing["id"], buyer="bob")
        self.assertTrue(out["success"])
        self.assertEqual(buyer.gold, 50)
        self.assertEqual(currency_balance(buyer, "ascension_sigil"), 4)

        sale = AUCTION_HISTORY[-1]
        self.assertEqual(sale["kind"], "currency")
        self.assertEqual(sale["currency_id"], "ascension_sigil")
        self.assertEqual(sale["amount"], 4)
        self.assertEqual(sale["paid"], 100)

    def test_gold_and_unknown_currencies_cannot_be_listed(self):
        player = Player()
        player.gold = 500
        self.assertIn("error", list_currency(player, "gold", 10, 5))
        self.assertIn("error", list_currency(player, "no_such_currency", 1, 5))

    def test_listing_requires_balance(self):
        player = Player()
        player.resources["warden_key"] = 1
        out = list_currency(player, "warden_key", 5, 50)
        self.assertIn("error", out)
        self.assertEqual(currency_balance(player, "warden_key"), 1)

    def test_cancel_returns_currency_stack(self):
        player = Player()
        player.resources["warden_key"] = 3
        listing = list_currency(player, "warden_key", 3, 30)
        out = auction_house.cancel_listing(player, listing["id"])
        self.assertTrue(out["ok"])
        self.assertEqual(currency_balance(player, "warden_key"), 3)


class ExchangeRateTests(unittest.TestCase):
    def setUp(self):
        AUCTIONS.clear()
        AUCTION_HISTORY.clear()

    def test_rate_is_mean_unit_price_of_recent_trades(self):
        samples = {
            "ascension_sigil": [(NOW - 10, 50.0), (NOW - 20, 40.0), (NOW - 30, 60.0)],
        }
        rates = compute_rates(samples, {}, now=NOW)
        entry = rates["ascension_sigil"]
        self.assertEqual(entry["rate_in_gold"], 50.0)
        self.assertEqual(entry["samples"], 3)
        self.assertEqual(entry["source"], "trades")
        self.assertEqual(rates[BASE_CURRENCY]["rate_in_gold"], 1.0)

    def test_rolling_window_drops_stale_samples_and_caps_count(self):
        stale = (NOW - RATE_WINDOW_SEC - 1, 999.0)
        fresh = [(NOW - i, 10.0) for i in range(RATE_MAX_SAMPLES + 5)]
        rates = compute_rates({"warden_key": [stale] + fresh}, {}, now=NOW)
        entry = rates["warden_key"]
        self.assertEqual(entry["rate_in_gold"], 10.0)
        self.assertEqual(entry["samples"], RATE_MAX_SAMPLES)

    def test_listings_quote_when_no_completed_trades(self):
        rates = compute_rates({}, {"crafted_supplies": 12.5}, now=NOW)
        entry = rates["crafted_supplies"]
        self.assertEqual(entry["rate_in_gold"], 12.5)
        self.assertEqual(entry["source"], "listings")
        self.assertEqual(entry["lowest_ask"], 12.5)

    def test_unknown_rate_without_any_activity(self):
        rates = compute_rates({}, {}, now=NOW)
        self.assertIsNone(rates["warden_key"]["rate_in_gold"])
        self.assertEqual(rates["warden_key"]["source"], "none")

    def test_auction_activity_flows_into_samples_and_asks(self):
        seller = Player()
        seller.resources["ascension_sigil"] = 10
        seller.resources["warden_key"] = 5
        sold = list_currency(seller, "ascension_sigil", 2, 100, seller="alice")
        list_currency(seller, "warden_key", 5, 200, seller="alice")

        buyer = Player()
        buyer.gold = 100
        buy_item(buyer, sold["id"], buyer="bob")

        samples = auction_sale_samples()
        self.assertEqual(len(samples["ascension_sigil"]), 1)
        self.assertEqual(samples["ascension_sigil"][0][1], 50.0)

        asks = active_asks()
        self.assertEqual(asks["warden_key"], 40.0)
        self.assertNotIn("ascension_sigil", asks)

    def test_trade_hub_rows_yield_samples_only_for_pure_currency_gold_trades(self):
        pure = {
            "status": "accepted",
            "offered_items": [],
            "requested_items": [],
            "offered_currencies": {"warden_key": 2},
            "requested_currencies": {},
            "gold_offer": 0,
            "gold_request": 90,
            "updated_at": NOW - 5,
        }
        reversed_direction = {
            "status": "accepted",
            "offered_items": [],
            "requested_items": [],
            "offered_currencies": {},
            "requested_currencies": {"crafted_supplies": 3},
            "gold_offer": 30,
            "gold_request": 0,
            "updated_at": NOW - 6,
        }
        mixed_with_items = dict(pure, offered_items=[{"name": "Blade"}])
        still_pending = dict(pure, status="pending")

        self.assertEqual(trade_sample(pure), ("warden_key", NOW - 5, 45.0))
        self.assertEqual(trade_sample(reversed_direction), ("crafted_supplies", NOW - 6, 10.0))
        self.assertIsNone(trade_sample(mixed_with_items))
        self.assertIsNone(trade_sample(still_pending))

        samples = trade_hub_samples([pure, reversed_direction, mixed_with_items, still_pending])
        self.assertEqual(samples["warden_key"], [(NOW - 5, 45.0)])
        self.assertEqual(samples["crafted_supplies"], [(NOW - 6, 10.0)])

    def test_get_exchange_rates_merges_auction_and_trade_activity(self):
        seller = Player()
        seller.resources["warden_key"] = 2
        listing = list_currency(seller, "warden_key", 2, 60, seller="alice")
        buyer = Player()
        buyer.gold = 60
        buy_item(buyer, listing["id"], buyer="bob")

        trade_rows = [{
            "status": "accepted",
            "offered_items": [],
            "requested_items": [],
            "offered_currencies": {"warden_key": 1},
            "requested_currencies": {},
            "gold_offer": 0,
            "gold_request": 50,
            "updated_at": int(AUCTION_HISTORY[-1]["at"]),
        }]
        rates = get_exchange_rates(trade_rows=trade_rows)
        entry = rates["warden_key"]
        # Auction sale at 30/unit and trade at 50/unit average to 40.
        self.assertEqual(entry["rate_in_gold"], 40.0)
        self.assertEqual(entry["samples"], 2)
        self.assertEqual(entry["source"], "trades")

    def test_cross_rates_derive_through_gold(self):
        rates = compute_rates(
            {
                "ascension_sigil": [(NOW, 100.0)],
                "crafted_supplies": [(NOW, 25.0)],
            },
            {},
            now=NOW,
        )
        self.assertEqual(rate_between("ascension_sigil", "crafted_supplies", rates), 4.0)
        self.assertEqual(rate_between("ascension_sigil", "gold", rates), 100.0)
        self.assertIsNone(rate_between("ascension_sigil", "warden_key", rates))


if __name__ == "__main__":
    unittest.main()
