"""Push-your-luck reward flow regression tests (core/gauntlet.py +
battle_app.py wiring).

Covers: the escalation curve's soft cap and hard ceiling, the pending
pool's accumulation across wins, banking committing the pool into the
wallet via the same grant_chest/add_currency every other chest/currency
award uses, forfeiture discarding the pool untouched by any wallet
write, and the end-to-end API flow (win -> decision offered -> bank or
continue -> a later loss only ever costs the *current* unbanked run).
"""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import battle_app
from core.gauntlet import (
    MAX_DEPTH,
    MAX_RISK,
    SOFT_CAP_STREAK,
    PendingPool,
    bank,
    escalation_for_streak,
    forfeit,
    next_encounter_enemy,
)
from core.player_state import PlayerState
from core.wallet import Wallet, wallet_payload


# ---------- Escalation curve ----------

class EscalationCurveTests(unittest.TestCase):
    def test_risk_matches_streak_up_to_the_soft_cap(self):
        for streak in range(0, SOFT_CAP_STREAK + 1):
            _, risk = escalation_for_streak(streak)
            self.assertEqual(risk, streak, streak)

    def test_risk_and_depth_are_non_decreasing_as_streak_grows(self):
        prev_depth, prev_risk = escalation_for_streak(0)
        for streak in range(1, 40):
            depth, risk = escalation_for_streak(streak)
            self.assertGreaterEqual(risk, prev_risk, streak)
            self.assertGreaterEqual(depth, prev_depth, streak)
            prev_depth, prev_risk = depth, risk

    def test_growth_flattens_past_the_soft_cap(self):
        # The step from streak N to N+1 must shrink once the soft cap is
        # passed -- diminishing returns, not a flat continuation of the
        # pre-cap slope.
        _, risk_at_cap = escalation_for_streak(SOFT_CAP_STREAK)
        _, risk_one_past = escalation_for_streak(SOFT_CAP_STREAK + 1)
        _, risk_two_past = escalation_for_streak(SOFT_CAP_STREAK + 2)
        pre_cap_step = 1  # risk == streak below the cap
        post_cap_step = risk_two_past - risk_one_past
        self.assertLessEqual(post_cap_step, pre_cap_step)
        self.assertGreater(risk_one_past, risk_at_cap - 1)  # still moves, just slower

    def test_absolute_ceiling_holds_even_for_a_very_long_streak(self):
        depth, risk = escalation_for_streak(10_000)
        self.assertLessEqual(risk, MAX_RISK)
        self.assertLessEqual(depth, MAX_DEPTH)

    def test_depth_and_risk_never_go_below_their_floors(self):
        depth, risk = escalation_for_streak(0)
        self.assertGreaterEqual(depth, 1)
        self.assertGreaterEqual(risk, 0)
        depth, risk = escalation_for_streak(-5)  # defensive: never negative in
        self.assertGreaterEqual(depth, 1)
        self.assertGreaterEqual(risk, 0)


class NextEncounterEnemyTests(unittest.TestCase):
    def test_next_encounter_enemy_is_generated_from_the_escalation_curve(self):
        with patch("core.gauntlet.create_enemy") as mock_create:
            next_encounter_enemy(streak=4)
        expected_depth, expected_risk = escalation_for_streak(4)
        mock_create.assert_called_once_with(depth=expected_depth, risk=expected_risk)


# ---------- Pending pool ----------

class PendingPoolTests(unittest.TestCase):
    def test_fresh_pool_is_empty(self):
        pool = PendingPool()
        self.assertTrue(pool.is_empty())
        self.assertEqual(pool.streak, 0)

    def test_add_win_increments_streak_and_accumulates_rewards(self):
        pool = PendingPool()
        pool.add_win({"chest_rarity": "rare", "currency_id": "gold", "currency_amount": 20})
        pool.add_win({"chest_rarity": "rare", "currency_id": "gold", "currency_amount": 15})
        pool.add_win({"chest_rarity": "epic", "currency_id": "crafted_supplies", "currency_amount": 2})
        self.assertEqual(pool.streak, 3)
        self.assertFalse(pool.is_empty())
        self.assertEqual(pool.chests, {"rare": 2, "epic": 1})
        self.assertEqual(pool.gold, 35)
        self.assertEqual(pool.resources, {"crafted_supplies": 2})

    def test_summary_is_a_plain_snapshot_not_a_live_reference(self):
        pool = PendingPool()
        pool.add_win({"chest_rarity": "common", "currency_id": "gold", "currency_amount": 5})
        snap = pool.summary()
        pool.add_win({"chest_rarity": "common", "currency_id": "gold", "currency_amount": 5})
        self.assertEqual(snap["gold"], 5)  # the earlier snapshot didn't mutate
        self.assertEqual(pool.gold, 10)

    def test_reset_clears_everything(self):
        pool = PendingPool()
        pool.add_win({"chest_rarity": "rare", "currency_id": "gold", "currency_amount": 20})
        pool.reset()
        self.assertTrue(pool.is_empty())
        self.assertEqual(pool.streak, 0)
        self.assertEqual(pool.chests, {})
        self.assertEqual(pool.gold, 0)
        self.assertEqual(pool.resources, {})


class BankTests(unittest.TestCase):
    def test_bank_grants_every_pending_chest_and_currency_to_the_wallet(self):
        pool = PendingPool()
        pool.add_win({"chest_rarity": "rare", "currency_id": "gold", "currency_amount": 20})
        pool.add_win({"chest_rarity": "rare", "currency_id": "crafted_supplies", "currency_amount": 3})
        wallet = Wallet()
        banked = bank(pool, wallet)

        self.assertEqual(banked["streak"], 2)
        self.assertEqual(wallet.chests.get("rare"), 2)
        self.assertEqual(wallet.gold, 20)
        self.assertEqual(wallet.resources.get("crafted_supplies"), 3)

    def test_bank_clears_the_pool(self):
        pool = PendingPool()
        pool.add_win({"chest_rarity": "epic", "currency_id": "gold", "currency_amount": 10})
        bank(pool, Wallet())
        self.assertTrue(pool.is_empty())

    def test_bank_is_additive_across_multiple_runs(self):
        wallet = Wallet()
        pool = PendingPool()
        pool.add_win({"chest_rarity": "rare", "currency_id": "gold", "currency_amount": 10})
        bank(pool, wallet)
        pool.add_win({"chest_rarity": "rare", "currency_id": "gold", "currency_amount": 10})
        bank(pool, wallet)
        # Two separate banked runs of 1 rare chest / 10 gold each -> the
        # wallet holds both, nothing was overwritten by the second bank.
        self.assertEqual(wallet.chests.get("rare"), 2)
        self.assertEqual(wallet.gold, 20)

    def test_bank_on_an_empty_pool_grants_nothing(self):
        wallet = Wallet()
        banked = bank(PendingPool(), wallet)
        self.assertEqual(banked["streak"], 0)
        self.assertEqual(wallet.chests, {})
        self.assertEqual(wallet.gold, 0)


class ForfeitTests(unittest.TestCase):
    def test_forfeit_returns_what_was_lost_and_clears_the_pool(self):
        pool = PendingPool()
        pool.add_win({"chest_rarity": "legendary", "currency_id": "gold", "currency_amount": 99})
        lost = forfeit(pool)
        self.assertEqual(lost["streak"], 1)
        self.assertEqual(lost["chests"], {"legendary": 1})
        self.assertTrue(pool.is_empty())

    def test_forfeit_never_touches_any_wallet(self):
        # forfeit() doesn't even take a wallet argument -- there is no
        # code path from it into grant_chest/add_currency. Prove the
        # pool's contents vanish rather than landing anywhere.
        wallet = Wallet()
        pool = PendingPool()
        pool.add_win({"chest_rarity": "mythic", "currency_id": "gold", "currency_amount": 500})
        forfeit(pool)
        self.assertEqual(wallet.gold, 0)
        self.assertEqual(wallet.chests, {})


# ---------- End-to-end API flow ----------

def client() -> TestClient:
    battle_app.CURRENT["battle"] = None
    battle_app.CURRENT["player"] = PlayerState()
    battle_app.CURRENT["wallet"] = Wallet()
    battle_app.CURRENT["pending"] = PendingPool()
    return TestClient(battle_app.app)


def start(c: TestClient, **overrides):
    payload = {"archetype": "brute"}
    payload.update(overrides)
    res = c.post("/api/battle/start", json=payload)
    assert res.status_code == 200, res.text
    return res.json()


def force_a_win(c: TestClient) -> dict:
    """Player level 10 vs. a level-1 enemy on auto-battle reliably wins
    (the same technique test_battle_screen.py uses for its 409 test)."""
    battle_app.CURRENT["player"].level = 10
    start(c, enemy_level=1, auto=True)
    last = None
    for _ in range(50):
        last = c.post("/api/battle/round", json={"response": None})
        assert last.status_code == 200, last.text
        if last.json()["state"]["finished"]:
            break
    body = last.json()
    assert body["state"]["outcome"] == "victory", body["state"]["outcome"]
    return body


def force_a_loss(c: TestClient) -> dict:
    """Crash the active battle's HP to near-zero and answer with a
    non-striking, non-blocking, non-dodging skill (Second Wind) so the
    enemy's guaranteed contact chip finishes the player off this round,
    deterministically. Default-attribute passive dodge is 0%, but the
    default rune loadout's Zephyr Charm adds a small start-of-turn dodge
    bonus -- stripped here so the forced loss can't flake."""
    battle = battle_app.CURRENT["battle"]
    battle._rune_passives = []
    battle.player_hp = 0.5
    res = c.post("/api/battle/round", json={"response": "second_wind"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["state"]["outcome"] == "defeat", body["state"]["outcome"]
    return body


class VictoryOffersThePendingDecisionTests(unittest.TestCase):
    def test_a_win_adds_a_guaranteed_reward_and_offers_bank_or_continue(self):
        c = client()
        body = force_a_win(c)
        result = body["push_luck_result"]
        self.assertEqual(result["result"], "win")
        self.assertIn(result["reward"]["chest_rarity"], (
            "common", "rare", "epic", "legendary", "mythic", "relic",
        ))
        self.assertGreater(result["reward"]["currency_amount"], 0)
        self.assertEqual(result["pending"]["streak"], 1)

        push_luck = body["state"]["push_luck"]
        self.assertTrue(push_luck["can_bank"])
        self.assertTrue(push_luck["can_continue"])
        self.assertEqual(push_luck["pending"]["streak"], 1)

    def test_before_any_win_no_decision_is_offered(self):
        c = client()
        state = start(c)
        self.assertFalse(state["push_luck"]["can_bank"])
        self.assertFalse(state["push_luck"]["can_continue"])
        self.assertTrue(state["push_luck"]["pending"]["streak"] == 0)


class BankEndpointTests(unittest.TestCase):
    def test_bank_commits_the_pending_pool_and_closes_the_battle(self):
        c = client()
        win_body = force_a_win(c)
        pending_before = win_body["push_luck_result"]["pending"]

        res = c.post("/api/battle/bank")
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["banked"], pending_before)
        self.assertEqual(body["wallet"]["chests"], pending_before["chests"])
        self.assertEqual(body["wallet"]["gold"], pending_before["gold"])

        # The decision point is resolved: no active battle remains.
        self.assertEqual(c.get("/api/battle/state").status_code, 404)
        # The bank is real and observable independent of battle state.
        self.assertEqual(c.get("/api/player/wallet").json(), body["wallet"])

    def test_bank_without_a_finished_victory_is_rejected(self):
        c = client()
        start(c)  # battle in progress, nothing pending
        self.assertEqual(c.post("/api/battle/bank").status_code, 409)

    def test_bank_after_defeat_is_rejected(self):
        c = client()
        start(c, enemy_level=30)
        force_a_loss(c)
        self.assertEqual(c.post("/api/battle/bank").status_code, 409)


class ContinueEndpointTests(unittest.TestCase):
    def test_continue_starts_a_harder_encounter_and_keeps_the_pool_at_risk(self):
        c = client()
        win_body = force_a_win(c)
        streak_before = win_body["push_luck_result"]["pending"]["streak"]

        res = c.post("/api/battle/continue")
        self.assertEqual(res.status_code, 200, res.text)
        state = res.json()
        self.assertEqual(state["outcome"], "in_progress")
        self.assertFalse(state["finished"])
        # The pool carried over untouched -- continuing doesn't bank or
        # reset anything by itself.
        self.assertEqual(state["push_luck"]["pending"]["streak"], streak_before)

    def test_continue_does_not_heal_the_player(self):
        # This is the whole point of "continue" carrying real risk: a
        # forced win at level 10 vs. a level-1 enemy never actually takes
        # damage, so asserting full HP after continue would pass whether
        # or not the healing bug were present. Damage the player for
        # real after the win, then prove continue doesn't top it back up.
        c = client()
        force_a_win(c)
        battle_app.CURRENT["player"].hp = 1.0

        state = c.post("/api/battle/continue").json()
        self.assertEqual(state["player"]["hp"], 1.0)
        self.assertLess(state["player"]["hp"], state["player"]["max_hp"])

    def test_a_fresh_hub_battle_still_heals_to_full(self):
        # Only ending the run (bank or defeat) and starting a fresh
        # battle from the hub should restore HP -- continuing must not.
        c = client()
        force_a_win(c)
        battle_app.CURRENT["player"].hp = 1.0
        c.post("/api/battle/bank")
        state = start(c)
        self.assertEqual(state["player"]["hp"], state["player"]["max_hp"])

    def test_continue_without_a_finished_victory_is_rejected(self):
        c = client()
        start(c)
        self.assertEqual(c.post("/api/battle/continue").status_code, 409)

    def test_continuation_enemy_escalates_with_the_streak(self):
        c = client()
        force_a_win(c)
        with patch("battle_app.next_encounter_enemy") as mock_next:
            mock_next.return_value = battle_app.baseline_enemy(1, archetype="brute")
            c.post("/api/battle/continue")
        mock_next.assert_called_once_with(1)  # streak after exactly one win


class LosingForfeitsOnlyTheUnbankedRunTests(unittest.TestCase):
    def test_a_loss_while_pushing_luck_forfeits_the_pending_pool(self):
        c = client()
        force_a_win(c)
        c.post("/api/battle/continue")
        body = force_a_loss(c)

        result = body["push_luck_result"]
        self.assertEqual(result["result"], "forfeit")
        self.assertEqual(result["lost"]["streak"], 1)

        push_luck = body["state"]["push_luck"]
        self.assertFalse(push_luck["can_bank"])
        self.assertFalse(push_luck["can_continue"])
        self.assertEqual(push_luck["pending"]["streak"], 0)

    def test_a_forfeited_run_never_reaches_the_wallet(self):
        c = client()
        force_a_win(c)
        c.post("/api/battle/continue")
        force_a_loss(c)
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["gold"], 0)
        self.assertEqual(wallet["chests"], {})

    def test_a_prior_banked_run_survives_a_later_forfeited_one(self):
        c = client()
        # Run 1: win once, bank it.
        force_a_win(c)
        banked = c.post("/api/battle/bank").json()["wallet"]
        self.assertGreater(banked["gold"] + sum(banked["chests"].values()), 0)

        # Run 2: win again, push on, then lose it all.
        force_a_win(c)
        c.post("/api/battle/continue")
        force_a_loss(c)

        wallet_after = c.get("/api/player/wallet").json()
        self.assertEqual(wallet_after, banked)  # untouched by run 2's loss

    def test_starting_a_fresh_battle_forfeits_an_unresolved_decision(self):
        c = client()
        force_a_win(c)  # a decision is now pending, never resolved
        start(c)  # walking straight into a new fight instead of choosing
        state = c.get("/api/battle/state").json()
        self.assertEqual(state["push_luck"]["pending"]["streak"], 0)
        wallet = c.get("/api/player/wallet").json()
        self.assertEqual(wallet["gold"], 0)
        self.assertEqual(wallet["chests"], {})


class WalletPayloadTests(unittest.TestCase):
    def test_wallet_payload_shape(self):
        payload = wallet_payload(Wallet(gold=5, resources={"crafted_supplies": 1}, chests={"rare": 1}))
        self.assertEqual(payload, {"gold": 5, "resources": {"crafted_supplies": 1}, "chests": {"rare": 1}})


class PushLuckMarkupTests(unittest.TestCase):
    """The battle screen must ship the bank-or-continue affordances; the
    panel itself is hidden until state.push_luck says a decision is
    actually pending (see renderPushLuck in app.js)."""

    def setUp(self):
        c = client()
        self.html = c.get("/battle").text
        self.js = c.get("/static/app.js").text

    def test_panel_and_both_actions_are_present(self):
        for element_id in ("push-luck-panel", "push-luck-summary", "push-luck-bank", "push-luck-continue"):
            self.assertIn(f'id="{element_id}"', self.html, element_id)

    def test_panel_starts_hidden(self):
        self.assertIn('id="push-luck-panel" class="hidden"', self.html)

    def test_js_wires_bank_and_continue_to_their_endpoints(self):
        self.assertIn("/api/battle/bank", self.js)
        self.assertIn("/api/battle/continue", self.js)
        self.assertIn("renderPushLuck", self.js)
        self.assertIn('$("push-luck-bank").addEventListener("click", bankPending)', self.js)
        self.assertIn('$("push-luck-continue").addEventListener("click", continuePushingLuck)', self.js)

    def test_panel_gates_on_can_bank_not_just_finished(self):
        # A defeat also finishes the battle but must not show the panel.
        fn = self.js.split("function renderPushLuck")[1].split("function ")[0]
        self.assertIn("can_bank", fn)


if __name__ == "__main__":
    unittest.main()
