"""Non-combat special-event regression tests (core/special_events.py +
battle_app.py wiring).

Covers: the encounter-kind gate and event-type roll, charisma/luck
actually shifting outcome-tier odds (a deterministic property here,
not a statistical one -- the same raw roll is compared with and
without the stat bonus, so "higher stats never produce a worse tier"
is a guarantee, not a trend), failure staying possible even at
maxed-out stats, every event/tier's reward staying within its declared
table (a hard-bounds property, not a probability curve), and the
end-to-end API flow for both a fresh hub start and a push-your-luck
continuation landing on an event instead of a fight.
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
    EVENT_TYPES,
    MAX_TOTAL_STAT_BONUS,
    OUTCOME_TIERS,
    REWARD_TABLES,
    TIER_CUTOFFS,
    resolve_event,
    roll_encounter_kind,
    roll_event_type,
    roll_outcome_tier,
    stat_bonus,
)
from core.wallet import Wallet

TIER_ORDER = {t: i for i, t in enumerate(OUTCOME_TIERS)}

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

class StatBonusTests(unittest.TestCase):
    def test_baseline_stats_give_zero_bonus(self):
        self.assertEqual(stat_bonus(BASELINE_STAT, BASELINE_STAT), 0.0)

    def test_bonus_increases_with_charisma_and_luck(self):
        low = stat_bonus(BASELINE_STAT, BASELINE_STAT)
        high = stat_bonus(BASELINE_STAT + 10, BASELINE_STAT + 10)
        self.assertGreater(high, low)

    def test_combined_bonus_never_exceeds_the_declared_cap(self):
        for charisma in (5, 20, 100, 10_000):
            for luck in (5, 20, 100, 10_000):
                self.assertLessEqual(stat_bonus(charisma, luck), MAX_TOTAL_STAT_BONUS)

    def test_cap_is_kept_below_the_fail_cutoff_so_failure_stays_possible(self):
        fail_cutoff = TIER_CUTOFFS[0][0]
        self.assertLess(MAX_TOTAL_STAT_BONUS, fail_cutoff)


class OutcomeTierRollTests(unittest.TestCase):
    def test_higher_stats_never_produce_a_worse_tier_for_the_same_roll(self):
        for raw in (0.0, 0.1, 0.2, 0.34, 0.35, 0.5, 0.64, 0.65, 0.89, 0.9, 0.99):
            baseline_tier = roll_outcome_tier(BASELINE_STAT, BASELINE_STAT, FixedRng(raw))
            high_tier = roll_outcome_tier(BASELINE_STAT + 20, BASELINE_STAT + 20, FixedRng(raw))
            self.assertGreaterEqual(TIER_ORDER[high_tier], TIER_ORDER[baseline_tier], raw)

    def test_higher_stats_meaningfully_improve_at_least_some_rolls(self):
        # Not just a tie everywhere -- some roll must actually cross a
        # tier boundary once charisma/luck are added, or the stats
        # wouldn't be "meaningfully" improving anything.
        improved = any(
            TIER_ORDER[roll_outcome_tier(BASELINE_STAT + 20, BASELINE_STAT + 20, FixedRng(raw))]
            > TIER_ORDER[roll_outcome_tier(BASELINE_STAT, BASELINE_STAT, FixedRng(raw))]
            for raw in (0.10, 0.30, 0.34, 0.60, 0.64, 0.88)
        )
        self.assertTrue(improved)

    def test_failure_stays_possible_even_at_extreme_stats(self):
        self.assertEqual(roll_outcome_tier(10_000, 10_000, FixedRng(0.0)), "fail")

    def test_great_is_reachable_at_baseline_stats(self):
        self.assertEqual(roll_outcome_tier(BASELINE_STAT, BASELINE_STAT, FixedRng(0.99)), "great")


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
        self.assertEqual(PlayerState().charisma, 5)
        self.assertIn("charisma", ATTRIBUTES)

    def test_charisma_is_spendable_like_any_other_attribute(self):
        player = PlayerState(stat_points=2)
        self.assertTrue(player.spend_stat("charisma", 2))
        self.assertEqual(player.charisma, 7)
        self.assertEqual(player.stat_points, 0)


# ---------- API integration ----------

def client() -> TestClient:
    # A brand-new, never-before-used account per call -- nothing stale
    # to reset, unlike the single shared global this used to reach into.
    return authed_client()


def force_event_type(event_type: str):
    """Patches battle_app's imported roll functions so the next
    encounter roll deterministically lands on an event of this type;
    the outcome *tier* is still a real roll from the request's seed
    (see SEED_FOR_TIER), not mocked."""
    return patch.multiple(
        "battle_app",
        roll_encounter_kind=lambda rng: "event",
        roll_event_type=lambda rng: event_type,
    )


class StartBattleEventIntegrationTests(unittest.TestCase):
    def test_start_can_roll_into_an_event_instead_of_a_fight(self):
        c = client()
        with force_event_type("treasure"):
            res = c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["kind"], "event")
        self.assertEqual(body["event"]["type"], "treasure")
        self.assertEqual(body["event"]["tier"], "success")
        self.assertEqual(body["event"]["chest_rarity"], "rare")
        # No battle was created for an event encounter.
        self.assertEqual(c.get("/api/battle/state").status_code, 404)

    def test_no_event_before_any_roll_is_a_404(self):
        c = client()
        self.assertEqual(c.get("/api/event/state").status_code, 404)

    def test_event_state_reflects_the_resolved_event_after_a_fresh_navigation(self):
        c = client()
        with force_event_type("treasure"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        res = c.get("/api/event/state")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["event"]["type"], "treasure")
        self.assertEqual(res.json()["event"]["chest_rarity"], "epic")

    def test_treasure_chest_lands_in_the_wallet_immediately(self):
        c = client()
        with force_event_type("treasure"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["partial"]})
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["chests"], {"common": 1})

    def test_merchant_great_tier_grants_gold_and_a_resource(self):
        c = client()
        with force_event_type("merchant"):
            res = c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        self.assertEqual(res.json()["event"]["gold_delta"], 15)
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["gold"], 15)
        self.assertEqual(wallet["resources"], {"ascension_sigil": 1})

    def test_merchant_fail_tier_grants_nothing(self):
        c = client()
        with force_event_type("merchant"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["gold"], 0)
        self.assertEqual(wallet["resources"], {})
        self.assertEqual(wallet["chests"], {})


class HazardEventTests(unittest.TestCase):
    def test_hazard_fail_tier_reduces_hp_by_its_declared_percentage(self):
        c = client()
        with force_event_type("hazard"):
            res = c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        self.assertEqual(res.json()["event"]["hp_loss_pct"], 0.18)
        player = bundle_for(c)["player"]
        self.assertIsNotNone(player.hp)
        self.assertLess(res.json()["player"]["hp"], res.json()["player"]["max_hp"])

    def test_hazard_never_drops_the_player_below_one_hp(self):
        c = client()
        bundle_for(c)["player"].hp = 0.5  # already nearly dead
        with force_event_type("hazard"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        self.assertGreaterEqual(bundle_for(c)["player"].hp, 1.0)

    def test_hazard_success_or_great_tier_causes_no_hp_loss(self):
        c = client()
        with force_event_type("hazard"):
            res = c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["great"]})
        self.assertEqual(res.json()["event"]["hp_loss_pct"], 0.0)
        self.assertEqual(res.json()["event"]["gold_delta"], 6)


class ShrineBlessingCarriesIntoNextBattleTests(unittest.TestCase):
    def test_a_shrine_blessing_seeds_the_next_battles_initial_buff(self):
        c = client()
        with force_event_type("shrine"):
            res = c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["success"]})
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
        with patch("battle_app.roll_encounter_kind", return_value="combat"):
            c.post("/api/battle/start", json={"archetype": "brute", "seed": 2})  # consumes it
            c.post("/api/battle/start", json={"archetype": "brute", "seed": 2})  # nothing left to seed
        self.assertEqual(bundle_for(c)["battle"]._buffs, [])

    def test_shrine_fail_tier_queues_no_blessing(self):
        c = client()
        with force_event_type("shrine"):
            c.post("/api/battle/start", json={"seed": SEED_FOR_TIER["fail"]})
        self.assertIsNone(bundle_for(c)["blessing"])


class ContinuationEventIntegrationTests(unittest.TestCase):
    def _win_a_battle(self, c: TestClient) -> None:
        bundle_for(c)["player"].level = 10
        c.post("/api/battle/start", json={"enemy_level": 1, "auto": True, "seed": 2})
        last = None
        for _ in range(50):
            last = c.post("/api/battle/round", json={"response": None})
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
        self.assertIs(bundle_for(c)["battle"], prior_battle)
        self.assertTrue(body["push_luck"]["can_bank"])
        self.assertTrue(body["push_luck"]["can_continue"])
        self.assertEqual(body["push_luck"]["pending"], pending_before)

        # The still-pending run can still be banked afterward.
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
            "event-card", "event-name", "event-description", "event-tier-banner",
            "event-outcome-list", "event-push-luck-panel", "event-bank",
            "event-continue", "event-return-hub",
        ):
            self.assertIn(f'id="{element_id}"', self.html, element_id)

    def test_event_js_fetches_state_and_wires_bank_and_continue(self):
        for marker in ("/api/event/state", "/api/battle/bank", "/api/battle/continue"):
            self.assertIn(marker, self.js, marker)
        self.assertIn('$("event-bank").addEventListener("click", bank)', self.js)
        self.assertIn('$("event-continue").addEventListener("click", continuePushingLuck)', self.js)

    def test_home_hub_redirects_to_the_event_screen_on_an_event_result(self):
        self.assertIn('body.kind === "event"', self.home_js)
        self.assertIn('"/event"', self.home_js)

    def test_battle_screen_redirects_to_the_event_screen_from_start_and_continue(self):
        self.assertIn('result.kind === "event"', self.battle_js)


if __name__ == "__main__":
    unittest.main()
