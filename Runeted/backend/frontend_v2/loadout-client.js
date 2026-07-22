/* Shared driver for the Skills and Runes pages.
 *
 * Both pages show the same shape of thing -- a fixed grid of equip
 * slots (6 for skills, 3 for runes -- the page passes its own count,
 * nothing here assumes a number) backed by the same kind of API
 * (GET the catalog+slots, POST equip/unequip/swap) -- so the grid and
 * modal logic lives here once, and each page supplies only what
 * actually differs: field names, icon glyphs, and how to render a
 * catalog item's tags/stats/description. Included via a <script> tag
 * before the page's own tiny config script, the same pattern
 * auth-client.js already uses.
 *
 * Interaction model (click-only, no drag-and-drop):
 * - Click an empty slot ("+")   -> picker: pick any available item to
 *                                  equip into that slot; the
 *                                  recommended one is marked.
 * - Click a filled slot         -> that item's detail, an Unequip
 *                                  button, and a mini-grid of every
 *                                  *other* slot to move/swap with in
 *                                  one step -- filled<->filled swaps,
 *                                  filled<->empty moves, no separate
 *                                  unequip-then-re-equip needed.
 */
"use strict";

function initLoadoutPage(config) {
  const $ = (id) => document.getElementById(id);
  let data = null;

  function iconFor(item) {
    return (config.icons[item.icon] || config.icons[config.defaultIcon]);
  }

  function render() {
    $("loadout-budget").textContent = config.budgetText(data.budget);

    const grid = $("slot-grid");
    grid.textContent = "";
    data.slots.forEach((slot) => {
      const item = slot[config.itemField];
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "slot-square" + (item ? " filled" : " empty");
      if (item) {
        const icon = document.createElement("span");
        icon.className = "slot-icon";
        icon.textContent = iconFor(item);
        const name = document.createElement("span");
        name.className = "slot-name";
        name.textContent = item.name;
        cell.append(icon, name);
        cell.title = item.name;
      } else {
        cell.textContent = "+";
        cell.title = "Equip something here";
      }
      cell.addEventListener("click", () => (item ? openSlotAction(slot.index, item) : openPicker(slot.index)));
      grid.append(cell);
    });
  }

  // ---------- Modal ----------

  function openModal(title) {
    $("loadout-modal-title").textContent = title;
    $("loadout-modal-body").textContent = "";
    $("loadout-modal").className = "";
  }

  function closeModal() {
    $("loadout-modal").className = "hidden";
  }

  function openPicker(slotIndex) {
    openModal(`Equip into slot ${slotIndex + 1}`);
    const body = $("loadout-modal-body");

    const available = data.catalog.filter((item) => !item.equipped);
    if (!available.length) {
      const p = document.createElement("p");
      p.className = "muted";
      p.textContent = "Nothing left to equip -- everything in the catalog is already in a slot.";
      body.append(p);
      return;
    }

    const list = document.createElement("ul");
    list.className = "picker-list";
    for (const item of available) {
      const li = document.createElement("li");
      const row = document.createElement("button");
      row.type = "button";
      row.className = "picker-row" + (item.id === data.recommended_id ? " recommended" : "");

      const icon = document.createElement("span");
      icon.className = "loadout-icon";
      icon.textContent = iconFor(item);

      const main = document.createElement("div");
      main.className = "loadout-main";
      const nameLine = document.createElement("div");
      nameLine.className = "loadout-name-line";
      const name = document.createElement("span");
      name.className = "loadout-name";
      name.textContent = item.name;
      nameLine.append(name);
      if (item.id === data.recommended_id) {
        const badge = document.createElement("span");
        badge.className = "picker-recommended-badge";
        badge.textContent = "Recommended";
        nameLine.append(badge);
      }
      const tag = document.createElement("span");
      tag.className = "loadout-tag";
      tag.textContent = config.renderTags(item);
      nameLine.append(tag);

      const stats = document.createElement("div");
      stats.className = "loadout-stats muted";
      stats.textContent = config.renderStats(item);

      const desc = document.createElement("p");
      desc.className = "loadout-desc muted";
      desc.textContent = config.renderDesc(item);

      main.append(nameLine, stats, desc);
      row.append(icon, main);
      row.addEventListener("click", () => equip(slotIndex, item.id));
      li.append(row);
      list.append(li);
    }
    body.append(list);
  }

  function openSlotAction(slotIndex, item) {
    openModal(item.name);
    const body = $("loadout-modal-body");

    const tag = document.createElement("p");
    tag.className = "loadout-tag";
    tag.textContent = config.renderTags(item);
    const stats = document.createElement("p");
    stats.className = "loadout-stats muted";
    stats.textContent = config.renderStats(item);
    const desc = document.createElement("p");
    desc.className = "loadout-desc";
    desc.textContent = config.renderDesc(item);
    body.append(tag, stats, desc);

    const unequipBtn = document.createElement("button");
    unequipBtn.type = "button";
    unequipBtn.className = "loadout-action-button";
    unequipBtn.textContent = "Unequip";
    unequipBtn.addEventListener("click", () => unequip(slotIndex));
    body.append(unequipBtn);

    const others = data.slots.filter((s) => s.index !== slotIndex);
    if (others.length) {
      const heading = document.createElement("p");
      heading.className = "muted loadout-swap-heading";
      heading.textContent = "Move or swap with another slot:";
      body.append(heading);

      const miniGrid = document.createElement("div");
      miniGrid.className = "slot-grid slot-grid-mini";
      for (const other of others) {
        const otherItem = other[config.itemField];
        const cell = document.createElement("button");
        cell.type = "button";
        cell.className = "slot-square slot-square-mini" + (otherItem ? " filled" : " empty");
        if (otherItem) {
          const icon = document.createElement("span");
          icon.className = "slot-icon";
          icon.textContent = iconFor(otherItem);
          const name = document.createElement("span");
          name.className = "slot-name";
          name.textContent = otherItem.name;
          cell.append(icon, name);
          cell.title = `Swap with ${otherItem.name}`;
        } else {
          cell.textContent = "+";
          cell.title = "Move here";
        }
        cell.addEventListener("click", () => swap(slotIndex, other.index));
        miniGrid.append(cell);
      }
      body.append(miniGrid);
    }
  }

  // ---------- API ----------

  async function equip(slot, id) {
    try {
      const res = await authFetch(`${config.apiBase}/equip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot, [config.idField]: id }),
      });
      const body = await res.json();
      if (!res.ok) return notify(body && body.detail ? body.detail : "That didn't work.");
      data = body;
      closeModal();
      render();
    } catch {
      notify("Couldn't reach the server. Try again.");
    }
  }

  async function unequip(slot) {
    try {
      const res = await authFetch(`${config.apiBase}/unequip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot }),
      });
      const body = await res.json();
      if (!res.ok) return notify(body && body.detail ? body.detail : "That didn't work.");
      data = body;
      closeModal();
      render();
    } catch {
      notify("Couldn't reach the server. Try again.");
    }
  }

  async function swap(slotA, slotB) {
    try {
      const res = await authFetch(`${config.apiBase}/swap`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slot_a: slotA, slot_b: slotB }),
      });
      const body = await res.json();
      if (!res.ok) return notify(body && body.detail ? body.detail : "That didn't work.");
      data = body;
      closeModal();
      render();
    } catch {
      notify("Couldn't reach the server. Try again.");
    }
  }

  function notify(message) {
    const el = $("loadout-notice");
    el.textContent = message;
    el.className = "";
    clearTimeout(notify._t);
    notify._t = setTimeout(() => (el.className = "hidden"), 3500);
  }

  $("loadout-modal-close").addEventListener("click", closeModal);
  $("loadout-modal").addEventListener("click", (ev) => {
    if (ev.target === $("loadout-modal")) closeModal();
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") closeModal();
  });

  async function load() {
    const res = await authFetch(config.apiBase);
    data = await res.json();
    render();
  }

  if (requireAuthToken()) {
    load();
  }
}
