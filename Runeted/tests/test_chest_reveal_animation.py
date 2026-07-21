"""Regression test for the chest-unboxing animation in the legacy
frontend (backend/frontend/app.js + style.css), wired to the existing
"Open 1 Chest" / "Open 10" flow (main.py's /runes/open_chest).

Reads the static files directly rather than booting main.py's FastAPI
app in-process: main.py carries heavy AI-client imports and no other
test in this suite spins it up as a TestClient.
"""
import os
import unittest

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
APP_JS_PATH = os.path.join(BACKEND_DIR, "frontend", "app.js")
STYLE_CSS_PATH = os.path.join(BACKEND_DIR, "frontend", "style.css")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class ChestRevealAnimationTests(unittest.TestCase):
    def setUp(self):
        self.js = _read(APP_JS_PATH)
        self.css = _read(STYLE_CSS_PATH)

    def test_reveal_function_exists(self):
        self.assertIn("function showChestRevealAnimation(runes)", self.js)

    def test_reveal_is_wired_into_the_open_chest_button_handler(self):
        handler = self.js.split("data-runes-open")[-1]
        self.assertIn("showChestRevealAnimation(res?.runes)", handler)

    def test_rare_and_above_are_celebratory_but_common_is_not(self):
        set_line = next(
            line for line in self.js.splitlines()
            if "CHEST_REVEAL_CELEBRATORY_RARITIES" in line and "new Set" in line
        )
        for rarity in ("rare", "epic", "legendary", "mythic", "supreme", "relic"):
            self.assertIn(f'"{rarity}"', set_line, rarity)
        self.assertNotIn('"common"', set_line)

    def test_css_defines_a_plain_pop_and_a_bigger_celebratory_burst(self):
        for marker in (
            ".chest-reveal-overlay", ".chest-reveal-card", ".chest-reveal-card.celebratory",
            "@keyframes chestRevealPop", "@keyframes chestRevealBurst",
        ):
            self.assertIn(marker, self.css, marker)
        # Every declared rarity gets its own accent color/glow, matching
        # the palette already used for rune-card borders elsewhere.
        for rarity in ("rare", "epic", "legendary", "mythic", "supreme", "relic"):
            self.assertIn(f".chest-reveal-card.{rarity}", self.css, rarity)

    def test_animation_timing_stays_fast_for_opening_several_chests_at_once(self):
        # Opening 10 must not force a long wait: a short per-card stagger
        # plus a short pop, not a slow sequential reveal.
        self.assertIn("CHEST_REVEAL_STAGGER_MS = 70", self.js)
        self.assertIn("CHEST_REVEAL_POP_MS = 480", self.js)
        ten_chest_wait_ms = 480 + 10 * 70
        self.assertLess(ten_chest_wait_ms, 1500)

    def test_reveal_does_nothing_for_an_empty_or_missing_rune_list(self):
        body = self.js.split("function showChestRevealAnimation(runes) {")[1].split("\nfunction ")[0]
        self.assertIn("if (!items.length) return;", body)


if __name__ == "__main__":
    unittest.main()
