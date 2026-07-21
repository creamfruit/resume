"""Phase 1 regression tests: core combat loop and player state.

Move selection is cooldown/stamina-gated random choice each round
(core/intent.py), not a fixed cyclic deck with a seed-pinned starting
index -- a seed alone no longer guarantees a specific opening move.
Tests that need a specific enemy move for their setup force it
directly via `force_intent()` instead.
"""
import random
import unittest

from core.battle import EXPOSED_DAMAGE_BONUS, Battle
from core.intent import ARCHETYPE_DECKS, INTENT_LIBRARY, IntentTracker, build_intent, is_counter
from core.player_state import PlayerState
from core.resolution import Outcome, resolve
from core.skills import (
    SkillLoadout,
    cooldown_of,
    default_loadout,
    skill_by_id,
)
from core.stats import StatContribution, baseline_enemy, compute_player_stats

# Generic seeds for tests that just need a reproducible battle -- not
# tied to any specific opening move.
SEED_A = 2
SEED_B = 1


def make_battle(player_level=1, enemy_level=1, archetype="brute", seed=SEED_A, auto=False):
    player = PlayerState(level=player_level)
    enemy = baseline_enemy(enemy_level, archetype=archetype)
    return Battle(player, enemy, loadout=default_loadout(), rng_seed=seed, auto=auto)


def force_intent(battle, kind):
    """Force the enemy's current (about-to-resolve) move for a
    deterministic test setup. Selection is live cooldown/stamina-gated
    random choice each round, so tests needing a specific move force it
    directly rather than relying on a seed to happen to produce it."""
    battle.tracker.current = build_intent(kind, battle.tracker.archetype)
    return battle.tracker.current


class NoForeknowledgeTests(unittest.TestCase):
    """The enemy's move for the round is decided by the engine and is
    never revealed to the player before it resolves -- these tests lock
    in every surface that used to leak it a round in advance."""

    def test_battle_has_no_telegraph_method(self):
        battle = make_battle()
        self.assertFalse(hasattr(battle, "telegraph"))

    def test_intent_tracker_has_no_telegraph_method(self):
        battle = make_battle()
        self.assertFalse(hasattr(battle.tracker, "telegraph"))

    def test_round_event_never_carries_the_next_move(self):
        battle = make_battle()
        result = battle.play_round(None)
        self.assertNotIn("next_telegraph", result)

    def test_movelist_reveals_no_specific_upcoming_move(self):
        # The movelist is the pool plus live cooldown state only -- it
        # never says which one is about to resolve.
        battle = make_battle()
        for move in battle.movelist():
            self.assertNotIn("is_next", move)
            self.assertNotIn("upcoming", move)

    def test_intent_system_never_writes_onto_the_enemy(self):
        battle = make_battle(auto=True)
        battle.run_to_completion()
        self.assertFalse(hasattr(battle.enemy, "intent"))
        self.assertEqual(len(battle.tracker.history), battle.round_no - 1)


class CounterResolutionTests(unittest.TestCase):
    def test_correct_counter_negates_effect_and_exposes_enemy(self):
        battle = make_battle()
        intent = force_intent(battle, "heavy")

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
        intent = force_intent(battle, "heavy")
        result = battle.play_round(None)
        full = round(max(1.0, battle.enemy_stats.attack * (intent.contact_mult + intent.effect_mult) - battle.stats.defense), 2)
        self.assertFalse(result["player"]["matched"])
        self.assertEqual(result["enemy"]["damage_dealt"], full)

    def test_wrong_skill_takes_full_effect_and_still_burns_cooldown(self):
        battle = make_battle()
        intent = force_intent(battle, "heavy")
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
        intent = force_intent(battle, "heavy")
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
                        rng_seed=SEED_A)
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
        force_intent(battle, "heavy")
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
        battle = make_battle(seed=SEED_B, auto=True)
        force_intent(battle, "basic")
        self.assertIsNone(battle.choose_auto_response())
        r1 = battle.play_round()
        self.assertIsNone(r1["player"]["response"])

    def test_auto_counters_dangerous_moves_with_matching_skill(self):
        battle = make_battle(seed=SEED_A, auto=True)
        force_intent(battle, "heavy")
        r1 = battle.play_round()
        self.assertEqual(r1["player"]["response"], "breaker_lunge")
        self.assertTrue(r1["player"]["matched"])

    def test_auto_falls_back_to_mitigation_without_a_matching_counter(self):
        loadout = SkillLoadout([skill_by_id("bulwark"), skill_by_id("sidestep")])
        battle = Battle(PlayerState(level=1), baseline_enemy(1),
                        loadout=loadout, rng_seed=SEED_A, auto=True)
        force_intent(battle, "heavy")
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
            rng_seed=SEED_A,
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
    def test_every_archetype_pool_eventually_produces_every_known_move(self):
        # Selection is cooldown/stamina-gated random choice, not a fixed
        # cycle -- over enough rounds every pool member should still
        # appear (generous stamina so only cooldown gates selection).
        for archetype, deck in ARCHETYPE_DECKS.items():
            pool = set(deck)
            tracker = IntentTracker(archetype, random.Random(0), stamina_budget=99)
            seen = {tracker.current.kind}
            for _ in range(40):
                seen.add(tracker.advance(stamina_budget=99).kind)
            self.assertEqual(seen, pool, archetype)

    def test_a_move_just_used_is_not_selectable_again_immediately(self):
        # A cooldown of 1 (basic's) nets to 0 the same round it's used --
        # same convention as the player's own cooldown=1 skills, where
        # there's no real gate either. Only cooldown > 1 moves (heavy,
        # guard_break, multi) should still show as cooling right after.
        tracker = IntentTracker("brute", random.Random(1), stamina_budget=99)
        for _ in range(30):
            used_kind = tracker.current.kind
            tracker.advance(stamina_budget=99)
            if tracker.current.downgraded_from is None and INTENT_LIBRARY[used_kind]["cooldown"] > 1:
                self.assertGreater(tracker.remaining_cooldown(used_kind), 0)

    def test_remaining_cooldown_counts_down_to_zero(self):
        tracker = IntentTracker("brute", random.Random(1))
        tracker.current = build_intent("multi", "brute")  # cooldown 3
        tracker.advance(stamina_budget=99)
        self.assertEqual(tracker.remaining_cooldown("multi"), 2)
        tracker.advance(stamina_budget=99)
        self.assertEqual(tracker.remaining_cooldown("multi"), 1)
        tracker.advance(stamina_budget=99)
        self.assertEqual(tracker.remaining_cooldown("multi"), 0)

    def test_movelist_reports_the_full_pool_with_live_cooldowns(self):
        tracker = IntentTracker("brute", random.Random(2))
        kinds = {m["kind"] for m in tracker.movelist()}
        self.assertEqual(kinds, {"heavy", "basic", "multi"})  # brute's distinct pool
        for move in tracker.movelist():
            self.assertEqual(move["remaining_cooldown"], 0)  # nothing used yet
        tracker.current = build_intent("heavy", "brute")
        tracker.advance(stamina_budget=99)
        heavy = next(m for m in tracker.movelist() if m["kind"] == "heavy")
        self.assertGreater(heavy["remaining_cooldown"], 0)

    def test_falls_back_to_the_cheapest_move_when_every_pool_move_is_on_cooldown(self):
        tracker = IntentTracker("brute", random.Random(3))
        for kind in tracker._pool:
            tracker._cooldowns[kind] = 5
        forced = tracker._roll(stamina_budget=99)
        self.assertEqual(forced.kind, "basic")  # cheapest in the whole library
        self.assertEqual(forced.downgraded_from, "cooldown")

    def test_counter_matches_archetype_or_kind(self):
        intent = build_intent("heavy", "brute")
        self.assertTrue(is_counter(["brute"], intent))
        self.assertTrue(is_counter(["heavy"], intent))
        self.assertFalse(is_counter(["caster"], intent))


if __name__ == "__main__":
    unittest.main()
