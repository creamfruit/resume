// Profile Page Tab Switching

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

  // Demo functionality for buttons
  document.querySelectorAll('.btn-edit').forEach(btn => {
    btn.addEventListener('click', function() {
      alert('Edit feature coming soon! This will allow you to update your information.');
    });
  });

  document.querySelector('.btn-report')?.addEventListener('click', function() {
    if (confirm('Are you sure you want to report a user or content?')) {
      alert('Your report has been submitted. Our safety team will review it within 24 hours.');
    }
  });

  document.querySelector('.btn-danger')?.addEventListener('click', function() {
    if (confirm('⚠️ Are you SURE you want to delete your account? This action cannot be undone.')) {
      alert('Account deletion process initiated. You will receive a confirmation email.');
    }
  });
});
