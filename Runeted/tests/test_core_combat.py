"""Phase 1 regression tests: core combat loop and player state.

Seeds pin the intent deck's starting index (random.Random(seed).randrange(4)):
seed 2 -> index 0 (brute deck opens with "heavy"), seed 1 -> index 1
(brute deck opens with "basic").
"""
import unittest

from core.battle import EXPOSED_DAMAGE_BONUS, Battle
from core.intent import ARCHETYPE_DECKS, IntentTracker, build_intent, is_counter
from core.player_state import PlayerState
from core.resolution import Outcome, resolve
from core.skills import (
    SkillLoadout,
    cooldown_of,
    default_loadout,
    skill_by_id,
)
from core.stats import StatContribution, baseline_enemy, compute_player_stats

SEED_BRUTE_OPENS_HEAVY = 2
SEED_BRUTE_OPENS_BASIC = 1


def make_battle(player_level=1, enemy_level=1, archetype="brute", seed=SEED_BRUTE_OPENS_HEAVY, auto=False):
    player = PlayerState(level=player_level)
    enemy = baseline_enemy(enemy_level, archetype=archetype)
    return Battle(player, enemy, loadout=default_loadout(), rng_seed=seed, auto=auto)


class TelegraphTests(unittest.TestCase):
    def test_move_is_telegraphed_before_player_acts(self):
        battle = make_battle()
        telegraph = battle.telegraph()
        self.assertEqual(telegraph["name"], "Brutal Swing")
        self.assertTrue(telegraph["description"])
        result = battle.play_round(None)
        self.assertEqual(result["enemy"]["intent"]["name"], telegraph["name"])

    def test_round_result_telegraphs_next_round_one_ahead(self):
        battle = make_battle()
        result = battle.play_round(None)
        self.assertIsNotNone(result["next_telegraph"])
        self.assertEqual(result["next_telegraph"], battle.telegraph())
        # Brute deck: heavy -> basic
        self.assertEqual(battle.telegraph()["name"], "Measured Strike")

    def test_intent_system_never_writes_onto_the_enemy(self):
        battle = make_battle(auto=True)
        battle.run_to_completion()
        self.assertFalse(hasattr(battle.enemy, "intent"))
        self.assertEqual(len(battle.tracker.history), battle.round_no - 1)


class CounterResolutionTests(unittest.TestCase):
    def test_correct_counter_negates_effect_and_exposes_enemy(self):
        battle = make_battle()
        intent = battle.tracker.current
        self.assertEqual(intent.kind, "heavy")

        r1 = battle.play_round("breaker_lunge")  # breaker_lunge counters heavy
        self.assertTrue(r1["player"]["matched"])
        self.assertTrue(r1["enemy"]["effect_negated"])
        self.assertIn(
            ("enemy", "exposed"),
            [(s["target"], s["status"]) for s in r1["statuses_applied"]],
        )
        # Only the contact graze lands; the telegraphed effect is negated.
        contact_only = round(max(0.0, battle.enemy_stats.attack * intent.contact_mult - battle.stats.defense), 2)
        self.assertEqual(r1["enemy"]["damage_dealt"], contact_only)

        r2 = battle.play_round(None)
        self.assertTrue(r2["player"]["exposed_bonus_applied"])
        self.assertIn(
            ("enemy", "exposed"),
            [(s["target"], s["status"]) for s in r2["statuses_removed"]],
        )
        expected = round(max(1.0, battle.stats.attack * (1.0 + EXPOSED_DAMAGE_BONUS) - battle.enemy_stats.defense), 2)
        self.assertEqual(r2["player"]["damage_dealt"], expected)
        self.assertGreater(r2["player"]["damage_dealt"], r1["player"]["damage_dealt"])

    def test_missing_response_takes_the_full_effect(self):
        battle = make_battle()
        intent = battle.tracker.current
        result = battle.play_round(None)
        full = round(max(1.0, battle.enemy_stats.attack * (intent.contact_mult + intent.effect_mult) - battle.stats.defense), 2)
        self.assertFalse(result["player"]["matched"])
        self.assertEqual(result["enemy"]["damage_dealt"], full)

    def test_wrong_skill_takes_full_effect_and_still_burns_cooldown(self):
        battle = make_battle()
        intent = battle.tracker.current
        result = battle.play_round("flurry_break")  # counters multi, not heavy
        full = round(max(1.0, battle.enemy_stats.attack * (intent.contact_mult + intent.effect_mult) - battle.stats.defense), 2)
        self.assertFalse(result["player"]["matched"])
        self.assertEqual(result["enemy"]["damage_dealt"], full)
        self.assertGreater(battle.loadout.remaining_cooldown("flurry_break"), 0)


class LoadoutCooldownTests(unittest.TestCase):
    def test_skill_on_cooldown_cannot_be_used_again(self):
        battle = make_battle(enemy_level=3)  # enemy tanky enough to outlast cooldown
        battle.play_round("breaker_lunge")
        self.assertFalse(battle.loadout.can_use("breaker_lunge"))
        with self.assertRaises(ValueError):
            battle.play_round("breaker_lunge")
        # The rejected round must not have advanced the battle.
        self.assertEqual(battle.round_no, 1)
        battle.play_round(None)  # cooldown (2) finishes ticking
        self.assertTrue(battle.loadout.can_use("breaker_lunge"))

    def test_response_must_come_from_the_loadout(self):
        battle = make_battle()
        with self.assertRaises(ValueError):
            battle.play_round("not_a_skill")

    def test_loadout_rejects_more_skills_than_capacity(self):
        skills = list(default_loadout().skills.values())
        with self.assertRaises(ValueError):
            SkillLoadout(skills, capacity=len(skills) - 1)

    def test_cooldown_scales_with_skill_value_within_clamp(self):
        loadout = default_loadout()
        for skill in loadout.skills.values():
            self.assertGreaterEqual(cooldown_of(skill), 1)
            self.assertLessEqual(cooldown_of(skill), 3)


class SkillBudgetTests(unittest.TestCase):
    """The value budget is enforced wherever a loadout is built — a
    player can never equip more total value than the cap allows."""

    def test_default_loadout_fits_the_budget(self):
        loadout = default_loadout()
        self.assertLessEqual(loadout.total_value, loadout.value_budget)

    def test_over_budget_loadout_is_rejected(self):
        # 4 + 3 + 2 + 2 = 11 > 10, and none of these modify the budget.
        skills = [skill_by_id(sid) for sid in
                  ("arcane_resonance", "venom_hex", "stone_steadfast", "ember_drive")]
        with self.assertRaises(ValueError) as ctx:
            SkillLoadout(skills)
        self.assertIn("budget", str(ctx.exception))

    def test_budget_modifier_raises_the_cap_while_equipped(self):
        # 4 + 4 + 3 = 11, but blood_pact carries budget_modifier +1.
        skills = [skill_by_id(sid) for sid in ("blood_pact", "arcane_resonance", "venom_hex")]
        loadout = SkillLoadout(skills)
        self.assertEqual(loadout.total_value, 11)
        self.assertEqual(loadout.value_budget, 11)


class SkillMoveTests(unittest.TestCase):
    """The non-attack move kinds added after playtesting: defend, dodge,
    buff, and recovery, all selectable from the same loadout."""

    def test_default_loadout_covers_every_move_kind(self):
        kinds = {s.kind for s in default_loadout().skills.values()}
        self.assertLessEqual({"attack", "defend", "dodge", "buff", "recovery"}, kinds)

    def test_defend_blocks_the_effect_without_dealing_damage(self):
        battle = make_battle()
        intent = battle.tracker.current
        self.assertEqual(intent.kind, "heavy")
        result = battle.play_round("bulwark")
        self.assertEqual(result["player"]["action"], "defend")
        self.assertEqual(result["player"]["damage_dealt"], 0.0)
        self.assertFalse(result["player"]["matched"])
        self.assertTrue(result["enemy"]["effect_negated"])
        # Only the contact graze can land, and no exposure is granted.
        contact_only = round(max(0.0, battle.enemy_stats.attack * intent.contact_mult - battle.stats.defense), 2)
        self.assertEqual(result["enemy"]["damage_dealt"], contact_only)
        self.assertNotIn(
            ("enemy", "exposed"),
            [(s["target"], s["status"]) for s in result["statuses_applied"]],
        )

    def test_dodge_evades_the_whole_move_without_dealing_damage(self):
        battle = make_battle()
        result = battle.play_round("sidestep")
        self.assertEqual(result["player"]["action"], "dodge")
        self.assertEqual(result["player"]["damage_dealt"], 0.0)
        self.assertTrue(result["enemy"]["dodged"])
        self.assertEqual(result["enemy"]["damage_dealt"], 0.0)
        self.assertEqual(result["player"]["hp"]["delta"], 0.0)

    def test_buff_costs_stamina_and_boosts_strikes_until_it_expires(self):
        battle = make_battle()
        chant = battle.loadout.get("war_chant")
        r1 = battle.play_round("war_chant")
        self.assertEqual(r1["player"]["action"], "buff")
        self.assertEqual(r1["player"]["damage_dealt"], 0.0)
        self.assertGreater(r1["player"]["stamina_spent"], 0.0)
        self.assertIn(
            ("player", "empowered"),
            [(s["target"], s["status"]) for s in r1["statuses_applied"]],
        )

        boosted = round(max(1.0, battle.stats.attack * (1.0 + chant.buff_attack_mult) - battle.enemy_stats.defense), 2)
        plain = round(max(1.0, battle.stats.attack - battle.enemy_stats.defense), 2)
        r2 = battle.play_round(None)
        self.assertEqual(r2["player"]["damage_dealt"], boosted)
        r3 = battle.play_round(None)
        self.assertEqual(r3["player"]["damage_dealt"], boosted)
        self.assertIn(
            ("player", "empowered"),
            [(s["target"], s["status"]) for s in r3["statuses_removed"]],
        )
        r4 = battle.play_round(None)
        self.assertEqual(r4["player"]["damage_dealt"], plain)

    def test_recovery_costs_nothing_and_restores_stamina(self):
        player = PlayerState(level=1, stamina=0)
        battle = Battle(player, baseline_enemy(1), loadout=default_loadout(),
                        rng_seed=SEED_BRUTE_OPENS_HEAVY)
        # With an empty stamina bar there is still a legal skill.
        result = battle.play_round("second_wind")
        self.assertEqual(result["player"]["action"], "recovery")
        self.assertEqual(result["player"]["stamina_spent"], 0.0)
        self.assertEqual(result["player"]["stamina_restored"], 3.0)
        self.assertEqual(result["player"]["damage_dealt"], 0.0)
        # +3 restored plus the end-of-round regen.
        self.assertEqual(result["player"]["stamina"]["after"],
                         3.0 + battle.stats.stamina_regen)

    def test_exposed_carries_over_non_strike_rounds(self):
        battle = make_battle(enemy_level=3)
        battle.play_round("breaker_lunge")  # counter -> enemy exposed
        r2 = battle.play_round("bulwark")   # no strike -> exposure not consumed
        self.assertNotIn(
            ("enemy", "exposed"),
            [(s["target"], s["status"]) for s in r2["statuses_removed"]],
        )
        r3 = battle.play_round(None)        # next strike consumes it
        self.assertTrue(r3["player"]["exposed_bonus_applied"])


class AutoBattleTests(unittest.TestCase):
    def test_auto_holds_on_low_danger_moves(self):
        battle = make_battle(seed=SEED_BRUTE_OPENS_BASIC, auto=True)
        self.assertEqual(battle.tracker.current.kind, "basic")
        self.assertIsNone(battle.choose_auto_response())
        r1 = battle.play_round()
        self.assertIsNone(r1["player"]["response"])

    def test_auto_counters_dangerous_moves_with_matching_skill(self):
        battle = make_battle(seed=SEED_BRUTE_OPENS_HEAVY, auto=True)
        self.assertEqual(battle.tracker.current.kind, "heavy")
        r1 = battle.play_round()
        self.assertEqual(r1["player"]["response"], "breaker_lunge")
        self.assertTrue(r1["player"]["matched"])

    def test_auto_falls_back_to_mitigation_without_a_matching_counter(self):
        loadout = SkillLoadout([skill_by_id("bulwark"), skill_by_id("sidestep")])
        battle = Battle(PlayerState(level=1), baseline_enemy(1),
                        loadout=loadout, rng_seed=SEED_BRUTE_OPENS_HEAVY, auto=True)
        self.assertEqual(battle.tracker.current.kind, "heavy")
        # Cheapest affordable mitigation: bulwark (1) over sidestep (2).
        self.assertEqual(battle.choose_auto_response(), "bulwark")

    def test_auto_battle_reliably_wins_at_or_below_level_and_loses_above(self):
        for level in (1, 3, 5):
            for diff in (-1, 0, 1, 2):
                enemy_level = level + diff
                if enemy_level < 1:
                    continue
                for archetype in ARCHETYPE_DECKS:
                    for seed in (0, 1, 2):
                        battle = make_battle(level, enemy_level, archetype, seed=seed, auto=True)
                        outcome = battle.run_to_completion()["outcome"]
                        expected = Outcome.VICTORY.value if diff <= 0 else Outcome.DEFEAT.value
                        self.assertEqual(
                            outcome, expected,
                            f"L{level} vs L{enemy_level} {archetype} seed={seed}",
                        )


class DerivedStatsPipelineTests(unittest.TestCase):
    def test_combat_damage_comes_from_derived_stats_not_raw_fields(self):
        plain = make_battle()
        boosted = Battle(
            PlayerState(level=1),
            baseline_enemy(1),
            loadout=default_loadout(),
            contributions=(StatContribution(source="test", attack_mult=0.5),),
            rng_seed=SEED_BRUTE_OPENS_HEAVY,
        )
        self.assertEqual(boosted.stats.attack, round(plain.stats.attack * 1.5, 2))
        r_plain = plain.play_round(None)
        r_boosted = boosted.play_round(None)
        self.assertGreater(r_boosted["player"]["damage_dealt"], r_plain["player"]["damage_dealt"])

    def test_contributions_affect_defense_hp_crit_and_dodge(self):
        base = compute_player_stats(PlayerState())
        boosted = compute_player_stats(
            PlayerState(),
            contributions=(StatContribution(source="test", defense_flat=3, max_hp_flat=20, crit_flat=0.05, dodge_flat=0.05),),
        )
        self.assertEqual(boosted.defense, base.defense + 3)
        self.assertEqual(boosted.max_hp, base.max_hp + 20)
        self.assertGreater(boosted.crit_chance, base.crit_chance)
        self.assertGreater(boosted.dodge_chance, base.dodge_chance)

    def test_higher_level_enemy_is_stronger_on_the_same_curve(self):
        low = baseline_enemy(2)
        high = baseline_enemy(3)
        self.assertGreater(high.attack, low.attack)
        self.assertGreater(high.max_hp, low.max_hp)
        self.assertGreater(high.defense, low.defense)


class ResolutionTests(unittest.TestCase):
    def test_outcomes(self):
        self.assertIs(resolve(10, 0), Outcome.VICTORY)
        self.assertIs(resolve(0, 10), Outcome.DEFEAT)
        self.assertIs(resolve(5, 5), Outcome.IN_PROGRESS)

    def test_battle_writes_hp_back_to_player_state_on_finish(self):
        battle = make_battle(player_level=3, enemy_level=1, auto=True)
        battle.run_to_completion()
        self.assertIs(battle.outcome, Outcome.VICTORY)
        self.assertEqual(battle.player.hp, battle.player_hp)
        self.assertGreater(battle.player.hp, 0)

        losing = make_battle(player_level=1, enemy_level=3, auto=True)
        losing.run_to_completion()
        self.assertIs(losing.outcome, Outcome.DEFEAT)
        self.assertEqual(losing.player.hp, 0)

    def test_finished_battle_rejects_further_rounds(self):
        battle = make_battle(player_level=5, enemy_level=1, auto=True)
        battle.run_to_completion()
        with self.assertRaises(RuntimeError):
            battle.play_round(None)


class PlayerStateTests(unittest.TestCase):
    def test_gain_exp_levels_up_and_restores_hp(self):
        state = PlayerState(hp=10)
        gained = state.gain_exp(100)
        self.assertEqual(gained, 1)
        self.assertEqual(state.level, 2)
        self.assertEqual(state.stat_points, 5)
        self.assertEqual(state.exp_to_next, 150)
        self.assertIsNone(state.hp)  # level-up restores to full

    def test_spend_stat_requires_points_and_valid_stat(self):
        state = PlayerState()
        self.assertFalse(state.spend_stat("strength"))
        state.stat_points = 2
        self.assertTrue(state.spend_stat("strength"))
        self.assertEqual(state.strength, 6)
        self.assertFalse(state.spend_stat("not_a_stat"))
        self.assertEqual(state.stat_points, 1)

    def test_player_state_stays_lean(self):
        # Equipment, stash, skills, and economy live in their own modules.
        for foreign in ("stash", "equipment", "rune_items", "rune_loadout", "gold",
                        "resources", "runes", "skills", "skill_loadout", "combat_mods", "status"):
            self.assertNotIn(foreign, PlayerState.model_fields)


class IntentSystemTests(unittest.TestCase):
    def test_every_archetype_deck_cycles_through_known_intents(self):
        import random
        for archetype, deck in ARCHETYPE_DECKS.items():
            tracker = IntentTracker(archetype, random.Random(0))
            seen = [tracker.current.kind]
            for _ in range(len(deck) - 1):
                seen.append(tracker.advance().kind)
            self.assertEqual(sorted(seen), sorted(deck))

    def test_counter_matches_archetype_or_kind(self):
        intent = build_intent("heavy", "brute")
        self.assertTrue(is_counter(["brute"], intent))
        self.assertTrue(is_counter(["heavy"], intent))
        self.assertFalse(is_counter(["caster"], intent))


if __name__ == "__main__":
    unittest.main()
