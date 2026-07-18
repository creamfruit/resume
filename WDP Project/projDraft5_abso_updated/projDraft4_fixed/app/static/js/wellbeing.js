function demoHeaders(extra) {
  const headers = extra ? { ...extra } : {};
  const demoId = sessionStorage.getItem('demo_user_id');
  if (demoId) headers['X-Demo-User'] = demoId;
  return headers;
}

function moodText(mood) {
  const map = {
    happy: '😊 Happy',
    good: '🙂 Good',
    neutral: '😐 Neutral',
    stressed: '😟 Stressed',
    sad: '😞 Sad'
  };
  return map[mood] || '😐 Neutral';
}

function recoIcon(type) {
  const iconMap = { circle: '📚', forum: '🧠', challenge: '🎯', match: '🤝' };
  return iconMap[type] || '💬';
}

document.addEventListener('DOMContentLoaded', function () {
  const scoreEl = document.getElementById('wb-score');
  const currentChip = document.getElementById('wb-current-chip');
  const updatedChip = document.getElementById('wb-updated-chip');
  const trendChip = document.getElementById('wb-trend-chip');
  const trendLine = document.getElementById('wb-trend-line');
  const breakdownEl = document.getElementById('wb-breakdown');
  const circlesEl = document.getElementById('wb-circles');
  const messagesEl = document.getElementById('wb-messages');
  const challengesEl = document.getElementById('wb-challenges');
  const miniNudgeEl = document.getElementById('wb-mini-nudge');
  const insightsEl = document.getElementById('wb-insights');
  const recosEl = document.getElementById('wellbeing-recos');
  const riskBanner = document.getElementById('wb-risk-banner');
  const riskList = document.getElementById('wb-risk-list');
  const badgesEl = document.getElementById('wb-badges');
  const journalList = document.getElementById('wb-journal-list');
  const journalSaveBtn = document.getElementById('wb-journal-save');
  const journalPrompt = document.getElementById('wb-journal-prompt');
  const journalGratitude = document.getElementById('wb-journal-gratitude');
  const journalReflection = document.getElementById('wb-journal-reflection');
  const moodButtons = document.querySelectorAll('.mood-btn');

  function renderTrendBars(points) {
    if (!trendLine) return;
    if (!Array.isArray(points) || !points.length) {
      trendLine.innerHTML = '<div class="muted">No mood data yet.</div>';
      return;
    }
    trendLine.innerHTML = points.map(p => {
      const v = typeof p.value === 'number' ? p.value : 0;
      const h = Math.max(4, Math.round((v / 5) * 100));
      const cls = typeof p.value === 'number' ? 'bar has-value' : 'bar';
      return `<div class="${cls}" style="height:${h}%"></div>`;
    }).join('');
  }

  function renderBreakdown(rows) {
    if (!breakdownEl) return;
    if (!Array.isArray(rows) || !rows.length) {
      breakdownEl.innerHTML = '<div class="muted">No emotion data yet.</div>';
      return;
    }
    breakdownEl.innerHTML = rows.map(r => (
      '<div class="breakdown-row">' +
      `<div>${r.emoji || ''} ${r.label || ''}</div>` +
      '<div class="breakdown-track"><div class="breakdown-fill" style="width:' + (r.pct || 0) + '%"></div></div>' +
      '<div>' + (r.pct || 0) + '%</div>' +
      '</div>'
    )).join('');
  }

  function renderInsights(insights) {
    if (!insightsEl) return;
    if (!Array.isArray(insights) || !insights.length) {
      insightsEl.innerHTML = '<div class="muted">No insights yet.</div>';
      return;
    }
    insightsEl.innerHTML = insights.map(t => `<div class="insight-item">${t}</div>`).join('');
  }

  function renderRecos(recos) {
    if (!recosEl) return;
    if (!Array.isArray(recos) || !recos.length) {
      recosEl.innerHTML = '<div class="muted">No recommendations yet.</div>';
      return;
    }
    recosEl.innerHTML = recos.map(r => (
      '<a class="support-action" href="' + (r.link || '#') + '">' +
      '<span class="icon">' + recoIcon(r.type) + '</span>' +
      '<span>' + (r.title || 'Recommendation') + '</span>' +
      '</a>'
    )).join('');
  }

  function renderRisk(risk) {
    if (riskBanner) {
      if (risk && risk.show) {
        riskBanner.style.display = '';
        riskBanner.textContent = '⚠ ' + (risk.message || 'We are here for you.');
      } else {
        riskBanner.style.display = 'none';
        riskBanner.textContent = '';
      }
    }
    if (!riskList) return;
    const items = [];
    if (risk && risk.show) {
      items.push('Talk to a buddy in Messages.');
      items.push('Join a support-focused learning circle.');
      items.push('Use reflection journaling to process the day.');
    } else {
      items.push('No active risk streak detected.');
      items.push('Maintain your momentum with one positive social action.');
    }
    riskList.innerHTML = items.map(t => `<div class="risk-item">${t}</div>`).join('');
  }

  function renderBadges(badges) {
    if (!badgesEl) return;
    if (!Array.isArray(badges) || !badges.length) {
      badgesEl.innerHTML = '<div class="muted">No badges yet.</div>';
      return;
    }
    badgesEl.innerHTML = badges.map(b => (
      '<div class="wb-badge ' + (b.unlocked ? '' : 'locked') + '">' +
      (b.unlocked ? '🏅 ' : '🔒 ') + (b.name || 'Badge') +
      '</div>'
    )).join('');
  }

  function renderJournal(entries) {
    if (!journalList) return;
    if (!Array.isArray(entries) || !entries.length) {
      journalList.innerHTML = '<div class="muted">No journal entries yet.</div>';
      return;
    }
    journalList.innerHTML = entries.map(e => (
      '<div class="journal-item">' +
      '<div><strong>' + (e.prompt || 'Reflection') + '</strong></div>' +
      (e.gratitude ? '<div>Gratitude: ' + e.gratitude + '</div>' : '') +
      (e.reflection ? '<div>Reflection: ' + e.reflection + '</div>' : '') +
      '<div class="muted mt-1">' + (e.created_at || '') + '</div>' +
      '</div>'
    )).join('');
  }

  function renderHeader(data) {
    if (scoreEl) scoreEl.textContent = String(data.score || 0);
    if (currentChip) {
      const m = data.latest_checkin && data.latest_checkin.mood ? data.latest_checkin.mood : 'neutral';
      currentChip.textContent = 'Current: ' + moodText(m);
    }
    if (updatedChip) {
      updatedChip.textContent = 'Last check-in: ' + (data.last_updated_human || 'N/A');
    }
    if (trendChip) {
      const t = data.trend || {};
      trendChip.textContent = 'Trend: ' + (t.arrow || '➡') + ' ' + (t.label || 'Stable');
    }
  }

  function renderActivity(activity, nudge) {
    if (circlesEl) circlesEl.textContent = String((activity && activity.circles) || 0);
    if (messagesEl) messagesEl.textContent = String((activity && activity.messages) || 0);
    if (challengesEl) challengesEl.textContent = String((activity && activity.challenges) || 0);
    if (miniNudgeEl) miniNudgeEl.innerHTML = '<div class="insight-item">' + (nudge || 'Stay connected to keep your wellbeing strong.') + '</div>';
  }

  async function loadDashboard() {
    const res = await fetch('/api/wellbeing/dashboard', { headers: demoHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) return;
    renderHeader(data);
    renderTrendBars(data.line_points_30d || []);
    renderBreakdown(data.emotion_breakdown || []);
    renderActivity(data.activity || {}, data.nudge || '');
    renderInsights(data.insights || []);
    renderRecos(data.recommendations || []);
    renderRisk(data.risk || {});
    renderBadges(data.badges || []);
    moodButtons.forEach(btn => btn.classList.remove('active'));
    if (data.latest_checkin && data.latest_checkin.mood) {
      moodButtons.forEach(btn => {
        if ((btn.dataset.mood || '') === data.latest_checkin.mood) btn.classList.add('active');
      });
    }
  }

  async function loadJournal() {
    const res = await fetch('/api/wellbeing/journal', { headers: demoHeaders() });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) return;
    renderJournal(data.entries || []);
  }

  moodButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const mood = btn.dataset.mood || '';
      if (!mood) return;
      moodButtons.forEach(b => { b.disabled = true; });
      const res = await fetch('/api/wellbeing/checkin', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ mood: mood })
      });
      const out = await res.json().catch(() => ({}));
      moodButtons.forEach(b => { b.disabled = false; });
      if (!res.ok) {
        alert(out.error || 'Could not save check-in.');
        return;
      }
      await loadDashboard();
    });
  });

  if (journalSaveBtn) {
    journalSaveBtn.addEventListener('click', async () => {
      const payload = {
        prompt: journalPrompt ? journalPrompt.value.trim() : '',
        gratitude: journalGratitude ? journalGratitude.value.trim() : '',
        reflection: journalReflection ? journalReflection.value.trim() : ''
      };
      journalSaveBtn.disabled = true;
      const res = await fetch('/api/wellbeing/journal', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload)
      });
      const out = await res.json().catch(() => ({}));
      journalSaveBtn.disabled = false;
      if (!res.ok) {
        alert(out.error || 'Could not save reflection.');
        return;
      }
      if (journalPrompt) journalPrompt.value = '';
      if (journalGratitude) journalGratitude.value = '';
      if (journalReflection) journalReflection.value = '';
      await loadJournal();
      await loadDashboard();
    });
  }

  loadDashboard().catch(() => {});
  loadJournal().catch(() => {});
});
