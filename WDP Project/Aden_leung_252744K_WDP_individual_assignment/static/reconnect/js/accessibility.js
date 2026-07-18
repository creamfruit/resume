// Accessibility Features

document.addEventListener('DOMContentLoaded', function() {
  let fontSize = 'normal'; // normal, large, xlarge
  let contrastMode = false;

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

  // High Contrast Mode
  const contrastBtn = document.getElementById('contrast-btn');
  if (contrastBtn) {
    contrastBtn.addEventListener('click', function() {
      contrastMode = !contrastMode;
      if (contrastMode) {
        document.body.classList.add('high-contrast');
        localStorage.setItem('contrastMode', 'true');
        this.style.backgroundColor = '#FFB84D';
        this.style.color = '#000000';
      } else {
        document.body.classList.remove('high-contrast');
        localStorage.setItem('contrastMode', 'false');
        this.style.backgroundColor = '';
        this.style.color = '';
      }
    });
  }

  // Language Selection
  const langBtn = document.getElementById('lang-btn');
  const langModal = document.getElementById('lang-modal');
  const closeLangModal = document.getElementById('close-lang-modal');

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
      const langNames = {
        en: 'English',
        zh: '中文',
        ms: 'Bahasa Melayu',
        ta: 'தமிழ்'
      };

      localStorage.setItem('language', lang);
      alert(`Language changed to ${langNames[lang]}!\n(Full translation coming soon)`);
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

  const savedContrast = localStorage.getItem('contrastMode');
  if (savedContrast === 'true') {
    contrastMode = true;
    document.body.classList.add('high-contrast');
    if (contrastBtn) {
      contrastBtn.style.backgroundColor = '#FFB84D';
      contrastBtn.style.color = '#000000';
    }
  }

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
