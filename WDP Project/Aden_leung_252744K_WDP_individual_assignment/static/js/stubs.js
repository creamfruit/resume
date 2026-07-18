document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('stub-button');
  if (!btn) return;
  btn.addEventListener('click', () => {
    btn.textContent = 'Clicked!';
  });
});
