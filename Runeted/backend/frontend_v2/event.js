/* Non-combat special-event screen (core/special_events.py). A real
 * alternative to fighting: its own page, not a battle-screen overlay.
 * Landing here never means an outcome has already happened -- the
 * server hands back an *unresolved* event (`resolved: false`) that
 * only presents a choice (engage or walk away). Nothing about the
 * outcome is decided until the player picks one; engaging is the only
 * path that rolls anything (deterministic, seeded, weighted by
 * whichever single stat this event type is gated on -- charisma or
 * luck), and walking away leaves the player exactly as they were.
 */
"use strict";

const $ = (id) => document.getElementById(id);

const TIER_LABELS = { fail: "No luck", partial: "Modest", success: "Good", great: "Great!" };

const ENGAGE_LABELS = {
  merchant: "Trade with the merchant",
  shrine: "Approach the shrine",
  hazard: "Investigate",
  treasure: "Open it",
};
const WALK_AWAY_LABELS = {
  merchant: "Walk away",
  shrine: "Walk away",
  hazard: "Leave it alone",
  treasure: "Leave it alone",
};
const GOVERNING_STAT_HINTS = {
  charisma: "Your charisma will decide how this goes.",
  luck: "Your luck will decide how this goes.",
};

async function api(path, options) {
  const res = await authFetch(path, options);
  const body = await res.json();
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return body;
}

function notify(message) {
  const el = $("notice");
  el.textContent = message;
  el.className = "";
  clearTimeout(notify._t);
  notify._t = setTimeout(() => (el.className = "hidden"), 3500);
}

function renderOutcomeLines(event) {
  const list = $("event-outcome-list");
  list.textContent = "";
  const add = (text) => {
    const li = document.createElement("li");
    li.textContent = text;
    list.append(li);
  };
  if (event.walked_away) {
    add("You walked away. Nothing gained, nothing lost.");
    return;
  }
  if (event.gold_delta) add(`+${event.gold_delta} gold`);
  if (event.resource_id && event.resource_amount) add(`+${event.resource_amount} ${event.resource_id}`);
  if (event.chest_rarity) add(`+1 ${event.chest_rarity} chest`);
  if (event.hp_loss_pct > 0) add(`Lost ${Math.round(event.hp_loss_pct * 100)}% of your max HP`);
  if (event.buff_rounds > 0) {
    add(`Blessed: +${Math.round(event.buff_mult * 100)}% attack for your next ${event.buff_rounds} rounds of battle`);
  }
  if (!list.children.length) add("Nothing happened this time.");
}

function totalChests(chests) {
  return Object.values(chests || {}).reduce((sum, n) => sum + n, 0);
}

function render(data) {
  const event = data.event;
  $("event-type-tag").textContent = event.type;
  $("event-name").textContent = event.name;
  $("event-description").textContent = event.description;

  const unresolved = !event.resolved;
  $("event-choice-panel").className = unresolved ? "" : "hidden";
  $("event-engage").textContent = ENGAGE_LABELS[event.type] || "Engage";
  $("event-walk-away").textContent = WALK_AWAY_LABELS[event.type] || "Walk away";
  $("event-governing-stat").className = unresolved ? "muted" : "muted hidden";
  $("event-governing-stat").textContent = GOVERNING_STAT_HINTS[event.governing_stat] || "";

  $("event-tier-banner").className = unresolved ? "hidden" : `event-tier ${event.tier || "walked-away"}`;
  $("event-tier-banner").textContent = unresolved ? "" : event.walked_away ? "Walked away" : (TIER_LABELS[event.tier] || event.tier);
  $("event-outcome-list").className = unresolved ? "hidden" : "";
  if (!unresolved) renderOutcomeLines(event);

  const pushLuck = data.push_luck;
  const midRun = Boolean(pushLuck && pushLuck.can_bank);
  const showPushLuck = !unresolved && midRun;
  $("event-push-luck-panel").className = showPushLuck ? "" : "hidden";
  $("event-return-hub").className = (!unresolved && !midRun) ? "placeholder-back" : "placeholder-back hidden";
  if (showPushLuck) {
    const p = pushLuck.pending;
    $("event-push-luck-summary").textContent =
      `Still pending from this run: ${p.gold} gold, ${totalChests(p.chests)} chest(s), streak ${p.streak}.`;
  }
}

async function engage() {
  try {
    const data = await api("/api/event/engage", { method: "POST" });
    render(data);
  } catch (err) {
    notify(err.message);
  }
}

async function walkAway() {
  try {
    const data = await api("/api/event/walk_away", { method: "POST" });
    render(data);
  } catch (err) {
    notify(err.message);
  }
}

async function bank() {
  try {
    await api("/api/battle/bank", { method: "POST" });
    window.location.href = "/";
  } catch (err) {
    notify(err.message);
  }
}

async function continuePushingLuck() {
  try {
    const result = await api("/api/battle/continue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    window.location.href = result.kind === "event" ? "/event" : "/battle";
  } catch (err) {
    notify(err.message);
  }
}

$("event-engage").addEventListener("click", engage);
$("event-walk-away").addEventListener("click", walkAway);
$("event-bank").addEventListener("click", bank);
$("event-continue").addEventListener("click", continuePushingLuck);

(async function boot() {
  if (!requireAuthToken()) return;
  try {
    const data = await api("/api/event/state");
    render(data);
  } catch {
    window.location.href = "/";
  }
})();
