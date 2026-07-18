const profiles = [
  {
    id: "mdm-chen",
    name: "Mdm Chen Wei Ling",
    age: 68,
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Chen",
    location: "Bukit Merah",
    match: "92%",
    bio: "Passionate about learning technology and staying connected with family.",
    matched: ["Tech support", "Friendly learner", "Community-minded"],
    interests: ["WhatsApp", "Cooking", "Stories"],
    goals: ["Learn video calls", "Meet new friends"],
    teach: ["Traditional recipes"],
    learn: ["Social media basics"],
  },
  {
    id: "uncle-kumar",
    name: "Mr Kumar Raj",
    age: 72,
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Kumar",
    location: "Jurong East",
    match: "90%",
    bio: "Enjoys learning digital tools and meeting new people.",
    matched: ["Learning circles", "Helpful mentor", "Curious explorer"],
    interests: ["Instagram", "Photography", "Walking"],
    goals: ["Make new friends", "Learn social apps"],
    teach: ["Life stories", "Cooking tips"],
    learn: ["Digital payments"],
  },
];

let index = 0;
let lastConnectedProfile = null;

const card = document.getElementById("card");
const avatar = document.querySelector(".avatar");
const nameEl = document.querySelector(".name");
const locationEl = document.querySelector(".location");
const matchEl = document.querySelector(".match-value");
const bioEl = document.querySelector(".bio");

const matchedTags = document.getElementById("matchedTags");
const interestTags = document.getElementById("interestTags");
const goalsList = document.getElementById("goalsList");
const teachTags = document.getElementById("teachTags");
const learnTags = document.getElementById("learnTags");

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
const matchesGrid = document.getElementById("matchesGrid");
const discoverBtn = document.getElementById("discoverBtn");
const discoverPanel = document.getElementById("discoverPanel");
const matchesHeader = document.getElementById("matchesHeader");

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

// API matches
async function apiListMatches() {
  const res = await fetch("/sean/api/matches");
  if (!res.ok) throw new Error("Failed to load matches");
  return await res.json();
}

// API create
async function apiCreateMatch(profile) {
  const res = await fetch("/sean/api/matches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const res = await fetch(`/sean/api/matches/${encodeURIComponent(matchId)}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete match");
  return await res.json();
}

// API clear
async function apiClearMatches() {
  const res = await fetch("/sean/api/matches", { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to clear matches");
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

// Render goals
function renderGoals(container, list) {
  container.innerHTML = "";
  (list || []).forEach((g) => {
    const li = document.createElement("li");
    li.textContent = g;
    container.appendChild(li);
  });
}

// Load profile
function loadProfile() {
  const p = profiles[index];
  avatar.src = p.avatar;
  nameEl.textContent = `${p.name}, ${p.age}`;
  locationEl.textContent = p.location;
  matchEl.textContent = p.match;
  bioEl.textContent = `"${p.bio}"`;

  renderTags(matchedTags, p.matched);
  renderTags(interestTags, p.interests);
  renderGoals(goalsList, p.goals);
  renderTags(teachTags, p.teach);
  renderTags(learnTags, p.learn);
}

// Next profile
function nextProfile() {
  index = (index + 1) % profiles.length;
  loadProfile();
}

// Match count
async function refreshMatchCount() {
  try {
    const matches = await apiListMatches();
    matchCount.textContent = String(matches.length);
    matchesCount.textContent = String(matches.length);
    renderMatchesGrid(matches);
  } catch (e) {
    matchCount.textContent = "0";
    matchesCount.textContent = "0";
    renderMatchesGrid([]);
  }
}

function renderMatchesGrid(matches) {
  if (!matchesGrid) return;
  matchesGrid.innerHTML = "";
  if (!matches || matches.length === 0) {
    matchesGrid.innerHTML = `<div class="matches-empty">No matches yet. Click Connect to start matching.</div>`;
    return;
  }

  matches.forEach((m) => {
    const card = document.createElement("div");
    card.className = "matches-grid-card";
    card.innerHTML = `
      <div class="matches-avatar">
        <img src="${escapeHtml(m.avatar)}" alt="Avatar" />
      </div>
      <div class="matches-name">${escapeHtml(m.name)}</div>
      <div class="matches-location">${escapeHtml(m.location || "Available now")}</div>
      <div class="matches-tags">
        <span class="matches-pill">Match</span>
      </div>
      <button class="matches-cta">Say Hi</button>
    `;
    card.querySelector(".matches-cta").addEventListener("click", () => {
      window.location.href = `/sean/messages?chat=${encodeURIComponent(m.match_id)}`;
    });
    matchesGrid.appendChild(card);
  });
}

// Connect
async function connectProfile() {
  const p = profiles[index];
  try {
    await apiCreateMatch(p);
    lastConnectedProfile = p;
    localStorage.setItem("lastConnectedUser", p.id);

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

    matchesCount.textContent = String(matches.length);
    matchCount.textContent = String(matches.length);

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
        window.location.href = `/sean/messages?chat=${encodeURIComponent(m.match_id)}`;
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
    const chatId = lastConnectedProfile?.id || localStorage.getItem("lastConnectedUser");
    if (chatId) window.location.href = `/sean/messages?chat=${encodeURIComponent(chatId)}`;
    else window.location.href = "/sean/messages";
  });
}

if (matchesBtn) matchesBtn.addEventListener("click", openMatchesModal);
if (closeMatchesBtn) closeMatchesBtn.addEventListener("click", () => matchesModal.classList.remove("show"));
if (discoverBtn && card && discoverPanel) {
  discoverBtn.addEventListener("click", () => {
    discoverPanel.style.display = "flex";
    if (matchesHeader) matchesHeader.classList.remove("hidden");
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

if (matchesModal) {
  matchesModal.addEventListener("click", (e) => {
    if (e.target === matchesModal) matchesModal.classList.remove("show");
  });
}

if (resetBtn) {
  resetBtn.addEventListener("click", async () => {
    openModal({
      title: "Reset matches?",
      bodyHtml: `<div style="color: var(--muted-foreground); font-weight: 700;">This will remove all matches and messages.</div>`,
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
          closeModal();
        } catch (e) {
          alert("Could not reset.");
          console.error(e);
        }
      });
    }
  });
}

loadProfile();
refreshMatchCount();
