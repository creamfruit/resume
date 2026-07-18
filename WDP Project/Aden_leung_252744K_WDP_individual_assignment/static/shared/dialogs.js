(function () {
  if (window.__uiDialogsInstalled) return;
  window.__uiDialogsInstalled = true;

  const overlay = document.createElement('div');
  overlay.className = 'ui-dialog-overlay';
  overlay.innerHTML = `
    <div class="ui-dialog" role="dialog" aria-modal="true" aria-live="assertive">
      <div class="ui-dialog-header" id="ui-dialog-title">Notice</div>
      <div class="ui-dialog-body" id="ui-dialog-body"></div>
      <div class="ui-dialog-actions" id="ui-dialog-actions"></div>
    </div>
  `;
  document.addEventListener('DOMContentLoaded', function () {
    document.body.appendChild(overlay);
  });

  function openDialog({ title, body, actions }) {
    document.getElementById('ui-dialog-title').textContent = title || 'Notice';
    document.getElementById('ui-dialog-body').innerHTML = body || '';
    const actionsEl = document.getElementById('ui-dialog-actions');
    actionsEl.innerHTML = '';
    (actions || []).forEach((a) => actionsEl.appendChild(a));
    overlay.classList.add('show');
  }

  function closeDialog() {
    overlay.classList.remove('show');
  }

  // Track last interactive target for confirm flows.
  let lastTarget = null;
  let lastForm = null;
  let skipConfirmOnce = false;

  document.addEventListener('click', (e) => {
    lastTarget = e.target;
    lastForm = null;
    if (lastTarget && lastTarget.form) lastForm = lastTarget.form;
  }, true);

  document.addEventListener('submit', (e) => {
    lastForm = e.target;
    lastTarget = e.submitter || null;
  }, true);

  window.alert = function (message) {
    const okBtn = document.createElement('button');
    okBtn.className = 'ui-dialog-btn primary';
    okBtn.textContent = 'OK';
    okBtn.addEventListener('click', closeDialog);

    openDialog({
      title: 'Notice',
      body: `<p style="margin:0;">${String(message || '')}</p>`,
      actions: [okBtn]
    });
  };

  window.confirm = function (message) {
    if (skipConfirmOnce) {
      skipConfirmOnce = false;
      return true;
    }

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'ui-dialog-btn';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.addEventListener('click', closeDialog);

    const okBtn = document.createElement('button');
    okBtn.className = 'ui-dialog-btn danger';
    okBtn.textContent = 'Confirm';
    okBtn.addEventListener('click', () => {
      closeDialog();
      skipConfirmOnce = true;
      if (lastForm && typeof lastForm.requestSubmit === 'function') {
        lastForm.requestSubmit(lastTarget || undefined);
        return;
      }
      if (lastForm) {
        lastForm.submit();
        return;
      }
      if (lastTarget && typeof lastTarget.click === 'function') {
        lastTarget.click();
      }
    });

    openDialog({
      title: 'Please Confirm',
      body: `<p style="margin:0;">${String(message || '')}</p>`,
      actions: [cancelBtn, okBtn]
    });

    return false;
  };
})();
