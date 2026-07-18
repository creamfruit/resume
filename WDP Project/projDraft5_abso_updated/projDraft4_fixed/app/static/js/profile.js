// Profile Page Tab Switching

function demoHeaders(extra) {
  const headers = extra ? { ...extra } : {};
  if (window.CSRF_TOKEN) headers['X-CSRF-Token'] = window.CSRF_TOKEN;
  const demoId = sessionStorage.getItem('demo_user_id');
  if (demoId) headers['X-Demo-User'] = demoId;
  return headers;
}

document.addEventListener('DOMContentLoaded', function() {
  const tabBtns = document.querySelectorAll('.profile-tab-btn');
  const tabContents = document.querySelectorAll('.profile-tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const tabName = this.dataset.tab;

      // Remove active from all
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      // Add active to clicked
      this.classList.add('active');
      const targetContent = document.getElementById(`tab-${tabName}`);
      if (targetContent) {
        targetContent.classList.add('active');
      }

      // Scroll to top
      window.scrollTo({ top: 200, behavior: 'smooth' });
    });
  });

  // Load profile data
  loadProfile();

  // Edit Bio functionality
  const editBioBtn = document.getElementById('edit-bio-btn');
  if (editBioBtn) {
    editBioBtn.addEventListener('click', function() {
      const bioText = document.getElementById('bio-text');
      if (!bioText) return;

      const currentBio = bioText.textContent || '';
      const textarea = document.createElement('textarea');
      textarea.value = currentBio;
      textarea.className = 'bio-edit-textarea';
      textarea.rows = 4;
      textarea.style.width = '100%';
      textarea.style.marginBottom = '10px';

      const saveBtn = document.createElement('button');
      saveBtn.textContent = 'Save';
      saveBtn.className = 'btn bio-save-btn';

      const cancelBtn = document.createElement('button');
      cancelBtn.textContent = 'Cancel';
      cancelBtn.className = 'btn btn-secondary bio-cancel-btn';

      const buttonContainer = document.createElement('div');
      buttonContainer.className = 'bio-action-buttons';
      buttonContainer.appendChild(saveBtn);
      buttonContainer.appendChild(cancelBtn);

      // Replace bio text with textarea and buttons
      bioText.style.display = 'none';
      editBioBtn.style.display = 'none';
      bioText.parentNode.insertBefore(textarea, bioText);
      bioText.parentNode.insertBefore(buttonContainer, bioText);

      saveBtn.addEventListener('click', function() {
        const newBio = textarea.value.trim();
        updateBio(newBio);
      });

      cancelBtn.addEventListener('click', function() {
        // Restore original
        textarea.remove();
        buttonContainer.remove();
        bioText.style.display = '';
        editBioBtn.style.display = '';
      });
    });
  }

  document.querySelector('.btn-danger')?.addEventListener('click', function() {
    if (confirm('\u26A0\uFE0F Are you SURE you want to delete your account? This action cannot be undone.')) {
      alert('Account deletion process initiated. You will receive a confirmation email.');
    }
  });

  const mediaModal = document.getElementById('media-choice-modal');
  const mediaAvatarEditBtn = document.getElementById('media-choice-avatar-edit');
  const mediaCameraBtn = document.getElementById('media-choice-camera');
  const mediaUploadBtn = document.getElementById('media-choice-upload');
  const mediaCancelBtn = document.getElementById('media-choice-cancel');
  let activeMediaTarget = null;

  function openMediaModal(target) {
    activeMediaTarget = target;
    if (mediaAvatarEditBtn) {
      mediaAvatarEditBtn.style.display = target === 'avatar' ? '' : 'none';
    }
    if (mediaModal) {
      mediaModal.classList.add('show');
      mediaModal.setAttribute('aria-hidden', 'false');
    }
  }

  function closeMediaModal() {
    activeMediaTarget = null;
    if (mediaModal) {
      mediaModal.classList.remove('show');
      mediaModal.setAttribute('aria-hidden', 'true');
    }
  }

  if (mediaCancelBtn) mediaCancelBtn.addEventListener('click', closeMediaModal);
  if (mediaModal) {
    mediaModal.addEventListener('click', function (e) {
      if (e.target === mediaModal) closeMediaModal();
    });
  }

  const avatarBtn = document.getElementById('edit-avatar-btn');
  const bannerBtn = document.getElementById('edit-banner-btn');
  const avatarCamera = document.getElementById('avatar-input-camera');
  const avatarUpload = document.getElementById('avatar-input-upload');
  const bannerCamera = document.getElementById('banner-input-camera');
  const bannerUpload = document.getElementById('banner-input-upload');

  if (avatarBtn) avatarBtn.addEventListener('click', () => openMediaModal('avatar'));
  if (bannerBtn) bannerBtn.addEventListener('click', () => openMediaModal('banner'));

  if (mediaCameraBtn) {
    mediaCameraBtn.addEventListener('click', function () {
      if (activeMediaTarget === 'avatar' && avatarCamera) avatarCamera.click();
      if (activeMediaTarget === 'banner' && bannerCamera) bannerCamera.click();
      closeMediaModal();
    });
  }

  if (mediaUploadBtn) {
    mediaUploadBtn.addEventListener('click', function () {
      if (activeMediaTarget === 'avatar' && avatarUpload) avatarUpload.click();
      if (activeMediaTarget === 'banner' && bannerUpload) bannerUpload.click();
      closeMediaModal();
    });
  }

  if (mediaAvatarEditBtn) {
    mediaAvatarEditBtn.addEventListener('click', function () {
      closeMediaModal();
      window.location.href = '/signup-avatar?edit=1';
    });
  }

  async function handleAvatarUpload(input) {
    if (!input || !input.files || !input.files[0]) return;
    const form = new FormData();
    form.append('avatar', input.files[0]);
    const res = await fetch('/api/profile/avatar', { method: 'POST', headers: demoHeaders(), body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return alert(data.error || 'Could not upload avatar.');
    const img = document.getElementById('profile-avatar');
    if (img) img.src = data.url;
  }

  async function handleBannerUpload(input) {
    if (!input || !input.files || !input.files[0]) return;
    const form = new FormData();
    form.append('banner', input.files[0]);
    const res = await fetch('/api/profile/banner', { method: 'POST', headers: demoHeaders(), body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return alert(data.error || 'Could not upload banner.');
    const cover = document.getElementById('profile-cover');
    if (cover) cover.style.backgroundImage = `url('${data.url}')`;
  }

  if (avatarCamera) avatarCamera.addEventListener('change', () => handleAvatarUpload(avatarCamera));
  if (avatarUpload) avatarUpload.addEventListener('change', () => handleAvatarUpload(avatarUpload));
  if (bannerCamera) bannerCamera.addEventListener('change', () => handleBannerUpload(bannerCamera));
  if (bannerUpload) bannerUpload.addEventListener('change', () => handleBannerUpload(bannerUpload));

  const editTeach = document.getElementById('edit-skills-teach');
  if (editTeach) {
    editTeach.addEventListener('click', () => {
      window.location.href = '/onboarding?edit=1&step=3';
    });
  }

  const editLearn = document.getElementById('edit-skills-learn');
  if (editLearn) {
    editLearn.addEventListener('click', () => {
      window.location.href = '/onboarding?edit=1&step=4';
    });
  }

  const editInterests = document.getElementById('edit-interests');
  if (editInterests) {
    editInterests.addEventListener('click', () => {
      window.location.href = '/onboarding?edit=1&step=2';
    });
  }

  const editAvailability = document.getElementById('edit-availability');
  if (editAvailability) {
    editAvailability.addEventListener('click', () => {
      window.location.href = '/onboarding?edit=1&step=5&section=availability';
    });
  }

  const editLanguages = document.getElementById('edit-languages');
  if (editLanguages) {
    editLanguages.addEventListener('click', () => {
      window.location.href = '/onboarding?edit=1&step=5&section=languages';
    });
  }

  const safetyInfo = document.getElementById('safety-score-info');
  if (safetyInfo) {
    safetyInfo.addEventListener('click', () => {
      alert('Your Safety Score grows with positive activity (circles, good behavior) and drops with confirmed violations or no-shows.');
    });
  }

  const publicProfileToggle = document.getElementById('public-profile');
  if (publicProfileToggle) {
    publicProfileToggle.addEventListener('change', async () => {
      try {
        const res = await fetch('/api/profile/privacy', {
          method: 'POST',
          headers: demoHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ is_private: !publicProfileToggle.checked }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.ok === false) {
          alert(data.error || 'Could not update profile privacy.');
        }
      } catch (err) {
        alert('Could not update profile privacy.');
      }
    });
  }

  let reportConnections = [];
  async function loadReportConnections() {
    const select = document.getElementById('report-connection');
    if (!select) return;
    try {
      const res = await fetch('/api/matches', { headers: demoHeaders() });
      const items = await res.json().catch(() => []);
      reportConnections = Array.isArray(items) ? items : [];
      select.innerHTML = '<option value="">Select connection</option>';
      reportConnections.forEach((row) => {
        const opt = document.createElement('option');
        opt.value = row.match_id;
        opt.textContent = row.location ? `${row.name} (${row.location})` : row.name;
        select.appendChild(opt);
      });
    } catch (_) {
      select.innerHTML = '<option value="">Select connection</option>';
    }
  }
  loadReportConnections();

  const reportBtn = document.getElementById('submit-report');
  if (reportBtn) {
    reportBtn.addEventListener('click', async () => {
      const selectedConnectionId = (document.getElementById('report-connection')?.value || '').trim();
      const selectedConnection = reportConnections.find((row) => row.match_id === selectedConnectionId);
      const reason = (document.getElementById('report-reason')?.value || '').trim();
      const date = (document.getElementById('report-date')?.value || '').trim();
      const details = (document.getElementById('report-details')?.value || '').trim();
      if (!reason || !date) return alert('Please select a reason and date.');
      const enrichedDetails = selectedConnection
        ? `Connection: ${selectedConnection.name} (${selectedConnection.match_id})\n${details}`
        : details;
      const res = await fetch('/api/report', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ reason: reason, incident_date: date, details: enrichedDetails })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return alert(data.error || 'Could not submit report.');
      alert('Report submitted. Our safety team will review it.');
      if (document.getElementById('report-connection')) document.getElementById('report-connection').value = '';
      if (document.getElementById('report-reason')) document.getElementById('report-reason').value = '';
      if (document.getElementById('report-date')) document.getElementById('report-date').value = '';
      if (document.getElementById('report-details')) document.getElementById('report-details').value = '';
    });
  }

  const blockBtn = document.getElementById('block-connection');
  if (blockBtn) {
    blockBtn.addEventListener('click', async () => {
      const selectedConnectionId = (document.getElementById('report-connection')?.value || '').trim();
      if (!selectedConnectionId) {
        alert('Select a connection first.');
        return;
      }
      const selectedConnection = reportConnections.find((row) => row.match_id === selectedConnectionId);
      const label = selectedConnection ? selectedConnection.name : selectedConnectionId;
      if (!confirm(`Block ${label}? This removes the match from your list.`)) return;
      const res = await fetch(`/api/matches/${encodeURIComponent(selectedConnectionId)}`, {
        method: 'DELETE',
        headers: demoHeaders(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return alert(data.error || 'Could not block this connection.');
      alert('Connection blocked.');
      await loadReportConnections();
      loadProfile();
    });
  }

  const saveEmergency = document.getElementById('save-emergency');
  const verifyPhoneInput = document.getElementById('verify-phone-number');
  if (verifyPhoneInput) {
    verifyPhoneInput.addEventListener('input', () => {
      verifyPhoneInput.value = verifyPhoneInput.value.replace(/\D/g, '');
    });
  }
  const emergencyPhoneInput = document.getElementById('emergency-phone');
  if (emergencyPhoneInput) {
    emergencyPhoneInput.addEventListener('input', () => {
      emergencyPhoneInput.value = emergencyPhoneInput.value.replace(/\D/g, '');
    });
  }
  if (saveEmergency) {
    saveEmergency.addEventListener('click', async () => {
      const name = (document.getElementById('emergency-name')?.value || '').trim();
      const relationship = (document.getElementById('emergency-relationship')?.value || '').trim();
      const countryCode = (document.getElementById('emergency-country-code')?.value || '+65').trim();
      const phone = (document.getElementById('emergency-phone')?.value || '').replace(/\D/g, '');
      await saveProfile({ emergency_contact: { name, relationship, country_code: countryCode, phone } });
    });
  }

  const linkNric = document.getElementById('link-nric');
  if (linkNric) {
    linkNric.addEventListener('click', async () => {
      await saveProfile({ verified_with: 'nric' });
    });
  }

  function refreshVerificationUiFromDomState() {
    const statusCard = document.getElementById('verification-status');
    const statusTitle = document.getElementById('verification-title');
    const statusDesc = document.getElementById('verification-desc');
    const statusDate = document.getElementById('verification-date');
    const emailRowSend = document.getElementById('email-verify-row-send');
    const emailRowConfirm = document.getElementById('email-verify-row-confirm');
    const verifyEmailInput = document.getElementById('verify-email');

    const emailVerified = !!(verifyEmailInput && verifyEmailInput.dataset.verified === '1');
    if (!emailVerified) return;

    if (statusCard) {
      statusCard.classList.remove('not-verified');
      statusCard.classList.add('verified');
    }
    if (statusTitle) statusTitle.textContent = 'Email Verified';
    if (statusDesc) statusDesc.textContent = 'Your email has been verified. You can continue with phone verification.';
    if (statusDate) statusDate.textContent = 'Verified';
    if (emailRowSend) emailRowSend.style.display = 'none';
    if (emailRowConfirm) emailRowConfirm.style.display = 'none';
  }

  function showVerificationPopup(message, title) {
    const modal = document.getElementById('verify-popup-modal');
    const titleEl = document.getElementById('verify-popup-title');
    const msgEl = document.getElementById('verify-popup-message');
    const okBtn = document.getElementById('verify-popup-ok');
    if (!modal || !msgEl || !okBtn) {
      alert(message || 'Done.');
      return;
    }
    if (titleEl) titleEl.textContent = title || 'Verification';
    msgEl.textContent = message || 'Done.';
    modal.classList.add('show');
    modal.setAttribute('aria-hidden', 'false');

    const close = () => {
      modal.classList.remove('show');
      modal.setAttribute('aria-hidden', 'true');
      okBtn.removeEventListener('click', close);
      modal.removeEventListener('click', onBackdrop);
    };
    const onBackdrop = (e) => {
      if (e.target === modal) close();
    };

    okBtn.addEventListener('click', close);
    modal.addEventListener('click', onBackdrop);
  }

  refreshVerificationUiFromDomState();

  const sendEmailVerify = document.getElementById('send-email-verify');
  if (sendEmailVerify) {
    sendEmailVerify.addEventListener('click', async () => {
      const res = await fetch('/api/verification/email/send', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return alert(data.error || 'Could not send email verification code.');
      const dev = document.getElementById('email-verify-dev-code');
      if (dev) {
        if (data.dev_code) {
          dev.value = data.dev_code;
          dev.style.display = '';
        } else {
          dev.value = '';
          dev.style.display = 'none';
        }
      }
      showVerificationPopup('Verification code sent to your email.', 'Email Verification');
    });
  }

  const confirmEmailVerify = document.getElementById('confirm-email-verify');
  if (confirmEmailVerify) {
    confirmEmailVerify.addEventListener('click', async () => {
      const code = (document.getElementById('email-verify-code')?.value || '').trim();
      const res = await fetch('/api/verification/email/verify', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ code }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return alert(data.error || 'Could not verify email.');
      const verifyEmailInput = document.getElementById('verify-email');
      if (verifyEmailInput) verifyEmailInput.dataset.verified = '1';
      refreshVerificationUiFromDomState();
      showVerificationPopup('Email verified.', 'Email Verification');
      loadProfile();
    });
  }

  const sendPhoneVerify = document.getElementById('send-phone-verify');
  if (sendPhoneVerify) {
    sendPhoneVerify.addEventListener('click', async () => {
      const country_code = (document.getElementById('verify-phone-country')?.value || '+65').trim();
      const phone_number = (document.getElementById('verify-phone-number')?.value || '').replace(/\D/g, '');
      const res = await fetch('/api/verification/phone/send', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ country_code, phone_number }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return alert(data.error || 'Could not send phone verification code.');
      const dev = document.getElementById('phone-verify-dev-code');
      if (dev) {
        if (data.dev_code) {
          dev.value = data.dev_code;
          dev.style.display = '';
        } else {
          dev.value = '';
          dev.style.display = 'none';
        }
      }
      showVerificationPopup('Verification code sent to your phone.', 'Phone Verification');
    });
  }

  const confirmPhoneVerify = document.getElementById('confirm-phone-verify');
  if (confirmPhoneVerify) {
    confirmPhoneVerify.addEventListener('click', async () => {
      const code = (document.getElementById('phone-verify-code')?.value || '').trim();
      const res = await fetch('/api/verification/phone/verify', {
        method: 'POST',
        headers: demoHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ code }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return alert(data.error || 'Could not verify phone.');
      showVerificationPopup('Phone verified.', 'Phone Verification');
      loadProfile();
    });
  }

  ['notif-messages','notif-matches','notif-circles','notif-challenges','notif-badges',
   'privacy-age','privacy-location','privacy-badges','privacy-direct'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        const notifications = {
          messages: !!document.getElementById('notif-messages')?.checked,
          matches: !!document.getElementById('notif-matches')?.checked,
          circles: !!document.getElementById('notif-circles')?.checked,
          challenges: !!document.getElementById('notif-challenges')?.checked,
          badges: !!document.getElementById('notif-badges')?.checked,
        };
        const privacy = {
          show_age: !!document.getElementById('privacy-age')?.checked,
          show_location: !!document.getElementById('privacy-location')?.checked,
          show_badges: !!document.getElementById('privacy-badges')?.checked,
          allow_direct: !!document.getElementById('privacy-direct')?.checked,
        };
        saveProfile({ notifications, privacy });
      });
    }
  });

  const MRT_STATIONS = [
    "Admiralty","Aljunied","Ang Mo Kio","Bartley","Bayfront","Beauty World","Bedok","Bedok North","Bedok Reservoir",
    "Bencoolen","Bendemeer","Bishan","Boon Keng","Boon Lay","Botanic Gardens","Braddell","Bras Basah","Bright Hill",
    "Bugis","Buona Vista","Buangkok","Bukit Batok","Bukit Gombak","Bukit Panjang","Caldecott","Canberra","Cashew",
    "Changi Airport","Chinatown","Choa Chu Kang","Chinese Garden","City Hall","Clarke Quay","Clementi","Commonwealth",
    "Dakota","Dhoby Ghaut","Dover","Downtown","Eunos","Expo","Farrer Park","Farrer Road","Fort Canning",
    "Gardens by the Bay","Geylang Bahru","Gul Circle","Great World","Havelock","Haw Par Villa","HarbourFront",
    "Hillview","Holland Village","Hougang","Jalan Besar","Joo Koon","Jurong East","Kaki Bukit","Kallang","Katong Park",
    "Kembangan","Kent Ridge","Khatib","King Albert Park","Kovan","Kranji","Labrador Park","Lakeside","Lavender",
    "Lentor","Little India","Lorong Chuan","MacPherson","Marina Bay","Marina South Pier","Marine Parade",
    "Marine Terrace","Marymount","Mattar","Maxwell","Mayflower","Mountbatten","Napier","Nicoll Highway","Novena",
    "one-north","Orchard","Orchard Boulevard","Outram Park","Pasir Panjang","Pasir Ris","Paya Lebar","Pioneer",
    "Potong Pasir","Promenade","Punggol","Queenstown","Raffles Place","Redhill","Rochor","Sembawang","Sengkang",
    "Serangoon","Shenton Way","Simei","Siglap","Sixth Avenue","Somerset","Springleaf","Stadium","Stevens","Tai Seng",
    "Tampines","Tampines East","Tampines West","Tan Kah Kee","Tanah Merah","Tanjong Katong","Tanjong Pagar",
    "Tanjong Rhu","Telok Ayer","Tiong Bahru","Toa Payoh","Tuas Crescent","Tuas Link","Tuas West Road",
    "Ubi","Upper Changi","Upper Thomson","Woodlands","Woodlands North","Woodlands South","Woodleigh","Yew Tee",
    "Yio Chu Kang","Yishun"
  ];
  const MRT_STATIONS_SORTED = MRT_STATIONS.slice().sort((a, b) => a.localeCompare(b));

  const MRT_LINE_GROUPS = [
    { key: "NSL", label: "North South", stations: ["Admiralty","Ang Mo Kio","Bishan","Braddell","Bukit Batok","Bukit Gombak","Canberra","Choa Chu Kang","City Hall","Dhoby Ghaut","Jurong East","Khatib","Kranji","Marina Bay","Marina South Pier","Novena","Orchard","Raffles Place","Sembawang","Somerset","Toa Payoh","Woodlands","Yew Tee","Yio Chu Kang","Yishun"] },
    { key: "EWL", label: "East West", stations: ["Aljunied","Bedok","Boon Lay","Bugis","Buona Vista","Changi Airport","Chinese Garden","City Hall","Clementi","Commonwealth","Dover","Eunos","Expo","Gul Circle","Joo Koon","Jurong East","Kallang","Kembangan","Lakeside","Lavender","Outram Park","Pasir Ris","Paya Lebar","Pioneer","Queenstown","Raffles Place","Redhill","Simei","Tanah Merah","Tanjong Pagar","Tiong Bahru","Tuas Crescent","Tuas Link","Tuas West Road"] },
    { key: "DTL", label: "Downtown", stations: ["Bayfront","Beauty World","Bedok North","Bedok Reservoir","Bencoolen","Bendemeer","Botanic Gardens","Bugis","Bukit Panjang","Cashew","Chinatown","Downtown","Expo","Fort Canning","Geylang Bahru","Hillview","Jalan Besar","Kaki Bukit","King Albert Park","Little India","MacPherson","Mattar","Promenade","Rochor","Sixth Avenue","Stevens","Tan Kah Kee","Telok Ayer","Tampines","Tampines East","Tampines West","Ubi","Upper Changi"] },
    { key: "NEL", label: "North East", stations: ["Boon Keng","Buangkok","Chinatown","Clarke Quay","Dhoby Ghaut","Farrer Park","HarbourFront","Hougang","Kovan","Little India","Outram Park","Potong Pasir","Punggol","Sengkang","Serangoon","Woodleigh"] },
    { key: "CCL", label: "Circle", stations: ["Bartley","Bayfront","Botanic Gardens","Bras Basah","Buona Vista","Caldecott","Dakota","Dhoby Ghaut","Farrer Road","HarbourFront","Haw Par Villa","Holland Village","Kent Ridge","Labrador Park","Lorong Chuan","MacPherson","Marina Bay","Marymount","Mountbatten","Nicoll Highway","one-north","Pasir Panjang","Promenade","Serangoon","Stadium","Tai Seng"] },
    { key: "TEL", label: "Thomson-East Coast", stations: ["Bright Hill","Caldecott","Gardens by the Bay","Great World","Havelock","Lentor","Marine Parade","Marine Terrace","Maxwell","Mayflower","Napier","Orchard Boulevard","Outram Park","Shenton Way","Siglap","Springleaf","Stevens","Tanjong Katong","Tanjong Rhu","Upper Thomson","Woodlands North","Woodlands South"] }
  ];

  const MRT_LINE_COLOR = {
    NSL: "#ef4444",
    EWL: "#22c55e",
    DTL: "#2563eb",
    NEL: "#a855f7",
    CCL: "#f59e0b",
    TEL: "#8b5e3c",
    OTHER: "#94a3b8"
  };

  const stationToLines = MRT_LINE_GROUPS.reduce((acc, group) => {
    group.stations.forEach((name) => {
      if (!acc[name]) acc[name] = [];
      if (!acc[name].includes(group.key)) acc[name].push(group.key);
    });
    return acc;
  }, {});

  let selectedStations = [];
  let activeLineFilter = "ALL";

  function stationLineKeys(stationName) {
    return stationToLines[stationName] && stationToLines[stationName].length
      ? stationToLines[stationName]
      : ["OTHER"];
  }

  function stationMarkerBackground(stationName) {
    const keys = stationLineKeys(stationName);
    const colors = keys.map((k) => MRT_LINE_COLOR[k] || MRT_LINE_COLOR.OTHER);
    if (colors.length === 1) return colors[0];
    const step = 100 / colors.length;
    return `linear-gradient(180deg, ${colors.map((c, i) => `${c} ${Math.round(i * step)}% ${Math.round((i + 1) * step)}%`).join(', ')})`;
  }

  function renderLineFilters() {
    const wrap = document.getElementById('profile-mrt-line-filters');
    if (!wrap) return;
    wrap.innerHTML = '';
    const allBtn = document.createElement('button');
    allBtn.type = 'button';
    allBtn.className = 'profile-line-filter' + (activeLineFilter === 'ALL' ? ' active' : '');
    allBtn.textContent = 'All Lines';
    allBtn.addEventListener('click', () => {
      activeLineFilter = 'ALL';
      renderLineFilters();
      filterProfileStations(document.getElementById('profile-mrt-search')?.value || '');
    });
    wrap.appendChild(allBtn);
    MRT_LINE_GROUPS.forEach((line) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'profile-line-filter' + (activeLineFilter === line.key ? ' active' : '');
      btn.innerHTML = `<span class="profile-line-dot" style="background:${MRT_LINE_COLOR[line.key]};"></span>${line.label}`;
      btn.addEventListener('click', () => {
        activeLineFilter = line.key;
        renderLineFilters();
        filterProfileStations(document.getElementById('profile-mrt-search')?.value || '');
      });
      wrap.appendChild(btn);
    });
  }

  function renderProfileStations(list) {
    const container = document.getElementById('profile-mrt-options');
    if (!container) return;
    container.innerHTML = '';
    list.forEach(function (name) {
      const id = 'profile-mrt-' + name.replace(/\s+/g, '-').toLowerCase();
      const checked = selectedStations.indexOf(name) !== -1 ? 'checked' : '';
      const item = document.createElement('label');
      item.className = 'station-option';
      item.innerHTML = `
        <span class="station-line-marker" style="background:${stationMarkerBackground(name)};"></span>
        <input type="checkbox" class="profile-station-checkbox" id="${id}" value="${name}" ${checked}>
        <span>${name}</span>
      `;
      container.appendChild(item);
    });

    container.querySelectorAll('.profile-station-checkbox').forEach(function (cb) {
      cb.addEventListener('change', function () {
        const val = cb.value;
        if (cb.checked) {
          if (selectedStations.indexOf(val) === -1) selectedStations.push(val);
        } else {
          selectedStations = selectedStations.filter(s => s !== val);
        }
      });
    });
  }

  function filterProfileStations(query) {
    const q = (query || '').toLowerCase();
    const filtered = MRT_STATIONS_SORTED.filter((stationName) => {
      if (!stationName.toLowerCase().includes(q)) return false;
      if (activeLineFilter === 'ALL') return true;
      return stationLineKeys(stationName).includes(activeLineFilter);
    });
    renderProfileStations(filtered);
  }

  const profileSearch = document.getElementById('profile-mrt-search');
  if (profileSearch) {
    profileSearch.addEventListener('input', function () {
      filterProfileStations(profileSearch.value);
    });
  }

  const profileSave = document.getElementById('profile-mrt-save-btn');
  if (profileSave) {
    profileSave.addEventListener('click', async () => {
      const name = selectedStations.join(', ');
      await saveProfile({ location_name: name, stations: selectedStations.slice() });
      const display = document.getElementById('location-display');
      if (display && name) display.textContent = `\u{1F4CD} ${name}`;
    });
  }

  window.__setProfileStations = function (stations) {
    selectedStations = Array.isArray(stations) ? stations.slice() : [];
    renderLineFilters();
    filterProfileStations(document.getElementById('profile-mrt-search')?.value || '');
  };

  // Render MRT options immediately so the picker is visible before profile API finishes.
  renderLineFilters();
  filterProfileStations('');
});

function loadProfile() {
  fetch('/api/profile', { headers: (typeof demoHeaders === 'function' ? demoHeaders() : {}) })
    .then(response => response.json())
    .then(data => {
      if (data.ok) {
        const profile = data.profile;
        const bioText = document.getElementById('bio-text');
        if (bioText) {
          bioText.textContent = profile.bio || '';
        }
        const bioTextHeader = document.getElementById('bio-text-header');
        if (bioTextHeader) {
          bioTextHeader.textContent = profile.bio || '';
        }
        const connections = document.getElementById('connections-count');
        if (connections) connections.textContent = profile.connections_count ?? 0;
        const connectionsStat = document.getElementById('connections-stat-count');
        if (connectionsStat) connectionsStat.textContent = profile.connections_count ?? 0;
        const memories = document.getElementById('memories-count');
        if (memories) memories.textContent = profile.memories_count ?? 0;
        const repoints = document.getElementById('repoints-count');
        if (repoints) repoints.textContent = profile.repoints ?? 0;
        const volunteerHours = document.getElementById('volunteer-hours-count');
        if (volunteerHours) volunteerHours.textContent = Number(profile.total_volunteer_hours || 0).toFixed(1);
        const volunteerHoursTotal = document.getElementById('volunteer-hours-total');
        if (volunteerHoursTotal) volunteerHoursTotal.textContent = Number(profile.total_volunteer_hours || 0).toFixed(1);
        const volunteerBreakdown = profile.volunteer_breakdown || {};
        const volunteerMeetups = document.getElementById('volunteer-meetups-count');
        const volunteerCircles = document.getElementById('volunteer-circles-count');
        const volunteerEvents = document.getElementById('volunteer-events-count');
        if (volunteerMeetups) volunteerMeetups.textContent = Number(volunteerBreakdown.meetups?.count || 0);
        if (volunteerCircles) volunteerCircles.textContent = Number(volunteerBreakdown.learning_circles?.count || 0);
        if (volunteerEvents) volunteerEvents.textContent = Number(volunteerBreakdown.events?.count || 0);
        const completeness = document.getElementById('profile-completeness');
        if (completeness) {
          const c = profile.completeness || {};
          const percent = Number(c.percent || 0);
          const completed = Number(c.completed || 0);
          const total = Number(c.total || 0);
          completeness.textContent = `Profile completeness: ${percent}% (${completed}/${total})`;
        }

        const avatar = document.getElementById('profile-avatar');
        if (avatar && profile.avatar_url) avatar.src = profile.avatar_url;
        const cover = document.getElementById('profile-cover');
        if (cover && profile.banner_url) cover.style.backgroundImage = `url('${profile.banner_url}')`;

        const locDisplay = document.getElementById('location-display');
        const onboardingStations = Array.isArray(profile.onboarding?.stations) ? profile.onboarding.stations : [];
        const storedStations = profile.location_name
          ? profile.location_name.split(',').map(s => s.trim()).filter(Boolean)
          : [];
        const stationList = onboardingStations.length ? onboardingStations : storedStations;
        if (locDisplay && stationList.length) locDisplay.textContent = `\u{1F4CD} ${stationList.join(', ')}`;
        if (stationList.length && typeof window.__setProfileStations === 'function') {
          window.__setProfileStations(stationList);
        } else if (typeof window.__setProfileStations === 'function') {
          window.__setProfileStations([]);
        }
        const interests = Array.isArray(profile.onboarding?.interests) ? profile.onboarding.interests : [];
        const interestMap = {
          technology: '💻 Technology',
          cooking: '🍳 Cooking',
          gardening: '🌱 Gardening',
          music: '🎵 Music',
          art: '🎨 Arts & Crafts',
          reading: '📚 Reading',
          fitness: '💪 Fitness',
          photography: '📷 Photography',
          travel: '✈️ Travel',
          games: '🎮 Games',
          language: '🗣️ Languages',
          volunteering: '🤝 Volunteering'
        };
        const interestsWrap = document.querySelector('.interest-tags');
        if (interestsWrap) {
          if (interests.length) {
            interestsWrap.innerHTML = interests.map(i => `<span class="interest-tag">${interestMap[i] || escapeHtml(i)}</span>`).join('');
          } else {
            interestsWrap.innerHTML = '<span class="interest-tag">Add your top 3 interests</span>';
          }
        }
        const onboardingLanguages = Array.isArray(profile.onboarding?.languages) ? profile.onboarding.languages : [];
        const langs = onboardingLanguages.length ? onboardingLanguages : (Array.isArray(profile.languages) ? profile.languages : []);
        const profMap = profile.onboarding?.language_proficiency || {};
        const languagesDisplay = document.getElementById('languages-display');
        if (languagesDisplay) {
          if (langs.length) {
            languagesDisplay.innerHTML = langs.map((lang) => {
              const level = String(profMap[lang] || 'Beginner');
              return `<span class="language-pill"><span class="language-pill-name">${escapeHtml(lang)}</span><span class="language-pill-level">${escapeHtml(level)}</span></span>`;
            }).join('');
          } else {
            languagesDisplay.innerHTML = '<span class="interest-tag">No languages listed</span>';
          }
        }

        const teachList = document.getElementById('skills-teach-list');
        if (teachList) {
          const list = profile.skills_teach && profile.skills_teach.length
            ? profile.skills_teach
            : (Array.isArray(profile.onboarding?.skills_teach) ? profile.onboarding.skills_teach : []);
          teachList.innerHTML = list.length
            ? list.map(s => `<li>${escapeHtml(s)}</li>`).join('')
            : '<li class="text-muted">Add skills you can teach</li>';
        }
        const learnList = document.getElementById('skills-learn-list');
        if (learnList) {
          const list = profile.skills_learn && profile.skills_learn.length
            ? profile.skills_learn
            : (Array.isArray(profile.onboarding?.skills_learn) ? profile.onboarding.skills_learn : []);
          learnList.innerHTML = list.length
            ? list.map(s => `<li>${escapeHtml(s)}</li>`).join('')
            : '<li class="text-muted">Add skills you want to learn</li>';
        }

        const dayLabel = {
          monday: 'Monday',
          tuesday: 'Tuesday',
          wednesday: 'Wednesday',
          thursday: 'Thursday',
          friday: 'Friday',
          saturday: 'Saturday',
          sunday: 'Sunday',
        };
        const timeLabel = {
          morning: 'Morning',
          afternoon: 'Afternoon',
          evening: 'Evening',
        };
        const days = Array.isArray(profile.onboarding?.days) ? profile.onboarding.days : [];
        const times = Array.isArray(profile.onboarding?.time) ? profile.onboarding.time : [];
        const availabilityDays = document.getElementById('availability-days');
        const availabilityTime = document.getElementById('availability-time');
        if (availabilityDays) {
          availabilityDays.textContent = days.length
            ? `Days: ${days.map((d) => dayLabel[d] || d).join(', ')}`
            : 'No days selected yet';
        }
        if (availabilityTime) {
          availabilityTime.textContent = times.length
            ? `Time: ${times.map((t) => timeLabel[t] || t).join(', ')}`
            : 'No time selected yet';
        }

        const emergency = profile.emergency_contact || {};
        if (document.getElementById('emergency-name')) document.getElementById('emergency-name').value = emergency.name || '';
        if (document.getElementById('emergency-relationship')) document.getElementById('emergency-relationship').value = emergency.relationship || '';
        if (document.getElementById('emergency-country-code')) {
          document.getElementById('emergency-country-code').value = emergency.country_code || '+65';
        }
        if (document.getElementById('emergency-phone')) {
          const rawPhone = String(emergency.phone || '').trim();
          const normalizedPhone = rawPhone.replace(/\D/g, '');
          document.getElementById('emergency-phone').value = normalizedPhone;
        }
        if (document.getElementById('verify-phone-country') && document.getElementById('verify-phone-number')) {
          const profilePhone = String(profile.phone_number || '').trim();
          const countryEl = document.getElementById('verify-phone-country');
          const phoneEl = document.getElementById('verify-phone-number');
          const options = Array.from(countryEl.options || []).map((o) => o.value).filter(Boolean);
          const matchedCode = options
            .sort((a, b) => b.length - a.length)
            .find((code) => profilePhone.startsWith(code));
          if (matchedCode) {
            countryEl.value = matchedCode;
            phoneEl.value = profilePhone.slice(matchedCode.length).replace(/\D/g, '');
          } else if (profilePhone) {
            document.getElementById('verify-phone-number').value = profilePhone.replace(/\D/g, '');
          }
        }

        const safety = profile.safety || {};
        const safetyValue = document.getElementById('safety-score-value');
        const safetyFill = document.getElementById('safety-score-fill');
        const safetyBadge = document.getElementById('safety-score-badge');
        const safetyEvents = document.getElementById('safety-events');
        const numericSafety = typeof safety.score === 'number' ? safety.score : 50;
        if (safetyValue) safetyValue.textContent = numericSafety;
        if (safetyFill) {
          safetyFill.style.width = Math.min(100, Math.max(0, numericSafety)) + '%';
          if (safety.tier === 'green') safetyFill.style.background = '#22c55e';
          else if (safety.tier === 'red') safetyFill.style.background = '#ef4444';
          else safetyFill.style.background = '#f59e0b';
        }
        if (safetyBadge) safetyBadge.style.display = safety.trusted ? '' : 'none';
        if (safetyEvents) {
          const events = Array.isArray(safety.events) ? safety.events : [];
          safetyEvents.innerHTML = events.length
            ? events.map(e => {
                const sign = e.points > 0 ? '+' : '';
                return `<div>${sign}${e.points} ${escapeHtml(e.details || e.event_type)}</div>`;
              }).join('')
            : '<div>No recent safety events yet.</div>';
        }

        const notifications = profile.notifications || {};
        if (document.getElementById('notif-messages')) document.getElementById('notif-messages').checked = notifications.messages ?? true;
        if (document.getElementById('notif-matches')) document.getElementById('notif-matches').checked = notifications.matches ?? true;
        if (document.getElementById('notif-circles')) document.getElementById('notif-circles').checked = notifications.circles ?? true;
        if (document.getElementById('notif-challenges')) document.getElementById('notif-challenges').checked = notifications.challenges ?? false;
        if (document.getElementById('notif-badges')) document.getElementById('notif-badges').checked = notifications.badges ?? true;

        const privacy = profile.privacy || {};
        if (document.getElementById('privacy-age')) document.getElementById('privacy-age').checked = privacy.show_age ?? true;
        if (document.getElementById('privacy-location')) document.getElementById('privacy-location').checked = privacy.show_location ?? true;
        if (document.getElementById('privacy-badges')) document.getElementById('privacy-badges').checked = privacy.show_badges ?? false;
        if (document.getElementById('privacy-direct')) document.getElementById('privacy-direct').checked = privacy.allow_direct ?? true;
        if (document.getElementById('public-profile')) document.getElementById('public-profile').checked = !(profile.is_private ?? false);

        const verifiedBadge = document.getElementById('verification-badge');
        const verificationTitle = document.getElementById('verification-title');
        const verificationDesc = document.getElementById('verification-desc');
        const verifiedMethod = String(profile.verified_with || '').toLowerCase();
        const verified = ['singpass', 'nric', 'email', 'phone'].includes(verifiedMethod);
        const verifiedLabelMap = {
          singpass: 'Singpass',
          nric: 'NRIC',
          email: 'Email',
          phone: 'Phone',
        };
        if (verifiedBadge) verifiedBadge.style.display = verified ? '' : 'none';
        if (verificationTitle) verificationTitle.textContent = verified ? 'Account Verified' : 'Not Verified Yet';
        if (verificationDesc) {
          verificationDesc.textContent = verified
            ? `Your identity has been verified with ${verifiedLabelMap[verifiedMethod] || profile.verified_with}`
            : 'Verify by Singpass, NRIC, email or phone number.';
        }

        const equippedTitlePill = document.getElementById('equipped-title-pill');
        if (equippedTitlePill) {
          if (profile.equipped_title && profile.equipped_title.display_name) {
            equippedTitlePill.style.display = '';
            equippedTitlePill.innerHTML = `<span class="title-pill">${escapeHtml(profile.equipped_title.display_name)}</span>`;
          } else {
            equippedTitlePill.style.display = 'none';
            equippedTitlePill.innerHTML = '';
          }
        }

        const verificationBadgesList = document.getElementById('verification-badges-list');
        if (verificationBadgesList) {
          const badges = Array.isArray(profile.verification_badges) ? profile.verification_badges : [];
          verificationBadgesList.innerHTML = badges.length
            ? badges.map((badge) => `<span style="padding:0.2rem 0.6rem;border-radius:999px;background:#ecfeff;border:1px solid #a5f3fc;color:#0f766e;font-weight:700;font-size:0.78rem;">${escapeHtml(badge)}</span>`).join('')
            : '<span style="color:#64748b;">No verification badges yet.</span>';
        }

        const titlesList = document.getElementById('profile-titles-list');
        if (titlesList) {
          const titles = Array.isArray(profile.titles) ? profile.titles : [];
          if (!titles.length) {
            titlesList.innerHTML = '' +
              '<div class="empty-state">' +
                '<div class="empty-state-icon">🏅</div>' +
                '<h4 class="empty-state-title">No titles unlocked yet</h4>' +
                '<p class="empty-state-text">Unlock titles by volunteering, joining circles, and building trust.</p>' +
                '<a href="/discover" class="btn-secondary">Discover Activities</a>' +
              '</div>';
          } else {
            const equippedId = profile.equipped_title && profile.equipped_title.id ? Number(profile.equipped_title.id) : null;
            titlesList.innerHTML = titles.map((t) => {
              const equipped = equippedId === Number(t.id);
              return `
                <div style="display:flex;align-items:center;justify-content:space-between;gap:0.6rem;border:1px solid #e2e8f0;border-radius:10px;padding:0.55rem 0.7rem;background:#fff;">
                  <div>
                    <div style="font-weight:700;">${escapeHtml(t.display_name)}</div>
                    <div style="font-size:0.82rem;color:#64748b;">${escapeHtml(t.description || "")}</div>
                  </div>
                  <button type="button" class="btn btn-outline-teal btn-sm" data-equip-title-id="${t.id}" ${equipped ? 'disabled' : ''}>${equipped ? 'Equipped' : 'Equip'}</button>
                </div>
              `;
            }).join('');
          }
        }
      }
    })
    .catch(error => {
      console.error('Error loading profile:', error);
    });
}

async function updateBio(bio) {
  const bioText = document.getElementById('bio-text');
  const bioTextHeader = document.getElementById('bio-text-header');
  const editBioBtn = document.getElementById('edit-bio-btn');
  const textarea = document.querySelector('.bio-edit-textarea');
  const buttonContainer = document.querySelector('.bio-action-buttons');
  try {
    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: demoHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ bio: bio }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      alert(data.error || 'Failed to update bio');
      return;
    }
    if (bioText) bioText.textContent = bio || '';
    if (bioTextHeader) bioTextHeader.textContent = bio || '';
    loadProfile();
  } catch (error) {
    console.error('Error updating bio:', error);
    alert('Error updating bio');
  } finally {
    if (textarea) textarea.remove();
    if (buttonContainer) buttonContainer.remove();
    if (bioText) bioText.style.display = '';
    if (editBioBtn) editBioBtn.style.display = '';
  }
}

document.addEventListener('click', async (event) => {
  const btn = event.target.closest('[data-equip-title-id]');
  if (!btn) return;
  const titleId = Number(btn.getAttribute('data-equip-title-id'));
  if (!titleId) return;
  try {
    const res = await fetch('/api/profile/equip_title', {
      method: 'POST',
      headers: demoHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ title_id: titleId }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) return alert(data.error || 'Could not equip title.');
    loadProfile();
  } catch (err) {
    alert('Could not equip title.');
  }
});

async function saveProfile(payload) {
  try {
    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: demoHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      alert(data.error || 'Could not save changes.');
      return;
    }
    loadProfile();
  } catch (err) {
    alert('Could not save changes.');
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text ?? '';
  return div.innerHTML;
}

