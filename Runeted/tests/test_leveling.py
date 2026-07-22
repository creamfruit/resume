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

from _account_test_helpers import authed_client, bundle_for
from core.player_state import ATTRIBUTES, BASE_VICTORY_EXP, LEVEL_UP_STAT_POINTS, PlayerState, victory_exp
from core.stats import (
    ATTACK_PER_STRENGTH,
    HP_PER_VITALITY,
    baseline_enemy,
    compute_player_stats,
    derive_enemy_stats,
)


def client() -> TestClient:
    # A brand-new, never-before-used account per call -- nothing stale
    # to reset, unlike the single shared global this used to reach into.
    return authed_client()


def start(c: TestClient, **overrides):
    # seed=2 is a known "combat" roll under core/events.py's encounter
    # gate -- this suite is about leveling, not events, so every call
    # needs a fight, deterministically.
    payload = {"archetype": "brute", "seed": 2}
    payload.update(overrides)
    res = c.post("/api/battle/start", json=payload)
    assert res.status_code == 200, res.text
    return res.json()


def force_a_win(c: TestClient) -> dict:
    """Player level 10 vs. a level-1 enemy reliably wins if every round
    is answered with the auto-battle policy's own counter choice --
    computed directly from the battle here rather than via
    `battle.auto = True`, so a win doesn't itself trigger auto-battle's
    bank-or-continue decision (test_push_your_luck.py covers that
    behavior on its own terms; this suite is about leveling, and needs
    the battle to actually stop at exactly one victory)."""
    bundle_for(c)["player"].level = 10
    start(c, enemy_level=1)
    last = None
    for _ in range(50):
        response = bundle_for(c)["battle"].choose_auto_response()
        last = c.post("/api/battle/round", json={"response": response})
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
    battle = bundle_for(c)["battle"]
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
        self.assertEqual(player.charisma, 10)
        after = compute_player_stats(player)
        self.assertEqual(before, after)

    def test_charisma_is_registered_as_a_real_attribute(self):
        self.assertIn("charisma", ATTRIBUTES)
        self.assertEqual(PlayerState().charisma, 0)


# ---------- The rebalanced growth curve itself ----------
#
# A simulation in the same spirit as test_core_combat.py's auto-battle
# balance matrix: levels and stat allocations in, resulting combat
# numbers out, checked at several sample points rather than one. This
# is what the ATK/HP rebalance (LEVEL_UP_STAT_POINTS=3,
# ATTACK_PER_STRENGTH, HP_PER_VITALITY in core/stats.py) was tuned
# against. Before the fix, allocating stat points multiplied them by
# the same exponential level_scale the base stats use, so 5 levels of
# pure-strength investment (25 points at the old 5/level rate) turned
# a 7-damage hit into 29 -- and the more levels gained, the worse the
# compounding got. The fix makes a stat point's contribution flat
# (added after level scaling, not before it), so it buys the same
# absolute bonus at every level.

def _damage_at(level: int, strength: int = 0) -> float:
    """The plain hit-vs-defense damage a level-`level` player with
    `strength` points invested deals to a same-level baseline enemy --
    the same differential core/battle.py and the skill-preview payload
    in battle_app.py both compute for an unmodified attack."""
    player_atk = compute_player_stats(PlayerState(level=level, strength=strength)).attack
    enemy_def = derive_enemy_stats(baseline_enemy(level)).defense
    return round(player_atk - enemy_def, 2)


class DerivedStatGrowthCurveTests(unittest.TestCase):
    FIVE_LEVELS_OF_POINTS = LEVEL_UP_STAT_POINTS * 5  # 15 at the current 3/level rate

    def test_baseline_damage_at_zero_investment_is_unchanged(self):
        # The rebalance must not disturb the existing zero-investment
        # curve (the per-level base growth is out of scope here).
        self.assertEqual(_damage_at(1), 7.0)

    def test_five_levels_of_strength_investment_lands_in_the_target_band(self):
        # The brief's own target: "something like 7 to 9" over a
        # 5-level span, replacing the old 7-to-29 blowup.
        before = _damage_at(1, strength=0)
        after = _damage_at(1, strength=self.FIVE_LEVELS_OF_POINTS)
        self.assertEqual(before, 7.0)
        self.assertGreaterEqual(after, 8.0)
        self.assertLessEqual(after, 10.0)
        # Nowhere near the old, broken 29 -- guards against reintroducing
        # the pre-scaling compounding bug.
        self.assertLess(after, 15.0)

    def test_stat_point_damage_bonus_does_not_compound_with_level(self):
        # The actual bug: the same number of invested points must buy
        # the same absolute damage bonus regardless of how many levels
        # the player has also gained, not a bonus that grows with level.
        expected_bonus = round(ATTACK_PER_STRENGTH * self.FIVE_LEVELS_OF_POINTS, 2)
        for level in (1, 3, 6, 10):
            with self.subTest(level=level):
                bonus = _damage_at(level, strength=self.FIVE_LEVELS_OF_POINTS) - _damage_at(level, strength=0)
                self.assertAlmostEqual(bonus, expected_bonus, places=2)

    def test_hp_gain_per_level_of_full_vitality_investment_is_capped_near_15(self):
        one_level_of_points = LEVEL_UP_STAT_POINTS
        for level in (1, 3, 6, 10):
            with self.subTest(level=level):
                before = compute_player_stats(PlayerState(level=level)).max_hp
                after = compute_player_stats(PlayerState(level=level, vitality=one_level_of_points)).max_hp
                gain = round(after - before, 2)
                self.assertAlmostEqual(gain, HP_PER_VITALITY * one_level_of_points, places=2)
                self.assertLessEqual(gain, 15.0 + 1e-6)

    def test_hp_gain_scales_linearly_with_points_not_exponentially_with_level(self):
        # 5 levels' worth of vitality should buy ~5x a single level's
        # HP gain at every sampled level -- not a growing multiple of it.
        one_level = LEVEL_UP_STAT_POINTS
        five_levels = self.FIVE_LEVELS_OF_POINTS
        for level in (1, 5, 10):
            with self.subTest(level=level):
                base = compute_player_stats(PlayerState(level=level)).max_hp
                one_gain = compute_player_stats(PlayerState(level=level, vitality=one_level)).max_hp - base
                five_gain = compute_player_stats(PlayerState(level=level, vitality=five_levels)).max_hp - base
                self.assertAlmostEqual(five_gain, one_gain * 5, places=1)


# ---------- Battle-victory XP wiring ----------

class BattleVictoryExpTests(unittest.TestCase):
    def test_victory_awards_and_reports_exp(self):
        c = client()
        body = force_a_win(c)
        self.assertIn("exp_result", body)
        self.assertGreater(body["exp_result"]["exp_gained"], 0)
        self.assertFalse(body["exp_result"]["leveled_up"])
        self.assertEqual(bundle_for(c)["player"].exp, body["exp_result"]["exp_gained"])

    def test_defeat_awards_no_exp(self):
        c = client()
        start(c, enemy_level=20)
        body = force_a_loss(c)
        self.assertNotIn("exp_result", body)
        self.assertEqual(bundle_for(c)["player"].exp, 0)

    def test_leveling_up_grants_the_configured_stat_points(self):
        c = client()
        player = bundle_for(c)["player"]
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
        player = bundle_for(c)["player"]
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
            self.assertEqual(body["attributes"][stat], 0)

    def test_spend_stat_applies_and_returns_the_updated_player(self):
        c = client()
        bundle_for(c)["player"].stat_points = 3
        res = c.post("/api/player/spend_stat", json={"stat": "strength"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["attributes"]["strength"], 1)
        self.assertEqual(body["stat_points"], 2)

    def test_spend_stat_respects_a_custom_amount(self):
        c = client()
        bundle_for(c)["player"].stat_points = 3
        res = c.post("/api/player/spend_stat", json={"stat": "charisma", "amount": 3})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["attributes"]["charisma"], 3)
        self.assertEqual(body["stat_points"], 0)

    def test_spend_stat_rejects_an_unknown_stat(self):
        c = client()
        bundle_for(c)["player"].stat_points = 3
        res = c.post("/api/player/spend_stat", json={"stat": "not_a_stat"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(bundle_for(c)["player"].stat_points, 3)

    def test_spend_stat_rejects_when_no_points_are_available(self):
        c = client()
        bundle_for(c)["player"].stat_points = 0
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
