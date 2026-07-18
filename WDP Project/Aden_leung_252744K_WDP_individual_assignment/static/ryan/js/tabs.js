// Tab Switching Functionality

document.addEventListener('DOMContentLoaded', function() {
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');

  function activateTab(tabName) {
    if (!tabName) return;

    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));

    const targetButton = document.querySelector(`.tab-button[data-tab="${tabName}"]`);
    const targetTab = document.getElementById(`tab-${tabName}`);

    if (targetButton) targetButton.classList.add('active');
    if (targetTab) targetTab.classList.add('active');

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  tabButtons.forEach(button => {
    button.addEventListener('click', function() {
      const tabName = this.dataset.tab;
      activateTab(tabName);
    });
  });

  const hash = window.location.hash || '';
  const hasFilter = window.location.search.includes('filter=');
  let initialTab = null;

  if (hash.startsWith('#tab-')) {
    initialTab = hash.replace('#tab-', '');
  } else if (hasFilter) {
    initialTab = 'wisdom-forum';
  }

  if (initialTab) {
    activateTab(initialTab);
  }

  if (hasFilter) {
    setTimeout(() => {
      const forumSection = document.getElementById('tab-wisdom-forum');
      if (forumSection) forumSection.scrollIntoView({ behavior: 'smooth' });
    }, 400);
  }
});
