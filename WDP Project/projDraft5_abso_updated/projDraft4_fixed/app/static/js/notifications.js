document.addEventListener("DOMContentLoaded", function () {
  const notifBtn = document.getElementById("notif-btn");
  const dropdown = document.getElementById("notifications-dropdown");
  const badge = document.querySelector(".notification-badge");
  const markReadBtn = document.querySelector(".mark-read-btn");
  const listEl = document.getElementById("notifications-list");

  const matchModal = document.createElement("div");
  matchModal.id = "match-success-modal";
  matchModal.style.cssText = "position:fixed;inset:0;background:rgba(15,23,42,.52);display:none;align-items:center;justify-content:center;z-index:2500;";
  matchModal.innerHTML = `
    <div style="width:min(420px,92vw);background:#fff;border:2px solid #fed7aa;border-radius:16px;box-shadow:0 18px 48px rgba(0,0,0,.25);padding:18px;">
      <div style="font-size:1.5rem;font-weight:800;color:#0f172a;margin-bottom:6px;">It's a match!</div>
      <p id="match-success-text" style="margin:0 0 14px;color:#475569;">You connected successfully.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        <button id="match-success-back" type="button" style="border:2px solid #14b8a6;background:#f0fdfa;color:#0f766e;padding:10px 12px;border-radius:10px;font-weight:700;">Back</button>
        <button id="match-success-message" type="button" style="border:2px solid #f97316;background:linear-gradient(135deg,#f97316,#fb923c);color:#fff;padding:10px 12px;border-radius:10px;font-weight:700;">Message</button>
      </div>
    </div>
  `;
  document.body.appendChild(matchModal);
  const matchSuccessText = document.getElementById("match-success-text");
  const matchSuccessBack = document.getElementById("match-success-back");
  const matchSuccessMessage = document.getElementById("match-success-message");
  let matchSuccessChatId = "";
  const quickModal = document.createElement("div");
  quickModal.id = "notif-overview-modal";
  quickModal.style.cssText = "position:fixed;inset:0;background:rgba(15,23,42,.52);display:none;align-items:center;justify-content:center;z-index:2600;";
  quickModal.innerHTML = `
    <div style="width:min(520px,94vw);max-height:84vh;overflow:auto;background:#fff;border:2px solid #fed7aa;border-radius:16px;box-shadow:0 18px 48px rgba(0,0,0,.25);padding:16px;">
      <h3 id="notif-ov-title" style="margin:0 0 10px;color:#0f172a;"></h3>
      <div id="notif-ov-body" style="margin-bottom:12px;"></div>
      <div id="notif-ov-actions" style="display:flex;gap:10px;justify-content:flex-end;"></div>
    </div>
  `;
  document.body.appendChild(quickModal);
  const quickTitle = document.getElementById("notif-ov-title");
  const quickBody = document.getElementById("notif-ov-body");
  const quickActions = document.getElementById("notif-ov-actions");

  function openQuickModal({ title, bodyHtml, actionsHtml }) {
    if (!quickTitle || !quickBody || !quickActions) return;
    quickTitle.textContent = title;
    quickBody.innerHTML = bodyHtml;
    quickActions.innerHTML = actionsHtml;
    quickModal.style.display = "flex";
  }
  function closeQuickModal() {
    quickModal.style.display = "none";
  }
  quickModal.addEventListener("click", (e) => {
    if (e.target === quickModal) closeQuickModal();
  });

  function demoHeaders(extra) {
    const headers = extra ? { ...extra } : {};
    const demoId = sessionStorage.getItem("demo_user_id");
    if (demoId) headers["X-Demo-User"] = demoId;
    return headers;
  }

  function updateBadge(count) {
    if (!badge) return;
    const unread = Number.isFinite(count) ? count : 0;
    badge.textContent = String(unread);
    badge.style.display = unread > 0 ? "inline-flex" : "none";
  }

  function toggleDropdown() {
    if (!dropdown) return;
    dropdown.classList.toggle("show");
    if (dropdown.classList.contains("show")) {
      requestAnimationFrame(positionDropdown);
    }
  }

  function positionDropdown() {
    if (!dropdown || !notifBtn) return;
    const rect = notifBtn.getBoundingClientRect();
    const width = dropdown.offsetWidth || 320;
    const margin = 8;
    let left = rect.left + rect.width / 2 - width / 2;
    if (left < margin) left = margin;
    let top = rect.bottom + margin;
    dropdown.style.top = `${top}px`;
    dropdown.style.left = `${left}px`;
    dropdown.style.right = "auto";
  }

  async function apiListNotifications() {
    const res = await fetch("/api/notifications", { headers: demoHeaders() });
    if (!res.ok) return { notifications: [], unread_count: 0 };
    return await res.json();
  }

  async function apiMarkRead() {
    const res = await fetch("/api/notifications/mark_read", {
      method: "POST",
      headers: demoHeaders(),
    });
    if (!res.ok) return false;
    return true;
  }

  async function apiRespondRequest(requestId, action) {
    const res = await fetch(`/api/match_requests/${requestId}/respond`, {
      method: "POST",
      headers: demoHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ action }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return { ok: false, error: data.error || "Could not update request." };
    return { ok: true, data };
  }

  async function apiMatchOverview(matchRef) {
    const res = await fetch(`/api/matches/${encodeURIComponent(matchRef)}/overview`, { headers: demoHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) return null;
    return data.profile || null;
  }

  async function openQuickOverview(matchRef) {
    const profile = await apiMatchOverview(matchRef);
    if (!profile) return;
    const safeRows = (profile.safe_locations || []).map((row) => {
      const mins = row.walking_mins ? ` - ${row.walking_mins} min walk` : "";
      return `<li>${row.place_name} (${row.station_name})${mins}</li>`;
    }).join("");
    openQuickModal({
      title: `${profile.name} - Profile Overview`,
      bodyHtml: `
        <div style="display:grid;gap:10px;">
          <div style="display:flex;align-items:center;gap:10px;">
            <img src="${profile.avatar_url || ""}" alt="${profile.name}" style="width:52px;height:52px;border-radius:50%;border:2px solid #fdba74;">
            <div>
              <div style="font-weight:800;color:#0f172a;">${profile.name || "User"}</div>
              <div style="color:#64748b;">${profile.member_type || "Member"}</div>
            </div>
          </div>
          <div><strong>Interests:</strong> ${(profile.interests || []).join(", ") || "None"}</div>
          <div><strong>Can Teach:</strong> ${(profile.skills_teach || []).join(", ") || "None"}</div>
          <div><strong>Wants to Learn:</strong> ${(profile.skills_learn || []).join(", ") || "None"}</div>
          <div><strong>Middle Meetup Station:</strong> ${profile.midpoint_station || "Not enough data yet"}</div>
          <div><strong>Safe Meetup Spots:</strong> ${safeRows ? `<ul style="margin:6px 0 0 18px;">${safeRows}</ul>` : "None yet"}</div>
        </div>
      `,
      actionsHtml: `
        <button class="ui-btn" id="notif-ov-close">Close</button>
      `,
    });
    const closeBtn = document.getElementById("notif-ov-close");
    if (closeBtn) closeBtn.addEventListener("click", closeQuickModal);
  }

  function renderNotifications(items) {
    if (!listEl) return;
    listEl.innerHTML = "";

    if (!items || items.length === 0) {
      listEl.innerHTML = `
        <div style="padding: 1rem; color: var(--muted-foreground); font-size: 0.95rem;">
          No notifications yet.
        </div>
      `;
      return;
    }

    items.forEach((n) => {
      const item = document.createElement("div");
      item.className = "notification-item";
      if (n.unread) item.classList.add("unread");

      if (n.type === "match_request") {
        item.innerHTML = `
          <div class="notif-icon teal">&#x1F91D;</div>
          <div class="notif-content">
            <p><strong>${n.sender_name}</strong> sent a match request</p>
            <span class="notif-time">${n.sender_location || "Nearby"} &#x2022; Pending</span>
            <div class="notif-actions">
              <button class="notif-action-btn accept" data-action="accept" data-id="${n.request_id}">Accept</button>
              <button class="notif-action-btn decline" data-action="decline" data-id="${n.request_id}">Decline</button>
            </div>
          </div>
        `;
      } else if (n.type === "match_decision") {
        const status = n.status === "accepted" ? "accepted" : "declined";
        item.innerHTML = `
          <div class="notif-icon ${status === "accepted" ? "success" : "orange"}">&#x1F514;</div>
          <div class="notif-content">
            <p>Your request to <strong>${n.receiver_name}</strong> was ${status}.</p>
            <span class="notif-time">Just now</span>
          </div>
        `;
      } else {
        item.innerHTML = `
          <div class="notif-icon orange">&#x1F514;</div>
          <div class="notif-content">
            <p>${n.message || "New notification"}</p>
            <span class="notif-time">Just now</span>
          </div>
        `;
      }

      listEl.appendChild(item);

      const targetUserId = n.type === "match_request" ? n.sender_id : (n.type === "match_decision" ? n.receiver_id : null);
      if (targetUserId) {
        const content = item.querySelector(".notif-content");
        if (content) {
          content.style.cursor = "pointer";
          content.addEventListener("click", () => {
            openQuickOverview(`user-${targetUserId}`).catch((err) => console.error(err));
          });
        }
      }
    });

    listEl.querySelectorAll(".notif-action-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = btn.getAttribute("data-id");
        const action = btn.getAttribute("data-action");
        if (!id || !action) return;
        const result = await apiRespondRequest(id, action);
        if (!result.ok) {
          alert(result.error || "Could not update request.");
          return;
        }
        const payload = result.data || {};
        if (action === "accept" && payload.status === "accepted") {
          const matchName = payload.match && payload.match.name ? payload.match.name : "your new connection";
          matchSuccessChatId = payload.match && payload.match.chat_id ? payload.match.chat_id : "";
          if (matchSuccessText) {
            matchSuccessText.textContent = `You matched with ${matchName}. Start chatting now?`;
          }
          matchModal.style.display = "flex";
        }
        await refreshNotifications();
      });
    });
  }

  if (matchSuccessBack) {
    matchSuccessBack.addEventListener("click", function () {
      matchModal.style.display = "none";
    });
  }
  if (matchSuccessMessage) {
    matchSuccessMessage.addEventListener("click", function () {
      const target = matchSuccessChatId ? `/messages?chat=${encodeURIComponent(matchSuccessChatId)}` : "/messages";
      window.location.href = target;
    });
  }

  async function refreshNotifications() {
    const out = await apiListNotifications();
    renderNotifications(out.notifications || []);
    updateBadge(out.unread_count || 0);
  }

  if (notifBtn && dropdown) {
    notifBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleDropdown();
      refreshNotifications();
    });

    document.addEventListener("click", function (e) {
      if (!dropdown.contains(e.target) && e.target !== notifBtn) {
        dropdown.classList.remove("show");
      }
    });
  }

  if (markReadBtn && dropdown) {
    markReadBtn.addEventListener("click", async function () {
      await apiMarkRead();
      await refreshNotifications();
    });
  }

  refreshNotifications();
  setInterval(refreshNotifications, 5000);

  window.addEventListener("resize", () => {
    if (dropdown && dropdown.classList.contains("show")) positionDropdown();
  });
  window.addEventListener("scroll", () => {
    if (dropdown && dropdown.classList.contains("show")) positionDropdown();
  });
});
