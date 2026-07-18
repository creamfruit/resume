// Messages Functionality

document.addEventListener('DOMContentLoaded', function() {
  // Notifications Dropdown
  const notifBtn = document.getElementById('notif-btn');
  const notifDropdown = document.getElementById('notifications-dropdown');

  if (notifBtn) {
    notifBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      notifDropdown.classList.toggle('show');
    });
  }

  // Close dropdown when clicking outside
  document.addEventListener('click', function(e) {
    if (notifDropdown && !notifDropdown.contains(e.target) && e.target !== notifBtn) {
      notifDropdown.classList.remove('show');
    }
  });

  // Mark all as read
  const markReadBtn = document.querySelector('.mark-read-btn');
  if (markReadBtn) {
    markReadBtn.addEventListener('click', function() {
      document.querySelectorAll('.notification-item.unread').forEach(item => {
        item.classList.remove('unread');
      });
      const badge = document.querySelector('.notification-badge');
      if (badge) badge.textContent = '0';
    });
  }

  // Back Button
  const backBtn = document.getElementById('back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', function() {
      window.history.back();
    });
  }

  // Translation Toggle
  const translateBtn = document.getElementById('translate-btn');
  const translationPanel = document.getElementById('translation-panel');

  if (translateBtn) {
    translateBtn.addEventListener('click', function() {
      if (translationPanel.style.display === 'none') {
        translationPanel.style.display = 'flex';
      } else {
        translationPanel.style.display = 'none';
      }
    });
  }

  // Language Selection
  document.querySelectorAll('.lang-option').forEach(btn => {
    btn.addEventListener('click', function() {
      const lang = this.dataset.lang;
      alert(`Messages will be translated to ${lang}. (Translation feature coming soon!)`);
      translationPanel.style.display = 'none';
    });
  });

  // Conversation Switching
  const conversationItems = document.querySelectorAll('.conversation-item');
  const chatMessages = document.getElementById('chat-messages');

  conversationItems.forEach(item => {
    item.addEventListener('click', function() {
      // Remove active from all
      conversationItems.forEach(i => i.classList.remove('active'));

      // Add active to clicked
      this.classList.add('active');

      // Remove unread badge
      const badge = this.querySelector('.unread-badge');
      if (badge) badge.remove();

      // Update chat header
      const name = this.querySelector('h4').textContent;
      const avatar = this.querySelector('.conversation-avatar').src;
      document.querySelector('.chat-header-info h3').textContent = name;
      document.querySelector('.chat-avatar').src = avatar;

      // Clear messages (in real app, would load conversation)
      loadConversation(this.dataset.chat);
    });
  });

  // Send Message
  const messageInput = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-btn');

  function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    // Remove typing indicator
    const typing = document.querySelector('.message.typing');
    if (typing) typing.remove();

    // Remove conversation starters if present
    const starters = document.querySelector('.conversation-starters');
    if (starters) starters.remove();

    // Create message element
    const messageEl = document.createElement('div');
    messageEl.className = 'message sent';
    messageEl.innerHTML = `
      <div class="message-content">
        <p>${escapeHtml(text)}</p>
        <span class="message-time">${getCurrentTime()}</span>
      </div>
    `;

    chatMessages.appendChild(messageEl);
    messageInput.value = '';

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Simulate response after 2 seconds
    setTimeout(() => {
      addTypingIndicator();
      setTimeout(() => {
        removeTypingIndicator();
        addReceivedMessage("Thank you! That's very helpful! 😊");
      }, 1500);
    }, 1000);
  }

  if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
  }

  if (messageInput) {
    messageInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });
  }

  // Conversation Starters
  document.querySelectorAll('.starter-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      messageInput.value = this.textContent;
      messageInput.focus();
    });
  });

  // Helper Functions
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function getCurrentTime() {
    const now = new Date();
    let hours = now.getHours();
    const minutes = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    const minutesStr = minutes < 10 ? '0' + minutes : minutes;
    return `${hours}:${minutesStr} ${ampm}`;
  }

  function addTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'message received typing';
    typing.innerHTML = `
      <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Chen" alt="Mdm Chen" class="message-avatar">
      <div class="message-content">
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;
    chatMessages.appendChild(typing);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function removeTypingIndicator() {
    const typing = document.querySelector('.message.typing');
    if (typing) typing.remove();
  }

  function addReceivedMessage(text) {
    const messageEl = document.createElement('div');
    messageEl.className = 'message received';
    messageEl.innerHTML = `
      <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Chen" alt="Mdm Chen" class="message-avatar">
      <div class="message-content">
        <p>${text}</p>
        <span class="message-time">${getCurrentTime()}</span>
      </div>
    `;
    chatMessages.appendChild(messageEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function loadConversation(chatId) {
    // Clear current messages
    chatMessages.innerHTML = '';

    // Sample conversation data
    const conversations = {
      'mdm-chen': [
        { type: 'received', text: 'Hello Sarah! I hope you\'re doing well. I wanted to thank you for helping me with WhatsApp yesterday! 😊', time: '10:30 AM' },
        { type: 'sent', text: 'Hi Mdm Chen! I\'m so happy I could help! How are you finding it so far?', time: '10:32 AM' },
        { type: 'received', text: 'Thank you so much! I finally managed to send a voice message to my grandson in Australia! He was so surprised! 🎉', time: '10:35 AM' },
        { type: 'sent', text: 'That\'s wonderful! I\'m sure he loved hearing your voice! Would you like to learn how to make video calls next? 📱', time: '10:37 AM' }
      ],
      'uncle-kumar': [
        { type: 'received', text: 'Hi! Looking forward to the Learning Circle today!', time: '9:00 AM' },
        { type: 'sent', text: 'Me too! See you at 3 PM! I\'ll bring my laptop.', time: '9:15 AM' },
        { type: 'received', text: 'Great! I have some questions about Instagram.', time: '9:20 AM' },
        { type: 'sent', text: 'Perfect! We can go through it step by step!', time: '9:22 AM' }
      ],
      'auntie-mary': [
        { type: 'sent', text: 'Hi Auntie Mary! How did the kueh turn out?', time: 'Yesterday' },
        { type: 'received', text: 'The kueh recipe was wonderful! My grandchildren loved it!', time: 'Yesterday' },
        { type: 'sent', text: 'That\'s amazing! Would you like to share the recipe in our Learning Circle?', time: 'Yesterday' }
      ],
      'uncle-tan': [
        { type: 'received', text: 'Can share my kopi secret with you next week!', time: '2 days ago' },
        { type: 'sent', text: 'I\'d love that! I\'ve been wanting to learn!', time: '2 days ago' }
      ]
    };

    const messages = conversations[chatId] || [];

    messages.forEach(msg => {
      const messageEl = document.createElement('div');
      messageEl.className = `message ${msg.type}`;

      if (msg.type === 'received') {
        const avatar = document.querySelector('.chat-avatar').src;
        messageEl.innerHTML = `
          <img src="${avatar}" alt="Avatar" class="message-avatar">
          <div class="message-content">
            <p>${msg.text}</p>
            <span class="message-time">${msg.time}</span>
          </div>
        `;
      } else {
        messageEl.innerHTML = `
          <div class="message-content">
            <p>${msg.text}</p>
            <span class="message-time">${msg.time}</span>
          </div>
        `;
      }

      chatMessages.appendChild(messageEl);
    });

    // Add typing indicator for active chat
    if (chatId === 'mdm-chen') {
      addTypingIndicator();
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
});
