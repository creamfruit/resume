"""Battle screen smoke tests: the API the screen consumes, and the
static page's required affordances (skill buttons, info modal, cancel,
figurines, floaters, battle log, two-column layout)."""
import re
import unittest

from fastapi.testclient import TestClient

import battle_app
from core.skills import default_loadout, describe_skill


def client() -> TestClient:
    battle_app.CURRENT["battle"] = None  # isolate tests
    return TestClient(battle_app.app)


def start(c: TestClient, **overrides):
    payload = {"player_level": 1, "enemy_level": 1, "archetype": "brute", "seed": 2}
    payload.update(overrides)
    res = c.post("/api/battle/start", json=payload)
    assert res.status_code == 200, res.text
    return res.json()


class BattleApiSmokeTests(unittest.TestCase):
    def test_start_returns_full_screen_state(self):
        c = client()
        state = start(c)
        self.assertEqual(state["outcome"], "in_progress")
        self.assertIn("name", state["telegraph"])
        self.assertIn("description", state["telegraph"])
        self.assertEqual(len(state["skills"]), 6)
        for skill in state["skills"]:
            for key in ("id", "name", "icon", "kind", "damage", "description", "full_text",
                        "stamina_cost", "cooldown", "remaining_cooldown", "usable",
                        "counters", "applies_status"):
                self.assertIn(key, skill)
            self.assertTrue(skill["usable"])

    def test_loadout_covers_all_move_kinds_in_one_button_list(self):
        # Defend, dodge, buff, and recovery render alongside attacks in
        # the same flat skills list — no separate button categories.
        state = start(client())
        kinds = {s["kind"] for s in state["skills"]}
        self.assertLessEqual({"attack", "defend", "dodge", "buff", "recovery"}, kinds)
        for skill in state["skills"]:
            if skill["kind"] == "attack":
                self.assertGreater(skill["damage"], 0)
            else:
                self.assertEqual(skill["damage"], 0)
            if skill["kind"] == "recovery":
                self.assertEqual(skill["stamina_cost"], 0)

    def test_state_reports_the_enforced_value_budget(self):
        state = start(client())
        self.assertIn("budget", state)
        self.assertLessEqual(state["budget"]["used"], state["budget"]["cap"])

    def test_state_requires_an_active_battle(self):
        c = client()
        self.assertEqual(c.get("/api/battle/state").status_code, 404)

    def test_round_returns_structured_event_and_updated_state(self):
        c = client()
        start(c)
        res = c.post("/api/battle/round", json={"response": "breaker_lunge"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        event, state = body["event"], body["state"]
        self.assertEqual(event["round"], 1)
        self.assertTrue(event["player"]["matched"])  # seed 2: brute opens heavy
        self.assertIn("hp", event["player"])
        self.assertIn("delta", event["enemy"]["hp"])
        self.assertLess(state["enemy"]["hp"], state["enemy"]["max_hp"])
        breaker = next(s for s in state["skills"] if s["id"] == "breaker_lunge")
        self.assertGreater(breaker["remaining_cooldown"], 0)
        self.assertFalse(breaker["usable"])

    def test_recovery_is_always_a_legal_action(self):
        c = client()
        start(c)
        battle = battle_app.CURRENT["battle"]
        battle.player_stamina = 0.0
        state = c.get("/api/battle/state").json()
        usable = {s["id"] for s in state["skills"] if s["usable"]}
        self.assertIn("second_wind", usable)
        res = c.post("/api/battle/round", json={"response": "second_wind"})
        self.assertEqual(res.status_code, 200)
        self.assertGreater(res.json()["event"]["player"]["stamina_restored"], 0)

    def test_invalid_and_blocked_responses_return_400(self):
        c = client()
        start(c)
        self.assertEqual(c.post("/api/battle/round", json={"response": "not_a_skill"}).status_code, 400)
        c.post("/api/battle/round", json={"response": "breaker_lunge"})
        res = c.post("/api/battle/round", json={"response": "breaker_lunge"})  # on cooldown
        self.assertEqual(res.status_code, 400)
        self.assertIn("cooldown", res.json()["detail"])

    def test_finished_battle_returns_409(self):
        c = client()
        start(c, player_level=5, enemy_level=1, auto=True)
        for _ in range(50):
            res = c.post("/api/battle/round", json={"response": None})
            if res.json()["state"]["finished"]:
                break
        self.assertEqual(c.post("/api/battle/round", json={"response": None}).status_code, 409)
        self.assertEqual(c.get("/api/battle/state").json()["outcome"], "victory")

    def test_auto_toggle(self):
        c = client()
        start(c)
        state = c.post("/api/battle/auto", json={"enabled": True}).json()
        self.assertTrue(state["auto"])
        state = c.post("/api/battle/auto", json={"enabled": False}).json()
        self.assertFalse(state["auto"])

    def test_unknown_archetype_rejected(self):
        c = client()
        res = c.post("/api/battle/start", json={"archetype": "dragon"})
        self.assertEqual(res.status_code, 400)


class BattleScreenMarkupTests(unittest.TestCase):
    """The page must ship the required affordances; the JS builds skill
    buttons from the skills payload at runtime."""

    def setUp(self):
        c = client()
        self.html = c.get("/").text
        self.js = c.get("/static/app.js").text
        self.css = c.get("/static/style.css").text

    def test_page_serves_and_declares_core_regions(self):
        for element_id in ("skill-list", "log-list", "battle-log-panel", "skills-panel",
                          "player-figure", "enemy-figure", "player-floaters", "enemy-floaters",
                          "telegraph", "confirm-cancel", "hold-button", "auto-toggle",
                          "player-zone", "enemy-zone", "center-zone"):
            self.assertIn(f'id="{element_id}"', self.html, element_id)

    def test_skill_info_lives_in_a_modal_not_inline(self):
        # A single centered modal with a dimmed backdrop, an explicit
        # close control, and click-outside-to-close.
        for element_id in ("skill-modal", "skill-modal-card", "skill-modal-close",
                          "skill-modal-title", "skill-modal-body"):
            self.assertIn(f'id="{element_id}"', self.html, element_id)
        for marker in ("openSkillModal", "closeSkillModal"):
            self.assertIn(marker, self.js, marker)
        self.assertIn('ev.target === $("skill-modal")', self.js)  # backdrop click closes
        # The old inline description block below each button is gone.
        self.assertNotIn("rune-details", self.js)
        self.assertNotIn("skill-details", self.js)

    def test_figurines_are_monochrome_svg_silhouettes(self):
        self.assertIn('<svg id="player-figure"', self.html)
        self.assertIn('<svg id="enemy-figure"', self.html)
        self.assertIn("fill: #ffffff", self.css)

    def test_no_dropdowns_for_skills(self):
        # The only <select> allowed is the pre-battle enemy archetype picker.
        self.assertEqual(self.html.count("<select"), 1)
        self.assertIn('id="setup-archetype"', self.html)

    def test_js_builds_skill_buttons_with_info_and_cancel_affordances(self):
        for marker in ("skill-button", "skill-info-toggle", "skill-dmg", "skill-cd",
                       "skill-status", "dataset.icon", "cancelSelection",
                       "spawnFloater", "appendLogEntry"):
            self.assertIn(marker, self.js, marker)

    def test_battle_ui_no_longer_speaks_of_runes(self):
        # "Runeted" (the title) is fine; the standalone word "rune" is not.
        for name, text in (("index.html", self.html), ("app.js", self.js)):
            self.assertIsNone(re.search(r"\brunes?\b", text, re.IGNORECASE),
                              f"battle-screen concept rename incomplete in {name}")


class SkillDescriptionTests(unittest.TestCase):
    def test_descriptions_are_complete_for_every_default_skill(self):
        for skill in default_loadout().skills.values():
            text = describe_skill(skill)
            self.assertIn("stamina", text["short"])
            self.assertIn("cooldown", text["short"])
            for counter in skill.counters:
                self.assertIn(counter, text["full"])
            self.assertIn(skill.name, text["full"])


if __name__ == "__main__":
    unittest.main()
