// Accessibility Features

document.addEventListener('DOMContentLoaded', function() {
  let fontSize = 'normal'; // normal, large, xlarge
  let activeLanguage = 'en';

  const translations = {
    en: {
      nav_home: 'Home',
      nav_messages: 'Messages',
      nav_profile: 'Profile',
      nav_admin: 'Admin',
      nav_dashboard: 'Dashboard',
      greeting_ready: 'Ready to connect and learn today?',
      matches_tab: 'Matches',
      wisdom_tab: 'Wisdom Forum',
      learning_tab: 'Learning Circles',
      challenges_tab: 'Weekly Challenges',
      achievements_tab: 'Achievements',
      search_conversations: 'Search conversations...',
      send_message: 'Send',
      weekly_submit: 'Submit Your Entry',
      weekly_recent: 'Recent Submissions',
    },
    zh: {
      nav_home: '主页',
      nav_messages: '消息',
      nav_profile: '个人资料',
      nav_admin: '管理员',
      nav_dashboard: '仪表板',
      greeting_ready: '准备好连接与学习了吗？',
      matches_tab: '配对',
      wisdom_tab: '智慧论坛',
      learning_tab: '学习圈',
      challenges_tab: '每周挑战',
      achievements_tab: '成就',
      search_conversations: '搜索对话...',
      send_message: '发送',
      weekly_submit: '提交作品',
      weekly_recent: '最新提交',
    },
    ms: {
      nav_home: 'Laman Utama',
      nav_messages: 'Mesej',
      nav_profile: 'Profil',
      nav_admin: 'Admin',
      nav_dashboard: 'Papan Pemuka',
      greeting_ready: 'Sedia untuk berhubung dan belajar hari ini?',
      matches_tab: 'Padanan',
      wisdom_tab: 'Forum Kebijaksanaan',
      learning_tab: 'Bulatan Pembelajaran',
      challenges_tab: 'Cabaran Mingguan',
      achievements_tab: 'Pencapaian',
      search_conversations: 'Cari perbualan...',
      send_message: 'Hantar',
      weekly_submit: 'Hantar Penyertaan',
      weekly_recent: 'Hantaran Terkini',
    },
    ta: {
      nav_home: 'முகப்பு',
      nav_messages: 'செய்திகள்',
      nav_profile: 'சுயவிவரம்',
      nav_admin: 'நிர்வாகம்',
      nav_dashboard: 'டாஷ்போர்ட்',
      greeting_ready: 'இன்று இணைந்து கற்றுக்கொள்ள தயாரா?',
      matches_tab: 'பொருத்தங்கள்',
      wisdom_tab: 'ஞானப் பேச்சகம்',
      learning_tab: 'கற்றல் வட்டம்',
      challenges_tab: 'வாரச் சவால்கள்',
      achievements_tab: 'சாதனைகள்',
      search_conversations: 'உரையாடல்களை தேடு...',
      send_message: 'அனுப்பு',
      weekly_submit: 'பதிவு செய்ய',
      weekly_recent: 'சமீபத்திய சமர்ப்பிப்புகள்',
    }
  };

  translations.zh = {
    nav_home: '主页',
    nav_messages: '消息',
    nav_profile: '个人资料',
    nav_admin: '管理员',
    nav_dashboard: '仪表板',
    greeting_ready: '准备好连接与学习了吗？',
    matches_tab: '匹配',
    wisdom_tab: '智慧论坛',
    learning_tab: '学习圈',
    challenges_tab: '每周挑战',
    achievements_tab: '成就',
    search_conversations: '搜索对话...',
    send_message: '发送',
    weekly_submit: '提交作品',
    weekly_recent: '最新提交',
  };

  translations.ta = {
    nav_home: 'முகப்பு',
    nav_messages: 'செய்திகள்',
    nav_profile: 'சுயவிவரம்',
    nav_admin: 'நிர்வாகம்',
    nav_dashboard: 'டாஷ்போர்டு',
    greeting_ready: 'இன்று இணைந்து கற்றுக்கொள்ள தயாரா?',
    matches_tab: 'பொருத்தங்கள்',
    wisdom_tab: 'ஞானப் பேச்சகம்',
    learning_tab: 'கற்றல் வட்டம்',
    challenges_tab: 'வாரச் சவால்கள்',
    achievements_tab: 'சாதனைகள்',
    search_conversations: 'உரையாடல்களைத் தேடு...',
    send_message: 'அனுப்பு',
    weekly_submit: 'பதிவு செய்',
    weekly_recent: 'சமீபத்திய சமர்ப்பிப்புகள்',
  };

  function applyLanguage(lang) {
    activeLanguage = translations[lang] ? lang : 'en';
    document.documentElement.setAttribute('lang', activeLanguage);
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const text = translations[activeLanguage][key] || translations.en[key];
      if (text) el.textContent = text;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      const key = el.getAttribute('data-i18n-placeholder');
      const text = translations[activeLanguage][key] || translations.en[key];
      if (text) el.setAttribute('placeholder', text);
    });
  }

  // Font Size Toggle
  const fontSizeBtn = document.getElementById('font-size-btn');
  if (fontSizeBtn) {
    fontSizeBtn.addEventListener('click', function() {
      if (fontSize === 'normal') {
        fontSize = 'large';
        document.body.classList.add('font-large');
        document.body.classList.remove('font-xlarge');
        localStorage.setItem('fontSize', 'large');
      } else if (fontSize === 'large') {
        fontSize = 'xlarge';
        document.body.classList.remove('font-large');
        document.body.classList.add('font-xlarge');
        localStorage.setItem('fontSize', 'xlarge');
      } else {
        fontSize = 'normal';
        document.body.classList.remove('font-large', 'font-xlarge');
        localStorage.setItem('fontSize', 'normal');
      }
    });
  }

  // Language Selection
  const langBtn = document.getElementById('lang-btn');
  const langModal = document.getElementById('lang-modal');
  const closeLangModal = document.getElementById('close-lang-modal');
  const a11yToggle = document.getElementById('accessibility-toggle');
  const a11yPanel = document.getElementById('accessibility-panel');

  if (a11yToggle && a11yPanel) {
    a11yToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      const isOpen = a11yPanel.classList.toggle('open');
      a11yToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    document.addEventListener('click', function(e) {
      if (!a11yPanel.contains(e.target) && e.target !== a11yToggle) {
        a11yPanel.classList.remove('open');
        a11yToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  if (langBtn && langModal) {
    langBtn.addEventListener('click', function() {
      langModal.classList.add('show');
    });
  }

  if (closeLangModal) {
    closeLangModal.addEventListener('click', function() {
      langModal.classList.remove('show');
    });
  }

  // Language options
  document.querySelectorAll('.lang-option-big').forEach(btn => {
    btn.addEventListener('click', function() {
      const lang = this.dataset.lang;
      localStorage.setItem('language', lang);
      applyLanguage(lang);
      langModal.classList.remove('show');
    });
  });

  // Close modal when clicking outside
  if (langModal) {
    langModal.addEventListener('click', function(e) {
      if (e.target === langModal) {
        langModal.classList.remove('show');
      }
    });
  }

  // Load saved preferences
  const savedFontSize = localStorage.getItem('fontSize');
  if (savedFontSize === 'large') {
    fontSize = 'large';
    document.body.classList.add('font-large');
  } else if (savedFontSize === 'xlarge') {
    fontSize = 'xlarge';
    document.body.classList.add('font-xlarge');
  }

  const savedLang = localStorage.getItem('language') || 'en';
  applyLanguage(savedLang);

  // Keyboard Navigation Enhancement
  document.addEventListener('keydown', function(e) {
    // ESC to close modals
    if (e.key === 'Escape') {
      if (langModal && langModal.classList.contains('show')) {
        langModal.classList.remove('show');
      }
      const notifDropdown = document.getElementById('notifications-dropdown');
      if (notifDropdown && notifDropdown.classList.contains('show')) {
        notifDropdown.classList.remove('show');
      }
    }

    // Alt + B for back
    if (e.altKey && e.key === 'b') {
      e.preventDefault();
      window.history.back();
    }

    // Alt + N for notifications
    if (e.altKey && e.key === 'n') {
      e.preventDefault();
      const notifBtn = document.getElementById('notif-btn');
      if (notifBtn) notifBtn.click();
    }
  });

  // Screen Reader Announcements
  function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);
  }

  // Add ARIA labels dynamically
  const buttons = document.querySelectorAll('button:not([aria-label])');
  buttons.forEach(btn => {
    if (!btn.getAttribute('aria-label') && btn.textContent.trim()) {
      btn.setAttribute('aria-label', btn.textContent.trim());
    }
  });

  // Focus visible for keyboard navigation
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Tab') {
      document.body.classList.add('keyboard-navigation');
    }
  });

  document.addEventListener('mousedown', function() {
    document.body.classList.remove('keyboard-navigation');
  });
});

// Screen Reader Only Styles
const style = document.createElement('style');
style.textContent = `
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }

  body.keyboard-navigation *:focus {
    outline: 3px solid #F47C20 !important;
    outline-offset: 2px;
  }
`;
document.head.appendChild(style);
