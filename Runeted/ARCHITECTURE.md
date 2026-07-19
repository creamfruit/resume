# RPG Game Architecture Inventory

This document has two parts. **Part A** describes the Runeted rebuild — the new game core being built in 5 phases under `backend/core/`. **Part B** (sections 1–8 below) is the legacy reference inventory of the old codebase, kept in place as the authority on what systems must exist; old files are replaced phase by phase.

## Part A — Runeted rebuild

### Phase 1: core combat loop and player state (`backend/core/`)

- `core/intent.py` — **the single system that generates and tracks enemy intent/telegraphs.** Every enemy move is announced one round ahead (name + short effect description) before the player acts. `IntentTracker` owns the archetype move deck and its index for a battle; no other module may create or mutate intents, and nothing is ever written onto the enemy object (the old split between `boss_ai.py` and `session.py` is deliberately not recreated). Each intent has a `contact_mult` (graze that always lands) and an `effect_mult` (the telegraphed effect, fully negated by a correct counter). An intent is countered when the responding skill's `counters` tags intersect the intent's `countered_by` set (enemy archetype + intent kind).
- `core/skills.py` — **the Skill system: the player's active, per-turn combat choice.** (This concept was originally mislabelled "equipped runes" in battle; it was renamed to skills after playtesting — same mechanics, new name. The *passive* Rune system is a separate phase-4 concern that stays in the pre-approved rune module `models/rune.py` / `services/rune_system.py`, which core no longer imports.) A `Skill` has a value, a value-scaled cooldown (1–3 rounds) and stamina cost (`max(1, value)`, overridable — recovery costs 0), `counters` tags, a coarse `method` tag (offense/defense/utility/drawback/amplifier), and a mechanical `kind`: **attack** (strike + counter attempt), **defend** (blocks any telegraphed effect, deals no damage), **dodge** (evades the whole move, deals no damage), **buff** (spends stamina for a temporary attack bonus), **recovery** (costs 0 stamina and restores stamina, so an empty bar never leaves the player without a legal action). `SkillLoadout` is the only place loadouts are built and enforces both caps at construction: at most 6 slots **and** total skill value within the value budget (10, plus any equipped `budget_modifier`s). The default loadout (total value 9/10) is two kind-countering attacks — Breaker Lunge (heavy, guard_break) and Flurry Break (multi), which together cover every dangerous telegraph in every archetype deck — plus Bulwark (defend), Sidestep (dodge), War Chant (buff, +50% attack for 2 rounds), and Second Wind (recovery, +3 stamina).
- `core/stats.py` — the derived-stats pipeline. Combat reads `DerivedStats` exclusively; raw player/enemy fields never appear in damage math. Later phases plug in via `StatContribution` (equipment in phase 2, runes in phase 4). Both sides share one per-level growth base (`GROWTH_PER_LEVEL`), so equal-level fights play identically at every level; `baseline_enemy()` is the canonical enemy statline per level, which phase 3 encounter generation must build on rather than invent a second curve.
- `core/battle.py` — the round loop: telegraph → player response (skill or hold) → the response resolves by kind (holding or an attack skill strikes; a matched counter negates the effect and leaves the enemy *exposed* — consumed by the next strike, so it carries over non-strike rounds; defend blocks the effect without striking; dodge routes through the game's single dodge roll at certainty; buff applies a duration-limited attack bonus; recovery restores stamina) → enemy's telegraphed move resolves → cooldowns tick, buffs count down → next telegraph. Includes the auto-battle toggle: the policy counters dangerous moves (`effect_mult >= 1.0`) with the cheapest matching off-cooldown attack, falls back to the cheapest affordable defend/dodge mitigation, and holds otherwise; it never spends turns on buffs or recovery. Tuned so auto-battle reliably wins at or below the player's level and reliably loses above it (the balance matrix re-verified unchanged after the skill rework, because the two default attacks keep full counter coverage of dangerous moves). Phase 1 combat is deterministic — crit/dodge exist in the pipeline but are not rolled yet.
- `core/resolution.py` — the single win/loss decision point (`Outcome`: in_progress / victory / defeat). The player acts first within a round, so simultaneous death cannot occur.
- `core/player_state.py` — lean `PlayerState`: identity (name) and progression (level, exp, stat points, attributes, current HP) only. Equipment, stash, runes, and economy live in their own modules; a regression test enforces that those fields never migrate onto the model.
- `tests/test_core_combat.py` — phase 1 regression suite (telegraph one-ahead contract, counter/negate/exposed rules, cooldown enforcement, value-budget enforcement, the defend/dodge/buff/recovery move kinds, auto-battle win/loss matrix, derived-pipeline isolation, resolution, player-state leanness).

### Phase 2: combat hardening and the structured event stream

- **Dodge single-sourced.** `services/dodge.py` does not exist in this folder (it was already dropped when the old repo was ported) and nothing references it — verified by search. Dodge is now a real mechanic with exactly one calculation in the whole game: the chance comes from the derived-stats pipeline (`DerivedStats.dodge_chance` — dexterity plus `dodge_flat` contributions, capped) and is rolled in one place, the enemy-move resolution in `core/battle.py`. A dodged move deals zero damage. Default attributes give 0% dodge, so baseline combat stays deterministic. The old stack's client-supplied `dodge_success` flag (legacy `engine/combat.py`) is retired with the rest of the old combat path.
- **Damage-suppression and enemy-HP audit.** The two intermittent old-codebase bugs ("damage sometimes not dealt", "enemy HP sometimes increases") were hunted with a fuzz audit over the rebuilt loop — 1,530 battles / 8,011 rounds across auto, random-manual, and dodge-heavy play: zero occurrences of either. Neither bug is reachable in the new loop (uncountered, undodged moves floor at 1 damage; enemy HP is monotonically non-increasing).
- **Enemy-HP hard invariant.** `core/battle.py` enforces at runtime that enemy HP never rises — within a round or between turns — unless a *named* heal/regen/lifesteal event fired that round (plumbed via the round's `healing_events`; none exist yet). A violation logs which events fired (or that none did) via the `core.battle` logger and raises. Later phases must register healing effects there or the invariant trips.
- **Stamina.** Neither new model had a stamina field; both gained one (`PlayerState.stamina`, `BaselineEnemy.stamina`/`max_stamina` — None means full for the player, like HP). Ceilings and regen flow through the pipeline (`DerivedStats.max_stamina` / `stamina_regen`). Tunables live at the top of `core/stats.py` (player base 10 + 0.5/INT, regen 2; enemy 20, regen 2 — deliberately scale-free so pacing is identical at every level). Skill activations cost `max(1, skill.value)` stamina (`core/skills.py: stamina_cost_of`, overridable per skill — recovery skills declare 0); enemy move costs sit in `INTENT_LIBRARY` (basic 1, guard_break 2, heavy 3, multi 3). Actions without enough stamina are blocked: a player response is rejected with no state change; an enemy that cannot afford its deck move telegraphs a downgraded (cheapest) move instead, decided inside the intent system and reported as `downgraded_from` in the event. Both sides regenerate a fixed amount at end of round; the auto-battle policy only picks affordable skills, and the 0-cost recovery skill guarantees a human player always has a legal action. Balance matrix re-verified after wiring: unchanged, zero violations.
- **Structured round events.** `core/events.py` defines the per-round contract (`RoundEvent`) the frontend renders from: for each side the move/intent used (with name and description), the response chosen and its `action` kind (strike/attack/defend/dodge/buff/recovery), damage dealt, HP delta (before/after/delta), stamina delta (spent/restored/regen/before/after/delta), statuses applied/removed (currently `exposed` on the enemy and `empowered` on the player), plus `next_telegraph` and outcome. `Battle.play_round` returns exactly this dict and appends it to `battle.rounds`.
- `tests/test_combat_hardening.py` — phase 2 regression suite (dodge retirement + single-source, stamina costs/regen/blocking, enemy-HP invariant, event schema).

### Battle screen (playtest slice) and the skill rename

A thin, playtest-facing battle screen exists ahead of the full phase-5 frontend work:

- `backend/battle_app.py` — minimal FastAPI server for the battle screen (`/api/battle/start|state|round|auto`). Deliberately thin: every rule lives in `backend/core`; responses are battle state plus the structured RoundEvent stream. State includes the `skills` payload (per skill: id, name, icon id, kind, base strike damage, stamina cost, cooldown, remaining cooldown, usability, counters, applied status + duration, short description, full modal text) and the loadout `budget` (cap and used value). Run from `backend/`: `..\.venv\Scripts\python.exe -m uvicorn battle_app:app --port 8010`. Legacy `main.py` still serves the old game.
- `backend/frontend_v2/` — the battle screen (no build step; plain HTML/CSS/JS rendering server state only). Structure after the playtest refinement:
  - **Skill buttons** (`#skill-list`): one compact single-line button per skill — icon, name, damage number, cooldown number, and a status-effect icon + duration when the skill applies one (e.g. `⚔ Breaker Lunge | 7 | 2 | 🎯 1`). All five kinds render in this one flat list; there are no separate button categories and no dropdowns. Icon ids come from the server; the frontend maps them to placeholder glyphs.
  - **Info modal** (`#skill-modal`): each button has an `ⓘ` affordance that opens a centered modal over a dimmed backdrop with the skill's full description, including what it counters. Closed by the explicit ✕ control, a click on the backdrop, or Escape. Descriptions are never rendered inline under the buttons.
  - **Two-column combatant layout** (`#arena`): the formerly empty margins are now flanking columns — player (name/level, figurine, HP, stamina) on the left, enemy (name/level, figurine, HP, stamina, telegraph card) on the right — with skills, actions, and the battle log in the center. Columns stack on narrow screens.
  - **Figurines**: plain monochrome placeholders — a white generic user silhouette for the player and a white devil-face silhouette (horns, no interior detail) for the enemy, both inline SVG.
  - The admin-style controls at the top (level inputs, enemy-type dropdown, new-battle button) are testing scaffolding, not final UI.
- **The rune→skill rename.** What the battle screen previously labelled "equipped runes" is the Skill system (`core/skills.py`) — the active per-turn choice with a value budget, cooldowns, counters, and stamina costs. The rename covers backend, frontend, and tests; a regression test asserts the battle UI no longer uses the word "rune". The passive Rune system (equipping runes for stat effects, crafting, economy) is the upcoming phase and builds on the untouched pre-approved rune module.
- `tests/test_battle_screen.py` — battle-screen suite (API payload shape incl. kinds/budget/recovery-legality, modal + layout + silhouette markup affordances, rename regression, skill description completeness).

Phases 3–5 (items/equipment/loot; enemies/encounters; runes/crafting/economy; full frontend) are otherwise not started. Pre-approved building blocks copied from the old repo and treated as correct: rune module, item schema + validation, weapon innate abilities, dismantle system, market rarity floor, enemy modifier stacking.

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
