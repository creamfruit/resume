const toast = document.getElementById("admin-toast");
const actionButtons = document.querySelectorAll("[data-action]");
const filterTabs = document.querySelectorAll(".filter-tab");
const curseList = document.getElementById("curse-list");
const addProfanityBtn = document.getElementById("add-profanity-btn");

const reportsTable = document.getElementById("reports-table");
const reportQueue = document.getElementById("report-queue");
const reportQueueCount = document.querySelector(".queue-count");
const reportCase = document.getElementById("report-case");
const reportMeta = document.getElementById("report-meta");
const reportSummary = document.getElementById("report-summary");
const reportStatusChip = document.getElementById("report-status-chip");
const reportTypeChip = document.getElementById("report-type-chip");
const reportEditBtn = document.getElementById("report-edit-btn");
const reportResolveBtn = document.getElementById("report-resolve-btn");
const reportCloseBtn = document.getElementById("report-close-btn");
const reportDeleteBtn = document.getElementById("report-delete-btn");

const uiModal = document.getElementById("ui-modal");
const uiModalTitle = document.getElementById("ui-modal-title");
const uiModalBody = document.getElementById("ui-modal-body");
const uiModalActions = document.getElementById("ui-modal-actions");
const uiModalClose = document.getElementById("ui-modal-close");

let activeReportId = null;
let currentProfanityFilter = "all";
let reportsCache = [];

// Toast
function showToast(message) {
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timerId);
  showToast.timerId = window.setTimeout(() => {
    toast.classList.remove("show");
  }, 2200);
}

// Modal open
function openModal({ title, bodyHtml, actionsHtml }) {
  if (!uiModal || !uiModalTitle || !uiModalBody || !uiModalActions) return;
  uiModalTitle.textContent = title;
  uiModalBody.innerHTML = bodyHtml;
  uiModalActions.innerHTML = actionsHtml;
  uiModal.classList.add("show");
}

// Modal close
function closeModal() {
  if (!uiModal) return;
  uiModal.classList.remove("show");
}

if (uiModalClose) uiModalClose.addEventListener("click", closeModal);
if (uiModal) {
  uiModal.addEventListener("click", (e) => {
    if (e.target === uiModal) closeModal();
  });
}

// HTML escape
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

// API profanities
async function apiListProfanities(level) {
  const url = level && level !== "all" ? `/api/profanities?level=${encodeURIComponent(level)}` : "/sean/api/profanities";
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load profanities");
  return await res.json();
}

// API create
async function apiCreateProfanity(word, level) {
  const res = await fetch("/sean/api/profanities", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word, level }),
  });
  if (!res.ok) throw new Error("Failed to create profanity");
  return await res.json();
}

// API update
async function apiUpdateProfanity(id, word, level) {
  const res = await fetch(`/api/profanities/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ word, level }),
  });
  if (!res.ok) throw new Error("Failed to update profanity");
  return await res.json();
}

// API delete
async function apiDeleteProfanity(id) {
  const res = await fetch(`/api/profanities/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete profanity");
  return await res.json();
}

// API reports
async function apiListReports(status) {
  const url = status ? `/api/reports?status=${encodeURIComponent(status)}` : "/sean/api/reports";
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load reports");
  return await res.json();
}

// API create
async function apiCreateReport(payload) {
  const res = await fetch("/sean/api/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create report");
  return await res.json();
}

// API update
async function apiUpdateReport(id, payload) {
  const res = await fetch(`/api/reports/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update report");
  return await res.json();
}

// API delete
async function apiDeleteReport(id) {
  const res = await fetch(`/api/reports/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete report");
  return await res.json();
}

// Badge map
function statusToBadge(status) {
  switch ((status || "").toLowerCase()) {
    case "resolved":
    case "closed":
      return "badge-teal";
    case "escalated":
    case "high":
      return "badge-red";
    case "in_review":
      return "badge-teal";
    case "queued":
      return "badge-gray";
    default:
      return "badge-orange";
  }
}

// Chip map
function statusToChip(status) {
  switch ((status || "").toLowerCase()) {
    case "resolved":
    case "closed":
      return "status-chip success";
    case "escalated":
      return "status-chip danger";
    case "in_review":
      return "status-chip warn";
    case "queued":
      return "status-chip";
    default:
      return "status-chip warn";
  }
}

// Queue badge
function reportQueueBadge(status) {
  switch ((status || "").toLowerCase()) {
    case "escalated":
      return "queue-badge danger";
    case "in_review":
      return "queue-badge teal";
    case "resolved":
    case "closed":
      return "queue-badge";
    default:
      return "queue-badge warn";
  }
}

// Active report
function setActiveReport(report) {
  activeReportId = report ? report.id : null;
  if (reportCase) reportCase.textContent = report ? `Case ${report.case_id}` : "Select a report";
  if (reportMeta) {
    const usersLabel = [report?.user_a, report?.user_b].filter(Boolean).join(" / ");
    reportMeta.textContent = report
      ? `${report.report_type} • ${report.reporter}${usersLabel ? ` • ${usersLabel}` : ""}`
      : "Pick a report from the queue to review details.";
  }
  if (reportSummary) reportSummary.textContent = report?.summary || "No summary provided.";
  if (reportStatusChip) {
    reportStatusChip.className = statusToChip(report?.status);
    reportStatusChip.textContent = report?.status || "Status";
  }
  if (reportTypeChip) {
    reportTypeChip.className = "status-chip";
    reportTypeChip.textContent = report?.report_type || "Type";
  }

  document.querySelectorAll(".queue-item").forEach((item) => {
    item.classList.toggle("active", Number(item.dataset.reportId) === activeReportId);
  });

  document.querySelectorAll("#reports-table tr").forEach((row) => {
    row.classList.toggle("active", Number(row.dataset.reportId) === activeReportId);
  });
}

// Render reports
function renderReports(list) {
  if (reportsTable) {
    if (!list.length) {
      reportsTable.innerHTML = `
        <tr>
          <td colspan="7" style="color: var(--muted-foreground); padding: 1rem;">No reports yet.</td>
        </tr>
      `;
    } else {
      reportsTable.innerHTML = "";
      list.forEach((report) => {
        const usersLabel = [report.user_a, report.user_b].filter(Boolean).join(" / ") || "N/A";
        const row = document.createElement("tr");
        row.dataset.reportId = report.id;
        row.innerHTML = `
          <td>${escapeHtml(report.case_id)}</td>
          <td>${escapeHtml(report.report_type)}</td>
          <td>${escapeHtml(report.reporter)}</td>
          <td>${escapeHtml(usersLabel)}</td>
          <td><span class="badge ${statusToBadge(report.status)}">${escapeHtml(report.status)}</span></td>
          <td>${escapeHtml(report.updated_at || report.created_at || "")}</td>
          <td>
            <div class="table-actions">
              <button class="table-btn" data-edit-report="${report.id}">Edit</button>
              <button class="table-btn" data-resolve-report="${report.id}">Resolve</button>
              <button class="table-btn danger" data-delete-report="${report.id}">Delete</button>
            </div>
          </td>
        `;
        row.addEventListener("click", () => setActiveReport(report));
        reportsTable.appendChild(row);
      });
    }
  }

  if (reportQueue) {
    reportQueue.innerHTML = "";
    list.forEach((report) => {
      const usersLabel = [report.user_a, report.user_b].filter(Boolean).join(" / ");
      const btn = document.createElement("button");
      btn.className = "queue-item";
      btn.dataset.reportId = report.id;
      if (report.id === activeReportId) btn.classList.add("active");
      btn.innerHTML = `
        <div class="queue-avatar">${escapeHtml(report.case_id.slice(0, 2))}</div>
        <div class="queue-info">
          <div class="queue-title">${escapeHtml(report.case_id)} - ${escapeHtml(report.report_type)}</div>
          <div class="queue-meta">${escapeHtml(report.reporter)}${usersLabel ? ` / ${escapeHtml(usersLabel)}` : ""}</div>
        </div>
        <span class="${reportQueueBadge(report.status)}">${escapeHtml(report.status)}</span>
      `;
      btn.addEventListener("click", () => setActiveReport(report));
      reportQueue.appendChild(btn);
    });
  }

  if (reportQueueCount) {
    reportQueueCount.textContent = `${list.length} pending`;
  }
}

// Load reports
async function loadReports() {
  reportsCache = await apiListReports();
  renderReports(reportsCache);
  attachReportActions();
  const active = reportsCache.find((r) => r.id === activeReportId) || reportsCache[0];
  if (active) setActiveReport(active);
  else setActiveReport(null);
}

// Render words
function renderProfanities(list) {
  if (!curseList) return;
  curseList.innerHTML = "";
  if (!list.length) {
    curseList.innerHTML = `<div style="color: var(--muted-foreground);">No words yet.</div>`;
    return;
  }

  list.forEach((entry) => {
    const chip = document.createElement("span");
    chip.className = `curse-chip ${entry.level}`;
    chip.dataset.id = entry.id;
    chip.dataset.word = entry.word;
    chip.dataset.level = entry.level;
    chip.innerHTML = `
      <span class="curse-chip-content">
        <span>${escapeHtml(entry.word)}</span>
        <span class="curse-chip-actions">
          <button data-edit-profanity="${entry.id}">Edit</button>
          <button data-delete-profanity="${entry.id}">Delete</button>
        </span>
      </span>
    `;
    curseList.appendChild(chip);
  });
}

// Load words
async function loadProfanities() {
  const list = await apiListProfanities(currentProfanityFilter);
  renderProfanities(list);
  attachProfanityActions();
}

// Word modal
function openProfanityModal({ title, entry }) {
  openModal({
    title,
    bodyHtml: `
      <div style="display: grid; gap: 0.75rem;">
        <input class="ui-input" id="profanity-word" placeholder="Word or phrase" value="${escapeHtml(entry?.word || "")}" />
        <select class="ui-select" id="profanity-level">
          <option value="mild" ${entry?.level === "mild" ? "selected" : ""}>Mild</option>
          <option value="strong" ${entry?.level === "strong" ? "selected" : ""}>Strong</option>
          <option value="extreme" ${entry?.level === "extreme" ? "selected" : ""}>Extreme</option>
        </select>
      </div>
    `,
    actionsHtml: `
      <button class="ui-btn" id="modal-cancel">Cancel</button>
      <button class="ui-btn primary" id="modal-save">Save</button>
    `,
  });

  const cancel = document.getElementById("modal-cancel");
  const save = document.getElementById("modal-save");
  if (cancel) cancel.addEventListener("click", closeModal);
  if (save) {
    save.addEventListener("click", async () => {
      const word = (document.getElementById("profanity-word").value || "").trim();
      const level = (document.getElementById("profanity-level").value || "").trim();
      if (!word) return;
      try {
        if (entry?.id) {
          await apiUpdateProfanity(entry.id, word, level);
          showToast("Word updated");
        } else {
          await apiCreateProfanity(word, level);
          showToast("Word added");
        }
        closeModal();
        await loadProfanities();
      } catch (e) {
        alert("Could not save word.");
        console.error(e);
      }
    });
  }
}

// Report modal
function openReportModal({ title, report, presetType }) {
  openModal({
    title,
    bodyHtml: `
      <div style="display: grid; gap: 0.75rem;">
        <input class="ui-input" id="report-case-id" placeholder="Case ID" value="${escapeHtml(report?.case_id || "")}" ${report ? "disabled" : ""} />
        <input class="ui-input" id="report-type" placeholder="Type" value="${escapeHtml(report?.report_type || presetType || "")}" />
        <input class="ui-input" id="report-reporter" placeholder="Reporter" value="${escapeHtml(report?.reporter || "")}" ${report ? "disabled" : ""} />
        <input class="ui-input" id="report-user-a" placeholder="User A name" value="${escapeHtml(report?.user_a || "")}" />
        <input class="ui-input" id="report-user-b" placeholder="User B name" value="${escapeHtml(report?.user_b || "")}" />
        <select class="ui-select" id="report-status">
          <option value="queued" ${report?.status === "queued" ? "selected" : ""}>Queued</option>
          <option value="in_review" ${report?.status === "in_review" ? "selected" : ""}>In Review</option>
          <option value="escalated" ${report?.status === "escalated" ? "selected" : ""}>Escalated</option>
          <option value="resolved" ${report?.status === "resolved" ? "selected" : ""}>Resolved</option>
          <option value="closed" ${report?.status === "closed" ? "selected" : ""}>Closed</option>
        </select>
        <textarea class="ui-textarea" id="report-summary" placeholder="Summary">${escapeHtml(report?.summary || "")}</textarea>
      </div>
    `,
    actionsHtml: `
      <button class="ui-btn" id="modal-cancel">Cancel</button>
      <button class="ui-btn primary" id="modal-save">Save</button>
    `,
  });

  const cancel = document.getElementById("modal-cancel");
  const save = document.getElementById("modal-save");
  if (cancel) cancel.addEventListener("click", closeModal);
  if (save) {
    save.addEventListener("click", async () => {
      const caseId = (document.getElementById("report-case-id").value || "").trim();
      const reportType = (document.getElementById("report-type").value || "").trim();
      const reporter = (document.getElementById("report-reporter").value || "").trim();
      const userA = (document.getElementById("report-user-a").value || "").trim();
      const userB = (document.getElementById("report-user-b").value || "").trim();
      const status = (document.getElementById("report-status").value || "").trim();
      const summary = (document.getElementById("report-summary").value || "").trim();
      try {
        if (report?.id) {
          await apiUpdateReport(report.id, { status, summary, user_a: userA, user_b: userB });
          showToast("Report updated");
        } else {
          await apiCreateReport({ case_id: caseId, report_type: reportType, reporter, status, summary, user_a: userA, user_b: userB });
          showToast("Report created");
        }
        closeModal();
        await loadReports();
      } catch (e) {
        alert("Could not save report.");
        console.error(e);
      }
    });
  }
}

// Report actions
function attachReportActions() {
  if (!reportsTable) return;

  reportsTable.querySelectorAll("[data-edit-report]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = Number(btn.getAttribute("data-edit-report"));
      const report = reportsCache.find((r) => r.id === id);
      if (!report) return;
      openReportModal({ title: "Edit report", report });
    });
  });

  reportsTable.querySelectorAll("[data-resolve-report]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = Number(btn.getAttribute("data-resolve-report"));
      try {
        await apiUpdateReport(id, { status: "resolved" });
        showToast("Report resolved");
        await loadReports();
      } catch (err) {
        alert("Could not resolve report.");
        console.error(err);
      }
    });
  });

  reportsTable.querySelectorAll("[data-delete-report]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = Number(btn.getAttribute("data-delete-report"));
      openModal({
        title: "Delete report?",
        bodyHtml: `<div style="color: var(--muted-foreground); font-weight: 700;">This will permanently remove the report.</div>`,
        actionsHtml: `
          <button class="ui-btn" id="modal-cancel">Cancel</button>
          <button class="ui-btn danger" id="modal-delete">Delete</button>
        `,
      });
      const cancel = document.getElementById("modal-cancel");
      const del = document.getElementById("modal-delete");
      if (cancel) cancel.addEventListener("click", closeModal);
      if (del) {
        del.addEventListener("click", async () => {
          try {
            await apiDeleteReport(id);
            closeModal();
            showToast("Report deleted");
            await loadReports();
          } catch (err) {
            alert("Could not delete report.");
            console.error(err);
          }
        });
      }
    });
  });
}

// Word actions
function attachProfanityActions() {
  if (!curseList) return;

  curseList.querySelectorAll("[data-edit-profanity]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.getAttribute("data-edit-profanity"));
      const chip = btn.closest(".curse-chip");
      const entry = {
        id,
        word: chip?.dataset.word || "",
        level: chip?.dataset.level || "mild",
      };
      openProfanityModal({ title: "Edit word", entry });
    });
  });

  curseList.querySelectorAll("[data-delete-profanity]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = Number(btn.getAttribute("data-delete-profanity"));
      openModal({
        title: "Delete word?",
        bodyHtml: `<div style="color: var(--muted-foreground); font-weight: 700;">Remove this word from the list?</div>`,
        actionsHtml: `
          <button class="ui-btn" id="modal-cancel">Cancel</button>
          <button class="ui-btn danger" id="modal-delete">Delete</button>
        `,
      });
      const cancel = document.getElementById("modal-cancel");
      const del = document.getElementById("modal-delete");
      if (cancel) cancel.addEventListener("click", closeModal);
      if (del) {
        del.addEventListener("click", async () => {
          try {
            await apiDeleteProfanity(id);
            closeModal();
            showToast("Word deleted");
            await loadProfanities();
          } catch (err) {
            alert("Could not delete word.");
            console.error(err);
          }
        });
      }
    });
  });
}

if (addProfanityBtn) {
  addProfanityBtn.addEventListener("click", () => openProfanityModal({ title: "Add word" }));
}

if (reportEditBtn) {
  reportEditBtn.addEventListener("click", () => {
    const report = reportsCache.find((r) => r.id === activeReportId);
    if (!report) return;
    openReportModal({ title: "Edit report", report });
  });
}

if (reportResolveBtn) {
  reportResolveBtn.addEventListener("click", async () => {
    if (!activeReportId) return;
    try {
      await apiUpdateReport(activeReportId, { status: "resolved" });
      showToast("Report resolved");
      await loadReports();
    } catch (e) {
      alert("Could not resolve report.");
      console.error(e);
    }
  });
}

if (reportCloseBtn) {
  reportCloseBtn.addEventListener("click", async () => {
    if (!activeReportId) return;
    try {
      await apiUpdateReport(activeReportId, { status: "closed" });
      showToast("Case closed");
      await loadReports();
    } catch (e) {
      alert("Could not close case.");
      console.error(e);
    }
  });
}

if (reportDeleteBtn) {
  reportDeleteBtn.addEventListener("click", () => {
    if (!activeReportId) return;
    openModal({
      title: "Delete report?",
      bodyHtml: `<div style="color: var(--muted-foreground); font-weight: 700;">This will permanently remove the report.</div>`,
      actionsHtml: `
        <button class="ui-btn" id="modal-cancel">Cancel</button>
        <button class="ui-btn danger" id="modal-delete">Delete</button>
      `,
    });
    const cancel = document.getElementById("modal-cancel");
    const del = document.getElementById("modal-delete");
    if (cancel) cancel.addEventListener("click", closeModal);
    if (del) {
      del.addEventListener("click", async () => {
        try {
          await apiDeleteReport(activeReportId);
          closeModal();
          showToast("Report deleted");
          await loadReports();
        } catch (err) {
          alert("Could not delete report.");
          console.error(err);
        }
      });
    }
  });
}

const createReportBtn = document.querySelector("[data-action='Create report']");
const openIncidentBtn = document.querySelector("[data-action='Open incident']");

if (createReportBtn) {
  createReportBtn.dataset.actionHandled = "true";
  createReportBtn.addEventListener("click", () => openReportModal({ title: "Create report" }));
}

if (openIncidentBtn) {
  openIncidentBtn.dataset.actionHandled = "true";
  openIncidentBtn.addEventListener("click", () => openReportModal({ title: "Open incident", presetType: "Incident" }));
}

actionButtons.forEach((btn) => {
  if (btn.dataset.actionHandled === "true") return;
  btn.addEventListener("click", () => {
    const label = btn.dataset.action || "Action";
    showToast(`${label} queued`);
  });
});

filterTabs.forEach((tab) => {
  tab.addEventListener("click", async () => {
    filterTabs.forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    currentProfanityFilter = tab.dataset.filter || "all";
    try {
      await loadProfanities();
    } catch (e) {
      alert("Could not load words.");
      console.error(e);
    }
  });
});

// Init
async function init() {
  try {
    await loadReports();
  } catch (e) {
    console.error(e);
  }

  try {
    await loadProfanities();
  } catch (e) {
    console.error(e);
  }
}

init();
