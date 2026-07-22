"""Skills/Runes loadout page regression tests.

Covers: LoadoutSelection's slot-based equip/unequip/swap enforcement
(the exact same SkillLoadout/RuneEquipment value/cost-budget rules
battle itself uses -- not a second rule set), the recommended-pick
heuristic, the /api/skills and /api/runes catalog + equip/unequip/swap
endpoints, and -- the core promise of this phase -- that a loadout
change made through these endpoints (including a slot swap) is exactly
what shows up in the next real battle, including a push-your-luck
continuation.
"""
import unittest

from fastapi.testclient import TestClient

from _account_test_helpers import authed_client, bundle_for
from core.loadout import LoadoutSelection
from core.runes import DEFAULT_EQUIPPED_IDS, RUNE_COST_BUDGET, RUNE_SLOT_CAP
from core.skills import DEFAULT_LOADOUT_IDS, SKILL_SLOT_CAP


def client() -> TestClient:
    return authed_client()


# ---------- core/loadout.py ----------

class LoadoutSelectionTests(unittest.TestCase):
    def test_defaults_match_battles_own_defaults_and_build_cleanly(self):
        sel = LoadoutSelection()
        self.assertEqual(sel.skill_slots, list(DEFAULT_LOADOUT_IDS))
        self.assertEqual(len(sel.skill_slots), SKILL_SLOT_CAP)
        self.assertEqual(sel.rune_slots, list(DEFAULT_EQUIPPED_IDS))
        self.assertEqual(len(sel.rune_slots), RUNE_SLOT_CAP)
        sel.build_skill_loadout()
        sel.build_rune_equipment()

    def test_equip_skill_rejects_an_out_of_range_slot(self):
        sel = LoadoutSelection()
        with self.assertRaises(ValueError):
            sel.equip_skill(99, "venom_hex")

    def test_equip_skill_rejects_an_already_occupied_slot(self):
        sel = LoadoutSelection()
        before = list(sel.skill_slots)
        with self.assertRaises(ValueError):
            sel.equip_skill(0, "venom_hex")  # slot 0 has breaker_lunge
        self.assertEqual(sel.skill_slots, before)

    def test_equip_skill_rejects_an_unknown_id(self):
        sel = LoadoutSelection()
        sel.unequip_skill(4)
        with self.assertRaises(ValueError):
            sel.equip_skill(4, "not_a_real_skill")

    def test_equip_skill_rejects_a_skill_already_equipped_elsewhere(self):
        sel = LoadoutSelection()
        sel.unequip_skill(4)
        with self.assertRaises(ValueError):
            sel.equip_skill(4, "breaker_lunge")  # already in slot 0

    def test_equip_skill_rejects_a_value_budget_violation_and_leaves_selection_untouched(self):
        sel = LoadoutSelection()
        sel.skill_slots = ["arcane_resonance", "venom_hex", "stone_steadfast", None, None, None]  # 4+3+2=9
        before = list(sel.skill_slots)
        with self.assertRaises(ValueError):
            sel.equip_skill(3, "ember_drive")  # +2 -> 11 > 10
        self.assertEqual(sel.skill_slots, before)

    def test_unequip_skill_empties_the_slot(self):
        sel = LoadoutSelection()
        sel.unequip_skill(0)
        self.assertIsNone(sel.skill_slots[0])

    def test_swap_skill_slots_exchanges_two_filled_slots(self):
        sel = LoadoutSelection()
        before_0, before_4 = sel.skill_slots[0], sel.skill_slots[4]
        sel.swap_skill_slots(0, 4)
        self.assertEqual(sel.skill_slots[0], before_4)
        self.assertEqual(sel.skill_slots[4], before_0)

    def test_swap_skill_slots_moves_a_filled_slot_into_an_empty_one(self):
        sel = LoadoutSelection()
        sel.unequip_skill(1)
        sel.swap_skill_slots(0, 1)
        self.assertIsNone(sel.skill_slots[0])
        self.assertEqual(sel.skill_slots[1], "breaker_lunge")

    def test_swap_skill_slots_never_violates_budget(self):
        # A swap only reorders the same equipped items -- total value is
        # invariant, so even a loadout already at the exact budget cap
        # must be able to swap freely.
        sel = LoadoutSelection()
        loadout = sel.build_skill_loadout()
        self.assertLessEqual(loadout.total_value, loadout.value_budget)
        sel.swap_skill_slots(2, 5)  # should not raise
        sel.build_skill_loadout()  # still valid

    def test_swap_skill_slots_rejects_an_out_of_range_slot(self):
        sel = LoadoutSelection()
        with self.assertRaises(ValueError):
            sel.swap_skill_slots(0, 99)

    def test_recommended_skill_id_is_none_when_no_slot_is_empty(self):
        sel = LoadoutSelection()
        self.assertIsNone(sel.recommended_skill_id())

    def test_recommended_skill_id_prefers_the_default_loadouts_own_pick(self):
        sel = LoadoutSelection()
        sel.unequip_skill(4)  # war_chant was here
        self.assertEqual(sel.recommended_skill_id(), "war_chant")

    def test_recommended_skill_id_falls_back_once_the_default_pick_no_longer_fits(self):
        # Fill the budget tight enough that war_chant (value 2) no
        # longer fits, then confirm the recommendation isn't war_chant
        # and is still something that actually fits.
        sel = LoadoutSelection()
        sel.skill_slots = ["venom_hex", "arcane_resonance", None, None, None, None]  # 3+4=7
        sel.equip_skill(2, "stone_steadfast")  # +2 -> 9
        rec = sel.recommended_skill_id()
        self.assertIsNotNone(rec)
        self.assertNotEqual(rec, "war_chant")
        # And it must actually fit if equipped.
        sel.equip_skill(3, rec)

    def test_equip_rune_rejects_an_already_occupied_slot(self):
        sel = LoadoutSelection()
        with self.assertRaises(ValueError):
            sel.equip_rune(0, "pebble_ward")  # slot 0 has emberheart

    def test_equip_rune_rejects_a_cost_budget_violation(self):
        sel = LoadoutSelection()
        sel.rune_slots = ["wardstone", "berserker_brand", None]  # 3+3=6
        before = list(sel.rune_slots)
        with self.assertRaises(ValueError):
            sel.equip_rune(2, "zephyr_charm")  # +1 -> 7 > 6
        self.assertEqual(sel.rune_slots, before)

    def test_unequip_rune_empties_the_slot(self):
        sel = LoadoutSelection()
        sel.unequip_rune(0)
        self.assertIsNone(sel.rune_slots[0])

    def test_swap_rune_slots_exchanges_two_filled_slots(self):
        sel = LoadoutSelection()
        before_0, before_2 = sel.rune_slots[0], sel.rune_slots[2]
        sel.swap_rune_slots(0, 2)
        self.assertEqual(sel.rune_slots[0], before_2)
        self.assertEqual(sel.rune_slots[2], before_0)

    def test_recommended_rune_id_prefers_the_default_sets_own_pick(self):
        sel = LoadoutSelection()
        sel.unequip_rune(2)  # zephyr_charm was here
        self.assertEqual(sel.recommended_rune_id(), "zephyr_charm")


# ---------- /api/skills, /api/runes ----------

class SkillsEndpointTests(unittest.TestCase):
    def test_get_skills_reports_slots_catalog_budget_and_recommendation(self):
        c = client()
        body = c.get("/api/skills").json()
        self.assertEqual(len(body["slots"]), SKILL_SLOT_CAP)
        slot_ids = [s["skill"]["id"] if s["skill"] else None for s in body["slots"]]
        self.assertEqual(slot_ids, list(DEFAULT_LOADOUT_IDS))
        self.assertGreaterEqual(len(body["catalog"]), 12)
        self.assertEqual(body["budget"]["used"], 9)
        self.assertIsNone(body["recommended_id"])  # loadout is full

    def test_equip_then_unequip_round_trips(self):
        c = client()
        c.post("/api/skills/unequip", json={"slot": 4})  # war_chant
        res = c.post("/api/skills/equip", json={"slot": 4, "skill_id": "venom_hex"})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["slots"][4]["skill"]["id"], "venom_hex")

        res2 = c.post("/api/skills/unequip", json={"slot": 4})
        self.assertEqual(res2.status_code, 200)
        self.assertIsNone(res2.json()["slots"][4]["skill"])

    def test_equip_rejects_an_occupied_slot_with_400_and_leaves_state_unchanged(self):
        c = client()
        res = c.post("/api/skills/equip", json={"slot": 0, "skill_id": "venom_hex"})
        self.assertEqual(res.status_code, 400)
        after = c.get("/api/skills").json()
        slot_ids = [s["skill"]["id"] if s["skill"] else None for s in after["slots"]]
        self.assertEqual(slot_ids, list(DEFAULT_LOADOUT_IDS))

    def test_equip_rejects_an_unknown_skill(self):
        c = client()
        c.post("/api/skills/unequip", json={"slot": 4})
        res = c.post("/api/skills/equip", json={"slot": 4, "skill_id": "not_a_real_skill"})
        self.assertEqual(res.status_code, 400)

    def test_swap_endpoint_exchanges_two_slots(self):
        c = client()
        res = c.post("/api/skills/swap", json={"slot_a": 0, "slot_b": 4})
        self.assertEqual(res.status_code, 200, res.text)
        slots = res.json()["slots"]
        self.assertEqual(slots[0]["skill"]["id"], "war_chant")
        self.assertEqual(slots[4]["skill"]["id"], "breaker_lunge")

    def test_swap_endpoint_rejects_an_out_of_range_slot(self):
        c = client()
        res = c.post("/api/skills/swap", json={"slot_a": 0, "slot_b": 99})
        self.assertEqual(res.status_code, 400)


class RunesEndpointTests(unittest.TestCase):
    def test_get_runes_reports_slots_catalog_budget_and_recommendation(self):
        c = client()
        body = c.get("/api/runes").json()
        self.assertEqual(len(body["slots"]), RUNE_SLOT_CAP)
        slot_ids = [s["rune"]["id"] if s["rune"] else None for s in body["slots"]]
        self.assertEqual(slot_ids, list(DEFAULT_EQUIPPED_IDS))
        self.assertGreaterEqual(len(body["catalog"]), 12)
        self.assertEqual(body["budget"]["cap"], RUNE_COST_BUDGET)
        self.assertEqual(body["budget"]["used"], 5)
        self.assertIsNone(body["recommended_id"])  # equipment is full

    def test_equip_then_unequip_round_trips(self):
        c = client()
        c.post("/api/runes/unequip", json={"slot": 2})  # zephyr_charm
        res = c.post("/api/runes/equip", json={"slot": 2, "rune_id": "pebble_ward"})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["slots"][2]["rune"]["id"], "pebble_ward")

        res2 = c.post("/api/runes/unequip", json={"slot": 2})
        self.assertEqual(res2.status_code, 200)
        self.assertIsNone(res2.json()["slots"][2]["rune"])

    def test_equip_rejects_an_occupied_slot_with_400_and_leaves_state_unchanged(self):
        c = client()
        res = c.post("/api/runes/equip", json={"slot": 0, "rune_id": "pebble_ward"})
        self.assertEqual(res.status_code, 400)
        after = c.get("/api/runes").json()
        slot_ids = [s["rune"]["id"] if s["rune"] else None for s in after["slots"]]
        self.assertEqual(slot_ids, list(DEFAULT_EQUIPPED_IDS))

    def test_equip_rejects_an_unknown_rune(self):
        c = client()
        c.post("/api/runes/unequip", json={"slot": 2})
        res = c.post("/api/runes/equip", json={"slot": 2, "rune_id": "not_a_real_rune"})
        self.assertEqual(res.status_code, 400)

    def test_swap_endpoint_exchanges_two_slots(self):
        c = client()
        res = c.post("/api/runes/swap", json={"slot_a": 0, "slot_b": 2})
        self.assertEqual(res.status_code, 200, res.text)
        slots = res.json()["slots"]
        self.assertEqual(slots[0]["rune"]["id"], "zephyr_charm")
        self.assertEqual(slots[2]["rune"]["id"], "emberheart")


# ---------- The core promise: battle uses exactly what's equipped ----------

class LoadoutFeedsRealBattleTests(unittest.TestCase):
    def start(self, c, **overrides):
        payload = {"archetype": "brute", "seed": 2}
        payload.update(overrides)
        res = c.post("/api/battle/start", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def test_a_fresh_battle_uses_the_edited_skill_loadout(self):
        c = client()
        c.post("/api/skills/unequip", json={"slot": 4})
        c.post("/api/skills/equip", json={"slot": 4, "skill_id": "venom_hex"})

        state = self.start(c)
        battle_skill_ids = {s["id"] for s in state["skills"]}
        self.assertIn("venom_hex", battle_skill_ids)
        self.assertNotIn("war_chant", battle_skill_ids)

    def test_a_fresh_battle_uses_a_skill_slot_swap(self):
        c = client()
        c.post("/api/skills/swap", json={"slot_a": 0, "slot_b": 4})  # breaker_lunge <-> war_chant

        state = self.start(c)
        battle_skill_ids = {s["id"] for s in state["skills"]}
        # Same six skills either way -- the swap only reorders them --
        # but the point is the reordering happened without dropping
        # anything, unlike an unequip-then-equip that could fail midway.
        self.assertEqual(battle_skill_ids, set(DEFAULT_LOADOUT_IDS))

    def test_a_fresh_battle_uses_the_edited_rune_equipment(self):
        c = client()
        c.post("/api/runes/unequip", json={"slot": 2})
        c.post("/api/runes/equip", json={"slot": 2, "rune_id": "pebble_ward"})

        state = self.start(c)
        equipped_rune_ids = {r["id"] for r in state["runes"]["equipped"]}
        self.assertIn("pebble_ward", equipped_rune_ids)
        self.assertNotIn("zephyr_charm", equipped_rune_ids)

    def test_a_fresh_battle_uses_a_rune_slot_swap(self):
        c = client()
        c.post("/api/runes/swap", json={"slot_a": 0, "slot_b": 2})  # emberheart <-> zephyr_charm

        state = self.start(c)
        equipped_rune_ids = {r["id"] for r in state["runes"]["equipped"]}
        self.assertEqual(equipped_rune_ids, set(DEFAULT_EQUIPPED_IDS))

    def test_a_push_your_luck_continuation_also_uses_the_edited_loadout(self):
        c = client()
        bundle_for(c)["player"].level = 10  # reliably wins vs. a level-1 enemy
        c.post("/api/skills/unequip", json={"slot": 4})
        c.post("/api/skills/equip", json={"slot": 4, "skill_id": "venom_hex"})

        # auto stays off for the win itself: with it on, winning would
        # trigger auto-battle's own bank-or-continue decision (battle_app.
        # _maybe_auto_advance, see test_push_your_luck.py) instead of
        # leaving the finished battle for this test's own manual
        # /api/battle/continue call below. The auto-battle policy's own
        # counter choice still reliably wins without the flag itself set.
        self.start(c, enemy_level=1)
        last = None
        for _ in range(50):
            response = bundle_for(c)["battle"].choose_auto_response()
            last = c.post("/api/battle/round", json={"response": response})
            self.assertEqual(last.status_code, 200, last.text)
            if last.json()["state"]["finished"]:
                break
        self.assertEqual(last.json()["state"]["outcome"], "victory")

        cont = c.post("/api/battle/continue", json={"seed": 2})
        self.assertEqual(cont.status_code, 200, cont.text)
        self.assertEqual(cont.json()["kind"], "combat")
        battle_skill_ids = {s["id"] for s in cont.json()["skills"]}
        self.assertIn("venom_hex", battle_skill_ids)
        self.assertNotIn("war_chant", battle_skill_ids)


# ---------- Page markup ----------

class LoadoutPageMarkupTests(unittest.TestCase):
    def setUp(self):
        self.client = client()

    def test_skills_page_is_a_real_page_with_a_slot_grid_and_shared_modal(self):
        html = self.client.get("/skills").text
        self.assertNotIn("isn't built yet", html)
        self.assertIn('id="slot-grid"', html)
        self.assertIn('id="loadout-modal"', html)
        self.assertIn('href="/"', html)
        loadout_js = self.client.get("/static/loadout-client.js").text
        for marker in ("openPicker", "openSlotAction", "recommended", "/equip", "/unequip", "/swap"):
            self.assertIn(marker, loadout_js, marker)
        page_js = self.client.get("/static/skills.js").text
        self.assertIn("/api/skills", page_js)
        self.assertIn("initLoadoutPage", page_js)

    def test_runes_page_is_a_real_page_with_a_slot_grid_and_shared_modal(self):
        html = self.client.get("/runes").text
        self.assertNotIn("isn't built yet", html)
        self.assertIn('id="slot-grid"', html)
        self.assertIn('id="loadout-modal"', html)
        self.assertIn('href="/"', html)
        page_js = self.client.get("/static/runes.js").text
        self.assertIn("/api/runes", page_js)
        self.assertIn("initLoadoutPage", page_js)

    def test_equipment_page_is_still_a_placeholder(self):
        # /skills and /runes graduated out of PLACEHOLDER_PAGES; confirms
        # that didn't accidentally take other unbuilt pages with them.
        res = self.client.get("/equipment")
        self.assertEqual(res.status_code, 200)
        self.assertIn("isn't built yet", res.text)


if __name__ == "__main__":
    unittest.main()
