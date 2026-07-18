(function () {
  const listEl = document.getElementById("hangouts-list");
  const categoryChipsEl = document.getElementById("hangouts-category-chips");
  const attrChipsEl = document.getElementById("hangouts-attr-chips");
  const map = L.map("hangouts-map").setView([1.3521, 103.8198], 11);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  let markers = [];
  let activeCategory = "";
  let activeAttrs = new Set();

  function esc(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function clearMarkers() {
    markers.forEach((m) => m.remove());
    markers = [];
  }

  function sourcePillClass(sourceType) {
    const s = String(sourceType || "").toLowerCase();
    if (s === "government") return "pill pill--gov";
    if (s === "corporate") return "pill pill--corp";
    if (s === "community") return "pill pill--community";
    return "pill";
  }

  async function load() {
    if (!listEl) return;
    listEl.innerHTML = "Loading spots...";
    const category = (activeCategory || "").trim();
    const res = await fetch(`/api/hangouts${category ? `?category=${encodeURIComponent(category)}` : ""}`);
    const data = await res.json().catch(() => ({ ok: false }));
    if (!res.ok || !data.ok) {
      listEl.innerHTML = "Could not load spots.";
      return;
    }
    let spots = Array.isArray(data.spots) ? data.spots : [];
    if (activeAttrs.size) {
      spots = spots.filter((s) => {
        const a = s.accessibility || {};
        for (const key of activeAttrs) {
          if (!a[key]) return false;
        }
        return true;
      });
    }
    if (!spots.length) {
      listEl.innerHTML = '<div class="empty-state">No spots match the selected filters.</div>';
      clearMarkers();
      return;
    }
    listEl.innerHTML = spots.map((s) => `
      <article class="spot-card">
        <strong>${esc(s.name)}</strong>
        <div style="font-size:0.85rem; color:#64748b;">${esc(s.category)} · ${esc(s.mrt_nearby || "")}</div>
        <div style="margin:0.2rem 0;display:flex;gap:0.35rem;flex-wrap:wrap;align-items:center;">
          ${s.is_verified ? `<span class="pill pill--verified">${esc(s.verified_label || "Community-Verified Venue")}</span>` : ""}
          <span class="${sourcePillClass(s.source_type)}">${esc((s.source_type || "user").replace("_", " "))}</span>
        </div>
        <p style="margin:0.35rem 0; color:#475569;">${esc(s.description || "")}</p>
      </article>
    `).join("");
    clearMarkers();
    spots.forEach((s) => {
      if (typeof s.lat !== "number" || typeof s.lng !== "number") return;
      const marker = L.marker([s.lat, s.lng]).addTo(map).bindPopup(`<strong>${esc(s.name)}</strong><br>${esc(s.category || "")}`);
      markers.push(marker);
    });
  }

  categoryChipsEl?.addEventListener("click", (ev) => {
    const chip = ev.target.closest("[data-category]");
    if (!chip) return;
    activeCategory = chip.getAttribute("data-category") || "";
    categoryChipsEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    load();
  });

  attrChipsEl?.addEventListener("click", (ev) => {
    const chip = ev.target.closest("[data-attr]");
    if (!chip) return;
    const attr = chip.getAttribute("data-attr");
    if (!attr) return;
    if (activeAttrs.has(attr)) {
      activeAttrs.delete(attr);
      chip.classList.remove("active");
    } else {
      activeAttrs.add(attr);
      chip.classList.add("active");
    }
    load();
  });
  load();
})();
