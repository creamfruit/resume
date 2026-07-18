document.addEventListener("DOMContentLoaded", function () {
  const backBtn = document.getElementById("back-btn");
  if (backBtn) backBtn.addEventListener("click", () => window.location.href = "/sean/dashboard");


  const conversationsListEl = document.getElementById("conversations-list");
  const searchInput = document.getElementById("search-conversations");

  const chatMessages = document.getElementById("chat-messages");
  const headerName = document.getElementById("chat-name");
  const headerAvatar = document.getElementById("chat-avatar");

  const messageInput = document.getElementById("message-input");
  const sendBtn = document.getElementById("send-btn");

  const params = new URLSearchParams(window.location.search);
  const urlChatId = params.get("chat");

  let activeChatId = null;
  let matchesCache = [];
  let profanityPatterns = [];
  let currentUser = { name: "User", role: "youth" };

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
    div.textContent = text ?? "";
    return div.innerHTML;
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
    const res = await fetch("/sean/api/matches");
    if (!res.ok) throw new Error("Failed to load matches");
    return await res.json();
  }

  // API messages
  async function apiListMessages(chatId) {
    const res = await fetch(`/api/messages/${encodeURIComponent(chatId)}`);
    if (!res.ok) throw new Error("Failed to load messages");
    return await res.json();
  }

  // API send
  async function apiCreateMessage(chatId, sender, text) {
    const res = await fetch(`/api/messages/${encodeURIComponent(chatId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender, text }),
    });
    if (!res.ok) throw new Error("Failed to send message");
    return await res.json();
  }

  async function apiReportProfanityBlock(chatId, text) {
    const res = await fetch("/sean/api/profanity-block", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    if (!res.ok) throw new Error("Failed to report blocked profanity");
    return await res.json();
  }

  // API profanities
  async function apiListProfanities() {
    const res = await fetch("/sean/api/profanities");
    if (!res.ok) throw new Error("Failed to load profanities");
    return await res.json();
  }

  // API session
  async function apiGetSession() {
    const res = await fetch("/sean/api/session");
    if (!res.ok) return null;
    return await res.json();
  }

  // API edit
  async function apiUpdateMessage(messageId, text) {
    const res = await fetch(`/api/messages/${messageId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error("Failed to edit message");
    return await res.json();
  }

  // API delete
  async function apiDeleteMessage(messageId) {
    const res = await fetch(`/api/messages/${messageId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete message");
    return await res.json();
  }

  // API restore
  async function apiRestoreMessage(messageId) {
    const res = await fetch(`/api/messages/${messageId}/restore`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to restore message");
    return await res.json();
  }

  // Sidebar state
  function setActiveSidebar(chatId) {
    document.querySelectorAll(".conversation-item").forEach((item) => {
      item.classList.toggle("active", item.dataset.chat === chatId);
    });
  }

  // Render list
  function renderConversationList(list) {
    if (!conversationsListEl) return;
    conversationsListEl.innerHTML = "";

    if (!list || list.length === 0) {
      conversationsListEl.innerHTML = `
        <div style="padding: 1rem; color: var(--muted-foreground); font-size: 0.95rem;">
          No connections yet. ❤️<br/>
          Go to Matches and click Connect first!
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
        <div style="padding:1rem; color: var(--muted-foreground);">
          No messages yet. Say hi! 👋
        </div>
      `;
      return;
    }

    messages.forEach((msg) => {
      const timeLabel = formatTimeFromISO(msg.created_at);

      if (msg.sender === "youth") {
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
      const senderRole = currentUser && currentUser.role ? currentUser.role : "youth";
      await apiCreateMessage(activeChatId, senderRole, text);
      if (messageInput) messageInput.value = "";
      await loadAndRenderChat(activeChatId);
    } catch (e) {
      alert("Send failed. Check /api/messages/<chatId> in Flask.");
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

  // Init
  async function init() {
    if (!conversationsListEl || !chatMessages) return;

    matchesCache = await apiListMatches();
    try {
      const session = await apiGetSession();
      if (session && session.name && session.role) {
        currentUser = { name: session.name, role: session.role };
      }
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
