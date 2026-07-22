/* Skills page config: everything specific to skills, handed to the
 * shared grid/modal/equip driver in loadout-client.js.
 */
"use strict";

const SKILL_ICONS = {
  flame: "🔥", frost: "❄", venom: "☠", stone: "🪨", arcane: "✴", blood: "🩸",
  sword: "⚔", cross: "✂", shield: "🛡", wind: "💨", banner: "📯", leaf: "🌿",
  sigil: "◆",
};

initLoadoutPage({
  apiBase: "/api/skills",
  idField: "skill_id",
  itemField: "skill",
  icons: SKILL_ICONS,
  defaultIcon: "sigil",
  budgetText: (b) => `Value: ${b.used} / ${b.cap} · ${b.slots_used} / ${b.slots_cap} slots equipped`,
  renderTags: (skill) => `${skill.kind} · ${skill.method}`,
  renderStats: (skill) => {
    const parts = [`Value ${skill.value}`, `Stamina ${skill.stamina_cost}`, `Cooldown ${skill.cooldown} round${skill.cooldown === 1 ? "" : "s"}`];
    if (skill.counters.length) parts.push(`Counters ${skill.counters.join(", ")}`);
    return parts.join(" · ");
  },
  renderDesc: (skill) => skill.full_text,
});
