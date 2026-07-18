(function () {
  const gridEl = document.getElementById("communityFeedGrid");
  if (!gridEl) return;
  const scopeChipsEl = document.getElementById("communityFeedScopeChips");

  const modalEl = document.getElementById("communityFeedModal");
  const closeEl = document.getElementById("communityModalClose");
  const imageEl = document.getElementById("communityModalImage");
  const avatarEl = document.getElementById("communityModalAvatar");
  const userEl = document.getElementById("communityModalUser");
  const captionEl = document.getElementById("communityModalCaption");
  const likeBtnEl = document.getElementById("communityModalLikeBtn");
  const likeCountEl = document.getElementById("communityModalLikeCount");
  const commentsEl = document.getElementById("communityModalComments");
  const commentInputEl = document.getElementById("communityModalCommentInput");
  const commentSendEl = document.getElementById("communityModalCommentSend");

  let posts = [];
  let currentPost = null;
  let activeScope = "community";

  function esc(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function demoHeaders(extra) {
    const headers = extra ? { ...extra } : {};
    if (window.CSRF_TOKEN) headers["X-CSRF-Token"] = window.CSRF_TOKEN;
    const demoId = sessionStorage.getItem("demo_user_id");
    if (demoId) headers["X-Demo-User"] = demoId;
    return headers;
  }

  function fallbackAvatar(name) {
    return "https://api.dicebear.com/7.x/avataaars/svg?seed=" + encodeURIComponent(name || "User");
  }

  function renderGrid() {
    if (!Array.isArray(posts) || posts.length === 0) {
      gridEl.innerHTML = '<div class="feed-empty">No community posts yet.</div>';
      return;
    }
    gridEl.innerHTML = posts
      .map((post) => {
        const image = post.media_url || "";
        return (
          '<button type="button" class="feed-tile" data-post-id="' + Number(post.id) + '">' +
            (image
              ? '<img src="' + esc(image) + '" alt="' + esc(post.caption || "Community post") + '">'
              : '<img src="/static/images/avatar-placeholder.svg" alt="No image">') +
            '<div class="feed-tile-overlay"><span>\u2764 ' + Number(post.like_count || 0) + '</span><span>\ud83d\udcac ' + Number(post.comment_count || 0) + '</span></div>' +
          "</button>"
        );
      })
      .join("");
  }

  async function loadFeed() {
    gridEl.innerHTML = '<div class="feed-empty">Loading community feed...</div>';
    try {
      let loaded = [];
      if (activeScope === "community") {
        const res = await fetch("/api/feed/community", { headers: demoHeaders() });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
          gridEl.innerHTML = '<div class="feed-empty">Could not load feed.</div>';
          return;
        }
        loaded = Array.isArray(data.posts) ? data.posts : [];
      } else {
        const scope = activeScope === "friends" ? "friends" : "community";
        const res = await fetch("/api/feed?scope=" + encodeURIComponent(scope), { headers: demoHeaders() });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
          gridEl.innerHTML = '<div class="feed-empty">Could not load feed.</div>';
          return;
        }
        const featured = Array.isArray(data.featured) ? data.featured : [];
        const entries = Array.isArray(data.entries) ? data.entries : [];
        const mapped = entries.map((e) => ({
          id: e.id,
          media_url: e.media_url,
          caption: e.content || e.title || "",
          like_count: e.like_count || 0,
          comment_count: e.comment_count || 0,
          user: { username: e.owner_name || "User", avatar_url: e.owner_avatar || "" },
        }));
        const featuredMapped = featured.map((e) => ({
          id: e.id,
          media_url: e.media_url,
          caption: e.content || e.title || "",
          like_count: e.like_count || 0,
          comment_count: e.comment_count || 0,
          user: { username: e.owner_name || "User", avatar_url: e.owner_avatar || "" },
        }));
        loaded = activeScope === "featured" ? featuredMapped : mapped;
      }
      posts = loaded;
      renderGrid();
    } catch (err) {
      gridEl.innerHTML = '<div class="feed-empty">Could not load feed.</div>';
    }
  }

  function setComments(comments) {
    if (!commentsEl) return;
    if (!Array.isArray(comments) || comments.length === 0) {
      commentsEl.innerHTML = '<div class="community-comment-item">No comments yet.</div>';
      return;
    }
    commentsEl.innerHTML = comments
      .map((c) => {
        const name = (c.user && c.user.username) || "User";
        return (
          '<div class="community-comment-item"><strong>' +
          esc(name) +
          ":</strong> " +
          esc(c.body || "") +
          "</div>"
        );
      })
      .join("");
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
    currentPost = null;
  }

  async function showPost(postId) {
    const res = await fetch("/api/posts/" + encodeURIComponent(postId), { headers: demoHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) return;

    currentPost = data;
    const username = (data.user && data.user.username) || "User";
    const avatar = (data.user && data.user.avatar_url) || fallbackAvatar(username);
    if (imageEl) imageEl.src = data.media_url || "/static/images/avatar-placeholder.svg";
    if (avatarEl) avatarEl.src = avatar;
    if (userEl) userEl.textContent = username;
    if (captionEl) captionEl.textContent = data.caption || "";
    if (likeCountEl) likeCountEl.textContent = String(Number(data.like_count || 0));
    if (likeBtnEl) likeBtnEl.innerHTML = (data.is_liked ? "&#x2764; Liked" : "&#x2764; Like");
    setComments(data.comments || []);
    openModal();
  }

  async function toggleLike() {
    if (!currentPost) return;
    try {
      if (likeBtnEl) likeBtnEl.disabled = true;
      const res = await fetch("/api/posts/" + encodeURIComponent(currentPost.id) + "/like", {
        method: "POST",
        headers: demoHeaders({ "Content-Type": "application/json" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        alert((data && data.error) || "Could not like this post.");
        return;
      }
      currentPost.like_count = Number(data.like_count || 0);
      currentPost.is_liked = Boolean(data.is_liked);
      if (likeCountEl) likeCountEl.textContent = String(currentPost.like_count);
      if (likeBtnEl) likeBtnEl.innerHTML = (currentPost.is_liked ? "&#x2764; Liked" : "&#x2764; Like");
      const idx = posts.findIndex((p) => Number(p.id) === Number(currentPost.id));
      if (idx >= 0) {
        posts[idx].like_count = currentPost.like_count;
        posts[idx].is_liked = currentPost.is_liked;
        renderGrid();
      }
    } catch (_) {
      alert("Could not like this post.");
    } finally {
      if (likeBtnEl) likeBtnEl.disabled = false;
    }
  }

  async function sendComment() {
    if (!currentPost || !commentInputEl) return;
    const text = String(commentInputEl.value || "").trim();
    if (!text) return;
    try {
      if (commentSendEl) commentSendEl.disabled = true;
      const res = await fetch("/api/posts/" + encodeURIComponent(currentPost.id) + "/comments", {
        method: "POST",
        headers: demoHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ text }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        alert((data && data.error) || "Could not send comment.");
        return;
      }
      commentInputEl.value = "";
      currentPost.comments = Array.isArray(currentPost.comments) ? currentPost.comments : [];
      if (data.comment) currentPost.comments.push(data.comment);
      currentPost.comment_count = Number(data.comment_count || currentPost.comments.length || 0);
      setComments(currentPost.comments);
      const idx = posts.findIndex((p) => Number(p.id) === Number(currentPost.id));
      if (idx >= 0) {
        posts[idx].comment_count = currentPost.comment_count;
        renderGrid();
      }
    } catch (_) {
      alert("Could not send comment.");
    } finally {
      if (commentSendEl) commentSendEl.disabled = false;
    }
  }

  gridEl.addEventListener("click", (e) => {
    const tile = e.target.closest("[data-post-id]");
    if (!tile) return;
    const postId = tile.getAttribute("data-post-id");
    if (postId) showPost(postId);
  });
  if (closeEl) closeEl.addEventListener("click", closeModal);
  if (modalEl) {
    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) closeModal();
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modalEl && modalEl.classList.contains("show")) closeModal();
  });
  if (likeBtnEl) likeBtnEl.addEventListener("click", toggleLike);
  if (commentSendEl) commentSendEl.addEventListener("click", sendComment);
  if (commentInputEl) {
    commentInputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendComment();
      }
    });
  }

  scopeChipsEl?.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-scope]");
    if (!chip) return;
    const scope = chip.getAttribute("data-scope") || "community";
    activeScope = scope;
    scopeChipsEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    loadFeed();
  });

  loadFeed();
})();
