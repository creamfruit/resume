/* Battle screen driver.
 *
 * Renders battle state from /api/battle/* and the structured RoundEvent
 * stream (core/events.py). All game rules live server-side; this file
 * only displays state and collects one response per round.
 *
 * Skill buttons are a compact single line — icon, name, damage,
 * cooldown, and a status icon + duration when the skill applies one.
 * The full description lives behind the ⓘ affordance, which opens a
 * centered modal over a dimmed backdrop. Equipped passive runes render
 * as a chip row below the enemy panel; clicking a chip opens the same
 * modal shell with the rune's type, rarity, cost, and description.
 */
"use strict";

const $ = (id) => document.getElementById(id);

let state = null;
let selectedSkill = null;
let renderedRounds = 0;

// Placeholder glyphs for server icon ids; swap for real art later.
const SKILL_ICONS = {
  flame: "🔥", frost: "❄", venom: "☠", stone: "🪨", arcane: "✴", blood: "🩸",
  sword: "⚔", cross: "✂", shield: "🛡", wind: "💨", banner: "📯", leaf: "🌿",
  sigil: "◆",
};
const STATUS_ICONS = { exposed: "🎯", empowered: "⬆", poison: "☠" };
// Passive-rune glyphs — a separate map from skill/status glyphs so the
// three icon families never collide visually.
const RUNE_ICONS = { ember: "❤️‍🔥", thorn: "🌵", zephyr: "🪶", ward: "🧿", brand: "💢", rune: "◈" };

// ---------- API ----------

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json();
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return body;
}

const apiStart = (payload) =>
  api("/api/battle/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

const apiRound = (response) =>
  api("/api/battle/round", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ response }),
  });

const apiAuto = (enabled) =>
  api("/api/battle/auto", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });

// ---------- Rendering ----------

function setBar(fillId, textId, value, max) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  $(fillId).style.width = pct + "%";
  $(textId).textContent = `${value} / ${max}`;
}

function render() {
  if (!state) return;

  $("player-name").textContent = `${state.player.name} · Lv ${state.player.level}`;
  $("enemy-name").textContent = `${state.enemy.name} · Lv ${state.enemy.level}`;
  setBar("player-hp-fill", "player-hp-text", state.player.hp, state.player.max_hp);
  setBar("player-stamina-fill", "player-stamina-text", state.player.stamina, state.player.max_stamina);
  setBar("enemy-hp-fill", "enemy-hp-text", state.enemy.hp, state.enemy.max_hp);
  setBar("enemy-stamina-fill", "enemy-stamina-text", state.enemy.stamina, state.enemy.max_stamina);

  if (state.telegraph) {
    $("telegraph-name").textContent = state.telegraph.name;
    $("telegraph-desc").textContent = state.telegraph.description;
  } else {
    $("telegraph-name").textContent = "—";
    $("telegraph-desc").textContent = "";
  }

  const banner = $("outcome-banner");
  if (state.finished) {
    banner.textContent = state.outcome === "victory" ? "Victory!" : "Defeat.";
    banner.className = state.outcome;
  } else {
    banner.className = "hidden";
  }

  $("auto-label").textContent = `Auto-battle: ${state.auto ? "on" : "off"}`;
  // The toggle's icon spins while auto-battle is on so the mode is
  // obvious at a glance.
  $("auto-icon").classList.toggle("spinning", state.auto);
  $("hold-icon").textContent = state.auto ? "▶" : "⏭";
  $("hold-label").textContent = state.auto ? "Play next round" : "Pass (no skill)";
  $("hold-button").disabled = state.finished;
  renderSkills();
  renderRunes();
  renderConfirmBar();
}

function renderSkills() {
  const list = $("skill-list");
  list.textContent = "";
  for (const skill of state.skills) {
    const li = document.createElement("li");
    li.className = "skill-item";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "skill-button" + (selectedSkill === skill.id ? " selected" : "");
    button.dataset.skillId = skill.id;
    button.disabled = state.finished || state.auto || !skill.usable;
    button.title = skill.description;

    const icon = document.createElement("span");
    icon.className = "skill-icon";
    icon.dataset.icon = skill.icon; // real icon ids slot in here later
    icon.textContent = SKILL_ICONS[skill.icon] || SKILL_ICONS.sigil;

    const name = document.createElement("span");
    name.className = "skill-name";
    name.textContent = skill.name;

    button.append(icon, name);

    const addStat = (cls, text, label) => {
      const sep = document.createElement("span");
      sep.className = "skill-sep";
      sep.textContent = "|";
      const stat = document.createElement("span");
      stat.className = cls;
      stat.textContent = text;
      if (label) stat.title = label;
      button.append(sep, stat);
    };

    addStat("skill-dmg", `💥 ${skill.damage > 0 ? String(Math.round(skill.damage)) : "—"}`, "Damage");
    addStat("skill-cd", `⏳ ${skill.cooldown}`, "Cooldown (rounds)");
    if (skill.applies_status) {
      const glyph = STATUS_ICONS[skill.applies_status.status] || "✦";
      addStat(
        "skill-status",
        `${glyph} ${skill.applies_status.duration}`,
        `${skill.applies_status.status} for ${skill.applies_status.duration} round(s) ${skill.applies_status.detail}`
      );
    }
    if (skill.remaining_cooldown > 0) {
      const chip = document.createElement("span");
      chip.className = "skill-cooling";
      chip.textContent = `CD ${skill.remaining_cooldown}`;
      button.append(chip);
    }

    button.addEventListener("click", () => selectSkill(skill));

    const infoToggle = document.createElement("button");
    infoToggle.type = "button";
    infoToggle.className = "skill-info-toggle";
    infoToggle.textContent = "ⓘ";
    infoToggle.title = `About ${skill.name}`;
    infoToggle.addEventListener("click", () => openSkillModal(skill));

    li.append(button, infoToggle);
    list.append(li);
  }
}

function renderRunes() {
  // Equipped passive runes: a compact chip row below the enemy panel.
  // Chips open the same centered modal the skill ⓘ affordance uses.
  const row = $("rune-row");
  row.textContent = "";
  const info = state.runes;
  if (!info) return;
  $("rune-panel-title").textContent = `Equipped runes · cost ${info.cost_used}/${info.cost_cap}`;
  for (const rune of info.equipped) {
    const li = document.createElement("li");
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "rune-chip";
    chip.title = rune.short;
    const icon = document.createElement("span");
    icon.className = "rune-icon";
    icon.dataset.icon = rune.icon; // real icon ids slot in here later
    icon.textContent = RUNE_ICONS[rune.icon] || RUNE_ICONS.rune;
    const name = document.createElement("span");
    name.textContent = rune.name;
    chip.append(icon, name);
    chip.addEventListener("click", () => openRuneModal(rune));
    li.append(chip);
    row.append(li);
  }
}

function renderConfirmBar() {
  const bar = $("confirm-bar");
  if (!selectedSkill) {
    bar.className = "hidden";
    return;
  }
  const skill = state.skills.find((s) => s.id === selectedSkill);
  if (!skill) {
    selectedSkill = null;
    bar.className = "hidden";
    return;
  }
  $("confirm-text").textContent = `Respond with ${skill.name}?`;
  bar.className = "";
}

// ---------- Skill info modal ----------

function openSkillModal(skill) {
  $("skill-modal-title").textContent = `${SKILL_ICONS[skill.icon] || ""} ${skill.name}`.trim();
  $("skill-modal-meta").textContent =
    `${skill.kind} · ${skill.stamina_cost} stamina · ${skill.cooldown}-round cooldown` +
    (skill.counters.length ? ` · counters ${skill.counters.join(", ")}` : "");
  $("skill-modal-body").textContent = skill.full_text;
  $("skill-modal").className = "";
}

function openRuneModal(rune) {
  // Runes reuse the skill modal shell: same centered card over the same
  // dimmed backdrop, same close affordances.
  $("skill-modal-title").textContent = `${RUNE_ICONS[rune.icon] || RUNE_ICONS.rune} ${rune.name}`;
  $("skill-modal-meta").textContent = `Passive rune · ${rune.type} · ${rune.rarity} · cost ${rune.cost}`;
  $("skill-modal-body").textContent = rune.full_text;
  $("skill-modal").className = "";
}

function closeSkillModal() {
  $("skill-modal").className = "hidden";
}

$("skill-modal-close").addEventListener("click", closeSkillModal);
// Clicking the dimmed backdrop (not the card) also closes the modal.
$("skill-modal").addEventListener("click", (ev) => {
  if (ev.target === $("skill-modal")) closeSkillModal();
});
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") closeSkillModal();
});

// ---------- Interactions ----------

function selectSkill(skill) {
  if (state.finished || state.auto || !skill.usable) return;
  selectedSkill = skill.id;
  render();
}

function cancelSelection() {
  // Back to the battle menu without committing to a turn.
  selectedSkill = null;
  render();
}

function notify(message) {
  const el = $("notice");
  el.textContent = message;
  el.className = "";
  clearTimeout(notify._t);
  notify._t = setTimeout(() => (el.className = "hidden"), 3500);
}

async function playRound(response) {
  try {
    const { event, state: newState } = await apiRound(response);
    state = newState;
    selectedSkill = null;
    appendLogEntry(event);
    spawnFloaters(event);
    render();
  } catch (err) {
    notify(err.message);
  }
}

async function toggleAuto() {
  try {
    state = await apiAuto(!state.auto);
    selectedSkill = null;
    render();
  } catch (err) {
    notify(err.message);
  }
}

async function newBattle() {
  // No manual parameters: the server derives the encounter from the
  // persistent player's real level and picks the archetype itself.
  try {
    state = await apiStart({});
    selectedSkill = null;
    closeSkillModal();
    renderedRounds = 0;
    $("log-list").textContent = "";
    appendSystemLog(`A ${state.enemy.name} appears. Its first move is telegraphed on the right.`);
    render();
  } catch (err) {
    notify(err.message);
  }
}

// ---------- Battle log & floaters (from structured RoundEvents) ----------

function describeEvent(ev) {
  const parts = [];
  const intent = ev.enemy.intent;
  let move = `Enemy telegraphed ${intent.name}`;
  if (intent.downgraded_from) move += ` (winded — downgraded from ${intent.downgraded_from})`;
  parts.push(move + ".");

  const name = ev.player.response_name;
  switch (ev.player.action) {
    case "attack":
      parts.push(
        ev.player.matched
          ? `You countered with ${name} — effect negated, enemy exposed.`
          : `You attacked with ${name}, but it did not counter the move.`
      );
      break;
    case "defend":
      parts.push(`You braced behind ${name} — the move's effect was blocked.`);
      break;
    case "dodge":
      parts.push(`You used ${name} to slip the incoming move.`);
      break;
    case "buff":
      parts.push(`You used ${name} — your attack is up for the next rounds.`);
      break;
    case "recovery":
      parts.push(`You used ${name} and recovered ${ev.player.stamina_restored} stamina.`);
      break;
    default:
      parts.push("You passed on skills and struck plainly.");
  }

  if (ev.player.damage_dealt > 0) {
    parts.push(`You dealt ${ev.player.damage_dealt}${ev.player.exposed_bonus_applied ? " (exposed bonus)" : ""}.`);
  }

  if (!ev.enemy.resolved) {
    parts.push("The enemy fell before it could act.");
  } else if (ev.enemy.dodged) {
    parts.push("You evaded its attack entirely.");
  } else if (ev.enemy.damage_dealt > 0) {
    parts.push(`It hit you for ${ev.enemy.damage_dealt}.`);
  } else {
    parts.push("Its move was fully blunted.");
  }
  return parts.join(" ");
}

function appendLogEntry(ev) {
  const li = document.createElement("li");
  li.textContent = `R${ev.round}: ${describeEvent(ev)}`;
  $("log-list").append(li);
  renderedRounds = ev.round;
  if (ev.outcome !== "in_progress") {
    appendSystemLog(ev.outcome === "victory" ? "Victory!" : "Defeat.", `log-${ev.outcome}`);
  }
  const panel = $("log-list");
  panel.scrollTop = panel.scrollHeight;
}

function appendSystemLog(text, cls) {
  const li = document.createElement("li");
  li.textContent = text;
  if (cls) li.className = cls;
  $("log-list").append(li);
}

function spawnFloater(zoneId, text, cls) {
  const zone = $(zoneId);
  const el = document.createElement("span");
  el.className = `floater ${cls}`;
  el.textContent = text;
  el.style.left = 30 + Math.random() * 40 + "%";
  zone.append(el);
  setTimeout(() => el.remove(), 1500);
}

function spawnFloaters(ev) {
  const enemyDelta = ev.enemy.hp.delta;
  if (enemyDelta < 0) spawnFloater("enemy-floaters", `−${Math.abs(enemyDelta)}`, "damage");
  else if (enemyDelta > 0) spawnFloater("enemy-floaters", `+${enemyDelta}`, "heal");

  const playerDelta = ev.player.hp.delta;
  if (playerDelta < 0) spawnFloater("player-floaters", `−${Math.abs(playerDelta)}`, "damage");
  else if (playerDelta > 0) spawnFloater("player-floaters", `+${playerDelta}`, "heal");
  else if (ev.enemy.resolved && ev.enemy.dodged) spawnFloater("player-floaters", "Dodged!", "info");
  else if (ev.enemy.resolved && ev.enemy.effect_negated) spawnFloater("player-floaters", "Negated!", "info");
  if (ev.player.stamina_restored > 0) spawnFloater("player-floaters", `+${ev.player.stamina_restored} stam`, "info");
}

// ---------- Boot ----------

$("confirm-use").addEventListener("click", () => selectedSkill && playRound(selectedSkill));
$("confirm-cancel").addEventListener("click", cancelSelection);
$("hold-button").addEventListener("click", () => playRound(null));
$("auto-toggle").addEventListener("click", toggleAuto);

(async function boot() {
  try {
    state = await api("/api/battle/state");
    for (const ev of state.rounds) appendLogEntry(ev);
    render();
  } catch {
    newBattle();
  }
})();
