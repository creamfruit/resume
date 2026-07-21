# RPG Game Architecture Inventory

This document is the shared reference for the combat, loot, item, rune, rarity, and market/trading systems currently present in the codebase. It is an inventory only; no gameplay logic was changed.

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
- `backend/services/dodge.py`
  - What it does: Legacy enemy-damage helper that resolves dodge outcomes with a simple reduction formula.
  - Data model: Uses `Player` and `Enemy` objects plus `player.defense` and `player.dodge_bonus`.
  - Assessment: Fragile / legacy; it is a thin, older helper and does not fully match the newer passive/status engine.

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
