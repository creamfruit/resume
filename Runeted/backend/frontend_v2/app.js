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
let autoTimer = null;
const AUTO_ROUND_DELAY_MS = 650;

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
  const res = await authFetch(path, options);
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

const apiBank = () => api("/api/battle/bank", { method: "POST" });
const apiContinueGauntlet = () => api("/api/battle/continue", { method: "POST" });

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
  renderEnemyMoves();

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
  // Auto-battle drives its own rounds (see maybeScheduleAutoRound below);
  // the manual pass button only makes sense when the player is in
  // control, so it disappears entirely while auto is on and reappears
  // the moment auto is turned back off.
  $("hold-button").className = state.auto ? "hidden" : "";
  $("hold-button").disabled = state.finished;
  renderSkills();
  renderRunes();
  renderConfirmBar();
  renderPushLuck();
  maybeScheduleAutoRound();
}

// ---------- Push your luck ----------
//
// After a victory the pending pool (this run's unbanked rewards) can
// either be banked for good, or put at risk on one more, harder fight.
// Both actions are only offered while state.push_luck says a decision
// is actually pending -- never as a standing option.

function renderPushLuck() {
  const panel = $("push-luck-panel");
  const info = state.push_luck;
  if (!info || !info.can_bank) {
    panel.className = "hidden";
    return;
  }
  const p = info.pending;
  const parts = [];
  for (const [tier, count] of Object.entries(p.chests)) parts.push(`${count}× ${tier} chest`);
  if (p.gold > 0) parts.push(`${p.gold} gold`);
  for (const [id, amount] of Object.entries(p.resources)) parts.push(`${amount} ${id}`);
  const pendingText = parts.length ? parts.join(", ") : "nothing yet";

  $("push-luck-summary").textContent =
    `Win streak ${p.streak}. Pending (unbanked): ${pendingText}. ` +
    `Banking keeps it for good — continuing risks losing all of it on a tougher fight for a bigger reward.`;
  panel.className = "";
}

async function bankPending() {
  try {
    await apiBank();
    window.location.href = "/";
  } catch (err) {
    notify(err.message);
  }
}

async function continuePushingLuck() {
  try {
    const result = await apiContinueGauntlet();
    // Continuing sometimes rolls a non-combat event instead of a fight
    // (core/events.py) -- that gets its own screen, not the arena. The
    // battle underneath is untouched, so coming back from /event lands
    // on this same bank/continue decision.
    if (result.kind === "event") {
      window.location.href = "/event";
      return;
    }
    state = result;
    selectedSkill = null;
    closeSkillModal();
    renderedRounds = 0;
    $("log-list").textContent = "";
    appendSystemLog(`Pushing your luck: a ${state.enemy.name} appears, tougher than before.`);
    render();
  } catch (err) {
    notify(err.message);
  }
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

function renderEnemyMoves() {
  // The enemy's full move pool, for reference — additive alongside the
  // telegraph card above, which only ever shows the one specific move
  // coming up next round.
  const list = $("enemy-movelist");
  list.textContent = "";
  for (const move of state.enemy.moves || []) {
    const li = document.createElement("li");
    li.className = "enemy-move-row";
    const name = document.createElement("span");
    name.className = "enemy-move-name";
    name.textContent = move.name;
    const desc = document.createElement("span");
    desc.className = "enemy-move-desc muted";
    desc.textContent = move.description;
    li.append(name, desc);
    list.append(li);
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
    const body = await apiRound(response);
    state = body.state;
    selectedSkill = null;
    appendLogEntry(body.event);
    spawnFloaters(body.event);
    render();
    describePushLuckResult(body.push_luck_result);
  } catch (err) {
    notify(err.message);
  }
}

function describePushLuckResult(result) {
  if (!result) return;
  if (result.result === "win") {
    const r = result.reward;
    notify(`Win banked to pending: +1 ${r.chest_rarity} chest, +${r.currency_amount} ${r.currency_id} (streak ${result.pending.streak}).`);
  } else if (result.result === "forfeit") {
    notify(`Defeated — the pending pool from this run (streak ${result.lost.streak}) was forfeited.`);
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

// ---------- Auto-battle round loop ----------
//
// While auto-battle is on, rounds advance by themselves — there is no
// manual "play next round" step. render() calls this after every state
// update; it arms at most one pending round at a time, so it can never
// fire a round while the previous one is still in flight, and it stops
// itself the instant auto turns off or the battle finishes (a defeat,
// or a victory that needs the push-your-luck decision).

function stopAutoLoop() {
  if (autoTimer !== null) {
    clearTimeout(autoTimer);
    autoTimer = null;
  }
}

function maybeScheduleAutoRound() {
  if (!state || !state.auto || state.finished) {
    stopAutoLoop();
    return;
  }
  if (autoTimer !== null) return; // a round is already queued
  autoTimer = setTimeout(() => {
    autoTimer = null;
    playRound(null);
  }, AUTO_ROUND_DELAY_MS);
}

async function newBattle() {
  // No manual parameters: the server derives the encounter from the
  // persistent player's real level and picks the archetype itself.
  try {
    const result = await apiStart({});
    // Some encounters roll into a non-combat event instead of a fight
    // (core/events.py) -- that gets its own screen, not the arena.
    if (result.kind === "event") {
      window.location.href = "/event";
      return;
    }
    state = result;
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
$("push-luck-bank").addEventListener("click", bankPending);
$("push-luck-continue").addEventListener("click", continuePushingLuck);

(async function boot() {
  if (!requireAuthToken()) return;
  try {
    state = await api("/api/battle/state");
    for (const ev of state.rounds) appendLogEntry(ev);
    render();
  } catch {
    newBattle();
  }
})();
