(function () {
  function pick(selector) {
    return document.querySelector(selector);
  }

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function esc(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function prettyTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  }

  const context = window.profileContext || {};
  const ownerUserId = Number(context.ownerUserId || 0);
  const profileUrl = String(context.profileUrl || window.location.href);
  const gridEl = pick("#profile-scrapbook-grid");
  const emptyEl = pick("#profile-scrapbook-empty");
  const modalEl = pick("#profile-post-modal");
  const closeBtn = pick("#profile-post-close");
  const mediaEl = pick("#profile-post-media");
  const titleEl = pick("#profile-post-title");
  const captionEl = pick("#profile-post-caption");
  const visEl = pick("#profile-post-visibility");
  const timeEl = pick("#profile-post-time");
  const commentsListEl = pick("#profile-post-comments-list");
  const likeBtn = pick("#profile-post-like");
  const commentInput = pick("#profile-post-comment-input");
  const commentSend = pick("#profile-post-comment-send");
  const shareBtn = pick("#share-profile-link-btn");

  let entries = [];
  let currentEntry = null;

  function requestHeaders(extra) {
    const headers = Object.assign({}, extra || {});
    if (window.CSRF_TOKEN) headers["X-CSRF-Token"] = window.CSRF_TOKEN;
    const demoId = sessionStorage.getItem("demo_user_id");
    if (demoId) headers["X-Demo-User"] = demoId;
    return headers;
  }

  function applyTabSwitching() {
    const tabBtns = Array.from(document.querySelectorAll(".profile-tab-btn"));
    const tabContents = Array.from(document.querySelectorAll(".profile-tab-content"));
    if (!tabBtns.length) return;
    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        tabBtns.forEach((b) => b.classList.remove("active"));
        tabContents.forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        const target = pick(`#tab-${tab}`);
        if (target) target.classList.add("active");
      });
    });
  }

  function renderGrid() {
    if (!gridEl) return;
    if (!entries.length) {
      gridEl.innerHTML = "";
      if (emptyEl) emptyEl.style.display = "";
      return;
    }
    if (emptyEl) emptyEl.style.display = "none";
    gridEl.innerHTML = entries
      .map((entry) => {
        const media = entry.media_url
          ? `<img class="profile-scrapbook-thumb" src="${esc(entry.media_url)}" alt="${esc(entry.title || "Memory")}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"><div class="profile-scrapbook-thumb profile-scrapbook-placeholder" style="display:none;">Memory</div>`
          : `<div class="profile-scrapbook-thumb profile-scrapbook-placeholder">Memory</div>`;
        return `
          <button type="button" class="profile-scrapbook-item" data-entry-id="${entry.id}">
            ${media}
            <div class="profile-scrapbook-body">
              <p class="profile-scrapbook-title">${esc(entry.title || "Untitled")}</p>
              <p class="profile-scrapbook-meta">${esc(entry.visibility || "private")} · ${esc(prettyTime(entry.created_at))}</p>
            </div>
          </button>
        `;
      })
      .join("");
  }

  async function loadEntries() {
    if (!gridEl || !ownerUserId) return;
    if (context.canView === false) {
      gridEl.innerHTML = "";
      if (emptyEl) {
        emptyEl.style.display = "";
        emptyEl.textContent = "This account is private.";
      }
      return;
    }
    gridEl.innerHTML = `<div class="profile-scrapbook-empty">Loading scrapbook...</div>`;
    try {
      const res = await fetch(`/api/scrapbook/entries?owner_user_id=${encodeURIComponent(ownerUserId)}`);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Could not load scrapbook");
      entries = Array.isArray(data.entries) ? data.entries : [];
      renderGrid();
    } catch (err) {
      gridEl.innerHTML = `<div class="profile-scrapbook-empty">${esc(err.message || "Unable to load scrapbook.")}</div>`;
    }
  }

  async function loadComments(entryId) {
    if (!commentsListEl) return;
    commentsListEl.innerHTML = "Loading comments...";
    try {
      const res = await fetch(`/api/scrapbook/comments?entry_id=${encodeURIComponent(entryId)}`);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Could not load comments");
      const comments = Array.isArray(data.comments) ? data.comments : [];
      if (!comments.length) {
        commentsListEl.innerHTML = '<div class="profile-post-comment-item">No comments yet.</div>';
        return;
      }
      commentsListEl.innerHTML = comments
        .map((c) => `<div class="profile-post-comment-item">${esc(c.comment_text)} <span style="color:#64748b;">· ${esc(prettyTime(c.created_at))}</span></div>`)
        .join("");
    } catch (err) {
      commentsListEl.innerHTML = `<div class="profile-post-comment-item">${esc(err.message || "Unable to load comments.")}</div>`;
    }
  }

  async function openModal(entryId) {
    currentEntry = entries.find((e) => Number(e.id) === Number(entryId)) || null;
    if (!currentEntry || !modalEl) return;
    if (mediaEl) {
      mediaEl.style.display = currentEntry.media_url ? "" : "none";
      mediaEl.src = currentEntry.media_url || "";
    }
    if (titleEl) titleEl.textContent = currentEntry.title || "Memory";
    if (captionEl) captionEl.textContent = currentEntry.content || "";
    if (visEl) visEl.textContent = currentEntry.visibility || "private";
    if (timeEl) timeEl.textContent = prettyTime(currentEntry.created_at);
    modalEl.classList.add("show");
    modalEl.setAttribute("aria-hidden", "false");
    await loadComments(currentEntry.id);
  }

  function closeModal() {
    if (!modalEl) return;
    modalEl.classList.remove("show");
    modalEl.setAttribute("aria-hidden", "true");
    currentEntry = null;
  }

  async function likeCurrentEntry() {
    if (!currentEntry) return;
    await fetch("/api/scrapbook/reactions", {
      method: "POST",
      headers: requestHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ entry_id: Number(currentEntry.id), reaction: "heart" }),
    });
  }

  async function sendComment() {
    if (!currentEntry || !commentInput) return;
    const text = String(commentInput.value || "").trim();
    if (!text) return;
    const res = await fetch("/api/scrapbook/comments", {
      method: "POST",
      headers: requestHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ entry_id: Number(currentEntry.id), text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      alert(data.error || "Could not send comment.");
      return;
    }
    commentInput.value = "";
    await loadComments(currentEntry.id);
  }

  async function copyProfileLink() {
    try {
      await navigator.clipboard.writeText(profileUrl);
      if (shareBtn) {
        shareBtn.setAttribute("title", "Link copied");
        const label = shareBtn.querySelector(".label");
        if (label) label.textContent = "Copied";
      }
      setTimeout(() => {
        if (shareBtn) {
          shareBtn.setAttribute("title", "Share Profile Link");
          const label = shareBtn.querySelector(".label");
          if (label) label.textContent = "Share Profile Link";
        }
      }, 1400);
    } catch (_) {
      window.prompt("Copy this profile link:", profileUrl);
    }
  }

  onReady(() => {
    applyTabSwitching();
    loadEntries();

    if (gridEl) {
      gridEl.addEventListener("click", (event) => {
        const item = event.target.closest(".profile-scrapbook-item");
        if (!item) return;
        const entryId = item.getAttribute("data-entry-id");
        if (!entryId) return;
        openModal(entryId);
      });
    }
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (modalEl) {
      modalEl.addEventListener("click", (event) => {
        if (event.target === modalEl) closeModal();
      });
    }
    if (likeBtn) likeBtn.addEventListener("click", likeCurrentEntry);
    if (commentSend) commentSend.addEventListener("click", sendComment);
    if (commentInput) {
      commentInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          sendComment();
        }
      });
    }
    if (shareBtn) shareBtn.addEventListener("click", copyProfileLink);
  });
})();
