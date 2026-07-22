"""Non-combat special-event regression tests (core/special_events.py +
battle_app.py wiring).

Covers: the encounter-kind gate and event-type roll, that every event
type requires an explicit choice (engage vs. walk away) before anything
resolves -- nothing auto-resolves off the encounter roll alone -- that
each event type's outcome is gated by exactly the correct single stat
(charisma for the social `merchant` event, luck for the environmental/
risk `shrine`/`hazard`/`treasure` events) with the *other* stat proven
to have no effect, failure staying possible even at maxed-out stats,
every event/tier's reward staying within its declared table (a
hard-bounds property, not a probability curve), and the end-to-end API
flow for both a fresh hub start and a push-your-luck continuation
landing on an event instead of a fight.
"""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import battle_app
from _account_test_helpers import authed_client, bundle_for
from core.gauntlet import PendingPool
from core.player_state import ATTRIBUTES, PlayerState
from core.special_events import (
    BASELINE_STAT,
    EVENT_CHANCE,
    EVENT_GOVERNING_STAT,
    EVENT_TYPES,
    MAX_CHARISMA_BONUS,
    MAX_LUCK_BONUS,
    OUTCOME_TIERS,
    REWARD_TABLES,
    STAT_CHARISMA,
    STAT_LUCK,
    TIER_CUTOFFS,
    event_flavor,
    resolve_event,
    roll_encounter_kind,
    roll_event_type,
    roll_outcome_tier,
    stat_bonus,
)
from core.wallet import Wallet

TIER_ORDER = {t: i for i, t in enumerate(OUTCOME_TIERS)}

CHARISMA_GATED_TYPES = tuple(t for t in EVENT_TYPES if EVENT_GOVERNING_STAT[t] == STAT_CHARISMA)
LUCK_GATED_TYPES = tuple(t for t in EVENT_TYPES if EVENT_GOVERNING_STAT[t] == STAT_LUCK)

# A stat value high enough to saturate either bonus cap (0.045/point and
# 0.028/point respectively -- 20 clears both with room to spare).
MAXED_STAT = 20

# random.Random(seed).random()'s first draw, precomputed, so API tests
# below can force a known tier without mocking the RNG itself:
#   seed 1 -> 0.1343 (fail)     seed 5 -> 0.6229 (partial)
#   seed 0 -> 0.8442 (success)  seed 2 -> 0.9560 (great)
SEED_FOR_TIER = {"fail": 1, "partial": 5, "success": 0, "great": 2}


class FixedRng:
    """Stands in for random.Random, pinning the single .random() draw
    core/special_events.py's tier roll consumes."""

    def __init__(self, value):
        self._value = float(value)

    def random(self):
        return self._value


# ---------- Unit tests: core/special_events.py ----------

class GoverningStatMapTests(unittest.TestCase):
    """The one thing the whole split hinges on: which event types are
    social (charisma) vs. environmental/risk (luck)."""

    def test_every_event_type_is_mapped_to_a_declared_stat(self):
        for event_type in EVENT_TYPES:
            self.assertIn(EVENT_GOVERNING_STAT[event_type], (STAT_CHARISMA, STAT_LUCK), event_type)

    def test_merchant_is_the_social_charisma_gated_event(self):
        self.assertEqual(EVENT_GOVERNING_STAT["merchant"], STAT_CHARISMA)

    def test_shrine_hazard_treasure_are_environmental_luck_gated_events(self):
        for event_type in ("shrine", "hazard", "treasure"):
            self.assertEqual(EVENT_GOVERNING_STAT[event_type], STAT_LUCK, event_type)

    def test_event_flavor_reports_the_correct_governing_stat(self):
        for event_type in EVENT_TYPES:
            self.assertEqual(event_flavor(event_type)["governing_stat"], EVENT_GOVERNING_STAT[event_type])

    def test_event_flavor_rejects_an_unknown_type(self):
        with self.assertRaises(ValueError):
            event_flavor("not_a_real_event")


class StatBonusTests(unittest.TestCase):
    def test_baseline_stats_give_zero_bonus_for_every_event_type(self):
        for event_type in EVENT_TYPES:
            self.assertEqual(stat_bonus(event_type, BASELINE_STAT, BASELINE_STAT), 0.0, event_type)

    def test_charisma_gated_events_ignore_luck_entirely(self):
        for event_type in CHARISMA_GATED_TYPES:
            self.assertEqual(stat_bonus(event_type, BASELINE_STAT, MAXED_STAT), 0.0, event_type)
            self.assertGreater(stat_bonus(event_type, MAXED_STAT, BASELINE_STAT), 0.0, event_type)

    def test_luck_gated_events_ignore_charisma_entirely(self):
        for event_type in LUCK_GATED_TYPES:
            self.assertEqual(stat_bonus(event_type, MAXED_STAT, BASELINE_STAT), 0.0, event_type)
            self.assertGreater(stat_bonus(event_type, BASELINE_STAT, MAXED_STAT), 0.0, event_type)

    def test_charisma_bonus_never_exceeds_its_declared_cap(self):
        for charisma in (5, 20, 100, 10_000):
            self.assertLessEqual(stat_bonus("merchant", charisma, 0), MAX_CHARISMA_BONUS)

    def test_luck_bonus_never_exceeds_its_declared_cap(self):
        for luck in (5, 20, 100, 10_000):
            self.assertLessEqual(stat_bonus("hazard", 0, luck), MAX_LUCK_BONUS)

    def test_both_caps_are_kept_below_the_fail_cutoff_so_failure_stays_possible(self):
        fail_cutoff = TIER_CUTOFFS[0][0]
        self.assertLess(MAX_CHARISMA_BONUS, fail_cutoff)
        self.assertLess(MAX_LUCK_BONUS, fail_cutoff)


class OutcomeTierRollTests(unittest.TestCase):
    def test_higher_governing_stat_never_produces_a_worse_tier_for_the_same_roll(self):
        for event_type in EVENT_TYPES:
            for raw in (0.0, 0.1, 0.2, 0.34, 0.35, 0.5, 0.64, 0.65, 0.89, 0.9, 0.99):
                baseline_tier = roll_outcome_tier(event_type, BASELINE_STAT, BASELINE_STAT, FixedRng(raw))
                maxed_tier = roll_outcome_tier(event_type, MAXED_STAT, MAXED_STAT, FixedRng(raw))
                self.assertGreaterEqual(
                    TIER_ORDER[maxed_tier], TIER_ORDER[baseline_tier], (event_type, raw)
                )

    def test_only_the_governing_stat_ever_changes_a_charisma_gated_events_tier(self):
        for event_type in CHARISMA_GATED_TYPES:
            for raw in (0.10, 0.30, 0.34, 0.60, 0.64, 0.88):
                baseline = roll_outcome_tier(event_type, BASELINE_STAT, BASELINE_STAT, FixedRng(raw))
                luck_only = roll_outcome_tier(event_type, BASELINE_STAT, MAXED_STAT, FixedRng(raw))
                self.assertEqual(luck_only, baseline, (event_type, raw))

    def test_only_the_governing_stat_ever_changes_a_luck_gated_events_tier(self):
        for event_type in LUCK_GATED_TYPES:
            for raw in (0.10, 0.30, 0.34, 0.60, 0.64, 0.88):
                baseline = roll_outcome_tier(event_type, BASELINE_STAT, BASELINE_STAT, FixedRng(raw))
                charisma_only = roll_outcome_tier(event_type, MAXED_STAT, BASELINE_STAT, FixedRng(raw))
                self.assertEqual(charisma_only, baseline, (event_type, raw))

    def test_governing_stat_meaningfully_improves_at_least_some_rolls(self):
        # Not just a tie everywhere -- some roll must actually cross a
        # tier boundary once the governing stat is maxed, or it wouldn't
        # be "meaningfully" improving anything.
        for event_type in EVENT_TYPES:
            improved = any(
                TIER_ORDER[roll_outcome_tier(event_type, MAXED_STAT, MAXED_STAT, FixedRng(raw))]
                > TIER_ORDER[roll_outcome_tier(event_type, BASELINE_STAT, BASELINE_STAT, FixedRng(raw))]
                for raw in (0.10, 0.30, 0.34, 0.60, 0.64, 0.88)
            )
            self.assertTrue(improved, event_type)

    def test_failure_stays_possible_even_at_extreme_stats(self):
        for event_type in EVENT_TYPES:
            self.assertEqual(roll_outcome_tier(event_type, 10_000, 10_000, FixedRng(0.0)), "fail", event_type)

    def test_great_is_reachable_at_baseline_stats(self):
        for event_type in EVENT_TYPES:
            self.assertEqual(
                roll_outcome_tier(event_type, BASELINE_STAT, BASELINE_STAT, FixedRng(0.99)), "great", event_type
            )


class EncounterGateTests(unittest.TestCase):
    def test_just_under_the_event_chance_is_an_event(self):
        self.assertEqual(roll_encounter_kind(FixedRng(EVENT_CHANCE - 0.001)), "event")

    def test_at_or_above_the_event_chance_is_combat(self):
        self.assertEqual(roll_encounter_kind(FixedRng(EVENT_CHANCE)), "combat")
        self.assertEqual(roll_encounter_kind(FixedRng(EVENT_CHANCE + 0.001)), "combat")

    def test_event_type_is_always_one_of_the_declared_types(self):
        import random
        rng = random.Random(0)
        for _ in range(200):
            self.assertIn(roll_event_type(rng), EVENT_TYPES)


class RewardBoundsTests(unittest.TestCase):
    """A hard-clamp property, not a probability curve -- every event's
    outcome at every tier must come from exactly its declared table,
    services/chest.py's tiered-bounds tests' approach applied here."""

    def test_every_declared_event_and_tier_resolves_to_its_exact_table_entry(self):
        raw_for_tier = {"fail": 0.0, "partial": 0.4, "success": 0.7, "great": 0.95}
        for event_type in EVENT_TYPES:
            for tier in OUTCOME_TIERS:
                outcome = resolve_event(event_type, BASELINE_STAT, BASELINE_STAT, FixedRng(raw_for_tier[tier]))
                self.assertEqual(outcome.tier, tier, (event_type, tier))
                self.assertEqual(outcome.governing_stat, EVENT_GOVERNING_STAT[event_type])
                row = REWARD_TABLES[event_type][tier]
                if event_type == "merchant":
                    self.assertEqual(outcome.gold_delta, row["gold"])
                    self.assertEqual(outcome.resource_id, row["resource_id"])
                    self.assertEqual(outcome.resource_amount, row["resource_amount"])
                elif event_type == "shrine":
                    self.assertEqual(outcome.gold_delta, row["gold"])
                    self.assertEqual(outcome.buff_rounds, row["buff_rounds"])
                    self.assertEqual(outcome.buff_mult, row["buff_mult"])
                elif event_type == "hazard":
                    self.assertEqual(outcome.gold_delta, row["gold"])
                    self.assertEqual(outcome.hp_loss_pct, row["hp_loss_pct"])
                elif event_type == "treasure":
                    self.assertEqual(outcome.chest_rarity, row["chest"])

    def test_unknown_event_type_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_event("not_a_real_event", 5, 5, FixedRng(0.5))

    def test_hazard_hp_loss_never_exceeds_its_worst_declared_tier(self):
        worst = max(row["hp_loss_pct"] for row in REWARD_TABLES["hazard"].values())
        self.assertEqual(worst, REWARD_TABLES["hazard"][OUTCOME_TIERS[0]]["hp_loss_pct"])  # fail is worst
        for row in REWARD_TABLES["hazard"].values():
            self.assertLessEqual(row["hp_loss_pct"], worst)
            self.assertGreaterEqual(row["hp_loss_pct"], 0.0)


class CharismaAttributeTests(unittest.TestCase):
    def test_charisma_exists_with_the_same_baseline_as_other_attributes(self):
        self.assertEqual(PlayerState().charisma, 0)
        self.assertIn("charisma", ATTRIBUTES)

    def test_charisma_is_spendable_like_any_other_attribute(self):
        player = PlayerState(stat_points=2)
        self.assertTrue(player.spend_stat("charisma", 2))
        self.assertEqual(player.charisma, 2)
        self.assertEqual(player.stat_points, 0)


# ---------- API integration ----------

def client() -> TestClient:
    # A brand-new, never-before-used account per call -- nothing stale
    # to reset, unlike the single shared global this used to reach into.
    return authed_client()


def force_event_type(event_type: str):
    """Patches battle_app's imported roll functions so the next
    encounter roll deterministically lands on an event of this type;
    the lambdas below don't touch `rng` at all, so it stays completely
    unconsumed -- the outcome *tier*, rolled later on engage, is still
    a real draw from the request's seed (see SEED_FOR_TIER), not mocked."""
    return patch.multiple(
        "battle_app",
        roll_encounter_kind=lambda rng: "event",
        roll_event_type=lambda rng: event_type,
    )


class EventChoiceGateTests(unittest.TestCase):
    """Nothing about an event ever resolves off the encounter roll
    alone -- landing on one only ever produces an unresolved choice,
    and only engaging (never walking away) rolls an outcome."""

    def test_landing_on_an_event_returns_an_unresolved_choice_not_an_outcome(self):
        c = client()
        with force_event_type("treasure"):
            res = c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["kind"], "event")
        event = body["event"]
        self.assertEqual(event["type"], "treasure")
        self.assertFalse(event["resolved"])
        self.assertFalse(event["walked_away"])
        self.assertIsNone(event["tier"])
        self.assertIsNone(event["chest_rarity"])
        # Nothing granted yet, and no battle was created for the event.
        self.assertEqual(c.get("/api/battle/state").status_code, 404)
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["chests"], {})

    def test_every_declared_event_type_lands_as_an_unresolved_choice(self):
        for event_type in EVENT_TYPES:
            c = client()
            with force_event_type(event_type):
                res = c.post("/api/battle/start", json={"seed": 0})
            event = res.json()["event"]
            self.assertEqual(event["type"], event_type)
            self.assertFalse(event["resolved"], event_type)

    def test_engaging_rolls_the_outcome_and_applies_it(self):
        c = client()
        with force_event_type("treasure"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})
        res = c.post("/api/event/engage")
        self.assertEqual(res.status_code, 200, res.text)
        event = res.json()["event"]
        self.assertTrue(event["resolved"])
        self.assertFalse(event["walked_away"])
        self.assertEqual(event["tier"], "success")
        self.assertEqual(event["chest_rarity"], "rare")
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["chests"], {"rare": 1})

    def test_walking_away_resolves_with_no_roll_and_no_effect(self):
        c = client()
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        res = c.post("/api/event/walk_away")
        self.assertEqual(res.status_code, 200, res.text)
        event = res.json()["event"]
        self.assertTrue(event["resolved"])
        self.assertTrue(event["walked_away"])
        self.assertIsNone(event["tier"])
        self.assertEqual(event["gold_delta"], 0)
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["gold"], 0)
        self.assertEqual(wallet["resources"], {})

    def test_engage_with_no_pending_event_is_rejected(self):
        c = client()
        res = c.post("/api/event/engage")
        self.assertEqual(res.status_code, 409)

    def test_walk_away_with_no_pending_event_is_rejected(self):
        c = client()
        res = c.post("/api/event/walk_away")
        self.assertEqual(res.status_code, 409)

    def test_engaging_twice_the_second_call_is_rejected(self):
        c = client()
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        c.post("/api/event/engage")
        res = c.post("/api/event/engage")
        self.assertEqual(res.status_code, 409)

    def test_walking_away_then_engaging_is_rejected(self):
        c = client()
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        c.post("/api/event/walk_away")
        res = c.post("/api/event/engage")
        self.assertEqual(res.status_code, 409)

    def test_event_state_reflects_the_unresolved_choice_on_a_fresh_reload(self):
        c = client()
        with force_event_type("shrine"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})
        res = c.get("/api/event/state")
        self.assertEqual(res.status_code, 200)
        event = res.json()["event"]
        self.assertEqual(event["type"], "shrine")
        self.assertFalse(event["resolved"])

    def test_event_state_reflects_the_resolved_outcome_after_engaging(self):
        c = client()
        with force_event_type("treasure"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        c.post("/api/event/engage")
        res = c.get("/api/event/state")
        self.assertTrue(res.json()["event"]["resolved"])
        self.assertEqual(res.json()["event"]["chest_rarity"], "epic")

    def test_starting_a_fresh_battle_abandons_a_stale_pending_choice(self):
        c = client()
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        # Walk away from the hub instead of resolving the event: start a
        # brand new encounter, forced onto combat this time.
        with patch("battle_app.roll_encounter_kind", return_value="combat"):
            c.post("/api/battle/start", json={"archetype": "brute", "seed": 2})
        # The abandoned choice is no longer reachable.
        self.assertEqual(c.post("/api/event/engage").status_code, 409)
        self.assertEqual(c.post("/api/event/walk_away").status_code, 409)


class EventChoiceMarkupSanityTests(unittest.TestCase):
    """The governing-stat gate is exercised end-to-end once through the
    real API/RNG path, on top of the exhaustive unit coverage above."""

    def test_merchant_tier_improves_with_charisma_but_not_with_luck(self):
        c = client()
        bundle_for(c)["player"].charisma = 10  # saturates MAX_CHARISMA_BONUS
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})  # raw ~0.1344
        event = c.post("/api/event/engage").json()["event"]
        self.assertEqual(event["tier"], "partial")  # 0.1344 + 0.22 bonus crosses the 0.35 fail cutoff

        c2 = client()
        bundle_for(c2)["player"].luck = 10  # should have zero effect on a charisma-gated event
        with force_event_type("merchant"):
            c2.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        event2 = c2.post("/api/event/engage").json()["event"]
        self.assertEqual(event2["tier"], "fail")

    def test_hazard_tier_improves_with_luck_but_not_with_charisma(self):
        c = client()
        bundle_for(c)["player"].luck = 10  # saturates MAX_LUCK_BONUS
        with force_event_type("hazard"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})  # raw ~0.1344
        event = c.post("/api/event/engage").json()["event"]
        self.assertEqual(event["tier"], "partial")

        c2 = client()
        bundle_for(c2)["player"].charisma = 10  # should have zero effect on a luck-gated event
        with force_event_type("hazard"):
            c2.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        event2 = c2.post("/api/event/engage").json()["event"]
        self.assertEqual(event2["tier"], "fail")


class HazardEventTests(unittest.TestCase):
    def test_hazard_fail_tier_reduces_hp_by_its_declared_percentage_once_engaged(self):
        c = client()
        with force_event_type("hazard"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        res = c.post("/api/event/engage")
        self.assertEqual(res.json()["event"]["hp_loss_pct"], 0.18)
        player = bundle_for(c)["player"]
        self.assertIsNotNone(player.hp)
        self.assertLess(res.json()["player"]["hp"], res.json()["player"]["max_hp"])

    def test_hazard_causes_no_hp_loss_until_engaged(self):
        c = client()
        with force_event_type("hazard"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        self.assertIsNone(bundle_for(c)["player"].hp)  # still full -- nothing resolved yet

    def test_hazard_never_drops_the_player_below_one_hp(self):
        c = client()
        bundle_for(c)["player"].hp = 0.5  # already nearly dead
        with force_event_type("hazard"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        c.post("/api/event/engage")
        self.assertGreaterEqual(bundle_for(c)["player"].hp, 1.0)

    def test_hazard_success_or_great_tier_causes_no_hp_loss(self):
        c = client()
        with force_event_type("hazard"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        res = c.post("/api/event/engage")
        self.assertEqual(res.json()["event"]["hp_loss_pct"], 0.0)
        self.assertEqual(res.json()["event"]["gold_delta"], 6)

    def test_walking_away_from_a_hazard_never_costs_hp(self):
        c = client()
        with force_event_type("hazard"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        c.post("/api/event/walk_away")
        self.assertIsNone(bundle_for(c)["player"].hp)


class MerchantEventTests(unittest.TestCase):
    def test_merchant_great_tier_grants_gold_and_a_resource_once_engaged(self):
        c = client()
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        res = c.post("/api/event/engage")
        self.assertEqual(res.json()["event"]["gold_delta"], 15)
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["gold"], 15)
        self.assertEqual(wallet["resources"], {"ascension_sigil": 1})

    def test_merchant_fail_tier_grants_nothing(self):
        c = client()
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        c.post("/api/event/engage")
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["gold"], 0)
        self.assertEqual(wallet["resources"], {})
        self.assertEqual(wallet["chests"], {})


class ShrineBlessingCarriesIntoNextBattleTests(unittest.TestCase):
    def test_a_shrine_blessing_seeds_the_next_battles_initial_buff(self):
        c = client()
        with force_event_type("shrine"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})
        res = c.post("/api/event/engage")
        self.assertEqual(res.json()["event"]["buff_rounds"], 3)
        self.assertEqual(res.json()["event"]["buff_mult"], 0.15)

        # A real combat encounter afterward should pick up the blessing.
        with patch("battle_app.roll_encounter_kind", return_value="combat"):
            c.post("/api/battle/start", json={"archetype": "brute", "seed": 2})
        battle = bundle_for(c)["battle"]
        self.assertEqual(len(battle._buffs), 1)
        self.assertAlmostEqual(battle._buffs[0]["attack_mult"], 0.15)
        self.assertEqual(battle._buffs[0]["rounds_left"], 3)
        self.assertEqual(battle.buff_attack_bonus(), 0.15)

    def test_blessing_is_consumed_once_not_reapplied_to_a_later_battle(self):
        c = client()
        with force_event_type("shrine"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})
        c.post("/api/event/engage")
        with patch("battle_app.roll_encounter_kind", return_value="combat"):
            c.post("/api/battle/start", json={"archetype": "brute", "seed": 2})  # consumes it
            c.post("/api/battle/start", json={"archetype": "brute", "seed": 2})  # nothing left to seed
        self.assertEqual(bundle_for(c)["battle"]._buffs, [])

    def test_shrine_fail_tier_queues_no_blessing(self):
        c = client()
        with force_event_type("shrine"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        c.post("/api/event/engage")
        self.assertIsNone(bundle_for(c)["blessing"])

    def test_walking_away_from_a_shrine_queues_no_blessing(self):
        c = client()
        with force_event_type("shrine"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})  # would bless if engaged
        c.post("/api/event/walk_away")
        self.assertIsNone(bundle_for(c)["blessing"])


class ContinuationEventIntegrationTests(unittest.TestCase):
    def _win_a_battle(self, c: TestClient) -> None:
        # auto stays off: with it on, the win itself would trigger
        # auto-battle's own bank-or-continue decision (battle_app.
        # _maybe_auto_advance, see test_push_your_luck.py) instead of
        # leaving this exact finished battle in place for the tests
        # below to manually continue from. The auto-battle policy's own
        # counter choice still reliably wins without the flag itself set.
        bundle_for(c)["player"].level = 10
        c.post("/api/battle/start", json={"enemy_level": 1, "seed": 2})
        last = None
        for _ in range(50):
            response = bundle_for(c)["battle"].choose_auto_response()
            last = c.post("/api/battle/round", json={"response": response})
            if last.json()["state"]["finished"]:
                break
        assert last.json()["state"]["outcome"] == "victory"

    def test_an_event_while_continuing_leaves_the_prior_battle_and_pool_intact(self):
        c = client()
        self._win_a_battle(c)
        prior_battle = bundle_for(c)["battle"]
        pending_before = bundle_for(c)["pending"].summary()

        with force_event_type("merchant"):
            res = c.post("/api/battle/continue", json={"seed": SEED_FOR_TIER["partial"]})
        body = res.json()

        self.assertEqual(body["kind"], "event")
        self.assertFalse(body["event"]["resolved"])
        self.assertIs(bundle_for(c)["battle"], prior_battle)
        self.assertTrue(body["push_luck"]["can_bank"])
        self.assertTrue(body["push_luck"]["can_continue"])
        self.assertEqual(body["push_luck"]["pending"], pending_before)

        # Resolving the event (either way) doesn't touch the still-intact
        # prior run, which can still be banked afterward.
        c.post("/api/event/engage")
        bank_res = c.post("/api/battle/bank")
        self.assertEqual(bank_res.status_code, 200, bank_res.text)

    def test_continuation_combat_still_escalates_when_no_event_fires(self):
        c = client()
        self._win_a_battle(c)
        with patch("battle_app.roll_encounter_kind", return_value="combat"), \
             patch("battle_app.next_encounter_enemy") as mock_next:
            mock_next.return_value = battle_app.baseline_enemy(1, archetype="brute")
            res = c.post("/api/battle/continue", json={"seed": 2})
        self.assertEqual(res.json()["kind"], "combat")
        mock_next.assert_called_once_with(1)


# ---------- Frontend markup ----------

class EventScreenMarkupTests(unittest.TestCase):
    def setUp(self):
        c = client()
        self.html = c.get("/event").text
        self.js = c.get("/static/event.js").text
        self.home_js = c.get("/static/home.js").text
        self.battle_js = c.get("/static/app.js").text

    def test_event_page_declares_core_regions(self):
        for element_id in (
            "event-card", "event-name", "event-description", "event-choice-panel",
            "event-engage", "event-walk-away", "event-tier-banner",
            "event-outcome-list", "event-push-luck-panel", "event-bank",
            "event-continue", "event-return-hub",
        ):
            self.assertIn(f'id="{element_id}"', self.html, element_id)

    def test_event_js_wires_the_choice_endpoints_before_bank_and_continue(self):
        for marker in (
            "/api/event/state", "/api/event/engage", "/api/event/walk_away",
            "/api/battle/bank", "/api/battle/continue",
        ):
            self.assertIn(marker, self.js, marker)
        self.assertIn('$("event-engage").addEventListener("click", engage)', self.js)
        self.assertIn('$("event-walk-away").addEventListener("click", walkAway)', self.js)
        self.assertIn('$("event-bank").addEventListener("click", bank)', self.js)
        self.assertIn('$("event-continue").addEventListener("click", continuePushingLuck)', self.js)

    def test_event_js_gates_rendering_the_outcome_on_resolved(self):
        # The choice panel and the outcome/reward panel are mutually
        # exclusive on `event.resolved` -- the regression that matters
        # here is that outcome rendering isn't reachable before a choice.
        self.assertIn("event.resolved", self.js)
        self.assertIn("unresolved", self.js)

    def test_home_hub_redirects_to_the_event_screen_on_an_event_result(self):
        self.assertIn('body.kind === "event"', self.home_js)
        self.assertIn('"/event"', self.home_js)

    def test_battle_screen_redirects_to_the_event_screen_from_start_and_continue(self):
        self.assertIn('result.kind === "event"', self.battle_js)


if __name__ == "__main__":
    unittest.main()
