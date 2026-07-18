document.addEventListener('DOMContentLoaded', () => {
  function setupTable(table) {
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const pageSize = 10;
    let currentPage = 1;
    let filteredRows = rows;

    function render() {
      rows.forEach(r => r.style.display = 'none');
      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;
      filteredRows.slice(start, end).forEach(r => r.style.display = '');
      if (pager) {
        pager.querySelector('.js-page-info').textContent = `${currentPage} / ${Math.max(1, Math.ceil(filteredRows.length / pageSize))}`;
      }
    }

    const pager = document.createElement('div');
    pager.className = 'd-flex align-items-center gap-2 mt-2';
    pager.innerHTML = `
      <button class="btn btn-sm btn-outline-secondary js-prev">Prev</button>
      <span class="js-page-info small">1 / 1</span>
      <button class="btn btn-sm btn-outline-secondary js-next">Next</button>
    `;
    table.parentElement.appendChild(pager);

    pager.querySelector('.js-prev').addEventListener('click', () => {
      currentPage = Math.max(1, currentPage - 1);
      render();
    });
    pager.querySelector('.js-next').addEventListener('click', () => {
      const maxPage = Math.max(1, Math.ceil(filteredRows.length / pageSize));
      currentPage = Math.min(maxPage, currentPage + 1);
      render();
    });

    function applyFilter(query) {
      const q = (query || '').toLowerCase();
      if (!q) {
        filteredRows = rows;
      } else {
        filteredRows = rows.filter(r => r.textContent.toLowerCase().includes(q));
      }
      currentPage = 1;
      render();
    }

    const searchInput = table.closest('.card')?.querySelector('.js-table-search');
    if (searchInput) {
      let timer = null;
      searchInput.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => applyFilter(searchInput.value), 300);
      });

      const exportLink = table.closest('.card')?.querySelector('.js-export-link');
      if (exportLink) {
        exportLink.addEventListener('click', (e) => {
          if (!searchInput.value) return;
          const url = new URL(exportLink.href, window.location.origin);
          url.searchParams.set('q', searchInput.value);
          exportLink.href = url.toString();
        });
      }
    }

    render();
  }

  document.querySelectorAll('table.js-data-table').forEach(setupTable);

  document.querySelectorAll('.js-bulk-form').forEach(form => {
    form.addEventListener('submit', () => {
      const table = form.closest('.card')?.querySelector('table.js-data-table');
      if (!table) return;
      const rowids = Array.from(table.querySelectorAll('.js-row-select:checked')).map(cb => cb.dataset.rowid);
      const input = form.querySelector('.js-rowids');
      if (input) input.value = rowids.join(',');
    });
  });

  const analyticsDataEl = document.getElementById('external-analytics-data');
  if (analyticsDataEl) {
    const data = JSON.parse(analyticsDataEl.textContent || '{}');
    if (data.app_totals) {
      const ctx = document.getElementById('externalAppChart');
      if (ctx) {
        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: data.app_totals.map(r => r.app),
            datasets: [{
              label: 'Rows',
              data: data.app_totals.map(r => r.count),
              backgroundColor: ['#2CB6A5', '#F47C20', '#64748b', '#38bdf8', '#a78bfa']
            }]
          },
          options: { responsive: true, plugins: { legend: { display: false } } }
        });
      }

      const pie = document.getElementById('externalAppPie');
      if (pie) {
        new Chart(pie, {
          type: 'pie',
          data: {
            labels: data.app_totals.map(r => r.app),
            datasets: [{
              data: data.app_totals.map(r => r.count),
              backgroundColor: ['#2CB6A5', '#F47C20', '#64748b', '#38bdf8', '#a78bfa']
            }]
          }
        });
      }
    }

    if (data.table_totals) {
      const ctx = document.getElementById('externalTableChart');
      if (ctx) {
        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: data.table_totals.map(r => `${r.app}:${r.table}`),
            datasets: [{
              label: 'Rows',
              data: data.table_totals.map(r => r.count),
              backgroundColor: '#2CB6A5'
            }]
          },
          options: { responsive: true, plugins: { legend: { display: false } } }
        });
      }
    }
  }
});
