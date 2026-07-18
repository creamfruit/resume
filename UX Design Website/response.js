document.addEventListener('DOMContentLoaded', function () {
  const params = new URLSearchParams(window.location.search);

  document.getElementById('name').textContent = params.get('name');
  document.getElementById('adminNumber').textContent = params.get('adminNumber');
  document.getElementById('reason').textContent = params.get('reason');
  document.getElementById('agree').textContent = params.get('agree') ? 'Yes' : 'No';
});
