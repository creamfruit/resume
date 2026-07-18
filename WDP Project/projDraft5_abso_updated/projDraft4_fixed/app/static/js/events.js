(function () {
  const listEl = document.getElementById("events-list");
  const chipsWrapEl = document.getElementById("events-category-chips");
  const layoutEl = document.getElementById("events-layout");
  const mapPanelEl = document.getElementById("events-map-panel");
  const mapUnavailableEl = document.getElementById("events-map-unavailable");
  const mapEl = document.getElementById("events-map");

  let gMap = null;
  let lMap = null;
  let infoWindow = null;
  let markers = [];
  let markerByEventId = new Map();
  let activeCategory = "";
  let cachedEvents = [];
  let forceLeaflet = false;
  let busyEventId = null;

  function esc(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function toCoord(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function hasGoogleMaps() {
    return Boolean(!forceLeaflet && window.google && window.google.maps && typeof window.google.maps.Map === "function");
  }

  function hasLeaflet() {
    return Boolean(window.L && typeof window.L.map === "function");
  }

  function currentProvider() {
    if (hasGoogleMaps()) return "google";
    if (hasLeaflet()) return "leaflet";
    return "none";
  }

  function ensureMap() {
    const provider = currentProvider();
    if (provider === "none") return;

    if (provider === "google") {
      if (gMap) return;
      gMap = new window.google.maps.Map(mapEl, {
        center: { lat: 1.3521, lng: 103.8198 },
        zoom: 11,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
      });
      infoWindow = new window.google.maps.InfoWindow();
      return;
    }

    if (provider === "leaflet") {
      if (lMap) return;
      if (mapEl) mapEl.innerHTML = "";
      lMap = window.L.map("events-map", {
        center: [1.3521, 103.8198],
        zoom: 11,
        zoomControl: true,
      });
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(lMap);
    }
  }

  function clearMarkers() {
    markers.forEach((item) => {
      if (!item) return;
      if (item.provider === "google" && item.marker && typeof item.marker.setMap === "function") {
        item.marker.setMap(null);
      }
      if (item.provider === "leaflet" && lMap && item.marker) {
        lMap.removeLayer(item.marker);
      }
    });
    markers = [];
    markerByEventId = new Map();
  }

  function focusEventCard(eventId) {
    const card = listEl?.querySelector(`.event-card[data-event-id="${eventId}"]`);
    if (!card) return;
    listEl.querySelectorAll(".event-card").forEach((el) => el.classList.remove("active"));
    card.classList.add("active");
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function organiserBadge(eventItem) {
    const text = eventItem.verification_badge || "Admin Hosted";
    const t = String(eventItem.organiser_type || "").toLowerCase();
    const cls =
      t === "government"
        ? "badge badge-gov"
        : t === "corporate"
        ? "badge badge-corporate"
        : "badge";
    return `<span class="${cls}">${esc(text)}</span>`;
  }

  function formatDuration(startTime, endTime) {
    if (!startTime || !endTime) return "";
    const start = new Date(startTime);
    const end = new Date(endTime);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "";
    const mins = Math.max(0, Math.round((end.getTime() - start.getTime()) / 60000));
    if (!mins) return "";
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m ? `${h}h ${m}m` : `${h}h`;
  }

  async function rsvp(eventId, status) {
    const res = await fetch(`/api/events/${eventId}/rsvp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || "Could not update RSVP");
    }
  }

  async function checkin(eventId) {
    const res = await fetch(`/api/events/${eventId}/checkin`, { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || "Could not check in");
    }
  }

  function toast(message) {
    if (!listEl) return;
    const node = document.createElement("div");
    node.className = "empty-state";
    node.style.marginBottom = "0.6rem";
    node.textContent = message;
    listEl.prepend(node);
    setTimeout(() => node.remove(), 1400);
  }

  function showMapAvailability(hasPoints) {
    const provider = currentProvider();
    const canShow = hasPoints && provider !== "none";
    if (layoutEl) layoutEl.classList.toggle("no-map", !canShow);
    if (mapPanelEl) mapPanelEl.style.display = canShow ? "" : "none";
    if (mapUnavailableEl) {
      mapUnavailableEl.style.display = canShow ? "none" : "block";
      if (!hasPoints) {
        mapUnavailableEl.textContent = "Map is shown when events include valid coordinates.";
      } else if (provider === "none") {
        mapUnavailableEl.textContent = "Map provider unavailable. Check API key or network.";
      }
    }
  }

  function renderMarkers(events) {
    const withCoords = events
      .map((e) => {
        const lat = toCoord(e.lat);
        const lng = toCoord(e.lng);
        return lat === null || lng === null ? null : { ...e, lat, lng };
      })
      .filter(Boolean);

    showMapAvailability(withCoords.length > 0);
    if (!withCoords.length) {
      clearMarkers();
      return;
    }

    ensureMap();
    const provider = currentProvider();
    if (provider === "none") return;

    clearMarkers();

    if (provider === "google" && gMap) {
      const bounds = new window.google.maps.LatLngBounds();
      withCoords.forEach((e) => {
        const position = { lat: e.lat, lng: e.lng };
        const marker = new window.google.maps.Marker({ position, map: gMap, title: e.title || "Event" });
        marker.addListener("click", () => {
          if (infoWindow) {
            infoWindow.setContent(`<strong>${esc(e.title)}</strong><br>${esc(e.location_name || "")}`);
            infoWindow.open({ anchor: marker, map: gMap });
          }
          focusEventCard(Number(e.id));
        });
        markers.push({ provider: "google", marker });
        markerByEventId.set(Number(e.id), { provider: "google", marker, lat: e.lat, lng: e.lng });
        bounds.extend(position);
      });
      gMap.fitBounds(bounds);
      return;
    }

    if (provider === "leaflet" && lMap) {
      const bounds = [];
      withCoords.forEach((e) => {
        const marker = window.L.marker([e.lat, e.lng]).addTo(lMap);
        marker.bindPopup(`<strong>${esc(e.title)}</strong><br>${esc(e.location_name || "")}`);
        marker.on("click", () => focusEventCard(Number(e.id)));
        markers.push({ provider: "leaflet", marker });
        markerByEventId.set(Number(e.id), { provider: "leaflet", marker, lat: e.lat, lng: e.lng });
        bounds.push([e.lat, e.lng]);
      });
      if (bounds.length) {
        lMap.fitBounds(bounds, { padding: [24, 24] });
      }
    }
  }

  function panToEvent(eventId) {
    const ref = markerByEventId.get(Number(eventId));
    if (!ref) return;
    if (ref.provider === "google" && gMap && ref.marker) {
      gMap.panTo(ref.marker.getPosition());
      gMap.setZoom(Math.max(gMap.getZoom(), 13));
      return;
    }
    if (ref.provider === "leaflet" && lMap && ref.marker) {
      lMap.flyTo([ref.lat, ref.lng], Math.max(lMap.getZoom(), 13));
      ref.marker.openPopup();
    }
  }

  async function load(options) {
    const opts = options || {};
    if (!listEl) return;
    const beforeY = window.scrollY;
    listEl.innerHTML = "Loading events...";
    const category = (activeCategory || "").trim();
    const res = await fetch(`/api/events${category ? `?category=${encodeURIComponent(category)}` : ""}`);
    const data = await res.json().catch(() => ({ ok: false }));
    if (!res.ok || !data.ok) {
      listEl.innerHTML = "Could not load events.";
      showMapAvailability(false);
      return;
    }

    const events = Array.isArray(data.events) ? data.events : [];
    cachedEvents = events;

    if (!events.length) {
      listEl.innerHTML = '<div class="empty-state">No events found for this filter.</div>';
      clearMarkers();
      showMapAvailability(false);
      return;
    }

    listEl.innerHTML = events
      .map(
        (e) => `
      <article class="event-card" data-event-id="${e.id}">
        <h3 class="event-title">${esc(e.title)}</h3>
        <div class="event-meta">${esc(e.category)} · ${esc(e.start_time)}</div>
        <div class="event-badge-row">
          ${organiserBadge(e)}
          <span style="font-size:0.82rem;color:#334155;">${esc(e.organiser_name || "Re:Connect Admin")}</span>
        </div>
        <div style="font-size:0.88rem; margin-top:6px;">${esc(e.location_name || "")}</div>
        <p class="event-desc">${esc(e.description || "")}</p>
        <div class="event-micro-stats">
          ${e.capacity ? `<span>👥 ${esc(e.capacity)} capacity</span>` : ""}
          ${formatDuration(e.start_time, e.end_time) ? `<span>🕒 ${esc(formatDuration(e.start_time, e.end_time))}</span>` : ""}
          ${e.tags && e.tags.length ? `<span>⭐ ${esc(e.tags[0])}</span>` : ""}
        </div>
        <div class="event-actions">
          <button class="btn btn-primary events-cta" data-rsvp="${e.id}" data-status="going">✔️ RSVP Going</button>
          <button class="btn btn-secondary events-cta" data-rsvp="${e.id}" data-status="interested">⭐ Interested</button>
          <button class="btn btn-tertiary events-checkin-cta" data-checkin="${e.id}">📍 Check in</button>
        </div>
      </article>
    `
      )
      .join("");

    renderMarkers(events);
    if (opts.focusEventId) {
      focusEventCard(Number(opts.focusEventId));
      panToEvent(Number(opts.focusEventId));
    }
    if (opts.preserveScroll) {
      window.scrollTo({ top: beforeY, behavior: "auto" });
    }
  }

  listEl?.addEventListener("click", async (ev) => {
    const rsvpBtn = ev.target.closest("[data-rsvp]");
    if (rsvpBtn) {
      ev.preventDefault();
      ev.stopPropagation();
      const eventId = Number(rsvpBtn.getAttribute("data-rsvp"));
      if (busyEventId === eventId) return;
      busyEventId = eventId;
      rsvpBtn.disabled = true;
      const originalText = rsvpBtn.textContent;
      rsvpBtn.textContent = "Saving...";
      try {
        await rsvp(eventId, rsvpBtn.getAttribute("data-status"));
        await load({ preserveScroll: true, focusEventId: eventId });
        toast("RSVP updated");
      } catch (err) {
        window.alert(err.message || "Could not update RSVP");
      } finally {
        busyEventId = null;
        rsvpBtn.disabled = false;
        rsvpBtn.textContent = originalText;
      }
      return;
    }

    const checkinBtn = ev.target.closest("[data-checkin]");
    if (checkinBtn) {
      ev.preventDefault();
      ev.stopPropagation();
      const eventId = Number(checkinBtn.getAttribute("data-checkin"));
      if (busyEventId === eventId) return;
      busyEventId = eventId;
      checkinBtn.disabled = true;
      const originalText = checkinBtn.textContent;
      checkinBtn.textContent = "Checking in...";
      try {
        await checkin(eventId);
        await load({ preserveScroll: true, focusEventId: eventId });
        toast("Check-in recorded");
      } catch (err) {
        window.alert(err.message || "Could not check in");
      } finally {
        busyEventId = null;
        checkinBtn.disabled = false;
        checkinBtn.textContent = originalText;
      }
      return;
    }

    const card = ev.target.closest(".event-card[data-event-id]");
    if (!card) return;
    listEl.querySelectorAll(".event-card").forEach((el) => el.classList.remove("active"));
    card.classList.add("active");
    panToEvent(Number(card.getAttribute("data-event-id")));
  });

  chipsWrapEl?.addEventListener("click", (ev) => {
    const chip = ev.target.closest("[data-category]");
    if (!chip) return;
    activeCategory = chip.getAttribute("data-category") || "";
    chipsWrapEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    load({ preserveScroll: true });
  });

  window.gm_authFailure = function gm_authFailure() {
    forceLeaflet = true;
    if (mapEl) mapEl.innerHTML = "";
    gMap = null;
    infoWindow = null;
    renderMarkers(cachedEvents || []);
  };

  window.initEventsMap = function initEventsMap() {
    ensureMap();
    load();
  };

  if (hasGoogleMaps()) {
    window.initEventsMap();
  } else {
    load();
  }
})();
