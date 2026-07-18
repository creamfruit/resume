const STATIC_PROFILES = [];

let index = 0;
let lastConnectedProfile = null;
let lastConnectedMatchId = null;
let currentSort = "default";
let userStations = [];

const MRT_STATIONS = [
  "Admiralty","Aljunied","Ang Mo Kio","Boon Lay","Braddell","Bishan","Bugis","Buangkok","Bukit Batok","Bukit Gombak",
  "Buona Vista","Changi Airport","Chinatown","Choa Chu Kang","City Hall","Clarke Quay","Clementi","Dover","Dhoby Ghaut",
  "Eunos","Hougang","Jurong East","Kallang","Kembangan","Khatib","Kranji","Lakeside","Lavender","Marymount","Novena",
  "Orchard","Outram Park","Paya Lebar","Potong Pasir","Pasir Ris","Punggol","Queenstown","Raffles Place","Redhill",
  "Serangoon","Sengkang","Somerset","Tai Seng","Tampines","Tanjong Pagar","Telok Ayer","Toa Payoh","Woodlands","Yishun"
];

let profiles = [];
let displayProfiles = [];

const card = document.getElementById("card");
const avatar = document.querySelector(".avatar");
const nameEl = document.querySelector(".name");
const locationEl = document.querySelector(".location");
const matchEl = document.querySelector(".match-value");
const bioEl = document.querySelector(".bio");

const matchedTags = document.getElementById("matchedTags");
const interestTags = document.getElementById("interestTags");
const teachTags = document.getElementById("teachTags");
const learnTags = document.getElementById("learnTags");
const availabilityStatusEl = document.querySelector(".availability-status");

const connectBtn = document.getElementById("connectBtn");
const passBtn = document.getElementById("passBtn");

const matchModal = document.getElementById("matchModal");
const matchedName = document.getElementById("matchedName");
const sendMessageBtn = document.getElementById("sendMessageBtn");
const keepSwipingBtn = document.getElementById("keepSwipingBtn");

const matchesBtn = document.getElementById("matchesBtn");
const resetBtn = document.getElementById("resetBtn");

const matchesModal = document.getElementById("matchesModal");
const closeMatchesBtn = document.getElementById("closeMatchesBtn");
const matchesList = document.getElementById("matchesList");
const matchesCount = document.getElementById("matchesCount");
const matchCount = document.getElementById("matchCount");
const filterButtons = document.querySelectorAll(".filter-btn");

const uiModal = document.getElementById("ui-modal");
const uiModalTitle = document.getElementById("ui-modal-title");
const uiModalBody = document.getElementById("ui-modal-body");
const uiModalActions = document.getElementById("ui-modal-actions");
const uiModalClose = document.getElementById("ui-modal-close");

// Modal open
function openModal({ title, bodyHtml, actionsHtml }) {
  if (!uiModal || !uiModalTitle || !uiModalBody || !uiModalActions) return;
  uiModalTitle.textContent = title;
  uiModalBody.innerHTML = bodyHtml;
  uiModalActions.innerHTML = actionsHtml;
  uiModal.classList.add("show");
}

// Modal close
function closeModal() {
  if (!uiModal) return;
  uiModal.classList.remove("show");
}

if (uiModalClose) uiModalClose.addEventListener("click", closeModal);
if (uiModal) {
  uiModal.addEventListener("click", (e) => {
    if (e.target === uiModal) closeModal();
  });
}

// HTML escape
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function demoHeaders(extra) {
  const headers = extra ? { ...extra } : {};
  const demoId = sessionStorage.getItem("demo_user_id");
  if (demoId) headers["X-Demo-User"] = demoId;
  return headers;
}

function stationIndex(name) {
  if (!name) return -1;
  return MRT_STATIONS.indexOf(String(name).trim());
}

function profileStations(profile) {
  const raw = profile?.stations;
  if (Array.isArray(raw) && raw.length) return raw;
  if (profile?.location) return [profile.location];
  return [];
}

function distanceToUser(profile) {
  const u = userStations || [];
  const p = profileStations(profile);
  if (!u.length || !p.length) return Number.POSITIVE_INFINITY;
  let best = Number.POSITIVE_INFINITY;
  u.forEach((uStation) => {
    const ui = stationIndex(uStation);
    if (ui < 0) return;
    p.forEach((pStation) => {
      const pi = stationIndex(pStation);
      if (pi < 0) return;
      const d = Math.abs(ui - pi);
      if (d < best) best = d;
    });
  });
  return best;
}

function compatibilityScore(profile) {
  const raw = String(profile?.match || "").replace("%", "");
  const val = parseInt(raw, 10);
  return Number.isNaN(val) ? 0 : val;
}

function sortProfiles(list, mode) {
  const sorted = list.slice();
  if (mode === "distance") {
    sorted.sort((a, b) => {
      const da = distanceToUser(a);
      const db = distanceToUser(b);
      if (da === db) return (a._sortIndex || 0) - (b._sortIndex || 0);
      return da - db;
    });
  } else if (mode === "compatibility") {
    sorted.sort((a, b) => {
      const ca = compatibilityScore(a);
      const cb = compatibilityScore(b);
      if (cb === ca) return (a._sortIndex || 0) - (b._sortIndex || 0);
      return cb - ca;
    });
  }
  return sorted;
}

function applySort(mode) {
  currentSort = mode || "default";
  displayProfiles = sortProfiles(profiles, currentSort);
  index = 0;
  updateFilterButtons();
  loadProfile();
}

function updateFilterButtons() {
  filterButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.sort === currentSort);
  });
}

async function loadUserStations() {
  try {
    const res = await fetch("/api/profile", { headers: demoHeaders() });
    if (!res.ok) return;
    const out = await res.json().catch(() => ({}));
    const onboarding = out?.profile?.onboarding || {};
    userStations = Array.isArray(onboarding.stations) ? onboarding.stations : [];
  } catch (e) {
  }
}

async function loadProfiles() {
  let combined = [];
  try {
    const res = await fetch("/api/matching/profiles", { headers: demoHeaders() });
    if (res.ok) {
      const out = await res.json().catch(() => ({}));
      const real = Array.isArray(out.profiles) ? out.profiles : [];
      if (real.length) {
        combined = real;
      }
    }
  } catch (e) {
  }
  profiles = combined.map((p, idx) => ({ ...p, _sortIndex: idx }));
}

// API matches
async function apiListMatches() {
  const res = await fetch("/api/matches", { headers: demoHeaders() });
  if (!res.ok) throw new Error("Failed to load matches");
  return await res.json();
}

// API create
async function apiCreateMatch(profile) {
  const res = await fetch("/api/matches", {
    method: "POST",
    headers: demoHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      match_id: profile.id,
      name: profile.name,
      avatar: profile.avatar,
      location: profile.location || "",
    }),
  });
  if (!res.ok) throw new Error("Failed to create match");
  return await res.json();
}

// API delete
async function apiDeleteMatch(matchId) {
  const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}`, {
    method: "DELETE",
    headers: demoHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete match");
  return await res.json();
}

// API clear
async function apiClearMatches() {
  const res = await fetch("/api/matches", { method: "DELETE", headers: demoHeaders() });
  if (!res.ok) throw new Error("Failed to clear matches");
  return await res.json();
}

async function apiSendMatchRequest(receiverId) {
  const res = await fetch("/api/match_requests", {
    method: "POST",
    headers: demoHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ receiver_id: receiverId }),
  });
  if (!res.ok) throw new Error("Failed to send match request");
  return await res.json();
}

// Render tags
function renderTags(container, list) {
  container.innerHTML = "";
  (list || []).forEach((t) => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = t;
    container.appendChild(span);
  });
}

// Load profile
function loadProfile() {
  const p = displayProfiles[index];
  if (!p) {
    if (nameEl) nameEl.textContent = "No profiles yet";
    if (locationEl) locationEl.textContent = "";
    if (matchEl) matchEl.textContent = "";
    if (bioEl) bioEl.textContent = "";
    renderTags(matchedTags, []);
    renderTags(interestTags, []);
    renderTags(teachTags, []);
    renderTags(learnTags, []);
    if (availabilityStatusEl) availabilityStatusEl.textContent = "🕐 Availability not set";
    return;
  }
  avatar.src = p.avatar;
  const memberLabel = (p.member_label || "").trim();
  nameEl.textContent = memberLabel ? `${p.name}, ${memberLabel}` : `${p.name}`;
  locationEl.textContent = p.location || "Hidden";
  matchEl.textContent = p.match;
  bioEl.textContent = `"${p.bio}"`;

  renderTags(matchedTags, p.matched);
  renderTags(interestTags, p.interests);
  renderTags(teachTags, p.teach);
  renderTags(learnTags, p.learn);
  if (availabilityStatusEl) availabilityStatusEl.textContent = `🕐 ${p.availability || "Availability not set"}`;

  if (sendMessageBtn) {
    const directAllowed = p.allow_direct !== false;
    sendMessageBtn.disabled = !directAllowed;
    sendMessageBtn.title = directAllowed ? "" : "Direct messages are disabled by this user.";
  }
}

// Next profile
function nextProfile() {
  if (!displayProfiles.length) return;
  index = (index + 1) % displayProfiles.length;
  loadProfile();
}

// Match count
async function refreshMatchCount() {
  try {
    const matches = await apiListMatches();
    if (matchCount) matchCount.textContent = String(matches.length);
    if (matchesCount) matchesCount.textContent = String(matches.length);
  } catch (e) {
    if (matchCount) matchCount.textContent = "0";
    if (matchesCount) matchesCount.textContent = "0";
  }
}

// Connect
async function connectProfile() {
  const p = displayProfiles[index];
  if (!p) return;
  try {
    if (p.is_real && p.user_id) {
      await apiSendMatchRequest(p.user_id);
      openModal({
        title: "Match request sent",
        bodyHtml: `<div style="color: var(--muted-foreground); font-weight: 700;">We'll notify you when they respond.</div>`,
        actionsHtml: `<button class="ui-btn primary" id="modal-ok">OK</button>`,
      });
      const ok = document.getElementById("modal-ok");
      if (ok) ok.addEventListener("click", closeModal);
      nextProfile();
      return;
    }

    const saved = await apiCreateMatch(p);
    lastConnectedProfile = p;
    lastConnectedMatchId = saved?.match_id || null;
    localStorage.setItem("lastConnectedUser", lastConnectedMatchId || p.id);

    matchedName.textContent = p.name;
    matchModal.classList.add("show");

    await refreshMatchCount();
  } catch (e) {
    alert("Could not save match. Check Flask is running.");
    console.error(e);
  }
}

// Pass
function passProfile() {
  nextProfile();
}

// Matches modal
async function openMatchesModal() {
  try {
    const matches = await apiListMatches();
    matchesList.innerHTML = "";

    if (matchesCount) matchesCount.textContent = String(matches.length);
    if (matchCount) matchCount.textContent = String(matches.length);

    if (matches.length === 0) {
      matchesList.innerHTML = `
        <div style="padding: 12px; color: #7f8c8d; font-size: 14px;">
          No matches yet. Click ❤ Connect to save a match.
        </div>
      `;
      matchesModal.classList.add("show");
      return;
    }

    matches.forEach((m) => {
      const item = document.createElement("div");
      item.className = "match-item";

      item.innerHTML = `
        <img class="avatar" src="${escapeHtml(m.avatar)}" alt="Avatar" />
        <div class="match-item-info">
          <div class="match-item-name">${escapeHtml(m.name)}</div>
          <div class="match-item-location">${escapeHtml(m.location || "")}</div>
        </div>
        <div class="match-actions">
          <button class="match-action-btn message-btn" data-chat="${escapeHtml(m.match_id)}">Chat</button>
          <button class="match-action-btn unmatch-btn" data-del="${escapeHtml(m.match_id)}">Delete</button>
        </div>
      `;

      item.querySelector("[data-chat]").addEventListener("click", () => {
        window.location.href = `/messages?chat=${encodeURIComponent(m.match_id)}`;
      });

      item.querySelector("[data-del]").addEventListener("click", async () => {
        const ok = confirm("Delete this match?");
        if (!ok) return;
        try {
          await apiDeleteMatch(m.match_id);
          await openMatchesModal();
          await refreshMatchCount();
        } catch (e) {
          alert("Could not delete match.");
          console.error(e);
        }
      });

      matchesList.appendChild(item);
    });

    matchesModal.classList.add("show");
  } catch (e) {
    alert("Could not load matches. Check Flask is running.");
    console.error(e);
  }
}

if (connectBtn) connectBtn.addEventListener("click", connectProfile);
if (passBtn) passBtn.addEventListener("click", passProfile);

if (keepSwipingBtn) {
  keepSwipingBtn.addEventListener("click", () => {
    matchModal.classList.remove("show");
    nextProfile();
  });
}

if (sendMessageBtn) {
  sendMessageBtn.addEventListener("click", () => {
    const chatId = lastConnectedMatchId || localStorage.getItem("lastConnectedUser");
    if (chatId) window.location.href = `/messages?chat=${encodeURIComponent(chatId)}`;
    else window.location.href = "/messages";
  });
}

if (matchesBtn) matchesBtn.addEventListener("click", openMatchesModal);
if (closeMatchesBtn) closeMatchesBtn.addEventListener("click", () => matchesModal.classList.remove("show"));

if (matchesModal) {
  matchesModal.addEventListener("click", (e) => {
    if (e.target === matchesModal) matchesModal.classList.remove("show");
  });
}

if (resetBtn) {
  resetBtn.addEventListener("click", async () => {
    openModal({
      title: "Reset matches?",
      bodyHtml: `<div style="color: var(--muted-foreground); font-weight: 700;">This will remove all saved matches.</div>`,
      actionsHtml: `
        <button class="ui-btn" id="modal-cancel">Cancel</button>
        <button class="ui-btn danger" id="modal-reset">Reset</button>
      `,
    });

    const cancel = document.getElementById("modal-cancel");
    const confirmReset = document.getElementById("modal-reset");
    if (cancel) cancel.addEventListener("click", closeModal);
    if (confirmReset) {
      confirmReset.addEventListener("click", async () => {
        try {
          await apiClearMatches();
          localStorage.removeItem("lastConnectedUser");
          await refreshMatchCount();
          index = 0;
          applySort(currentSort);
          closeModal();
        } catch (e) {
          alert("Could not reset.");
          console.error(e);
        }
      });
    }
  });
}

filterButtons.forEach((btn) => {
  btn.addEventListener("click", () => applySort(btn.dataset.sort || "default"));
});

async function initMatching() {
  await loadUserStations();
  await loadProfiles();
  applySort(currentSort);
  refreshMatchCount();
}

initMatching();


