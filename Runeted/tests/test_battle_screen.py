"""Battle screen smoke tests: the API the screen consumes, and the
static page's required affordances (skill buttons, info modal, cancel,
figurines, floaters, battle log, two-column layout)."""
import re
import unittest

from fastapi.testclient import TestClient

import battle_app
from _account_test_helpers import authed_client, bundle_for
from core.intent import build_intent
from core.skills import default_loadout, describe_skill


def client() -> TestClient:
    # A brand-new, never-before-used account per call -- nothing stale
    # to reset, unlike the single shared global this used to reach into.
    return authed_client()


def start(c: TestClient, **overrides):
    payload = {"archetype": "brute", "seed": 2}
    payload.update(overrides)
    res = c.post("/api/battle/start", json=payload)
    assert res.status_code == 200, res.text
    return res.json()


def force_intent(c: TestClient, kind, archetype="brute"):
    """Force the active battle's current (about-to-resolve) enemy move
    for a deterministic test setup. Move selection is live cooldown/
    stamina-gated random choice each round, so a seed alone no longer
    guarantees a specific opening move -- see test_core_combat.py."""
    bundle_for(c)["battle"].tracker.current = build_intent(kind, archetype)


class BattleApiSmokeTests(unittest.TestCase):
    def test_start_returns_full_screen_state(self):
        c = client()
        state = start(c)
        self.assertEqual(state["outcome"], "in_progress")
        # The enemy's specific next move is never revealed in advance.
        self.assertNotIn("telegraph", state)
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

    def test_enemy_moves_lists_the_full_pool_with_live_cooldowns(self):
        c = client()
        state = start(c, archetype="brute")
        # brute's deck is heavy/basic/heavy/multi -- the movelist is the
        # deduplicated pool, not the raw cyclic deck order.
        kinds = [m["kind"] for m in state["enemy"]["moves"]]
        self.assertEqual(kinds, ["heavy", "basic", "multi"])
        for move in state["enemy"]["moves"]:
            self.assertIn("name", move)
            self.assertIn("description", move)
            self.assertIn("cooldown", move)
            self.assertIn("remaining_cooldown", move)
            # Nothing has been used yet -- no move starts on cooldown.
            self.assertEqual(move["remaining_cooldown"], 0)

    def test_a_move_shows_as_cooling_down_after_it_resolves(self):
        c = client()
        start(c, archetype="brute")
        force_intent(c, "heavy", "brute")
        res = c.post("/api/battle/round", json={"response": None})
        state = res.json()["state"]
        heavy = next(m for m in state["enemy"]["moves"] if m["kind"] == "heavy")
        self.assertGreater(heavy["remaining_cooldown"], 0)

    def test_round_returns_structured_event_and_updated_state(self):
        c = client()
        start(c)
        force_intent(c, "heavy")  # breaker_lunge counters heavy
        res = c.post("/api/battle/round", json={"response": "breaker_lunge"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        event, state = body["event"], body["state"]
        self.assertEqual(event["round"], 1)
        self.assertTrue(event["player"]["matched"])
        self.assertIn("hp", event["player"])
        self.assertIn("delta", event["enemy"]["hp"])
        self.assertLess(state["enemy"]["hp"], state["enemy"]["max_hp"])
        breaker = next(s for s in state["skills"] if s["id"] == "breaker_lunge")
        self.assertGreater(breaker["remaining_cooldown"], 0)
        self.assertFalse(breaker["usable"])

    def test_recovery_is_always_a_legal_action(self):
        c = client()
        start(c)
        battle = bundle_for(c)["battle"]
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
        bundle_for(c)["player"].level = 5  # real progression, not a request field
        # auto stays off here: with it on, a win would trigger
        # auto-battle's own bank-or-continue decision (see
        # test_push_your_luck.py) and hand back a fresh in-progress
        # battle instead of the finished one this test wants to probe.
        # The auto-battle policy's own counter choice still reliably
        # wins without the flag, computed directly each round.
        start(c, enemy_level=1)
        for _ in range(50):
            response = bundle_for(c)["battle"].choose_auto_response()
            res = c.post("/api/battle/round", json={"response": response})
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
        self.html = c.get("/battle").text
        self.js = c.get("/static/app.js").text
        self.css = c.get("/static/style.css").text

    def test_page_serves_and_declares_core_regions(self):
        for element_id in ("skill-list", "log-list", "battle-log-panel", "skills-panel",
                          "player-figure", "enemy-figure", "player-floaters", "enemy-floaters",
                          "enemy-movelist-panel", "confirm-cancel", "auto-toggle",
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
        # No manual archetype picker either — the admin testing bar is gone.
        self.assertEqual(self.html.count("<select"), 0)

    def test_admin_testing_bar_is_gone(self):
        # The manual level/enemy-type/new-battle controls never reflected
        # real game state and must not ship. Battles start from the hub.
        for element_id in ("setup-bar", "setup-player-level", "setup-enemy-level",
                          "setup-archetype", "new-battle"):
            self.assertNotIn(f'id="{element_id}"', self.html, element_id)
        self.assertNotIn("setup-player-level", self.js)
        self.assertIn('href="/"', self.html)  # a way back to the hub remains

    def test_js_builds_skill_buttons_with_info_and_cancel_affordances(self):
        for marker in ("skill-button", "skill-info-toggle", "skill-dmg", "skill-cd",
                       "skill-status", "dataset.icon", "cancelSelection",
                       "spawnFloater", "appendLogEntry"):
            self.assertIn(marker, self.js, marker)

    def test_skill_ui_never_speaks_of_runes(self):
        # The old mislabel called skills "equipped runes". Passive runes
        # now legitimately have their own panel, so the rename guard is
        # scoped to the skill UI: the skills panel keeps its name and the
        # skill-button builder never mentions runes, and no hybrid
        # skill/rune identifier exists anywhere.
        self.assertIn("<h2>Skills</h2>", self.html)
        skills_fn = self.js.split("function renderSkills")[1].split("function renderRunes")[0]
        self.assertIsNone(re.search(r"\brunes?\b", skills_fn, re.IGNORECASE),
                          "skill-button builder mentions runes")
        self.assertIsNone(re.search(r"skill[-_]?rune|rune[-_]?skill", self.html + self.js, re.IGNORECASE))
        # The passive-rune UI is its own separate panel + shared modal.
        self.assertIn('id="rune-row"', self.html)
        self.assertIn("openRuneModal", self.js)

    def test_enemy_movelist_panel_replaces_the_telegraph_card(self):
        # The old single-upcoming-move telegraph card is gone entirely.
        self.assertNotIn('id="telegraph"', self.html)
        self.assertNotIn("telegraph", self.html.lower())
        self.assertIn('id="enemy-movelist-panel"', self.html)
        self.assertIn('id="enemy-movelist"', self.html)
        self.assertIn("renderEnemyMoves", self.js)

    def test_enemy_movelist_shows_cooldown_badges_matching_skill_style(self):
        # Same visual language as the player's own skill-cooldown chips:
        # a fixed ⏳ stat plus a "CD N" chip while a move is cooling,
        # and the row itself darkens (mirrors disabled skill buttons).
        self.assertIn("enemy-move-cd", self.js)
        self.assertIn("enemy-move-cooling", self.js)
        self.assertIn("on-cooldown", self.js)
        self.assertIn(".enemy-move-cooling", self.css)
        self.assertIn(".enemy-move-row.on-cooldown", self.css)

    def test_enemy_movelist_cooldown_row_gets_gold_outline_on_top_of_darkening(self):
        # The darkening alone (opacity fade) stays; a gold outline is
        # layered on top so a cooling-down move reads at a glance, using
        # the same gold accent (#af8b4c) as the rest of the UI's
        # confirm/primary actions.
        rule = self.css.split(".enemy-move-row.on-cooldown {")[1].split("}")[0]
        self.assertIn("opacity: 0.45", rule)
        self.assertIn("outline", rule)
        self.assertIn("#af8b4c", rule)

    def test_hover_popup_replaces_native_title_tooltips_on_skills_and_runes(self):
        # The skill button and rune chip no longer set a native `title`
        # attribute for their description -- that's now a custom popup
        # that follows the cursor and hides on mouseleave.
        self.assertIn('id="hover-tooltip"', self.html)
        for marker in ("wireHoverPopup", "positionHoverTooltip", "hideHoverTooltip"):
            self.assertIn(marker, self.js, marker)
        self.assertIn("wireHoverPopup(button, skill.description)", self.js)
        self.assertIn("wireHoverPopup(chip, rune.short)", self.js)
        self.assertNotIn("button.title = skill.description", self.js)
        self.assertNotIn("chip.title = rune.short", self.js)

    def test_hover_popup_is_hidden_when_the_info_modal_opens(self):
        # The popup and the click-to-open modal are separate affordances;
        # opening the modal shouldn't leave a stale popup on screen.
        open_skill_modal = self.js.split("function openSkillModal")[1].split("\nfunction ")[0]
        open_rune_modal = self.js.split("function openRuneModal")[1].split("\nfunction ")[0]
        self.assertIn("hideHoverTooltip()", open_skill_modal)
        self.assertIn("hideHoverTooltip()", open_rune_modal)

    def test_defeat_panel_ships_with_a_clear_return_to_hub_button(self):
        self.assertIn('id="defeat-panel"', self.html)
        self.assertIn('id="defeat-return-button"', self.html)
        self.assertIn("Return to hub", self.html)
        # Same navigation bankPending() uses after a win.
        handler = self.js.split('$("defeat-return-button").addEventListener')[-1]
        self.assertIn('window.location.href = "/"', handler)

    def test_defeat_panel_only_shows_on_a_finished_defeat(self):
        render_fn = self.js.split("function render()")[1].split("\nfunction ")[0]
        self.assertIn(
            '$("defeat-panel").className = state.finished && state.outcome === "defeat" ? "" : "hidden"',
            render_fn,
        )

    def test_auto_battle_icon_has_no_background_shape(self):
        self.assertIn("#auto-toggle { background: transparent; }", self.css)

    def test_pass_button_removed_entirely(self):
        # The 0-cost recovery skill already guarantees a legal action
        # every round, so the standalone "Pass (no skill)" button was
        # removed rather than kept as a redundant affordance.
        self.assertNotIn("Play next round", self.js)
        self.assertNotIn("Pass (no skill)", self.html)
        self.assertNotIn('id="hold-button"', self.html)
        self.assertNotIn("hold-button", self.js)

    def test_auto_battle_advances_rounds_without_a_manual_trigger(self):
        for marker in ("maybeScheduleAutoRound", "stopAutoLoop", "autoTimer"):
            self.assertIn(marker, self.js, marker)


class HomeHubTests(unittest.TestCase):
    """The persistent navigation hub outside of battle: real player
    state, and one entry point per major system."""

    def test_hub_serves_at_root_with_nav_tiles_for_every_system(self):
        c = client()
        html = c.get("/").text
        js = c.get("/static/home.js").text
        for element_id in ("home-screen", "home-nav", "nav-battle",
                          "home-player-name", "home-player-level"):
            self.assertIn(f'id="{element_id}"', html, element_id)
        for href in ("/skills", "/runes", "/equipment", "/inventory", "/market", "/exchange"):
            self.assertIn(f'href="{href}"', html, href)
        self.assertIn("/api/battle/start", js)  # Start Battle triggers a real flow

    def test_player_api_reflects_real_persistent_state_not_a_debug_value(self):
        c = client()
        bundle_for(c)["player"].level = 7
        body = c.get("/api/player").json()
        self.assertEqual(body["level"], 7)
        # Starting a battle with no client-supplied level still uses it.
        state = start(c, enemy_level=None)
        self.assertEqual(state["player"]["level"], 7)

    def test_battle_start_ignores_a_client_supplied_player_level(self):
        # The old admin bar posted player_level directly; the field no
        # longer exists on the contract, so a caller can't spoof it.
        # seed=2 pins this to a "combat" roll under core/events.py's
        # encounter gate (random.Random(2).random() == 0.956) -- this
        # test is about the player-level contract, not events.
        c = client()
        bundle_for(c)["player"].level = 3
        res = c.post("/api/battle/start", json={"player_level": 99, "archetype": "brute", "seed": 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["player"]["level"], 3)

    def test_battle_start_with_no_body_derives_everything(self):
        # The hub's Start Battle action posts an empty object -- pin the
        # encounter roll to "combat" with a known-safe seed so this test
        # (about deriving level/archetype, not about events) isn't flaky.
        c = client()
        res = c.post("/api/battle/start", json={"seed": 2})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["outcome"], "in_progress")

    def test_unbuilt_nav_targets_serve_a_placeholder_not_a_dead_link(self):
        c = client()
        for slug, title in (("skills", "Skills"), ("runes", "Runes"),
                            ("equipment", "Equipment"), ("inventory", "Inventory"),
                            ("market", "Market"), ("exchange", "Currency Exchange")):
            res = c.get(f"/{slug}")
            self.assertEqual(res.status_code, 200, slug)
            self.assertIn(title, res.text)
            self.assertIn('href="/"', res.text)  # always a way back to the hub

    def test_unknown_slug_is_a_real_404(self):
        c = client()
        self.assertEqual(c.get("/not-a-real-page").status_code, 404)

    def test_battle_page_falls_back_to_a_real_start_with_no_active_battle(self):
        # The hub's Start Battle action is the primary flow (POST then
        # navigate), but a direct/bookmarked visit to /battle with no
        # active battle must still work: boot() catches the 404 from
        # /api/battle/state and starts one itself, no manual params.
        c = client()
        js = c.get("/static/app.js").text
        boot_fn = js.split("(async function boot()")[1]
        self.assertIn("newBattle()", boot_fn)
        self.assertEqual(c.get("/api/battle/state").status_code, 404)
        res = c.post("/api/battle/start", json={})
        self.assertEqual(res.status_code, 200)


class SkillDescriptionTests(unittest.TestCase):
    """Descriptions are meant to be plain-language: a player should
    understand what the button does from the text alone, without
    needing to translate game jargon. The modal's meta line already
    shows kind/cost/cooldown/counters as separate structured fields, so
    `full` shouldn't repeat those as prose."""

    def test_descriptions_are_complete_for_every_default_skill(self):
        for skill in default_loadout().skills.values():
            text = describe_skill(skill)
            self.assertTrue(text["short"])
            self.assertIn(skill.name, text["full"])
            for counter in skill.counters:
                self.assertIn(counter, text["full"])

    def test_full_text_does_not_repeat_the_meta_lines_cost_and_cooldown(self):
        # Those numbers already appear in skill-modal-meta; repeating
        # them as prose in the body is exactly the clutter being removed.
        for skill in default_loadout().skills.values():
            text = describe_skill(skill)
            self.assertNotIn("cooldown", text["full"].lower())
            self.assertNotIn("cools down", text["full"].lower())

    def test_short_text_avoids_jargon_terms(self):
        # "telegraph" and "effect_mult"-style wording are internal game
        # vocabulary; a player reading the button tooltip shouldn't need
        # to know them.
        for skill in default_loadout().skills.values():
            text = describe_skill(skill)
            self.assertNotIn("telegraph", text["short"].lower())


if __name__ == "__main__":
    unittest.main()
