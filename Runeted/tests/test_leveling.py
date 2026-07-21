"""Leveling system regression tests.

Covers: the victory-XP award curve (core/player_state.py::victory_exp,
reusing core/stats.py's per-level growth curve rather than inventing a
second one), that a battle victory actually calls gain_exp (and a
defeat never does), that a level-up's usual "heal to full" side effect
is suppressed specifically on a battle-victory award (so it can't
undercut the push-your-luck continue-without-healing risk model), that
allocated stat points actually change what core/stats.py::
compute_player_stats returns (the same pipeline combat already reads),
that charisma is allocatable but never touches derived combat stats,
and the /api/player/spend_stat endpoint + stats-page markup.
"""
import unittest

from fastapi.testclient import TestClient

import battle_app
from core.gauntlet import PendingPool
from core.player_state import ATTRIBUTES, BASE_VICTORY_EXP, PlayerState, victory_exp
from core.stats import compute_player_stats
from core.wallet import Wallet


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
    (the same technique test_push_your_luck.py uses)."""
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
    non-striking, non-blocking, non-dodging skill so the enemy's
    guaranteed contact chip finishes the player off deterministically."""
    battle = battle_app.CURRENT["battle"]
    battle._rune_passives = []
    battle.player_hp = 0.5
    res = c.post("/api/battle/round", json={"response": "second_wind"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["state"]["outcome"] == "defeat", body["state"]["outcome"]
    return body


# ---------- XP curve ----------

class VictoryExpCurveTests(unittest.TestCase):
    def test_level_one_enemy_grants_the_base_amount(self):
        self.assertEqual(victory_exp(1), BASE_VICTORY_EXP)

    def test_a_tougher_enemy_grants_more_exp(self):
        self.assertGreater(victory_exp(5), victory_exp(1))
        self.assertGreater(victory_exp(10), victory_exp(5))

    def test_exp_never_drops_below_one(self):
        self.assertGreaterEqual(victory_exp(1), 1)


# ---------- Allocated stats -> derived combat stats ----------

class AllocatedStatsFeedDerivedStatsTests(unittest.TestCase):
    def test_strength_raises_attack(self):
        player = PlayerState(stat_points=5)
        before = compute_player_stats(player).attack
        self.assertTrue(player.spend_stat("strength", 5))
        after = compute_player_stats(player).attack
        self.assertGreater(after, before)

    def test_vitality_raises_defense_and_max_hp(self):
        player = PlayerState(stat_points=5)
        before = compute_player_stats(player)
        self.assertTrue(player.spend_stat("vitality", 5))
        after = compute_player_stats(player)
        self.assertGreater(after.defense, before.defense)
        self.assertGreater(after.max_hp, before.max_hp)

    def test_dexterity_raises_dodge_chance(self):
        player = PlayerState(stat_points=20)
        before = compute_player_stats(player).dodge_chance
        self.assertTrue(player.spend_stat("dexterity", 20))
        after = compute_player_stats(player).dodge_chance
        self.assertGreater(after, before)

    def test_intelligence_raises_max_stamina(self):
        player = PlayerState(stat_points=5)
        before = compute_player_stats(player).max_stamina
        self.assertTrue(player.spend_stat("intelligence", 5))
        after = compute_player_stats(player).max_stamina
        self.assertGreater(after, before)

    def test_luck_raises_crit_chance(self):
        player = PlayerState(stat_points=5)
        before = compute_player_stats(player).crit_chance
        self.assertTrue(player.spend_stat("luck", 5))
        after = compute_player_stats(player).crit_chance
        self.assertGreater(after, before)

    def test_charisma_is_allocatable_but_never_touches_derived_stats(self):
        player = PlayerState(stat_points=10)
        before = compute_player_stats(player)
        self.assertTrue(player.spend_stat("charisma", 10))
        self.assertEqual(player.charisma, 15)
        after = compute_player_stats(player)
        self.assertEqual(before, after)

    def test_charisma_is_registered_as_a_real_attribute(self):
        self.assertIn("charisma", ATTRIBUTES)
        self.assertEqual(PlayerState().charisma, 5)


# ---------- Battle-victory XP wiring ----------

class BattleVictoryExpTests(unittest.TestCase):
    def test_victory_awards_and_reports_exp(self):
        c = client()
        body = force_a_win(c)
        self.assertIn("exp_result", body)
        self.assertGreater(body["exp_result"]["exp_gained"], 0)
        self.assertFalse(body["exp_result"]["leveled_up"])
        self.assertEqual(battle_app.CURRENT["player"].exp, body["exp_result"]["exp_gained"])

    def test_defeat_awards_no_exp(self):
        c = client()
        start(c, enemy_level=20)
        body = force_a_loss(c)
        self.assertNotIn("exp_result", body)
        self.assertEqual(battle_app.CURRENT["player"].exp, 0)

    def test_leveling_up_grants_the_configured_stat_points(self):
        c = client()
        player = battle_app.CURRENT["player"]
        player.exp = player.exp_to_next - 1  # this win's XP crosses the threshold
        body = force_a_win(c)
        self.assertTrue(body["exp_result"]["leveled_up"])
        self.assertEqual(body["exp_result"]["levels_gained"], 1)
        self.assertGreater(body["exp_result"]["stat_points"], 0)
        self.assertEqual(player.stat_points, body["exp_result"]["stat_points"])

    def test_leveling_up_on_a_battle_victory_does_not_grant_a_free_heal(self):
        # PlayerState.gain_exp() heals to full (hp=None) on every level-up
        # -- correct for that method standalone, but a battle victory
        # must never grant a free heal: that would undercut the very
        # risk continuing-without-healing exists to create (Phase 6).
        c = client()
        player = battle_app.CURRENT["player"]
        player.exp = player.exp_to_next - 1
        body = force_a_win(c)
        self.assertTrue(body["exp_result"]["leveled_up"])
        hp_after_fight = body["state"]["player"]["hp"]
        self.assertIsNotNone(player.hp)
        self.assertEqual(player.hp, hp_after_fight)


# ---------- /api/player and /api/player/spend_stat ----------

class SpendStatEndpointTests(unittest.TestCase):
    def test_player_payload_includes_every_attribute(self):
        c = client()
        body = c.get("/api/player").json()
        self.assertIn("attributes", body)
        for stat in ATTRIBUTES:
            self.assertIn(stat, body["attributes"])
            self.assertEqual(body["attributes"][stat], 5)

    def test_spend_stat_applies_and_returns_the_updated_player(self):
        c = client()
        battle_app.CURRENT["player"].stat_points = 3
        res = c.post("/api/player/spend_stat", json={"stat": "strength"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["attributes"]["strength"], 6)
        self.assertEqual(body["stat_points"], 2)

    def test_spend_stat_respects_a_custom_amount(self):
        c = client()
        battle_app.CURRENT["player"].stat_points = 3
        res = c.post("/api/player/spend_stat", json={"stat": "charisma", "amount": 3})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["attributes"]["charisma"], 8)
        self.assertEqual(body["stat_points"], 0)

    def test_spend_stat_rejects_an_unknown_stat(self):
        c = client()
        battle_app.CURRENT["player"].stat_points = 3
        res = c.post("/api/player/spend_stat", json={"stat": "not_a_stat"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(battle_app.CURRENT["player"].stat_points, 3)

    def test_spend_stat_rejects_when_no_points_are_available(self):
        c = client()
        battle_app.CURRENT["player"].stat_points = 0
        res = c.post("/api/player/spend_stat", json={"stat": "strength"})
        self.assertEqual(res.status_code, 400)


# ---------- Stats page ----------

class StatsPageMarkupTests(unittest.TestCase):
    def setUp(self):
        c = client()
        self.home_html = c.get("/").text
        self.stats_html = c.get("/stats").text
        self.stats_js = c.get("/static/stats.js").text

    def test_home_hub_links_to_the_stats_page(self):
        self.assertIn('href="/stats"', self.home_html)

    def test_stats_page_serves_an_allocation_ui_for_every_attribute(self):
        self.assertIn('id="stat-list"', self.stats_html)
        self.assertIn('href="/"', self.stats_html)  # a way back to the hub
        self.assertIn("/api/player/spend_stat", self.stats_js)
        for stat in ATTRIBUTES:
            self.assertIn(stat, self.stats_js)


if __name__ == "__main__":
    unittest.main()
