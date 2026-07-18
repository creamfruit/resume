import unittest

from engine.enemy_factory import create_enemy
from engine.passive_system import collect_equipment_passives
from models.enemy import Enemy
from models.item import Item
from models.passive import PassiveEffect, PassiveModel
from models.player import Player
from services.auction_house import list_item
from services.stash import dismantle_item


class CombatLoadoutIntegrationTests(unittest.TestCase):
    def test_collect_equipment_passives_includes_weapon_innate_abilities(self):
        weapon = Item(
            name="Unique Blade",
            rarity="legendary",
            power=24,
            slot="weapon",
            passives=[
                PassiveModel(
                    name="Razor Edge",
                    trigger="on_hit",
                    effects=[PassiveEffect(type="damage_mult", value=0.08)],
                )
            ],
            innate_abilities=[
                PassiveModel(
                    name="Wild Instinct",
                    trigger="start_of_turn",
                    effects=[PassiveEffect(type="dodge_mod", value=0.06)],
                ),
                PassiveModel(
                    name="Cinder Burst",
                    trigger="on_hit",
                    effects=[PassiveEffect(type="dot", value=3.5, duration=2)],
                ),
            ],
        )
        player = Player(equipment={"weapon": weapon, "armor": None})

        passives = collect_equipment_passives(player)
        names = {p.name for p in passives}

        self.assertIn("Razor Edge", names)
        self.assertIn("Wild Instinct", names)
        self.assertIn("Cinder Burst", names)

    def test_enemy_factory_rolls_stacked_modifiers_for_low_depth_enemy(self):
        enemy = create_enemy(depth=1, risk=0)

        self.assertIsInstance(enemy, Enemy)
        self.assertGreaterEqual(len(enemy.modifiers), 2)
        self.assertLessEqual(len(enemy.modifiers), 3)
        self.assertTrue(any(mod in enemy.modifiers for mod in ("colossal", "volatile", "runic")))

    def test_dismantle_item_yields_crafting_material(self):
        player = Player()
        player.stash.append(Item(name="Crude Blade", rarity="rare", power=12, slot="weapon", passives=[]))

        result = dismantle_item(player, 0)

        self.assertTrue(result["ok"])
        self.assertGreaterEqual(player.resources.get("crafted_supplies", 0), 1)

    def test_market_rejects_common_items_below_floor(self):
        player = Player()
        player.stash.append(Item(name="Scrap Edge", rarity="common", power=8, slot="weapon", passives=[]))

        result = list_item(player, 0, price=10, seller="player")

        self.assertIn("error", result)
        self.assertEqual(len(player.stash), 1)


if __name__ == "__main__":
    unittest.main()
