/* Stats screen: view attributes and spend earned stat points.
 *
 * Deliberately minimal -- a simple panel of six rows, each with a "+"
 * button that spends one point via /api/player/spend_stat. Might fold
 * into the equipment page later; there's no reason to build more than
 * this until there's something else to put next to it.
 */
"use strict";

const $ = (id) => document.getElementById(id);

const STAT_LABELS = {
  strength: "Strength",
  dexterity: "Dexterity",
  intelligence: "Intelligence",
  vitality: "Vitality",
  luck: "Luck",
  charisma: "Charisma",
};

// What each point actually does, for the player reading this screen.
// Charisma is the one attribute with nothing here yet -- it feeds a
// later event system, not combat.
const STAT_EFFECTS = {
  strength: "Raises attack.",
  dexterity: "Raises dodge chance.",
  intelligence: "Raises max stamina.",
  vitality: "Raises defense and max HP.",
  luck: "Raises crit chance.",
  charisma: "No combat effect yet.",
};

let player = null;

function render() {
  $("stats-player-name").textContent = player.name;
  $("stats-player-level").textContent = `Lv ${player.level}`;
  $("stats-xp").textContent = `XP: ${player.exp} / ${player.exp_to_next}`;
  $("stats-points").textContent = player.stat_points > 0
    ? `${player.stat_points} stat point${player.stat_points === 1 ? "" : "s"} to spend`
    : "No stat points to spend right now — win battles to earn more.";

  const list = $("stat-list");
  list.textContent = "";
  for (const [stat, value] of Object.entries(player.attributes)) {
    const li = document.createElement("li");
    li.className = "stat-row";

    const name = document.createElement("span");
    name.className = "stat-name";
    name.textContent = STAT_LABELS[stat] || stat;

    const value_el = document.createElement("span");
    value_el.className = "stat-value";
    value_el.textContent = value;

    const effect = document.createElement("span");
    effect.className = "stat-effect muted";
    effect.textContent = STAT_EFFECTS[stat] || "";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "stat-add";
    btn.textContent = "+";
    btn.disabled = player.stat_points <= 0;
    btn.title = `Spend 1 point on ${STAT_LABELS[stat] || stat}`;
    btn.addEventListener("click", () => spend(stat));

    li.append(name, value_el, effect, btn);
    list.append(li);
  }
}

async function spend(stat) {
  try {
    const res = await fetch("/api/player/spend_stat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stat, amount: 1 }),
    });
    if (!res.ok) return;
    player = await res.json();
    render();
  } catch {
    // A failed spend just leaves the screen showing the last known state.
  }
}

async function load() {
  const res = await fetch("/api/player");
  player = await res.json();
  render();
}

load();
