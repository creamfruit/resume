(function () {
  const listEl = document.getElementById("feed-list");
  const featuredWrapEl = document.getElementById("featured-feed-wrap");
  const toggleButtons = Array.from(document.querySelectorAll(".feed-toggle button"));
  const modalEl = document.getElementById("feed-post-modal");
  const modalCloseEl = document.getElementById("feed-post-close");
  const modalMediaEl = document.getElementById("feed-post-media");
  const modalUserEl = document.getElementById("feed-post-user");
  const modalCaptionEl = document.getElementById("feed-post-caption");
  const modalStatsEl = document.getElementById("feed-post-stats");
  const modalCommentsEl = document.getElementById("feed-post-comments");
  let scope = "community";

  function esc(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function humanTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  function profileUrl(item) {
    const username = (item.owner_username || "").trim();
    if (username) return `/profile/${encodeURIComponent(username)}`;
    return `/u/${encodeURIComponent(item.owner_user_id)}`;
  }

  function csrfHeaders(extra) {
    const out = Object.assign({}, extra || {});
    if (window.CSRF_TOKEN) out["X-CSRF-Token"] = window.CSRF_TOKEN;
    return out;
  }

  function cardHtml(item) {
    const avatar = item.owner_avatar || "/static/images/avatar-placeholder.svg";
    const media = item.media_url
      ? `<button type="button" class="feed-media-btn" data-post-id="${item.id}"><img src="${esc(item.media_url)}" class="feed-media" alt="${esc(item.title || "Memory")}"></button>`
      : "";
    const campaignTag = item.campaign_tag ? `<span style="display:inline-block;margin-top:0.25rem;font-size:0.72rem;padding:0.15rem 0.5rem;border-radius:999px;background:#fff7ed;color:#c2410c;border:1px solid #fdba74;">${esc(item.campaign_tag)}</span>` : "";
    const userHref = profileUrl(item);
    return `
      <article class="feed-card">
        <div class="feed-card-head">
          <img src="${esc(avatar)}" class="feed-avatar" alt="${esc(item.owner_name)}">
          <div class="feed-meta">
            <strong><a href="${esc(userHref)}">${esc(item.owner_name)}</a></strong>
            <span>${esc(humanTime(item.created_at))} · ${esc(item.visibility)}</span>
          </div>
        </div>
        ${media}
        <div class="feed-body">
          <h3 class="feed-title">${esc(item.title || "Untitled memory")}</h3>
          <p class="feed-text">${esc(item.content || "")}</p>
          ${campaignTag}
          <div class="feed-actions">
            <button class="feed-like-btn" data-entry-id="${item.id}" type="button">&#x2764; Like</button>
            <span>${item.like_count} likes · ${item.comment_count} comments</span>
          </div>
        </div>
      </article>
    `;
  }

  function renderFeatured(items) {
    if (!featuredWrapEl) return;
    const list = Array.isArray(items) ? items : [];
    if (!list.length) {
      featuredWrapEl.innerHTML = "";
      return;
    }
    featuredWrapEl.innerHTML = `
      <section style="border:1px solid #f59e0b;border-radius:14px;background:#fff7ed;padding:0.85rem;">
        <div style="font-weight:800;color:#9a3412;margin-bottom:0.5rem;">Featured Campaigns</div>
        <div class="feed-grid">${list.map(cardHtml).join("")}</div>
      </section>
    `;
  }

  async function loadFeed() {
    if (!listEl) return;
    listEl.innerHTML = '<div class="feed-empty">Loading feed...</div>';
    try {
      const res = await fetch(`/api/feed?scope=${encodeURIComponent(scope)}`);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Failed to load feed");
      const entries = Array.isArray(data.entries) ? data.entries : [];
      const featured = Array.isArray(data.featured) ? data.featured : [];
      renderFeatured(featured);
      if (!entries.length) {
        listEl.innerHTML = '<div class="feed-empty">No posts in this feed yet.</div>';
        return;
      }
      listEl.innerHTML = entries.map(cardHtml).join("");
    } catch (err) {
      listEl.innerHTML = `<div class="feed-empty">${err.message || "Unable to load feed."}</div>`;
    }
  }

  async function likeEntry(entryId) {
    try {
      await fetch("/api/posts/" + encodeURIComponent(entryId) + "/like", {
        method: "POST",
        headers: csrfHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({}),
      });
      await loadFeed();
    } catch (_) {
      // Keep UI resilient for demo usage.
    }
  }

  function openModal() {
    if (!modalEl) return;
    modalEl.classList.add("show");
    modalEl.setAttribute("aria-hidden", "false");
  }

  function closeModal() {
    if (!modalEl) return;
    modalEl.classList.remove("show");
    modalEl.setAttribute("aria-hidden", "true");
  }

  async function openPostDetail(postId) {
    try {
      const res = await fetch(`/api/posts/${encodeURIComponent(postId)}`);
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Could not load post");
      if (modalMediaEl) modalMediaEl.src = data.media_url || "";
      const profileHref = data.user && data.user.username ? `/profile/${encodeURIComponent(data.user.username)}` : "#";
      if (modalUserEl) {
        modalUserEl.href = profileHref;
        modalUserEl.textContent = (data.user && data.user.username) || "User";
      }
      if (modalCaptionEl) modalCaptionEl.textContent = data.caption || "";
      if (modalStatsEl) modalStatsEl.textContent = `${Number(data.like_count || 0)} likes · ${Number(data.comment_count || 0)} comments`;
      if (modalCommentsEl) {
        const comments = Array.isArray(data.comments) ? data.comments : [];
        modalCommentsEl.innerHTML = comments.length
          ? comments.map((c) => `<div style="font-size:0.9rem;"><strong>${esc((c.user && c.user.username) || "User")}:</strong> ${esc(c.body || "")}</div>`).join("")
          : '<div style="font-size:0.9rem;color:#64748b;">No comments yet.</div>';
      }
      openModal();
    } catch (err) {
      alert(err.message || "Unable to open post.");
    }
  }

  toggleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      scope = btn.dataset.scope || "community";
      toggleButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      loadFeed();
    });
  });

  document.addEventListener("click", (event) => {
    const mediaBtn = event.target.closest(".feed-media-btn");
    if (mediaBtn) {
      const postId = mediaBtn.getAttribute("data-post-id");
      if (postId) openPostDetail(postId);
      return;
    }
    const button = event.target.closest(".feed-like-btn");
    if (!button) return;
    const entryId = button.getAttribute("data-entry-id");
    if (!entryId) return;
    likeEntry(entryId);
  });

  if (modalCloseEl) modalCloseEl.addEventListener("click", closeModal);
  if (modalEl) {
    modalEl.addEventListener("click", (event) => {
      if (event.target === modalEl) closeModal();
    });
  }

  loadFeed();
})();
