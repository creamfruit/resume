const statusText = document.getElementById("statusText");
const preview = document.getElementById("avatarPreview");
const btnRandom = document.getElementById("btnRandom");
const btnSave = document.getElementById("btnSave");
const avatarNameInput = document.getElementById("avatarName");
const poseSelect = document.getElementById("poseSelect");
const genderSelect = document.getElementById("genderSelect");
const skinSelect = document.getElementById("skinSelect");

let OPTIONS = {};
let DEFAULT = {};
let current = {};
const layerEls = {};

const LAYER_ORDER = ["base", "top", "face", "eyes", "mouth", "hair", "glasses"];
const FOLDERS = {
  base: "base",
  face: "face",
  eyes: "eyes",
  mouth: "mouth",
  hair: "hair",
  glasses: "glasses",
  top: "top",
};

const PRESETS = {
  friendly: { mouth: "mouth_1", eyes: "eyes_1" },
  happy: { mouth: "mouth_1", eyes: "eyes_2" },
  calm: { mouth: "mouth_2", eyes: "eyes_1" },
  serious: { mouth: "mouth_2", eyes: "eyes_2" },
};

function demoHeaders(extra) {
  const headers = extra ? { ...extra } : {};
  const demoId = sessionStorage.getItem("demo_user_id");
  if (demoId) headers["X-Demo-User"] = demoId;
  return headers;
}

function setStatus(msg) {
  if (statusText) statusText.textContent = msg || "";
}

function toTitle(text) {
  return String(text || "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function assetUrl(category, variant) {
  return `${window.AVATAR_ASSET_BASE}${FOLDERS[category]}/${variant}.svg`;
}

function applyDerivedLayers() {
  const pose = current.pose || "waving";
  const tone = current.skin_tone || "light";
  current.base = `body_${pose}`;
  current.face = `face_${tone}`;
}

function buildPreview() {
  if (!preview) return;
  applyDerivedLayers();
  if (!Object.keys(layerEls).length) {
    LAYER_ORDER.forEach((key) => {
      const img = document.createElement("img");
      img.className = "layer";
      img.alt = key;
      preview.appendChild(img);
      layerEls[key] = img;
    });
  }
  LAYER_ORDER.forEach((key) => {
    const src = assetUrl(key, current[key]);
    if (layerEls[key].getAttribute("src") !== src) {
      layerEls[key].setAttribute("src", src);
    }
  });
}

function createThumb(category, variant, selectedValue, onSelect) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "thumb-btn" + (selectedValue === variant ? " active" : "");
  btn.innerHTML = `<img src="${assetUrl(category, variant)}" alt="${toTitle(variant)}"><span class="thumb-label">${toTitle(variant)}</span>`;
  btn.addEventListener("click", () => onSelect(variant));
  return btn;
}

function renderThumbGrid(containerId, category, selectedValue, onSelect) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";
  const list = OPTIONS[category] || [];
  list.forEach((variant) => {
    container.appendChild(createThumb(category, variant, selectedValue, onSelect));
  });
}

function renderAllThumbs() {
  renderThumbGrid("eyesChoices", "eyes", current.eyes, (value) => {
    current.eyes = value;
    buildPreview();
    renderAllThumbs();
    setStatus("Unsaved changes");
  });
  renderThumbGrid("mouthChoices", "mouth", current.mouth, (value) => {
    current.mouth = value;
    buildPreview();
    renderAllThumbs();
    setStatus("Unsaved changes");
  });
  renderThumbGrid("hairChoices", "hair", current.hair, (value) => {
    current.hair = value;
    buildPreview();
    renderAllThumbs();
    setStatus("Unsaved changes");
  });
  renderThumbGrid("outfitChoices", "top", current.top, (value) => {
    current.top = value;
    buildPreview();
    renderAllThumbs();
    setStatus("Unsaved changes");
  });
  renderThumbGrid("accessoryChoices", "glasses", current.glasses, (value) => {
    current.glasses = value;
    buildPreview();
    renderAllThumbs();
    setStatus("Unsaved changes");
  });
}

function randomPick(arr, fallback) {
  if (!arr || !arr.length) return fallback;
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomize() {
  current.pose = randomPick(OPTIONS.pose, current.pose);
  current.skin_tone = randomPick(OPTIONS.skin_tone, current.skin_tone);
  current.eyes = randomPick(OPTIONS.eyes, current.eyes);
  current.mouth = randomPick(OPTIONS.mouth, current.mouth);
  current.hair = randomPick(OPTIONS.hair, current.hair);
  current.glasses = randomPick(OPTIONS.glasses, current.glasses);
  current.top = randomPick(OPTIONS.top, current.top);
  syncControlsFromState();
  buildPreview();
  renderAllThumbs();
  setStatus("Unsaved changes");
}

function applyPreset(name) {
  const preset = PRESETS[name];
  if (!preset) return;
  Object.assign(current, preset);
  buildPreview();
  renderAllThumbs();
  setStatus("Unsaved changes");
}

function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-content").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tabName}`);
  });
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
}

function bindPresets() {
  document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => applyPreset(btn.dataset.preset));
  });
}

function syncControlsFromState() {
  if (avatarNameInput) avatarNameInput.value = current.avatar_name || "";
  if (poseSelect) poseSelect.value = current.pose || DEFAULT.pose || "waving";
  if (genderSelect) genderSelect.value = current.gender || DEFAULT.gender || "girl";
  if (skinSelect) skinSelect.value = current.skin_tone || DEFAULT.skin_tone || "light";
}

async function loadOptions() {
  const res = await fetch("/api/avatar/options", { headers: demoHeaders() });
  if (!res.ok) throw new Error("Failed to load options");
  const data = await res.json();
  OPTIONS = data.options || {};
  DEFAULT = data.default || {};
}

async function loadMe() {
  const res = await fetch("/api/avatar/me", { headers: demoHeaders() });
  if (!res.ok) throw new Error("Failed to load avatar");
  const data = await res.json();
  current = data.config || {};
}

function attachFieldEvents() {
  if (avatarNameInput) {
    avatarNameInput.addEventListener("input", () => {
      current.avatar_name = avatarNameInput.value.trim();
      setStatus("Unsaved changes");
    });
  }
  if (poseSelect) {
    poseSelect.addEventListener("change", () => {
      current.pose = poseSelect.value;
      buildPreview();
      setStatus("Unsaved changes");
    });
  }
  if (genderSelect) {
    genderSelect.addEventListener("change", () => {
      current.gender = genderSelect.value;
      if (current.gender === "boy") current.hair = "hair_1";
      if (current.gender === "girl") current.hair = "hair_2";
      buildPreview();
      renderAllThumbs();
      setStatus("Unsaved changes");
    });
  }
  if (skinSelect) {
    skinSelect.addEventListener("change", () => {
      current.skin_tone = skinSelect.value;
      buildPreview();
      setStatus("Unsaved changes");
    });
  }
}

async function saveMe() {
  setStatus("Saving...");
  if (avatarNameInput) current.avatar_name = avatarNameInput.value.trim();
  const res = await fetch("/api/avatar/me", {
    method: "POST",
    headers: demoHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ config: current }),
  });
  if (!res.ok) {
    setStatus("Save failed");
    return;
  }
  const data = await res.json();
  current = { ...DEFAULT, ...(data.config || {}) };
  syncControlsFromState();
  buildPreview();
  renderAllThumbs();
  setStatus("Saved");
}

if (btnRandom) btnRandom.addEventListener("click", randomize);
if (btnSave) btnSave.addEventListener("click", saveMe);

(async function init() {
  try {
    await loadOptions();
    await loadMe();
    current = { ...DEFAULT, ...current };
    bindTabs();
    bindPresets();
    attachFieldEvents();
    syncControlsFromState();
    buildPreview();
    renderAllThumbs();
    setStatus("");
  } catch (error) {
    console.error(error);
    setStatus("Could not load avatar builder");
  }
})();
