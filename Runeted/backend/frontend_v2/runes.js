/* Runes page config: everything specific to runes, handed to the
 * shared grid/modal/equip driver in loadout-client.js.
 */
"use strict";

const RUNE_ICONS = {
  ember: "❤️‍🔥", thorn: "🌵", zephyr: "🪶", ward: "🧿", brand: "💢",
  pebble: "🪨", phantom: "👻", bastion: "🛡", crimson: "🩸", lastbreath: "🌬",
  dusk: "🌙", warbrand: "🗡", rune: "◈",
};

initLoadoutPage({
  apiBase: "/api/runes",
  idField: "rune_id",
  itemField: "rune",
  icons: RUNE_ICONS,
  defaultIcon: "rune",
  budgetText: (b) => `Cost: ${b.used} / ${b.cap} · ${b.slots_used} / ${b.slots_cap} slots equipped`,
  renderTags: (rune) => `${rune.type} · ${rune.rarity}`,
  renderStats: (rune) => `Cost ${rune.cost}`,
  renderDesc: (rune) => rune.description,
});
