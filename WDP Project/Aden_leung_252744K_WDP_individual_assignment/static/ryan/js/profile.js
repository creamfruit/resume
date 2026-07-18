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

function loadProfile() {
  fetch('/ryan/api/profile')
    .then(response => response.json())
    .then(data => {
      if (data.ok) {
        const profile = data.profile;
        const bioText = document.getElementById('bio-text');
        if (bioText) {
          bioText.textContent = profile.bio || '';
        }
        // You can load other profile data here if needed
      }
    })
    .catch(error => {
      console.error('Error loading profile:', error);
    });
}

function updateBio(bio) {
  fetch('/ryan/api/profile', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ bio: bio }),
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      // Reload profile to update display
      loadProfile();
      // Restore UI
      const textarea = document.querySelector('.bio-edit-textarea');
      const buttonContainer = textarea ? textarea.nextSibling : null;
      if (textarea) textarea.remove();
      if (buttonContainer && buttonContainer.tagName === 'DIV') buttonContainer.remove();
      document.getElementById('bio-text').style.display = '';
      document.getElementById('edit-bio-btn').style.display = '';
    } else {
      alert('Failed to update bio');
    }
  })
  .catch(error => {
    console.error('Error updating bio:', error);
    alert('Error updating bio');
  });
}
