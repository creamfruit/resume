document.addEventListener('DOMContentLoaded', () => {
  const notifBtn = document.getElementById('global-notif-btn');
  const chatbotBtn = document.getElementById('global-chatbot-btn');
  const accessBtn = document.getElementById('global-access-btn');
  const notifPanel = document.getElementById('global-notif-panel');
  const chatbotPanel = document.getElementById('global-chatbot-panel');
  const accessPanel = document.getElementById('global-access-panel');
  const notifList = document.getElementById('global-notif-list');
  const notifBadge = document.getElementById('global-notif-badge');

  function toggle(panel) {
    [notifPanel, chatbotPanel, accessPanel].forEach(p => {
      if (p && p !== panel) p.classList.remove('open');
    });
    if (panel) panel.classList.toggle('open');
  }

  if (notifBtn && notifPanel) notifBtn.addEventListener('click', () => toggle(notifPanel));
  if (chatbotBtn && chatbotPanel) chatbotBtn.addEventListener('click', () => toggle(chatbotPanel));
  if (accessBtn && accessPanel) accessBtn.addEventListener('click', () => toggle(accessPanel));

  let unread = 0;
  function addNotif(message) {
    if (!notifList) return;
    const item = document.createElement('div');
    item.className = 'item';
    item.textContent = message;
    notifList.prepend(item);
    unread += 1;
    if (notifBadge) notifBadge.textContent = String(unread);
  }

  if (notifPanel) {
    notifPanel.addEventListener('click', () => {
      unread = 0;
      if (notifBadge) notifBadge.textContent = '0';
    });
  }

  const eventSource = new EventSource('/api/notifications/stream');
  eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload && payload.message) {
        addNotif(payload.message);
      }
    } catch (err) {
      if (event.data) addNotif(event.data);
    }
  };

  const chatbotForm = document.getElementById('global-chatbot-form');
  const chatbotInput = document.getElementById('global-chatbot-input');
  const chatbotLog = document.getElementById('global-chatbot-log');

  function addChat(message, isBot) {
    if (!chatbotLog) return;
    const item = document.createElement('div');
    item.className = 'item';
    item.textContent = (isBot ? 'Bot: ' : 'You: ') + message;
    chatbotLog.appendChild(item);
    chatbotLog.scrollTop = chatbotLog.scrollHeight;
  }

  if (chatbotForm) {
    chatbotForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = (chatbotInput && chatbotInput.value || '').trim();
      if (!text) return;
      addChat(text, false);
      if (chatbotInput) chatbotInput.value = '';
      try {
        const res = await fetch('/api/chatbot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        addChat(data.reply || 'Thanks! A team member will follow up.', true);
      } catch (err) {
        addChat('Sorry, I am offline right now.', true);
      }
    });
  }
});
