document.addEventListener("DOMContentLoaded", function () {
  const backBtn = document.getElementById("back-btn");
  if (backBtn) backBtn.addEventListener("click", () => window.location.href = "/dashboard");


  const conversationsListEl = document.getElementById("conversations-list");
  const searchInput = document.getElementById("search-conversations");

  const chatMessages = document.getElementById("chat-messages");
  const headerName = document.getElementById("chat-name");
  const headerAvatar = document.getElementById("chat-avatar");

  const messageInput = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");
  const setMeetupBtn = document.getElementById("set-meetup-btn");
  const starterBtn = document.getElementById("starter-btn");
  const starterPopup = document.getElementById("starter-popup");

  const params = new URLSearchParams(window.location.search);
  const urlChatId = params.get("chat");

  let activeChatId = null;
  let matchesCache = [];
  let profanityPatterns = [];
  let currentUser = { user_id: null, name: "User", role: "youth" };
  let ownSenderRole = "youth";

  const uiModal = document.getElementById("ui-modal");
  const uiModalTitle = document.getElementById("ui-modal-title");
  const uiModalBody = document.getElementById("ui-modal-body");
  const uiModalActions = document.getElementById("ui-modal-actions");
  const uiModalClose = document.getElementById("ui-modal-close");

  const plantBuddy = document.getElementById("plant-buddy");
  const plantIcon = document.getElementById("plant-icon");
  const plantStreak = document.getElementById("plant-streak");
  const plantProgressFill = document.getElementById("plant-progress-fill");
  const csrfToken = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";

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
    div.textContent = text ?? "";
    return div.innerHTML;
  }

  function demoHeaders(extra) {
    const headers = extra ? { ...extra } : {};
    const demoId = sessionStorage.getItem("demo_user_id");
    if (demoId) headers["X-Demo-User"] = demoId;
    return headers;
  }

  function csrfHeaders(extra) {
    const headers = demoHeaders(extra);
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
    return headers;
  }

  function normalizeSenderRole(roleValue) {
    const role = String(roleValue || "").trim().toLowerCase();
    if (role === "elderly" || role === "senior" || role === "old" || role === "older") return "elderly";
    return "youth";
  }

  // Time format
  function formatTimeFromISO(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    let hours = d.getHours();
    const minutes = d.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    const minutesStr = minutes < 10 ? "0" + minutes : minutes;
    return `${hours}:${minutesStr} ${ampm}`;
  }

  function parseMeetupMarker(text) {
    const m = String(text || "").trim().match(/^__MEETUP__:(\d+)$/);
    return m ? Number(m[1]) : null;
  }

  function extractOtherUserId(chatId) {
    const raw = String(chatId || "").trim();
    if (!raw) return null;
    let m = raw.match(/^(\d+):user-(\d+)$/);
    if (m) return Number(m[2]);
    m = raw.match(/^dm:(\d+)-(\d+)$/);
    if (m && currentUser.user_id) {
      const a = Number(m[1]);
      const b = Number(m[2]);
      if (a === Number(currentUser.user_id)) return b;
      if (b === Number(currentUser.user_id)) return a;
    }
    return null;
  }

  // Regex escape
  function escapeRegex(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Build patterns
  function buildProfanityPatterns(list) {
    profanityPatterns = (list || []).map((item) => {
      const raw = (item.word || "").trim();
      if (!raw) return null;
      const pattern = raw.includes(" ")
        ? `\\b${escapeRegex(raw).replace(/\s+/g, "\\s+")}\\b`
        : `\\b${escapeRegex(raw)}\\b`;
      return new RegExp(pattern, "gi");
    }).filter(Boolean);
  }

  // Censor text
  function censorText(text) {
    if (!text || profanityPatterns.length === 0) return text;
    let output = text;
    profanityPatterns.forEach((pattern) => {
      output = output.replace(pattern, (match) => "*".repeat(match.length));
    });
    return output;
  }

  function isDemoUser() {
    const name = currentUser && currentUser.name ? currentUser.name : "";
    return name.trim().toLowerCase() === "demo user";
  }

  function hasBlockedProfanity(text) {
    if (!text || profanityPatterns.length === 0) return false;
    return profanityPatterns.some((pattern) => {
      pattern.lastIndex = 0;
      return pattern.test(text);
    });
  }

  function showProfanityBlock(text) {
    if (activeChatId) {
      apiReportProfanityBlock(activeChatId, text || "").catch((e) => {
        console.error(e);
      });
    }
    if (uiModal && typeof openModal === "function") {
      openModal({
        title: "Please be kind",
        bodyHtml: "<p style=\"margin:0;\">That message includes blocked words. Keep it respectful.</p>",
        actionsHtml: "<button class=\"ui-btn primary\" id=\"modal-ok\">OK</button>",
      });
      const ok = document.getElementById("modal-ok");
      if (ok) ok.addEventListener("click", closeModal);
      return;
    }
    alert("That message includes blocked words. Please be kind.");
  }

  // API matches
  async function apiListMatches() {
    const res = await fetch("/api/matches", { headers: csrfHeaders() });
    if (!res.ok) throw new Error("Failed to load matches");
    return await res.json();
  }

  function closeStarterPopup() {
    if (!starterPopup) return;
    starterPopup.classList.remove("show");
    starterPopup.setAttribute("aria-hidden", "true");
  }

  function openStarterPopup() {
    if (!starterPopup) return;
    starterPopup.classList.add("show");
    starterPopup.setAttribute("aria-hidden", "false");
  }

  async function apiMatchOverview(chatId) {
    const res = await fetch(`/api/matches/${encodeURIComponent(chatId)}/overview`, { headers: csrfHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || "Failed to load overview");
    return data.profile || null;
  }

  // API messages
  async function apiListMessages(chatId) {
    const res = await fetch(`/api/messages/${encodeURIComponent(chatId)}`, { headers: csrfHeaders() });
    if (!res.ok) throw new Error("Failed to load messages");
    return await res.json();
  }

  async function apiGetPairPlant(otherUserId) {
    const safeId = Number(otherUserId);
    if (!Number.isInteger(safeId) || safeId <= 0) throw new Error("Invalid user_id");
    const res = await fetch(`/api/plants/pair?user_id=${encodeURIComponent(String(safeId))}`, { headers: demoHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || "Failed to load plant");
    return data.plant || null;
  }

  // API send
  async function apiCreateMessage(chatId, sender, text) {
    const res = await fetch(`/api/messages/${encodeURIComponent(chatId)}`, {
      method: "POST",
      headers: csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ sender, text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Failed to send message");
    return data;
  }

  async function apiCreateMeetup(payload) {
    const res = await fetch("/api/meetups", {
      method: "POST",
      headers: csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || "Failed to create meetup");
    return data;
  }

  async function apiGetMeetup(meetupId) {
    const res = await fetch(`/api/meetups/${encodeURIComponent(meetupId)}`, { headers: csrfHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.error || "Failed to load meetup");
    return data.meetup;
  }

  async function apiMeetupAction(meetupId, action, body) {
    const res = await fetch(`/api/meetups/${encodeURIComponent(meetupId)}/${action}`, {
      method: "POST",
      headers: csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || `Failed to ${action}`);
    return data;
  }

  async function apiReportProfanityBlock(chatId, text) {
    const res = await fetch("/api/profanity-block", {
      method: "POST",
      headers: csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    if (!res.ok) throw new Error("Failed to report blocked profanity");
    return await res.json();
  }

  // API profanities
  async function apiListProfanities() {
    const res = await fetch("/api/profanities");
    if (!res.ok) throw new Error("Failed to load profanities");
    return await res.json();
  }

  // API session
  async function apiGetSession() {
    const res = await fetch("/api/session", { headers: csrfHeaders() });
    if (!res.ok) return null;
    return await res.json();
  }

  // API edit
  async function apiUpdateMessage(messageId, text) {
    const res = await fetch(`/api/messages/${messageId}`, {
      method: "PUT",
      headers: csrfHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error("Failed to edit message");
    return await res.json();
  }

  // API delete
  async function apiDeleteMessage(messageId) {
    const res = await fetch(`/api/messages/${messageId}`, { method: "DELETE", headers: csrfHeaders() });
    if (!res.ok) throw new Error("Failed to delete message");
    return await res.json();
  }

  // API restore
  async function apiRestoreMessage(messageId) {
    const res = await fetch(`/api/messages/${messageId}/restore`, { method: "POST", headers: csrfHeaders() });
    if (!res.ok) throw new Error("Failed to restore message");
    return await res.json();
  }

  // Sidebar state
  function setActiveSidebar(chatId) {
    document.querySelectorAll(".conversation-item").forEach((item) => {
      item.classList.toggle("active", item.dataset.chat === chatId);
    });
  }

  function updatePlantUI(plant) {
    if (!plantIcon || !plantStreak || !plantProgressFill) return;
    const stage = Math.max(1, Math.min(7, Number(plant && plant.stage ? plant.stage : 1)));
    const streak = Math.max(0, Number(plant && plant.streak ? plant.streak : 0));
    const progressPct = Math.max(0, Math.min(100, Number(plant && plant.progressPct ? plant.progressPct : 0)));

    plantIcon.className = `plant-icon stage-${stage}`;
    plantStreak.textContent = `🔥 Streak: ${streak} day${streak === 1 ? "" : "s"}`;
    plantProgressFill.style.width = `${progressPct}%`;
  }

  function showPlantToast(plant) {
    if (!plant || !plant.changed) return;
    const gainedXp = Number(plant.gained_xp || 0);
    const toast = document.createElement("div");
    toast.className = "plant-toast";
    toast.textContent = `🔥 Streak +1${gainedXp > 0 ? ` • +${gainedXp} XP` : ""}`;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.classList.add("show"), 10);
    window.setTimeout(() => {
      toast.classList.remove("show");
      window.setTimeout(() => toast.remove(), 260);
    }, 2200);
  }

  async function refreshPairPlant(chatId) {
    if (!plantBuddy) return;
    const otherUserId = extractOtherUserId(chatId);
    if (!otherUserId) {
      updatePlantUI({ stage: 1, streak: 0, progressPct: 0 });
      return;
    }
    try {
      const plant = await apiGetPairPlant(otherUserId);
      if (plant) updatePlantUI(plant);
    } catch (_) {
      updatePlantUI({ stage: 1, streak: 0, progressPct: 0 });
    }
  }

  // Render list
  function renderConversationList(list) {
    if (!conversationsListEl) return;
    conversationsListEl.innerHTML = "";

    if (!list || list.length === 0) {
      conversationsListEl.innerHTML = `
        <div style="padding: 1rem; color: var(--muted-foreground); font-size: 0.92rem; line-height:1.5;">
          No conversations yet.<br/>
          Your connections will appear here.
        </div>
      `;
      return;
    }

    list.forEach((m) => {
      const item = document.createElement("div");
      item.className = "conversation-item";
      item.dataset.chat = m.match_id;

      item.innerHTML = `
        <img src="${escapeHtml(m.avatar)}" alt="${escapeHtml(m.name)}" class="conversation-avatar">
        <div class="conversation-info">
          <div class="conversation-header">
            <h4>${escapeHtml(m.name)}</h4>
            <span class="conversation-time"></span>
          </div>
          <p class="conversation-preview">${escapeHtml(m.location || "Tap to chat")}</p>
        </div>
      `;

      item.addEventListener("click", () => openChat(m.match_id));
      conversationsListEl.appendChild(item);
    });
  }

  // Message actions
  function attachMessageHandlers() {
    if (!chatMessages) return;

    chatMessages.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-edit");
        const raw = btn.getAttribute("data-text");
        const currentText = raw ? decodeURIComponent(raw) : btn.closest(".message-content").querySelector("p").textContent;

        openModal({
          title: "Edit message",
          bodyHtml: `<textarea class="ui-textarea" id="edit-textarea">${escapeHtml(currentText)}</textarea>`,
          actionsHtml: `
            <button class="ui-btn" id="modal-cancel">Cancel</button>
            <button class="ui-btn primary" id="modal-save">Save</button>
          `,
        });

        const cancel = document.getElementById("modal-cancel");
        const save = document.getElementById("modal-save");

        if (cancel) cancel.addEventListener("click", closeModal);
        if (save) {
          save.addEventListener("click", async () => {
            const next = (document.getElementById("edit-textarea").value || "").trim();
            if (!next) {
              alert("Message cannot be empty.");
              return;
            }
            if (isDemoUser() && hasBlockedProfanity(next)) {
              showProfanityBlock(next);
              return;
            }

            try {
              await apiUpdateMessage(id, next);
              closeModal();
              await loadAndRenderChat(activeChatId);
            } catch (e) {
              alert("Could not edit message.");
              console.error(e);
            }
          });
        }
      });
    });

    chatMessages.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-del");

        openModal({
          title: "Delete message?",
          bodyHtml: `<div style="color: var(--muted-foreground); font-weight: 700;">This will remove the message. You can undo immediately.</div>`,
          actionsHtml: `
            <button class="ui-btn" id="modal-cancel">Cancel</button>
            <button class="ui-btn danger" id="modal-delete">Delete</button>
          `,
        });

        const cancel = document.getElementById("modal-cancel");
        const del = document.getElementById("modal-delete");

        if (cancel) cancel.addEventListener("click", closeModal);
        if (del) {
          del.addEventListener("click", async () => {
            try {
              await apiDeleteMessage(id);
              closeModal();
              await loadAndRenderChat(activeChatId);
            } catch (e) {
              alert("Could not delete message.");
              console.error(e);
            }
          });
        }
      });
    });

    chatMessages.querySelectorAll("[data-undo]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-undo");
        try {
          await apiRestoreMessage(id);
          await loadAndRenderChat(activeChatId);
        } catch (e) {
          alert("Could not undo.");
          console.error(e);
        }
      });
    });
  }

  // Render chat
  function renderMessages(messages) {
    if (!chatMessages) return;
    chatMessages.innerHTML = "";

    if (!messages || messages.length === 0) {
      chatMessages.innerHTML = `
        <div style="margin:auto; text-align:center; color: var(--muted-foreground); line-height:1.5; padding:1rem;">
          Start a conversation.<br/>
          Send a message when you're ready.
        </div>
      `;
      return;
    }

    messages.forEach((msg) => {
      const timeLabel = formatTimeFromISO(msg.created_at);

      if (msg.sender === ownSenderRole) {
        const messageEl = document.createElement("div");
        messageEl.className = "message sent";

        if (msg.is_deleted) {
          messageEl.innerHTML = `
            <div class="message-content">
              <div class="deleted-placeholder">
                <span>You deleted a message</span>
                <button class="undo-btn" data-undo="${msg.id}">Undo</button>
              </div>
              <div class="message-meta">
                <span class="message-time">${escapeHtml(timeLabel)}</span>
              </div>
            </div>
          `;
          chatMessages.appendChild(messageEl);
          return;
        }

        const editedHtml = msg.edited_at
          ? `<span class="edited-badge"><span class="material-symbols-outlined">edit</span>edited</span>`
          : "";

        messageEl.innerHTML = `
          <div class="message-content">
            <p>${escapeHtml(censorText(msg.text))}</p>

            <div class="message-meta">
              <span class="message-time">${escapeHtml(timeLabel)}</span>
              ${editedHtml}

              <div class="message-actions">
                <button class="icon-btn edit-btn" data-edit="${msg.id}" data-text="${encodeURIComponent(msg.text)}" title="Edit">
                  <span class="material-symbols-outlined">edit</span>
                </button>
                <button class="icon-btn delete-btn" data-del="${msg.id}" title="Delete">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </div>
            </div>
          </div>
        `;
        chatMessages.appendChild(messageEl);
        return;
      }

      const messageEl = document.createElement("div");
      messageEl.className = "message received";

      const avatarSrc = headerAvatar && headerAvatar.src ? headerAvatar.src : "";
      messageEl.innerHTML = `
        <img src="${escapeHtml(avatarSrc)}" class="message-avatar" alt="Avatar">
        <div class="message-content">
          <p>${escapeHtml(censorText(msg.text))}</p>
          <span class="message-time">${escapeHtml(timeLabel)}</span>
        </div>
      `;
      chatMessages.appendChild(messageEl);
    });

    attachMessageHandlers();
    enhanceMeetupCards().then(attachMeetupHandlers).catch(() => {});
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Load chat
  async function loadAndRenderChat(chatId) {
    const msgs = await apiListMessages(chatId);
    renderMessages(msgs);
  }

  // Open chat
  async function openChat(chatId) {
    const user = matchesCache.find((m) => m.match_id === chatId);
    if (!user) return;

    activeChatId = chatId;

    if (headerName) headerName.textContent = user.name;
    if (headerAvatar) headerAvatar.src = user.avatar;

    setActiveSidebar(chatId);
    localStorage.setItem("lastConnectedUser", chatId);

    await loadAndRenderChat(chatId);
    await refreshPairPlant(chatId);
    startPolling();
  }

  function renderTagRow(items) {
    if (!items || items.length === 0) return '<span class="ov-empty">None</span>';
    return items.map((t) => `<span class="ov-chip">${escapeHtml(String(t))}</span>`).join("");
  }

  async function openChatOverview() {
    if (!activeChatId) return;
    try {
      const profile = await apiMatchOverview(activeChatId);
      if (!profile) return;
      const safeRows = (profile.safe_locations || []).map((row) => {
        const mins = row.walking_mins ? ` - ${escapeHtml(String(row.walking_mins))} min walk` : "";
        return `<li>${escapeHtml(row.place_name)} (${escapeHtml(row.station_name)})${mins}</li>`;
      }).join("");

      openModal({
        title: `${profile.name} - Quick Overview`,
        bodyHtml: `
          <div class="ov-wrap">
            <div class="ov-top">
              <img src="${escapeHtml(profile.avatar_url || "")}" alt="${escapeHtml(profile.name || "User")}" class="ov-avatar">
              <div>
                <div class="ov-name">${escapeHtml(profile.name || "User")}</div>
                <div class="ov-type">${escapeHtml(profile.member_type || "Member")}</div>
              </div>
            </div>
            <div class="ov-section"><strong>Interests</strong><div class="ov-chips">${renderTagRow(profile.interests || [])}</div></div>
            <div class="ov-section"><strong>Can Teach</strong><div class="ov-chips">${renderTagRow(profile.skills_teach || [])}</div></div>
            <div class="ov-section"><strong>Wants to Learn</strong><div class="ov-chips">${renderTagRow(profile.skills_learn || [])}</div></div>
            <div class="ov-section"><strong>Their Stations</strong><div class="ov-chips">${renderTagRow(profile.stations || [])}</div></div>
            <div class="ov-section"><strong>Middle Meetup Station</strong><div class="ov-mid">${escapeHtml(profile.midpoint_station || "Not enough shared station data")}</div></div>
            <div class="ov-section"><strong>Senior-Friendly Spots</strong>${safeRows ? `<ul class="ov-list">${safeRows}</ul>` : '<div class="ov-empty">No senior-friendly location data yet.</div>'}</div>
          </div>
        `,
        actionsHtml: `
          <button class="ui-btn" id="ov-close">Back</button>
        `,
      });

      const closeBtn = document.getElementById("ov-close");
      if (closeBtn) closeBtn.addEventListener("click", closeModal);
    } catch (err) {
      alert("Could not load profile overview.");
      console.error(err);
    }
  }

  // Send message
  async function sendMessage() {
    if (!activeChatId) {
      alert("Select a chat first.");
      return;
    }

    const text = (messageInput && messageInput.value ? messageInput.value : "").trim();
    if (!text) {
      if (messageInput) {
        messageInput.value = "";
        messageInput.focus();
      }
      alert("Message cannot be empty.");
      return;
    }
    if (isDemoUser() && hasBlockedProfanity(text)) {
      showProfanityBlock(text);
      return;
    }

    try {
      const senderRole = ownSenderRole;
      const response = await apiCreateMessage(activeChatId, senderRole, text);
      if (response && response.plant) {
        updatePlantUI(response.plant);
        showPlantToast(response.plant);
      }
      if (messageInput) messageInput.value = "";
      await loadAndRenderChat(activeChatId);
    } catch (e) {
      alert(`Send failed: ${e && e.message ? e.message : "unknown error"}`);
      console.error(e);
    }
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", () => {
      sendMessage().catch((e) => {
        alert("Could not send message. Check Flask is running and API routes exist.");
        console.error(e);
      });
    });
  }

  if (messageInput) {
    messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendMessage().catch((err) => {
          alert("Could not send message. Check Flask is running and API routes exist.");
          console.error(err);
        });
      }
    });
  }

  // Polling
  const MESSAGE_POLL_MS = 3000;
  const MATCH_POLL_MS = 5000;
  let messagePollTimer = null;
  let matchPollTimer = null;

  function startPolling() {
    if (messagePollTimer) return;
    messagePollTimer = setInterval(async () => {
      if (!activeChatId) return;
      try {
        await loadAndRenderChat(activeChatId);
      } catch (e) {
        console.error(e);
      }
    }, MESSAGE_POLL_MS);
  }

  if (headerAvatar) {
    headerAvatar.style.cursor = "pointer";
    headerAvatar.title = "View quick profile";
    headerAvatar.addEventListener("click", () => {
      openChatOverview().catch((e) => console.error(e));
    });
  }

  if (setMeetupBtn) {
    setMeetupBtn.addEventListener("click", async () => {
      if (!activeChatId) {
        alert("Select a chat first.");
        return;
      }
      const otherUserId = extractOtherUserId(activeChatId);
      if (!otherUserId) {
        alert("Could not determine connected user.");
        return;
      }
      const meetupTime = window.prompt("Meetup date/time (YYYY-MM-DDTHH:MM):");
      if (!meetupTime) return;
      const spotRaw = window.prompt("Hangout spot ID (optional):", "");
      const spotId = spotRaw ? Number(spotRaw) : null;
      try {
        await apiCreateMeetup({
          target_user_id: otherUserId,
          meetup_time: meetupTime,
          spot_id: Number.isFinite(spotId) ? spotId : null,
          chat_id: activeChatId,
        });
        await loadAndRenderChat(activeChatId);
      } catch (err) {
        alert(err.message || "Could not create meetup");
      }
    });
  }

  if (starterBtn && starterPopup && messageInput) {
    starterBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      if (starterPopup.classList.contains("show")) {
        closeStarterPopup();
      } else {
        openStarterPopup();
      }
    });

    starterPopup.querySelectorAll(".starter-option").forEach((optionBtn) => {
      optionBtn.addEventListener("click", () => {
        const starter = (optionBtn.textContent || "").trim();
        messageInput.value = starter;
        messageInput.focus();
        const len = messageInput.value.length;
        messageInput.setSelectionRange(len, len);
        closeStarterPopup();
      });
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!target) return;
      if (target === starterBtn || starterBtn.contains(target) || starterPopup.contains(target)) return;
      closeStarterPopup();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeStarterPopup();
    });
  }

  async function enhanceMeetupCards() {
    if (!chatMessages) return;
    const nodes = Array.from(chatMessages.querySelectorAll(".message-content p"));
    for (const p of nodes) {
      const meetupId = parseMeetupMarker(p.textContent || "");
      if (!meetupId) continue;
      try {
        const meetup = await apiGetMeetup(meetupId);
        const spot = meetup.spot_name || "Hangout spot";
        p.outerHTML = `
          <div class="message-meetup-card" style="background:#fff7ed; border:1px solid #fdba74; border-radius:12px; padding:0.65rem;">
            <strong>Meetup Card</strong>
            <div style="font-size:0.85rem; color:#334155; margin-top:0.2rem;">${escapeHtml(spot)} · ${escapeHtml(meetup.meetup_time || "")}</div>
            <div style="font-size:0.8rem; color:#64748b;">Status: ${escapeHtml(meetup.status || "proposed")}</div>
            <div style="display:flex; gap:0.45rem; flex-wrap:wrap; margin-top:0.45rem;">
              <button class="btn btn-outline-teal btn-sm" data-meetup-action="confirm" data-meetup-id="${meetup.id}" type="button">Confirm</button>
              <button class="btn btn-outline-teal btn-sm" data-meetup-action="reschedule" data-meetup-id="${meetup.id}" type="button">Suggest new time</button>
              <button class="btn btn-outline-orange btn-sm" data-meetup-action="cancel" data-meetup-id="${meetup.id}" type="button">Cancel</button>
              <button class="btn btn-orange btn-sm glow" data-meetup-action="checkin" data-meetup-id="${meetup.id}" type="button">I've arrived</button>
              <button class="btn btn-outline-orange btn-sm" data-meetup-action="mark_no_show" data-meetup-id="${meetup.id}" type="button">No-show</button>
              <button class="btn btn-outline-teal btn-sm" data-meetup-action="review" data-meetup-id="${meetup.id}" type="button">Leave review</button>
            </div>
          </div>
        `;
      } catch (_) {
        p.textContent = "Meetup card unavailable.";
      }
    }
  }

  function attachMeetupHandlers() {
    if (!chatMessages) return;
    chatMessages.querySelectorAll("[data-meetup-action]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const action = btn.getAttribute("data-meetup-action");
        const meetupId = btn.getAttribute("data-meetup-id");
        if (!action || !meetupId) return;
        try {
          if (action === "reschedule") {
            const value = window.prompt("Enter new meetup time (YYYY-MM-DDTHH:MM):");
            if (!value) return;
            await apiMeetupAction(meetupId, "reschedule", { meetup_time: value });
          } else if (action === "review") {
            const ratingRaw = window.prompt("Rating (1-5):", "5");
            if (!ratingRaw) return;
            const rating = Number(ratingRaw);
            const comment = window.prompt("Comment (optional):", "") || "";
            const res = await fetch("/api/reviews", {
              method: "POST",
              headers: csrfHeaders({ "Content-Type": "application/json" }),
              body: JSON.stringify({ meetup_id: Number(meetupId), rating, comment, tags: [] }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || !data.ok) throw new Error(data.error || "Could not submit review");
          } else {
            await apiMeetupAction(meetupId, action, {});
          }
          await loadAndRenderChat(activeChatId);
        } catch (err) {
          alert(err.message || "Meetup action failed");
        }
      });
    });
  }
  if (headerName) {
    headerName.style.cursor = "pointer";
    headerName.title = "View quick profile";
    headerName.addEventListener("click", () => {
      openChatOverview().catch((e) => console.error(e));
    });
  }

  function startMatchPolling() {
    if (matchPollTimer) return;
    matchPollTimer = setInterval(async () => {
      try {
        const list = await apiListMatches();
        matchesCache = list || [];
        renderConversationList(matchesCache);
        if (activeChatId) setActiveSidebar(activeChatId);
      } catch (e) {
        console.error(e);
      }
    }, MATCH_POLL_MS);
  }

  // Init
  async function init() {
    if (!conversationsListEl || !chatMessages) return;

    matchesCache = await apiListMatches();
    try {
      const session = await apiGetSession();
      if (session && session.name && session.role) {
        currentUser = { user_id: session.user_id || null, name: session.name, role: session.role };
      }
      ownSenderRole = normalizeSenderRole(currentUser && currentUser.role);
    } catch (e) {
      console.error(e);
    }
    try {
      const profanities = await apiListProfanities();
      buildProfanityPatterns(profanities);
    } catch (e) {
      console.error(e);
    }
    renderConversationList(matchesCache);

    const lastConnectedId = localStorage.getItem("lastConnectedUser");
    const autoChat = urlChatId || lastConnectedId || (matchesCache[0] && matchesCache[0].match_id);

    if (autoChat) await openChat(autoChat);
    startPolling();
    startMatchPolling();
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const q = (searchInput.value || "").toLowerCase();
      const filtered = matchesCache.filter((m) => (m.name || "").toLowerCase().includes(q));
      renderConversationList(filtered);
      if (activeChatId) setActiveSidebar(activeChatId);
    });
  }

  init().catch((e) => {
    if (conversationsListEl) {
      conversationsListEl.innerHTML = `<div style="padding:1rem; color:#7f8c8d;">Flask/DB not available.</div>`;
    }
    console.error(e);
  });
});

