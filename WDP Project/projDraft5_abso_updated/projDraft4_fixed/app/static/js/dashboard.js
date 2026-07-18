// Dashboard JavaScript

// Show main dashboard after welcome screen
window.addEventListener('DOMContentLoaded', function() {
  const welcomeScreen = document.getElementById('welcome-screen');
  const mainDashboard = document.getElementById('main-dashboard');

  function demoHeaders(extra) {
    const headers = extra ? { ...extra } : {};
    const demoId = sessionStorage.getItem('demo_user_id');
    if (demoId) headers['X-Demo-User'] = demoId;
    return headers;
  }

  // Show main dashboard after 2 seconds
  setTimeout(function() {
    mainDashboard.classList.remove('hidden');
  }, 2000);

  // Remove welcome screen from DOM after animation
  setTimeout(function() {
    if (welcomeScreen) {
      welcomeScreen.remove();
    }
  }, 2500);

  const nameEl = document.getElementById('user-name');
  const welcomeTimeEl = document.getElementById('welcome-time');
  const welcomeContext = document.getElementById('welcome-context');
  const welcomeSupport = document.getElementById('welcome-support');

  function timeGreeting(name) {
    const hour = new Date().getHours();
    if (hour < 12) return '🌅 Good Morning, ' + name;
    if (hour < 18) return '☀️ Good Afternoon, ' + name;
    return '🌙 Good Evening, ' + name;
  }

  if (nameEl || welcomeTimeEl) {
    fetch('/api/session', { headers: demoHeaders() })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        let currentName = 'User';
        if (data && data.logged_in && data.name) {
          currentName = data.name;
          if (nameEl) nameEl.textContent = data.name;
        }
        if (welcomeTimeEl) {
          const tg = timeGreeting(currentName);
          welcomeTimeEl.textContent = tg.split(',')[0];
        }

        const navAvatar = document.querySelector('img.nav-avatar');
        if (navAvatar) {
          if (data && data.logged_in && data.avatar_url) {
            navAvatar.src = data.avatar_url;
            navAvatar.dataset.sessionAvatar = '1';
          } else if (data && data.logged_in && data.name) {
            const generated = 'https://api.dicebear.com/7.x/avataaars/svg?seed=' + encodeURIComponent(data.name);
            navAvatar.src = generated;
            navAvatar.dataset.sessionAvatar = '1';
          }
        }
      })
      .catch(() => {});
  }

  const statConnections = document.getElementById('stat-connections');
  const statMemories = document.getElementById('stat-memories');
  const statRepoints = document.getElementById('stat-repoints');
  const statCircles = document.getElementById('stat-circles');
  const statBadges = document.getElementById('stat-badges');
  if (statConnections || statMemories || statRepoints || statCircles || statBadges) {
    fetch('/api/profile', { headers: demoHeaders() })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        if (!data || !data.ok || !data.profile) return;
        const profile = data.profile;
        if (statConnections) statConnections.textContent = profile.connections_count ?? statConnections.textContent;
        if (statMemories) statMemories.textContent = profile.memories_count ?? statMemories.textContent;
        if (statRepoints) statRepoints.textContent = profile.repoints ?? statRepoints.textContent;
        if (statCircles) statCircles.textContent = profile.circles_count ?? statCircles.textContent;
        if (statBadges) statBadges.textContent = profile.badges_count ?? statBadges.textContent;
      })
      .catch(() => {});
  }

  const connectionsCard = statConnections ? statConnections.closest('.stat-card') : null;
  const connModal = document.createElement('div');
  connModal.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,.52);display:none;align-items:center;justify-content:center;z-index:2600;';
  connModal.innerHTML = `
    <div style="width:min(760px,95vw);max-height:86vh;overflow:auto;background:#fff;border:2px solid #fed7aa;border-radius:16px;box-shadow:0 18px 48px rgba(0,0,0,.25);padding:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h3 style="margin:0;color:#0f172a;">Your Connections</h3>
        <button type="button" id="conn-close" style="border:1px solid #cbd5e1;background:#fff;border-radius:8px;padding:6px 10px;">Close</button>
      </div>
      <div id="conn-list"></div>
    </div>
  `;
  document.body.appendChild(connModal);
  const connList = connModal.querySelector('#conn-list');
  const connClose = connModal.querySelector('#conn-close');
  if (connClose) connClose.addEventListener('click', () => { connModal.style.display = 'none'; });
  connModal.addEventListener('click', (e) => { if (e.target === connModal) connModal.style.display = 'none'; });

  async function apiListConnections() {
    const res = await fetch('/api/matches', { headers: demoHeaders() });
    if (!res.ok) return [];
    return await res.json().catch(() => []);
  }
  async function apiOverview(matchId) {
    const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}/overview`, { headers: demoHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) return null;
    return data.profile || null;
  }
  async function apiRemoveConnection(matchId) {
    const res = await fetch(`/api/matches/${encodeURIComponent(matchId)}`, { method: 'DELETE', headers: demoHeaders() });
    return res.ok;
  }

  async function showConnectionOverview(row) {
    const profile = await apiOverview(row.match_id);
    if (!profile || !connList) return;
    const safeRows = (profile.safe_locations || []).map((s) => `<li>${s.place_name} (${s.station_name})</li>`).join('');
    connList.innerHTML = `
      <div style="margin-bottom:12px;">
        <button type="button" id="conn-back-list" style="border:1px solid #cbd5e1;background:#fff;border-radius:8px;padding:6px 10px;">Back to list</button>
      </div>
      <div style="display:grid;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <img src="${profile.avatar_url || ''}" alt="${profile.name}" style="width:56px;height:56px;border-radius:50%;border:2px solid #fdba74;">
          <div><div style="font-weight:800;">${profile.name || 'User'}</div><div style="color:#64748b;">${profile.member_type || 'Member'}</div></div>
        </div>
        <div><strong>Interests:</strong> ${(profile.interests || []).join(', ') || 'None'}</div>
        <div><strong>Can Teach:</strong> ${(profile.skills_teach || []).join(', ') || 'None'}</div>
        <div><strong>Wants to Learn:</strong> ${(profile.skills_learn || []).join(', ') || 'None'}</div>
        <div><strong>Middle Meetup Station:</strong> ${profile.midpoint_station || 'Not enough data yet'}</div>
        <div><strong>Safe Meetup Spots:</strong> ${safeRows ? `<ul style="margin:6px 0 0 18px;">${safeRows}</ul>` : 'None yet'}</div>
        <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px;">
          <button type="button" id="conn-open-profile" style="border:1px solid #0ea5e9;background:#eff6ff;color:#0369a1;border-radius:8px;padding:8px 12px;">Open Profile</button>
          <button type="button" id="conn-remove" style="border:1px solid #ef4444;background:#fef2f2;color:#b91c1c;border-radius:8px;padding:8px 12px;">Remove Connection</button>
        </div>
      </div>
    `;
    const back = connList.querySelector('#conn-back-list');
    const open = connList.querySelector('#conn-open-profile');
    const remove = connList.querySelector('#conn-remove');
    if (back) back.addEventListener('click', showConnectionsList);
    if (open) open.addEventListener('click', () => { window.location.href = profile.profile_url || '/profile'; });
    if (remove) {
      remove.addEventListener('click', async () => {
        if (!confirm(`Remove connection with ${profile.name}?`)) return;
        const ok = await apiRemoveConnection(row.match_id);
        if (!ok) return alert('Could not remove connection.');
        await showConnectionsList();
      });
    }
  }

  async function showConnectionsList() {
    if (!connList) return;
    const rows = await apiListConnections();
    if (!rows.length) {
      connList.innerHTML = '<div style=\"padding:10px;color:#64748b;\">No connections yet.</div>';
      return;
    }
    connList.innerHTML = rows.map((r) => `
      <button type=\"button\" class=\"conn-row\" data-match=\"${r.match_id}\" style=\"width:100%;display:flex;align-items:center;gap:10px;border:1px solid #e2e8f0;background:#fff;border-radius:10px;padding:10px;margin-bottom:8px;cursor:pointer;\">
        <img src=\"${r.avatar || ''}\" alt=\"${r.name}\" style=\"width:42px;height:42px;border-radius:50%;border:2px solid #fdba74;\">
        <div style=\"text-align:left;\"><div style=\"font-weight:700;color:#0f172a;\">${r.name}</div><div style=\"color:#64748b;font-size:0.9rem;\">${r.location || ''}</div></div>
      </button>
    `).join('');
    connList.querySelectorAll('.conn-row').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const matchId = btn.getAttribute('data-match');
        const row = rows.find((r) => r.match_id === matchId);
        if (row) await showConnectionOverview(row);
      });
    });
  }

  if (connectionsCard) {
    connectionsCard.style.cursor = 'pointer';
    connectionsCard.addEventListener('click', async () => {
      connModal.style.display = 'flex';
      await showConnectionsList();
    });
  }

  const wellbeingWidget = document.getElementById('wellbeing-widget');
  if (wellbeingWidget) {
    const moodButtons = wellbeingWidget.querySelectorAll('.mood-btn');
    const summary = document.getElementById('wellbeing-summary');
    const recosWrap = document.getElementById('wellbeing-recos');
    const currentEl = document.getElementById('wellbeing-current');
    const updatedEl = document.getElementById('wellbeing-last-updated');
    const trendEl = document.getElementById('wellbeing-trend');
    const weeklyMicroEl = document.getElementById('wellbeing-social');
    const nudgeEl = document.getElementById('wellbeing-nudge');
    const riskEl = document.getElementById('wellbeing-risk');
    let selectedMood = '';

    function moodLabel(mood) {
      const map = {
        happy: '😊 Feeling Happy Today',
        good: '🙂 Feeling Good',
        neutral: '😐 Feeling Neutral',
        stressed: '😟 Feeling Stressed',
        sad: '😞 Feeling Low'
      };
      return map[mood] || '😐 Feeling Neutral';
    }

    function renderSummary(checkin, insight) {
      if (!summary) return;
      if (!checkin) {
        summary.style.display = 'none';
        return;
      }
      summary.textContent = (insight || '').trim();
      summary.style.display = '';
    }

    function renderWelcomeContext(data) {
      if (!welcomeContext) return;
      const checkin = data && data.latest_checkin ? data.latest_checkin : null;
      const mood = checkin && checkin.mood ? checkin.mood : 'neutral';
      const activity = data && data.activity ? data.activity : { circles: 0, messages: 0, challenges: 0 };
      const risk = data && data.risk ? data.risk : null;
      let line = 'Ready to connect and learn today?';
      let supportLine = 'We are glad you are here.';
      if (risk && risk.show) {
        line = 'We are here to support you and take things at your pace.';
        supportLine = 'A gentle step today is enough.';
      } else if (mood === 'happy' || mood === 'good') {
        line = 'Great to see you feeling positive today.';
        supportLine = 'Your positive energy can brighten someone’s day.';
      } else if (mood === 'stressed' || mood === 'sad') {
        line = 'You are not alone today.';
        supportLine = 'Take one calm step and we will support you.';
      } else if ((activity.circles || 0) === 0 && (activity.messages || 0) === 0) {
        line = 'It has been a while. Let’s reconnect gently.';
        supportLine = 'A short hello can make a meaningful difference.';
      }
      welcomeContext.textContent = line;
      if (welcomeSupport) welcomeSupport.textContent = supportLine;
    }

    function renderRecos(recos) {
      if (!recosWrap) return;
      if (!recos || !recos.length) {
        recosWrap.style.display = 'none';
        return;
      }
      const iconMap = {
        circle: '📚',
        forum: '🧠',
        challenge: '🎯',
        match: '🤝'
      };
      recosWrap.innerHTML = recos.map(r => (
        '<a class="support-action" href="' + (r.link || '#') + '">' +
          '<span class="icon">' + (iconMap[r.type] || '💬') + '</span>' +
          '<span>' + r.title + '</span>' +
        '</a>'
      )).join('');
      recosWrap.style.display = '';
    }

    function setCheckedIn(checkin, insight, recos) {
      moodButtons.forEach(btn => btn.classList.remove('active'));
      if (checkin && checkin.mood) {
        moodButtons.forEach(btn => {
          if ((btn.dataset.mood || '') === checkin.mood) btn.classList.add('active');
        });
      }
      renderSummary(checkin, insight);
      renderRecos(recos);
    }

    function loadSummary() {
      fetch('/api/wellbeing/dashboard', { headers: demoHeaders() })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (!data || !data.ok) return;
          const checkin = data.latest_checkin || null;
          if (currentEl && checkin) currentEl.textContent = moodLabel(checkin.mood);
          if (updatedEl) updatedEl.textContent = 'Last check-in: ' + (data.last_updated_human || 'No check-ins yet');
          if (trendEl && data.trend) trendEl.innerHTML = '<span>' + (data.trend.arrow || '➡') + '</span><span>' + (data.trend.label || 'Stable') + '</span>';
          if (weeklyMicroEl && data.activity) {
            weeklyMicroEl.textContent = 'This week: ' +
              String(data.activity.circles || 0) + ' circles • ' +
              String(data.activity.messages || 0) + ' messages • ' +
              String(data.activity.challenges || 0) + ' challenges';
          }
          if (nudgeEl) nudgeEl.textContent = data.nudge || 'You have been quiet this week - reconnect when you feel ready.';
          renderWelcomeContext(data);
          if (riskEl) {
            if (data.risk && data.risk.show) {
              riskEl.style.display = '';
              riskEl.textContent = '⚠ ' + (data.risk.message || 'We are here for you — explore support circles.');
            } else {
              riskEl.style.display = 'none';
              riskEl.textContent = '';
            }
          }
          const trendSentence = 'Trend: ' + ((data.trend && data.trend.label) || 'Stable') + ' this week.';
          if (checkin) {
            setCheckedIn(checkin, trendSentence, data.recommendations || []);
          } else {
            renderSummary({ mood: 'neutral' }, trendSentence);
            renderRecos(data.recommendations || []);
          }
        })
        .catch(() => {});
    }

    moodButtons.forEach(btn => {
      btn.addEventListener('click', async () => {
        selectedMood = btn.dataset.mood || '';
        if (!selectedMood) return;
        moodButtons.forEach(b => { b.disabled = true; });
        const payload = {
          mood: selectedMood
        };
        const res = await fetch('/api/wellbeing/checkin', {
          method: 'POST',
          headers: demoHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify(payload)
        });
        const out = await res.json().catch(() => ({}));
        if (!res.ok) {
          moodButtons.forEach(b => { b.disabled = false; });
          alert(out.error || 'Could not save check-in.');
          return;
        }
        setCheckedIn({ mood: selectedMood }, out.insight || '', out.recommendations || []);
        moodButtons.forEach(b => { b.disabled = false; });
        loadSummary();
      });
    });

    loadSummary();
  }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});
