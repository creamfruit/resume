"""Passive Rune system regression tests.

Covers: equip-budget enforcement (slot cap and cost cap at
construction, the only place equipment is built), each starter rune's
passive actually firing during a battle round (on-hit lifesteal,
on-take-hit thorns, start-of-turn dodge bonus, below-hp shield and
damage boost), the baseline guarantee that a rune-less battle fires
nothing, and the battle-screen payload + markup for the equipped-rune
row and its modal.
"""
import random
import unittest

from fastapi.testclient import TestClient

import battle_app
from core.battle import Battle
from core.intent import build_intent
from core.player_state import PlayerState
from core.runes import (
    RUNE_COST_BUDGET,
    RUNE_SLOT_CAP,
    Rune,
    RuneEquipment,
    catalog_runes,
    default_equipment,
    describe_rune,
    rune_by_id,
)
from core.stats import baseline_enemy


class FixedRoll(random.Random):
    """Pins random() (chance + dodge rolls) while leaving the integer
    draws the intent deck uses untouched."""

    def __init__(self, value):
        super().__init__(0)
        self.value = float(value)

    def random(self):
        return self.value


def battle_with(rune_ids, seed=3, player_level=1, enemy_level=1):
    # Equal levels so the enemy survives the player's opening strike —
    # otherwise it never resolves its telegraphed move and the
    # on-take-hit / dodge hooks below never get a chance to fire.
    runes = RuneEquipment([rune_by_id(rid) for rid in rune_ids])
    return Battle(
        PlayerState(level=player_level),
        baseline_enemy(enemy_level),
        runes=runes,
        rng_seed=seed,
    )


def rune_hits(event, effect_type):
    return [e for e in event["rune_events"] if e["type"] == effect_type]


class EquipBudgetTests(unittest.TestCase):
    def test_slot_cap_enforced_at_construction(self):
        cheap = [
            Rune(id=f"filler_{i}", name=f"Filler {i}", cost=0, passives=[])
            for i in range(RUNE_SLOT_CAP + 1)
        ]
        with self.assertRaises(ValueError):
            RuneEquipment(cheap)

    def test_cost_budget_enforced_at_construction(self):
        # Emberheart 2 + Wardstone 3 + Berserker Brand 3 = 8 > 6.
        over = [rune_by_id(r) for r in ("emberheart", "wardstone", "berserker_brand")]
        self.assertGreater(sum(r.cost for r in over), RUNE_COST_BUDGET)
        with self.assertRaises(ValueError):
            RuneEquipment(over)

    def test_default_equipment_fits_both_caps(self):
        equipment = default_equipment()
        self.assertLessEqual(len(equipment.runes), RUNE_SLOT_CAP)
        self.assertLessEqual(equipment.total_cost, RUNE_COST_BUDGET)
        self.assertEqual(len(equipment.runes), 3)
        self.assertEqual(equipment.total_cost, 5)

    def test_every_catalog_rune_carries_effective_passives(self):
        # Each rune's rarity must allow its passives through the shared
        # clamp, or the rune would silently do nothing.
        for rune in catalog_runes():
            self.assertTrue(rune.clamped_passives(), rune.id)
            self.assertIn(rune.description, describe_rune(rune)["full"])

    def test_rune_text_never_leaks_the_underlying_trigger_or_effect_data(self):
        # "Hooks: Emberheart Drain (on_hit: lifesteal 0.1)"-style dumps
        # are developer/debug text, not something a player reads to
        # understand what the rune does -- describe_rune must not
        # surface passive-engine internals in either string.
        for rune in catalog_runes():
            text = describe_rune(rune)
            for internal in ("Hooks:", "trigger", "on_hit", "on_take_hit",
                              "start_of_turn", "below_hp"):
                self.assertNotIn(internal, text["short"], rune.id)
                self.assertNotIn(internal, text["full"], rune.id)


class PassiveFiringTests(unittest.TestCase):
    def test_on_hit_lifesteal_heals_a_share_of_strike_damage(self):
        battle = battle_with(["emberheart"])
        battle.player_hp = 10.0  # headroom so the heal is visible
        # Force the weakest enemy move so this round's hit can't be
        # lethal -- move selection is random now, and a heavier move
        # would clamp HP at 0 and break the exact accounting below.
        battle.tracker.current = build_intent("basic", battle.tracker.archetype)
        event = battle.play_round(None)  # holding strikes

        dealt = event["player"]["damage_dealt"]
        self.assertGreater(dealt, 0)
        (steal,) = rune_hits(event, "lifesteal")
        self.assertEqual(steal["trigger"], "on_hit")
        self.assertAlmostEqual(steal["amount"], round(0.10 * dealt, 2), places=2)
        self.assertGreater(steal["amount"], 0)
        # HP accounting: start − enemy hit + heal.
        self.assertAlmostEqual(
            event["player"]["hp"]["after"],
            10.0 - event["enemy"]["damage_dealt"] + steal["amount"],
            places=2,
        )

    def test_lifesteal_at_full_hp_heals_nothing(self):
        battle = battle_with(["emberheart"])
        event = battle.play_round(None)
        (steal,) = rune_hits(event, "lifesteal")
        self.assertEqual(steal["amount"], 0.0)

    def test_on_take_hit_thorns_reflects_a_share_of_damage_taken(self):
        battle = battle_with(["thornmail_sigil"])
        event = battle.play_round(None)

        taken = event["enemy"]["damage_dealt"]
        self.assertGreater(taken, 0)  # an uncountered move always chips
        (thorns,) = rune_hits(event, "thorns")
        self.assertEqual(thorns["trigger"], "on_take_hit")
        self.assertAlmostEqual(thorns["amount"], round(0.20 * taken, 2), places=2)
        self.assertGreater(thorns["amount"], 0)
        # Enemy HP fell by strike + reflect; the enemy-HP invariant
        # tolerates decreases, so no error was raised getting here.
        self.assertAlmostEqual(
            event["enemy"]["hp"]["after"],
            event["enemy"]["hp"]["before"] - event["player"]["damage_dealt"] - thorns["amount"],
            places=2,
        )

    def test_start_of_turn_dodge_bonus_feeds_the_single_dodge_roll(self):
        battle = battle_with(["zephyr_charm"])
        battle._rng = FixedRoll(0.049)  # just under the +5% rune bonus
        event = battle.play_round(None)
        (dodge,) = rune_hits(event, "dodge_mod")
        self.assertEqual(dodge["trigger"], "start_of_turn")
        self.assertAlmostEqual(dodge["amount"], 0.05, places=3)
        self.assertTrue(event["enemy"]["dodged"])
        self.assertEqual(event["enemy"]["damage_dealt"], 0)

    def test_same_roll_without_the_rune_does_not_dodge(self):
        battle = battle_with([])
        battle._rng = FixedRoll(0.049)
        event = battle.play_round(None)
        self.assertFalse(event["enemy"]["dodged"])

    def test_below_hp_shield_absorbs_incoming_damage(self):
        battle = battle_with(["wardstone"])
        battle.player_hp = round(battle.stats.max_hp * 0.4, 2)  # under the 50% threshold
        event = battle.play_round(None)

        (ward,) = rune_hits(event, "shield")
        self.assertEqual(ward["trigger"], "below_hp")
        self.assertEqual(ward["amount"], 6.0)
        (absorbed,) = rune_hits(event, "shield_absorbed")
        self.assertGreater(absorbed["amount"], 0)
        # What reached the player is the post-absorb remainder.
        self.assertAlmostEqual(
            event["player"]["hp"]["delta"],
            -event["enemy"]["damage_dealt"],
            places=2,
        )

    def test_below_hp_shield_stays_dormant_above_threshold(self):
        battle = battle_with(["wardstone"])
        event = battle.play_round(None)  # full HP
        self.assertEqual(rune_hits(event, "shield"), [])

    def test_below_hp_damage_boost_raises_the_strike(self):
        boosted = battle_with(["berserker_brand"])
        boosted.player_hp = round(boosted.stats.max_hp * 0.3, 2)  # under the 40% threshold
        event = boosted.play_round(None)

        (berserk,) = rune_hits(event, "damage_mult")
        self.assertEqual(berserk["trigger"], "below_hp")
        self.assertAlmostEqual(berserk["amount"], 0.15, places=3)
        expected = round(max(1.0, boosted.stats.attack * 1.15 - boosted.enemy_stats.defense), 2)
        self.assertAlmostEqual(event["player"]["damage_dealt"], expected, places=2)

        control = battle_with([])
        control.player_hp = round(control.stats.max_hp * 0.3, 2)
        plain = control.play_round(None)
        self.assertGreater(event["player"]["damage_dealt"], plain["player"]["damage_dealt"])

    def test_no_runes_fires_nothing(self):
        battle = battle_with([])
        event = battle.play_round(None)
        self.assertEqual(event["rune_events"], [])


class BattleScreenRuneTests(unittest.TestCase):
    """The battle screen serves the equipped runes and ships the row +
    modal affordances the JS builds from that payload."""

    def setUp(self):
        battle_app.CURRENT["battle"] = None
        battle_app.CURRENT["player"] = PlayerState()
        self.client = TestClient(battle_app.app)

    def start(self):
        res = self.client.post(
            "/api/battle/start",
            json={"enemy_level": 1, "archetype": "brute", "seed": 2},
        )
        self.assertEqual(res.status_code, 200)
        return res.json()

    def test_state_serves_equipped_runes_with_budget(self):
        state = self.start()
        runes = state["runes"]
        self.assertEqual(len(runes["equipped"]), 3)
        self.assertEqual(runes["slots"], RUNE_SLOT_CAP)
        self.assertEqual(runes["cost_cap"], RUNE_COST_BUDGET)
        self.assertEqual(runes["cost_used"], 5)
        for rune in runes["equipped"]:
            for key in ("id", "name", "icon", "type", "rarity", "cost",
                        "description", "short", "full_text"):
                self.assertIn(key, rune)
            self.assertIn("Passive", rune["full_text"])

    def test_markup_ships_rune_row_and_shared_modal_wiring(self):
        html = self.client.get("/battle").text
        js = self.client.get("/static/app.js").text
        css = self.client.get("/static/style.css").text
        for element_id in ("rune-panel", "rune-panel-title", "rune-row"):
            self.assertIn(f'id="{element_id}"', html, element_id)
        for marker in ("renderRunes", "openRuneModal", "RUNE_ICONS", "rune-chip"):
            self.assertIn(marker, js, marker)
        # The rune modal reuses the skill modal shell, not a second dialog.
        self.assertIn('$("skill-modal-title")', js.split("function openRuneModal")[1])
        self.assertEqual(html.count('role="dialog"'), 1)
        self.assertIn(".rune-chip", css)

    def test_action_bar_pass_rename_and_auto_spin_markers(self):
        html = self.client.get("/battle").text
        js = self.client.get("/static/app.js").text
        css = self.client.get("/static/style.css").text
        self.assertIn("Pass (no skill)", html)
        self.assertNotIn("Hold (no skill)", html + js)
        self.assertIn('id="hold-icon"', html)
        self.assertIn('id="auto-icon"', html)
        self.assertIn('classList.toggle("spinning", state.auto)', js)
        self.assertIn("@keyframes icon-spin", css)


if __name__ == "__main__":
    unittest.main()
