import unittest

from models.enemy import Enemy
from models.item import Item
from models.player import Player
from engine.boss_ai import roll_enemy_intent
from engine.player_stats import compute_derived_stats
from engine.death import resolve_battle_outcome


class CombatLoopTelegraphTests(unittest.TestCase):
    def test_regular_enemy_intent_has_name_and_description(self):
        enemy = Enemy(name="Test Raider", level=3, hp=20, max_hp=20, attack=8, archetype="brute")
        intent = roll_enemy_intent(enemy, risk=1)
        self.assertIn("name", intent)
        self.assertIn("description", intent)
        self.assertIn("type", intent)

    def test_player_derived_stats_are_computed_from_equipment_and_runes(self):
        player = Player(
            strength=10,
            vitality=10,
            dexterity=10,
            luck=8,
            equipment={"weapon": Item(name="Sword", rarity="rare", power=5, slot="weapon", passives=[]), "armor": Item(name="Mail", rarity="rare", power=3, slot="armor", passives=[])},
            rune_items=[
                {"id": "r1", "rarity": "rare", "effects": [{"type": "damage_mult", "value": 0.10, "target": "self"}]},
                {"id": "r2", "rarity": "rare", "effects": [{"type": "shield", "value": 8, "target": "self"}]},
            ],
        )
        stats = compute_derived_stats(player)
        self.assertGreater(stats["attack"], 0)
        self.assertGreaterEqual(stats["defense"], 0)
        self.assertGreaterEqual(stats["crit_chance"], 0.0)

    def test_battle_outcome_returns_victory_when_enemy_defeated(self):
        enemy = Enemy(name="Test Raider", level=3, hp=0, max_hp=20, attack=8, archetype="brute")
        player = Player(name="Player") if hasattr(Player, "name") else Player()
        result = resolve_battle_outcome(player, enemy)
        self.assertEqual(result["winner"], "player")


if __name__ == "__main__":
    unittest.main()
