// Dashboard JavaScript

// Show main dashboard after welcome screen
window.addEventListener('DOMContentLoaded', function() {
  const welcomeScreen = document.getElementById('welcome-screen');
  const mainDashboard = document.getElementById('main-dashboard');

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
