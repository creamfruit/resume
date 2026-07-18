function demoHeaders(extra) {
  const headers = extra ? { ...extra } : {};
  const demoId = sessionStorage.getItem('demo_user_id');
  if (demoId) headers['X-Demo-User'] = demoId;
  return headers;
}

document.addEventListener('DOMContentLoaded', function () {
  const grid = document.getElementById('scrapbookGrid');
  const form = document.getElementById('scrapbookForm');
  const addBtn = document.getElementById('addMemoryBtn');
  const saveBtn = document.getElementById('saveMemoryBtn');
  const cancelBtn = document.getElementById('cancelMemoryBtn');
  const storyToggle = document.getElementById('storybookToggle');
  const storyForm = document.getElementById('storybookForm');
  const saveStoryBtn = document.getElementById('saveStoryBtn');
  const cancelStoryBtn = document.getElementById('cancelStoryBtn');
  const stage = document.getElementById('scrapbookStage');
  const leftPage = document.getElementById('scrapbookLeft');
  const rightPage = document.getElementById('scrapbookRight');
  const book = document.getElementById('scrapbookBook');
  const prevBtn = document.getElementById('prevPageBtn');
  const nextBtn = document.getElementById('nextPageBtn');
  const flip = document.getElementById('bookFlip');
  const coverPanel = document.getElementById('bookCoverPanel');
  const timeline = document.getElementById('scrapbookTimeline');

  let allEntries = [];
  let pageIndex = 0;
  const entriesPerPage = 1;

  function esc(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
  }

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Failed to read file.'));
      reader.readAsDataURL(file);
    });
  }

  function fmtDate(iso) {
    if (!iso) return '';
    try {
      const cleaned = String(iso).replace(/(\.\d{3})\d+/, '$1');
      const d = new Date(cleaned);
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
    } catch (e) {
      return iso;
    }
  }

  function entryHtml(e) {
    const hasImage = e.media_url && !e.media_url.toLowerCase().endsWith('.mp3') && !e.media_url.toLowerCase().endsWith('.wav') && !e.media_url.toLowerCase().endsWith('.ogg');
    let media = '';
    if (e.media_url) {
      const lower = e.media_url.toLowerCase();
      if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.ogg')) {
        media = '<audio controls style="width:100%"><source src="' + esc(e.media_url) + '"></audio>';
      }
    }
    const bannerImage = hasImage
      ? '<img src="' + esc(e.media_url) + '" alt="Memory banner">'
      : '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;height:100%;">' +
          '<div style="background:#fde2c7;"></div>' +
          '<div style="background:#d1fae5;"></div>' +
          '<div style="background:#fff7ed;"></div>' +
        '</div>';
    const banner = '<div class="memory-banner">' +
      '<span class="banner-tape"></span><span class="banner-tape right"></span>' +
      (bannerImage || '') +
    '</div>';
    const stickerMap = {
      chat: '💬 Chat',
      meetup: '📍 Meetup',
      circle: '📚 Circle',
      challenge: '🎯 Challenge',
      storybook: '📖 Storybook'
    };
    const ribbon = '<span class="memory-ribbon">' + (stickerMap[e.entry_type] || '✨ Memory') + '</span>';
    const date = '<span class="memory-date">🗓 ' + esc(fmtDate(e.created_at || '')) + '</span>';
    const moodClass = e.mood_tag ? ' mood-' + e.mood_tag : '';
    const classes = 'memory-card' + (e.pinned ? ' pinned' : '') + (e.related_user_id ? ' shared' : '') + moodClass + (e.featured ? ' featured' : '');
    const companion = e.related_user_id
      ? '<div class="companion-block"><img class="companion-avatar" src="https://api.dicebear.com/7.x/avataaars/svg?seed=' + esc(e.related_user_id) + '" alt="Companion"> Added together with your companion</div>'
      : '';
    const badge = e.entry_type === 'meetup'
      ? '<span class="badge">First Meetup</span>'
      : (e.entry_type === 'circle' ? '<span class="badge">Circle Memory</span>' : (e.entry_type === 'storybook' ? '<span class="badge">Storybook Page</span>' : ''));
    const featuredBanner = e.featured ? '<div class="featured-banner">✨ AI Highlight</div>' : '';
    return (
      '<div class="' + classes + '">' +
        '<div class="corner-stickers">❤️ ⭐ 🌼</div>' +
        banner +
        '<div class="memory-meta">' + ribbon + ' ' + date + '</div>' +
        featuredBanner +
        '<div class="memory-title">' + esc(e.title || '') + '</div>' +
        (e.mood_tag ? '<div class="memory-sticker">Mood: ' + esc(e.mood_tag) + '</div>' : '') +
        (e.location ? '<div class="memory-sticker">📍 ' + esc(e.location) + '</div>' : '') +
        badge +
        (e.content ? '<div class="memory-content">' + esc(e.content) + '</div>' : '') +
        media +
        companion +
        '<div class="memory-actions">' +
          '<button class="btn btn-outline-teal btn-sm reaction-btn" data-reaction="heart">❤️</button>' +
          '<button class="btn btn-outline-teal btn-sm reaction-btn" data-reaction="star">⭐</button>' +
          '<button class="btn btn-outline-teal btn-sm reaction-btn" data-reaction="thumbs">👍</button>' +
          '<button class="btn btn-outline-teal btn-sm pin-btn" data-entry="' + esc(e.id) + '" data-pinned="' + (e.pinned ? '1' : '0') + '">' + (e.pinned ? 'Unpin' : 'Pin') + '</button>' +
        '</div>' +
      '</div>'
    );
  }

  function renderGrid() {
    if (!grid) return;
    if (!allEntries.length) {
      grid.innerHTML = '<div class="muted">No memories yet.</div>';
      return;
    }
    const pinned = allEntries.filter(e => e.pinned);
    const rest = allEntries.filter(e => !e.pinned);
    const featured = rest.length ? entryHtml({ ...rest[0], featured: true }) : '';
    const featuredBlock = featured
      ? '<div class="timeline-divider"><span>Featured Memory</span></div>' + featured
      : '';
    const pinnedBlock = pinned.length
      ? '<div class="timeline-divider"><span>Pinned Memories</span></div><div class="pinned-row">' + pinned.map(e => entryHtml({ ...e, featured: true })).join('') + '</div>'
      : '';
    const remaining = rest.length ? rest.slice(1).map(entryHtml).join('') : '';
    grid.innerHTML = featuredBlock + pinnedBlock + remaining;
  }

  function renderTimeline() {
    if (!timeline) return;
    if (!allEntries.length) {
      timeline.innerHTML = '<div class="muted">No memories yet.</div>';
      return;
    }
    const items = [];
    let firstMeetup = false;
    allEntries.forEach((e, idx) => {
      if (idx === 0) {
        items.push('<div class="timeline-divider"><span>Newest Memories</span></div>');
      }
      if (e.entry_type === 'meetup' && !firstMeetup) {
        firstMeetup = true;
        items.push('<div class="timeline-divider"><span>First Meetup</span></div>');
      }
      if (idx === 4) {
        items.push('<div class="timeline-divider"><span>30 Days Friends</span></div>');
      }
      items.push('<div class="timeline-item">' + entryHtml(e) + '</div>');
    });
    timeline.innerHTML = items.join('');
  }

  function renderPages() {
    if (!leftPage || !rightPage) return;
    if (!allEntries.length) {
      leftPage.innerHTML = '<div class="muted">No memories yet. Add your first memory!</div>';
      rightPage.innerHTML = '<div class="muted">Your story begins here.</div>';
      return;
    }
    const pinned = allEntries.filter(e => e.pinned);
    const rest = allEntries.filter(e => !e.pinned);
    const featured = rest.length ? entryHtml({ ...rest[0], featured: true }) : '';
    const pinnedBlock = pinned.length
      ? pinned.map(e => entryHtml({ ...e, featured: true })).join('')
      : '';
    const leftPool = [];
    if (pinnedBlock) leftPool.push(pinnedBlock);
    if (featured) leftPool.push(featured);
    const leftItems = leftPool.join('');
    const rightPool = featured ? rest.slice(1) : rest;
    const rightItems = rightPool.length ? rightPool.map(entryHtml) : [];
    const allRight = rightItems;
    const start = pageIndex * entriesPerPage;
    const pageRight = allRight.slice(start, start + entriesPerPage).join('');
    leftPage.innerHTML = leftItems || '<div class="muted">Pin a memory to feature it here.</div>';
    rightPage.innerHTML = pageRight || '<div class="muted">No more memories on this page.</div>';
  }

  function maxPageIndex() {
    const restCount = allEntries.filter(e => !e.pinned).length;
    const rightCount = restCount > 0 ? restCount - 1 : 0;
    const total = Math.max(1, Math.ceil(rightCount / entriesPerPage));
    return Math.max(0, total - 1);
  }

  function animateFlip(dir) {
    if (!flip) return;
    flip.classList.remove('animate-next', 'animate-prev', 'active');
    void flip.offsetWidth;
    flip.classList.add('active', dir === 'next' ? 'animate-next' : 'animate-prev');
    setTimeout(() => flip.classList.remove('active', 'animate-next', 'animate-prev'), 650);
  }

  function nextPage() {
    if (pageIndex >= maxPageIndex()) return;
    pageIndex += 1;
    animateFlip('next');
    renderPages();
  }

  function prevPage() {
    if (pageIndex <= 0) return;
    pageIndex -= 1;
    animateFlip('prev');
    renderPages();
  }
  async function loadEntries() {
    const res = await fetch('/api/scrapbook/entries', { headers: demoHeaders() });
    const out = await res.json().catch(() => ({}));
    if (!res.ok || !out.ok) {
      if (leftPage) leftPage.innerHTML = '<div class="muted">Could not load memories.</div>';
      if (rightPage) rightPage.innerHTML = '';
      return;
    }
    allEntries = out.entries || [];
    pageIndex = 0;
    renderPages();
    renderTimeline();
    renderGrid();
  }

  if (addBtn) addBtn.addEventListener('click', () => {
    if (form) form.style.display = '';
  });
  if (cancelBtn) cancelBtn.addEventListener('click', () => {
    if (form) form.style.display = 'none';
  });

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const title = document.getElementById('memory-title')?.value.trim() || '';
      const entryType = document.getElementById('memory-type')?.value || 'chat';
      const visibility = document.getElementById('memory-visibility')?.value || 'private';
      const content = document.getElementById('memory-content')?.value.trim() || '';
      const mediaUrlInput = document.getElementById('memory-media')?.value.trim() || '';
      const fileInput = document.getElementById('memory-file');
      let mediaUrl = mediaUrlInput;
      if (fileInput && fileInput.files && fileInput.files[0]) {
        try {
          mediaUrl = await readFileAsDataUrl(fileInput.files[0]);
        } catch (err) {
          return alert('Could not read the selected file.');
        }
      }
      const moodTag = document.getElementById('memory-mood')?.value || '';
      const location = document.getElementById('memory-location')?.value || '';
      if (!title) return alert('Title is required.');
      const res = await fetch('/api/scrapbook/entries', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          title,
          entry_type: entryType,
          visibility,
          content,
          media_url: mediaUrl,
          mood_tag: moodTag,
          location: location
        })
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok || !out.ok) return alert(out.error || 'Could not save memory.');
      if (form) form.style.display = 'none';
      if (fileInput) fileInput.value = '';
      await loadEntries();
      const firstCard = document.querySelector('.memory-card');
      if (firstCard) firstCard.classList.add('memory-new');
    });
  }

  if (storyToggle && storyForm) {
    storyToggle.addEventListener('click', () => {
      storyForm.style.display = storyForm.style.display === 'none' ? '' : 'none';
    });
  }
  if (cancelStoryBtn && storyForm) {
    cancelStoryBtn.addEventListener('click', () => {
      storyForm.style.display = 'none';
    });
  }
  if (saveStoryBtn) {
    saveStoryBtn.addEventListener('click', async () => {
      const title = document.getElementById('story-title')?.value.trim() || '';
      const place = document.getElementById('story-place')?.value.trim() || '';
      const event = document.getElementById('story-event')?.value.trim() || '';
      const feeling = document.getElementById('story-feeling')?.value.trim() || '';
      const lesson = document.getElementById('story-lesson')?.value.trim() || '';
      const mediaUrlInput = document.getElementById('story-media-url')?.value.trim() || '';
      const storyFile = document.getElementById('story-media-file');
      let mediaUrl = mediaUrlInput;
      if (storyFile && storyFile.files && storyFile.files[0]) {
        try {
          mediaUrl = await readFileAsDataUrl(storyFile.files[0]);
        } catch (err) {
          return alert('Could not read the selected photo.');
        }
      }
      if (!title) return alert('Story title is required.');
      const res = await fetch('/api/storybook/create', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          title,
          place,
          event,
          feeling,
          lesson,
          media_url: mediaUrl
        })
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok || !out.ok) return alert(out.error || 'Could not save storybook.');
      if (storyForm) storyForm.style.display = 'none';
      if (storyFile) storyFile.value = '';
      await loadEntries();
    });
  }

  if (coverPanel) {
    coverPanel.addEventListener('click', () => {
      coverPanel.classList.add('open');
      setTimeout(() => {
        coverPanel.style.display = 'none';
      }, 950);
    });
  }

  if (nextBtn) nextBtn.addEventListener('click', nextPage);
  if (prevBtn) prevBtn.addEventListener('click', prevPage);

  document.addEventListener('click', async (e) => {
    const reaction = e.target.closest('.reaction-btn');
    if (reaction) {
      reaction.classList.add('active');
      setTimeout(() => reaction.classList.remove('active'), 400);
      return;
    }
    const pinBtn = e.target.closest('.pin-btn');
    if (pinBtn) {
      const entryId = pinBtn.getAttribute('data-entry');
      const isPinned = pinBtn.getAttribute('data-pinned') === '1';
      const shouldPin = !isPinned;
      await fetch('/api/scrapbook/pin', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ entry_id: Number(entryId), pinned: shouldPin })
      });
      loadEntries();
    }
  });

  loadEntries();
});
