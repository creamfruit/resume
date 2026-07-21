import unittest

from pydantic import ValidationError

from ai.item_schema import AIDesignedItem
from models.item import Item
from utils.validators import validate_item_payload, validate_item_object


class AIItemValidationTests(unittest.TestCase):
    def test_ai_item_schema_rejects_out_of_range_damage(self):
        with self.assertRaises(ValidationError):
            AIDesignedItem(
                name="Overpowered Blade",
                slot="weapon",
                rarity="legendary",
                damage=200,
                passives=[],
                flavor="",
            )

    def test_validate_item_payload_clamps_inventory_and_market_values(self):
        payload = {
            "name": "Broken Blade",
            "rarity": "legendary",
            "power": 999,
            "slot": "weapon",
            "source": "ai",
            "passives": [],
        }

        item = validate_item_payload(payload)
        self.assertIsInstance(item, Item)
        self.assertLessEqual(item.power, 55)

        object_item = validate_item_object(Item(name="Another Blade", rarity="legendary", power=999, slot="weapon", passives=[]))
        self.assertLessEqual(object_item.power, 55)


if __name__ == "__main__":
    unittest.main()
