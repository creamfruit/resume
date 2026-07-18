import unittest

from models.player import Player
from services.rune_system import (
    AMPLIFIER_BONUS_CAP,
    AMPLIFIER_RECIPES,
    amplifier_bonus,
    collect_rune_mods,
    equipped_amplifier,
    generate_amplifier_rune,
    is_amplifier,
    set_equipped_amplifier,
)


class AmplifierRuneTests(unittest.TestCase):
    def test_generate_amplifier_rune_shape(self):
        for recipe_id, recipe in AMPLIFIER_RECIPES.items():
            rune = generate_amplifier_rune(recipe_id)

            self.assertIsInstance(rune, dict)
            self.assertTrue(is_amplifier(rune))
            self.assertEqual(rune["recipe"], recipe_id)
            self.assertEqual(rune["amp_bonus"], recipe["amp_bonus"])
            self.assertFalse(rune["equipped"])
            self.assertEqual(rune["effects"], [])

        self.assertIsNone(generate_amplifier_rune("no_such_recipe"))

    def test_amplifier_multiplies_equipped_rune_mods(self):
        player = Player()
        player.rune_items = [
            {"id": "r1", "rarity": "rare", "effects": [{"type": "attack_mult", "value": 0.10}]},
        ]
        player.rune_loadout = ["r1", None, None, None, None, None]

        baseline = collect_rune_mods(player)
        self.assertAlmostEqual(baseline["attack_mult"], 0.10)
        self.assertEqual(baseline["amp_bonus"], 0.0)

        amp = generate_amplifier_rune("amp_minor")
        player.rune_items.append(amp)
        set_equipped_amplifier(player, amp["id"])

        boosted = collect_rune_mods(player)
        self.assertAlmostEqual(boosted["attack_mult"], 0.11)
        self.assertAlmostEqual(boosted["amp_bonus"], 0.10)

    def test_amplifier_bonus_capped_and_equip_exclusive(self):
        player = Player()
        overtuned = generate_amplifier_rune("amp_major")
        overtuned["amp_bonus"] = 0.9
        overtuned["equipped"] = True
        player.rune_items = [overtuned]

        self.assertEqual(amplifier_bonus(player), AMPLIFIER_BONUS_CAP)

        second = generate_amplifier_rune("amp_minor")
        player.rune_items.append(second)
        set_equipped_amplifier(player, second["id"])

        equipped = [r for r in player.rune_items if is_amplifier(r) and r["equipped"]]
        self.assertEqual(len(equipped), 1)
        self.assertEqual(equipped_amplifier(player)["id"], second["id"])

        set_equipped_amplifier(player, None)
        self.assertIsNone(equipped_amplifier(player))


if __name__ == "__main__":
    unittest.main()
