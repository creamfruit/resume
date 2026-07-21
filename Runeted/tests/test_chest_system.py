"""Chest reward system regression tests.

Covers: the chest model's own rarity tier and its floor/ceiling content
window (the core ask — a chest can never roll contents outside its
declared bounds), the enemy-driven chest-tier roll reusing
engine.loot.roll_rarity rather than a second probability system,
opening as a single consuming action across all three content kinds
(item/rune/currency), the independent chest/currency battle-victory
award ("instead of, or alongside"), and that the victory hook in
main.py is actually wired to this system.
"""
import inspect
import unittest
from unittest.mock import patch

from models.enemy import Enemy
from models.player import Player
from services.chest import (
    CHEST_RARITY_ORDER,
    CONTENT_KIND_WEIGHTS,
    _enemy_risk_score,
    award_battle_chest,
    chest_content_bounds,
    grant_chest,
    open_chest,
    roll_chest_tier,
)


def make_enemy(level=1, tier="normal", elite=False, modifiers=None):
    return Enemy(
        name="Test Foe", level=level, hp=10, attack=5,
        tier=tier, elite=elite, modifiers=list(modifiers or []),
    )


class ChestContentBoundsTests(unittest.TestCase):
    """The floor/ceiling window itself, independent of any rolling."""

    def test_every_tier_windows_to_one_below_and_one_above(self):
        expected = {
            "common": ("common", "rare"),
            "rare": ("common", "epic"),
            "epic": ("rare", "legendary"),
            "legendary": ("epic", "mythic"),
            "mythic": ("legendary", "relic"),
            "relic": ("mythic", "relic"),
        }
        for tier, bounds in expected.items():
            self.assertEqual(chest_content_bounds(tier), bounds, tier)

    def test_common_chest_can_never_reach_legendary(self):
        floor, ceiling = chest_content_bounds("common")
        self.assertLess(CHEST_RARITY_ORDER.index(ceiling), CHEST_RARITY_ORDER.index("legendary"))

    def test_legendary_chest_floor_is_well_above_junk(self):
        floor, _ = chest_content_bounds("legendary")
        self.assertGreater(CHEST_RARITY_ORDER.index(floor), CHEST_RARITY_ORDER.index("rare"))

    def test_floor_is_non_decreasing_across_the_ladder(self):
        floors = [CHEST_RARITY_ORDER.index(chest_content_bounds(t)[0]) for t in CHEST_RARITY_ORDER]
        self.assertEqual(floors, sorted(floors))

    def test_unknown_rarity_string_falls_back_to_common_bounds(self):
        self.assertEqual(chest_content_bounds("not_a_tier"), chest_content_bounds("common"))


class EnemyRiskScoreTests(unittest.TestCase):
    """The enemy-derived number fed into the reused roll_rarity call."""

    def test_baseline_level_one_normal_enemy_is_zero_risk(self):
        self.assertEqual(_enemy_risk_score(make_enemy(level=1, tier="normal")), 0)

    def test_level_scales_risk_linearly_above_one(self):
        self.assertEqual(_enemy_risk_score(make_enemy(level=8, tier="normal")), 7)

    def test_boss_tier_adds_a_flat_bonus(self):
        self.assertEqual(_enemy_risk_score(make_enemy(level=1, tier="boss")), 6)

    def test_elite_flag_adds_a_smaller_flat_bonus_even_if_tier_is_normal(self):
        self.assertEqual(_enemy_risk_score(make_enemy(level=1, tier="normal", elite=True)), 3)

    def test_modifiers_from_the_encounter_phase_each_add_one(self):
        enemy = make_enemy(level=6, tier="elite", modifiers=["colossal", "volatile", "runic"])
        # (6-1) level + 3 elite + 3 modifiers
        self.assertEqual(_enemy_risk_score(enemy), 5 + 3 + 3)

    def test_roll_chest_tier_feeds_risk_and_boss_flag_into_loot_roll_rarity(self):
        enemy = make_enemy(level=6, tier="boss", modifiers=["swift"])
        with patch("services.chest.roll_rarity", return_value="epic") as spy:
            result = roll_chest_tier(enemy, luck_bonus=0.4)
        spy.assert_called_once_with(is_boss=True, risk=5 + 6 + 1, luck_bonus=0.4)
        self.assertEqual(result, "epic")


class OpenChestBoundsTests(unittest.TestCase):
    """The core regression: opening any chest of a given tier, many
    times, never produces contents outside that tier's declared window
    — a hard clamp, not a probabilistic tendency, so this cannot flake."""

    TRIALS = 50

    def _open_many(self, tier):
        player = Player()
        rarities = []
        for _ in range(self.TRIALS):
            grant_chest(player, tier)
            out = open_chest(player, tier)
            self.assertTrue(out["ok"], out)
            rarities.append(out["rarity"])
        return rarities

    def test_every_tier_stays_within_its_own_window_across_many_opens(self):
        for tier in CHEST_RARITY_ORDER:
            floor, ceiling = chest_content_bounds(tier)
            lo, hi = CHEST_RARITY_ORDER.index(floor), CHEST_RARITY_ORDER.index(ceiling)
            for rarity in self._open_many(tier):
                idx = CHEST_RARITY_ORDER.index(rarity)
                self.assertTrue(lo <= idx <= hi, f"{tier} chest rolled {rarity} outside [{floor}, {ceiling}]")

    def test_common_chest_never_yields_a_legendary_weapon(self):
        for rarity in self._open_many("common"):
            self.assertNotIn(rarity, {"legendary", "mythic", "relic"})

    def test_legendary_chest_never_rolls_pure_junk(self):
        for rarity in self._open_many("legendary"):
            self.assertNotIn(rarity, {"common", "rare"})

    def test_content_kind_is_always_one_of_the_declared_three(self):
        player = Player()
        for _ in range(self.TRIALS):
            grant_chest(player, "epic")
            out = open_chest(player, "epic")
            self.assertIn(out["kind"], CONTENT_KIND_WEIGHTS)
            self.assertIn(out["kind"], out)  # e.g. out["item"] / out["rune"] / out["currency"]

    def test_item_and_rune_rewards_carry_exactly_the_clamped_rarity(self):
        # forced_rarity / rarity_override must keep the generated
        # item/rune internally consistent with the rarity label, not
        # just cosmetically stamped after the fact.
        player = Player()
        found_item = found_rune = False
        for _ in range(200):
            if found_item and found_rune:
                break
            grant_chest(player, "epic")
            out = open_chest(player, "epic")
            if out["kind"] == "item":
                self.assertEqual(player.stash[-1].rarity, out["rarity"])
                found_item = True
            elif out["kind"] == "rune":
                self.assertEqual(player.rune_items[-1]["rarity"], out["rarity"])
                found_rune = True
        self.assertTrue(found_item and found_rune, "didn't observe both kinds in 200 opens")


class OpenChestInventoryTests(unittest.TestCase):
    def test_open_consumes_exactly_one_chest_of_that_tier(self):
        player = Player()
        grant_chest(player, "rare")
        grant_chest(player, "rare")
        grant_chest(player, "rare")
        open_chest(player, "rare")
        self.assertEqual(player.chests["rare"], 2)

    def test_opening_with_none_held_is_a_no_op_error(self):
        player = Player()
        out = open_chest(player, "mythic")
        self.assertFalse(out["ok"])
        self.assertIn("mythic", out["error"])
        self.assertEqual(len(player.stash), 0)
        self.assertEqual(len(player.rune_items), 0)

    def test_grant_chest_clamps_an_unrecognized_rarity_to_common(self):
        player = Player()
        rarity = grant_chest(player, "not_a_real_rarity")
        self.assertEqual(rarity, "common")
        self.assertEqual(player.chests["common"], 1)

    def test_player_starts_with_no_chests_and_prestige_clears_them(self):
        player = Player()
        self.assertEqual(player.chests, {})
        grant_chest(player, "relic")
        self.assertEqual(player.chests["relic"], 1)
        player.prestige_reset()
        self.assertEqual(player.chests, {})


class AwardBattleChestTests(unittest.TestCase):
    """Two independent rolls: a chest and a currency amount are each
    reachable alone, together, or not at all."""

    def _enemy(self):
        return make_enemy(level=5, tier="normal")

    def test_chest_and_currency_can_both_drop(self):
        with patch("services.chest.random.random", side_effect=[0.0, 0.0]), \
             patch("services.chest.roll_chest_tier", return_value="rare"), \
             patch("services.chest.roll_currency_reward", return_value=("gold", 42)):
            player = Player()
            out = award_battle_chest(player, self._enemy(), risk=0, room_type="combat")
        self.assertEqual(out["chest"], "rare")
        self.assertEqual(out["currency"], {"currency_id": "gold", "amount": 42})
        self.assertEqual(player.chests.get("rare"), 1)
        self.assertEqual(player.gold, 42)

    def test_chest_only_when_the_currency_roll_misses(self):
        with patch("services.chest.random.random", side_effect=[0.0, 0.99]), \
             patch("services.chest.roll_chest_tier", return_value="epic"):
            out = award_battle_chest(Player(), self._enemy(), risk=0, room_type="combat")
        self.assertEqual(out["chest"], "epic")
        self.assertIsNone(out["currency"])

    def test_currency_only_when_the_chest_roll_misses(self):
        with patch("services.chest.random.random", side_effect=[0.99, 0.0]), \
             patch("services.chest.roll_chest_tier", return_value="epic"), \
             patch("services.chest.roll_currency_reward", return_value=("crafted_supplies", 3)):
            out = award_battle_chest(Player(), self._enemy(), risk=0, room_type="combat")
        self.assertIsNone(out["chest"])
        self.assertEqual(out["currency"], {"currency_id": "crafted_supplies", "amount": 3})

    def test_neither_drops_when_both_rolls_miss(self):
        with patch("services.chest.random.random", side_effect=[0.99, 0.99]):
            out = award_battle_chest(Player(), self._enemy(), risk=0, room_type="combat")
        self.assertIsNone(out["chest"])
        self.assertIsNone(out["currency"])

    def test_boss_room_raises_the_chest_chance_enough_to_flip_a_fixed_roll(self):
        # A fixed 0.40 roll sits between combat's chest_chance (0.10,
        # gate stays closed) and boss's (0.45, gate opens) — a direct,
        # deterministic demonstration that room_type reaches the
        # formula rather than a probability-curve assertion.
        with patch("services.chest.random.random", return_value=0.40), \
             patch("services.chest.roll_chest_tier", return_value="common"):
            combat_out = award_battle_chest(Player(), self._enemy(), risk=0, room_type="combat")
            boss_out = award_battle_chest(Player(), self._enemy(), risk=0, room_type="boss")
        self.assertIsNone(combat_out["chest"])
        self.assertEqual(boss_out["chest"], "common")


class BattleVictoryWiringTests(unittest.TestCase):
    """main.py's single 'enemy defeated' hook must actually call into
    this system — a lightweight source check rather than simulating the
    whole dungeon session, which nothing else in this codebase does
    either (main.py's session machinery has no existing test coverage
    to build on)."""

    def test_handle_enemy_defeat_calls_award_battle_chest_not_the_old_flat_resource(self):
        import main
        source = inspect.getsource(main._handle_enemy_defeat)
        self.assertIn("award_battle_chest", source)
        self.assertNotIn('"arcane_chest"', source)
        self.assertNotIn("add_resource(\"arcane_chest\"", source)

    def test_victory_rewards_payloads_expose_chest_and_chest_currency_keys(self):
        import main
        source = inspect.getsource(main._handle_enemy_defeat)
        self.assertEqual(source.count('"chest": chest_rarity_gain'), 3)
        self.assertEqual(source.count('"chest_currency": currency_award'), 3)

    def test_chest_endpoints_are_registered(self):
        import main
        paths = {getattr(r, "path", "") for r in main.app.routes}
        self.assertIn("/player/chests", paths)
        self.assertIn("/chests/open", paths)


if __name__ == "__main__":
    unittest.main()
