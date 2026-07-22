/* Non-combat special-event screen (core/events.py). A real alternative
 * to fighting: its own page, not a battle-screen overlay. The event has
 * already been rolled and resolved server-side by the time this page
 * loads (deterministic, seeded, no live/generative call involved) --
 * this page only fetches and displays what already happened, then lets
 * the player either return to the hub or, if this event was reached
 * mid push-your-luck run, make the same bank/continue decision the
 * battle screen would have offered.
 */
"use strict";

const $ = (id) => document.getElementById(id);

const TIER_LABELS = { fail: "No luck", partial: "Modest", success: "Good", great: "Great!" };

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
  $("event-tier-banner").textContent = TIER_LABELS[event.tier] || event.tier;
  $("event-tier-banner").className = `event-tier ${event.tier}`;
  renderOutcomeLines(event);

  const pushLuck = data.push_luck;
  const midRun = Boolean(pushLuck && pushLuck.can_bank);
  $("event-push-luck-panel").className = midRun ? "" : "hidden";
  $("event-return-hub").className = midRun ? "placeholder-back hidden" : "placeholder-back";
  if (midRun) {
    const p = pushLuck.pending;
    $("event-push-luck-summary").textContent =
      `Still pending from this run: ${p.gold} gold, ${totalChests(p.chests)} chest(s), streak ${p.streak}.`;
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
