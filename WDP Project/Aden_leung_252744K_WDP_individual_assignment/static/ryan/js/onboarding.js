// Onboarding Flow JavaScript

let currentStep = 1;
let selectedUserType = null;
let selectedInterests = [];
let selectedDays = [];
let selectedTime = null;

// Step 1: User Type Selection
const userTypeCards = document.querySelectorAll('.user-type-card');
const nextBtn1 = document.getElementById('next-1');

userTypeCards.forEach(card => {
  card.addEventListener('click', function() {
    userTypeCards.forEach(c => c.classList.remove('selected'));
    this.classList.add('selected');
    selectedUserType = this.dataset.type;
    nextBtn1.disabled = false;
  });
});

nextBtn1.addEventListener('click', function() {
  goToStep(2);
});

// Step 2: Interests Selection
const interestChips = document.querySelectorAll('.interest-chip');
const nextBtn2 = document.getElementById('next-2');
const backBtn2 = document.getElementById('back-2');

interestChips.forEach(chip => {
  chip.addEventListener('click', function() {
    const interest = this.dataset.interest;

    if (this.classList.contains('selected')) {
      this.classList.remove('selected');
      selectedInterests = selectedInterests.filter(i => i !== interest);
    } else {
      this.classList.add('selected');
      selectedInterests.push(interest);
    }

    nextBtn2.disabled = selectedInterests.length < 3;
  });
});

nextBtn2.addEventListener('click', function() {
  goToStep(3);
});

backBtn2.addEventListener('click', function() {
  goToStep(1);
});

// Step 3: Availability Selection
const dayChips = document.querySelectorAll('.day-chip');
const timeChips = document.querySelectorAll('.time-chip');
const backBtn3 = document.getElementById('back-3');
const finishBtn = document.getElementById('finish');

dayChips.forEach(chip => {
  chip.addEventListener('click', function() {
    const day = this.dataset.day;

    if (this.classList.contains('selected')) {
      this.classList.remove('selected');
      selectedDays = selectedDays.filter(d => d !== day);
    } else {
      this.classList.add('selected');
      selectedDays.push(day);
    }
  });
});

timeChips.forEach(chip => {
  chip.addEventListener('click', function() {
    timeChips.forEach(c => c.classList.remove('selected'));
    this.classList.add('selected');
    selectedTime = this.dataset.time;
  });
});

backBtn3.addEventListener('click', function() {
  goToStep(2);
});

finishBtn.addEventListener('click', async function() {
  // Store onboarding data in the database
  var payload = {
    memberType: selectedUserType || '',
    interests: selectedInterests || [],
    days: selectedDays || [],
    time: selectedTime || ''
  };

  try {
    var res = await fetch('/ryan/api/onboarding', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    var out = await res.json().catch(function () { return {}; });

    if (!res.ok) {
      if (res.status === 401) {
        alert('Please sign up or log in first.');
        window.location.href = '/signup';
        return;
      }
      alert(out.error || 'Could not save your onboarding details.');
      return;
    }

    // Redirect to dashboard
    window.location.href = '/dashboard';
  } catch (err) {
    alert('Could not reach the server. Please try again.');
  }
});

// Navigation Function
function goToStep(stepNumber) {
  // Hide all steps
  document.querySelectorAll('.onboarding-step').forEach(step => {
    step.classList.remove('active');
  });

  // Show current step
  document.getElementById(`step-${stepNumber}`).classList.add('active');

  // Update progress
  currentStep = stepNumber;
  document.getElementById('current-step').textContent = stepNumber;

  const progressPercent = (stepNumber / 3) * 100;
  document.getElementById('progress-fill').style.width = `${progressPercent}%`;

  // Scroll to top
  window.scrollTo(0, 0);
}
