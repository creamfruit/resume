/* Home hub: the persistent navigation surface outside of battle.
 * Shows the real player state (never a debug value) and the entry
 * points to every major system. Only Start Battle leads somewhere
 * built; the rest are placeholder pages until their phase lands.
 */
"use strict";

const $ = (id) => document.getElementById(id);

async function loadPlayer() {
  try {
    const res = await fetch("/api/player");
    if (!res.ok) throw new Error("player fetch failed");
    const player = await res.json();
    $("home-player-name").textContent = player.name;
    $("home-player-level").textContent = `Lv ${player.level}`;
  } catch {
    $("home-player-level").textContent = "Lv —";
  }
}

async function startBattle() {
  const btn = $("nav-battle");
  btn.disabled = true;
  try {
    const res = await fetch("/api/battle/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error("battle start failed");
    window.location.href = "/battle";
  } catch {
    btn.disabled = false;
  }
}

$("nav-battle").addEventListener("click", startBattle);
loadPlayer();
