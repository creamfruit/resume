(function () {
  const input = document.getElementById("user-search-input");
  const button = document.getElementById("user-search-btn");
  const resultsEl = document.getElementById("user-search-results");
  const clubsWrap = document.getElementById("clubs-results");
  const clubsGrid = document.getElementById("clubs-grid");
  const typeEl = document.getElementById("explore-type");
  const activeType = (typeEl?.value || "people").toLowerCase();

  function esc(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function requestHeaders(extra) {
    const headers = Object.assign({}, extra || {});
    if (window.CSRF_TOKEN) headers["X-CSRF-Token"] = window.CSRF_TOKEN;
    const demoId = sessionStorage.getItem("demo_user_id");
    if (demoId) headers["X-Demo-User"] = demoId;
    return headers;
  }

  function stateButton(user) {
    const status = user.friend_status;
    if (status === "friends") {
      return `<button class="btn btn-secondary" data-action="unfriend" data-user-id="${user.user_id}" type="button">Friends</button>`;
    }
    if (status === "pending_sent") {
      return `<button class="btn btn-secondary" type="button" disabled>Pending</button>`;
    }
    if (status === "pending_received") {
      return `<button class="btn btn-primary" data-action="accept" data-request-id="${user.request_id}" type="button">Accept</button>`;
    }
    if (status === "blocked") {
      return `<button class="btn btn-secondary" type="button" disabled>Blocked</button>`;
    }
    return `<button class="btn btn-primary" data-action="request" data-user-id="${user.user_id}" type="button">Add Friend</button>`;
  }

  function userCard(user) {
    const avatar = user.avatar_url || "/static/images/avatar-placeholder.svg";
    const interests = (user.interests || []).slice(0, 3).map((i) => `<span class="chip">${esc(i)}</span>`).join(" ");
    return `
      <article class="search-card">
        <div class="search-head">
          <img class="search-avatar" src="${esc(avatar)}" alt="${esc(user.username)}">
          <div>
            <strong>${esc(user.username)}</strong>
            <div class="trust-pill">Trust Score: ${Number(user.trust_score || 0)}</div>
          </div>
        </div>
        <p style="margin:0; color:#475569;">${esc(user.bio || "")}</p>
        <div class="chip-row" style="margin-top:0.45rem;">${interests}</div>
        <div class="search-actions">
          ${stateButton(user)}
          <a href="${esc(user.profile_url || "#")}" class="btn btn-secondary">View Profile</a>
        </div>
      </article>
    `;
  }

  function clubCard(club) {
    return `
      <article class="club-card">
        <div class="club-banner">🏷️</div>
        <div class="club-body">
          <strong>${esc(club.name)}</strong>
          <div class="club-meta">${esc(club.category || "Community")} · ${Number(club.member_count || 0)} members</div>
          <p style="margin:0; color:#475569;">${esc((club.description || "Community club for peer support and activities.").slice(0, 120))}</p>
          <div class="club-actions">
            <a href="/clubs/${Number(club.id)}" class="btn btn-secondary">Details</a>
            <button type="button" class="btn ${club.is_joined ? "btn-secondary" : "btn-primary"} club-join-btn" data-club-id="${Number(club.id)}" data-joined="${club.is_joined ? "1" : "0"}">${club.is_joined ? "Joined" : "Join"}</button>
          </div>
        </div>
      </article>
    `;
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: requestHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || "Request failed");
    return data;
  }

  async function searchUsers() {
    if (!resultsEl) return;
    resultsEl.innerHTML = `<div class="search-empty">Loading people...</div>`;
    const q = (input?.value || "").trim();
    try {
      const res = await fetch(`/api/search/users?q=${encodeURIComponent(q)}`, { headers: requestHeaders() });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Could not load users");
      const users = Array.isArray(data.results) ? data.results : [];
      if (!users.length) {
        resultsEl.innerHTML = `<div class="search-empty">No matching users found.</div>`;
        return;
      }
      resultsEl.innerHTML = users.map(userCard).join("");
    } catch (err) {
      resultsEl.innerHTML = `<div class="search-empty">${esc(err.message || "Unable to search users.")}</div>`;
    }
  }

  async function searchClubs() {
    if (!clubsGrid) return;
    clubsGrid.innerHTML = `<div class="search-empty">Loading clubs...</div>`;
    const q = (input?.value || "").trim();
    try {
      const res = await fetch(`/api/clubs?q=${encodeURIComponent(q)}`, { headers: requestHeaders() });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Could not load clubs");
      const clubs = Array.isArray(data.clubs) ? data.clubs : [];
      if (!clubs.length) {
        clubsGrid.innerHTML = `<div class="search-empty">No matching clubs found.</div>`;
        return;
      }
      clubsGrid.innerHTML = clubs.map(clubCard).join("");
    } catch (err) {
      clubsGrid.innerHTML = `<div class="search-empty">${esc(err.message || "Unable to search clubs.")}</div>`;
    }
  }

  async function handlePeopleAction(target) {
    const action = target.getAttribute("data-action");
    if (!action) return;
    if (action === "request") {
      await postJson("/api/friends/request", { user_id: Number(target.getAttribute("data-user-id")) });
    } else if (action === "accept") {
      await postJson("/api/friends/accept", { request_id: Number(target.getAttribute("data-request-id")) });
    } else if (action === "unfriend") {
      await postJson("/api/friends/unfriend", { user_id: Number(target.getAttribute("data-user-id")) });
    }
    await searchUsers();
  }

  async function handleClubAction(target) {
    const clubId = Number(target.getAttribute("data-club-id") || 0);
    if (!clubId) return;
    const joined = target.getAttribute("data-joined") === "1";
    const endpoint = joined ? `/api/clubs/${clubId}/leave` : `/api/clubs/${clubId}/join`;
    await postJson(endpoint, {});
    await searchClubs();
  }

  if (button) {
    button.addEventListener("click", () => {
      if (activeType === "clubs") {
        searchClubs();
      } else {
        searchUsers();
      }
    });
  }

  if (input) {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        if (activeType === "clubs") {
          searchClubs();
        } else {
          searchUsers();
        }
      }
    });
  }

  if (resultsEl) {
    resultsEl.addEventListener("click", (event) => {
      const btn = event.target.closest("button[data-action]");
      if (!btn) return;
      handlePeopleAction(btn).catch((err) => window.alert(err.message || "Action failed"));
    });
  }

  if (clubsWrap) {
    clubsWrap.addEventListener("click", (event) => {
      const btn = event.target.closest(".club-join-btn");
      if (!btn) return;
      handleClubAction(btn).catch((err) => window.alert(err.message || "Action failed"));
    });
  }

  if (activeType === "clubs") {
    searchClubs();
  } else {
    searchUsers();
  }
})();
