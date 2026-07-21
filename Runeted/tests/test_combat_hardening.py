"""Phase 2 regression tests: dodge retirement, stamina, the enemy-HP
invariant, and the structured round-event schema."""
import importlib.util
import os
import unittest

from core.battle import Battle
from core.intent import build_intent
from core.player_state import PlayerState
from core.skills import Skill, default_loadout, stamina_cost_of
from core.stats import (
    ENEMY_STAMINA_REGEN,
    PLAYER_STAMINA_REGEN,
    StatContribution,
    baseline_enemy,
    compute_player_stats,
)

# Generic seed for tests that just need a reproducible battle -- move
# selection is cooldown/stamina-gated random choice each round
# (core/intent.py), not a fixed cyclic deck tied to the seed.
SEED_A = 2

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_battle(player_level=1, enemy_level=1, archetype="brute", seed=SEED_A, **kwargs):
    player = kwargs.pop("player", None) or PlayerState(level=player_level)
    enemy = kwargs.pop("enemy", None) or baseline_enemy(enemy_level, archetype=archetype)
    return Battle(player, enemy, loadout=default_loadout(), rng_seed=seed, **kwargs)


def force_intent(battle, kind):
    """Force the enemy's current (about-to-resolve) move for a
    deterministic test setup -- see test_core_combat.py for why."""
    battle.tracker.current = build_intent(kind, battle.tracker.archetype)
    return battle.tracker.current


class DodgeRetirementTests(unittest.TestCase):
    def test_dodge_service_stays_retired(self):
        self.assertFalse(
            os.path.exists(os.path.join(BACKEND_DIR, "backend", "services", "dodge.py")),
            "services/dodge.py must not come back; dodge lives in the derived-stats pipeline",
        )
        self.assertIsNone(importlib.util.find_spec("services.dodge"))

    def test_zero_dodge_chance_never_dodges(self):
        battle = make_battle(auto=True)  # default dexterity -> dodge_chance 0
        self.assertEqual(battle.stats.dodge_chance, 0.0)
        battle.run_to_completion()
        self.assertFalse(any(r["enemy"]["dodged"] for r in battle.rounds))

    def test_dodge_chance_comes_from_pipeline_and_zeroes_the_hit(self):
        dodge_contrib = (StatContribution(source="test", dodge_flat=0.20),)
        dodged_rounds = []
        for seed in range(60):
            battle = Battle(
                PlayerState(level=1),
                baseline_enemy(3),  # tanky enough for many rounds
                loadout=default_loadout(),
                contributions=dodge_contrib,
                rng_seed=seed,
                auto=True,
            )
            self.assertEqual(battle.stats.dodge_chance, 0.20)
            battle.run_to_completion()
            dodged_rounds.extend(r for r in battle.rounds if r["enemy"]["dodged"])
        self.assertTrue(dodged_rounds, "a 20% dodge chance never fired across 60 seeded battles")
        for r in dodged_rounds:
            self.assertEqual(r["enemy"]["damage_dealt"], 0.0)
            self.assertEqual(r["player"]["hp"]["delta"], 0.0)


class StaminaTests(unittest.TestCase):
    def test_stamina_regenerates_by_fixed_amount_when_holding(self):
        battle = make_battle(enemy_level=3)
        battle.player_stamina = 5.0
        result = battle.play_round(None)
        self.assertEqual(result["player"]["stamina_spent"], 0.0)
        self.assertEqual(result["player"]["stamina_regen"], PLAYER_STAMINA_REGEN)
        self.assertEqual(result["player"]["stamina"]["delta"], PLAYER_STAMINA_REGEN)
        self.assertEqual(result["enemy"]["stamina_regen"], ENEMY_STAMINA_REGEN)

    def test_stamina_regen_is_capped_at_max(self):
        battle = make_battle(enemy_level=3)
        self.assertEqual(battle.player_stamina, battle.stats.max_stamina)
        result = battle.play_round(None)
        self.assertEqual(result["player"]["stamina"]["after"], battle.stats.max_stamina)

    def test_skill_use_costs_roughly_its_value_with_minimum_one(self):
        loadout = default_loadout()
        breaker = loadout.get("breaker_lunge")
        self.assertEqual(stamina_cost_of(breaker), 2)  # value 2
        drawback = Skill(
            id="test_drawback", name="Test Drawback", rarity="common", value=-2,
            element="physical", method="drawback",
        )
        self.assertEqual(stamina_cost_of(drawback), 1)  # floored at 1

        battle = make_battle(enemy_level=3)
        result = battle.play_round("breaker_lunge")
        self.assertEqual(result["player"]["stamina_spent"], 2.0)

    def test_action_blocked_without_enough_stamina(self):
        player = PlayerState(level=1, stamina=1)
        battle = make_battle(player=player)
        with self.assertRaises(ValueError):
            battle.play_round("breaker_lunge")  # costs 2, only 1 available
        # The rejected action must not have advanced or mutated the battle.
        self.assertEqual(battle.round_no, 0)
        self.assertEqual(battle.player_stamina, 1.0)
        self.assertTrue(battle.loadout.can_use("breaker_lunge"))

    def test_auto_policy_respects_stamina(self):
        # Counters cost 2; with 1 stamina the auto policy falls back to
        # the cheapest affordable mitigation (bulwark costs 1)...
        player = PlayerState(level=1, stamina=1)
        battle = make_battle(player=player, auto=True)
        force_intent(battle, "heavy")
        self.assertEqual(battle.choose_auto_response(), "bulwark")
        # ...and with 0 stamina no counter or mitigation is affordable.
        broke = make_battle(player=PlayerState(level=1, stamina=0), auto=True)
        force_intent(broke, "heavy")
        self.assertIsNone(broke.choose_auto_response())

    def test_enemy_pays_stamina_for_its_moves(self):
        battle = make_battle()
        intent = battle.tracker.current
        result = battle.play_round(None)
        self.assertEqual(result["enemy"]["stamina_spent"], float(intent.stamina_cost))

    def test_enemy_falls_back_to_the_cheapest_move_when_stamina_cant_afford_anything(self):
        starving = baseline_enemy(1)
        starving.stamina = 0.0
        starving.max_stamina = 0.0
        battle = make_battle(enemy=starving, seed=SEED_A)
        # Nothing in the pool is affordable at 0 stamina -- emergency
        # fallback to the cheapest move in the whole library.
        self.assertEqual(battle.tracker.current.kind, "basic")
        self.assertEqual(battle.tracker.current.downgraded_from, "stamina")


class EnemyHpInvariantTests(unittest.TestCase):
    def test_normal_battles_never_violate_the_invariant(self):
        for seed in range(10):
            battle = make_battle(seed=seed, auto=True)
            battle.run_to_completion()
            for r in battle.rounds:
                self.assertLessEqual(r["enemy"]["hp"]["delta"], 0.0)

    def test_unexplained_hp_increase_raises_and_logs(self):
        battle = make_battle()
        with self.assertLogs("core.battle", level="ERROR") as logs:
            with self.assertRaises(RuntimeError):
                battle._enforce_enemy_hp_invariant(10.0, 12.0, [], when="this round")
        self.assertIn("none", logs.output[0])

    def test_named_healing_event_permits_the_increase(self):
        battle = make_battle()
        battle._enforce_enemy_hp_invariant(10.0, 12.0, [("regen", 2.0)], when="this round")

    def test_tampered_enemy_hp_is_caught_between_turns(self):
        battle = make_battle(enemy_level=3)
        battle.play_round(None)
        battle.enemy_hp += 5.0  # simulated stray heal outside the loop
        with self.assertLogs("core.battle", level="ERROR"):
            with self.assertRaises(RuntimeError):
                battle.play_round(None)


class RoundEventSchemaTests(unittest.TestCase):
    def test_event_carries_everything_the_frontend_needs(self):
        battle = make_battle()
        event = battle.play_round("breaker_lunge")

        self.assertEqual(event["round"], 1)
        self.assertIn(event["outcome"], ("in_progress", "victory", "defeat"))

        player = event["player"]
        for key in ("action", "response", "response_name", "matched", "damage_dealt",
                    "stamina_spent", "stamina_restored", "stamina_regen", "hp", "stamina"):
            self.assertIn(key, player)
        enemy = event["enemy"]
        for key in ("intent", "resolved", "effect_negated", "dodged", "damage_dealt",
                    "stamina_spent", "stamina_regen", "hp", "stamina"):
            self.assertIn(key, enemy)
        for key in ("kind", "name", "description", "downgraded_from"):
            self.assertIn(key, enemy["intent"])
        for side in (player, enemy):
            for resource in ("hp", "stamina"):
                for key in ("before", "after", "delta"):
                    self.assertIn(key, side[resource])

        self.assertIsInstance(event["statuses_applied"], list)
        self.assertIsInstance(event["statuses_removed"], list)
        # The enemy's next move is never revealed in the event -- only
        # what already resolved this round.
        self.assertNotIn("next_telegraph", event)

    def test_deltas_are_consistent_with_damage(self):
        battle = make_battle()
        event = battle.play_round(None)
        self.assertEqual(event["enemy"]["hp"]["delta"], -event["player"]["damage_dealt"])
        self.assertEqual(event["player"]["hp"]["delta"], -event["enemy"]["damage_dealt"])

    def test_stamina_is_written_back_to_player_state_on_finish(self):
        player = PlayerState(level=5)
        battle = make_battle(player=player, enemy_level=1, auto=True)
        battle.run_to_completion()
        self.assertEqual(player.stamina, battle.player_stamina)
        self.assertEqual(player.hp, battle.player_hp)


if __name__ == "__main__":
    unittest.main()
