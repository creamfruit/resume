# RPG Game Architecture Inventory

This document has two parts. **Part A** describes the Runeted rebuild — the new game core being built in phases under `backend/core/` (the plan started at 5 phases and has grown as playtesting surfaced more work; see the phase list below for the current count). **Part B** (sections 1–8 below) is the legacy reference inventory of the old codebase, kept in place as the authority on what systems must exist; old files are replaced phase by phase.

## Part A — Runeted rebuild

### Phase 1: core combat loop and player state (`backend/core/`)

- `core/intent.py` — **the single system that generates and tracks enemy moves.** The enemy's move for the round is decided by the engine and resolved immediately — it is **not** announced to the player ahead of time. This replaces the original "telegraph" design (name + effect shown a full round before it resolved), which was removed because it made combat a solved puzzle: once the exact next move is known in advance, there is always one exact correct counter, and every fight degenerates into looking up that counter rather than weighing risk. `IntentTracker` owns the archetype's distinct move pool and per-move cooldowns for a battle; no other module may create or mutate intents, and nothing is ever written onto the enemy object (the old split between `boss_ai.py` and `session.py` is deliberately not recreated). Move selection is cooldown- and stamina-gated random choice each round (`IntentTracker._roll`): a move just used goes on cooldown (1–3 rounds, mirroring the player skill-cooldown range) and can't come up again until it clears; if every pool move is on cooldown or unaffordable, the enemy falls back to the cheapest move in the whole library as a legal-action guarantee (reported as `downgraded_from`: `"cooldown"` or `"stamina"`). `IntentTracker.movelist()` is what the player actually sees — the full move pool with live cooldown state, so play is reasoning about what the enemy *could* do (what's off cooldown) rather than reading off what it *will* do. Each intent still has a `contact_mult` (graze that always lands) and an `effect_mult` (the move's full effect, fully negated by a correct counter). An intent is countered when the responding skill's `counters` tags intersect the intent's `countered_by` set (enemy archetype + intent kind).
- `core/skills.py` — **the Skill system: the player's active, per-turn combat choice.** (This concept was originally mislabelled "equipped runes" in battle; it was renamed to skills after playtesting — same mechanics, new name. The *passive* Rune system is the separate Phase 4 concern below — its own module, `core/runes.py`, not the legacy `models/rune.py` / `services/rune_system.py`, which core no longer imports.) A `Skill` has a value, a value-scaled cooldown (1–3 rounds) and stamina cost (`max(1, value)`, overridable — recovery costs 0), `counters` tags, a coarse `method` tag (offense/defense/utility/drawback/amplifier), and a mechanical `kind`: **attack** (strike + counter attempt), **defend** (blocks the enemy move's effect, deals no damage), **dodge** (evades the whole move, deals no damage), **buff** (spends stamina for a temporary attack bonus), **recovery** (costs 0 stamina and restores stamina, so an empty bar never leaves the player without a legal action). `SkillLoadout` is the only place loadouts are built and enforces both caps at construction: at most 6 slots **and** total skill value within the value budget (10, plus any equipped `budget_modifier`s). The default loadout (total value 9/10) is two kind-countering attacks — Breaker Lunge (heavy, guard_break) and Flurry Break (multi), which together cover every dangerous move kind in every archetype pool — plus Bulwark (defend), Sidestep (dodge), War Chant (buff, +50% attack for 2 rounds), and Second Wind (recovery, +3 stamina).
- `core/stats.py` — the derived-stats pipeline. Combat reads `DerivedStats` exclusively; raw player/enemy fields never appear in damage math. Later phases plug in via `StatContribution` (equipment in phase 2; Phase 4's runes resolve through the passive engine directly rather than this pipeline — see below). Both sides share one per-level growth base (`GROWTH_PER_LEVEL`), so equal-level fights play identically at every level; `baseline_enemy()` is the canonical enemy statline per level, which phase 3 encounter generation must build on rather than invent a second curve.
- `core/battle.py` — the round loop: the enemy has already picked its move for the round (server-authoritative, not shown to the player) → player response (skill or hold) → the response resolves by kind (holding or an attack skill strikes; a matched counter negates the effect and leaves the enemy *exposed* — consumed by the next strike, so it carries over non-strike rounds; defend blocks the effect without striking; dodge routes through the game's single dodge roll at certainty; buff applies a duration-limited attack bonus; recovery restores stamina) → enemy's move resolves → cooldowns tick, buffs count down → the enemy's next move is picked (still not shown; only revealed after the fact, in the round event, once it has already resolved). Includes the auto-battle toggle: the policy counters dangerous moves (`effect_mult >= 1.0`) with the cheapest matching off-cooldown attack, falls back to the cheapest affordable defend/dodge mitigation, and holds otherwise; it never spends turns on buffs or recovery — this reads the enemy's live move directly as authoritative server state, unaffected by what is or isn't shown to a human player. Tuned so auto-battle reliably wins at or below the player's level and reliably loses above it (the balance matrix holds unchanged under the movelist/cooldown rework below, because the two default attacks keep full counter coverage of every dangerous move kind regardless of selection order). Phase 1 combat is deterministic — crit/dodge exist in the pipeline but are not rolled yet.
- `core/resolution.py` — the single win/loss decision point (`Outcome`: in_progress / victory / defeat). The player acts first within a round, so simultaneous death cannot occur.
- `core/player_state.py` — lean `PlayerState`: identity (name) and progression (level, exp, stat points, attributes, current HP) only. Equipment, stash, runes, and economy live in their own modules; a regression test enforces that those fields never migrate onto the model. The XP/level/stat-point machinery here (`gain_exp`, `spend_stat`) was scaffolding until Phase 7 actually wired it to battle victories and an allocation screen — see below.
- `tests/test_core_combat.py` — phase 1 regression suite (no-foreknowledge contract, counter/negate/exposed rules, cooldown enforcement — both the player's skill cooldowns and the enemy's move cooldowns, including the cheapest-move emergency fallback — value-budget enforcement, the defend/dodge/buff/recovery move kinds, auto-battle win/loss matrix, derived-pipeline isolation, resolution, player-state leanness).

### Phase 2: combat hardening and the structured event stream

- **Dodge single-sourced.** `services/dodge.py` does not exist in this folder (it was already dropped when the old repo was ported) and nothing references it — verified by search. Dodge is now a real mechanic with exactly one calculation in the whole game: the chance comes from the derived-stats pipeline (`DerivedStats.dodge_chance` — dexterity plus `dodge_flat` contributions, capped) and is rolled in one place, the enemy-move resolution in `core/battle.py`. A dodged move deals zero damage. Default attributes give 0% dodge, so baseline combat stays deterministic. The old stack's client-supplied `dodge_success` flag (legacy `engine/combat.py`) is retired with the rest of the old combat path.
- **Damage-suppression and enemy-HP audit.** The two intermittent old-codebase bugs ("damage sometimes not dealt", "enemy HP sometimes increases") were hunted with a fuzz audit over the rebuilt loop — 1,530 battles / 8,011 rounds across auto, random-manual, and dodge-heavy play: zero occurrences of either. Neither bug is reachable in the new loop (uncountered, undodged moves floor at 1 damage; enemy HP is monotonically non-increasing).
- **Enemy-HP hard invariant.** `core/battle.py` enforces at runtime that enemy HP never rises — within a round or between turns — unless a *named* heal/regen/lifesteal event fired that round (plumbed via the round's `healing_events`; none exist yet). A violation logs which events fired (or that none did) via the `core.battle` logger and raises. Later phases must register healing effects there or the invariant trips.
- **Stamina.** Neither new model had a stamina field; both gained one (`PlayerState.stamina`, `BaselineEnemy.stamina`/`max_stamina` — None means full for the player, like HP). Ceilings and regen flow through the pipeline (`DerivedStats.max_stamina` / `stamina_regen`). Tunables live at the top of `core/stats.py` (player base 10 + 0.5/INT, regen 2; enemy 20, regen 2 — deliberately scale-free so pacing is identical at every level). Skill activations cost `max(1, skill.value)` stamina (`core/skills.py: stamina_cost_of`, overridable per skill — recovery skills declare 0); enemy move costs sit in `INTENT_LIBRARY` (basic 1, guard_break 2, heavy 3, multi 3). Actions without enough stamina are blocked: a player response is rejected with no state change; an enemy with no affordable off-cooldown move falls back to the cheapest move in the library instead, decided inside the intent system and reported as `downgraded_from` in the event (`"stamina"`, distinguished from a `"cooldown"` fallback — see Phase 1's `core/intent.py` entry above). Both sides regenerate a fixed amount at end of round; the auto-battle policy only picks affordable skills, and the 0-cost recovery skill guarantees a human player always has a legal action. Balance matrix re-verified after wiring: unchanged, zero violations.
- **Structured round events.** `core/events.py` defines the per-round contract (`RoundEvent`) the frontend renders from: for each side the move/intent used (with name and description), the response chosen and its `action` kind (strike/attack/defend/dodge/buff/recovery), damage dealt, HP delta (before/after/delta), stamina delta (spent/restored/regen/before/after/delta), statuses applied/removed (currently `exposed` on the enemy and `empowered` on the player), and outcome. `Battle.play_round` returns exactly this dict and appends it to `battle.rounds`. The event reports only the move that just resolved — it never carried a preview of the next one even before the telegraph-to-movelist rework below removed the concept entirely (see Home hub/battle screen section).
- `tests/test_combat_hardening.py` — phase 2 regression suite (dodge retirement + single-source, stamina costs/regen/blocking, enemy-HP invariant, event schema).

### Home hub, battle screen (playtest slice), and the skill rename

A thin, playtest-facing home hub and battle screen exist ahead of the full phase-5 frontend work:

- `backend/battle_app.py` — minimal FastAPI server for the home hub, battle screen, and their shared player state. Routes: `GET /` (home hub), `GET /battle` (battle screen), `GET /api/player` (persistent player identity/progression), `POST /api/battle/start` + `GET /api/battle/state` + `POST /api/battle/round` + `POST /api/battle/auto` (the battle loop), and `GET /{slug}` for the six not-yet-built sub-pages (see below). Deliberately thin: every rule lives in `backend/core`; responses are battle state plus the structured RoundEvent stream. State includes the `skills` payload (per skill: id, name, icon id, kind, base strike damage, stamina cost, cooldown, remaining cooldown, usability, counters, applied status + duration, short description, full modal text) and the loadout `budget` (cap and used value). Run from `backend/`: `..\.venv\Scripts\python.exe -m uvicorn battle_app:app --port 8010`. Legacy `main.py` still serves the old game.
- **Persistent player state, not a debug value.** `CURRENT["player"]` is one `PlayerState` object for the process lifetime — the same object `Battle` reads and writes, so level, HP, and stamina genuinely carry across battles rather than resetting from a request field. `POST /api/battle/start` takes no player-level field at all (there is nothing to override): it always builds the encounter from `_player().level`, heals the player to full first (every fresh engagement starts rested — there's no rest/recovery system yet to justify carrying damage between fights), and — unless a caller supplies `enemy_level`/`archetype`/`seed` for deterministic testing — picks the enemy level to match the player's and the archetype at random. Anywhere the UI shows a level, it is reading this object (`/api/player`, and the battle screen's `state.player.level` from the same source), never a value typed into a form.
- **Shared visual language.** Home, the battle screen, and the placeholder pages all load the one `style.css` and use its existing tokens rather than inventing a second look: near-black background (`#14161c`/`#1a1d26`/`#232838`), high-contrast light text (`#e8e8ec`), minimal decoration, and color spent only functionally (the gold `#af8b4c` accent already used for the confirm/primary action reused for the hub's Start Battle tile; everything else is neutral panels and borders). New pages should pull from these tokens instead of picking new ones.
- **Home hub** (`GET /`, `frontend_v2/home.html` + `home.js`) — the persistent navigation surface outside of battle: the player's real name/level (from `/api/player`) plus one tile per entry point — Start Battle, Skills, Runes, Equipment, Inventory, Market, Currency Exchange. Start Battle is the only tile wired to something built: it `POST`s `/api/battle/start` with an empty body (no manual parameters) and then navigates to `/battle`, so a battle is always started as a real request against real player state, not a page the UI merely links to. The other six are plain links to placeholder pages — this phase is shell and navigation only, and it's fine for a nav target to not be built yet as long as it leads somewhere real rather than a dead link.
- **Placeholder sub-pages** (`GET /{slug}`, `battle_app.PLACEHOLDER_PAGES`) — Skills, Runes, Equipment, Inventory, Market, and Currency Exchange all render one shared server-side HTML template (title swapped in) rather than six near-duplicate static files, each with a link back to the hub. An unrecognized slug is a real 404, not a silently-rendered placeholder. Each of these six gets its own route (shadowing this fallback) the phase it's actually built — Runes' real screen, for instance, is the equipped-rune row already living on the battle screen (see Phase 4), so `/runes` as a standalone management page is still open.
- **The admin-style testing bar is gone.** The battle screen used to open with manual level inputs, an enemy-archetype dropdown, and a "New battle" button — none of it reflected real game state, and it shipped only because there was no other way to start a fight. It has been removed entirely, not hidden or gated; there are zero `<select>` elements left in the battle screen. Starting a battle is now only reachable from the home hub's Start Battle action described above. Visiting `/battle` directly with no active battle still works as a fallback (the page's `boot()` catches the resulting 404 and starts one itself, with the same no-manual-parameters call) so a bookmark or reload never dead-ends, but the primary flow is the hub.
- `backend/frontend_v2/` — the battle screen (no build step; plain HTML/CSS/JS rendering server state only). Structure after the playtest refinement:
  - **Skill buttons** (`#skill-list`): one compact single-line button per skill — icon, name, a damage stat, a cooldown stat, and a status-effect icon + duration when the skill applies one (e.g. `⚔ Breaker Lunge | 💥 7 | ⏳ 2 | 🎯 1`). Each stat is prefixed with a fixed meaning-glyph so the bare numbers aren't ambiguous at a glance: `💥` for damage, `⏳` for cooldown (rounds). These are distinct from the per-skill type glyphs in `SKILL_ICONS` (app.js) and the status glyphs in `STATUS_ICONS` (e.g. `🎯` exposed, `⬆` empowered, `☠` poison) — any new stat added to the skill button line should follow the same pattern (one fixed glyph per stat meaning, reused across all skills) rather than reusing a type/status glyph. All five kinds render in this one flat list; there are no separate button categories and no dropdowns. Icon ids come from the server; the frontend maps them to placeholder glyphs.
  - **Info modal** (`#skill-modal`): each button has an `ⓘ` affordance that opens a centered modal over a dimmed backdrop with the skill's full description, including what it counters. Closed by the explicit ✕ control, a click on the backdrop, or Escape. Descriptions are never rendered inline under the buttons. The equipped-rune row (see Phase 4 below) reuses this exact modal shell rather than shipping a second dialog — `role="dialog"` appears exactly once in the page.
  - **Hover popup** (`#hover-tooltip`): hovering a skill button or rune chip shows its plain-language description in a small custom-styled popup that follows the cursor (`wireHoverPopup()` in app.js — `mouseenter` positions and shows it, `mousemove` tracks the cursor, `mouseleave` hides it) instead of the browser's default `title` tooltip. This is a separate, lighter affordance from the `ⓘ`/chip-click info modal above — the modal still owns full detail on demand, and opening it (`openSkillModal`/`openRuneModal`) explicitly hides any stale popup first. Both the hover popup and the modal draw on the same underlying text (`describe_skill`/`describe_rune`), which is deliberately player-facing prose only — neither ever surfaces the passive engine's internal trigger/effect vocabulary (`on_hit`, `damage_mult`, `Hooks: ...`), which used to leak into the rune modal body before this cleanup.
  - **Two-column combatant layout** (`#arena`): the formerly empty margins are now flanking columns — player (name/level, figurine, HP, stamina) on the left, enemy (name/level, figurine, HP, stamina, known-moves panel, equipped-rune row) on the right — with skills, actions, and the battle log in the center. Columns stack on narrow screens.
  - **Enemy movelist panel** (`#enemy-movelist-panel`, `#enemy-movelist`): the enemy's full move pool rendered as a list, replacing the old single-upcoming-move telegraph card entirely (there is no telegraph anywhere in `frontend_v2` any more — see the `core/intent.py` entry under Phase 1 above for why it was removed). Each row shows the move's name, description, and its own cooldown length (`⏳ N`, the same fixed-glyph stat convention the skill buttons use); a move currently on cooldown darkens the whole row (`.enemy-move-row.on-cooldown`, mirroring the opacity already used on disabled skill buttons) and gets a `CD N` chip (`.enemy-move-cooling`) styled identically to the player's own `.skill-cooling` chip — deliberately the same visual language on both sides of the arena. `renderEnemyMoves()` (app.js) rebuilds this list every render from `state.enemy.moves`, which is `Battle.movelist()` → `IntentTracker.movelist()`: the pool plus each move's live `remaining_cooldown`, never which one is about to resolve.
  - **Figurines**: plain monochrome placeholders — a white generic user silhouette for the player and a white devil-face silhouette (horns, no interior detail) for the enemy, both inline SVG.
  - **Action-bar icons.** `#main-actions` follows the same fixed-glyph convention as the skill stats: an icon precedes its label rather than standing alone, and the glyph's meaning never changes across states. Pass (`#hold-icon`, ⏭ — renamed from "Hold"; the mechanic is unchanged, just no longer implying a pause) swaps to ▶ only when auto-battle has taken over the button's role (label becomes "Play next round"). Auto-battle (`#auto-icon`, 🔄) gains a `.spinning` class — a CSS keyframe rotation — for exactly as long as `state.auto` is true, so the mode is visible at a glance without reading the label; toggling off removes the class and the spin stops immediately, no fade-out.
  - The header is now just a small `.site-home-link` back to the hub plus the outcome banner and notice strip — no admin controls (see above).
  - **Defeat panel.** A loss has no reward decision to make (any pending push-your-luck pool was already forfeited server-side — see Phase 6 below), so it doesn't reuse the push-luck panel. Instead `#defeat-panel` (hidden unless `state.finished && state.outcome === "defeat"`) renders below the outcome banner with a single, unmissable "Return to hub" button (`window.location.href = "/"`, the same navigation `bankPending()` uses after a win) — a loss never dead-ends on just the small header link.
- **The rune→skill rename.** What the battle screen previously labelled "equipped runes" is the Skill system (`core/skills.py`) — the active per-turn choice with a value budget, cooldowns, counters, and stamina costs. The rename covers backend, frontend, and tests. The regression guard is scoped to the skill UI (the `renderSkills` builder and the skills panel) rather than the whole page, since the battle screen now legitimately shows real passive runes alongside it (Phase 4).
- `tests/test_battle_screen.py` — battle-screen and hub suite (API payload shape incl. kinds/budget/recovery-legality, modal + layout + silhouette markup affordances, skill-UI rename regression, skill description completeness, admin-bar-is-gone regression, home hub nav/placeholder/404 coverage, persistent-player-level-not-a-request-field coverage).

### Phase 4: passive Rune system

The passive counterpart to Skills — equipped before battle, always active while equipped, never a per-turn choice. Lives in `core/runes.py`; battle-screen wiring is `battle_app.py` + `frontend_v2`.

- **Rune vs. Skill.** A Skill (`core/skills.py`) is the active choice committed each round, drawing on the skill value budget. A Rune is equipped before battle and drawn from its own, separate equip-cost budget (`RUNE_SLOT_CAP` = 3 slots, `RUNE_COST_BUDGET` = 6 cost) — enforced at construction, the only place `RuneEquipment` is built, exactly like `SkillLoadout`'s caps. The two budgets never interact; a rune's `cost` field and a skill's `value` field are unrelated numbers. A rune carries standard `PassiveModel` payloads and is resolved by the *existing* passive engine (`engine/passive_system.py`) — the same triggers, chance/threshold rules, and rarity-based `clamp_passives` limits items already use — so runes are a new equip slot for an old effect system, not a new mechanic. `core/battle.py` fires the triggers each round (`start_of_turn`, `below_hp` at round start; `on_hit` when the player's strike lands; `on_take_hit` when the player loses HP) and maps resolved effects onto battle state (damage_mult/dodge_mod/shield/lifesteal/thorns); every fired hook is reported in the round event's `rune_events`. The starter catalog (`RUNE_CATALOG`, 5 runes) covers one hook each: Emberheart (on-hit lifesteal), Thornmail Sigil (on-take-hit thorns), Zephyr Charm (start-of-turn dodge bonus), Wardstone (below-hp shield), Berserker Brand (below-hp damage boost). The default equipped set (`DEFAULT_EQUIPPED_IDS`) is Emberheart + Thornmail Sigil + Zephyr Charm — cost 5 of 6, 3 of 3 slots.
- **Battle-screen integration.** `battle_app.py` passes `runes=default_equipment()` into `Battle` and serves the equipped set as `state.runes` (`equipped` list with id/name/icon/type/rarity/cost/description/short/full_text, plus `slots`/`cost_cap`/`cost_used`). `frontend_v2` renders it as a chip row (`#rune-row`) in a new `#rune-panel` below the enemy's known-moves panel, inside the existing two-column combatant layout — no new page region, no new modal. Each chip's icon comes from its own glyph map (`RUNE_ICONS` in app.js), kept separate from `SKILL_ICONS` and `STATUS_ICONS` so the three icon families can never collide even where an id string might coincidentally match. Clicking a chip calls `openRuneModal`, which reuses the skill-info modal shell verbatim (same `#skill-modal` element, same close/backdrop/Escape handling) rather than building a second dialog — the modal is generic over "thing with a name, a meta line, and body text," and runes fit that contract exactly.
- `tests/test_passive_runes.py` — regression suite: equip-budget enforcement (slot cap and cost cap both raise at construction; the default set fits both), every catalog rune's passives surviving its rarity's `clamp_passives` cap, each starter rune's effect actually firing in a real battle round with the expected trigger/amount/consequence (lifesteal heal amount and HP accounting, thorns reflect amount and enemy-HP accounting, the dodge bonus tipping an otherwise-fixed RNG roll into a dodge — with a control case proving the same roll doesn't dodge without the rune, the below-hp shield both absorbing damage and staying dormant above its threshold, the below-hp damage boost raising the actual strike total against a same-seed control without it), the rune-less baseline firing nothing, and the battle-screen payload/markup contract (wallet-style rune payload shape, chip row + shared-modal markup, exactly one `role="dialog"` on the page).

### Phase 5 groundwork: multi-currency crafting economy

A Path-of-Exile-style economy: several distinct currencies, each with a specific crafting use, instead of one generic gold. Lives in `backend/services/currency.py` (catalog + wallet + crafting effects) and `backend/services/currency_exchange.py` (rates).

- **Currency model.** Every currency is an inventory-held quantity, not a stat: non-gold currencies are entries in `player.resources[currency_id]` — the same quantity map that holds crafting materials — accessed only through the wallet API (`currency_balance` / `add_currency` / `spend_currency` / `wallet`). The starter set (`CURRENCIES` catalog — id, display name, use):
  - `gold` — **"Gold", the base currency.** Confirmed as already serving the primary buy/sell role before this phase: `AuctionListing.price` is denominated in it and `auction_house.buy_item` spends `player.gold`. It therefore was **not** duplicated; it stays on the pre-existing `player.gold` field and the wallet API routes to it. It is the one exception to the resources-map rule, and it cannot itself be listed on the market (it is the medium).
  - `crafted_supplies` — **"Flux Sigil", the reroll currency.** Deliberately reuses the existing dismantle sink from `services/stash.py` (dismantled gear yields `crafted_supplies`) rather than adding a parallel material. Spending 1 rerolls one affix on a stash item (`reroll_item_affix` — a fresh affix from the shared pool in `engine/affixes.py`, extracted from loot generation so both draw from the same templates without loot's AI imports) or one effect on a rune (`reroll_rune_effect` — redrawn from `RUNE_EFFECT_POOL` at the rune's rarity). The old stash reroll function now delegates here (it previously replaced an affix with itself). Skills have no per-player instances or random affixes yet, so reroll/ascend target items and runes; skill support slots in when skills gain rollable affixes.
  - `ascension_sigil` — **"Ascension Sigil", the upgrade currency.** Spending 1 raises an item one tier on the item ladder (common → uncommon → rare → epic → legendary → mythic → supreme → relic) or a rune one tier via `RUNE_NEXT_RARITY` (also refreshing the rune's `max_upgrade` cap). Top tier cannot ascend; amplifier runes are excluded (their tier is recipe-fixed).
  - `warden_key` — **"Warden's Key", the chest-key currency.** Two modes: *upgrade* shifts a chest roll one rarity tier up (`chest_key_upgrade_tier`) and *guarantee* forces a specific content type instead of a random roll (`chest_key_guarantee`, validated against `CHEST_CONTENT_TYPES`). Both modes are wired into the legacy flat-chest endpoint (`/runes/open_chest`, `key_mode: "upgrade"`, one key per chest) but **not yet** into the new tiered `/chests/open` below — the chest phase built the tier/contents system first; porting key support onto it is the natural next step, not done here.
- **Currency trading.** Currencies circulate through both trade systems: `AuctionListing` gained a `"currency"` kind (`currency_id` + `amount`, priced in gold, gold-buyout only — item barter is disabled on currency listings so sales stay attributable) via `auction_house.list_currency`; trade-hub requests carry `offered_currencies` / `requested_currencies` quantity maps with full escrow/refund symmetry in the send/cancel/decline/accept/expire flow (mirroring the existing gold escrow).
- **Exchange rates — derived, never hardcoded** (`services/currency_exchange.py`). Each non-gold currency's gold rate comes from real completed activity: auction sales of currency listings (unit price = paid/amount, from `AUCTION_HISTORY`) plus accepted trade-hub requests that exchanged *exactly one currency against gold and nothing else* (mixed item/multi-currency trades can't be attributed to one currency and are excluded). The rolling rate is the mean unit price of the most recent `RATE_MAX_SAMPLES` (20) such trades inside `RATE_WINDOW_SEC` (24 h); with no completed trades the lowest active ask from open currency listings is quoted (`source: "listings"`); with neither the rate is unknown (`source: "none"`). Cross rates between two currencies derive through gold (`rate_between`). Queried via `GET /exchange/rates` (per-currency rate, sample count, lowest ask, source) — the frontend phase builds the actual exchange page on top of this; `GET /player/wallet` exposes holdings.
- `tests/test_currency_economy.py` — regression suite: catalog/wallet contract (inventory-held quantities, gold routed to the base field), each currency's crafting effect (reroll spend/replace + pool membership, ascension tier walk + caps, chest-key tier upgrade and content-type guarantee), currency auction flow (escrow, gold buyout, history rows, cancel refund), and the exchange-rate math (windowing, sample cap, listings fallback, trade-hub sample filtering, cross rates).

### Phase 5 groundwork: chest reward system

A tiered chest model, built on the legacy stack alongside the currency work above (`backend/services/chest.py`) — **not** the Phase 1-2 `core/battle.py` rebuild. "Battle victories" here means the legacy dungeon combat's single win hook, `main.py::_handle_enemy_defeat`; the new Runeted battle screen (`battle_app.py`) has no reward system yet (Phase 3, not started), so there was nothing there to wire into.

- **Chest model.** A chest's own rarity tier is separate from the rarity of whatever it contains — `player.chests: Dict[str, int]` holds a quantity per tier (its own field, alongside `resources` and `runes`, since a chest's only distinguishing property is its tier and the existing quantity-map pattern already fits that). Both tier decisions — the chest's own tier, and its contents' tier once opened — reuse `engine/loot.py`'s existing `roll_rarity` rather than a second probability system; nothing in `services/chest.py` invents its own rarity weights. The six tiers are exactly the ones `roll_rarity` can produce (`CHEST_RARITY_ORDER = common, rare, epic, legendary, mythic, relic`), which is what makes comparing a chest's tier against its contents' tier meaningful rather than arbitrary.
- **Contents floor/ceiling** (`chest_content_bounds`). A chest's contents are clamped to a window from one tier below to one tier above its own tier (clamped to the ladder's ends): common windows to `[common, rare]` and can never roll a legendary weapon; legendary windows to `[epic, mythic]` and can never roll pure junk; the floor is non-decreasing all the way up the ladder, so "higher-rarity chests roll a higher floor" is a hard guarantee, not a tendency. "Better average contents" on top of that hard floor comes from also biasing the underlying `roll_rarity` call's `risk` input upward with the chest's own tier before the clamp is applied — so a higher-tier chest's raw roll already leans toward the top of its window, not just gets clipped into it.
- **Rarity-consistent generation, not a re-stamp.** Once `open_chest` has clamped a content rarity, handing it to the item/rune generators has to keep the label consistent with what's actually generated (power, passives, effects) — stamping `.rarity` on an item *after* generation would leave a "legendary" item with common-tier stats if the internal roll landed low. Both existing generators already had (or gained) a way to accept a pre-decided rarity instead of rolling their own: `engine/loot.py::generate_loot(forced_rarity=...)` (new parameter, skips its internal `roll_rarity` call when set — added for this) and `services/rune_system.py::generate_build_rune(rarity_override=...)` (already existed, previously used only by the legacy key-upgrade chest flow). Both leave every existing caller's behavior unchanged when the new/existing parameter is omitted.
- **Contents pool.** `CONTENT_KIND_WEIGHTS = {item: 45, rune: 35, currency: 20}` — a flat, tier-independent weighted pick between the three kinds; the *rarity* of the pick is what scales with chest tier, not which kind gets picked. Skills are deliberately excluded: `core/skills.py` is a fixed catalog with no per-player unlock state, the same constraint `services/currency.py` already documented for reroll/ascend — "skill" slots into the weight table the day a skill-unlock system exists. A currency reward also draws from a weighted pool (`CHEST_CURRENCY_POOL`: gold, crafted_supplies, ascension_sigil) with `warden_key` deliberately excluded — it's the currency that opens/upgrades chests, not something a chest should hand back out.
- **Opening is one action** (`open_chest`): decrements the held tier by exactly one, rolls the clamped content rarity, picks a kind, and grants it immediately — no peek step, nothing left pending. `GET /player/chests` (holdings per tier) and `POST /chests/open` (`{"rarity": "..."}`) expose this.
- **Battle-victory wiring** (`award_battle_chest`, called from `_handle_enemy_defeat`). The defeated enemy's level, tier, and modifier count (`engine/enemy_factory.py`'s `colossal`/`volatile`/`runic`/`swift` stack from the encounter-generation phase) fold into one risk number (`_enemy_risk_score`) that biases the chest-tier roll — a tougher fight's chest leans higher, it's never hand-picked from enemy stats. A chest and a bonus currency amount are two independent rolls, so a victory can award a chest, currency, both, or neither — "instead of, or alongside" a chest, per the brief. This **replaces** the old flat, untiered `chest_chance` roll that fed the legacy `arcane_chest` resource from combat specifically; that resource and its other income sources (starter bonus, event rooms, quest rewards, the legacy `/runes/open_chest` endpoint) are untouched, they just no longer receive anything from battle wins. `victory_rewards` payloads carry the new `chest` (rarity string or `None`) and `chest_currency` (`{currency_id, amount}` or `None`) keys in place of the old `arcane_chest` count.
- `tests/test_chest_system.py` — regression suite: the floor/ceiling window math itself, the enemy-to-risk-score mapping and that it actually reaches the reused `roll_rarity` call, the core ask — opening every tier many times never produces contents outside that tier's declared bounds (a hard-clamp property test, not a probability-curve one, so it can't flake) — plus the task's literal examples (a common chest never yields legendary+, a legendary chest never yields common/rare), that a generated item/rune's rarity label always matches what's actually inside it, chest-inventory consumption and the empty-chest error path, the independent chest/currency award roll (all four combinations, deterministically forced via mocking), and a source-level check that the battle-victory hook is actually wired to this system instead of the old resource.

### Phase 6: push-your-luck reward flow

The new battle screen's first reward system. On every victory the player picks: bank the run's pending rewards and return to the hub, or push on into a harder encounter for a bigger pending reward. Lives in `core/gauntlet.py` (escalation curve + pending pool + bank/forfeit) and `core/wallet.py` (where a bank actually lands); wiring is `battle_app.py` + `frontend_v2`.

- **Pending, not immediate.** A win's reward is never granted directly — it accumulates in a `PendingPool` (`streak`, `chests`, `gold`, `resources`). Exiting (`bank`) commits the whole pool into the wallet via the same `grant_chest`/`add_currency` every other chest/currency award already uses; nothing here is a second grant path. Losing while continuing (`forfeit`) discards the pool untouched — the wallet is never even passed in, so there is no code path from a loss into a grant. Whatever was already banked from an earlier exit is unaffected either way: the wallet only ever grows through `bank`, never shrinks, and a loss can only cost the *current*, unbanked run.
- **No standing wallet on the new player model.** `core/player_state.py` stays identity + progression only by design (a regression test enforces it). `core/wallet.py::Wallet` (gold, resources, chests) is the sidecar this system banks into instead — shaped to satisfy `grant_chest`/`add_currency`'s duck typing without pulling in the legacy `models.player.Player` god-model's stash/equipment/rune-loadout fields, none of which the new system has built yet. `battle_app.CURRENT["wallet"]` holds it for the process lifetime, the same pattern as `CURRENT["player"]`; `GET /api/player/wallet` exposes it.
- **Escalating difficulty reuses the enemy-variety/modifier system, not a new one.** A fresh hub-started fight still uses `core/stats.py::baseline_enemy` (the plain per-level curve). A *continuation* fight instead calls `engine/enemy_factory.py::create_enemy(depth, risk)` — the pre-approved "enemy modifier stacking" building block (five archetypes, the colossal/volatile/runic/swift modifier pool, elite variants) — scaled by `core/gauntlet.py::escalation_for_streak(streak)`. That curve is linear (`risk == streak`, `depth = 1 + streak // 2`) through `SOFT_CAP_STREAK` (6 wins), then flattens sharply (`POST_CAP_RISK_STEP` = 0.35 risk and `POST_CAP_DEPTH_STEP` = 0.18 depth per extra win past the cap), and both are additionally hard-clamped (`MAX_RISK` = 30, `MAX_DEPTH` = 12) so a very long run can't grow unbounded even asymptotically. Only continuation encounters swap generators; the first fight of a session is unaffected.
- **Escalating reward reuses the chest/currency tables, not a new curve.** `services/chest.py::roll_guaranteed_reward(enemy)` rolls exactly one chest tier (`roll_chest_tier`, itself biased by the defeated enemy's risk score) and one currency amount (the shared currency pool) — unlike `award_battle_chest` (the legacy per-victory hook, two independent chance rolls that can both miss), a push-your-luck win always yields both; the escalating difficulty of staying in is the risk, and a guaranteed, growing reward is the pull to keep going. The escalation lives entirely in the *enemy*: a streak-scaled encounter carries a higher risk score, and that alone is what pushes the reward roll upward.
- **HP carries over while continuing — this is what makes "continue" a real risk.** `POST /api/battle/continue` deliberately does **not** heal: the next `Battle` is built directly off the persistent `PlayerState`, picking up whatever HP/stamina the just-finished fight left it with. Only ending the run — banking, or a defeat — and starting a fresh battle from the hub (`POST /api/battle/start`, still `heal_full()`) rests the player back to full. Earlier drafts of this system healed on every continue the same way a fresh start does; that made pushing your luck free of any cost beyond the escalating enemy, so it was changed to carry damage forward instead. `tests/test_battle_screen.py::test_continue_does_not_heal_the_player` and `test_a_fresh_hub_battle_still_heals_to_full` pin both halves of this contract down.
- **API.** `POST /api/battle/round` computes the reward and calls `pending.add_win(...)` the moment a round's outcome is `"victory"` (before returning), and calls `forfeit(pending)` the moment it's `"defeat"` with a non-empty pool; either way the response carries a `push_luck_result` (`{"result": "win", "reward", "pending"}` or `{"result": "forfeit", "lost"}`). `state.push_luck` (`pending`, `can_bank`, `can_continue`) is included in every battle-state payload, not just the round response, so a page reload at a decision point still shows it. `POST /api/battle/bank` and `POST /api/battle/continue` both 409 unless the active battle is finished with a victory and the pool is non-empty (`_require_victory_decision`); bank clears the battle (back to the hub), continue replaces it with the next escalated encounter. Starting a fresh battle (`POST /api/battle/start`) while a decision is unresolved forfeits the stale pool first — walking into a new fight without choosing is treated the same as walking away without banking.
- **Battle-screen integration.** `frontend_v2/index.html` gets a `#push-luck-panel` (hidden unless `state.push_luck.can_bank`) between the outcome banner and the arena, with a pending-rewards summary line and two buttons (bank / continue). `app.js::renderPushLuck()` builds the summary from `state.push_luck.pending`; `bankPending()` posts to `/api/battle/bank` and returns to the hub, `continuePushingLuck()` posts to `/api/battle/continue` and re-renders the harder encounter in place, and `describePushLuckResult()` surfaces the win/forfeit notice (reward or lost-pool amount) through the existing `notify()` banner after each round.
- `tests/test_push_your_luck.py` — regression suite: the escalation curve's soft-cap slope and absolute ceiling, `PendingPool` accumulation/reset, `bank` granting every pending entry to a wallet via the shared grant/add functions and being additive across multiple banked runs, `forfeit` never touching any wallet, and the end-to-end API flow (a win always offers the decision; bank/continue both 409 outside a finished victory; continuing escalates the next enemy and keeps the pool at risk; losing after continuing forfeits only that run while an earlier banked run survives untouched; starting a fresh battle over an unresolved decision forfeits it).

### Phase 7: leveling and stat allocation

`core/player_state.py` already carried the *scaffolding* for this from Phase 1 — `PlayerState.level/exp/exp_to_next/stat_points`, five attributes (strength, dexterity, intelligence, vitality, luck), `gain_exp()` (a `EXP_CURVE_MULT` = 1.5 XP-to-next-level curve, `LEVEL_UP_STAT_POINTS` = 5 granted flat per level), and `spend_stat()` — but none of it was reachable from a running game: nothing ever called `gain_exp()`, and no endpoint or page ever called `spend_stat()`. This phase is entirely about wiring that existing machinery up, plus one new attribute.

- **`charisma` — a sixth attribute, deliberately outside the derived-stats pipeline.** Added to `PlayerState` and `ATTRIBUTES` alongside the other five, so it's allocatable through the exact same `spend_stat()` path and stat-point economy. `core/stats.py::compute_player_stats` is **not** touched — it still reads only strength/vitality/luck/dexterity/intelligence, so charisma has zero effect on attack/defense/HP/crit/dodge/stamina today. It exists now because a later event system needs a stat to read; combat gets no special case for it, matching how equipment/runes already plug into combat only through `StatContribution` rather than the pipeline growing bespoke branches. `tests/test_leveling.py::test_charisma_is_allocatable_but_never_touches_derived_stats` pins this down by asserting `compute_player_stats` returns byte-identical `DerivedStats` before and after spending points into it.
- **Victory XP** (`core/player_state.py::victory_exp`). A battle win grants `BASE_VICTORY_EXP` (20) scaled by the defeated enemy's level through `core/stats.py::level_scale` — the same per-level growth curve combat stats already share, not a second curve invented for XP; a tougher win is worth proportionally more. Wired into `battle_app.py::play_round`'s existing `if event["outcome"] == "victory":` branch (the same branch that rolls the push-your-luck reward), so every victory — a fresh fight or a push-your-luck continuation — grants XP through the one call site. A defeat grants nothing, matching the existing reward flow.
- **Leveling up must never grant a free heal.** `PlayerState.gain_exp()`'s existing behavior sets `hp`/`stamina` back to `None` (the model's "full" sentinel) on every level-up — correct for that method used on its own, but a battle victory silently healing the player would undercut the entire point of Phase 6's continue-without-healing design (`core/wallet.py`/gauntlet section above): pushing your luck is supposed to carry real risk forward. `battle_app.py` snapshots `player.hp`/`player.stamina` immediately before calling `gain_exp()` and restores them if a level-up fired, so the battle's own end-of-fight HP/stamina always wins over `gain_exp()`'s heal-to-full side effect. `tests/test_leveling.py::test_leveling_up_on_a_battle_victory_does_not_grant_a_free_heal` forces a level-up mid-fight and asserts `player.hp` ends up a concrete post-fight number, never `None`.
- **API.** `POST /api/battle/round`'s response carries an `exp_result` (`{"exp_gained", "levels_gained", "leveled_up", "stat_points"}`) whenever the round's outcome is `"victory"` — parallel to the existing `push_luck_result`, same pattern, same call site. `GET /api/player` now also returns an `"attributes"` map (all six stats, charisma included) alongside the existing name/level/exp/exp_to_next/stat_points fields. `POST /api/player/spend_stat` (`{"stat", "amount": 1}`) validates the stat name and available points, calls `PlayerState.spend_stat`, and returns the same expanded player payload; a 400 on an unknown stat or insufficient points leaves `stat_points` and every attribute untouched.
- **Stats page** (`GET /stats`, `frontend_v2/stats.html` + `stats.js`) — a new, real page (not a `PLACEHOLDER_PAGES` entry), reachable from a new "Stats" tile on the home hub. Deliberately minimal per the brief: one row per attribute (current value, a one-line description of what it does, a "+" button that spends one point via `/api/player/spend_stat` and re-renders from the response), plus an XP line and a stat-points-remaining line. No new visual language — pulls the same `style.css` tokens (panel background/border, the gold `#af8b4c` accent on the "+" button, `.site-home-link` back to the hub) everything else already uses. Charisma's row reads "No combat effect yet." rather than pretending it does something today. This is intentionally a standalone panel rather than folded into the equipment page, since equipment doesn't exist yet (Phase 3); revisit the split once it does.
- `tests/test_leveling.py` — regression suite: the victory-XP curve (scales with enemy level, floors at 1), every allocatable combat attribute actually moving the corresponding `DerivedStats` field, charisma's allocatable-but-inert contract, the battle-victory-to-`gain_exp` wiring (awards on win, nothing on defeat, reports `exp_result`), the level-up-must-not-heal interaction above, the `/api/player`/`/api/player/spend_stat` contract (all six attributes present, spend applies and persists, rejects an unknown stat or an empty point balance without mutating state), and the stats-page markup (allocation UI present, every attribute referenced, a way back to the hub, the hub links to it).

Phase 4 (the passive Rune system), Phase 6 (push-your-luck rewards), and Phase 7 (leveling and stat allocation) are done, backend and UI both, per above. Phase 3 (items/equipment/loot), enemies/encounters, and the full frontend are otherwise not started; Phase 5 (runes/crafting/economy) has the currency and chest groundwork above but not the rest. Pre-approved building blocks copied from the old repo and treated as correct: rune module, item schema + validation, weapon innate abilities, dismantle system, market rarity floor, enemy modifier stacking.

## Part B — Legacy reference inventory (old codebase)

The sections below describe the old implementation. It is an inventory only; no gameplay logic was changed.

## 1) Combat system

### New telegraph-and-response combat loop
- `backend/engine/combat.py`
  - What it does: The combat core now reads an `enemy.intent` telegraph, evaluates the player’s chosen response against the telegraphed counter, and applies either a correct-answer bonus or a full effect. It also pulls derived combat stats from `player_stats.py` instead of relying on a single raw `attack` property.
  - Data model: Uses runtime objects with `hp`, `attack`, `defense`, `status`, `combat_mods`, and `intent`. The turn result is returned as a structured dict containing `intent`, `response`, and combat totals.
  - Assessment: This is now a more explicit telegraph/response loop and is much closer to the requested design. It still sits on top of the existing damage-plus-passives model rather than a fully separate combat grammar.

### Single source of truth for enemy intent
- `backend/engine/boss_ai.py`
  - What it does: Now owns both boss intent generation and regular enemy intent generation. It supplies a normalized `intent` dict with `name`, `description`, `type`, `counter`, and `effect` fields, so enemy telegraphs are created in one place.
  - Data model: Stores the intent on `enemy.intent` and optionally updates `enemy.combat_mods` for room pressure and intent cycling.
  - Assessment: Strong improvement over the previous split between `boss_ai.py` and `session.py`. The intent source is now centralized.

### Session orchestration
- `backend/services/session.py`
  - What it does: Tracks dungeon session state, pending enemy attack, room pressure, and room progression. It now seeds enemy intent from the centralized `boss_ai` helper rather than maintaining a separate deck in session code.
  - Data model: Uses the in-memory `SESSION` dictionary with room lists, current enemy, and turn flags.
  - Assessment: Cleaner and less duplicated; it now acts as state plumbing instead of inventing a second intent system.

### Boss behavior
- `backend/engine/boss_ai.py`
  - What it does: Computes boss phase from HP ratio and rolls boss intent (basic/heavy/multi) for the next enemy turn.
  - Data model: Reads and writes `enemy.phase`, `enemy.intent`, and `enemy.combat_mods["boss_run_state"]`.
  - Assessment: Solid, localized logic. It is a stronger combat AI component than the old `services/dodge.py` helper.

### Status effects
- `backend/engine/status_effects.py`
  - What it does: Stores and ticks status effects such as `burn`, `bleed`, `weak`, `vulnerable`, and `guard`.
  - Data model: `target.status` is a dict of status IDs to `{turns, potency}`.
  - Assessment: Good lightweight status framework; simple and reliable.

### Passive effect engine
- `backend/engine/passive_system.py`
  - What it does: Normalizes, clamps, collects, and resolves passive effects on equipment and combat triggers like `on_hit`, `on_take_hit`, `on_dodge`, `below_hp`, `start_of_turn`, and `end_of_turn`.
  - Data model: Uses `PassiveModel` / `PassiveEffect` Pydantic models and mutates `entity.combat_mods`. It now also consumes item-level `innate_abilities` alongside normal `passives`, allowing each unique weapon roll to bake in 1-3 fixed combat abilities without polluting the rune loadout.
  - Assessment: The most important “system glue” for item power. Solid and somewhat well-structured, though it depends on many stringly-typed effect IDs.

### Session / dungeon turn flow
- `backend/services/session.py`
  - What it does: Maintains the single-player in-memory dungeon session, room progression, enemy intent, room pressure, and UI-facing turn state.
  - Data model: Session dictionary containing room lists, `current_enemy`, `awaiting_enemy_attack`, and combat metadata.
  - Assessment: Solid for in-memory flow, but it is a big orchestration object rather than a domain service with strict boundaries.

### Old dodge helper
- `backend/services/dodge.py` — **not present in this folder**: the file was dropped during the port that produced this copy, and nothing references it. Kept in this inventory for history only. In the rebuild, dodge lives solely in the derived-stats pipeline + `core/battle.py` (see Part A, Phase 2).

### Empty or stub combat files
- `backend/engine/death.py`
  - What it does: Present but empty.
  - Data model: None.
  - Assessment: Placeholder / not yet implemented.
- `backend/engine/player_stats.py`
  - What it does: Present but empty.
  - Data model: None.
  - Assessment: Placeholder / not yet implemented.

## 2) Enemy / encounter model

### Enemy model
- `backend/models/enemy.py`
  - What it does: Defines the runtime enemy data model used by combat, room generation, and session state.
  - Data model: Pydantic `Enemy` with `name`, `level`, `hp`, `max_hp`, `attack`, `abilities`, `elite`, `tier`, `defense`, `crit_chance`, `status`, `combat_mods`, `intent`, and `archetype`.
  - Assessment: Solid domain model.

### Enemy factory
- `backend/engine/enemy_factory.py`
  - What it does: Generates enemies and bosses from AI design plus archetype stat scaling. Applies elite/boss modifications and stat variance, and can now roll a low-depth base enemy with a short stack of modifiers such as `colossal`, `volatile`, or `runic` so a shallow dungeon can still produce a high-level threat without a pre-authored template.
  - Data model: Produces `Enemy` objects from design data, archetype baselines, and a `modifiers` list that is carried on the runtime model.
  - Assessment: Solid generation logic, now more expressive for early-game threat scaling without introducing a second hand-built encounter template system.

### Ability registry
- `backend/engine/ability_registry.py`
  - What it does: A tiny registry for named enemy abilities that translate into simple stat boosts or damage-over-time effects.
  - Data model: Dictionary-based `ABILITY_EFFECTS` mapping names to bonus payloads.
  - Assessment: Very lightweight and likely placeholder-level rather than a full combat ability system.

## 3) Item, rarity, and passive data model

### Item model
- `backend/models/item.py`
  - What it does: Defines the item structure that goes into stash and equipment.
  - Data model: Pydantic `Item` with `name`, `rarity`, `power`, `passives`, `innate_abilities`, `slot`, and `source`.
  - Assessment: Simple and practical; solid base model. The new `innate_abilities` list is a weapon-specific contract that stays baked into that exact item roll and is separate from the universal rune loadout.

### Passive model
- `backend/models/passive.py`
  - What it does: Defines the schema for item passives and triggered effects.
  - Data model: `PassiveModel`, `PassiveEffect`, trigger literals, effect types, target, stat, and scaling.
  - Assessment: Solid schema; central to combat/item balance.

### Player model
- `backend/models/player.py`
  - What it does: Bulk runtime progression + equipment + inventory + resource + rune system model.
  - Data model: Pydantic `Player` with stats, equipment, stash, resources, runes, rune loadout, battle state, and dungeon progression fields.
  - Assessment: Strongly central model, but it has become a “god model” with many unrelated subsystems mixed together (combat, progress, idle, rune, battle skill trees, trade state, etc.).

### Derived combat stat computation
- `backend/engine/player_stats.py`
  - What it does: Computes the derived stats that combat actually reads: base attack/defense plus equipment, rune modifiers, dodge bonus, crit chance, and passive-derived utility such as shield/lifesteal/thorns.
  - Data model: Returns a dictionary of derived scalar combat values.
  - Assessment: This solves the missing “combat reads from derived stats” layer and makes combat outputs easier to reason about.

### Battle outcome resolution
- `backend/engine/death.py`
  - What it does: Resolves the controller-facing winner once either side has fallen below or equal to zero HP.
  - Data model: Returns a simple winner/reason payload.
  - Assessment: Lightweight and appropriate as a separate outcome layer; it acts as the combat end-state decision point.

## 4) Loot generation and rarity

### Loot generator
- `backend/engine/loot.py`
  - What it does: Creates random loot items with rarity roll, name generation, passive assignment, and optional AI-generated item fallback for top tiers.
  - Data model: Produces `Item` objects using `roll_rarity()`, `Item`, and `PassiveModel` output.
  - Assessment: Solid for a procedural drop system. The fallback path is safe and non-crashing, which is good.

### Rarity logic
- In `backend/engine/loot.py`
  - What it does: Uses a tiered probability curve (`common` → `rare` → `epic` → `legendary` → `mythic` → `relic`) to determine drop quality.
  - Data model: Rarity strings only; no schema enum.
  - Assessment: Practical and simple, but string-based rarity handling is easy to drift out of sync across modules.

### AI item design
- `backend/ai/item_designer.py`
  - What it does: Calls the LLM to generate high-tier item names, stats, and passives, with a clamp/fallback layer.
  - Data model: Input/output is `AIDesignedItem`, which is a Pydantic schema over `name`, `slot`, `rarity`, `damage`, `passives`, `flavor`.
  - Assessment: Good optional enhancement path, but it is an external dependency and fragile if the model output deviates.

### AI item schema
- `backend/ai/item_schema.py`
  - What it does: Defines the strict schema for AI item design and now enforces rarity-based damage bounds for `legendary`, `mythic`, and `relic` items.
  - Data model: Pydantic `AIDesignedItem` with `damage` now constrained by `RARITY_DAMAGE_BOUNDS` and a validator that rejects out-of-range values.
  - Assessment: The AI boundary is now much more trustworthy before content leaves generation.

### AI enemy generation
- `backend/ai/enemy_designer.py`
  - What it does: Creates enemy names/archetypes/abilities via LLM or fallback naming.
  - Data model: Input/output uses `AIEnemyDesign`.
  - Assessment: Good as an optional content-generation layer, but it remains an external-content dependency with fallback logic.

### AI enemy schema
- `backend/ai/enemy_schema.py`
  - What it does: Defines the schema for AI enemy design and now carries optional bounded fields for `level`, `hp`, `attack`, `defense`, and `crit_chance` to make the payload contract explicit.
  - Data model: Pydantic `AIEnemyDesign` with numeric constraints to prevent pathological stat growth from model drift.
  - Assessment: This is the missing “guardrail” layer that makes downstream combat code less dependent on unchecked AI outputs.

### Shared item validation helper
- `backend/utils/validators.py`
  - What it does: Centralizes a single server-side clamp/re-validate step for items entering stash, market, or trade flows.
  - Data model: Converts raw payloads into `Item` objects using item rarity bounds and passive normalization before the object is accepted.
  - Assessment: This is the enforcement gate that prevents badly-shaped AI items from crossing the runtime boundary.

### OpenAI / Gemini client bridge
- `backend/ai/openai_client.py`
  - What it does: Supplies a `genai.Client` singleton and checks for the environment key.
  - Data model: No domain entities, just API-client configuration.
  - Assessment: Thin and lightweight; safe placeholder for AI integration.

## 5) Runes and crafting systems

### Main API / orchestrator
- `backend/main.py`
  - What it does: The main application entrypoint that exposes the dungeon, combat, auction, and rune/crafting endpoints. It is the central integration point for almost everything in the repo.
  - Data model: Uses `Player`, `Enemy`, and raw request payload dictionaries; it also manipulates large nested response dictionaries.
  - Assessment: Strongly functional, but it is a large mixed orchestration file and likely the most fragile part of the architecture because it couples many systems into one place.

### Runes / rune recipes
- In `backend/main.py`
  - What it does: Defines `RUNE_RECIPES`, `RUNE_BUILD_RARITIES`, `RUNE_EFFECT_POOL`, rune name parts, upgrade costs, gem/chest weights, and craft logic.
  - Data model: Python dictionaries keyed by rune ID and rarity strings; players store quantities in `Player.runes` and rune item payloads in `Player.rune_items`.
  - Assessment: Rich content and progression logic exist, but they are embedded in a giant controller file rather than a dedicated crafting module. The canonical rune state and loadout contract now lives in the dedicated rune service layer so weapon-specific abilities stay separate from the universal rune loadout.

### Dismantle and market floor
- `backend/services/stash.py`
  - What it does: Defines the generic crafting-material sink for dismantling. Any rune or weapon can be dismantled into `crafted_supplies`, with yield scaled by rarity. Common / uncommon yield the least, while rare and above yield progressively more.
  - Data model: Uses `player.resources["crafted_supplies"]` as the sink resource and returns a simple `{ok, dismantled, yield}` payload.
  - Assessment: This creates a low-friction conversion path from “disposable” loot into a reusable currency for later rerolls and amplifier-rune crafting.

- `backend/services/auction_house.py`
  - What it does: Applies the market rarity floor before a listing can be created. `common` and `uncommon` are intentionally below the floor and are not allowed to be posted on the market; they exist to be dismantled, used, or converted into crafting material instead of traded.
  - Data model: `list_item()` and `list_rune()` now reject below-floor rarities before the listing is stored in the auction board.
  - Assessment: This keeps the market economy honest: only the “real trade tier” can circulate through the market, while basic loot stays in the crafting loop.

- `backend/main.py`
  - What it does: Exposes the dismantle and affix-reroll endpoint shape so the player can spend `crafted_supplies` to reroll an existing affix or to convert low-value gear into a sink resource for later amplifier-rune recipes.
  - Data model: These endpoints feed both the in-memory stash flow and the future runecrafting flow that consumes `crafted_supplies`.
  - Assessment: This is the bridge into the next crafting phase: low-tier trash gear becomes the sink material that powers rerolls and amplifier-rune creation.

### Build-rune generation
- In `backend/main.py`
  - What it does: Generates rune items, rolls rarity, generates passive/effect payloads, and manages rune loadout capacity.
  - Data model: `player.rune_items` is a list of dicts; each rune has `id`, `name`, `rarity`, `effects`, `level`, `upgrade`, etc.
  - Assessment: Fairly complete for a build-rune system, but it is still controller-owned and not isolated into a dedicated domain service.

### Rune collections / loadout sync
- In `backend/main.py`
  - What it does: Computes rune slot capacity, syncs loadout to player level, and applies rune-derived combat modifiers.
  - Data model: Uses `player.rune_loadout`, `player.rune_slot_capacity`, and `player.rune_items`.
  - Assessment: Functional, but the rune system is still tightly coupled to the API layer.

## 6) Market and trading systems

### Auction board model
- `backend/models/auction.py`
  - What it does: Defines the auction listing entity for either an `Item` or a `rune` dictionary.
  - Data model: Pydantic `AuctionListing` with `kind`, `item`, `rune`, `price`, `seller`, `allow_item_offers`, `min_offer_power`.
  - Assessment: Sound, compact domain model.

### Auction house service
- `backend/services/auction_house.py`
  - What it does: In-memory auction board, listing creation, listing cancellation, purchase by gold, and barter-style offers based on offered item power.
  - Data model: Uses `AuctionListing` instances stored in `AUCTIONS` and sales history in `AUCTION_HISTORY`.
  - Assessment: The strongest market implementation in the repo; it is still in-memory and single-process only, which makes it fragile for persistence or multi-user scaling.

### Trade request persistence
- `backend/services/trade_hub.py`
  - What it does: Persists trade requests into `database/trade_requests.json` with `create`, `list`, `update`, and expiration logic.
  - Data model: JSON rows with sender, target, offered items, requested items, gold fields, timestamps, status, and id.
  - Assessment: Solid lightweight persistence approach for a prototype, but it is plain JSON and not a proper relational or transactional store.

### Stash / inventory helpers
- `backend/services/stash.py`
  - What it does: Simple append/get helpers for the player stash.
  - Data model: Uses `Player.stash`.
  - Assessment: Very thin; this is a helper layer rather than a full inventory service.

### Equipment helpers
- `backend/services/equipment.py`
  - What it does: Equips and unequips items between stash and equipment slots.
  - Data model: Uses `Player.equipment` and `Player.stash`.
  - Assessment: Basic and functional, but it is a small service with minimal validation beyond index checks.

### Dungeon run wrappers
- `backend/services/dungeon_run.py`
  - What it does: Provides an older “run dungeon” flow that auto-simulates combat and grants loot. Also has interactive helpers for start/complete dungeon loops.
  - Data model: Uses `Player`, `generate_dungeon()`, and `Item` drops.
  - Assessment: Useful compatibility layer, but it still depends on the older combat simulation path.

## 7) Notable implementation risks / placeholders

- The project’s combat loop is not a strict branching state machine. Many outcomes are resolved by repeated function calls and accumulated modifiers rather than explicit multi-path combat rules.
- `backend/main.py` is the main integration point and therefore the highest-risk file for future changes; it is not modularized around trade, rune, or combat domains.
- Stringly-typed effect IDs (`damage_mult`, `shield`, `bleed`, etc.) are used widely. This is flexible, but it invites drift and typo bugs.
- The project mixes runtime state into the `Player` model very aggressively. This makes object access convenient, but it creates a large surface area for breakage.
- `backend/engine/compile_dungeon.py` references `scale_enemy()` but that function is not present in the file set; that is a clear fragility / stale integration sign.
- The project has a few empty placeholder files: `engine/death.py` and `engine/player_stats.py`.

## 8) System summary

- Combat: Present and fairly coherent in `engine/combat.py` plus passive/status systems.
- Loot: Present and procedural in `engine/loot.py`.
- Items: Present as a clear Pydantic `Item` model with passives.
- Rarity: Present as string-based tiering plus probabilistic rolls.
- Runes: Present, but the implementation is spread across `main.py` and the player model rather than a single dedicated rune domain module.
- Market / trading: Present in both auction-house and trade-request forms; auction logic is fairly complete, while trade requests are JSON-backed and lightweight.
