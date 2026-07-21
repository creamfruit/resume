const output = document.getElementById("output");
const debug = document.getElementById("debug");
const inventoryEl = document.getElementById("inventory");
const statsEl = document.getElementById("stats");
const equipmentEl = document.getElementById("equipment");
const enemyBox = document.getElementById("enemyBox");
const statButtons = document.getElementById("statButtons");
const statsPanel = document.getElementById("statsPanel");
const btnToggleStats = document.getElementById("btnToggleStats");
const aiStatusEl = document.getElementById("aiStatus");
const itemDetailsEl = document.getElementById("itemDetails");
const combatLogEl = document.getElementById("combatLog");
const roomEventsEl = document.getElementById("roomEvents");
const recentDropsEl = document.getElementById("recentDrops");
const turnSummaryEl = document.getElementById("turnSummary");
const turnSummaryStripEl = document.getElementById("turnSummaryStrip");
const phaseBannerEl = document.getElementById("phaseBanner");
const runProgressEl = document.getElementById("runProgress");
const runRulesEl = document.getElementById("runRules");
const runGainsEl = document.getElementById("runGains");
const exitReadyEl = document.getElementById("exitReady");
const roomBriefEl = document.getElementById("roomBrief");
const combatPressureEl = document.getElementById("combatPressure");
const victoryForecastEl = document.getElementById("victoryForecast");
const intentBannerEl = document.getElementById("intentBanner");
const intentKindEl = document.querySelector("#intentBanner .intent-kind");
const intentThreatEl = document.getElementById("intentThreat");
const intentTextEl = document.getElementById("intentText");
const combatCommandShellEl = document.getElementById("combatCommandShell");
const passiveFeedEl = document.getElementById("passiveFeed");
const tabs = Array.from(document.querySelectorAll(".tab"));
const combatView = document.getElementById("combat-view");
const tabView = document.getElementById("tab-view");
const tabTitle = document.getElementById("tab-title");
const tabContent = document.getElementById("tab-content");
const hudBarEl = document.querySelector(".hud-bar");
const chipDepthEl = document.getElementById("chipDepth");
const chipRoomEl = document.getElementById("chipRoom");
const chipGoldEl = document.getElementById("chipGold");
const chipEssenceEl = document.getElementById("chipEssence");
const chipChestEl = document.getElementById("chipChest");
const combatRunContextEl = document.getElementById("combatRunContext");
const combatEmptyStateEl = document.getElementById("combatEmptyState");
const combatEmptyHintEl = document.getElementById("combatEmptyHint");
const combatEmptyCtaEl = document.getElementById("combatEmptyCta");
const combatToplineEl = document.getElementById("combatTopline");
const combatNavButtons = Array.from(document.querySelectorAll("[data-combat-nav]"));
const combatMiniTabs = Array.from(document.querySelectorAll(".combat-mini-tab"));
const combatNavHomeEl = document.getElementById("combatNavHome");
const combatNavAreasEl = document.getElementById("combatNavAreas");
const combatSetupToggleEl = document.getElementById("combatSetupToggle");
const combatDetailsToggleEl = document.getElementById("combatDetailsToggle");
const combatDetailsWrapEl = document.getElementById("combatDetailsWrap");
const combatUtilityToggleEl = document.getElementById("combatUtilityToggle");
const combatSetupWrapEl = document.getElementById("combatSetupWrap");
const hudPlayerEl = document.getElementById("hudPlayer");
const hudEnemyEl = document.getElementById("hudEnemy");
const hudPhaseEl = document.getElementById("hudPhase");
const arenaGridEl = document.getElementById("arenaGrid");
const arenaShellEl = document.getElementById("arenaShell");
const playerPanelTitleEl = document.getElementById("playerPanelTitle");
const enemyPanelTitleEl = document.getElementById("enemyPanelTitle");
const quickStaminaEl = document.getElementById("quickStamina");
const quickEnemyEl = document.getElementById("quickEnemy");
const quickRollEl = document.getElementById("quickRoll");
const quickRerollsEl = document.getElementById("quickRerolls");
const quickCurseEl = document.getElementById("quickCurse");
const combatReadoutEl = document.getElementById("combatReadout");
const pathPreviewEl = document.getElementById("pathPreview");
const rollHistoryEl = document.getElementById("rollHistory");
const combatDeckEl = document.getElementById("combatDeck");
const rollFocusEl = document.getElementById("rollFocus");
const turnExplainEl = document.getElementById("turnExplain");
const roomResolutionEl = document.getElementById("roomResolution");
const offlineModalEl = document.getElementById("offlineModal");
const offlineSummaryBodyEl = document.getElementById("offlineSummaryBody");
const btnOfflineClose = document.getElementById("btnOfflineClose");
const btnOfflineClaim = document.getElementById("btnOfflineClaim");
const guideModalEl = document.getElementById("guideModal");
const guideModalBodyEl = document.getElementById("guideModalBody");
const btnGuideClose = document.getElementById("btnGuideClose");
const btnGuideHide = document.getElementById("btnGuideHide");
const btnGuidePrimary = document.getElementById("btnGuidePrimary");
const runClearModalEl = document.getElementById("runClearModal");
const runClearBodyEl = document.getElementById("runClearBody");
const btnRunClearClose = document.getElementById("btnRunClearClose");
const btnRunClearHome = document.getElementById("btnRunClearHome");
const btnRunClearContinue = document.getElementById("btnRunClearContinue");
const accountSelectEl = document.getElementById("accountSelect");
const accountInputEl = document.getElementById("accountInput");
const btnAccountUse = document.getElementById("btnAccountUse");
const btnAccountCreate = document.getElementById("btnAccountCreate");
const btnAccountSave = document.getElementById("btnAccountSave");
const btnAccountRename = document.getElementById("btnAccountRename");
const btnAccountDelete = document.getElementById("btnAccountDelete");
const accountStatusEl = document.getElementById("accountStatus");
const accountSavedAtEl = document.getElementById("accountSavedAt");
const accountActiveChipEl = document.getElementById("accountActiveChip");
const accountCountChipEl = document.getElementById("accountCountChip");
const accountSaveChipEl = document.getElementById("accountSaveChip");
const tradeAlertChipEl = document.getElementById("tradeAlertChip");

/* âœ… Step 15: Boss intent UI */
const bossIntentEl = document.getElementById("bossIntent");
let lastBossIntent = null;

const riskSlider = document.getElementById("risk");
const riskValue = document.getElementById("riskValue");

const btnStart = document.getElementById("btnStart");
const btnTurn = document.getElementById("btnTurn");
const btnReroll = document.getElementById("btnReroll");
const btnDodgeAction = document.getElementById("btnDodge");
const btnPAtk = document.getElementById("btnPAtk");
const btnLeave = document.getElementById("btnLeave");
const btnEAtk = document.getElementById("btnEAtk");
const btnStash = document.getElementById("btnStash");
const btnPrestige = document.getElementById("btnPrestige");
const btnAdvanced = document.getElementById("btnAdvanced");
const advancedControls = document.getElementById("advancedControls");
const btnClearLog = document.getElementById("btnClearLog");
const btnClearDrops = document.getElementById("btnClearDrops");
const actionButtons = Array.from(document.querySelectorAll(".action-btn"));
const actionBriefEl = document.getElementById("actionBrief");
const actionDockEl = document.getElementById("actionDock");

const safeZone = document.getElementById("safeZone");
const marker = document.getElementById("marker");
const dodgeResult = document.getElementById("dodgeResult");
const dodgeStatus = document.getElementById("dodgeStatus");
const dodgeWindowText = document.getElementById("dodgeWindowText");
const dodgeCardEl = document.querySelector(".dodge-card");
const dodgeOverlayEl = document.getElementById("dodgeOverlay");
const dodgeOverlayCardEl = document.getElementById("dodgeOverlayCard");
const dodgeOverlayHintEl = document.getElementById("dodgeOverlayHint");
const dodgeOverlaySafeZoneEl = document.getElementById("dodgeOverlaySafeZone");
const dodgeOverlayMarkerEl = document.getElementById("dodgeOverlayMarker");
const dodgeOverlayStatusEl = document.getElementById("dodgeOverlayStatus");
const dodgeOverlayWindowTextEl = document.getElementById("dodgeOverlayWindowText");
const dodgeOverlayResultEl = document.getElementById("dodgeOverlayResult");
const dodgeOverlayActionEl = document.getElementById("dodgeOverlayAction");
const playerSupportGridEl = document.querySelector(".player-support-grid");
const enemySupportGridEl = document.querySelector(".enemy-support-grid");

/* âœ… Status containers */
const playerStatusList = document.getElementById("player-status-list");
const playerStatusMini = document.getElementById("player-status-mini");
const enemyStatusList = document.getElementById("enemy-status-list");
const playerCombatCard = document.getElementById("playerCombatCard");
const leftPanelEl = document.querySelector(".left-panel");
const rightPanelEl = document.querySelector(".right-panel");
const inventoryBlockEl = inventoryEl?.closest(".stack-block") || null;
const turnSummaryBlockEl = turnSummaryEl?.closest(".collapsible-block") || null;
const passiveFeedBlockEl = passiveFeedEl?.closest(".collapsible-block") || null;
const combatLogBlockEl = combatLogEl?.closest(".collapsible-block") || null;
const roomEventsBlockEl = roomEventsEl?.closest(".collapsible-block") || null;
const recentDropsBlockEl = recentDropsEl?.closest(".stack-block") || null;
const itemDetailsBlockEl = itemDetailsEl?.closest(".stack-block") || null;

let dodgeInterval = null;
let markerPos = 0;
let markerDir = 1;
let currentWindow = { leftPct: 60, widthPct: 12 };
let lastDodgeSuccess = false;
let dodgePhasePrimed = false;

let lastStats = null;
let lastEnemy = null;
let activeTab = "home";
let selectedItem = null;
let selectedAction = "basic";
let lastShopListings = [];
let bankFilters = { rarity: "all", source: "all", sort: "power_desc", search: "" };
let shopFilters = { kind: "all", rarity: "all", source: "all", sort: "price_asc", search: "" };
let bankPage = 1;
let shopPage = 1;
let selectedBankIndex = -1;
let bankSellMode = false;
let shopOfferPicker = { auctionId: "", stash: [], selected: [] };
let tradeComposer = { target: "", stash: [], selected: [], requestedPool: [], requested: [], goldOffer: 0, goldRequest: 0, note: "" };
const PAGE_SIZE = 8;
let recentDrops = [];
let recentRoomEvents = [];
let awaitingEnemyPhase = false;
let lastState = null;
let lastRunResult = null;
let combatFxTimer = null;
let turnSummaryStripTimer = null;
let combatSetupOpen = false;
let combatDetailsOpen = false;
let combatUtilityOpen = false;
let idleStateCache = null;
let shownOfflineSummaryAt = 0;
let accountStateCache = null;
let autosaveTimer = null;
let lastRollFocus = null;
let lastRoomResolution = null;
let lastTurnExplain = [];
let latestPlayerStatus = {};
let latestEnemyStatus = {};
let latestTradeInboxAt = 0;
let latestGuideState = null;
let guideModalActionTab = "home";
let guideModalOpen = false;
let runClearModalOpen = false;

function getTradeSeenKey() {
  const active = normalizeAccountName(accountStateCache?.active || lastStats?.account?.active || "default");
  return `trade_seen_${active}`;
}

function getGuideSeenKey() {
  const active = normalizeAccountName(accountStateCache?.active || lastStats?.account?.active || "default");
  return `guide_seen_${active}`;
}

function hasSeenGuideModal() {
  try {
    return window.localStorage.getItem(getGuideSeenKey()) === "1";
  } catch {
    return false;
  }
}

function markGuideModalSeen() {
  try {
    window.localStorage.setItem(getGuideSeenKey(), "1");
  } catch {}
}

function hideGuideModal(markSeen = true) {
  if (markSeen) markGuideModalSeen();
  guideModalOpen = false;
  guideModalEl?.classList.add("hidden");
}

function maybeShowGuideModal(guide = null) {
  if (!guideModalEl || !guideModalBodyEl || !btnGuidePrimary) return;
  if (guideModalOpen) return;
  const nextStep = guide?.next_step || null;
  if (!guide?.show || !nextStep) return;
  if (hasSeenGuideModal()) return;

  guideModalActionTab = String(nextStep.tab || "home");
  guideModalBodyEl.innerHTML = `
    <div class="home-summary-line"><b>${nextStep.label || "Start here"}</b></div>
    <div class="home-summary-line">${nextStep.detail || "Follow this guide to learn the early game flow."}</div>
    <div class="battle-rule-strip compact" style="margin-top:10px;">
      <span>${Number(guide?.completed_count || 0)}/${Number(guide?.total_count || 0) || 5} complete</span>
      <span>Starter Guide</span>
    </div>
  `;
  btnGuidePrimary.textContent = String(nextStep.cta_label || "Open");
  guideModalEl.classList.remove("hidden");
  guideModalOpen = true;
}

function hideRunClearModal() {
  runClearModalOpen = false;
  runClearModalEl?.classList.add("hidden");
}

function showRunClearModal(result = {}) {
  if (!runClearModalEl || !runClearBodyEl) return;
  const loot = Array.isArray(result?.loot) ? result.loot : [];
  const lootNames = loot.slice(0, 5).map((row) => String(row?.name || row?.id || "Loot")).filter(Boolean);
  const starterBonus = result?.starter_bonus || null;
  const summaryBits = [];
  if (Number(result?.gold_gained || 0) > 0) summaryBits.push(`${Number(result.gold_gained)} gold`);
  if (Number(result?.depth || 0) > 0) summaryBits.push(`Depth ${Number(result.depth)}`);
  if (Number(result?.next_depth || 0) > 0) summaryBits.push(`Next ${Number(result.next_depth)}`);
  runClearBodyEl.innerHTML = `
    <div class="home-summary-line"><b>Dungeon cleared</b></div>
    <div class="battle-rule-strip compact" style="margin-top:10px;">
      <span>${summaryBits[0] || "Rewards locked"}</span>
      <span>${summaryBits[1] || `Loot ${loot.length}`}</span>
      <span>${summaryBits[2] || "Depth open"}</span>
    </div>
    <div class="home-summary-line">Your run rewards are locked in. Next depth ${result?.next_depth ?? "-"} is now available.</div>
    <div class="home-stat-strip">
      <span>Loot ${loot.length}</span>
      <span>Boss Down</span>
      <span>Next ${result?.next_depth ?? "-"}</span>
    </div>
    ${starterBonus ? `
      <div class="battle-rule-strip compact" style="margin-top:10px;">
        <span>Starter Cache</span>
        <span>+${Number(starterBonus.gold || 0)}g</span>
        <span>+${Number(starterBonus.arcane_chest || 0)} chest</span>
        <span>+${Number(starterBonus.idle_tonic || 0)} tonic</span>
        <span>+${Number(starterBonus.rune_essence || 0)} essence</span>
      </div>
    ` : ""}
    <div class="home-summary-line">${lootNames.length ? `Drops: ${lootNames.join(", ")}` : "No drops this run."}</div>
  `;
  runClearModalEl.classList.remove("hidden");
  runClearModalOpen = true;
}

function getSeenTradeInboxAt() {
  try {
    return Number(window.localStorage.getItem(getTradeSeenKey()) || 0);
  } catch {
    return 0;
  }
}

function markTradeInboxSeen(ts = null) {
  const value = Number(ts ?? (latestTradeInboxAt || 0));
  try {
    window.localStorage.setItem(getTradeSeenKey(), String(value));
  } catch {}
}

function collapseCombatPanels() {
  combatSetupOpen = false;
  combatDetailsOpen = false;
  combatUtilityOpen = false;
  updateCombatSetupToggle();
  updateCombatDetailsToggle();
  updateCombatUtilityToggle();
  updateCombatDetailBlocksVisibility();
}

function refreshCombatLayoutMode() {
  const isCombat = document.body.dataset.view === "combat";
  document.body.classList.toggle("combat-minimal", isCombat);
}

function openCombatOverlay(panel) {
  combatSetupOpen = panel === "setup" ? !combatSetupOpen : false;
  combatDetailsOpen = panel === "details" ? !combatDetailsOpen : false;
  combatUtilityOpen = panel === "utility" ? !combatUtilityOpen : false;
  updateCombatSetupToggle();
  updateCombatDetailsToggle();
  updateCombatUtilityToggle();
  updateCombatDetailBlocksVisibility();
}

function syncActiveTabButtons() {
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === activeTab));
  combatMiniTabs.forEach((t) => t.classList.toggle("active", t.dataset.combatNav === activeTab));
}

async function setActiveTab(nextTab) {
  activeTab = nextTab || "home";
  syncActiveTabButtons();
  refreshCombatLayoutMode();
  if (activeTab === "shop") {
    markTradeInboxSeen();
  }
  await renderActiveTab();
}

function setTurnSummaryStrip(text, forceShow = false) {
  if (!turnSummaryStripEl) return;
  const value = String(text || "").trim();
  turnSummaryStripEl.textContent = value || "--";
  const hide = !forceShow && (!value || value === "--");
  turnSummaryStripEl.classList.toggle("hidden", hide);
  if (turnSummaryStripTimer) {
    clearTimeout(turnSummaryStripTimer);
    turnSummaryStripTimer = null;
  }
  const sticky = /Boss defeated|Run complete|Dungeon cleared/i.test(value);
  if (!hide && !sticky) {
    turnSummaryStripTimer = setTimeout(() => {
      turnSummaryStripEl.classList.add("hidden");
    }, 2600);
  }
}

function setDodgeResultText(text, forceShow = false) {
  const value = String(text || "").trim();
  const hide = !forceShow && (!value || value === "Not started.");
  if (dodgeResult) {
    dodgeResult.textContent = value || "Not started.";
    dodgeResult.classList.toggle("hidden", hide);
  }
  if (dodgeOverlayResultEl) {
    dodgeOverlayResultEl.textContent = value || "";
    dodgeOverlayResultEl.classList.toggle("hidden", hide);
    dodgeOverlayResultEl.classList.remove("success", "fail");
    if (!hide) {
      if (/success|evaded/i.test(value)) dodgeOverlayResultEl.classList.add("success");
      if (/fail|hit/i.test(value)) dodgeOverlayResultEl.classList.add("fail");
    }
  }
  updateDodgeCardVisibility();
  updateDodgeOverlayVisibility();
}

function updateDodgeCardVisibility() {
  if (!dodgeCardEl) return;
  dodgeCardEl.classList.add("hidden");
  updateArenaSupportVisibility();
}

function setDodgeWindowActive(active = false) {
  if (dodgeOverlayEl) {
    document.body.classList.toggle("dodge-live", Boolean(active));
  }
}

function updateDodgeOverlayVisibility() {
  if (!dodgeOverlayEl) return;
  const visible = document.body.dataset.view === "combat" && awaitingEnemyPhase;
  dodgeOverlayEl.classList.toggle("hidden", !visible);
  document.body.classList.toggle("dodge-active", visible);
  if (visible) {
    dodgeOverlayCardEl?.focus();
  } else {
    setDodgeWindowActive(false);
  }
}

function updateArenaSupportVisibility() {
  const playerSupportCards = Array.from(playerSupportGridEl?.children || []);
  const enemySupportCards = Array.from(enemySupportGridEl?.children || []);
  const hasPlayerSupport = playerSupportCards.some((el) => !el.classList.contains("hidden"));
  const hasEnemySupport = enemySupportCards.some((el) => !el.classList.contains("hidden")) || !(dodgeCardEl?.classList.contains("hidden") ?? true);
  playerSupportGridEl?.classList.toggle("hidden", !hasPlayerSupport);
  enemySupportGridEl?.classList.toggle("hidden", !hasEnemySupport);
}

function updateCombatDetailBlocksVisibility() {
  const inventoryEmpty = !inventoryEl || inventoryEl.children.length === 0;
  const turnEmpty = isEmptyUiText(String(turnSummaryEl?.textContent || ""));
  const passiveEmpty = isEmptyUiText(String(passiveFeedEl?.textContent || ""));
  const combatLogEmpty = isEmptyUiText(String(combatLogEl?.textContent || ""));
  const roomEventsEmpty = isEmptyUiText(String(roomEventsEl?.textContent || ""));
  const dropsEmpty = isEmptyUiText(String(recentDropsEl?.textContent || ""));
  const itemDetailsEmpty = isEmptyUiText(String(itemDetailsEl?.textContent || ""));
  inventoryBlockEl?.classList.toggle("hidden", inventoryEmpty);
  turnSummaryBlockEl?.classList.toggle("hidden", turnEmpty);
  passiveFeedBlockEl?.classList.toggle("hidden", passiveEmpty);
  combatLogBlockEl?.classList.toggle("hidden", combatLogEmpty);
  roomEventsBlockEl?.classList.toggle("hidden", roomEventsEmpty);
  recentDropsBlockEl?.classList.toggle("hidden", dropsEmpty);
  itemDetailsBlockEl?.classList.toggle("hidden", itemDetailsEmpty);
  if (rightPanelEl && document.body.dataset.view === "combat") {
    const hasVisibleBlocks = Array.from(rightPanelEl.querySelectorAll(".stack-block")).some((el) => !el.classList.contains("hidden"));
    const showRightPanel = combatUtilityOpen && hasVisibleBlocks;
    rightPanelEl.classList.toggle("combat-collapsed", !combatUtilityOpen);
    rightPanelEl.classList.toggle("hidden", !showRightPanel);
  } else {
    rightPanelEl?.classList.remove("hidden");
    rightPanelEl?.classList.remove("combat-collapsed");
  }
  updateCombatUtilityToggle();
}

function updateCombatCommandShellVisibility() {
  if (!combatCommandShellEl) return;
  const intentHidden = intentBannerEl?.classList.contains("hidden") ?? true;
  const quickHidden = document.getElementById("combatQuickBar")?.classList.contains("hidden") ?? true;
  combatCommandShellEl.classList.toggle("hidden", intentHidden && quickHidden);
}

function updateCombatUtilityToggle() {
  if (!combatUtilityToggleEl) return;
  const inCombat = document.body.dataset.view === "combat";
  const hasVisibleBlocks =
    !!rightPanelEl &&
    !rightPanelEl.classList.contains("hidden") &&
    Array.from(rightPanelEl.querySelectorAll(".stack-block")).some((el) => !el.classList.contains("hidden"));
  const show = inCombat && hasVisibleBlocks;
  combatUtilityToggleEl.classList.toggle("hidden", !show);
  combatUtilityToggleEl.classList.toggle("active", show && combatUtilityOpen);
  combatUtilityToggleEl.textContent = "B";
}

function updateCombatSetupToggle() {
  if (!combatSetupToggleEl || !combatSetupWrapEl) return;
  const inCombat = document.body.dataset.view === "combat";
  const hasSetupState = Boolean(lastEnemy) || awaitingEnemyPhase || Boolean(lastState?.room_type) || Boolean(lastState?.can_leave);
  if (!inCombat || !hasSetupState) {
    combatSetupOpen = false;
  }
  combatSetupWrapEl.classList.toggle("hidden", !inCombat || !hasSetupState || !combatSetupOpen);
  combatSetupToggleEl.classList.toggle("hidden", !inCombat || !hasSetupState);
  combatSetupToggleEl.classList.toggle("active", hasSetupState && combatSetupOpen);
  combatSetupToggleEl.textContent = "S";
  if (!inCombat || !hasSetupState || !combatSetupOpen) {
    advancedControls?.classList.add("hidden");
    if (btnAdvanced) btnAdvanced.textContent = "More";
  }
}

function updateCombatDetailsToggle() {
  if (!combatDetailsToggleEl || !combatDetailsWrapEl) return;
  const inCombat = document.body.dataset.view === "combat";
  const hasDetailsState = Boolean(lastEnemy) || awaitingEnemyPhase || Boolean(lastState?.room_type) || Boolean(lastState?.can_leave);
  if (!inCombat || !hasDetailsState) {
    combatDetailsOpen = false;
  }
  combatDetailsWrapEl.classList.toggle("hidden", !inCombat || !hasDetailsState || !combatDetailsOpen);
  combatDetailsToggleEl.classList.toggle("hidden", !inCombat || !hasDetailsState);
  combatDetailsToggleEl.classList.toggle("active", hasDetailsState && combatDetailsOpen);
  combatDetailsToggleEl.textContent = "I";
}

function updateActionDockVisibility() {
  if (!actionDockEl) return;
  const inCombat = document.body.dataset.view === "combat";
  const hasCombatState = Boolean(lastEnemy) || awaitingEnemyPhase || Boolean(lastState?.room_type) || Boolean(lastState?.can_leave);
  actionDockEl.classList.toggle("hidden", !inCombat || (!hasCombatState && !combatSetupOpen));
}

function updateArenaShellVisibility() {
  if (!arenaShellEl) return;
  const inCombat = document.body.dataset.view === "combat";
  const hasArenaState = Boolean(lastEnemy) || awaitingEnemyPhase || Boolean(lastState?.room_type) || Boolean(lastState?.can_leave);
  arenaShellEl.classList.toggle("hidden", !inCombat || !hasArenaState);
}

function updateCombatToplineVisibility() {
  if (!combatToplineEl) return;
  const showPhase = phaseBannerEl && !phaseBannerEl.classList.contains("hidden");
  const showProgress = runProgressEl && !runProgressEl.classList.contains("hidden");
  combatToplineEl.classList.toggle("hidden", !(showPhase || showProgress));
}

function updateCombatMiniNavState() {
  const hasRunState = Boolean(lastEnemy) || awaitingEnemyPhase || Boolean(lastState?.room_type) || Boolean(lastState?.can_leave);
  combatNavHomeEl?.classList.toggle("hidden", hasRunState);
  combatNavAreasEl?.classList.toggle("hidden", hasRunState);
  const visibleButtons = combatMiniTabs.filter((el) => !el.classList.contains("hidden"));
  const showNav = document.body.dataset.view === "combat" && hasRunState && visibleButtons.length > 0;
  document.getElementById("combatMiniNav")?.classList.toggle("hidden", !showNav);
}

function updateCombatEmptyStateVisibility() {
  if (!combatEmptyStateEl) return;
  const hasRunState = Boolean(lastEnemy) || awaitingEnemyPhase || Boolean(lastState?.room_type) || Boolean(lastState?.can_leave);
  const inCombat = document.body.dataset.view === "combat";
  if (!hasRunState) {
    const recommendedArea = getRecommendedCombatArea();
    if (combatEmptyHintEl) {
      combatEmptyHintEl.textContent = recommendedArea
        ? `${recommendedArea.name} is the best next route for your current power.`
        : "Choose an area and enter the dungeon.";
    }
    if (combatEmptyCtaEl) {
      if (recommendedArea) {
        combatEmptyCtaEl.textContent = `Start ${recommendedArea.name}`;
        combatEmptyCtaEl.dataset.riskStart = String(recommendedArea.risk);
      } else {
        combatEmptyCtaEl.textContent = "Open Routes";
        delete combatEmptyCtaEl.dataset.riskStart;
      }
    }
  }
  combatEmptyStateEl.classList.toggle("hidden", !inCombat || hasRunState);
}

function setDodgeUiState(kind = "idle", text = "Idle", detail = "Safe window waiting.") {
  if (dodgeStatus) {
    dodgeStatus.className = `dodge-chip ${kind}`;
    dodgeStatus.textContent = text;
  }
  if (dodgeWindowText) {
    dodgeWindowText.textContent = detail;
  }
  if (dodgeOverlayStatusEl) {
    dodgeOverlayStatusEl.className = `dodge-chip ${kind}`;
    dodgeOverlayStatusEl.textContent = text;
  }
  if (dodgeOverlayWindowTextEl) {
    dodgeOverlayWindowTextEl.textContent = detail;
  }
  updateDodgeCardVisibility();
  updateDodgeOverlayVisibility();
}

function updateDodgeTrackingReadout() {
  if (!dodgeInterval || !currentWindow) return;
  const left = Number(currentWindow.leftPct || 0);
  const right = left + Number(currentWindow.widthPct || 0);
  const center = left + ((right - left) / 2);
  const distance = Math.abs(markerPos - center);
  const centerTolerance = Math.max(2, (right - left) * 0.18);
  const nearTolerance = Math.max(4, (right - left) * 0.7);

  if (markerPos >= left && markerPos <= right) {
    const perfect = distance <= centerTolerance;
    setDodgeUiState(
      "locked",
      perfect ? "Perfect" : "Now",
      perfect ? "Press now." : "Hit now."
    );
    return;
  }

  if (distance <= nearTolerance) {
    setDodgeUiState(
      "ready",
      "Close",
      markerDir > 0 ? "Get ready." : "Coming back."
    );
    return;
  }

  setDodgeUiState(
    "danger",
    "Wait",
    "Hold."
  );
}
let lastRolledSkillName = "-";
let recentBattleRolls = [];


const ACTION_RULES = {
  basic: { cost: 0 },
  heavy: { cost: 35 },
  rupture: { cost: 30 },
  guard: { cost: 25 },
  focus: { cost: 20 },
};

const ACTION_META = {
  basic: { tone: "basic", short: "B", key: "1", label: "Strike", hint: "Free hit" },
  heavy: { tone: "heavy", short: "H", key: "2", label: "Cleave", hint: "Burst" },
  rupture: { tone: "rupture", short: "R", key: "3", label: "Rupture", hint: "Bleed" },
  guard: { tone: "guard", short: "G", key: "4", label: "Guard", hint: "Block" },
  focus: { tone: "focus", short: "F", key: "5", label: "Focus", hint: "Charge" },
};

function renderActionButtonContent(btn, meta, cooldown = 0, cost = 0) {
  if (!btn) return;
  const name = String(meta?.label || btn.dataset.action || "Skill");
  const hint = cooldown > 0
    ? `CD ${cooldown}`
    : (cost > 0 ? `${cost} STA` : (meta?.hint || "Ready"));
  btn.innerHTML = `
    <span class="action-btn-label">
      <span class="action-btn-name">${name}</span>
      <span class="action-btn-meta">${hint}</span>
    </span>
  `;
}

const telemetry = {
  turns_started: 0,
  actions_failed: 0,
  dodge_started: 0,
  dodge_clicked: 0,
  dodge_success: 0,
  dodge_fail: 0,
};

function _hasRunModifier(modId) {
  const mods = Array.isArray(lastStats?.run_modifiers) ? lastStats.run_modifiers : [];
  return mods.some((m) => String(m?.id || "") === modId);
}

function _actionCost(action) {
  let cost = Number(ACTION_RULES?.[action]?.cost || 0);
  if (action === "focus" && _hasRunModifier("arcane_suppression")) {
    cost += 10;
  }
  return cost;
}

function getRecommendedAction(cooldowns = {}) {
  if (awaitingEnemyPhase) return "";
  const stamina = Number(lastStats?.stamina || 0);
  const counter = String(lastBossIntent?.counter_action || "").toLowerCase();
  const available = ["basic", "heavy", "rupture", "guard", "focus"].filter((action) => {
    const cd = Number(cooldowns?.[action] || 0);
    return cd <= 0 && stamina >= _actionCost(action);
  });
  if (!available.length) return "";

  if (counter && available.includes(counter)) return counter;
  if (stamina < 20 && available.includes("basic")) return "basic";
  if (stamina < 30 && available.includes("guard")) return "guard";
  if (available.includes("heavy") && stamina >= _actionCost("heavy")) return "heavy";
  if (available.includes("rupture") && stamina >= _actionCost("rupture")) return "rupture";
  if (available.includes("basic")) return "basic";
  return available[0] || "";
}

async function emitTelemetry(eventName, payload = {}) {
  try {
    await fetch("/telemetry/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: eventName, payload }),
    });
  } catch {
    // Ignore telemetry failures; gameplay must never block.
  }
}

function updateActionButtons(cooldowns = {}) {
  const recommended = getRecommendedAction(cooldowns);
  actionButtons.forEach((btn) => {
    const action = btn.dataset.action || "";
    const meta = ACTION_META[action] || { short: action.slice(0, 1).toUpperCase(), key: "", label: action };
    const cd = Number(cooldowns?.[action] || 0);
    const baseLabel = String(meta.label || (action.charAt(0).toUpperCase() + action.slice(1)));
    const stamina = Number(lastStats?.stamina || 0);
    const cost = _actionCost(action);
    btn.dataset.cost = cost > 0 ? `${cost}` : "";
    btn.dataset.short = meta.short || "";
    btn.dataset.key = meta.key || "";
    renderActionButtonContent(btn, meta, cd, cost);

    let reason = "";
    if (awaitingEnemyPhase) {
      reason = "Enemy phase pending: complete dodge first.";
    } else if (cd > 0) {
      reason = `Cooldown: ${cd} turn(s) remaining.`;
    } else if (stamina < cost) {
      reason = `Need ${cost} stamina (${stamina} available).`;
    }

    btn.disabled = Boolean(reason);
    btn.classList.toggle("is-disabled-ui", Boolean(reason));
    btn.classList.toggle("is-recommended", Boolean(recommended) && action === recommended && !btn.disabled);
    btn.title = reason || `${baseLabel}: costs ${cost} stamina.`;

    if (btn.disabled && selectedAction === action) {
      selectedAction = "basic";
      const basicBtn = actionButtons.find((b) => (b.dataset.action || "") === "basic");
      actionButtons.forEach((b) => b.classList.remove("active"));
      basicBtn?.classList.add("active");
    }
  });
}

function setDebug(msg) { debug.textContent = msg; }

function formatUnixTs(ts) {
  const n = Number(ts || 0);
  if (n <= 0) return "never";
  try {
    const d = new Date(n * 1000);
    return d.toLocaleString();
  } catch {
    return "never";
  }
}

function formatTimeRemaining(targetTs) {
  const target = Number(targetTs || 0);
  if (target <= 0) return "unknown";
  const remaining = Math.max(0, (target * 1000) - Date.now());
  if (remaining <= 0) return "expired";
  return formatDurationCompact(Math.ceil(remaining / 1000));
}

function getNextTradeExpiry(rows = []) {
  if (!Array.isArray(rows) || !rows.length) return 0;
  return rows.reduce((minTs, row) => {
    const ts = Number(row?.expires_at || 0);
    if (ts <= 0) return minTs;
    if (!minTs) return ts;
    return Math.min(minTs, ts);
  }, 0);
}

function normalizeAccountName(name) {
  return String(name || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "")
    .slice(0, 32);
}

function renderAccountState(state = null) {
  const active = String(state?.active || "default");
  const accounts = Array.isArray(state?.accounts) ? state.accounts : [];
  accountStateCache = state || null;
  const total = accounts.length || 1;
  const row = accounts.find((a) => String(a?.id || "") === active);
  const savedAt = formatUnixTs(row?.saved_at || 0);

  if (accountSelectEl) {
    if (!accounts.length) {
      accountSelectEl.innerHTML = `<option value="${active}">${active}</option>`;
      accountSelectEl.value = active;
    } else {
      accountSelectEl.innerHTML = accounts
        .map((a) => {
          const id = String(a?.id || "");
          const saved = formatUnixTs(a?.saved_at || 0);
          return `<option value="${id}">${id} (${saved})</option>`;
        })
        .join("");
      accountSelectEl.value = active;
    }
  }

  if (accountActiveChipEl) accountActiveChipEl.textContent = `Active: ${active}`;
  if (accountCountChipEl) accountCountChipEl.textContent = `Accounts: ${total}`;
  if (accountSaveChipEl && !accountSaveChipEl.dataset.locked) {
    accountSaveChipEl.textContent = "Save: synced";
    accountSaveChipEl.className = "chip save-chip synced";
  }
  if (accountStatusEl) {
    accountStatusEl.textContent = `Loaded ${active} • ${total} account(s) • one save per account`;
  }
  if (accountSavedAtEl) {
    accountSavedAtEl.textContent = `Last saved: ${savedAt}`;
  }
}

function setAccountSaveState(label = "idle", tone = "idle", locked = false) {
  if (!accountSaveChipEl) return;
  accountSaveChipEl.textContent = `Save: ${label}`;
  accountSaveChipEl.className = `chip save-chip ${tone}`;
  if (locked) accountSaveChipEl.dataset.locked = "1";
  else delete accountSaveChipEl.dataset.locked;
}

function renderTradeAlert(state = null) {
  if (!tradeAlertChipEl) return;
  const summary = state?.summary || state || {};
  const inbox = Number(summary?.pending_inbox || 0);
  const outbox = Number(summary?.pending_outbox || 0);
  const inboxRows = Array.isArray(state?.inbox) ? state.inbox : [];
  const outboxRows = Array.isArray(state?.outbox) ? state.outbox : [];
  latestTradeInboxAt = inboxRows.reduce((maxTs, row) => {
    const ts = Number(row?.updated_at || row?.created_at || 0);
    return Math.max(maxTs, ts);
  }, 0);
  const seenAt = getSeenTradeInboxAt();
  const hasUnread = inbox > 0 && latestTradeInboxAt > seenAt;
  const visible = inbox > 0 || outbox > 0;
  const nextExpiry = getNextTradeExpiry(inbox > 0 ? inboxRows : outboxRows);
  const expirySuffix = nextExpiry > 0 ? ` • ${formatTimeRemaining(nextExpiry)}` : "";
  tradeAlertChipEl.textContent = inbox > 0 ? `Trades: ${inbox} inbox${expirySuffix}` : `Trades: ${outbox} outbox${expirySuffix}`;
  tradeAlertChipEl.className = `chip trade-alert-chip ${inbox > 0 ? "has-inbox" : "has-outbox"}${hasUnread ? " unread" : ""}${visible ? "" : " hidden"}`;
}

async function refreshAccountState() {
  const state = await api("/account/state");
  if (state?.error) {
    if (accountStatusEl) accountStatusEl.textContent = `Account error: ${state.error}`;
    return null;
  }
  renderAccountState(state);
  return state;
}

async function useAccount(name, create = true) {
  const account = normalizeAccountName(name);
  if (!account) {
    setDebug("Account name required.");
    return;
  }

  const res = await api("/account/use", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account, create }),
  });
  if (res?.error) {
    setDebug(`Account switch failed: ${res.error}`);
    await refreshAccountState();
    return;
  }

  renderAccountState(res?.state || null);
  lastState = null;
  lastEnemy = null;
  awaitingEnemyPhase = false;
  lastRunResult = null;
  idleStateCache = null;
  shownOfflineSummaryAt = 0;
  lastRolledSkillName = "-";
  recentBattleRolls = [];
  offlineModalEl?.classList.add("hidden");
  hideGuideModal(false);

  setDebug(`Using account: ${res?.account || account}`);
  renderRollHistory();
  await refreshStats();
  await loadInventory();
  await renderActiveTab();
  const dungeonState = await api("/dungeon/state");
  renderCombatLogFromResponse(dungeonState);
  renderEnemyFromState(dungeonState);
  syncTurnFlowState({ awaiting_enemy_phase: false });
}

async function saveActiveAccount(silent = false) {
  setAccountSaveState("saving", "saving", true);
  const res = await api("/account/save", { method: "POST" });
  if (res?.error) {
    setAccountSaveState("error", "error");
    if (!silent) setDebug(`Save failed: ${res.error}`);
    return false;
  }
  renderAccountState(res?.state || accountStateCache);
  setAccountSaveState("synced", "synced");
  if (!silent) setDebug(`Saved account: ${res?.account || "default"}`);
  return true;
}

async function syncProgressSave(label = "synced") {
  const ok = await saveActiveAccount(true);
  if (ok) setAccountSaveState(label, "synced");
  return ok;
}

function syncTurnFlowState(data = null) {
  if (data && typeof data.awaiting_enemy_phase === "boolean") {
    awaitingEnemyPhase = data.awaiting_enemy_phase;
  } else if (data?.state && typeof data.state.awaiting_enemy_attack === "boolean") {
    awaitingEnemyPhase = data.state.awaiting_enemy_attack;
  }
  if (!awaitingEnemyPhase) {
    dodgePhasePrimed = false;
  }

  if (btnTurn) {
    btnTurn.textContent = awaitingEnemyPhase ? "Enemy Pending" : "Attack";
    btnTurn.disabled = awaitingEnemyPhase;
    btnTurn.title = awaitingEnemyPhase ? "Finish dodge to resolve enemy phase." : "Execute selected action.";
  }
  if (btnReroll) {
    const rerolls = Number(lastStats?.battle?.rerolls || 0);
    btnReroll.textContent = awaitingEnemyPhase ? "Reroll Pending" : `Reroll (${rerolls})`;
    btnReroll.disabled = awaitingEnemyPhase || rerolls <= 0;
    btnReroll.title = rerolls > 0
      ? "Consume 1 reroll and roll a different skill this turn."
      : "No rerolls queued.";
  }
  if (btnDodgeAction) {
    btnDodgeAction.classList.toggle("hidden", !awaitingEnemyPhase);
    btnDodgeAction.disabled = !awaitingEnemyPhase;
    btnDodgeAction.textContent = "Dodge";
    btnDodgeAction.title = awaitingEnemyPhase
      ? (dodgeInterval
          ? "Press Space or click now to dodge."
          : "Press Space or click to begin dodge window.")
      : "No enemy action is pending.";
  }
  if (btnLeave) {
    const canLeave = Boolean(lastState?.can_leave || data?.can_leave || data?.state?.can_leave);
    btnLeave.disabled = !canLeave || awaitingEnemyPhase;
    btnLeave.title = canLeave
      ? (awaitingEnemyPhase ? "Finish enemy phase first." : "Leave now to lock rewards and finish the run.")
      : "Defeat the boss to unlock exit.";
  }

  if (phaseBannerEl) {
    const canLeave = Boolean(lastState?.can_leave || data?.can_leave || data?.state?.can_leave);
    const phaseText = canLeave
      ? "CLEAR"
      : (awaitingEnemyPhase ? "DODGE" : "ACT");
    phaseBannerEl.textContent = phaseText;
    phaseBannerEl.dataset.phase = String(phaseText || "").toLowerCase();
    phaseBannerEl.classList.remove("hidden");
    phaseBannerEl.parentElement?.classList.remove("phase-hidden");
  }

  if (turnSummaryStripEl) {
    const canLeave = Boolean(lastState?.can_leave || data?.can_leave || data?.state?.can_leave);
    if (canLeave) {
      setTurnSummaryStrip("Boss defeated. Press Leave Dungeon to lock rewards and finish the run.", true);
    }
  }

  updateActionButtons(lastStats?.action_cooldowns || {});
  updateActionDockVisibility();
  updateArenaShellVisibility();
  updateCombatToplineVisibility();
  updateCombatMiniNavState();
  updateCombatEmptyStateVisibility();
  updateDodgeOverlayVisibility();
  if (awaitingEnemyPhase && !dodgePhasePrimed) {
    dodgePhasePrimed = true;
    startDodge();
  }
  renderHud();
}

function renderTopRunContext() {
  const depthText = `Depth: ${lastState?.depth ?? lastStats?.depth ?? "-"}`;
  const roomIndex = Number(lastState?.room_index ?? -1);
  const roomCount = Number(lastState?.room_count ?? 0);
  const roomType = String(lastState?.room_type || "-").toUpperCase();
  const hasRunState = Boolean(lastState) && ((roomCount > 0 && roomIndex >= 0) || Number(lastState?.depth || 0) > 0);
  const roomText = roomCount > 0 && roomIndex >= 0
    ? `Room: ${roomIndex + 1}/${roomCount} ${roomType}`
    : `Room: -`;
  const goldText = `Gold: ${lastStats?.gold ?? "-"}`;
  const essenceText = `Essence: ${lastStats?.resources?.rune_essence ?? "-"}`;
  const chestText = `Chests: ${lastStats?.resources?.arcane_chest ?? 0}`;
  if (chipDepthEl) {
    chipDepthEl.textContent = depthText;
  }
  if (chipRoomEl) {
    chipRoomEl.textContent = roomText;
  }
  if (chipGoldEl) {
    chipGoldEl.textContent = goldText;
  }
  if (chipEssenceEl) {
    chipEssenceEl.textContent = essenceText;
  }
  if (chipChestEl) {
    chipChestEl.textContent = chestText;
  }
  if (combatRunContextEl) {
    const depthCompact = `D${lastState?.depth ?? lastStats?.depth ?? "-"}`;
    const roomCompact = roomCount > 0 && roomIndex >= 0
      ? `R${roomIndex + 1}/${roomCount}`
      : "R-";
    const goldCompact = `G${lastStats?.gold ?? "-"}`;
    const essenceCompact = `E${lastStats?.resources?.rune_essence ?? "-"}`;
    const chestCompact = `C${lastStats?.resources?.arcane_chest ?? 0}`;
    combatRunContextEl.classList.toggle("hidden", !hasRunState);
    combatRunContextEl.innerHTML = `
      <span class="chip">${depthCompact}</span>
      <span class="chip">${roomCompact}</span>
      <span class="chip">${goldCompact}</span>
      <span class="chip">${essenceCompact}</span>
      <span class="chip">${chestCompact}</span>
    `;
  }
  renderRunProgress();
  renderRunRules();
  renderRunGains();
  renderExitReady();
}

function renderRunProgress() {
  if (!runProgressEl) return;
  const roomIndex = Number(lastState?.room_index ?? -1);
  const roomCount = Number(lastState?.room_count ?? 0);
  const roomType = String(lastState?.room_type || "").toUpperCase();
  const canLeave = Boolean(lastState?.can_leave);

  if (roomCount <= 0 || roomIndex < 0) {
    runProgressEl.classList.add("hidden");
    runProgressEl.innerHTML = "";
    updateCombatToplineVisibility();
    return;
  }

  const completed = Math.min(roomCount, roomIndex + (canLeave ? 1 : 0));
  const pct = Math.max(0, Math.min(100, (completed / Math.max(1, roomCount)) * 100));
  const roomsLeft = Math.max(0, roomCount - completed);
  const bossText = canLeave
    ? "Exit open"
    : `${roomsLeft} left`;

  runProgressEl.classList.remove("hidden");
  runProgressEl.innerHTML = `
    <div class="run-progress-head">
      <b>${roomIndex + 1}/${roomCount}${roomType ? ` ${roomType}` : ""}</b>
      <span class="small">${bossText}</span>
    </div>
    <div class="run-progress-bar">
      <span style="width:${pct.toFixed(1)}%"></span>
    </div>
  `;
  updateCombatToplineVisibility();
}

function renderRunRules() {
  if (!runRulesEl) return;
  const mods = Array.isArray(lastStats?.run_modifiers) ? lastStats.run_modifiers : [];
  const affix = lastState?.current_affix || null;

  const parts = [];
  if (affix?.name) {
    parts.push(`
      <div class="rule-pill affix">
        <b>Room Affix</b>
        <span>${affix.name}</span>
      </div>
    `);
  }
  mods.forEach((mod) => {
    parts.push(`
      <div class="rule-pill">
        <b>${mod?.name || "Modifier"}</b>
        <span>${mod?.desc || "No description."}</span>
      </div>
    `);
  });

  if (!parts.length) {
    runRulesEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }
  runRulesEl.innerHTML = `<div class="run-rules-row">${parts.join("")}</div>`;
}

function renderRunGains() {
  if (!runGainsEl) return;
  const gains = lastState?.run_gains || {};
  const preview = lastState?.boss_preview || {};
  const cadence = lastState?.run_cadence || {};
  const gold = Number(gains?.gold || 0);
  const essence = Number(gains?.rune_essence || 0);
  const chest = Number(gains?.arcane_chest || 0);
  const relic = Number(gains?.rune_relic || 0);
  const pityChest = Boolean(preview?.chest_pity_live);
  const pityRelic = Boolean(preview?.relic_pity_live);
  const bossGoldFloor = Number(preview?.gold_floor || 0);
  const bossEssenceFloor = Number(preview?.essence_floor || 0);
  const chestFloor = Number(preview?.chest_floor || 0);
  const relicFloor = Number(preview?.relic_floor || 0);
  const projectedGold = Number(preview?.projected_gold_if_clear || 0);
  const projectedEssence = Number(preview?.projected_essence_if_clear || 0);
  const rewardOffset = Number.isFinite(Number(cadence?.next_reward_offset)) ? Number(cadence.next_reward_offset) : null;
  const recoveryOffset = Number.isFinite(Number(cadence?.next_recovery_offset)) ? Number(cadence.next_recovery_offset) : null;
  if (
    gold <= 0 &&
    essence <= 0 &&
    chest <= 0 &&
    relic <= 0 &&
    !bossGoldFloor &&
    !bossEssenceFloor &&
    !projectedGold &&
    !projectedEssence
  ) {
    runGainsEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }
  runGainsEl.innerHTML = `
    <div class="run-gains-row">
      <div class="gain-pill"><b>Gold</b><span>+${gold}</span></div>
      <div class="gain-pill"><b>Essence</b><span>+${essence}</span></div>
      <div class="gain-pill"><b>Chests</b><span>+${chest}</span></div>
      <div class="gain-pill"><b>Relics</b><span>+${relic}</span></div>
    </div>
    <div class="run-gains-row run-gains-preview">
      <div class="gain-pill preview"><b>Boss Floor</b><span>${bossGoldFloor > 0 ? `${bossGoldFloor}g / ${bossEssenceFloor} ess` : "--"}</span></div>
      <div class="gain-pill preview"><b>Pity Floor</b><span>${chestFloor > 0 || relicFloor > 0 ? `${chestFloor > 0 ? `${chestFloor} chest` : "0 chest"} / ${relicFloor > 0 ? `${relicFloor} relic` : "0 relic"}` : "Spent"}</span></div>
      <div class="gain-pill preview"><b>Clear Total</b><span>${projectedGold > 0 || projectedEssence > 0 ? `${projectedGold}g / ${projectedEssence} ess` : "--"}</span></div>
      <div class="gain-pill preview"><b>Route</b><span>${rewardOffset !== null ? `Reward in ${rewardOffset} room(s)` : recoveryOffset !== null ? `Recovery in ${recoveryOffset} room(s)` : pityChest || pityRelic ? "Boss pity live" : "--"}</span></div>
    </div>
  `;
}

function renderExitReady() {
  if (!exitReadyEl) return;
  const canLeave = Boolean(lastState?.can_leave);
  const gains = lastState?.run_gains || {};
  const rewardBits = [];
  if (Number(gains?.gold || 0) > 0) rewardBits.push(`+${Number(gains.gold)} gold`);
  if (Number(gains?.rune_essence || 0) > 0) rewardBits.push(`+${Number(gains.rune_essence)} essence`);
  if (Number(gains?.arcane_chest || 0) > 0) rewardBits.push(`+${Number(gains.arcane_chest)} chest`);
  if (Number(gains?.rune_relic || 0) > 0) rewardBits.push(`+${Number(gains.rune_relic)} relic`);

  if (!canLeave) {
    const roomType = String(lastState?.room_type || "").toUpperCase();
    exitReadyEl.innerHTML = `
      <div class="exit-ready-card locked">
        <b>Run Status</b>
        <span>${roomType ? `${roomType} active. Defeat the boss to unlock exit.` : "--"}</span>
      </div>
    `;
    return;
  }

  exitReadyEl.innerHTML = `
    <div class="exit-ready-card ready">
      <b>Boss Defeated</b>
      <span>Leave dungeon now to finalize the run and lock rewards.</span>
      <i>${rewardBits.length ? rewardBits.join(" | ") : "Rewards secured."}</i>
    </div>
  `;
}

function renderRoomBrief() {
  if (!roomBriefEl) return;
  const roomTypeRaw = String(lastState?.room_type || "").toLowerCase();
  if (!roomTypeRaw) {
    roomBriefEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }

  const affix = lastState?.current_affix || null;
  const roomMap = {
    boss: {
      label: "Boss Room",
      posture: "High reward, highest pressure. Clear this room to unlock exit.",
      payout: "Best chest/relic payout. Expect the hardest dodge and counter windows.",
    },
    treasure: {
      label: "Treasure Room",
      posture: "Low combat pressure. Convert room tempo into loot.",
      payout: "Gold, essence, and chest spikes land here.",
    },
    rest: {
      label: "Recovery Room",
      posture: "Reset HP and stamina before the next threat ramp.",
      payout: "Best place to stabilize for the next fight.",
    },
    shrine: {
      label: "Shrine Room",
      posture: "Utility room with a blessing pivot.",
      payout: "Can restore HP, stamina, or relic value depending on blessing.",
    },
    trap: {
      label: "Trap Room",
      posture: "Punishes mistakes. Enter with HP buffer.",
      payout: "Usually no direct payout; the win condition is avoiding loss.",
    },
    event: {
      label: "Event Room",
      posture: "Variable outcome room. Expect swingy utility.",
      payout: "Can produce stamina, tempo, or side-resource value.",
    },
    combat: {
      label: "Combat Room",
      posture: "Standard combat pacing. Use it to build clean momentum.",
      payout: "Reliable gold/xp pacing with modest drops.",
    },
  };
  const meta = roomMap[roomTypeRaw] || {
    label: `${roomTypeRaw.toUpperCase()} Room`,
    posture: "Route data pending.",
    payout: "--",
  };
  const affixName = affix?.name || "None";
  const affixDesc = affix?.desc || "No active affix.";
  const bossPreview = lastState?.boss_preview || {};
  const cadence = lastState?.run_cadence || {};
  const pressure = lastState?.room_pressure || {};
  const bossTemper = lastState?.boss_temper || {};
  const pressureLabel = String(pressure?.label || "Low");
  const pressureIntensity = Math.round(Number(pressure?.intensity || 0) * 100);
  const bossForecast = roomTypeRaw === "boss"
    ? `Boss floor ${Number(bossPreview?.gold_floor || 0)}g / ${Number(bossPreview?.essence_floor || 0)} essence | clear total ${Number(bossPreview?.projected_gold_if_clear || 0)}g / ${Number(bossPreview?.projected_essence_if_clear || 0)} essence${bossPreview?.chest_pity_live ? " | chest pity live" : ""}${bossPreview?.relic_pity_live ? " | relic pity live" : ""}`
    : meta.payout;
  const routeCue = roomTypeRaw === "boss"
    ? `Final combat room. ${String(bossTemper?.reward_heat ?? "") !== "" ? `Boss mood ${String((bossTemper?.finisher_window ? "desperate" : (bossTemper?.reward_heat >= 0.66 ? "predatory" : bossTemper?.reward_heat >= 0.33 ? "hunting" : "calm"))).toUpperCase()}.` : Number(cadence?.remaining_combat_rooms || 0) > 0 ? `${Number(cadence.remaining_combat_rooms)} combat room(s) still counted in preview.` : "Beat the boss to unlock exit."}`
    : Number.isFinite(Number(cadence?.next_boss_offset))
      ? `Boss in ${Number(cadence.next_boss_offset)} room(s).`
      : Number.isFinite(Number(cadence?.next_recovery_offset))
        ? `Recovery in ${Number(cadence.next_recovery_offset)} room(s).`
        : "No major spike in this route slice.";
  const danger = roomTypeRaw === "boss" || roomTypeRaw === "trap"
    ? "high"
    : (roomTypeRaw === "combat" || roomTypeRaw === "event" ? "mid" : "low");

  roomBriefEl.innerHTML = `
    <div class="room-brief-row">
      <div class="room-brief-card ${danger}">
        <b>Current Room</b>
        <span>${meta.label}</span>
      </div>
      <div class="room-brief-card">
        <b>Posture</b>
        <span>${meta.posture}</span>
      </div>
      <div class="room-brief-card">
        <b>Expected Payout</b>
        <span>${bossForecast}</span>
      </div>
      <div class="room-brief-card">
        <b>Route Cue</b>
        <span>${routeCue}</span>
      </div>
      <div class="room-brief-card ${pressureIntensity >= 24 ? "high" : pressureIntensity >= 12 ? "mid" : "low"}">
        <b>Pressure</b>
        <span>${pressureLabel} ${pressureIntensity > 0 ? `| +${pressureIntensity}% room threat` : "| Stable"}</span>
      </div>
      ${roomTypeRaw === "boss"
        ? `<div class="room-brief-card ${Number(bossTemper?.reward_heat || 0) >= 0.66 || bossTemper?.finisher_window ? "high" : Number(bossTemper?.reward_heat || 0) >= 0.33 ? "mid" : "low"}">
            <b>Boss Temper</b>
            <span>${bossTemper?.finisher_window ? "Desperate" : Number(bossTemper?.reward_heat || 0) >= 0.66 ? "Predatory" : Number(bossTemper?.reward_heat || 0) >= 0.33 ? "Hunting" : "Calm"}${Number(bossTemper?.reward_heat || 0) > 0 ? ` | heat ${Math.round(Number(bossTemper.reward_heat) * 100)}%` : ""}</span>
          </div>`
        : ""}
      <div class="room-brief-card ${affix?.name ? "affix-live" : ""}">
        <b>Affix</b>
        <span>${affixName}${affix?.desc ? ` | ${affixDesc}` : ""}</span>
      </div>
    </div>
  `;
}

function renderCombatPressure() {
  if (!combatPressureEl) return;
  const gains = lastState?.run_gains || {};
  const rows = Array.isArray(lastState?.room_preview) ? lastState.room_preview : [];
  const cadence = lastState?.run_cadence || {};
  const pressure = lastState?.room_pressure || {};
  const bossTemper = lastState?.boss_temper || {};
  const nextBoss = Number.isFinite(Number(cadence?.next_boss_offset)) ? Number(cadence.next_boss_offset) : null;
  const nextLoot = Number.isFinite(Number(cadence?.next_reward_offset)) ? Number(cadence.next_reward_offset) : null;
  const nextRecovery = Number.isFinite(Number(cadence?.next_recovery_offset)) ? Number(cadence.next_recovery_offset) : null;
  const remainingCombat = Number(cadence?.remaining_combat_rooms || 0);
  const remainingSupport = Number(cadence?.remaining_support_rooms || 0);
  const gold = Number(gains?.gold || 0);
  const essence = Number(gains?.rune_essence || 0);
  const chest = Number(gains?.arcane_chest || 0);
  const relic = Number(gains?.rune_relic || 0);
  const rewardScore = gold + (essence * 0.6) + (chest * 120) + (relic * 240);
  const threat = String(intentThreatEl?.textContent || "SAFE").toUpperCase();
  const enemyTier = String(lastEnemy?.tier || "").toLowerCase();
  const roomPressureIntensity = Number(pressure?.intensity || 0);
  const highPressure = threat === "HIGH" || enemyTier === "boss" || roomPressureIntensity >= 0.24;
  const mediumPressure = !highPressure && (threat === "MED" || enemyTier === "elite" || roomPressureIntensity >= 0.12);
  const posture = highPressure ? "stabilize" : (mediumPressure ? "steady" : "push");
  const postureLabel = posture === "stabilize" ? "Stabilize" : (posture === "steady" ? "Steady" : "Push");
  const postureReason = highPressure
    ? `Respect the next hit. ${roomPressureIntensity >= 0.24 ? "Room pressure is spiking." : "Guard, dodge cleanly, or reroll for a safer line."}`
    : mediumPressure
      ? `You can press damage, but watch stamina and cooldown drift.${roomPressureIntensity >= 0.12 ? " Pressure is building." : ""}`
      : "Low pressure window. Push damage and speed the room clear.";
  const rewardText = rewardScore <= 0
    ? `<span class="small muted">--</span>`
    : `Run value ${Math.round(rewardScore)} | +${gold}g, +${essence} essence${chest > 0 ? `, +${chest} chest` : ""}${relic > 0 ? `, +${relic} relic` : ""}`;
  const pathText = nextBoss !== null
    ? `Boss in ${nextBoss} room(s) | ${remainingCombat} combat / ${remainingSupport} support ahead`
    : (lastState?.can_leave ? "Boss defeated | exit ready" : remainingCombat > 0 ? `${remainingCombat} combat room(s) still in preview` : `<span class="small muted">--</span>`);
  const lootText = nextLoot !== null
    ? `Reward in ${nextLoot} room(s)${nextRecovery !== null ? ` | recovery in ${nextRecovery}` : ""}`
    : nextRecovery !== null
      ? `Recovery in ${nextRecovery} room(s)`
      : (chest > 0 || relic > 0 ? "Reward spike already hit this run" : `<span class="small muted">--</span>`);
  const pressureText = roomPressureIntensity > 0
    ? `${String(pressure?.label || "Low")} | +${Math.round(roomPressureIntensity * 100)}% enemy pace${Number(pressure?.enemy_phase_bonus || 0) > 0 ? ` | +${Math.round(Number(pressure.enemy_phase_bonus) * 100)}% enemy turn` : ""}`
    : `<span class="small muted">--</span>`;
  const bossTemperText = enemyTier === "boss"
    ? `${bossTemper?.finisher_window ? "Desperate finisher" : Number(bossTemper?.reward_heat || 0) >= 0.66 ? "Predatory" : Number(bossTemper?.reward_heat || 0) >= 0.33 ? "Hunting" : "Calm"}${Number(bossTemper?.reward_heat || 0) > 0 ? ` | heat ${Math.round(Number(bossTemper.reward_heat) * 100)}%` : ""}`
    : `<span class="small muted">--</span>`;

  combatPressureEl.innerHTML = `
    <div class="combat-pressure-row">
      <div class="pressure-pill ${posture}">
        <b>${postureLabel}</b>
        <span>${postureReason}</span>
      </div>
      <div class="pressure-pill reward">
        <b>Run Value</b>
        <span>${rewardText}</span>
      </div>
      <div class="pressure-pill path">
        <b>Path</b>
        <span>${pathText}</span>
      </div>
      <div class="pressure-pill loot">
        <b>Reward Route</b>
        <span>${lootText}</span>
      </div>
      <div class="pressure-pill ${highPressure ? "stabilize" : mediumPressure ? "steady" : "push"}">
        <b>Room Pressure</b>
        <span>${pressureText}</span>
      </div>
      ${enemyTier === "boss"
        ? `<div class="pressure-pill ${bossTemper?.finisher_window || Number(bossTemper?.reward_heat || 0) >= 0.66 ? "stabilize" : Number(bossTemper?.reward_heat || 0) >= 0.33 ? "steady" : "push"}">
            <b>Boss Tempo</b>
            <span>${bossTemperText}</span>
          </div>`
        : ""}
    </div>
  `;
}

function renderVictoryForecast() {
  if (!victoryForecastEl) return;
  if (!lastEnemy || !lastStats) {
    victoryForecastEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }

  const enemyHp = Math.max(0, Number(lastEnemy?.hp || 0));
  const playerHp = Math.max(0, Number(lastStats?.hp || 0));
  const playerAtk = Math.max(1, Number(lastStats?.attack || 1));
  const playerDef = Math.max(0, Number(lastStats?.defense || 0));
  const enemyAtk = Math.max(1, Number(lastEnemy?.attack || 1));
  const action = String(selectedAction || "basic");
  const actionCost = _actionCost(action);
  const actionCfg = ACTION_RULES?.[action] || {};
  const mult = Number(actionCfg?.damage_mult || 1);
  const projectedDamage = Math.max(1, Math.round(playerAtk * mult));
  const hitsToKill = enemyHp > 0 ? Math.max(1, Math.ceil(enemyHp / projectedDamage)) : 0;
  const incoming = Math.max(1, Math.round(enemyAtk - (playerDef * 0.35)));
  const hitsToDie = playerHp > 0 ? Math.max(1, Math.ceil(playerHp / incoming)) : 0;
  const stamina = Number(lastStats?.stamina || 0);
  const roomType = String(lastState?.room_type || "").toLowerCase();
  const bossPreview = lastState?.boss_preview || {};
  const recommendation = hitsToKill <= hitsToDie ? "Favored" : (hitsToKill <= (hitsToDie + 1) ? "Tight" : "Danger");
  const tone = recommendation === "Favored" ? "safe" : (recommendation === "Tight" ? "mid" : "risk");
  const summary = recommendation === "Favored"
    ? "You can usually race this enemy if dodge stays clean."
    : (recommendation === "Tight" ? "Fight is close. Rerolling or guarding may be higher EV." : "You lose the trade on current line. Stabilize or change action.");

  victoryForecastEl.innerHTML = `
    <div class="victory-forecast-row">
      <div class="victory-pill ${tone}">
        <b>Forecast</b>
        <span>${recommendation}</span>
      </div>
      <div class="victory-pill">
        <b>Your Line</b>
        <span>${action.toUpperCase()} | est ${projectedDamage} dmg | cost ${actionCost}</span>
      </div>
      <div class="victory-pill">
        <b>Finish Clock</b>
        <span>${hitsToKill} hit(s) to kill</span>
      </div>
      <div class="victory-pill">
        <b>Danger Clock</b>
        <span>${hitsToDie} enemy hit(s) to die | est ${incoming} dmg in</span>
      </div>
      <div class="victory-pill ${stamina >= actionCost ? "safe" : "risk"}">
        <b>Stamina Gate</b>
        <span>${stamina >= actionCost ? "Action funded" : `Need ${actionCost - stamina} more stamina`}</span>
      </div>
      <div class="victory-pill">
        <b>Read</b>
        <span>${summary}</span>
      </div>
      ${roomType === "boss" ? `
      <div class="victory-pill ${bossPreview?.relic_pity_live || bossPreview?.chest_pity_live ? "safe" : "mid"}">
        <b>Boss Cache</b>
        <span>${Number(bossPreview?.gold_floor || 0)}g / ${Number(bossPreview?.essence_floor || 0)} essence${bossPreview?.chest_pity_live ? ` | chest pity` : ""}${bossPreview?.relic_pity_live ? ` | relic pity` : ""}</span>
      </div>
      ` : ``}
    </div>
  `;
}

function renderHud() {
  if (arenaGridEl) {
    const phase = lastState?.can_leave
      ? "CLEAR"
      : (awaitingEnemyPhase ? "DODGE" : "ACT");
    arenaGridEl.dataset.phase = phase;
    arenaGridEl.classList.remove("phase-act", "phase-dodge", "phase-clear");
    arenaGridEl.classList.add(`phase-${String(phase || "act").toLowerCase()}`);
  }
  if (playerPanelTitleEl) {
    playerPanelTitleEl.textContent = "You";
  }
  if (enemyPanelTitleEl) {
    enemyPanelTitleEl.textContent = lastState?.can_leave ? "Clear" : "Enemy";
  }
  if (hudPhaseEl) {
    hudPhaseEl.textContent = awaitingEnemyPhase ? "Dodge / Enemy Turn" : "Player Turn";
  }

  if (hudPlayerEl) {
    if (!lastStats) {
      hudPlayerEl.textContent = "Player HUD";
    } else {
      hudPlayerEl.innerHTML = `
        <b>Player</b> | HP ${lastStats.hp}/${lastStats.max_hp} | STA ${lastStats.stamina}/${lastStats.max_stamina}<br>
        ATK ${lastStats.attack} | DEF ${lastStats.defense}
      `;
    }
  }

  if (hudEnemyEl) {
    if (!lastEnemy) {
      hudEnemyEl.textContent = "No active enemy";
    } else {
      hudEnemyEl.innerHTML = `
        <b>${lastEnemy.name}</b> (${lastEnemy.tier}) | HP ${lastEnemy.hp}<br>
        ATK ${lastEnemy.attack} | Archetype ${lastEnemy.archetype || "brute"}
      `;
    }
  }
  renderRoomBrief();
  renderCombatPressure();
  renderVictoryForecast();
  renderCombatQuickBar();
}

function renderCombatQuickBar() {
  const battle = lastStats?.battle || {};
  let visibleCount = 0;
  if (quickStaminaEl) {
    const sta = Number(lastStats?.stamina || 0);
    const maxSta = Number(lastStats?.max_stamina || 0);
    quickStaminaEl.textContent = maxSta > 0 ? `STA ${sta}/${maxSta}` : "";
    quickStaminaEl.classList.toggle("hidden", maxSta <= 0);
    if (maxSta > 0) visibleCount += 1;
  }
  if (quickEnemyEl) {
    if (lastEnemy && Number.isFinite(Number(lastEnemy?.hp))) {
      quickEnemyEl.textContent = `${String(lastEnemy.name || "Enemy").slice(0, 14)} ${Number(lastEnemy.hp)} HP`;
      quickEnemyEl.classList.remove("hidden");
      visibleCount += 1;
    } else if (lastState?.can_leave) {
      quickEnemyEl.textContent = "Clear";
      quickEnemyEl.classList.remove("hidden");
      visibleCount += 1;
    } else {
      quickEnemyEl.textContent = "";
      quickEnemyEl.classList.add("hidden");
    }
  }
  if (quickRollEl) {
    const actionLabel = String(selectedAction || "basic").toUpperCase();
    quickRollEl.textContent = awaitingEnemyPhase
      ? `Resolve ${lastRolledSkillName || actionLabel}`
      : `${actionLabel} ready`;
    quickRollEl.classList.remove("hidden");
    visibleCount += 1;
  }
  if (quickRerollsEl) {
    const rr = Number(battle?.rerolls || 0);
    const rrCap = Number(battle?.reroll_cap || 0);
    quickRerollsEl.textContent = rrCap > 0 ? `RR ${rr}/${rrCap}` : "";
    quickRerollsEl.classList.toggle("hidden", rrCap <= 0);
    if (rrCap > 0) visibleCount += 1;
  }
  if (quickCurseEl) {
    const charge = Number(battle?.curse_charge || 0);
    quickCurseEl.textContent = `CURSE ${charge.toFixed(2)}`;
    quickCurseEl.classList.toggle("hidden", charge <= 0 && !awaitingEnemyPhase);
    quickCurseEl.classList.toggle("risk", charge >= 1);
    if (!(charge <= 0 && !awaitingEnemyPhase)) visibleCount += 1;
  }
  const quickBarEl = document.getElementById("combatQuickBar");
  quickBarEl?.classList.toggle("hidden", visibleCount <= 1);
  updateCombatCommandShellVisibility();
  renderCombatDeck();
  renderRollFocus();
  renderTurnExplain();
  renderActionBrief();
  renderCombatReadout();
  renderPathPreview();
  renderRoomResolution();
}

function getCurrentRollInsight() {
  const battle = lastStats?.battle || {};
  const skills = Array.isArray(battle.skills) ? battle.skills : [];
  const currentRoll = normalizeText(lastRolledSkillName || "");
  if (!currentRoll) return null;
  const index = skills.findIndex((row) => normalizeText(String(row?.name || row?.id || "")) === currentRoll);
  if (index < 0) return null;
  const row = skills[index] || {};
  const baseWeight = Number(row?.base_weight || 0);
  const effectiveWeight = Number(row?.effective_weight || 0);
  const rollChance = Number(row?.roll_chance || 0) * 100;
  const reasons = [];
  if (index === 0 && effectiveWeight > baseWeight + 0.01) reasons.push("slot 1 bias");
  if (String(row?.kind || "") === "cursed" && effectiveWeight < baseWeight - 0.01) reasons.push("curse tuning");
  if (effectiveWeight > baseWeight + 0.01 && index !== 0) reasons.push("mastery weight");
  return {
    slot: index + 1,
    kind: String(row?.kind || "normal"),
    rollChance,
    baseWeight,
    effectiveWeight,
    reasons,
  };
}

function renderRollFocus() {
  if (!rollFocusEl) return;
  const info = lastRollFocus || null;
  if (!info) {
    rollFocusEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }

  const perkText = Array.isArray(info.masteryPerks) && info.masteryPerks.length
    ? info.masteryPerks.join(", ")
    : "—";
  const counterText = info.counterNeeded
    ? (info.counterSuccess ? `Counter hit: ${info.counterNeeded}` : `Counter miss: needed ${info.counterNeeded}`)
    : "—";
  const tone = info.kind === "cursed" ? "cursed" : (info.counterSuccess ? "success" : "");
  const rollInsight = getCurrentRollInsight();
  const biasText = rollInsight
    ? `Slot ${rollInsight.slot} • ${rollInsight.rollChance.toFixed(1)}% • w ${rollInsight.effectiveWeight.toFixed(2)}/${rollInsight.baseWeight.toFixed(2)}`
    : "—";
  const biasReasonText = rollInsight?.reasons?.length ? rollInsight.reasons.join(", ") : "base odds";

  rollFocusEl.innerHTML = `
    <div class="roll-focus-row">
      <div class="roll-focus-card ${tone}">
        <b>Current Roll</b>
        <span>${info.name}</span>
      </div>
      <div class="roll-focus-card">
        <b>Type</b>
        <span>${info.kind}${info.rerolled ? " | rerolled" : ""}</span>
      </div>
      <div class="roll-focus-card">
        <b>Mastery</b>
        <span>Lv ${info.masteryLevel}${info.masteryGain > 0 ? ` (+${info.masteryGain})` : ""}</span>
      </div>
      <div class="roll-focus-card">
        <b>Perks</b>
        <span>${perkText}</span>
      </div>
      <div class="roll-focus-card ${info.counterSuccess ? "success" : ""}">
        <b>Counter</b>
        <span>${counterText}</span>
      </div>
      <div class="roll-focus-card">
        <b>Bias</b>
        <span>${biasText}</span>
      </div>
      <div class="roll-focus-card">
        <b>Why</b>
        <span>${biasReasonText}</span>
      </div>
      <div class="roll-focus-card">
        <b>Outcome</b>
        <span>${info.outcome}</span>
      </div>
    </div>
  `;
}

function renderTurnExplain() {
  if (!turnExplainEl) return;
  const rows = Array.isArray(lastTurnExplain) ? lastTurnExplain.filter(Boolean) : [];
  if (!rows.length) {
    turnExplainEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }
  turnExplainEl.innerHTML = `
    <div class="turn-explain-row">
      ${rows.map((row) => `
        <div class="turn-explain-pill ${row.tone || ""}">
          <b>${row.label}</b>
          <span>${row.text}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function renderRoomResolution() {
  if (!roomResolutionEl) return;
  const info = lastRoomResolution || null;
  if (!info) {
    roomResolutionEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }

  roomResolutionEl.innerHTML = `
    <div class="room-resolution-row">
      <div class="room-resolution-card ${info.kind}">
        <b>Resolved Room</b>
        <span>${info.title}</span>
      </div>
      <div class="room-resolution-card">
        <b>Outcome</b>
        <span>${info.outcome}</span>
      </div>
      <div class="room-resolution-card">
        <b>Reward</b>
        <span>${info.reward}</span>
      </div>
      <div class="room-resolution-card">
        <b>Next Room</b>
        <span>${info.next}</span>
      </div>
    </div>
  `;
}

function renderCombatDeck() {
  if (!combatDeckEl) return;
  const battle = lastStats?.battle || {};
  const skills = Array.isArray(battle.skills) ? battle.skills : [];
  if (!skills.length) {
    combatDeckEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }

  const manaCap = Number(battle.mana_cap || 0);
  const manaUsed = Number(battle.mana_used || 0);
  const normalCount = skills.filter((row) => String(row?.kind || "") !== "cursed").length;
  const cursedCount = skills.filter((row) => String(row?.kind || "") === "cursed").length;
  const validRole = normalCount === 4 && cursedCount === 2;
  const currentRoll = normalizeText(lastRolledSkillName || "");

  combatDeckEl.innerHTML = `
    <div class="combat-deck-head">
      <b>Battle Deck</b>
      <span class="small">Mana ${manaUsed}/${manaCap} | ${validRole ? "4 normal / 2 cursed" : `${normalCount} normal / ${cursedCount} cursed`}</span>
    </div>
    <div class="combat-deck-row">
      ${skills.map((row, idx) => {
        const name = String(row?.name || row?.id || `Slot ${idx + 1}`);
        const kind = String(row?.kind || "normal");
        const mana = Number(row?.mana_cost || 0);
        const chance = Number(row?.roll_chance || 0) * 100;
        const rolled = currentRoll && normalizeText(name) === currentRoll;
        const starterHint = row?.id === "self_bleed"
          ? "self-hit -> reroll"
          : (row?.id === "blank_stumble" ? "reroll setup" : `${kind} | M${mana}`);
        return `
          <div class="deck-pill ${kind} ${rolled ? "rolled" : ""}">
            <b>${idx + 1}. ${name}</b>
            <span>${starterHint}</span>
            <i>${chance.toFixed(1)}% roll</i>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderActionBrief() {
  if (!actionBriefEl) return;
  const hasCombatState = Boolean(lastEnemy) || awaitingEnemyPhase;
  if (!hasCombatState) {
    actionBriefEl.classList.add("hidden");
    actionBriefEl.innerHTML = "";
    return;
  }
  const cooldowns = lastStats?.action_cooldowns || {};
  const stamina = Number(lastStats?.stamina || 0);
  const action = String(selectedAction || "basic");
  const actionLabel = String(ACTION_META[action]?.label || action).toUpperCase();
  const cost = _actionCost(action);
  const cooldown = Number(cooldowns?.[action] || 0);
  const rerolls = Number(lastStats?.battle?.rerolls || 0);
  const canAfford = stamina >= cost;
  const isReady = !awaitingEnemyPhase && cooldown <= 0 && canAfford;
  const readinessTone = awaitingEnemyPhase ? "pending" : (isReady ? "ready" : "locked");
  const recommended = getRecommendedAction(cooldowns);
  const focusText = awaitingEnemyPhase
    ? "Dodge now"
    : cooldown > 0
      ? `Cooldown ${cooldown}t`
      : !canAfford
        ? `Need ${cost - stamina} stamina`
        : recommended && recommended !== action
          ? `Better: ${String(ACTION_META[recommended]?.label || recommended).toUpperCase()}`
          : "Ready";
  const supportText = awaitingEnemyPhase
    ? "Space / Click"
    : rerolls > 0
      ? `${rerolls} reroll${rerolls === 1 ? "" : "s"}`
      : `${cost} STA`;

  actionBriefEl.classList.remove("hidden");
  actionBriefEl.innerHTML = `
    <div class="action-brief-line ${readinessTone}">
      <b>${actionLabel}</b>
      <span>${focusText}</span>
      <i>${supportText}</i>
    </div>
  `;
}

function renderPathPreview() {
  if (!pathPreviewEl) return;
  const rows = Array.isArray(lastState?.room_preview) ? lastState.room_preview : [];
  const cadence = lastState?.run_cadence || {};
  if (!rows.length) {
    pathPreviewEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }

  const iconFor = (type, hasEnemy) => {
    const t = String(type || "").toLowerCase();
    if (t === "boss") return "BOSS";
    if (hasEnemy) return "FIGHT";
    if (t === "treasure") return "LOOT";
    if (t === "rest") return "REST";
    if (t === "trap") return "TRAP";
    if (t === "shrine") return "SHRINE";
    if (t === "event") return "EVENT";
    return t.toUpperCase();
  };

  const milestoneBits = [];
  if (Number.isFinite(Number(cadence?.next_reward_offset))) milestoneBits.push(`Reward in ${Number(cadence.next_reward_offset)} room(s)`);
  if (Number.isFinite(Number(cadence?.next_recovery_offset))) milestoneBits.push(`Recovery in ${Number(cadence.next_recovery_offset)} room(s)`);
  if (Number.isFinite(Number(cadence?.next_boss_offset))) milestoneBits.push(`Boss in ${Number(cadence.next_boss_offset)} room(s)`);
  if (Number.isFinite(Number(cadence?.next_hazard_offset))) milestoneBits.push(`Hazard in ${Number(cadence.next_hazard_offset)} room(s)`);
  if (Number(cadence?.remaining_combat_rooms || 0) > 0 || Number(cadence?.remaining_support_rooms || 0) > 0) {
    milestoneBits.push(`${Number(cadence?.remaining_combat_rooms || 0)} combat / ${Number(cadence?.remaining_support_rooms || 0)} support`);
  }

  pathPreviewEl.innerHTML = `
    <div class="path-preview-head">
      <b>Dungeon Path</b>
      <span class="small">Next ${rows.length} rooms</span>
    </div>
    <div class="path-milestones">
      ${milestoneBits.length
        ? milestoneBits.map((bit) => `<span class="path-milestone-pill">${bit}</span>`).join("")
        : `<span class="small muted">--</span>`}
    </div>
    <div class="path-preview-row">
      ${rows.map((row) => `
        <div class="path-pill ${row.is_current ? "current" : ""}">
          <span>${iconFor(row.type, row.has_enemy)}</span>
          <b>${Number(row.index || 0) + 1}</b>
          ${row.affix ? `<i>${row.affix}</i>` : ""}
        </div>
      `).join("")}
    </div>
  `;
}

function renderCombatReadout() {
  if (!combatReadoutEl) return;

  const action = String(selectedAction || "basic").toUpperCase();
  const rolled = String(lastRolledSkillName || "-");
  const rerolls = Number(lastStats?.battle?.rerolls || 0);
  const phaseTone = awaitingEnemyPhase ? "risk" : "safe";
  const phaseText = awaitingEnemyPhase ? "Enemy turn pending. Resolve dodge." : "Player turn.";
  const rerollText = rerolls > 0 ? `Rerolls ${rerolls} ready` : "—";
  combatReadoutEl.innerHTML = `
    <div class="combat-readout-grid">
      <div class="combat-readout-card ${phaseTone}">
        <b>Phase</b>
        <span>${phaseText}</span>
      </div>
      <div class="combat-readout-card">
        <b>Selected Action</b>
        <span>${action}</span>
      </div>
      <div class="combat-readout-card">
        <b>Last Rolled Skill</b>
        <span>${rolled}</span>
      </div>
      <div class="combat-readout-card">
        <b>Rerolls</b>
        <span>${rerollText}</span>
      </div>
    </div>
  `;
}

function renderRollHistory() {
  if (!rollHistoryEl) return;
  if (!Array.isArray(recentBattleRolls) || recentBattleRolls.length === 0) {
    rollHistoryEl.innerHTML = `<div class="small muted">--</div>`;
    return;
  }
  rollHistoryEl.innerHTML = recentBattleRolls.map((row, idx) => {
    const dmg = Number(row?.damage || 0).toFixed(1);
    const roll = String(row?.name || "-");
    const meta = String(row?.meta || "");
    return `
      <div class="roll-history-row">
        <span class="name">${idx + 1}. ${roll}</span>
        <span class="meta">${meta} | dmg ${dmg}</span>
      </div>
    `;
  }).join("");
}

async function startDungeonWithRisk(riskValue = null) {
  const risk = Number(riskValue === null ? (riskSlider.value || 0) : riskValue);
  riskSlider.value = String(Math.max(0, Math.min(5, risk)));
  syncRiskLabel();

  const data = await api(`/dungeon/start?risk=${riskSlider.value}`, { method: "POST" });
  recentBattleRolls = [];
  lastRolledSkillName = "-";
  lastDodgeSuccess = false;
  awaitingEnemyPhase = false;
  stopDodge();
  markerPos = 0;
  markerDir = 1;
  if (marker) marker.style.left = "0%";
  if (dodgeResult) dodgeResult.textContent = "Not started.";
  setDodgeUiState("idle", "Idle", "Safe window waiting.");
  show(data);
}

function normalizeText(v) {
  return String(v || "").toLowerCase();
}

function isEmptyUiText(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return true;
  if (text === "ready." || text === "not started." || text === "-" || text === "--") return true;
  if (/^no .* yet\.?$/i.test(text)) return true;
  if (/^no .* available\.?$/i.test(text)) return true;
  if (/^no .* ready\.?$/i.test(text)) return true;
  if (/^no .* counter hint$/i.test(text)) return true;
  if (text === "none" || text === "no active intent." || text === "no combat snapshot yet.") return true;
  return false;
}

const IDLE_TAB_META = {
  woodcutting: { icon: "ðŸŒ²", title: "Woodcutting", subtitle: "Steady timber and tonic finds." },
  fishing: { icon: "ðŸŽ£", title: "Fishing", subtitle: "Balanced gold and passive drops." },
  mining: { icon: "â›ï¸", title: "Mining", subtitle: "Best essence flow while idle." },
  herblore: { icon: "ðŸ§ª", title: "Crafting", subtitle: "High XP with support resources." },
};

function formatDurationCompact(totalSeconds) {
  const s = Math.max(0, Number(totalSeconds || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

function renderResourceLines(resources = {}) {
  const entries = Object.entries(resources || {}).filter(([, v]) => Number(v || 0) > 0);
  if (!entries.length) return `<span class="small">None</span>`;
  return entries.map(([k, v]) => `<span class="mini-chip">${k}: +${Number(v || 0)}</span>`).join("");
}

function renderOfflineSummaryModal(summary = {}) {
  if (!offlineSummaryBodyEl) return;
  const skillName = String(summary.skill_name || summary.skill || "Idle");
  const elapsed = formatDurationCompact(summary.elapsed_seconds || 0);
  const effective = formatDurationCompact(summary.effective_seconds || 0);
  const overflow = formatDurationCompact(summary.overflow_seconds || 0);
  const diminished = formatDurationCompact(summary.diminished_seconds || 0);
  const cappedNote = summary.capped ? `<p class="small muted">Duration cap reached. Upgrade Long-Haul Buffer to process more offline time.</p>` : "";
  const rare = Array.isArray(summary.rare_drops) ? summary.rare_drops : [];
  const items = Array.isArray(summary.items_gained) ? summary.items_gained : [];
  const rareText = rare.length
    ? rare.map((r) => {
        const label = r.name || r.key || r.kind || "drop";
        const amount = Number(r.amount || 0);
        return `${label}${amount > 0 ? ` +${amount}` : ""}${r.pity ? " (pity)" : ""}`;
      }).join(", ")
    : "None";
  const itemText = items.length
    ? items.map((it) => `${it.name} [${it.rarity}] P${it.power}${Array.isArray(it.passives) && it.passives.length ? ` • ${it.passives.join("/")}` : ""}`).join(", ")
    : "None";

  offlineSummaryBodyEl.innerHTML = `
    <div class="battle-rule-strip">
      <span>${skillName}</span>
      <span>Offline ${elapsed}</span>
      <span>Effective ${effective}</span>
      <span>XP ${Number(summary.xp_gained || 0)}</span>
      <span>Gold ${Number(summary.gold_gained || 0)}</span>
    </div>
    <div class="battle-rule-strip compact offline-summary-strip">
      <span>Session x${Number(summary.session_mult || 1).toFixed(2)}</span>
      <span>Efficiency x${Number(summary.efficiency_mult || 1).toFixed(2)}</span>
      <span>Quality x${Number(summary.quality_mult || 1).toFixed(2)}</span>
      <span>Levels +${Number(summary.levels_gained || 0)}</span>
      <span>Rare ${Number(summary.rare_drop_count || 0)}</span>
    </div>
    <div class="home-kv"><b>XP Gained</b><span>${Number(summary.xp_gained || 0)}</span></div>
    <div class="home-kv"><b>Levels Gained</b><span>${Number(summary.levels_gained || 0)}</span></div>
    <div class="home-kv"><b>Gold Gained</b><span>${Number(summary.gold_gained || 0)}</span></div>
    <div class="home-kv"><b>Overflow</b><span>${overflow}</span></div>
    <div class="home-kv"><b>Diminished</b><span>${diminished}</span></div>
    <p class="small"><b>Resources:</b> ${renderResourceLines(summary.resources_gained || {})}</p>
    <p class="small"><b>Rare Drops:</b> ${rareText}</p>
    <p class="small"><b>Items:</b> ${itemText}</p>
    ${cappedNote}
  `;
}

function maybeShowOfflineSummary(summary = {}) {
  if (!offlineModalEl) return;
  const at = Number(summary?.at || 0);
  const xp = Number(summary?.xp_gained || 0);
  const gold = Number(summary?.gold_gained || 0);
  const resources = summary?.resources_gained || {};
  const items = Array.isArray(summary?.items_gained) ? summary.items_gained.length : 0;
  const resourceTotal = Object.values(resources).reduce((sum, v) => sum + Number(v || 0), 0);
  const meaningful = xp > 0 || gold > 0 || resourceTotal > 0 || items > 0;
  if (!meaningful || at <= shownOfflineSummaryAt) return;
  shownOfflineSummaryAt = at;
  renderOfflineSummaryModal(summary);
  offlineModalEl.classList.remove("hidden");
}

async function refreshIdleState(showSummary = false) {
  const state = await api("/idle/state");
  if (state?.error) return null;
  idleStateCache = state;
  if (showSummary) {
    const summary = state?.offline_summary || {};
    maybeShowOfflineSummary(summary);
  }
  return state;
}

async function renderIdleTab(skillId) {
  const skill = normalizeText(skillId);
  const state = await refreshIdleState(false);
  if (!state || state.error) {
    tabContent.innerHTML = `<p class="small">Idle systems unavailable.</p>`;
    return;
  }

  const meta = IDLE_TAB_META[skill] || { icon: "â³", title: skill, subtitle: "Idle activity." };
  const activity = state.activity || {};
  const activeSkill = normalizeText(activity.skill || "");
  const isActive = state.active && activeSkill === skill;
  const skillState = state.skills?.[skill] || { level: 1, xp: 0, xp_to_next: 100 };
  const boosts = Array.isArray(state.boosts) ? state.boosts : [];
  const upgrades = state.upgrades || {};
  const summary = state.offline_summary || {};
  const tuning = state.tuning || {};
  const tuningPresets = state.tuning_presets || {};
  const skillTune = state?.skill_tuning?.[skill] || {};
  const skillPresetMap = state?.skill_tuning_presets?.[skill] || {};
  const presetIds = Object.keys(tuningPresets || {});
  const skillPresetIds = Object.keys(skillPresetMap || {});
  const presetOptions = presetIds.length
    ? presetIds.map((pid) => `<option value="${pid}">${pid}</option>`).join("")
    : `<option value="neutral">neutral</option>`;
  const skillPresetOptions = skillPresetIds.length
    ? skillPresetIds.map((pid) => `<option value="${pid}">${pid}</option>`).join("")
    : `<option value="">(none)</option>`;
  const presetDesc = {
    active_favor: "Lower idle speed, stronger active-play advantage.",
    neutral: "Balanced baseline progression.",
    idle_favor: "Higher idle gains and better long-session returns.",
  };
  const presetCards = (presetIds.length ? presetIds : ["active_favor", "neutral", "idle_favor"]).map((pid) => `
    <button class="preset-card" data-idle-balance="${pid}">
      <b>${pid}</b>
      <span>${presetDesc[pid] || "Custom preset."}</span>
    </button>
  `).join("");

  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>${meta.icon} ${meta.title}</h3>
        <p class="small area-lore">${meta.subtitle}</p>
        <div class="home-kv"><b>Status</b><span>${isActive ? "Running" : "Idle"}</span></div>
        <div class="home-kv"><b>Level</b><span>${skillState.level}</span></div>
        <div class="home-kv"><b>XP</b><span>${skillState.xp} / ${skillState.xp_to_next}</span></div>
        <div class="home-kv"><b>Runtime</b><span>${isActive ? formatDurationCompact(activity.uptime_sec || 0) : "-"}</span></div>
        <div class="home-actions">
          <button data-idle-start="${skill}" class="accent" ${isActive ? "disabled" : ""}>Start Task</button>
          <button data-idle-stop="1" ${state.active ? "" : "disabled"}>Stop Task</button>
        </div>
      </article>

      <article class="home-card">
        <h3>Boosts & Upgrades</h3>
        <div class="home-kv"><b>Efficiency Core</b><span>${Number(upgrades.efficiency || 0)}</span></div>
        <div class="home-kv"><b>Rare Scanner</b><span>${Number(upgrades.rare_find || 0)}</span></div>
        <div class="home-kv"><b>Long-Haul Buffer</b><span>${Number(upgrades.duration_cap || 0)}</span></div>
        <div class="home-actions">
          <button data-idle-upgrade="efficiency">Eff</button>
          <button data-idle-upgrade="rare_find">Rare</button>
          <button data-idle-upgrade="duration_cap">Duration</button>
        </div>
        <p class="small"><b>Active Boosts:</b> ${boosts.length ? boosts.map((b) => `${b.name} (${formatDurationCompact(b.remaining_sec)})`).join(", ") : "None"}</p>
        <div class="home-actions">
          <button data-idle-boost="surge_2h">Use Surge</button>
          <button data-idle-boost="tonic_1h">Use Tonic</button>
        </div>
      </article>

      <article class="home-card">
        <h3>Latest Offline Summary</h3>
        <div class="home-kv"><b>Activity</b><span>${summary.skill_name || "-"}</span></div>
        <div class="home-kv"><b>Time</b><span>${formatDurationCompact(summary.elapsed_seconds || 0)}</span></div>
        <div class="home-kv"><b>XP</b><span>${Number(summary.xp_gained || 0)}</span></div>
        <div class="home-kv"><b>Gold</b><span>${Number(summary.gold_gained || 0)}</span></div>
        <p class="small"><b>Resources:</b> ${renderResourceLines(summary.resources_gained || {})}</p>
        <p class="small area-lore"><b>Items:</b> ${Array.isArray(summary.items_gained) && summary.items_gained.length ? summary.items_gained.map((it) => `${it.name} [${it.rarity}]`).join(", ") : "None"}</p>
        <div class="home-actions">
          <button data-idle-summary-open="1" class="subtle">View Popup</button>
          <button data-idle-summary-claim="1" class="subtle">Clear Summary</button>
        </div>
      </article>
      <article class="home-card">
        <h3>Balance</h3>
        <div class="preset-grid">
          ${presetCards}
        </div>
        <details class="idle-advanced">
          <summary>Advanced Tuning</summary>
          <div class="idle-advanced-body">
        <div class="home-kv"><b>Idle Rate</b><span>${Number(tuning.idle_rate_mult || 0).toFixed(2)}</span></div>
        <div class="home-kv"><b>Rare Rate</b><span>${Number(tuning.rare_drop_rate_mult || 0).toFixed(2)}</span></div>
        <div class="home-kv"><b>Item Rate</b><span>${Number(tuning.item_drop_rate_mult || 0).toFixed(2)}</span></div>
        <div class="home-kv"><b>Mid Diminish</b><span>${Number(tuning.diminish_mid_mult || 0).toFixed(2)}</span></div>
        <div class="home-kv"><b>Long Diminish</b><span>${Number(tuning.diminish_long_mult || 0).toFixed(2)}</span></div>
        <div class="home-kv"><b>Preset</b><span><select class="idle-tune-input" data-idle-preset-select="1">${presetOptions}</select></span></div>
        <div class="home-kv"><b>Save As</b><span><input class="idle-tune-input" data-idle-preset-name="1" placeholder="custom_preset" /></span></div>
        <div class="home-actions">
          <button data-idle-preset-apply="1" class="subtle">Apply Preset</button>
          <button data-idle-preset-save="1" class="subtle">Save Preset</button>
          <button data-idle-preset-reset="1" class="subtle">Reset Default</button>
        </div>
        <div class="home-actions">
          <button data-idle-preset-rename="1" class="subtle">Rename Preset</button>
          <button data-idle-preset-delete="1" class="subtle">Delete Preset</button>
        </div>
        <hr />
        <p class="small"><b>Current Skill Tuning (${meta.title})</b></p>
        <div class="home-kv"><b>XP / hr</b><span><input class="idle-tune-input" data-idle-tune="xp_per_hour" type="number" min="5" max="600" step="1" value="${Number(skillTune.xp_per_hour || 0).toFixed(1)}" /></span></div>
        <div class="home-kv"><b>Gold / hr</b><span><input class="idle-tune-input" data-idle-tune="gold_per_hour" type="number" min="0" max="800" step="1" value="${Number(skillTune.gold_per_hour || 0).toFixed(1)}" /></span></div>
        <div class="home-kv"><b>Res / hr</b><span><input class="idle-tune-input" data-idle-tune="resource_per_hour" type="number" min="0" max="500" step="1" value="${Number(skillTune.resource_per_hour || 0).toFixed(1)}" /></span></div>
        <div class="home-kv"><b>Rare / min</b><span><input class="idle-tune-input" data-idle-tune="rare_chance_per_min" type="number" min="0.0001" max="0.05" step="0.0001" value="${Number(skillTune.rare_chance_per_min || 0).toFixed(4)}" /></span></div>
        <div class="home-kv"><b>Skill Preset</b><span><select class="idle-tune-input" data-idle-skill-preset-select="1">${skillPresetOptions}</select></span></div>
        <div class="home-kv"><b>Skill Save As</b><span><input class="idle-tune-input" data-idle-skill-preset-name="1" placeholder="${skill}_default" /></span></div>
        <div class="home-actions">
          <button data-idle-skill-preset-apply="1" class="subtle">Apply Skill Preset</button>
          <button data-idle-skill-preset-save="1" class="subtle">Save Skill Preset</button>
        </div>
        <div class="home-actions">
          <button data-idle-skill-preset-rename="1" class="subtle">Rename Skill Preset</button>
          <button data-idle-skill-preset-delete="1" class="subtle">Delete Skill Preset</button>
        </div>
        <div class="home-actions">
          <button data-idle-skill-tune-save="1" class="subtle">Save Skill Tuning</button>
        </div>
          </div>
        </details>
      </article>
    </section>
  `;

  tabContent.querySelector(`button[data-idle-start="${skill}"]`)?.addEventListener("click", async () => {
    const res = await api("/idle/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill }),
    });
    if (res?.error) setDebug(`Idle: ${res.error}`);
    else setDebug(`Idle started: ${meta.title}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-stop="1"]')?.addEventListener("click", async () => {
    const res = await api("/idle/stop", { method: "POST" });
    if (res?.error) setDebug(`Idle: ${res.error}`);
    else setDebug("Idle stopped.");
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelectorAll("button[data-idle-upgrade]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const upgrade = btn.getAttribute("data-idle-upgrade") || "";
      const res = await api("/idle/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upgrade }),
      });
      if (res?.error) setDebug(`Idle upgrade: ${res.error}`);
      else setDebug(`Idle upgrade applied: ${upgrade} -> ${res?.new_level || "?"}`);
      await refreshStats();
      await renderIdleTab(skill);
      if (!res?.error) await syncProgressSave("idle saved");
    });
  });

  tabContent.querySelectorAll("button[data-idle-boost]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const boost = btn.getAttribute("data-idle-boost") || "";
      const res = await api("/idle/boost/use", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ boost }),
      });
      if (res?.error) setDebug(`Idle boost: ${res.error}`);
      else setDebug(`Idle boost active: ${res?.boost?.name || boost}`);
      await refreshStats();
      await renderIdleTab(skill);
      if (!res?.error) await syncProgressSave("idle saved");
    });
  });

  tabContent.querySelector('button[data-idle-summary-open="1"]')?.addEventListener("click", () => {
    const s = idleStateCache?.offline_summary || {};
    renderOfflineSummaryModal(s);
    offlineModalEl?.classList.remove("hidden");
  });

  tabContent.querySelector('button[data-idle-summary-claim="1"]')?.addEventListener("click", async () => {
    const res = await api("/idle/summary/claim", { method: "POST" });
    if (res?.error) setDebug(`Idle summary: ${res.error}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelectorAll("button[data-idle-balance]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const profile = btn.getAttribute("data-idle-balance") || "neutral";
      const res = await api("/idle/tuning/preset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset: profile }),
      });
      if (res?.error) setDebug(`Idle tuning: ${res.error}`);
      else setDebug(`Idle tuning profile applied: ${profile}`);
      await refreshStats();
      await renderIdleTab(skill);
    });
  });

  tabContent.querySelector('button[data-idle-preset-apply="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector('select[data-idle-preset-select="1"]');
    const preset = String(sel?.value || "neutral");
    const res = await api("/idle/tuning/preset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset }),
    });
    if (res?.error) setDebug(`Preset apply failed: ${res.error}`);
    else setDebug(`Preset applied: ${preset}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-preset-save="1"]')?.addEventListener("click", async () => {
    const nameEl = tabContent.querySelector('input[data-idle-preset-name="1"]');
    const fallbackEl = tabContent.querySelector('select[data-idle-preset-select="1"]');
    const preset = String((nameEl?.value || fallbackEl?.value || "custom").trim().toLowerCase());
    if (!preset) {
      setDebug("Preset save failed: name required.");
      return;
    }
    const res = await api("/idle/tuning/preset/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset, tuning }),
    });
    if (res?.error) setDebug(`Preset save failed: ${res.error}`);
    else setDebug(`Preset saved: ${preset}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-preset-reset="1"]')?.addEventListener("click", async () => {
    const res = await api("/idle/tuning/preset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: "neutral" }),
    });
    if (res?.error) setDebug(`Reset failed: ${res.error}`);
    else setDebug("Tuning reset to neutral defaults.");
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-preset-rename="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector('select[data-idle-preset-select="1"]');
    const src = String(sel?.value || "").trim().toLowerCase();
    const nameEl = tabContent.querySelector('input[data-idle-preset-name="1"]');
    const dst = String(nameEl?.value || "").trim().toLowerCase();
    if (!src || !dst) {
      setDebug("Preset rename failed: select source and enter new name.");
      return;
    }
    const res = await api("/idle/tuning/preset/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: src, new_name: dst }),
    });
    if (res?.error) setDebug(`Preset rename failed: ${res.error}`);
    else setDebug(`Preset renamed: ${src} -> ${dst}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-preset-delete="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector('select[data-idle-preset-select="1"]');
    const preset = String(sel?.value || "").trim().toLowerCase();
    if (!preset) {
      setDebug("Preset delete failed: select a preset.");
      return;
    }
    const res = await api("/idle/tuning/preset/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset }),
    });
    if (res?.error) setDebug(`Preset delete failed: ${res.error}`);
    else setDebug(`Preset deleted: ${preset}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-skill-tune-save="1"]')?.addEventListener("click", async () => {
    const fields = Array.from(tabContent.querySelectorAll("input[data-idle-tune]"));
    const patch = {};
    fields.forEach((el) => {
      const key = el.getAttribute("data-idle-tune") || "";
      const val = Number(el.value || 0);
      if (!key || Number.isNaN(val)) return;
      patch[key] = val;
    });
    const res = await api("/idle/tuning/skill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill, tuning: patch }),
    });
    if (res?.error) setDebug(`Skill tuning: ${res.error}`);
    else setDebug(`Skill tuning saved: ${meta.title}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-skill-preset-apply="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector('select[data-idle-skill-preset-select="1"]');
    const preset = String(sel?.value || "").trim().toLowerCase();
    if (!preset) {
      setDebug("Skill preset apply failed: select a preset.");
      return;
    }
    const res = await api("/idle/tuning/skill/preset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill, preset }),
    });
    if (res?.error) setDebug(`Skill preset apply failed: ${res.error}`);
    else setDebug(`Skill preset applied: ${preset}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-skill-preset-save="1"]')?.addEventListener("click", async () => {
    const nameEl = tabContent.querySelector('input[data-idle-skill-preset-name="1"]');
    const selEl = tabContent.querySelector('select[data-idle-skill-preset-select="1"]');
    const preset = String((nameEl?.value || selEl?.value || `${skill}_default`).trim().toLowerCase());
    if (!preset) {
      setDebug("Skill preset save failed: name required.");
      return;
    }
    const fields = Array.from(tabContent.querySelectorAll("input[data-idle-tune]"));
    const patch = {};
    fields.forEach((el) => {
      const key = el.getAttribute("data-idle-tune") || "";
      const val = Number(el.value || 0);
      if (!key || Number.isNaN(val)) return;
      patch[key] = val;
    });
    const res = await api("/idle/tuning/skill/preset/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill, preset, tuning: patch }),
    });
    if (res?.error) setDebug(`Skill preset save failed: ${res.error}`);
    else setDebug(`Skill preset saved: ${preset}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-skill-preset-rename="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector('select[data-idle-skill-preset-select="1"]');
    const src = String(sel?.value || "").trim().toLowerCase();
    const nameEl = tabContent.querySelector('input[data-idle-skill-preset-name="1"]');
    const dst = String(nameEl?.value || "").trim().toLowerCase();
    if (!src || !dst) {
      setDebug("Skill preset rename failed: select source and enter new name.");
      return;
    }
    const res = await api("/idle/tuning/skill/preset/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill, preset: src, new_name: dst }),
    });
    if (res?.error) setDebug(`Skill preset rename failed: ${res.error}`);
    else setDebug(`Skill preset renamed: ${src} -> ${dst}`);
    await refreshStats();
    await renderIdleTab(skill);
  });

  tabContent.querySelector('button[data-idle-skill-preset-delete="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector('select[data-idle-skill-preset-select="1"]');
    const preset = String(sel?.value || "").trim().toLowerCase();
    if (!preset) {
      setDebug("Skill preset delete failed: select a preset.");
      return;
    }
    const res = await api("/idle/tuning/skill/preset/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skill, preset }),
    });
    if (res?.error) setDebug(`Skill preset delete failed: ${res.error}`);
    else setDebug(`Skill preset deleted: ${preset}`);
    await refreshStats();
    await renderIdleTab(skill);
  });
}

function rarityRank(rarity) {
  const ranks = {
    common: 1,
    rare: 2,
    epic: 3,
    legendary: 4,
    mythic: 5,
    supreme: 6,
    relic: 7,
  };
  return ranks[normalizeText(rarity)] || 0;
}

function runePowerScore(rune) {
  if (!rune || typeof rune !== "object") return 0;
  const effects = Array.isArray(rune.effects) ? rune.effects : [];
  const effectScore = effects.reduce((sum, e) => {
    const v = Number(e?.value || 0);
    return sum + Math.max(0, v * 100);
  }, 0);
  const lvl = Number(rune.upgrade_level || 0);
  const inf = Number(rune.relic_infusions || 0);
  return Math.round((effectScore * 8) + (lvl * 55) + (inf * 35));
}

function listingToDisplayItem(entry) {
  const kind = normalizeText(entry?.kind || "item");
  if (kind === "rune") {
    const r = entry?.rune || {};
    return {
      kind: "rune",
      name: String(r.name || "Unnamed Rune"),
      rarity: String(r.rarity || "common"),
      source: "system",
      power: runePowerScore(r),
      slot: "rune",
      rune: r,
    };
  }

  const item = entry?.item || {};
  return {
    kind: "item",
    name: String(item.name || "Item"),
    rarity: String(item.rarity || "common"),
    source: String(item.source || "system"),
    power: Number(item.power || 0),
    slot: String(item.slot || "-"),
    item,
  };
}

function itemOfferPowerScore(item) {
  const rarity = normalizeText(item?.rarity);
  const power = Number(item?.power || 0);
  const rarityMult = {
    common: 1.0,
    rare: 1.4,
    epic: 2.0,
    legendary: 3.0,
    mythic: 4.0,
    supreme: 4.8,
    relic: 5.5,
  };
  return Math.max(0, Math.floor(power * Number(rarityMult[rarity] || 1.0) * 10));
}

function _shopOfferPickerSelectedPower() {
  const stash = Array.isArray(shopOfferPicker?.stash) ? shopOfferPicker.stash : [];
  const selected = new Set(Array.isArray(shopOfferPicker?.selected) ? shopOfferPicker.selected : []);
  return stash.reduce((sum, item, idx) => selected.has(idx) ? (sum + itemOfferPowerScore(item)) : sum, 0);
}

function renderShopOfferPicker() {
  const auctionId = String(shopOfferPicker?.auctionId || "");
  if (!auctionId) return "";
  const listing = (Array.isArray(lastShopListings) ? lastShopListings : []).find((x) => String(x?.id || "") === auctionId);
  if (!listing) return "";

  const entity = listingToDisplayItem(listing);
  const stash = Array.isArray(shopOfferPicker?.stash) ? shopOfferPicker.stash : [];
  const selected = new Set(Array.isArray(shopOfferPicker?.selected) ? shopOfferPicker.selected : []);
  const selectedPower = _shopOfferPickerSelectedPower();
  const required = Number(listing?.min_offer_power || 0);

  return `
    <section class="bank-shell">
      <div class="block-head">
        <h3>Offer Items for ${entity.name}</h3>
        <button data-offer-cancel="1" class="subtle">Close</button>
      </div>
      <div class="bank-meta">
        <span>Selected: ${selected.size}</span>
        <span>Offer Power: ${selectedPower}</span>
        <span>Required: ${required}</span>
        <span>Price Alt: ${Number(listing?.price || 0)} gold</span>
      </div>
      <div class="bank-layout">
        <div class="bank-grid">
          ${stash.map((item, idx) => {
            const active = selected.has(idx) ? "active" : "";
            const score = itemOfferPowerScore(item);
            const source = item.source === "ai" ? "AI" : "SYS";
            return `
              <button class="bank-cell ${active} ${item.rarity || ""}" data-offer-pick="${idx}" title="${item.name}">
                <span class="bank-cell-name">${item.name}</span>
                <span class="bank-cell-meta">P${item.power} | ${item.slot} | ${source}</span>
                <span class="bank-cell-meta">Offer Score ${score}</span>
              </button>
            `;
          }).join("")}
          ${stash.length === 0 ? `<p class="small">Your stash is empty.</p>` : ""}
        </div>
        <aside class="bank-inspector">
          <p class="small"><b>Target:</b> ${entity.name} [${entity.slot}]</p>
          <p class="small"><b>Target Kind:</b> ${String(listing?.kind || entity.kind || "item")}</p>
          <p class="small"><b>Barter Min Power:</b> ${required}</p>
          <div class="bank-inspector-actions">
            <button data-offer-submit="${auctionId}" ${selected.size ? "" : "disabled"}>Submit Offer</button>
            <button data-offer-clear="1" class="subtle" ${selected.size ? "" : "disabled"}>Clear</button>
            <button data-offer-inspect-target="${auctionId}" class="subtle">Inspect Target</button>
          </div>
        </aside>
      </div>
    </section>
  `;
}

function renderTradeComposer(targets, inbox, outbox) {
  const targetRows = Array.isArray(targets) ? targets : [];
  const stash = Array.isArray(tradeComposer?.stash) ? tradeComposer.stash : [];
  const selected = new Set(Array.isArray(tradeComposer?.selected) ? tradeComposer.selected : []);
  const requestedPool = Array.isArray(tradeComposer?.requestedPool) ? tradeComposer.requestedPool : [];
  const requested = new Set(Array.isArray(tradeComposer?.requested) ? tradeComposer.requested : []);
  const selectedPower = stash.reduce((sum, item, idx) => selected.has(idx) ? (sum + itemOfferPowerScore(item)) : sum, 0);
  return `
    <section class="stack-block">
      <div class="block-head">
        <h3>Direct Trades</h3>
        <span class="small">Inbox ${inbox.length} • Outbox ${outbox.length}</span>
      </div>
      <div class="trade-compose-grid">
        <select data-trade-target="1">
          <option value="">Choose account</option>
          ${targetRows.map((row) => `<option value="${row}" ${String(tradeComposer?.target || "") === String(row) ? "selected" : ""}>${row}</option>`).join("")}
        </select>
        <input data-trade-gold-offer="1" type="number" min="0" step="1" value="${Number(tradeComposer?.goldOffer || 0)}" placeholder="Offer gold" />
        <input data-trade-gold-request="1" type="number" min="0" step="1" value="${Number(tradeComposer?.goldRequest || 0)}" placeholder="Request gold" />
      </div>
      <input data-trade-note="1" class="trade-note-input" maxlength="180" value="${String(tradeComposer?.note || "")}" placeholder="Note (optional)" />
      <div class="battle-rule-strip compact telemetry-strip">
        <span>Items ${selected.size}</span>
        <span>Ask Items ${requested.size}</span>
        <span>Offer Gold ${Number(tradeComposer?.goldOffer || 0)}</span>
        <span>Ask Gold ${Number(tradeComposer?.goldRequest || 0)}</span>
        <span>Offer Power ${selectedPower}</span>
      </div>
      <div class="trade-panel-head small muted">Your Offer</div>
      <div class="trade-stash-grid">
        ${stash.map((item, idx) => `
          <button class="bank-cell ${selected.has(idx) ? "active" : ""}" data-trade-pick="${idx}">
            <span class="bank-cell-name">${item.name}</span>
            <span class="bank-cell-meta">P${item.power} • ${item.slot}</span>
          </button>
        `).join("")}
        ${stash.length === 0 ? `<div class="small muted">No stash items available for trading.</div>` : ""}
      </div>
      <div class="trade-panel-head small muted">Requested From ${tradeComposer?.target || "target"}</div>
      <div class="trade-stash-grid trade-request-grid">
        ${requestedPool.map((item, idx) => `
          <button class="bank-cell ${requested.has(idx) ? "active" : ""}" data-trade-request-pick="${idx}">
            <span class="bank-cell-name">${item.name}</span>
            <span class="bank-cell-meta">P${item.power} • ${item.slot}</span>
          </button>
        `).join("")}
        ${tradeComposer?.target && requestedPool.length === 0 ? `<div class="small muted">No preview items on target account.</div>` : ""}
      </div>
      <div class="shop-card-actions trade-actions">
        <button data-trade-send="1" class="accent">Send Trade</button>
        <button data-trade-clear="1" class="subtle">Clear</button>
      </div>
    </section>
  `;
}

function renderTradeRows(title, rows, mode) {
  if (!Array.isArray(rows) || !rows.length) return "";
  return `
    <section class="stack-block">
      <div class="block-head">
        <h3>${title}</h3>
        <span class="small">${rows.length}</span>
      </div>
      <div class="shop-sales-list">
        ${rows.map((row) => `
          <div class="trade-request-row">
            <div class="trade-request-main">
              <b>${mode === "inbox" ? row.sender : mode === "outbox" ? row.target : `${row.sender} -> ${row.target}`}</b>
              <span class="small muted">${row.item_count} give | ${Number(row.requested_item_count || 0)} ask item | +${Number(row.gold_offer || 0)}g | asks ${Number(row.gold_request || 0)}g</span>
              ${mode !== "history" && Number(row.expires_at || 0) > 0 ? `<span class="small muted">Expires in ${formatTimeRemaining(Number(row.expires_at || 0))}</span>` : ""}
              ${row.note ? `<span class="small muted">${row.note}</span>` : ""}
              ${Array.isArray(row.items) && row.items.length ? `
                <div class="trade-item-preview">
                  <span class="trade-item-label">Offers</span>
                  ${row.items.map((item) => `<span class="trade-item-pill ${item.rarity || ""}">${item.name}</span>`).join("")}
                </div>
              ` : ""}
              ${Array.isArray(row.requested_items) && row.requested_items.length ? `
                <div class="trade-item-preview requested">
                  <span class="trade-item-label">Requests</span>
                  ${row.requested_items.map((item) => `<span class="trade-item-pill ${item.rarity || ""}">${item.name}</span>`).join("")}
                </div>
              ` : ""}
              ${mode === "history" && Number(row.expires_at || 0) > 0 ? `<span class="small muted">Expired / closed at ${formatUnixTs(Number(row.updated_at || row.expires_at || 0))}</span>` : ""}
            </div>
            <div class="trade-request-actions">
              ${mode === "inbox" ? `<button data-trade-accept="${row.id}" class="accent">Accept</button><button data-trade-decline="${row.id}" class="warn">Decline</button>` : mode === "outbox" ? `<button data-trade-cancel="${row.id}" class="warn">Cancel</button>` : `<span class="trade-status ${String(row.status || "pending")}">${String(row.status || "pending")}</span>`}
            </div>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function bindTradeControls() {
  tabContent.querySelector('select[data-trade-target="1"]')?.addEventListener("change", (e) => {
    tradeComposer.target = String(e.target?.value || "");
    tradeComposer.requested = [];
    tradeComposer.requestedPool = [];
    Promise.resolve(api(`/trade/target-preview?account=${encodeURIComponent(tradeComposer.target)}`)).then((res) => {
      tradeComposer.requestedPool = Array.isArray(res?.stash) ? res.stash : [];
      renderShopTab();
    });
  });
  tabContent.querySelector('input[data-trade-gold-offer="1"]')?.addEventListener("input", (e) => {
    tradeComposer.goldOffer = Math.max(0, Number(e.target?.value || 0));
  });
  tabContent.querySelector('input[data-trade-gold-request="1"]')?.addEventListener("input", (e) => {
    tradeComposer.goldRequest = Math.max(0, Number(e.target?.value || 0));
  });
  tabContent.querySelector('input[data-trade-note="1"]')?.addEventListener("input", (e) => {
    tradeComposer.note = String(e.target?.value || "");
  });
  tabContent.querySelectorAll("button[data-trade-pick]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = Number(btn.getAttribute("data-trade-pick"));
      const set = new Set(Array.isArray(tradeComposer.selected) ? tradeComposer.selected : []);
      if (set.has(idx)) set.delete(idx);
      else set.add(idx);
      tradeComposer.selected = Array.from(set.values()).sort((a, b) => a - b);
      await renderShopTab();
    });
  });
  tabContent.querySelectorAll("button[data-trade-request-pick]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = Number(btn.getAttribute("data-trade-request-pick"));
      const set = new Set(Array.isArray(tradeComposer.requested) ? tradeComposer.requested : []);
      if (set.has(idx)) set.delete(idx);
      else set.add(idx);
      tradeComposer.requested = Array.from(set.values()).sort((a, b) => a - b);
      await renderShopTab();
    });
  });
  tabContent.querySelector('button[data-trade-clear="1"]')?.addEventListener("click", async () => {
    tradeComposer = { target: "", stash: tradeComposer.stash || [], selected: [], requestedPool: [], requested: [], goldOffer: 0, goldRequest: 0, note: "" };
    await renderShopTab();
  });
  tabContent.querySelector('button[data-trade-send="1"]')?.addEventListener("click", async () => {
    const payload = {
      target_account: tradeComposer.target,
      item_indices: Array.isArray(tradeComposer.selected) ? tradeComposer.selected : [],
      requested_indices: Array.isArray(tradeComposer.requested) ? tradeComposer.requested : [],
      gold_offer: Number(tradeComposer.goldOffer || 0),
      gold_request: Number(tradeComposer.goldRequest || 0),
      note: String(tradeComposer.note || ""),
    };
    const res = await api("/trade/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res?.error) {
      setDebug(`Trade send failed: ${res.error}`);
      return;
    }
    setDebug(`Trade request sent to ${payload.target_account}.`);
    tradeComposer = { target: "", stash: [], selected: [], requestedPool: [], requested: [], goldOffer: 0, goldRequest: 0, note: "" };
    await refreshStats();
    await loadInventory();
    await renderShopTab();
    await syncProgressSave("trade saved");
  });
  tabContent.querySelectorAll("button[data-trade-accept]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const tradeId = btn.getAttribute("data-trade-accept");
      const res = await api("/trade/request/accept", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_id: tradeId }),
      });
      if (res?.error) {
        const missingName = String(res?.requested_item?.name || "");
        setDebug(`Trade accept failed: ${res.error}${missingName ? ` (${missingName})` : ""}`);
      }
      else setDebug("Trade accepted.");
      await refreshStats();
      await loadInventory();
      tradeComposer.stash = [];
      await renderShopTab();
      if (!res?.error) await syncProgressSave("trade saved");
    });
  });
  tabContent.querySelectorAll("button[data-trade-decline]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const tradeId = btn.getAttribute("data-trade-decline");
      const res = await api("/trade/request/decline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_id: tradeId }),
      });
      if (res?.error) setDebug(`Trade decline failed: ${res.error}`);
      else setDebug("Trade declined.");
      await renderShopTab();
    });
  });
  tabContent.querySelectorAll("button[data-trade-cancel]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const tradeId = btn.getAttribute("data-trade-cancel");
      const res = await api("/trade/request/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_id: tradeId }),
      });
      if (res?.error) setDebug(`Trade cancel failed: ${res.error}`);
      else setDebug("Trade cancelled.");
      await refreshStats();
      await loadInventory();
      tradeComposer.stash = [];
      await renderShopTab();
      if (!res?.error) await syncProgressSave("trade saved");
    });
  });
}

function matchesItemFilters(item, filters) {
  const kind = normalizeText(item?.kind || "item");
  const rarity = normalizeText(item?.rarity);
  const name = normalizeText(item?.name);
  const source = normalizeText(item?.source || "system");
  const kindFilter = normalizeText(filters.kind || "all");
  const kindOk = kindFilter === "all" || kind === kindFilter;
  const rarityOk = filters.rarity === "all" || rarity === filters.rarity;
  const sourceOk = filters.source === "all" || source === filters.source;
  const search = normalizeText(filters.search || "");
  const searchOk = !search || name.includes(search);
  return kindOk && rarityOk && sourceOk && searchOk;
}

function renderFilterControls(prefix, filters) {
  const sortOptions = prefix === "shop"
    ? `
      <option value="price_asc" ${filters.sort === "price_asc" ? "selected" : ""}>Price: Low -> High</option>
      <option value="price_desc" ${filters.sort === "price_desc" ? "selected" : ""}>Price: High -> Low</option>
      <option value="rarity_desc" ${filters.sort === "rarity_desc" ? "selected" : ""}>Rarity: High -> Low</option>
      <option value="power_desc" ${filters.sort === "power_desc" ? "selected" : ""}>Power: High -> Low</option>
    `
    : `
      <option value="power_desc" ${filters.sort === "power_desc" ? "selected" : ""}>Power: High -> Low</option>
      <option value="power_asc" ${filters.sort === "power_asc" ? "selected" : ""}>Power: Low -> High</option>
      <option value="rarity_desc" ${filters.sort === "rarity_desc" ? "selected" : ""}>Rarity: High -> Low</option>
      <option value="rarity_asc" ${filters.sort === "rarity_asc" ? "selected" : ""}>Rarity: Low -> High</option>
      <option value="name_asc" ${filters.sort === "name_asc" ? "selected" : ""}>Name: A -> Z</option>
      <option value="name_desc" ${filters.sort === "name_desc" ? "selected" : ""}>Name: Z -> A</option>
    `;

  const kindControl = prefix === "shop"
    ? `
      <label>Type</label>
      <select data-filter="${prefix}-kind">
        <option value="all" ${filters.kind === "all" ? "selected" : ""}>All</option>
        <option value="item" ${filters.kind === "item" ? "selected" : ""}>Items</option>
        <option value="rune" ${filters.kind === "rune" ? "selected" : ""}>Runes</option>
      </select>
    `
    : "";

  return `
    <div class="filter-row">
      <label>Search</label>
      <input data-filter="${prefix}-search" value="${filters.search || ""}" placeholder="item name" />
      ${kindControl}
      <label>Rarity</label>
      <select data-filter="${prefix}-rarity">
        <option value="all" ${filters.rarity === "all" ? "selected" : ""}>All</option>
        <option value="common" ${filters.rarity === "common" ? "selected" : ""}>Common</option>
        <option value="rare" ${filters.rarity === "rare" ? "selected" : ""}>Rare</option>
        <option value="epic" ${filters.rarity === "epic" ? "selected" : ""}>Epic</option>
        <option value="legendary" ${filters.rarity === "legendary" ? "selected" : ""}>Legendary</option>
        <option value="mythic" ${filters.rarity === "mythic" ? "selected" : ""}>Mythic</option>
        <option value="supreme" ${filters.rarity === "supreme" ? "selected" : ""}>Supreme</option>
        <option value="relic" ${filters.rarity === "relic" ? "selected" : ""}>Relic</option>
      </select>
      <label>Source</label>
      <select data-filter="${prefix}-source">
        <option value="all" ${filters.source === "all" ? "selected" : ""}>All</option>
        <option value="ai" ${filters.source === "ai" ? "selected" : ""}>AI</option>
        <option value="system" ${filters.source === "system" ? "selected" : ""}>System</option>
      </select>
      <label>Sort</label>
      <select data-filter="${prefix}-sort">
        ${sortOptions}
      </select>
    </div>
  `;
}

function bindFilterControls(prefix, filters, rerenderFn) {
  const searchInput = tabContent.querySelector(`input[data-filter="${prefix}-search"]`);
  if (searchInput) {
    searchInput.addEventListener("input", async () => {
      filters.search = searchInput.value || "";
      if (prefix === "bank") bankPage = 1;
      if (prefix === "shop") shopPage = 1;
      await rerenderFn();
    });
  }

  const kindSelect = tabContent.querySelector(`select[data-filter="${prefix}-kind"]`);
  if (kindSelect) {
    kindSelect.addEventListener("change", async () => {
      filters.kind = kindSelect.value;
      if (prefix === "shop") shopPage = 1;
      await rerenderFn();
    });
  }

  const raritySelect = tabContent.querySelector(`select[data-filter="${prefix}-rarity"]`);
  const sourceSelect = tabContent.querySelector(`select[data-filter="${prefix}-source"]`);
  if (raritySelect) {
    raritySelect.addEventListener("change", async () => {
      filters.rarity = raritySelect.value;
      if (prefix === "bank") bankPage = 1;
      if (prefix === "shop") shopPage = 1;
      await rerenderFn();
    });
  }
  if (sourceSelect) {
    sourceSelect.addEventListener("change", async () => {
      filters.source = sourceSelect.value;
      if (prefix === "bank") bankPage = 1;
      if (prefix === "shop") shopPage = 1;
      await rerenderFn();
    });
  }
  const sortSelect = tabContent.querySelector(`select[data-filter="${prefix}-sort"]`);
  if (sortSelect) {
    sortSelect.addEventListener("change", async () => {
      filters.sort = sortSelect.value;
      if (prefix === "bank") bankPage = 1;
      if (prefix === "shop") shopPage = 1;
      await rerenderFn();
    });
  }
}

function sortEntries(entries, sortKey, kind) {
  const sorted = [...entries];
  sorted.sort((a, b) => {
    const itemA = kind === "shop" ? (a.entity || listingToDisplayItem(a.entry)) : a.item;
    const itemB = kind === "shop" ? (b.entity || listingToDisplayItem(b.entry)) : b.item;
    const priceA = kind === "shop" ? Number(a.entry.price || 0) : 0;
    const priceB = kind === "shop" ? Number(b.entry.price || 0) : 0;

    if (sortKey === "price_asc") return priceA - priceB;
    if (sortKey === "price_desc") return priceB - priceA;
    if (sortKey === "power_asc") return Number(itemA.power || 0) - Number(itemB.power || 0);
    if (sortKey === "power_desc") return Number(itemB.power || 0) - Number(itemA.power || 0);
    if (sortKey === "rarity_asc") return rarityRank(itemA.rarity) - rarityRank(itemB.rarity);
    if (sortKey === "rarity_desc") return rarityRank(itemB.rarity) - rarityRank(itemA.rarity);
    if (sortKey === "name_desc") return normalizeText(itemB.name).localeCompare(normalizeText(itemA.name));
    return normalizeText(itemA.name).localeCompare(normalizeText(itemB.name));
  });
  return sorted;
}

function paginateEntries(entries, page) {
  const totalPages = Math.max(1, Math.ceil(entries.length / PAGE_SIZE));
  const clampedPage = Math.max(1, Math.min(page, totalPages));
  const start = (clampedPage - 1) * PAGE_SIZE;
  const pageItems = entries.slice(start, start + PAGE_SIZE);
  return { pageItems, totalPages, clampedPage };
}

function renderPager(prefix, page, totalPages) {
  return `
    <div class="pager-row">
      <button ${page <= 1 ? "disabled" : ""} data-page="${prefix}-prev">Prev</button>
      <span class="small">Page ${page} / ${totalPages}</span>
      <button ${page >= totalPages ? "disabled" : ""} data-page="${prefix}-next">Next</button>
    </div>
  `;
}

function bindPager(prefix, page, totalPages, rerenderFn) {
  const prev = tabContent.querySelector(`button[data-page="${prefix}-prev"]`);
  const next = tabContent.querySelector(`button[data-page="${prefix}-next"]`);
  if (prev) {
    prev.addEventListener("click", async () => {
      if (prefix === "bank" && page > 1) bankPage -= 1;
      if (prefix === "shop" && page > 1) shopPage -= 1;
      await rerenderFn();
    });
  }
  if (next) {
    next.addEventListener("click", async () => {
      if (prefix === "bank" && page < totalPages) bankPage += 1;
      if (prefix === "shop" && page < totalPages) shopPage += 1;
      await rerenderFn();
    });
  }
}

function renderItemDetails(item = null) {
  if (!itemDetailsEl) return;
  const i = item || selectedItem;
  if (!i) {
    itemDetailsEl.innerHTML = "<div class=\"small muted\">--</div>";
    updateCombatDetailBlocksVisibility();
    return;
  }

  selectedItem = i;
  const source = i.source === "ai" ? "AI" : "System";
  const passives = Array.isArray(i.passives) ? i.passives : [];
  const innate = Array.isArray(i.innate_abilities) ? i.innate_abilities : [];
  const equipped = lastStats?.equipment?.[i.slot] || null;
  const equippedPower = Number(equipped?.power || 0);
  const delta = Number(i.power || 0) - equippedPower;
  const deltaSign = delta > 0 ? "+" : "";
  const deltaText = delta === 0 ? "same as equipped" : `${delta > 0 ? "up" : "down"} ${Math.abs(delta)}`;
  const compareText = equipped
    ? `Equipped ${i.slot}: ${equipped.name} (${equippedPower}) | ${deltaText} by ${deltaSign}${delta}`
    : `Equipped ${i.slot}: None | New item is +${Number(i.power || 0)} power`;

  const innateHtml = innate.length
    ? innate.map((p) => {
        if (typeof p === "string") {
          return `<span class="passive-pill">${p}</span>`;
        }
        const trigger = p.trigger ? `@${p.trigger}` : "";
        const effects = Array.isArray(p.effects)
          ? p.effects.map((e) => `<span class="effect-tag ${["self_damage", "stat_drain", "enemy_buff"].includes(e.type) ? "debuff" : "buff"}">${e.type}:${e.value}</span>`).join("")
          : `<span class="effect-tag">no effects</span>`;
        return `<div class="passive-pill"><b>${p.name || "Innate"}</b> ${trigger}<div class="effect-tags">${effects}</div></div>`;
      }).join("")
    : `<span class="small muted">No innate weapon abilities</span>`;

  const passiveHtml = passives.length
    ? passives.map((p) => {
        if (typeof p === "string") {
          return `<span class="passive-pill">${p}</span>`;
        }
        const trigger = p.trigger ? `@${p.trigger}` : "";
        const cursedClass = p.cursed ? "cursed" : "";
        const cursedTag = p.cursed ? "cursed" : "buff";
        const effects = Array.isArray(p.effects)
          ? p.effects.map((e) => {
              const bad = ["self_damage", "stat_drain", "enemy_buff"].includes(e.type);
              const cls = bad ? "debuff" : "buff";
              return `<span class="effect-tag ${cls}">${e.type}:${e.value}</span>`;
            }).join("")
          : `<span class="effect-tag">no effects</span>`;
        return `<div class="passive-pill ${cursedClass}"><b>${p.name || "Passive"}</b> ${trigger} <span class="small">(${cursedTag})</span><div class="effect-tags">${effects}</div></div>`;
      }).join("")
    : `<span class="small muted">--</span>`;

  itemDetailsEl.innerHTML = `
    <p class="item-title ${i.rarity || ""}">${i.name}</p>
    <p>Rarity: <b>${i.rarity || "unknown"}</b> | Slot: <b>${i.slot || "-"}</b> | Power: <b>${i.power ?? "-"}</b></p>
    <p class="small">Source: ${source}</p>
    <p class="small">${compareText}</p>
    <div><b>Innate weapon abilities</b>${innateHtml}</div>
    <div>${passiveHtml}</div>
  `;
  updateCombatDetailBlocksVisibility();
}

function renderCombatLogFromResponse(data) {
  if (!combatLogEl) return;
  const log = data?.state?.log || data?.log || [];
  if (!Array.isArray(log) || log.length === 0) {
    combatLogEl.innerHTML = `<div class="small muted">--</div>`;
    updateCombatDetailBlocksVisibility();
    return;
  }

  const tail = log.slice(-12).reverse();
  combatLogEl.innerHTML = tail.map((line) => `<div class="log-line">${line}</div>`).join("");
  updateCombatDetailBlocksVisibility();
}

function _extractLootFromResponse(data) {
  const fromResult = data?.result?.loot;
  if (Array.isArray(fromResult)) return fromResult;
  const direct = data?.loot;
  if (Array.isArray(direct)) return direct;
  return [];
}

function renderRecentDrops(data = null) {
  if (!recentDropsEl) return;

  const loot = _extractLootFromResponse(data || {});
  if (loot.length > 0) {
    recentDrops = [...loot, ...recentDrops].slice(0, 12);
  }

  if (!recentDrops.length) {
    recentDropsEl.innerHTML = `<div class="small muted">--</div>`;
    updateCombatDetailBlocksVisibility();
    return;
  }

  recentDropsEl.innerHTML = recentDrops.map((item, idx) => `
    <div class="drop-row ${item.rarity || ""}">
      <span><b>${idx + 1}. ${item.name}</b> [${item.slot}]</span>
      <span class="drop-actions">
        <span class="small">P${item.power} | ${item.source === "ai" ? "AI" : "System"}</span>
        <button data-drop-inspect="${idx}">Inspect</button>
      </span>
    </div>
  `).join("");

  recentDropsEl.querySelectorAll("button[data-drop-inspect]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.getAttribute("data-drop-inspect"));
      const item = recentDrops[idx];
      renderItemDetails(item || null);
    });
  });
  updateCombatDetailBlocksVisibility();
}

function _collectPassiveEffectsFromTriggers(triggers) {
  if (!triggers || typeof triggers !== "object") return [];
  const all = [];
  Object.entries(triggers).forEach(([triggerName, block]) => {
    const effects = block?.effects || [];
    if (!Array.isArray(effects)) return;
    effects.forEach((e) => {
      all.push({
        trigger: triggerName,
        passive_name: e.passive_name || "Passive",
        type: e.type || "effect",
        value: e.value,
        cursed: Boolean(e.cursed),
      });
    });
  });
  return all;
}

function renderTurnSummary(data) {
  if (!turnSummaryEl) return;
  const turn = data?.turn;
  const combat = data?.combat;

  if (data?.cleared && data?.result) {
    const r = data.result || {};
    const lootCount = Array.isArray(r.loot) ? r.loot.length : 0;
    turnSummaryEl.innerHTML = `
      <div class="summary-row"><b>Dungeon Cleared</b><span>Yes</span></div>
      <div class="summary-row"><b>Boss Defeated</b><span>Yes</span></div>
      <div class="summary-row"><b>Next Depth</b><span>${r.next_depth ?? "-"}</span></div>
      <div class="summary-row"><b>Loot Count</b><span>${lootCount}</span></div>
    `;
    setTurnSummaryStrip(`Dungeon cleared | Boss defeated | Next depth ${r.next_depth ?? "-"}`, true);
    updateCombatDetailBlocksVisibility();
    return;
  }

  if (turn && typeof turn === "object") {
    const p = turn.player || {};
    const e = turn.enemy || {};
    const playerDmg = Number(p.damage || 0);
    const enemyDmg = Number(e.damage || 0);
    const dodge = typeof e.dodge_success === "boolean" ? (e.dodge_success ? "Success" : "Fail") : "N/A";
    const rollName = String(p?.skill_roll?.name || p?.skill_roll?.id || "-");
    const mastery = p?.skill_roll?.mastery || {};
    const masteryLvl = Number(mastery.level || 1).toFixed(1);
    const masteryGain = Number(p?.skill_roll?.mastery_gain_levels || 0);
    const masteryPerks = Array.isArray(p?.skill_roll?.mastery_perks) ? p.skill_roll.mastery_perks : [];
    const perkText = masteryPerks.length ? masteryPerks.map((x) => String(x?.id || x)).join(", ") : "-";
    const rerollsLeft = Number(p?.skill_roll?.rerolls_left || 0);
    const strip = `Rolled ${rollName} | You dealt ${playerDmg.toFixed(2)} | Enemy dealt ${enemyDmg.toFixed(2)} | Dodge ${dodge}`;
    turnSummaryEl.innerHTML = `
      <div class="summary-row"><b>Rolled Skill</b><span>${rollName}</span></div>
      <div class="summary-row"><b>Mastery</b><span>Lv ${masteryLvl}${masteryGain > 0 ? ` (+${masteryGain})` : ""}</span></div>
      <div class="summary-row"><b>Mastery Perks</b><span>${perkText}</span></div>
      <div class="summary-row"><b>Rerolls Left</b><span>${rerollsLeft}</span></div>
      <div class="summary-row"><b>You dealt</b><span>${playerDmg.toFixed(2)}</span></div>
      <div class="summary-row"><b>Enemy dealt</b><span>${enemyDmg.toFixed(2)}</span></div>
      <div class="summary-row"><b>Dodge</b><span>${dodge}</span></div>
    `;
    setTurnSummaryStrip(strip, true);
    updateCombatDetailBlocksVisibility();
    return;
  }

  if (combat && typeof combat === "object") {
    const isEnemyEvent = combat.event === "enemy_attack";
    const dealt = Number(combat.damage || 0);
    const dodge = isEnemyEvent && typeof combat.dodge_success === "boolean" ? (combat.dodge_success ? "Success" : "Fail") : "N/A";
    const rollName = String(combat?.skill_roll?.name || combat?.skill_roll?.id || "-");
    const mastery = combat?.skill_roll?.mastery || {};
    const masteryLvl = Number(mastery.level || 1).toFixed(1);
    const masteryPerks = Array.isArray(combat?.skill_roll?.mastery_perks) ? combat.skill_roll.mastery_perks : [];
    const perkText = masteryPerks.length ? masteryPerks.map((x) => String(x?.id || x)).join(", ") : "-";
    const strip = `${combat.event || "combat"} | Rolled ${rollName} | ${dealt.toFixed(2)} damage | Dodge ${dodge}`;
    turnSummaryEl.innerHTML = `
      <div class="summary-row"><b>Event</b><span>${combat.event || "combat"}</span></div>
      <div class="summary-row"><b>Rolled Skill</b><span>${rollName}</span></div>
      <div class="summary-row"><b>Mastery</b><span>Lv ${masteryLvl}</span></div>
      <div class="summary-row"><b>Mastery Perks</b><span>${perkText}</span></div>
      <div class="summary-row"><b>Damage</b><span>${dealt.toFixed(2)}</span></div>
      <div class="summary-row"><b>Dodge</b><span>${dodge}</span></div>
    `;
    setTurnSummaryStrip(strip, true);
    updateCombatDetailBlocksVisibility();
    return;
  }

  turnSummaryEl.innerHTML = `<div class="small muted">--</div>`;
  setTurnSummaryStrip("--", true);
  updateCombatDetailBlocksVisibility();
}

function renderPassiveFeed(data) {
  if (!passiveFeedEl) return;
  const turn = data?.turn;
  let entries = [];

  if (turn?.player?.passive_triggers) {
    entries = entries.concat(_collectPassiveEffectsFromTriggers(turn.player.passive_triggers));
  }
  if (turn?.enemy?.passive_triggers) {
    entries = entries.concat(_collectPassiveEffectsFromTriggers(turn.enemy.passive_triggers));
  }
  if (entries.length === 0 && data?.combat?.passive_triggers) {
    entries = _collectPassiveEffectsFromTriggers(data.combat.passive_triggers);
  }

  if (!entries.length) {
    passiveFeedEl.innerHTML = `<div class="small muted">--</div>`;
    updateCombatDetailBlocksVisibility();
    return;
  }

  passiveFeedEl.innerHTML = entries.slice(0, 12).map((x) => `
    <div class="proc-line ${x.cursed ? "cursed" : "buff"}">
      <span class="trigger-badge">${x.trigger}</span>
      <b>${x.passive_name}</b> -> ${x.type}${x.value !== undefined ? `:${x.value}` : ""}
    </div>
  `).join("");
  updateCombatDetailBlocksVisibility();
}

function renderAiStatus(data) {
  if (!aiStatusEl) return;
  if (!data || data.error) {
    aiStatusEl.textContent = "AI: Unavailable";
    aiStatusEl.classList.add("off");
    return;
  }

  if (data.enabled) {
    aiStatusEl.textContent = `AI: ON (${data.provider}/${data.model})`;
    aiStatusEl.classList.add("on");
    aiStatusEl.classList.remove("off");
  } else {
    aiStatusEl.textContent = `AI: OFF (loot falls back to system)`;
    aiStatusEl.classList.add("off");
    aiStatusEl.classList.remove("on");
  }
}

/* =========================
   STATUS PANEL FUNCTIONS
========================= */

function formatPotency(id, data) {
  if (!data) return "";
  const pot = data.potency ?? 0;

  if (id === "bleed") {
    const tick = data.tick ?? pot;
    return `tick ${Number(tick).toFixed(1)}`;
  }
  if (id === "burn") {
    return `dmg ${Number(pot).toFixed(1)}`;
  }
  if (["weak","freeze","vulnerable","guard"].includes(id)) {
    return `${Math.round(Number(pot) * 100)}%`;
  }
  return pot;
}

function renderStatusList(el, statusObj) {
  if (!el) return false;

  const entries = Object.entries(statusObj || {});
  if (entries.length === 0) {
    el.innerHTML = `<div class="status-empty">None</div>`;
    return false;
  }

  el.innerHTML = entries.map(([id, data]) => `
    <div class="status-badge status-${id}">
      <strong>${id.toUpperCase()}</strong>
      <span>${data.turns}t â€¢ ${formatPotency(id, data)}</span>
    </div>
  `).join("");
  return true;
}

function summarizeStatusMap(statusObj) {
  const entries = Object.entries(statusObj || {});
  if (!entries.length) return "";
  return entries
    .slice(0, 3)
    .map(([id, data]) => `${String(id).toUpperCase()} ${Number(data?.turns || 0)}t`)
    .join(" • ");
}

function updateStatusPanelsFromResponse(data) {
  // backend may return status at top-level or nested in state
  const playerStatus =
    data?.player_status ||
    data?.combat?.player_status ||
    data?.state?.player_status ||
    data?.player?.status ||
    {};
  const enemyStatus =
    data?.enemy_status ||
    data?.combat?.enemy_status ||
    data?.state?.enemy_status ||
    data?.state?.enemy?.status ||
    data?.enemy?.status ||
    {};

  latestPlayerStatus = playerStatus || {};
  latestEnemyStatus = enemyStatus || {};

  const hasPlayerStatus = renderStatusList(playerStatusList, playerStatus);
  const hasPlayerMiniStatus = renderStatusList(playerStatusMini, playerStatus);
  const hasEnemyStatus = renderStatusList(enemyStatusList, enemyStatus);

  playerStatusMini?.closest(".player-support-card")?.classList.toggle("hidden", !hasPlayerMiniStatus);
  enemyStatusList?.closest(".enemy-support-card")?.classList.toggle("hidden", !hasEnemyStatus);
  if (!hasPlayerStatus && playerStatusList) {
    playerStatusList.innerHTML = `<div class="status-empty">None</div>`;
  }
  updateArenaSupportVisibility();
}

/* =========================
   âœ… STEP 15: BOSS INTENT UI
========================= */

function renderBossIntentFromResponse(data) {
  if (!bossIntentEl) return;

  // try multiple possible response shapes
  const intent =
    data?.next_intent ||
    data?.state?.next_intent ||
    data?.combat?.next_intent ||
    null;

  if (intent) lastBossIntent = intent;

  if (!lastBossIntent) {
    bossIntentEl.textContent = "None";
    bossIntentEl.closest(".enemy-support-card")?.classList.toggle("hidden", true);
    updateArenaSupportVisibility();
    return;
  }

  bossIntentEl.closest(".enemy-support-card")?.classList.toggle("hidden", false);
  const name = lastBossIntent.name || "Attack";
  const tele = lastBossIntent.telegraph || "";
  const counter = lastBossIntent.counter_action ? `Counter: ${String(lastBossIntent.counter_action).toUpperCase()}` : "";
  const hits = Number(lastBossIntent.hits || 1);
  const mult = Number(lastBossIntent.damage_mult || 1);
  bossIntentEl.innerHTML = `
    <div class="combat-card-title">${name}</div>
    <div class="combat-card-text">${tele || "No telegraph."}</div>
    <div class="combat-chip-row">
      <span class="mini-chip">Hits ${hits}</span>
      <span class="mini-chip">x${mult.toFixed(2)} dmg</span>
      ${counter ? `<span class="mini-chip mini-chip-counter">${counter}</span>` : ""}
    </div>
  `;
  updateArenaSupportVisibility();
}

/* ========================= */

function show(data) {
  output.textContent = JSON.stringify(data, null, 2);
  const explain = [];
  const rolledName = data?.turn?.player?.skill_roll?.name || data?.combat?.skill_roll?.name || "";
  if (rolledName) {
    lastRolledSkillName = String(rolledName);
    const rolled = data?.turn?.player?.skill_roll || data?.combat?.skill_roll || {};
    const dmg = Number(data?.turn?.player?.damage ?? data?.combat?.damage ?? 0);
    const rerolled = Boolean(rolled?.rerolled);
    const kind = String(rolled?.kind || "normal");
    const masteryLevel = Number(rolled?.mastery?.level || 1).toFixed(1);
    const masteryGain = Number(rolled?.mastery_gain_levels || 0);
    const masteryPerks = Array.isArray(rolled?.mastery_perks) ? rolled.mastery_perks : [];
    const perkText = masteryPerks.length ? ` | ${masteryPerks.map((x) => String(x?.id || x)).join("+")}` : "";
    const meta = `${kind}${rerolled ? " | rerolled" : ""} | M${masteryLevel}${masteryGain > 0 ? ` +${masteryGain}` : ""}${perkText}`;
    recentBattleRolls.unshift({
      name: lastRolledSkillName,
      damage: dmg,
      meta,
      ts: Date.now(),
    });
    if (recentBattleRolls.length > 5) {
      recentBattleRolls = recentBattleRolls.slice(0, 5);
    }
    const counter = data?.turn?.player?.counter || data?.combat?.counter || {};
    lastRollFocus = {
      name: String(rolled?.name || rolled?.id || rolledName),
      kind: String(rolled?.kind || "normal"),
      rerolled: Boolean(rolled?.rerolled),
      masteryLevel: Number(rolled?.mastery?.level || 1).toFixed(1),
      masteryGain: Number(rolled?.mastery_gain_levels || 0),
      masteryPerks: Array.isArray(rolled?.mastery_perks) ? rolled.mastery_perks.map((x) => String(x?.id || x)) : [],
      counterNeeded: String(counter?.needed || counter?.against || "").toUpperCase(),
      counterSuccess: Boolean(counter?.success),
      outcome: dmg > 0 ? `${dmg.toFixed(1)} damage` : (String(rolled?.kind || "") === "cursed" ? "Cursed utility / backlash line" : "No damage line"),
    };
  }
  const turnPlayer = data?.turn?.player || data?.combat || {};
  const turnEnemy = data?.turn?.enemy || {};
  const mechanicText = {
    crusher_break_guard: "Crusher punished a guard-heavy line and shaved damage.",
    shadowstep_slip: "Shadowstep slipped the commit and reduced the hit.",
    bulwark_shell: "Bulwark shell absorbed part of the strike.",
    tank_bastion: "Boss bastion phase reduced incoming damage.",
    skirmisher_phase_slip: "Boss skirmisher phase slipped the commitment.",
    caster_barrier_snap: "Boss caster phase snapped a barrier back online.",
    berserker_rage: "Berserker rage increased enemy-turn damage.",
    hexweaver_weak: "Hexweaver applied weak pressure.",
    stormcaller_discharge: "Stormcaller discharged stored pressure.",
    venomrunner_bleed: "Venomrunner applied bleed pressure.",
    ironhide_guard: "Ironhide re-formed guard.",
    broodlord_swarm: "Broodlord swarm burst triggered.",
    bonecaller_harvest: "Bonecaller harvested bleed into healing.",
    brute_quake: "Boss brute phase triggered quake damage.",
    caster_barrier_phase: "Boss caster phase rebuilt barrier.",
    caster_hex_phase: "Boss caster phase applied a hex window.",
    skirmisher_rupture_window: "Boss skirmisher phase opened a weak window.",
    tank_fortress_cycle: "Boss tank phase cycled fortress guard.",
    summoner_phase_swarm: "Boss summoner phase added swarm pressure.",
  };
  if (turnPlayer?.battle_fallback) {
    explain.push({ label: "Fallback", text: `Rolled action failed, used BASIC instead (${turnPlayer.battle_fallback.reason || "unusable"}).`, tone: "risk" });
  }
  if (turnPlayer?.archetype_reaction?.type) {
    explain.push({ label: "Enemy Reaction", text: `${String(turnPlayer.archetype_reaction.type).replaceAll("_", " ")} changed damage flow.`, tone: "mid" });
  }
  if (turnPlayer?.elite_variant_reaction?.type) {
    const type = String(turnPlayer.elite_variant_reaction.type || "");
    const reduced = Number(turnPlayer?.elite_variant_reaction?.reduced || 0);
    explain.push({
      label: "Elite",
      text: `${mechanicText[type] || type.replaceAll("_", " ")}${reduced > 0 ? ` (${reduced.toFixed(1)} prevented)` : ""}`,
      tone: "mid",
    });
  }
  if (turnPlayer?.boss_phase_reaction?.type) {
    const type = String(turnPlayer.boss_phase_reaction.type || "");
    const phase = Number(turnPlayer?.boss_phase_reaction?.phase || 0);
    const reduced = Number(turnPlayer?.boss_phase_reaction?.reduced || 0);
    explain.push({
      label: "Boss Phase",
      text: `${mechanicText[type] || type.replaceAll("_", " ")}${phase > 0 ? ` (phase ${phase + 1})` : ""}${reduced > 0 ? ` | ${reduced.toFixed(1)} reduced` : ""}`,
      tone: "risk",
    });
  }
  if (turnPlayer?.room_affix_effect?.id) {
    const affix = String(turnPlayer.room_affix_effect.id).toUpperCase();
    const extra = turnPlayer.room_affix_effect.reduced
      ? ` cut ${Number(turnPlayer.room_affix_effect.reduced).toFixed(1)} damage`
      : (turnPlayer.room_affix_effect.self_damage ? ` reflected ${Number(turnPlayer.room_affix_effect.self_damage).toFixed(1)} to you` : " altered the turn");
    explain.push({ label: "Affix", text: `${affix}${extra}.`, tone: "risk" });
  }
  if (turnPlayer?.counter?.against) {
    explain.push({
      label: "Counter",
      text: turnPlayer.counter.success
        ? `Matched intent and gained bonus pressure.`
        : `Missed counter; needed ${String(turnPlayer.counter.needed || "").toUpperCase() || "different action"}.`,
      tone: turnPlayer.counter.success ? "safe" : "mid",
    });
  }
  if (Number(turnPlayer?.mastery_bonus_damage || 0) > 0) {
    explain.push({ label: "Mastery", text: `Apex mastery added ${Number(turnPlayer.mastery_bonus_damage).toFixed(1)} bonus damage.`, tone: "safe" });
  }
  if (Number(turnPlayer?.rune_attack_bonus || 0) > 0 || Number(turnPlayer?.rune_lifesteal_heal || 0) > 0) {
    const bits = [];
    if (Number(turnPlayer?.rune_attack_bonus || 0) > 0) bits.push(`+${Number(turnPlayer.rune_attack_bonus).toFixed(1)} damage`);
    if (Number(turnPlayer?.rune_lifesteal_heal || 0) > 0) bits.push(`+${Number(turnPlayer.rune_lifesteal_heal).toFixed(1)} HP`);
    explain.push({ label: "Runes", text: bits.join(" | "), tone: "safe" });
  }
  if (Number(turnEnemy?.rune_damage_prevented || 0) > 0 || Number(turnEnemy?.tree_damage_prevented || 0) > 0 || Number(turnEnemy?.boss_wrath_bonus || 0) > 0) {
    const bits = [];
    if (Number(turnEnemy?.rune_damage_prevented || 0) > 0) bits.push(`runes prevented ${Number(turnEnemy.rune_damage_prevented).toFixed(1)}`);
    if (Number(turnEnemy?.tree_damage_prevented || 0) > 0) bits.push(`tree prevented ${Number(turnEnemy.tree_damage_prevented).toFixed(1)}`);
    if (Number(turnEnemy?.boss_wrath_bonus || 0) > 0) bits.push(`boss wrath +${Number(turnEnemy.boss_wrath_bonus).toFixed(1)}`);
    explain.push({ label: "Enemy Phase", text: bits.join(" | "), tone: Number(turnEnemy?.boss_wrath_bonus || 0) > 0 ? "risk" : "mid" });
  }
  if (Number(turnEnemy?.summoner_swarm || 0) > 0 || turnEnemy?.caster_barrier_refreshed) {
    const bits = [];
    if (Number(turnEnemy?.summoner_swarm || 0) > 0) bits.push(`summoner swarm ${Number(turnEnemy.summoner_swarm).toFixed(0)}`);
    if (turnEnemy?.caster_barrier_refreshed) bits.push("caster barrier refreshed");
    explain.push({ label: "Archetype", text: bits.join(" | "), tone: "mid" });
  }
  if (turnEnemy?.elite_variant_effect?.type) {
    const type = String(turnEnemy.elite_variant_effect.type || "");
    const bits = [mechanicText[type] || type.replaceAll("_", " ")];
    if (Number(turnEnemy?.elite_variant_effect?.damage || 0) > 0) bits.push(`${Number(turnEnemy.elite_variant_effect.damage).toFixed(0)} dmg`);
    if (Number(turnEnemy?.elite_variant_effect?.bonus || 0) > 0) bits.push(`+${Number(turnEnemy.elite_variant_effect.bonus).toFixed(1)}`);
    if (Number(turnEnemy?.elite_variant_effect?.heal || 0) > 0) bits.push(`+${Number(turnEnemy.elite_variant_effect.heal).toFixed(1)} HP`);
    explain.push({ label: "Elite", text: bits.join(" | "), tone: "mid" });
  }
  if (turnEnemy?.boss_phase_effect?.type) {
    const type = String(turnEnemy.boss_phase_effect.type || "");
    const phase = Number(turnEnemy?.boss_phase_effect?.phase || 0);
    const bits = [`${mechanicText[type] || type.replaceAll("_", " ")}${phase > 0 ? ` (phase ${phase + 1})` : ""}`];
    if (Number(turnEnemy?.boss_phase_effect?.damage || 0) > 0) bits.push(`${Number(turnEnemy.boss_phase_effect.damage).toFixed(0)} dmg`);
    explain.push({ label: "Boss Phase", text: bits.join(" | "), tone: "risk" });
  }
  if (data?.victory_rewards && typeof data.victory_rewards === "object") {
    const rewards = data.victory_rewards;
    const bits = [];
    if (Number(rewards.gold || 0) > 0) bits.push(`+${Number(rewards.gold)} gold`);
    if (Number(rewards.stamina || 0) > 0) bits.push(`+${Number(rewards.stamina).toFixed(0)} stamina`);
    if (Number(rewards.rune_essence || 0) > 0) bits.push(`+${Number(rewards.rune_essence)} essence`);
    if (Number(rewards.arcane_chest || 0) > 0) bits.push(`+${Number(rewards.arcane_chest)} chest`);
    if (Number(rewards.rune_relic || 0) > 0) bits.push(`+${Number(rewards.rune_relic)} relic`);
    if (bits.length) {
      explain.push({ label: "Rewards", text: bits.join(" | "), tone: "safe" });
    }
  }
  lastTurnExplain = explain.slice(0, 7);
  if (data?.cleared && data?.result) {
    lastRunResult = data.result;
    showRunClearModal(data.result);
    saveActiveAccount(true).then((ok) => {
      if (ok) setAccountSaveState("run saved", "synced");
    });
  }
  if (data?.state) {
    lastState = data.state;
  } else if (typeof data?.active === "boolean" && data?.room_count !== undefined) {
    lastState = data;
  }
  syncTurnFlowState(data);
  renderEnemyFromState(data);
  renderBossIntentFromResponse(data);
  updateStatusPanelsFromResponse(data);
  renderCombatLogFromResponse(data);
  renderRoomEvents(data);
  renderRecentDrops(data);
  renderTurnSummary(data);
  renderPassiveFeed(data);
  renderCombatFeedback(data);
  refreshStats();
  loadInventory();
  renderActiveTab();
  renderItemDetails();
  renderTopRunContext();
  renderHud();
  renderRollHistory();
}

const API_TIMEOUT_MS = 4000;

async function api(url, opts = {}) {
  try {
    setDebug(`Calling: ${opts.method || "GET"} ${url}`);
    const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timeoutId = controller
      ? setTimeout(() => controller.abort(new Error(`Timeout after ${API_TIMEOUT_MS}ms`)), API_TIMEOUT_MS)
      : null;
    const requestOpts = { ...opts };
    if (controller && !requestOpts.signal) {
      requestOpts.signal = controller.signal;
    }
    const res = await fetch(url, requestOpts);
    if (timeoutId) clearTimeout(timeoutId);
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { raw: text }; }
    if (!res.ok) setDebug(`ERROR ${res.status} ${res.statusText}\n${text}`);
    return data;
  } catch (e) {
    const message = /abort|timeout/i.test(String(e))
      ? `Request timed out: ${url}`
      : `FETCH FAILED: ${e}`;
    setDebug(message);
    return { error: String(e) };
  }
}

function syncRiskLabel() { riskValue.textContent = String(riskSlider.value); }
riskSlider.addEventListener("input", syncRiskLabel);
riskSlider.addEventListener("change", syncRiskLabel);
syncRiskLabel();

function renderEnemyFromState(data) {
  const state = data.state || data;
  const e = state && state.enemy ? state.enemy : null;
  const affix = state?.current_affix || null;
  lastEnemy = e;

  if (!e) {
    if (state?.can_leave) {
      enemyBox.innerHTML = `
        <div class="combat-entity-card empty">
          <div class="combat-card-title">Boss Defeated</div>
          <div class="combat-card-text">Leave the dungeon to complete the run and lock in rewards.</div>
        </div>
      `;
    } else {
      enemyBox.textContent = "No active enemy.";
    }
    renderIntentBanner(null);
    renderCombatQuickBar();
    updateDodgeCardVisibility();
    return;
  }

  const enemyHp = Number(e.hp || 0);
  const enemyMaxHp = Math.max(enemyHp, Number(e.max_hp || enemyHp || 1));
  const enemyHpPct = Math.max(0, Math.min(100, (enemyHp / Math.max(1, enemyMaxHp)) * 100));
  const playerAtk = Number(lastStats?.attack || 0);
  const playerDef = Number(lastStats?.defense || 0);
  const playerSta = Number(lastStats?.stamina || 0);
  const enemyAtk = Number(e.attack || 0);
  const atkDelta = playerAtk - enemyAtk;
  const defDelta = playerDef - enemyAtk;
  const pressure = enemyAtk >= (Number(lastStats?.max_hp || 100) * 0.22)
    ? "High pressure"
    : (enemyAtk >= (Number(lastStats?.max_hp || 100) * 0.12) ? "Mid pressure" : "Low pressure");
  const matchup = atkDelta >= 12 ? "You have the edge" : (atkDelta >= 0 ? "Matchup is even" : "Enemy has the edge");
  const sustain = playerSta >= 35 ? "Stamina stable" : "Stamina tight";
  const readLine = defDelta >= 0 ? "You can push damage." : "Guard or dodge the next exchange.";
  const eliteVariant = String(e?.combat_mods?.elite_variant || "").toLowerCase();
  const learnedMechanics = lastStats?.mechanics_learned || {};
  const isNewEliteVariant = eliteVariant && !learnedMechanics[`elite_variant:${eliteVariant}`];
  const bossArchetype = String(e?.archetype || "brute").toLowerCase();
  const isBoss = String(e?.tier || "").toLowerCase() === "boss";
  const isNewBossArchetype = isBoss && !learnedMechanics[`boss_archetype:${bossArchetype}`];
  const affixId = String(affix?.id || "").toLowerCase();
  const isNewAffix = affixId && !learnedMechanics[`room_affix:${affixId}`];
  const bossHintMap = {
    brute: "Phase quake bursts on enemy turns.",
    caster: "Rebuilds barrier and hex pressure.",
    skirmisher: "Slips commitment and opens weak windows.",
    tank: "Builds fortress guard cycles.",
    summoner: "Adds swarm pressure every phase.",
  };
  const eliteHintMap = {
    crusher: "Punishes guard-heavy lines.",
    berserker: "Gets sharper below half HP.",
    hexweaver: "Applies weakening pressure.",
    stormcaller: "Discharges after building charge.",
    shadowstep: "Can slip heavy commitments.",
    venomrunner: "Stacks bleed on enemy turns.",
    bulwark: "Shrugs off non-rupture hits.",
    ironhide: "Can re-form guard mid fight.",
    broodlord: "Builds swarm bursts over time.",
    bonecaller: "Bleed lets it harvest back HP.",
  };
  const enemyMeta = [
    `ATK ${e.attack}`,
    `LV ${e.level ?? "-"}`,
    e.archetype ? String(e.archetype).toUpperCase() : "",
    eliteVariant ? `ELITE ${eliteVariant.replaceAll("_", " ").toUpperCase()}` : "",
    affix?.name ? affix.name : "",
  ].filter(Boolean).join(" • ");
  const noveltyBits = [
    isNewBossArchetype ? "NEW BOSS" : "",
    isNewEliteVariant ? "NEW VARIANT" : "",
    isNewAffix ? "NEW AFFIX" : "",
  ].filter(Boolean);
  const encounterRead = [
    isBoss ? (state?.boss_temper?.mood ? `Temper ${String(state.boss_temper.mood).replaceAll("_", " ")}` : "Boss phase fight") : "",
    eliteVariant ? `${eliteVariant.replaceAll("_", " ")} pattern` : "",
    affix?.name ? `${affix.name} room` : "",
  ].filter(Boolean).join(" • ");
  const enemyStatusSummary = summarizeStatusMap(latestEnemyStatus);
  const intentSummary = lastBossIntent
    ? `${String(lastBossIntent.name || "Attack").toUpperCase()}${lastBossIntent.counter_action ? ` • counter ${String(lastBossIntent.counter_action).toUpperCase()}` : ""}`
    : "";
  const enemyDetailChips = [
    encounterRead || "",
    isBoss ? (bossHintMap[String(e?.archetype || "brute").toLowerCase()] || "Boss phase behavior active.") : "",
    eliteVariant ? (eliteHintMap[eliteVariant] || "Elite behavior active.") : "",
    intentSummary ? `Intent ${intentSummary}` : "",
    enemyStatusSummary ? `Status ${enemyStatusSummary}` : "",
  ].filter(Boolean).slice(0, 3);

  enemyBox.innerHTML = `
    <div class="combat-entity-card">
      <div class="combat-entity-head">
        <div>
          <div class="combat-card-title">${e.name}</div>
          <div class="combat-card-subtitle">${String(e.tier || "normal").toUpperCase()}</div>
        </div>
        <div class="combat-card-meta">${enemyMeta}</div>
      </div>
      ${noveltyBits.length ? `<div class="combat-chip-row">${noveltyBits.map((bit) => `<span class="mini-chip new">${bit}</span>`).join("")}</div>` : ""}
      <div class="resource-track-wrap">
        <div class="resource-track-label"><span>HP</span><b>${enemyHp} / ${enemyMaxHp}</b></div>
        <div class="resource-track enemy"><span style="width:${enemyHpPct.toFixed(1)}%"></span></div>
      </div>
      <div class="combat-chip-row matchup-row combat-chip-row-primary">
        <span class="mini-chip emphasis">${pressure}</span>
        <span class="mini-chip">${matchup}</span>
        <span class="mini-chip">${sustain}</span>
      </div>
      <div class="combat-card-text">${readLine}</div>
      ${enemyDetailChips.length ? `<div class="combat-chip-row combat-chip-row-secondary">${enemyDetailChips.map((bit) => `<span class="mini-chip soft">${bit}</span>`).join("")}</div>` : ""}
    </div>
  `;

  renderIntentBanner(e.intent || data?.next_intent || data?.combat?.next_intent || null);
  renderCombatQuickBar();
  updateDodgeCardVisibility();
}

function renderIntentBanner(intent) {
  if (!intentBannerEl || !intentThreatEl || !intentTextEl) return;

  if (!intent || typeof intent !== "object") {
    if (intentKindEl) intentKindEl.textContent = "Intent";
    intentThreatEl.textContent = "SAFE";
    intentThreatEl.className = "intent-threat safe";
    intentTextEl.innerHTML = "<span class=\"small muted\">--</span>";
    intentBannerEl.classList.add("hidden");
    updateCombatCommandShellVisibility();
    return;
  }

  const kind = String(intent.name || intent.type || "Move");
  const telegraph = String(intent.telegraph || "The enemy is hard to read.");
  const hits = Number(intent.hits || 1);
  const mult = Number(intent.damage_mult || 1);
  const counter = String(intent.counter_action || "").trim().toUpperCase();
  const threatScore = (hits * mult);
  const state = lastState || {};
  const enemy = state?.enemy || lastEnemy || {};
  const affix = state?.current_affix || null;
  const learnedMechanics = lastStats?.mechanics_learned || {};
  const eliteVariant = String(enemy?.combat_mods?.elite_variant || "").toLowerCase();
  const bossArchetype = String(enemy?.archetype || "").toLowerCase();
  const isBoss = String(enemy?.tier || "").toLowerCase() === "boss";
  const affixId = String(affix?.id || "").toLowerCase();

  let threat = "safe";
  let threatLabel = "SAFE";
  if (threatScore >= 2.4) {
    threat = "lethal";
    threatLabel = "LETHAL";
  } else if (threatScore >= 1.4) {
    threat = "risky";
    threatLabel = "RISKY";
  }

  if (intentKindEl) intentKindEl.textContent = kind;
  intentThreatEl.textContent = threatLabel;
  intentThreatEl.className = `intent-threat ${threat}`;
  const readCue = counter
    ? `Best: ${counter}`
    : (threat === "lethal" ? "Best: dodge" : (threat === "risky" ? "Best: guard or dodge" : "Best: press"));
  const noveltyBits = [
    isBoss && bossArchetype && !learnedMechanics[`boss_archetype:${bossArchetype}`] ? "NEW BOSS" : "",
    eliteVariant && !learnedMechanics[`elite_variant:${eliteVariant}`] ? "NEW VARIANT" : "",
    affixId && !learnedMechanics[`room_affix:${affixId}`] ? "NEW AFFIX" : "",
  ].filter(Boolean);
  const factChips = [
    `${hits} hit${hits === 1 ? "" : "s"}`,
    `x${mult.toFixed(2)}`,
    counter ? `counter ${counter}` : "",
    readCue,
  ].filter(Boolean);
  intentTextEl.innerHTML = `
    <div class="intent-summary">${factChips.map((fact) => `<span class="mini-chip">${fact}</span>`).join("")}</div>
    ${noveltyBits.length ? `<div class="intent-summary intent-summary-secondary">${noveltyBits.map((bit) => `<span class="mini-chip new">${bit}</span>`).join("")}</div>` : ""}
    <div class="intent-telegraph">${telegraph}</div>
  `;

  intentBannerEl.classList.remove("hidden");
  updateCombatCommandShellVisibility();
}

function renderPlayerCombatCard() {
  if (!playerCombatCard || !lastStats) return;
  const hpPct = Math.max(0, Math.min(100, (Number(lastStats.hp || 0) / Math.max(1, Number(lastStats.max_hp || 1))) * 100));
  const staPct = Math.max(0, Math.min(100, (Number(lastStats.stamina || 0) / Math.max(1, Number(lastStats.max_stamina || 1))) * 100));
  const actionCost = _actionCost(selectedAction);
  const battle = lastStats?.battle || {};
  const rerolls = Number(battle?.rerolls || 0);
  const rerollCap = Number(battle?.reroll_cap || 0);
  const curseCharge = Number(battle?.curse_charge || 0);
  const readyText = Number(lastStats.stamina || 0) >= actionCost
    ? `${String(selectedAction || "basic").toUpperCase()} ready`
    : `Need ${actionCost}`;
  const playerMeta = [
    `ATK ${lastStats.attack}`,
    `DEF ${lastStats.defense}`,
    `LV ${lastStats.level}`,
    `DEPTH ${lastStats.depth}`,
  ].join(" • ");
  const playerStatusSummary = summarizeStatusMap(latestPlayerStatus);
  const playerDetailChips = [
    lastRolledSkillName ? `Roll ${lastRolledSkillName}` : "Roll -",
    `RR ${rerolls}/${rerollCap}`,
    `Curse ${curseCharge.toFixed(2)}`,
    playerStatusSummary ? `Status ${playerStatusSummary}` : "",
  ].filter(Boolean);
  playerCombatCard.innerHTML = `
    <div class="combat-entity-card player">
      <div class="combat-entity-head">
        <div>
          <div class="combat-card-title">You</div>
          <div class="combat-card-subtitle">${playerMeta}</div>
        </div>
        <div class="combat-card-meta">${readyText}</div>
      </div>
      <div class="resource-track-wrap">
        <div class="resource-track-label"><span>HP</span><b>${lastStats.hp} / ${lastStats.max_hp}</b></div>
        <div class="resource-track hp"><span style="width:${hpPct.toFixed(1)}%"></span></div>
      </div>
      <div class="resource-track-wrap">
        <div class="resource-track-label"><span>STA</span><b>${lastStats.stamina} / ${lastStats.max_stamina}</b></div>
        <div class="resource-track stamina"><span style="width:${staPct.toFixed(1)}%"></span></div>
      </div>
      <div class="combat-chip-row matchup-row combat-chip-row-primary">
        <span class="mini-chip emphasis">${readyText}</span>
        <span class="mini-chip">Cost ${actionCost}</span>
        <span class="mini-chip">STA ${lastStats.stamina}</span>
      </div>
      <div class="combat-chip-row combat-chip-row-secondary">${playerDetailChips.map((bit) => `<span class="mini-chip soft">${bit}</span>`).join("")}</div>
    </div>
  `;
}

async function refreshStats() {
  const data = await api("/player/stats");
  if (data.error) return;
  const tradeState = await api("/trade/requests");

  lastStats = data;
  idleStateCache = data.idle || idleStateCache;
  latestGuideState = data.guide || null;
  renderTradeAlert(tradeState || null);
  if (data?.idle?.offline_summary) {
    maybeShowOfflineSummary(data.idle.offline_summary);
  }
  maybeShowGuideModal(latestGuideState);
  const mods = Array.isArray(data.run_modifiers) ? data.run_modifiers : [];
  const modsText = mods.length ? mods.map((m) => m.name).join(", ") : "None";
  const cooldowns = data.action_cooldowns || {};
  const combos = data.combo_windows || {};
  const cdText = Object.keys(cooldowns).length
    ? Object.entries(cooldowns).map(([k, v]) => `${k}:${v}`).join(", ")
    : "None";
  const comboText = Object.keys(combos).length
    ? Object.entries(combos).map(([k, v]) => `${k}:${v}`).join(", ")
    : "None";

  statsEl.innerHTML = `
    <p>Level: ${data.level}</p>
    <p>Depth: ${data.depth}</p>
    <p>EXP: ${data.exp} / ${data.exp_to_next}</p>
    <p>HP: ${data.hp} / ${data.max_hp}</p>
    <p>ATK: ${data.attack}</p>
    <p>DEF: ${data.defense}</p>
    <p>Stamina: ${data.stamina} / ${data.max_stamina}</p>
    <p>Action Streak: ${data.action_streak} (${data.last_action || "none"})</p>
    <p>Cooldowns: ${cdText}</p>
    <p>Combos: ${comboText}</p>
    <p>Run Mods: ${modsText}</p>
    <p>Stat Points: ${data.stat_points}</p>
    <hr />
    <p>STR: ${data.strength}</p>
    <p>DEX: ${data.dexterity} (dodge bonus: ${(data.dodge_bonus * 100).toFixed(0)}%)</p>
    <p>INT: ${data.intelligence}</p>
    <p>VIT: ${data.vitality}</p>
    <p>LUCK: ${data.luck} (loot bonus: ${(data.loot_luck * 100).toFixed(0)}%)</p>
  `;

  equipmentEl.innerHTML = `
    <p>Weapon: ${data.equipment?.weapon ? data.equipment.weapon.name : "None"}</p>
    <p>Armor: ${data.equipment?.armor ? data.equipment.armor.name : "None"}</p>
  `;

  renderStatButtons(data.stat_points);
  updateActionButtons(cooldowns);
  renderPlayerCombatCard();
  renderTopRunContext();
  renderHud();
  if (data?.account?.active) {
    const cur = normalizeAccountName(data.account.active);
    if (accountSelectEl && accountSelectEl.options.length > 0) {
      accountSelectEl.value = cur;
    }
  }
}

function renderStatButtons(points) {
  statButtons.innerHTML = "";

  const stats = [
    ["strength", "STR"],
    ["dexterity", "DEX"],
    ["intelligence", "INT"],
    ["vitality", "VIT"],
    ["luck", "LUCK"],
  ];

  stats.forEach(([key, label]) => {
    const row = document.createElement("div");
    row.style.display = "flex";
    row.style.gap = "8px";
    row.style.marginBottom = "8px";
    row.style.alignItems = "center";

    const txt = document.createElement("span");
    txt.textContent = `${label}`;

    const btn = document.createElement("button");
    btn.textContent = `+1`;
    btn.disabled = points <= 0;
    btn.addEventListener("click", async () => {
      const res = await api(`/player/spend_stat?stat=${key}&amount=1`, { method: "POST" });
      show(res);
    });

    row.appendChild(txt);
    row.appendChild(btn);
    statButtons.appendChild(row);
  });
}

async function loadInventory() {
  const data = await api("/player/stash");
  if (!data || !data.stash) return;

  inventoryEl.innerHTML = "";
  data.stash.forEach((item, i) => {
    const source = item.source === "ai" ? "AI" : "System";
    const li = document.createElement("li");
    li.className = item.rarity || "";
    li.innerHTML = `
      <b>${item.name}</b> (Power: ${item.power}) [${item.slot}] <span class="small">(${source})</span>
      <button data-inspect="${i}">Inspect</button>
      <button data-equip="${i}">Equip</button>
    `;
    inventoryEl.appendChild(li);
  });

  inventoryEl.querySelectorAll("button[data-inspect]").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.getAttribute("data-inspect"));
      const item = data.stash[idx];
      renderItemDetails(item);
    });
  });

  inventoryEl.querySelectorAll("button[data-equip]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const idx = btn.getAttribute("data-equip");
      const res = await api(`/player/equip?stash_index=${idx}`, { method: "POST" });
      show(res);
    });
  });
  updateCombatDetailBlocksVisibility();
}

function stopDodge() {
  if (dodgeInterval) clearInterval(dodgeInterval);
  dodgeInterval = null;
  setDodgeWindowActive(false);
}

function syncDodgeVisuals() {
  if (safeZone) {
    safeZone.style.left = `${currentWindow.leftPct}%`;
    safeZone.style.width = `${currentWindow.widthPct}%`;
  }
  if (marker) {
    marker.style.left = `${markerPos}%`;
  }
  if (dodgeOverlaySafeZoneEl) {
    dodgeOverlaySafeZoneEl.style.left = `${currentWindow.leftPct}%`;
    dodgeOverlaySafeZoneEl.style.width = `${currentWindow.widthPct}%`;
  }
  if (dodgeOverlayMarkerEl) {
    dodgeOverlayMarkerEl.style.left = `${markerPos}%`;
  }
}

function computeSafeZoneWidthPct() {
  // Base width depends on risk
  const risk = parseInt(riskSlider.value, 10);
  let width = Math.max(5, 18 - risk * 2);

  // Player DEX increases width (easier dodge)
  const dexBonus = lastStats ? lastStats.dodge_bonus : 0;
  width = width * (1 + dexBonus); // up to +20%

  // Enemy tier decreases width
  if (lastEnemy) {
    if (lastEnemy.tier === "boss") width *= 0.6;
    else if (lastEnemy.tier === "elite") width *= 0.8;
  }

  // âœ… Boss intent can make dodge harder (higher mult => smaller safe zone)
  if (lastBossIntent && lastBossIntent.dodge_difficulty_mult) {
    const mult = Number(lastBossIntent.dodge_difficulty_mult);
    if (!Number.isNaN(mult) && mult > 0) {
      width *= (1 / mult);
    }
  }

  // Clamp
  width = Math.max(4, Math.min(25, width));
  return width;
}

function startDodge() {
  if (!awaitingEnemyPhase) {
    setDodgeResultText("Attack first. Dodge opens after your action.", true);
    setDodgeUiState("idle", "Locked", "Enemy phase is not active yet.");
    return;
  }

  telemetry.dodge_started += 1;
  emitTelemetry("dodge_started", { total: telemetry.dodge_started });

  stopDodge();

  const risk = parseInt(riskSlider.value, 10);

  const width = computeSafeZoneWidthPct();
  const left = Math.floor(Math.random() * (100 - width));
  currentWindow = { leftPct: left, widthPct: width };

  markerPos = 0;
  markerDir = 1;
  syncDodgeVisuals();
  setDodgeResultText("Running... press Space or click while in the blue zone.", true);
  setDodgeUiState("danger", "Tracking", `Window width ${width.toFixed(1)}%. Wait for the marker to enter.`);
  if (dodgeOverlayHintEl) {
    dodgeOverlayHintEl.textContent = "Press Space or click while the marker is inside the blue zone.";
  }

  // Speed scales with risk + enemy tier
  let speedMs = Math.max(10, 30 - risk * 4);
  if (lastEnemy) {
    if (lastEnemy.tier === "boss") speedMs = Math.max(8, speedMs - 4);
    else if (lastEnemy.tier === "elite") speedMs = Math.max(9, speedMs - 2);
  }

  dodgeInterval = setInterval(() => {
    markerPos += markerDir * 1.2;
    if (markerPos >= 100) { markerPos = 100; markerDir = -1; }
    if (markerPos <= 0) { markerPos = 0; markerDir = 1; }
    syncDodgeVisuals();
    updateDodgeTrackingReadout();
  }, speedMs);
  setDodgeWindowActive(true);
}

async function clickDodge() {
  if (!awaitingEnemyPhase) {
    setDodgeResultText("No enemy attack is pending.", true);
    setDodgeUiState("idle", "Locked", "No incoming enemy action to dodge.");
    return;
  }

  telemetry.dodge_clicked += 1;

  if (!dodgeInterval) {
    setDodgeResultText("Start dodge first!", true);
    setDodgeUiState("idle", "Idle", "Start the dodge slider, then click inside the safe zone.");
    return;
  }

  stopDodge();

  const left = currentWindow.leftPct;
  const right = currentWindow.leftPct + currentWindow.widthPct;

  const success = markerPos >= left && markerPos <= right;
  lastDodgeSuccess = success;

  if (success) {
    telemetry.dodge_success += 1;
  } else {
    telemetry.dodge_fail += 1;
  }
  emitTelemetry("dodge_result", {
    success,
    clicked_total: telemetry.dodge_clicked,
    success_total: telemetry.dodge_success,
    fail_total: telemetry.dodge_fail,
  });

  setDodgeResultText(success ? "Evaded" : "Hit", true);
  if (dodgeResult) {
    dodgeResult.classList.remove("fx-success", "fx-fail");
    void dodgeResult.offsetWidth;
    dodgeResult.classList.add(success ? "fx-success" : "fx-fail");
  }
  if (dodgeOverlayResultEl) {
    dodgeOverlayResultEl.classList.remove("fx-success", "fx-fail");
    void dodgeOverlayResultEl.offsetWidth;
    dodgeOverlayResultEl.classList.add(success ? "fx-success" : "fx-fail");
  }
  setDodgeUiState(
    success ? "success" : "fail",
    success ? "Evaded" : "Hit",
    success
      ? "Clean timing."
      : "Missed the window."
  );
  await enemyPhase(success);
}

async function startDungeon() {
  await startDungeonWithRisk(null);
}

async function playerAttack() {
  const data = await api("/combat/player_attack", { method: "POST" });
  show(data);
}

function computeRecommendedPower(risk) {
  const level = Number(lastStats?.level || 1);
  return Math.round(28 + (risk * 34) + (level * 8) + (risk * level * 3));
}

function calcBossChestChance(risk, lootLuck = 0) {
  const chance = 0.06 + (Number(risk || 0) * 0.03) + (Number(lootLuck || 0) * 0.20) + 0.15;
  return Math.max(0, Math.min(0.95, chance));
}

function calcBossRelicChance(risk) {
  const chance = 0.03 + (Number(risk || 0) * 0.02) + 0.10;
  return Math.max(0, Math.min(0.95, chance));
}

function formatPct(value) {
  return `${(Number(value || 0) * 100).toFixed(0)}%`;
}

function computePlayerPower() {
  if (!lastStats) return 0;
  const atk = Number(lastStats.attack || 0);
  const def = Number(lastStats.defense || 0);
  const hp = Number(lastStats.max_hp || 0);
  const lvl = Number(lastStats.level || 1);
  return Math.round((atk * 2.1) + (def * 1.7) + (hp * 0.22) + (lvl * 9));
}

function getCombatAreaPresets() {
  return [
    { id: 'penumbra', name: 'Penumbra', risk: 0, type: 'combat', level: 1, diffA: 'easy', diffB: 'hard', mod: '-0% Accuracy Rating', lore: 'Entry training ground with low pressure patterns.' },
    { id: 'forest_goo', name: 'Forest of Goo', risk: 1, type: 'combat', level: 10, diffA: 'easy', diffB: 'normal', mod: '+0% Attack Interval', lore: 'Stable area with predictable intents.' },
    { id: 'strange_cave', name: 'Strange Cave', risk: 1, type: 'combat', level: 14, diffA: 'normal', diffB: 'master', mod: '-5% Global Evasion', lore: 'Dense cave fights, harder elite patterns.' },
    { id: 'holy_isles', name: 'Holy Isles', risk: 2, type: 'slayer', level: 24, diffA: 'easy', diffB: 'hard', mod: '+10% Prayer Point Cost', lore: 'Adds support pressure and sustain checks.' },
    { id: 'runic_ruins', name: 'Runic Ruins', risk: 3, type: 'dungeon', level: 34, diffA: 'normal', diffB: 'hard', mod: '-40% Magic Evasion (non-magic)', lore: 'Rune-driven enemies and unstable modifiers.' },
    { id: 'arid_plains', name: 'Arid Plains', risk: 3, type: 'slayer', level: 45, diffA: 'normal', diffB: 'hard', mod: '-20% Auto Eat Efficiency', lore: 'Long skirmishes with attrition pressure.' },
    { id: 'high_lands', name: 'High Lands', risk: 4, type: 'slayer', level: 58, diffA: 'hard', diffB: 'elite', mod: 'Enemies heal every 5 turns', lore: 'Forces burst windows and anti-heal pace.' },
    { id: 'toxic_swamps', name: 'Toxic Swamps', risk: 4, type: 'slayer', level: 68, diffA: 'elite', diffB: 'hard', mod: '+poison chance on enemy attack', lore: 'Status-heavy fights and dodge discipline.' },
    { id: 'desolate_plains', name: 'Desolate Plains', risk: 5, type: 'dungeon', level: 75, diffA: 'hard', diffB: 'elite', mod: '-90% Hitpoint Regeneration', lore: 'Boss-level pressure across full run path.' },
  ];
}

function getRecommendedCombatArea() {
  const power = computePlayerPower();
  const areas = getCombatAreaPresets();
  return [...areas]
    .reverse()
    .find((area) => {
      const rec = computeRecommendedPower(area.risk);
      return power >= (rec - 15);
    }) || areas[0];
}

async function renderAreasTab() {
  const stats = await api('/player/stats');
  if (!stats?.error) {
    lastStats = stats;
  }

  const playerPower = computePlayerPower();
  const level = Number(lastStats?.level || 1);
  const lootLuck = Number(lastStats?.loot_luck || 0);
  const areas = getCombatAreaPresets().map((a) => {
    const recPower = computeRecommendedPower(a.risk);
    const levelOk = level >= a.level;
    const powerOk = playerPower >= recPower;
    const stateClass = levelOk && powerOk ? "ok" : (levelOk ? "warn" : "locked");
    const stateLabel = levelOk && powerOk ? "Ready" : (levelOk ? "Risky" : `Need Lv ${a.level}`);
    const chestChance = formatPct(calcBossChestChance(a.risk, lootLuck));
    const relicChance = formatPct(calcBossRelicChance(a.risk));
    const bestFor = a.type === "dungeon" ? "best relic/chest route" : (a.type === "slayer" ? "best slayer pacing" : "best stable farming");
    const score = (levelOk ? 100 : 0) + (powerOk ? 100 : 0) - Math.abs(playerPower - recPower);
    return { ...a, recPower, levelOk, powerOk, stateClass, stateLabel, chestChance, relicChance, bestFor, score };
  }).sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  const featuredArea = areas[0];
  const readyCount = areas.filter((a) => a.stateClass === "ok").length;
  const dungeonCount = areas.filter((a) => a.type === "dungeon").length;
  const slayerCount = areas.filter((a) => a.type === "slayer").length;

  tabContent.innerHTML = `
    <section class="areas-top-actions compact">
      <article class="areas-top-card featured featured-wide">
        <div class="area-head">
          <h3>Recommended Route</h3>
          <span class="risk-tag ${featuredArea.stateClass}">${featuredArea.stateLabel}</span>
        </div>
        <div class="battle-rule-strip">
          <span>${featuredArea.name}</span>
          <span>Risk ${featuredArea.risk}</span>
          <span>Chest ${featuredArea.chestChance}</span>
          <span>Relic ${featuredArea.relicChance}</span>
        </div>
        <p class="small area-lore">${featuredArea.lore}</p>
        <div class="home-actions">
          <button data-area-start="${featuredArea.risk}" ${featuredArea.levelOk ? '' : 'disabled'} class="accent">Run Recommended</button>
        </div>
      </article>
      <article class="areas-top-card compact-metrics">
        <h3>Route Summary</h3>
        <div class="home-kv"><b>Ready</b><span>${readyCount}</span></div>
        <div class="home-kv"><b>Slayer</b><span>${slayerCount}</span></div>
        <div class="home-kv"><b>Dungeons</b><span>${dungeonCount}</span></div>
        <div class="home-kv"><b>Power</b><span>${playerPower}</span></div>
      </article>
    </section>

    <section class="areas-grid">
      ${areas.map((a) => {
        return `
          <article class="area-card ${a.stateClass}">
            <div class="area-head">
              <h3>${a.name}</h3>
              <span class="risk-tag ${a.stateClass}">${a.stateLabel}</span>
            </div>
            <div class="area-tags">
              <span class="risk-tag">${a.type.toUpperCase()}</span>
              <span class="risk-tag ${a.diffA}">${a.diffA}</span>
              <span class="risk-tag ${a.diffB}">${a.diffB}</span>
            </div>
            <div class="battle-rule-strip compact">
              <span>Lv ${a.level}</span>
              <span>Risk ${a.risk}</span>
              <span>Pow ${a.recPower}</span>
            </div>
            <div class="home-kv"><b>Best For</b><span>${a.bestFor}</span></div>
            <div class="home-kv"><b>Modifier</b><span>${a.mod}</span></div>
            <div class="home-kv"><b>Boss</b><span>${a.chestChance} chest • ${a.relicChance} relic</span></div>
            <p class="small area-lore">${a.lore}</p>
            <button data-area-start="${a.risk}" ${a.levelOk ? '' : 'disabled'} class="accent">Enter</button>
          </article>
        `;
      }).join('')}
    </section>
  `;

  tabContent.querySelectorAll('button[data-area-start]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const risk = Number(btn.getAttribute('data-area-start') || 0);
      await startDungeonWithRisk(risk);
      await setActiveTab("combat");
    });
  });
}

async function renderHomeTab() {
  tabContent.innerHTML = `
    <section class="dashboard-shell">
      <section class="dashboard-top">
        <article class="dashboard-hero">
          <div class="dashboard-hero-head">
            <div>
              <p class="dashboard-kicker">Home Base</p>
              <h3>Loading Dashboard</h3>
            </div>
            <span class="risk-tag fair">Syncing</span>
          </div>
          <div class="dashboard-summary">Loading routes, build state, idle status, and market activity.</div>
        </article>
        <article class="dashboard-focus-card">
          <h3>Next Goal</h3>
          <div class="dashboard-summary">Pulling live progress from your save.</div>
        </article>
      </section>
      <section class="dashboard-lower-grid">
        <article class="home-card">
          <h3>Dashboard</h3>
          <div class="home-summary-line">Loading core game state...</div>
        </article>
      </section>
    </section>
  `;

  const stats = await api("/player/stats");
  if (!stats?.error) {
    lastStats = stats;
  }
  const idle = stats?.idle || idleStateCache || {};
  const objectiveRows = Array.isArray(stats?.objectives?.objectives) ? stats.objectives.objectives : [];
  const idleActivity = idle?.activity || {};
  const idleActive = Boolean(idle?.active);
  const idleLabel = idleActive ? (idleActivity.skill_name || idleActivity.skill || "Idle") : "None";
  const lootLuck = Number(stats?.loot_luck || 0);

  const [stashData, auctionData, tradeState, eventState] = await Promise.all([
    api("/player/stash"),
    api("/auction"),
    api("/trade/requests"),
    api("/events/log?limit=40"),
  ]);
  const stash = Array.isArray(stashData?.stash) ? stashData.stash : [];
  const listings = Array.isArray(auctionData) ? auctionData : [];
  const tradeInbox = Array.isArray(tradeState?.inbox) ? tradeState.inbox : [];
  const tradeOutbox = Array.isArray(tradeState?.outbox) ? tradeState.outbox : [];
  const tradeSummary = tradeState?.summary || {};
  const learnedMechanics = stats?.mechanics_learned || {};
  const guide = stats?.guide || {};
  const guideSteps = Array.isArray(guide?.steps) ? guide.steps : [];
  const nextGuideStep = guide?.next_step || null;
  const guideShow = Boolean(guide?.show);
  const guideCompleted = Number(guide?.completed_count || 0);
  const guideTotal = Number(guide?.total_count || guideSteps.length || 0);
  const mechanicEvents = Array.isArray(eventState?.events)
    ? eventState.events.filter((ev) => String(ev?.title || "").toLowerCase().startsWith("mechanic learned:")).slice(0, 3)
    : [];
  const tradePendingNames = tradeInbox.slice(0, 3).map((row) => String(row?.sender || "")).filter(Boolean);
  const nextTradeExpiry = getNextTradeExpiry(tradeInbox.length ? tradeInbox : tradeOutbox);
  const tradePreviewRows = tradeInbox.slice(0, 2).map((row) => {
    const offered = Array.isArray(row?.items) ? row.items.slice(0, 2).map((item) => item.name).join(", ") : "";
    const requested = Array.isArray(row?.requested_items) ? row.requested_items.slice(0, 2).map((item) => item.name).join(", ") : "";
    return `
      <div class="home-trade-row">
        <div class="home-trade-main">
          <b>${String(row?.sender || "Trade")}</b>
          <span class="small muted">${offered || "Gold only"}${requested ? ` -> ${requested}` : ""}</span>
        </div>
        <span class="risk-tag">${formatTimeRemaining(Number(row?.expires_at || 0))}</span>
      </div>
    `;
  }).join("");

  const power = computePlayerPower();
  const lastRunLootCount = Array.isArray(lastRunResult?.loot) ? lastRunResult.loot.length : 0;
  const areaPresets = [
    { risk: 0, name: "Sunken Approach", diff: "Easy", mod: "None", theme: "Training halls and weak scouts." },
    { risk: 1, name: "Mossbound Halls", diff: "Easy", mod: "None", theme: "Balanced rooms with low pressure." },
    { risk: 2, name: "Shatter Vault", diff: "Normal", mod: "1", theme: "Early elites appear more often." },
    { risk: 3, name: "Ruin Spine", diff: "Hard", mod: "1", theme: "Aggressive intents and tighter dodges." },
    { risk: 4, name: "Bleak Crucible", diff: "Hard", mod: "2", theme: "Punishing rooms with stacked modifiers." },
    { risk: 5, name: "Abyss Crown", diff: "Elite", mod: "2", theme: "Boss-tier pressure across the run." },
  ];

  const riskCards = areaPresets.map((area) => {
    const risk = area.risk;
    const rec = computeRecommendedPower(risk);
    const delta = power - rec;
    const badge = delta >= 20 ? "ready" : (delta >= 0 ? "fair" : "danger");
    const label = delta >= 20 ? "Ready" : (delta >= 0 ? "Risky" : "Underpowered");
    const reqLevel = Math.max(1, 1 + (risk * 4));
    const icon = risk <= 1 ? "???" : (risk <= 3 ? "??" : "??");
    const diffClass = area.diff.toLowerCase();
    const chestChance = formatPct(calcBossChestChance(risk, lootLuck));
    const relicChance = formatPct(calcBossRelicChance(risk));
    const bestFor = risk >= 4 ? "relic push" : (risk >= 2 ? "balanced loot" : "safe leveling");

    return `
      <article class="risk-card">
        <div class="risk-card-head">
          <h3>${icon} ${area.name}</h3>
          <span class="risk-badge ${badge}">${label}</span>
        </div>
        <div class="risk-tags">
          <span class="risk-tag">Risk ${risk}</span>
          <span class="risk-tag ${diffClass}">${area.diff}</span>
        </div>
        <p class="small"><b>Entry:</b> Level ${reqLevel} | <b>Run Mods:</b> ${area.mod}</p>
        <p class="small"><b>Recommended Power:</b> ${rec}</p>
        <p class="small"><b>Boss Chest:</b> ${chestChance} | <b>Boss Relic:</b> ${relicChance}</p>
        <p class="small"><b>Best For:</b> ${bestFor}</p>
        <p class="small"><b>Your Power:</b> ${power}</p>
        <p class="small">${area.theme}</p>
        <button data-risk-start="${risk}" class="accent">Enter</button>
      </article>
    `;
  }).join("");

  const recommendedArea = [...areaPresets]
    .reverse()
    .find((area) => {
      const rec = computeRecommendedPower(area.risk);
      return power >= (rec - 15);
    }) || areaPresets[0];
  const recommendedPower = computeRecommendedPower(recommendedArea.risk);
  const sessionRef = lastState || {};
  const runActive = Boolean(sessionRef?.active || sessionRef?.room_type || sessionRef?.can_leave);
  const runRoom = String(sessionRef?.room_type || "").toLowerCase();
  const runPhaseLabel = sessionRef?.can_leave
    ? "Exit Ready"
    : (runRoom ? runRoom.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase()) : "No Active Run");
  const runDepth = Number(sessionRef?.depth || stats?.depth || 1);
  const currentObjective = objectiveRows.find((obj) => !obj.claimed) || null;
  const activeTradeCount = Number(tradeSummary.pending_inbox || 0) + Number(tradeSummary.pending_outbox || 0);
  const claimableCount = objectiveRows.filter((obj) => obj.claimable).length;
  const summaryChips = [
    `Power ${power}`,
    `Gold ${lastStats?.gold ?? "-"}`,
    `Idle ${idleLabel}`,
    `Claims ${claimableCount}`,
    `Trades ${Number(tradeSummary.pending_inbox || 0)}`,
  ];

  const objectiveHtml = objectiveRows.length
    ? objectiveRows.map((obj) => {
        const pct = Math.max(0, Math.min(100, Number(obj.progress_pct || 0) * 100));
        const rewardBits = [];
        if (Number(obj.reward_gold || 0) > 0) rewardBits.push(`${Number(obj.reward_gold)}g`);
        if (Number(obj.reward_relic || 0) > 0) rewardBits.push(`${Number(obj.reward_relic)} relic`);
        if (Number(obj.reward_chest || 0) > 0) rewardBits.push(`${Number(obj.reward_chest)} chest`);
        if (Number(obj.reward_tonic || 0) > 0) rewardBits.push(`${Number(obj.reward_tonic)} tonic`);
        return `
          <div class="objective-card ${obj.claimable ? "claimable" : ""}">
            <div class="drop-row">
              <span><b>${obj.label || obj.id}</b></span>
              <span class="small">${Math.floor(Number(obj.value || 0))}/${Math.floor(Number(obj.target || 1))}</span>
            </div>
            <div class="xpbar"><div class="xpfill" style="width:${pct.toFixed(1)}%"></div></div>
            <div class="battle-rule-strip compact objective-strip">
              <span>${pct.toFixed(0)}%</span>
              <span>${rewardBits.join(" • ") || "reward"}</span>
            </div>
            <div class="home-actions">
              ${obj.claimed
                ? `<button class="subtle" disabled>Claimed</button>`
                : (obj.claimable
                    ? `<button data-objective-claim="${obj.id}" class="accent">Claim Reward</button>`
                    : `<button class="subtle" disabled>In Progress</button>`)}
            </div>
          </div>
        `;
      }).join("")
    : `<p class="small">No objectives loaded.</p>`;

  tabContent.innerHTML = `
    <section class="dashboard-shell">
      <section class="dashboard-top">
        <article class="dashboard-hero">
          <div class="dashboard-hero-head">
            <div>
              <p class="dashboard-kicker">Home Base</p>
              <h3>${runActive ? "Current Run" : "Choose Your Next Move"}</h3>
            </div>
            <span class="risk-tag ${runActive ? "ready" : "fair"}">${runActive ? runPhaseLabel : recommendedArea.name}</span>
          </div>
          <div class="dashboard-stat-row">
            <span>Lv ${lastStats?.level ?? "-"}</span>
            <span>Depth ${runDepth}</span>
            <span>Power ${power}</span>
            <span>Gold ${lastStats?.gold ?? "-"}</span>
          </div>
          <div class="dashboard-summary">
            ${runActive
              ? `Room ${Number(sessionRef?.room_index ?? 0) + 1} | ${runPhaseLabel} | ${sessionRef?.can_leave ? "Leave now to finish the run." : "Beat the boss to unlock exit."}`
              : `${recommendedArea.theme} This is the best route for your current power and reward pace.`}
          </div>
          <div class="dashboard-actions">
            ${runActive
              ? `<button data-home-nav="combat" class="accent">Resume Run</button>`
              : `<button data-risk-start="${recommendedArea.risk}" class="accent">Start Route</button>`}
            <button data-home-nav="areas" class="subtle">Browse Routes</button>
            <button data-home-nav="skills" class="subtle">Open Build</button>
          </div>
        </article>

        <article class="dashboard-focus-card">
          <h3>Next Goal</h3>
          ${currentObjective
            ? `
              <div class="dashboard-focus-title">${currentObjective.label || currentObjective.id}</div>
              <div class="dashboard-summary">${Math.floor(Number(currentObjective.value || 0))}/${Math.floor(Number(currentObjective.target || 1))} complete</div>
              <div class="xpbar"><div class="xpfill" style="width:${Math.max(0, Math.min(100, Number(currentObjective.progress_pct || 0) * 100)).toFixed(1)}%"></div></div>
              <div class="dashboard-actions">
                ${claimableCount > 0
                  ? `<button data-guide-claim-all="1" class="accent">Claim</button>`
                  : `<button class="subtle" disabled>In Progress</button>`}
                <button data-home-nav="tracker" class="subtle">Tracker</button>
              </div>
            `
            : `
              <div class="dashboard-focus-title">Progress clear</div>
              <div class="dashboard-summary">Objectives are caught up. Push routes, improve your build, or farm resources.</div>
              <div class="dashboard-actions">
                <button data-home-nav="areas" class="subtle">Routes</button>
                <button data-home-nav="codex" class="subtle">Codex</button>
              </div>
            `}
        </article>
      </section>

      <section class="dashboard-destination-grid">
        <article class="destination-card primary">
          <div class="destination-head">
            <h3>Routes</h3>
            <span class="risk-tag">${recommendedArea.diff}</span>
          </div>
          <div class="dashboard-summary">${recommendedArea.name} | Risk ${recommendedArea.risk} | Pow ${power}/${recommendedPower}</div>
          <div class="destination-meta">
            <span>Chest ${formatPct(calcBossChestChance(recommendedArea.risk, lootLuck))}</span>
            <span>Relic ${formatPct(calcBossRelicChance(recommendedArea.risk))}</span>
          </div>
          <div class="dashboard-actions">
            <button data-risk-start="${recommendedArea.risk}" class="accent">${runActive ? "Start New Run" : "Start Route"}</button>
            <button data-home-nav="areas" class="subtle">Browse</button>
          </div>
        </article>

        <article class="destination-card">
          <div class="destination-head">
            <h3>Combat Build</h3>
            <span class="risk-tag">6 Skills</span>
          </div>
          <div class="dashboard-summary">Build your loadout, tune roll odds, and set your mana cap.</div>
          <div class="destination-meta">
            <span>Claims ${claimableCount}</span>
            <span>Depth ${lastStats?.depth ?? "-"}</span>
          </div>
          <div class="dashboard-actions">
            <button data-home-nav="skills" class="accent">Open Build</button>
            <button data-home-nav="combat" class="subtle">Fight View</button>
          </div>
        </article>

        <article class="destination-card">
          <div class="destination-head">
            <h3>Idle</h3>
            <span class="risk-tag">${idleActive ? "Running" : "Idle Off"}</span>
          </div>
          <div class="dashboard-summary">${idleLabel} | ${idleActive ? formatDurationCompact(idleActivity.uptime_sec || 0) : "No active task"}</div>
          <div class="destination-meta">
            <span>Tonic ${Number(lastStats?.resources?.idle_tonic || 0)}</span>
            <span>Cap ${formatDurationCompact(idle?.offline_cap_sec || 0)}</span>
          </div>
          <div class="dashboard-actions">
            <button data-home-nav="woodcutting" class="accent">${idleActive ? "Open Tasks" : "Start Task"}</button>
            <button data-home-offline="1" class="subtle">Offline</button>
          </div>
        </article>

        <article class="destination-card">
          <div class="destination-head">
            <h3>Runes</h3>
            <span class="risk-tag">Power</span>
          </div>
          <div class="dashboard-summary">Manage rune drops, upgrades, and equipped power spikes.</div>
          <div class="destination-meta">
            <span>Essence ${lastStats?.resources?.rune_essence ?? 0}</span>
            <span>Relics ${lastStats?.resources?.rune_relic ?? 0}</span>
          </div>
          <div class="dashboard-actions">
            <button data-home-nav="runes" class="accent">Open Runes</button>
            <button data-home-nav="runecrafting" class="subtle">Craft</button>
          </div>
        </article>

        <article class="destination-card">
          <div class="destination-head">
            <h3>Market</h3>
            <span class="risk-tag">${activeTradeCount > 0 ? `${activeTradeCount} Live` : "Quiet"}</span>
          </div>
          <div class="dashboard-summary">Listings ${listings.length} | Inbox ${Number(tradeSummary.pending_inbox || 0)} | Outbox ${Number(tradeSummary.pending_outbox || 0)}</div>
          <div class="destination-meta">
            <span>Accepted ${Number(tradeSummary.accepted || 0)}</span>
            <span>Next ${nextTradeExpiry > 0 ? formatTimeRemaining(nextTradeExpiry) : "-"}</span>
          </div>
          <div class="dashboard-actions">
            <button data-home-nav="shop" class="${tradeInbox.length ? "accent" : ""}">Open Market</button>
            <button data-home-nav="bank" class="subtle">Stash</button>
          </div>
        </article>

        <article class="destination-card">
          <div class="destination-head">
            <h3>Codex</h3>
            <span class="risk-tag">${Object.keys(learnedMechanics).length}</span>
          </div>
          <div class="dashboard-summary">${mechanicEvents.length ? String(mechanicEvents[0]?.title || "").replace("Mechanic learned: ", "") : "No recent discoveries"}</div>
          <div class="destination-meta">
            <span>Learned ${Object.keys(learnedMechanics).length}</span>
            <span>Recent ${mechanicEvents.length}</span>
          </div>
          <div class="dashboard-actions">
            <button data-home-nav="codex" class="accent">Open Codex</button>
            <button data-home-nav="eventlog" class="subtle">Events</button>
          </div>
        </article>
      </section>

      <section class="dashboard-lower-grid">
        <article class="home-card">
          <h3>Guide</h3>
          <div class="battle-rule-strip compact">
            <span>${guideCompleted}/${guideTotal || 5} complete</span>
            <span>${guideShow ? "Active" : "Hidden"}</span>
          </div>
          ${nextGuideStep
            ? `<div class="home-summary-line"><b>${nextGuideStep.label}</b></div>
               <div class="home-summary-line">${nextGuideStep.detail || ""}</div>`
            : `<div class="home-summary-line">Starter Guide is complete. Push routes, improve your build, and use the codex to learn matchups.</div>`}
          <div class="home-actions">
            ${nextGuideStep
              ? (
                  nextGuideStep.id === "claim_objective" && claimableCount > 0
                    ? `<button data-guide-claim-all="1" class="accent">${nextGuideStep.cta_label || "Claim"}</button>`
                    : `<button data-home-nav="${nextGuideStep.tab || "home"}" class="accent">${nextGuideStep.cta_label || "Open"}</button>`
                )
              : `<button data-home-nav="codex" class="accent">Open Codex</button>`}
            <button data-guide-dismiss="${guideShow ? "1" : "0"}" class="subtle">${guideShow ? "Dismiss" : "Resume"}</button>
          </div>
        </article>

        <article class="home-card">
          <h3>Snapshot</h3>
          <div class="battle-rule-strip compact">
            ${summaryChips.map((chip) => `<span>${chip}</span>`).join("")}
          </div>
          <div class="home-stat-strip">
            <span>Lv ${lastStats?.level ?? "-"}</span>
            <span>Depth ${lastStats?.depth ?? "-"}</span>
            <span>HP ${lastStats?.hp ?? "-"}/${lastStats?.max_hp ?? "-"}</span>
            <span>STA ${lastStats?.stamina ?? "-"}/${lastStats?.max_stamina ?? "-"}</span>
          </div>
        </article>

        <article class="home-card">
          <h3>Objectives</h3>
          <div class="home-actions">
            <button data-objective-claim-all="1" class="accent" ${claimableCount > 0 ? "" : "disabled"}>Claim All (${claimableCount})</button>
          </div>
          ${objectiveHtml}
        </article>

        <article class="home-card">
          <h3>Last Run</h3>
          <div class="battle-rule-strip compact">
            <span>${lastRunResult ? "Completed" : "No run yet"}</span>
            <span>Boss ${lastRunResult ? (lastRunResult.boss_defeated ? "Down" : "Alive") : "-"}</span>
            <span>Loot ${lastRunLootCount}</span>
          </div>
          <div class="home-summary-line">Next depth ${lastRunResult?.next_depth ?? "-"}</div>
        </article>

        <article class="home-card">
          <h3>Trades</h3>
          <div class="battle-rule-strip compact">
            <span>Inbox ${Number(tradeSummary.pending_inbox || 0)}</span>
            <span>Outbox ${Number(tradeSummary.pending_outbox || 0)}</span>
            <span>Accepted ${Number(tradeSummary.accepted || 0)}</span>
          </div>
          <div class="home-summary-line">${tradePendingNames.length ? `Recent ${tradePendingNames.join(", ")}` : "No pending senders."}</div>
          ${tradePreviewRows ? `<div class="home-trade-preview">${tradePreviewRows}</div>` : `<div class="small muted">No pending inbox trades.</div>`}
        </article>
      </section>
    </section>
  `;

  tabContent.querySelectorAll("button[data-risk-start]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const risk = Number(btn.getAttribute("data-risk-start") || 0);
      riskSlider.value = String(risk);
      syncRiskLabel();
      await startDungeonWithRisk(risk);
      await setActiveTab("combat");
    });
  });

  tabContent.querySelectorAll("button[data-home-nav]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const tab = btn.getAttribute("data-home-nav") || "bank";
      await setActiveTab(tab);
    });
  });

  tabContent.querySelector('button[data-home-offline="1"]')?.addEventListener("click", async () => {
    const idleState = await api("/idle/state");
    if (idleState?.error) {
      setDebug(`Offline summary failed: ${idleState.error}`);
      return;
    }
    if (idleState?.summary) {
      showOfflineSummary(idleState.summary);
    } else {
      setDebug("No offline summary available.");
    }
  });

  tabContent.querySelectorAll("button[data-objective-claim]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const objective_id = btn.getAttribute("data-objective-claim") || "";
      if (!objective_id) return;
      const res = await api("/objectives/claim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ objective_id }),
      });
      if (res?.error) setDebug(`Objective claim failed: ${res.error}`);
      else setDebug(`Objective claimed: ${objective_id}`);
      await refreshStats();
      await renderHomeTab();
    });
  });

  tabContent.querySelector('button[data-objective-claim-all="1"]')?.addEventListener("click", async () => {
    const res = await api("/objectives/claim_all", { method: "POST" });
    if (res?.error) setDebug(`Claim all failed: ${res.error}`);
    else setDebug(`Claimed ${res?.claimed_count || 0} objectives.`);
    await refreshStats();
    await renderHomeTab();
  });

  tabContent.querySelector('button[data-guide-claim-all="1"]')?.addEventListener("click", async () => {
    const res = await api("/objectives/claim_all", { method: "POST" });
    if (res?.error) setDebug(`Claim all failed: ${res.error}`);
    else setDebug(`Claimed ${res?.claimed_count || 0} objectives.`);
    await refreshStats();
    await renderHomeTab();
  });

  tabContent.querySelector('button[data-guide-dismiss]')?.addEventListener("click", async (event) => {
    const dismissed = String(event.currentTarget?.getAttribute("data-guide-dismiss") || "1") === "1";
    const res = await api("/guide/dismiss", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dismissed }),
    });
    if (res?.error) setDebug(`Guide update failed: ${res.error}`);
    await refreshStats();
    await renderHomeTab();
  });
}

function renderLockedSkillTab(name, subtitle = "System coming next") {
  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>${name}</h3>
        <p class="small">${subtitle}</p>
        <p class="small">This panel is scaffolded in the Melvor-style shell and will be wired with progression loops next.</p>
      </article>
      <article class="home-card">
        <h3>Current Character Snapshot</h3>
        <div class="home-kv"><b>Level</b><span>${lastStats?.level ?? "-"}</span></div>
        <div class="home-kv"><b>Depth</b><span>${lastStats?.depth ?? "-"}</span></div>
        <div class="home-kv"><b>Gold</b><span>${lastStats?.gold ?? "-"}</span></div>
        <div class="home-kv"><b>Power</b><span>${computePlayerPower()}</span></div>
      </article>
    </section>
  `;
}

async function renderSlayerTab() {
  const state = await api("/slayer/state");
  if (state?.error) {
    tabContent.innerHTML = `<p class="small">Slayer unavailable: ${state.error}</p>`;
    return;
  }

  const task = state.task || {};
  const hasTask = Number(task.remaining || 0) > 0;
  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>Slayer Progress</h3>
        <div class="home-kv"><b>Level</b><span>${state.level}</span></div>
        <div class="home-kv"><b>XP</b><span>${state.xp} / ${state.xp_to_next}</span></div>
        <div class="home-kv"><b>Task Target</b><span>${task.target_label || task.target || "None"}</span></div>
        <div class="home-kv"><b>Remaining</b><span>${task.remaining || 0} / ${task.total || 0}</span></div>
        <div class="home-actions">
          <button data-slayer-new="1" class="accent">New Task</button>
          <button data-slayer-extend="1" ${hasTask ? '' : 'disabled'}>Extend Task</button>
        </div>
      </article>
      <article class="home-card">
        <h3>Unlocked Targets</h3>
        ${(state.targets || []).map((t) => `
          <div class="home-kv">
            <b>${t.label}</b>
            <span>${state.level >= t.unlock ? 'Unlocked' : `Lv ${t.unlock}`}</span>
          </div>
        `).join('')}
      </article>
    </section>
  `;

  tabContent.querySelector('button[data-slayer-new="1"]')?.addEventListener('click', async () => {
    const res = await api('/slayer/new_task', { method: 'POST' });
    if (res?.error) setDebug(`Slayer: ${res.error}`);
    await renderSlayerTab();
    await refreshStats();
  });

  tabContent.querySelector('button[data-slayer-extend="1"]')?.addEventListener('click', async () => {
    const res = await api('/slayer/extend_task?extra=10', { method: 'POST' });
    if (res?.error) setDebug(`Slayer: ${res.error}`);
    await renderSlayerTab();
    await refreshStats();
  });
}

async function renderPrayerTab() {
  const state = await api('/prayer/state');
  if (state?.error) {
    tabContent.innerHTML = `<p class="small">Prayer unavailable: ${state.error}</p>`;
    return;
  }

  const active = String(state.active || '');
  const runes = state.runes || {};
  const book = state.book || {};
  const items = Object.entries(book);

  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>Prayer Control</h3>
        <div class="home-kv"><b>Active</b><span>${active || 'None'}</span></div>
        <div class="home-kv"><b>Air Runes</b><span>${runes.air || 0}</span></div>
        <div class="home-kv"><b>Earth Runes</b><span>${runes.earth || 0}</span></div>
        <div class="home-kv"><b>Mind Runes</b><span>${runes.mind || 0}</span></div>
        <div class="home-actions">
          <button data-prayer-id="" class="subtle">Disable Prayer</button>
        </div>
      </article>
      <article class="home-card">
        <h3>Prayer Book</h3>
        ${items.map(([id, p]) => `
          <div class="rune-card ${active === id ? 'ok' : ''}">
            <div class="rune-card-head">
              <b>${p.name}</b>
              <span class="risk-tag">Lv ${p.unlock}</span>
            </div>
            <p class="small">Consumes: ${p.runes_per_turn} ${p.rune} rune/turn</p>
            <p class="small">Effect: ${p.effect} (${p.value})</p>
            <button data-prayer-id="${id}" class="${active === id ? 'accent' : ''}">${active === id ? 'Active' : 'Activate'}</button>
          </div>
        `).join('')}
      </article>
    </section>
  `;

  tabContent.querySelectorAll('button[data-prayer-id]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const prayer = btn.getAttribute('data-prayer-id') || '';
      const res = await api('/prayer/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prayer }),
      });
      if (res?.error) setDebug(`Prayer: ${res.error}`);
      await renderPrayerTab();
      await refreshStats();
    });
  });
}

// Quick chest-unboxing flourish: one card per rune just pulled from a
// chest, popping in with a short stagger so opening several at once
// (the "Open 10" button) still finishes fast. Rare-and-above results
// get a bigger, brighter "celebratory" pop instead of the plain one so
// a good pull actually reads as a good pull.
const CHEST_REVEAL_CELEBRATORY_RARITIES = new Set(["rare", "epic", "legendary", "mythic", "supreme", "relic"]);
const CHEST_REVEAL_STAGGER_MS = 70;
const CHEST_REVEAL_POP_MS = 480;

function showChestRevealAnimation(runes) {
  const items = Array.isArray(runes) ? runes : [];
  if (!items.length) return;

  const overlay = document.createElement("div");
  overlay.className = "chest-reveal-overlay";
  const grid = document.createElement("div");
  grid.className = "chest-reveal-grid";
  overlay.appendChild(grid);

  items.forEach((rune, i) => {
    const rarity = String(rune?.rarity || "common").toLowerCase();
    const celebratory = CHEST_REVEAL_CELEBRATORY_RARITIES.has(rarity);
    const card = document.createElement("div");
    card.className = `chest-reveal-card ${rarity}${celebratory ? " celebratory" : ""}`;
    card.style.animationDelay = `${i * CHEST_REVEAL_STAGGER_MS}ms`;
    const rarityLabel = document.createElement("div");
    rarityLabel.className = "chest-reveal-rarity";
    rarityLabel.textContent = rarity;
    const nameLabel = document.createElement("div");
    nameLabel.className = "chest-reveal-name";
    nameLabel.textContent = rune?.name || "Rune";
    card.append(rarityLabel, nameLabel);
    grid.appendChild(card);
  });

  document.body.appendChild(overlay);
  overlay.addEventListener("click", () => overlay.remove());
  const totalDuration = CHEST_REVEAL_POP_MS + items.length * CHEST_REVEAL_STAGGER_MS;
  setTimeout(() => overlay.remove(), totalDuration);
}

async function renderRunesTab() {
  const state = await api('/runes/state');
  if (state?.error) {
    tabContent.innerHTML = `<p class="small">Runes unavailable: ${state.error}</p>`;
    return;
  }

  const inv = Array.isArray(state.inventory) ? state.inventory : [];
  const buildRunes = inv.filter((x) => String(x.kind || '') !== 'amplifier');
  const amplifiers = inv.filter((x) => String(x.kind || '') === 'amplifier');
  const ampState = state.amplifier || {};
  const ampEquipped = ampState.equipped || null;
  const ampBonus = Number(ampState.bonus || 0);
  const cap = Number(state?.slots?.capacity || 0);
  const budget = Number(state?.slots?.budget || 0);
  const totalValue = Number(state?.slots?.total_value || 0);
  const equipped = Array.isArray(state?.slots?.equipped) ? state.slots.equipped : [];
  const mods = state.mods || {};
  const chests = Number(state.chests || 0);
  const relics = Number(state.relics || 0);
  const bonusActive = Boolean(state?.slots?.bonus_active || false);

  const rarityOrder = ['common', 'rare', 'epic', 'legendary', 'mythic', 'supreme', 'relic'];
  const upgradeCosts = { common: 1, rare: 2, epic: 4, legendary: 8, mythic: 16, supreme: 28, relic: 45 };
  const infusionCaps = { common: 0, rare: 1, epic: 2, legendary: 4, mythic: 6, supreme: 8, relic: 12 };

  const rarityRows = rarityOrder.map((r) => {
    const count = buildRunes.filter((x) => String(x.rarity || '').toLowerCase() === r).length;
    return `<div class="home-kv"><b>${r}</b><span>${count}</span></div>`;
  }).join('');
  const effectSummary = [
    `ATK +${((mods.attack_mult || 0) * 100).toFixed(1)}%`,
    `DEF +${((mods.defense_mult || 0) * 100).toFixed(1)}%`,
    `Dodge +${((mods.dodge_flat || 0) * 100).toFixed(1)}%`,
    `Lifesteal +${((mods.lifesteal || 0) * 100).toFixed(1)}%`,
  ];

  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>Rune Core</h3>
        <div class="battle-rule-strip">
          <span>Chests ${chests}</span>
          <span>Relics ${relics}</span>
          <span>Slots ${cap}</span>
          <span>Budget ${budget}</span>
          <span>Value ${totalValue}</span>
          <span>Runes ${buildRunes.length}</span>
        </div>
        <div class="battle-rule-strip compact">
          <span>${bonusActive ? 'Overloaded Sigil active' : 'Value budget not full yet'}</span>
          <span>${bonusActive ? 'Crit +5%' : `${budget - totalValue} point(s) remaining`}</span>
        </div>
        <div class="home-actions">
          <button data-runes-open="1" ${chests > 0 ? '' : 'disabled'} class="accent">Open 1 Chest</button>
          <button data-runes-open="10" ${chests >= 10 ? '' : 'disabled'}>Open 10</button>
        </div>
      </article>
      <article class="home-card">
        <h3>Combined Effects</h3>
        <div class="battle-rule-strip compact">
          ${effectSummary.map((line) => `<span>${line}</span>`).join("")}
          <span>Thorns +${((mods.thorns || 0) * 100).toFixed(1)}%</span>
          <span>Amp +${(ampBonus * 100).toFixed(1)}%</span>
        </div>
      </article>
      <article class="home-card">
        <h3>Amplifier</h3>
        <div class="home-kv"><b>Equipped</b><span>${ampEquipped ? ampEquipped.name : 'None'}</span></div>
        <div class="home-kv"><b>Bonus</b><span>+${(ampBonus * 100).toFixed(0)}% rune output</span></div>
        ${amplifiers.length
          ? amplifiers.map((a) => `
            <div class="rune-actions compact">
              <span class="small">${a.name} (+${((a.amp_bonus || 0) * 100).toFixed(0)}%)</span>
              ${a.equipped
                ? `<button data-amp-unequip="1">Unequip</button>`
                : `<button data-amp-equip="${a.id}" class="accent">Equip</button>`}
              <button data-rune-sell="${a.id}" class="warn">Sell</button>
            </div>
          `).join('')
          : `<p class="small muted">Craft amplifiers in the Craft tab.</p>`}
      </article>
    </section>

    <section class="home-grid">
      <article class="home-card">
        <h3>Rune Slots</h3>
        <div class="rune-slot-grid">
          ${Array.from({ length: cap }).map((_, i) => {
            const rid = equipped[i] || '';
            const rune = buildRunes.find((x) => String(x.id || '') === String(rid));
            return `
              <div class="rune-slot-card">
                <b>Slot ${i + 1}</b>
                <div class="rune-slot-name">${rune ? rune.name : 'Empty'}</div>
                <div class="rune-slot-meta">${rune ? `${rune.rarity} • ${(Array.isArray(rune.effects) ? rune.effects.length : 0)} effects` : 'No rune equipped'}</div>
                <button data-rune-unequip="${i}" ${rune ? '' : 'disabled'}>Unequip</button>
              </div>
            `;
          }).join('')}
        </div>
      </article>

      <article class="home-card">
        <h3>Combine Runes (4 -> 1 next rarity)</h3>
        ${rarityRows}
        <div class="rune-actions-list">
          ${['common','rare','epic','legendary','mythic','supreme'].map((r) => `
            <button data-rune-combine="${r}">Combine ${r}</button>
          `).join('')}
        </div>
      </article>
    </section>

    <section class="rune-grid">
      ${buildRunes.map((r) => {
        const rarity = String(r.rarity || 'common').toLowerCase();
        const level = Number(r.upgrade_level || 0);
        const max = Number(r.max_upgrade || 0);
        const baseCost = Number(upgradeCosts[rarity] || 1);
        const nextCost = Math.max(1, Math.floor(baseCost * (1 + (level * 0.85))));
        const infusions = Number(r.relic_infusions || 0);
        const infCap = Number(infusionCaps[rarity] || 0);
        const maxed = level >= max;
        const infMaxed = infusions >= infCap;
        return `
        <article class="rune-card ${r.rarity || ''}">
          <div class="rune-card-head">
            <div>
              <h3>${r.name}</h3>
              <div class="rune-card-sub">+${level} upgrade • ${infusions}/${infCap} infuse</div>
            </div>
            <span class="risk-tag">${r.rarity}</span>
          </div>
          <div class="battle-rule-strip compact">
            <span>${r.source || 'chest'}</span>
            <span>Up ${level}/${max}${maxed ? ' MAX' : ''}</span>
            <span>Next ${maxed ? '-' : `${nextCost} relic`}</span>
            <span>Infuse ${infusions}/${infCap}${infCap > 0 ? '' : ' locked'}</span>
          </div>
          <div class="effect-tags">
            ${(Array.isArray(r.effects) ? r.effects : []).map((e) => `<span class="effect-tag">${e.type}: ${(Number(e.value || 0) * 100).toFixed(1)}%</span>`).join('')}
          </div>
          <div class="rune-actions compact">
            <button data-rune-upgrade="${r.id}" ${maxed ? 'disabled' : ''}>Upgrade</button>
            <button data-rune-infuse="${r.id}" ${infCap <= 0 || infMaxed ? 'disabled' : ''}>Relic Boost</button>
          </div>
          <div class="rune-actions slot-actions">
            ${Array.from({ length: cap }).map((_, idx) => `<button data-rune-equip="${r.id}" data-slot="${idx}">Slot ${idx + 1}</button>`).join('')}
          </div>
          <div class="rune-actions compact">
            <button data-rune-sell="${r.id}" class="warn">Sell</button>
            <button data-rune-dismantle="${r.id}" class="subtle">Dismantle</button>
            <button data-rune-list="${r.id}" class="subtle">List Market</button>
          </div>
        </article>
      `;
      }).join('')}
    </section>
  `;

  tabContent.querySelectorAll('button[data-runes-open]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const count = Number(btn.getAttribute('data-runes-open') || 1);
      const res = await api('/runes/open_chest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count }),
      });
      if (res?.error) {
        setDebug(`Runes: ${res.error}`);
      } else {
        showChestRevealAnimation(res?.runes);
        if (Number(res?.relic_found || 0) > 0) setDebug(`Opened ${count} chest(s), found ${res.relic_found} rune relic(s).`);
        else setDebug(`Opened ${count} chest(s).`);
      }
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-equip]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rune_id = btn.getAttribute('data-rune-equip') || '';
      const slot = Number(btn.getAttribute('data-slot') || 0);
      const res = await api('/runes/equip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rune_id, slot }),
      });
      if (res?.error) setDebug(`Runes: ${res.error}`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-unequip]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const slot = Number(btn.getAttribute('data-rune-unequip') || 0);
      const res = await api('/runes/unequip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot }),
      });
      if (res?.error) setDebug(`Runes: ${res.error}`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-amp-equip]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rune_id = btn.getAttribute('data-amp-equip') || '';
      const res = await api('/runes/amplifier_equip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rune_id }),
      });
      if (res?.error) setDebug(`Amplifier: ${res.error}`);
      else setDebug(`Equipped ${res?.equipped?.name || 'amplifier'}.`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-amp-unequip]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const res = await api('/runes/amplifier_unequip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res?.error) setDebug(`Amplifier: ${res.error}`);
      else setDebug('Amplifier unequipped.');
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-combine]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rarity = btn.getAttribute('data-rune-combine') || 'common';
      const res = await api('/runes/combine_by_rarity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rarity }),
      });
      if (res?.error) setDebug(`Runes: ${res.error}`);
      else if (res?.bonus_tier) setDebug(`Combined 4 ${rarity} runes. Bonus tier proc!`);
      else setDebug(`Combined 4 ${rarity} runes.`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-upgrade]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rune_id = btn.getAttribute('data-rune-upgrade') || '';
      const res = await api('/runes/upgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rune_id }),
      });
      if (res?.error) setDebug(`Rune upgrade: ${res.error}`);
      else setDebug(`Upgraded rune to +${res?.upgraded?.level || '?'} (${res?.upgraded?.cost || 0} relic).`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-infuse]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rune_id = btn.getAttribute('data-rune-infuse') || '';
      const res = await api('/runes/relic_infuse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rune_id }),
      });
      if (res?.error) setDebug(`Relic boost: ${res.error}`);
      else setDebug(`Relic boosted rune (${res?.infused?.infusions || 0}/${res?.infused?.cap || 0}).`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-sell]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rune_id = btn.getAttribute('data-rune-sell') || '';
      const res = await api('/runes/sell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rune_id }),
      });
      if (res?.error) setDebug(`Rune sell: ${res.error}`);
      else setDebug(`Sold rune for ${res?.sold?.value || 0} gold.`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-dismantle]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rune_id = btn.getAttribute('data-rune-dismantle') || '';
      const res = await api('/runes/dismantle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rune_id }),
      });
      if (res?.error) setDebug(`Rune dismantle: ${res.error}`);
      else setDebug(`Dismantled rune (+${res?.dismantled?.relic_gain || 0} relic, +${res?.dismantled?.essence_gain || 0} essence).`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("runes saved");
    });
  });

  tabContent.querySelectorAll('button[data-rune-list]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const rune_id = btn.getAttribute('data-rune-list') || '';
      const raw = prompt('List rune for gold price:', '1500');
      if (raw === null) return;
      const price = Math.floor(Number(raw));
      if (!Number.isFinite(price) || price <= 0) {
        setDebug('Invalid rune list price.');
        return;
      }
      const res = await api('/auction/list_rune', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rune_id, price, allow_item_offers: true }),
      });
      if (res?.error) setDebug(`Rune market list: ${res.error}`);
      else setDebug(`Rune listed for ${price} gold.`);
      await renderRunesTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("market saved");
    });
  });

  tabContent.querySelector('button[data-home-offline="1"]')?.addEventListener("click", () => {
    const summary = idle?.offline_summary || {};
    renderOfflineSummaryModal(summary);
    offlineModalEl?.classList.remove("hidden");
  });
}

async function renderTrackerTab() {
  const data = await api("/tracker/summary");
  if (data?.error) {
    tabContent.innerHTML = `<p class="small">Tracker unavailable: ${data.error}</p>`;
    return;
  }

  const combat = data?.combat || {};
  const idle = data?.idle || {};
  const economy = data?.economy || {};
  const latest = idle?.latest_summary || {};
  const counts = data?.telemetry_counts || {};
  const topCounts = Object.entries(counts)
    .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0))
    .slice(0, 8);

  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>Combat Action Tracker</h3>
        <div class="battle-rule-strip compact">
          <span>Turns ${Number(combat.turns_started || 0)}</span>
          <span>Fails ${Number(combat.action_failed || 0)}</span>
          <span>Fail ${Number(combat.action_fail_rate_pct || 0).toFixed(2)}%</span>
          <span>Dodge ${Number(combat.dodge_success || 0)}/${Number(combat.dodges || 0)}</span>
          <span>Rate ${Number(combat.dodge_success_rate_pct || 0).toFixed(2)}%</span>
        </div>
      </article>

      <article class="home-card">
        <h3>Idle Action Tracker</h3>
        <div class="battle-rule-strip compact">
          <span>${idle.active ? (idle.skill_name || idle.skill || "-") : "None"}</span>
          <span>Up ${idle.active ? formatDurationCompact(idle.uptime_sec || 0) : "-"}</span>
          <span>XP ${Number(idle.xp_per_hour || 0).toFixed(1)}/h</span>
          <span>Gold ${Number(idle.gold_per_hour || 0).toFixed(1)}/h</span>
          <span>Rare ${Number(idle.rare_chance_per_min || 0).toFixed(4)}/m</span>
          <span>Cap ${formatDurationCompact(idle.offline_cap_sec || 0)}</span>
        </div>
      </article>

      <article class="home-card">
        <h3>Economy Snapshot</h3>
        <div class="battle-rule-strip compact">
          <span>Gold ${Number(economy.gold || 0)}</span>
          <span>Stash ${Number(economy.stash_count || 0)}</span>
          <span>Runes ${Number(economy.rune_items || 0)}</span>
          <span>Chests ${Number(economy.arcane_chest || 0)}</span>
          <span>Relics ${Number(economy.rune_relic || 0)}</span>
        </div>
      </article>

      <article class="home-card">
        <h3>Latest Offline Tick</h3>
        <div class="battle-rule-strip compact">
          <span>${latest.skill_name || latest.skill || "-"}</span>
          <span>${formatDurationCompact(latest.elapsed_seconds || 0)}</span>
          <span>XP ${Number(latest.xp_gained || 0)}</span>
          <span>Gold ${Number(latest.gold_gained || 0)}</span>
        </div>
      </article>
    </section>

    <section class="stack-block">
      <h3>Telemetry Counters</h3>
      ${topCounts.length
        ? `<div class="battle-rule-strip compact telemetry-strip">${topCounts.map(([k, v]) => `<span>${k}: ${Number(v || 0)}</span>`).join("")}</div>`
        : `<p class="small muted">--</p>`}
    </section>
  `;
}

async function renderEventLogTab() {
  const data = await api("/events/log?limit=140");
  if (data?.error) {
    tabContent.innerHTML = `<p class="small">Event log unavailable: ${data.error}</p>`;
    return;
  }

  const allEvents = Array.isArray(data?.events) ? data.events : [];
  const kinds = Array.from(new Set(allEvents.map((ev) => String(ev?.kind || "system")))).sort();
  const severities = Array.from(new Set(allEvents.map((ev) => String(ev?.severity || "info")))).sort();
  tabContent.innerHTML = `
    <section class="stack-block">
      <div class="block-head">
        <h3>Event Log (${Number(data?.total || 0)})</h3>
        <div>
          <button data-events-refresh="1" class="subtle">Refresh</button>
          <button data-events-clear="1" class="warn">Clear</button>
        </div>
      </div>
      <div class="toolbar-row">
        <input data-events-search="1" type="text" placeholder="Search events..." />
        <select data-events-kind="1">
          <option value="all">All Kinds</option>
          ${kinds.map((k) => `<option value="${k}">${k}</option>`).join("")}
        </select>
        <select data-events-severity="1">
          <option value="all">All Severity</option>
          ${severities.map((s) => `<option value="${s}">${s}</option>`).join("")}
        </select>
      </div>
      <div class="combat-log">
        ${allEvents.length
          ? allEvents.map((ev) => `
              <div class="log-line" data-kind="${String(ev?.kind || "system")}" data-severity="${String(ev?.severity || "info")}" data-search="${normalizeText(`${ev?.title || ""} ${ev?.detail || ""} ${ev?.kind || ""} ${ev?.severity || ""}`)}">
                <b>[${formatUnixTs(ev.ts)}]</b> ${ev.title || "Event"} <span class="small">(${ev.kind || "system"} | ${ev.severity || "info"})</span>
                ${ev.detail ? `<div class="small">${ev.detail}</div>` : ""}
              </div>
            `).join("")
          : `<div class="small muted">--</div>`}
      </div>
    </section>
  `;

  tabContent.querySelector('button[data-events-refresh="1"]')?.addEventListener("click", async () => {
    await renderEventLogTab();
  });
  tabContent.querySelector('button[data-events-clear="1"]')?.addEventListener("click", async () => {
    const res = await api("/events/clear", { method: "POST" });
    if (res?.error) setDebug(`Event clear failed: ${res.error}`);
    else setDebug("Event log cleared.");
    await renderEventLogTab();
  });

  const searchEl = tabContent.querySelector('input[data-events-search="1"]');
  const kindEl = tabContent.querySelector('select[data-events-kind="1"]');
  const severityEl = tabContent.querySelector('select[data-events-severity="1"]');
  const applyFilters = () => {
    const q = normalizeText(searchEl?.value || "");
    const kind = normalizeText(kindEl?.value || "all");
    const severity = normalizeText(severityEl?.value || "all");
    tabContent.querySelectorAll(".combat-log .log-line").forEach((line) => {
      const rowKind = normalizeText(line.getAttribute("data-kind") || "system");
      const rowSeverity = normalizeText(line.getAttribute("data-severity") || "info");
      const rowSearch = normalizeText(line.getAttribute("data-search") || "");
      const kindOk = kind === "all" || rowKind === kind;
      const sevOk = severity === "all" || rowSeverity === severity;
      const searchOk = !q || rowSearch.includes(q);
      line.style.display = kindOk && sevOk && searchOk ? "" : "none";
    });
  };
  searchEl?.addEventListener("input", applyFilters);
  kindEl?.addEventListener("change", applyFilters);
  severityEl?.addEventListener("change", applyFilters);
}

async function renderCodexTab() {
  const data = await api("/codex");
  if (data?.error) {
    tabContent.innerHTML = `<p class="small">Codex unavailable: ${data.error}</p>`;
    return;
  }

  const drops = data?.drop_rates || {};
  const battleSkills = Array.isArray(data?.battle_skills) ? data.battle_skills : [];
  const eliteVariants = data?.elite_variants || {};
  const bossArchetypes = data?.boss_archetypes || {};
  const roomAffixes = Array.isArray(data?.room_affixes) ? data.room_affixes : [];
  const supportMechanics = data?.support_mechanics || {};
  const dungeonStructure = data?.dungeon_structure || {};
  const learnedMechanics = data?.mechanics_learned || {};
  const idleSkills = Array.isArray(data?.idle_skills) ? data.idle_skills : [];
  const recipes = Array.isArray(data?.rune_recipes) ? data.rune_recipes : [];
  const mods = Array.isArray(data?.run_modifiers) ? data.run_modifiers : [];

  tabContent.innerHTML = `
    <section class="stack-block">
      <div class="toolbar-row">
        <input data-codex-search="1" type="text" placeholder="Search codex..." />
        <select data-codex-kind="1">
          <option value="all">All Categories</option>
          <option value="drop">Drop Rates</option>
          <option value="battle">Battle Skills</option>
          <option value="enemy">Enemy Mechanics</option>
          <option value="support">Support Rooms</option>
          <option value="structure">Dungeon Structure</option>
          <option value="idle">Idle Skills</option>
          <option value="recipe">Rune Recipes</option>
          <option value="modifier">Run Modifiers</option>
        </select>
      </div>
    </section>

    <section class="home-grid">
      <article class="home-card codex-row" data-kind="drop" data-search="${normalizeText(`drop rate ${drops.dungeon_chest_drop_formula || ""} ${drops.dungeon_relic_drop_formula || ""} ${drops.idle_rare_formula || ""}`)}">
        <h3>Drop Rate Reference</h3>
        <p class="small"><b>Dungeon Chest:</b> ${drops.dungeon_chest_drop_formula || "-"}</p>
        <p class="small"><b>Dungeon Relic:</b> ${drops.dungeon_relic_drop_formula || "-"}</p>
        <p class="small"><b>Idle Rare:</b> ${drops.idle_rare_formula || "-"}</p>
        <p class="small"><b>Combine Bonus:</b> ${
          drops.combine_bonus_chance
            ? Object.entries(drops.combine_bonus_chance).map(([k, v]) => `${k}:${v}`).join(" | ")
            : "-"
        }</p>
      </article>

      <article class="home-card codex-row" data-kind="drop" data-search="${normalizeText(`rune rarity weights ${Object.keys(drops.chest_rarity_weights || {}).join(" ")}`)}">
        <h3>Rune Rarity Weights</h3>
        ${drops.chest_rarity_weights
          ? Object.entries(drops.chest_rarity_weights).map(([k, v]) => `<div class="home-kv"><b>${k}</b><span>${v}</span></div>`).join("")
          : `<p class="small">No rarity weights.</p>`}
      </article>

      <article class="home-card codex-row" data-kind="battle" data-search="${normalizeText(battleSkills.map((s) => `${s.name} ${s.kind} ${s.tags?.join(" ") || ""}`).join(" "))}">
        <h3>Battle Skills (${battleSkills.length})</h3>
        <div class="combat-log">
          ${battleSkills.map((s) => `<div class="log-line"><b>${s.name}</b> | ${s.kind} | mana ${s.mana_cost} | lv ${s.unlock_level}</div>`).join("")}
        </div>
      </article>

      <article class="home-card codex-row" data-kind="idle" data-search="${normalizeText(idleSkills.map((s) => `${s.name} ${s.resource_key}`).join(" "))}">
        <h3>Idle Skills (${idleSkills.length})</h3>
        <div class="combat-log">
          ${idleSkills.map((s) => `<div class="log-line"><b>${s.name}</b> | XP/hr ${Number(s.xp_per_hour || 0).toFixed(1)} | Gold/hr ${Number(s.gold_per_hour || 0).toFixed(1)}</div>`).join("")}
        </div>
      </article>

      <article class="home-card codex-row" data-kind="enemy" data-search="${normalizeText(`${Object.keys(eliteVariants).join(" ")} ${Object.keys(bossArchetypes).join(" ")}`)}">
        <h3>Elite Variants</h3>
        <div class="combat-log">
          ${Object.entries(eliteVariants).map(([arch, rows]) => `
            <div class="log-line"><b>${String(arch).toUpperCase()}</b> | ${(Array.isArray(rows) ? rows : []).map((row) => `${row.name} ${learnedMechanics[`elite_variant:${String(row.id || "").toLowerCase()}`] ? "[Learned]" : "[Unseen]"}: ${row.effect}`).join(" / ")}</div>
          `).join("")}
        </div>
      </article>
    </section>

    <section class="home-grid">
      <article class="home-card codex-row" data-kind="recipe" data-search="${normalizeText(recipes.map((r) => `${r.name} ${r.id}`).join(" "))}">
        <h3>Rune Recipes</h3>
        ${recipes.map((r) => `<div class="home-kv"><b>${r.name}</b><span>Ess ${r.essence_cost} | XP ${r.xp} | Lv ${r.unlock}</span></div>`).join("")}
      </article>
      <article class="home-card codex-row" data-kind="modifier" data-search="${normalizeText(mods.map((m) => `${m.name || m.id} ${m.desc || ""}`).join(" "))}">
        <h3>Run Modifiers</h3>
        <div class="combat-log">
          ${mods.map((m) => `<div class="log-line"><b>${m.name || m.id}</b> ${learnedMechanics[`run_modifier:${String(m.id || "").toLowerCase()}`] ? "[Learned]" : "[Unseen]"} - ${m.desc || ""}</div>`).join("")}
        </div>
      </article>
      <article class="home-card codex-row" data-kind="enemy" data-search="${normalizeText(Object.entries(bossArchetypes).map(([arch, rows]) => `${arch} ${(Array.isArray(rows) ? rows.join(" ") : "")}`).join(" "))}">
        <h3>Boss Archetypes</h3>
        <div class="combat-log">
          ${Object.entries(bossArchetypes).map(([arch, rows]) => `
            <div class="log-line"><b>${String(arch).toUpperCase()}</b> ${learnedMechanics[`boss_archetype:${String(arch || "").toLowerCase()}`] ? "[Learned]" : "[Unseen]"} - ${(Array.isArray(rows) ? rows.join(" | ") : "")}</div>
          `).join("")}
        </div>
      </article>
      <article class="home-card codex-row" data-kind="modifier" data-search="${normalizeText(roomAffixes.map((row) => `${row.name} ${row.effect}`).join(" "))}">
        <h3>Room Affixes</h3>
        <div class="combat-log">
          ${roomAffixes.map((row) => `<div class="log-line"><b>${row.name}</b> ${learnedMechanics[`room_affix:${String(row.id || "").toLowerCase()}`] ? "[Learned]" : "[Unseen]"} - ${row.effect || ""}</div>`).join("")}
        </div>
      </article>
      <article class="home-card codex-row" data-kind="support" data-search="${normalizeText(Object.entries(supportMechanics).map(([kind, rows]) => `${kind} ${(Array.isArray(rows) ? rows.map((row) => `${row.name} ${row.effect}`).join(" ") : "")}`).join(" "))}">
        <h3>Support Rooms</h3>
        <div class="combat-log">
          ${Object.entries(supportMechanics).map(([kind, rows]) => `
            <div class="log-line"><b>${String(kind).toUpperCase()}</b> | ${(Array.isArray(rows) ? rows : []).map((row) => `${row.name} ${learnedMechanics[`support_${String(kind).toLowerCase()}:${String(row.id || "").toLowerCase()}`] ? "[Learned]" : "[Unseen]"}: ${row.effect}`).join(" / ")}</div>
          `).join("")}
        </div>
      </article>
      <article class="home-card codex-row" data-kind="structure" data-search="${normalizeText(`${(Array.isArray(dungeonStructure?.room_types) ? dungeonStructure.room_types.map((row) => `${row.name} ${row.effect}`).join(" ") : "")} ${(Array.isArray(dungeonStructure?.cadence) ? dungeonStructure.cadence.map((row) => `${row.name} ${row.effect}`).join(" ") : "")}`)}">
        <h3>Dungeon Structure</h3>
        <div class="combat-log">
          ${(Array.isArray(dungeonStructure?.room_types) ? dungeonStructure.room_types : []).map((row) => `<div class="log-line"><b>${row.name}</b> ${learnedMechanics[`room_type:${String(row.id || "").toLowerCase()}`] ? "[Learned]" : "[Unseen]"} - ${row.effect || ""}</div>`).join("")}
          ${(Array.isArray(dungeonStructure?.cadence) ? dungeonStructure.cadence : []).map((row) => `<div class="log-line"><b>${row.name}</b> ${learnedMechanics[`cadence:${String(row.id || "").toLowerCase()}`] ? "[Learned]" : "[Unseen]"} - ${row.effect || ""}</div>`).join("")}
        </div>
      </article>
    </section>
  `;

  const searchEl = tabContent.querySelector('input[data-codex-search="1"]');
  const kindEl = tabContent.querySelector('select[data-codex-kind="1"]');
  const applyFilters = () => {
    const q = normalizeText(searchEl?.value || "");
    const kind = normalizeText(kindEl?.value || "all");
    tabContent.querySelectorAll(".codex-row").forEach((row) => {
      const rowKind = normalizeText(row.getAttribute("data-kind") || "");
      const rowSearch = normalizeText(row.getAttribute("data-search") || "");
      const kindOk = kind === "all" || rowKind === kind;
      const searchOk = !q || rowSearch.includes(q);
      row.style.display = kindOk && searchOk ? "" : "none";
    });
  };
  searchEl?.addEventListener("input", applyFilters);
  kindEl?.addEventListener("change", applyFilters);
}

function initActionButtonsUi() {
  actionButtons.forEach((btn) => {
    const action = btn.dataset.action || "";
    const meta = ACTION_META[action];
    btn.classList.add(`action-${meta?.tone || action}`);
    if (meta?.short) btn.dataset.short = meta.short;
    if (meta?.key) btn.dataset.key = meta.key;
    renderActionButtonContent(btn, meta || { label: action });
  });
}

function clearCombatFxClasses() {
  [playerCombatCard, enemyBox, dodgeBar, dodgeResult].forEach((el) => {
    if (!el) return;
    el.classList.remove("fx-hit", "fx-success", "fx-fail", "fx-glow");
  });
}

function triggerCombatFx(target, kind) {
  if (!target || !kind) return;
  target.classList.remove("fx-hit", "fx-success", "fx-fail", "fx-glow");
  void target.offsetWidth;
  target.classList.add(kind);
}

function spawnCombatFloat(target, text, kind = "neutral") {
  if (!target || !text) return;
  const el = document.createElement("div");
  el.className = `combat-float-text ${kind}`;
  el.textContent = text;
  target.appendChild(el);
  setTimeout(() => {
    el.remove();
  }, 760);
}

function renderCombatFeedback(data) {
  const combat = data?.combat;
  if (!combat || typeof combat !== "object") return;

  const event = String(combat.event || "");
  const damage = Number(combat.damage || 0);
  const dodgeSuccess = combat.dodge_success;

  if (combatFxTimer) {
    clearTimeout(combatFxTimer);
    combatFxTimer = null;
  }
  clearCombatFxClasses();

  if (event === "player_attack") {
    if (damage > 0) {
      triggerCombatFx(enemyBox, "fx-hit");
      triggerCombatFx(enemyBox, "fx-glow");
      spawnCombatFloat(enemyBox, `-${Math.round(damage)}`, "damage");
    } else {
      triggerCombatFx(enemyBox, "fx-fail");
      spawnCombatFloat(enemyBox, "MISS", "miss");
    }
  } else if (event === "enemy_attack") {
    if (typeof dodgeSuccess === "boolean") {
      triggerCombatFx(dodgeBar, dodgeSuccess ? "fx-success" : "fx-fail");
      triggerCombatFx(dodgeResult, dodgeSuccess ? "fx-success" : "fx-fail");
    }
    if (damage > 0) {
      triggerCombatFx(playerCombatCard, "fx-hit");
      spawnCombatFloat(playerCombatCard, `-${Math.round(damage)}`, "damage");
    } else if (dodgeSuccess === true) {
      triggerCombatFx(playerCombatCard, "fx-success");
      spawnCombatFloat(playerCombatCard, "DODGE", "success");
    }
  }

  combatFxTimer = setTimeout(() => {
    clearCombatFxClasses();
    combatFxTimer = null;
  }, 550);
}

function _extractRoomEventsFromResponse(data) {
  const fromState = data?.state?.room_events;
  if (Array.isArray(fromState)) return fromState;
  const direct = data?.room_events;
  if (Array.isArray(direct)) return direct;
  return [];
}

function _roomEventLine(ev) {
  const rt = String(ev?.room_type || "room").toUpperCase();
  const scaleTier = String(ev?.support_scale?.tier || "").toLowerCase();
  const scaleTag = scaleTier ? ` [${scaleTier.replace("_", " ").toUpperCase()}]` : "";
  if (rt === "REST") {
    const restType = String(ev?.rest_type || "standard");
    if (restType === "camp_cache") return `${rt}${scaleTag}: +${Number(ev?.heal || 0)} HP, +${Number(ev?.stamina_restore || 0)} STA, +${Number(ev?.idle_tonic || 0)} tonic${Number(ev?.gold || 0) > 0 ? `, +${Number(ev?.gold || 0)} gold` : ""}`;
    if (restType === "cleanse") return `${rt}${scaleTag}: +${Number(ev?.heal || 0)} HP, +${Number(ev?.stamina_restore || 0)} STA, cleansed`;
    return `${rt}${scaleTag}: +${Number(ev?.heal || 0)} HP, +${Number(ev?.stamina_restore || 0)} STA`;
  }
  if (rt === "TRAP") return ev?.dodged ? `${rt}${scaleTag}: dodged` : `${rt}${scaleTag}: took ${Number(ev?.damage || 0)} dmg`;
  if (rt === "EVENT") {
    const kind = String(ev?.event || "event");
    if (kind === "gold_cache") return `${rt}${scaleTag}: found ${Number(ev?.gold || 0)} gold`;
    if (kind === "ancient_tablet") return `${rt}${scaleTag}: gained ${Number(ev?.exp || 0)} EXP`;
    if (kind === "war_altar") return `${rt}${scaleTag}: +${Number(ev?.stamina_restore || 0)} STA`;
    if (kind === "rune_scraps") return `${rt}${scaleTag}: +${Number(ev?.essence || 0)} essence`;
    if (kind === "battle_trance") return `${rt}${scaleTag}: temporary guard formed`;
    return `${rt}${scaleTag}: ${kind}`;
  }
  if (rt === "TREASURE") {
    return `${rt}${scaleTag}: +${Number(ev?.gold || 0)} gold, +${Number(ev?.essence || 0)} essence${Number(ev?.chests || 0) > 0 ? `, +${Number(ev?.chests || 0)} chest` : ""}`;
  }
  if (rt === "SHRINE") {
    const blessing = String(ev?.blessing || "blessing");
    if (blessing === "healing") return `${rt}${scaleTag}: healing shrine (+${Number(ev?.heal || 0)} HP)`;
    if (blessing === "focus") return `${rt}${scaleTag}: focus shrine (+${Number(ev?.stamina_restore || 0)} STA)`;
    if (blessing === "ward") return `${rt}${scaleTag}: ward shrine (temporary guard)`;
    if (blessing === "vault") return `${rt}${scaleTag}: vault shrine (+${Number(ev?.chests || 0)} chest)`;
    return `${rt}${scaleTag}: rune shrine (+${Number(ev?.relics || 0)} relic)`;
  }
  return `${rt}${scaleTag}: resolved`;
}

function _roomResolutionPayload(ev, stateOverride = null) {
  if (!ev || typeof ev !== "object") return null;
  const rt = String(ev?.room_type || "room").toLowerCase();
  const stateRef = stateOverride || lastState || {};
  const nextType = String(stateRef?.room_type || "").toLowerCase();
  const nextLabel = nextType ? nextType.toUpperCase() : (stateRef?.can_leave ? "Exit Ready" : "--");
  let title = rt.toUpperCase();
  let outcome = "Room complete.";
  let reward = "No bonus.";
  let kind = "neutral";

  if (rt === "rest") {
    title = "Rest Room";
    const restType = String(ev?.rest_type || "standard");
    const scaleTier = String(ev?.support_scale?.tier || "").toLowerCase();
    outcome = `Recovered ${Number(ev?.heal || 0)} HP and ${Number(ev?.stamina_restore || 0)} stamina.${scaleTier ? ` ${scaleTier.replace("_", " ")} support timing.` : ""}`;
    if (restType === "camp_cache") reward = `+${Number(ev?.idle_tonic || 0)} idle tonic`;
    else if (restType === "cleanse") reward = "Negative statuses cleared.";
    else reward = "Tempo reset for the next fight.";
    kind = "safe";
  } else if (rt === "trap") {
    title = "Trap Room";
    outcome = ev?.dodged ? "Avoided the trap." : `Took ${Number(ev?.damage || 0)} damage.`;
    reward = ev?.dodged ? "No damage taken." : "No direct reward.";
    kind = ev?.dodged ? "safe" : "risk";
  } else if (rt === "event") {
    title = "Event Room";
    const kindId = String(ev?.event || "event");
    if (kindId === "gold_cache") {
      outcome = `Found ${Number(ev?.gold || 0)} gold.`;
      reward = `+${Number(ev?.gold || 0)} gold`;
    } else if (kindId === "ancient_tablet") {
      outcome = `Gained ${Number(ev?.exp || 0)} EXP.`;
      reward = `+${Number(ev?.exp || 0)} EXP`;
    } else if (kindId === "rune_scraps") {
      outcome = `Recovered ${Number(ev?.essence || 0)} rune essence from scraps.`;
      reward = `+${Number(ev?.essence || 0)} essence`;
    } else if (kindId === "battle_trance") {
      outcome = `A battle trance wrapped you in guard.`;
      reward = "Temporary guard for upcoming fights";
    } else {
      outcome = `Recovered ${Number(ev?.stamina_restore || 0)} stamina.`;
      reward = `+${Number(ev?.stamina_restore || 0)} stamina`;
    }
    kind = "event";
  } else if (rt === "treasure") {
    title = "Treasure Room";
    outcome = `Looted ${Number(ev?.gold || 0)} gold and ${Number(ev?.essence || 0)} essence.`;
    reward = `Gold ${Number(ev?.gold || 0)} | Essence ${Number(ev?.essence || 0)}${Number(ev?.chests || 0) > 0 ? ` | Chest ${Number(ev?.chests || 0)}` : ""}`;
    kind = "reward";
  } else if (rt === "shrine") {
    title = "Shrine Room";
    const blessing = String(ev?.blessing || "blessing");
    if (blessing === "healing") {
      outcome = `Healing shrine restored ${Number(ev?.heal || 0)} HP.`;
      reward = `+${Number(ev?.heal || 0)} HP`;
    } else if (blessing === "focus") {
      outcome = `Focus shrine restored ${Number(ev?.stamina_restore || 0)} stamina.`;
      reward = `+${Number(ev?.stamina_restore || 0)} stamina`;
    } else if (blessing === "ward") {
      outcome = `Ward shrine granted a defensive blessing.`;
      reward = `Temporary guard`;
    } else if (blessing === "vault") {
      outcome = `Vault shrine opened a hidden cache.`;
      reward = `+${Number(ev?.chests || 0)} chest`;
    } else {
      outcome = `Rune shrine yielded ${Number(ev?.relics || 0)} relic.`;
      reward = `+${Number(ev?.relics || 0)} relic${Number(ev?.relics || 0) === 1 ? "" : "s"}`;
    }
    kind = "reward";
  }

  return { title, outcome, reward, next: nextLabel, kind };
}

function renderRoomEvents(data = null) {
  if (!roomEventsEl) return;
  const events = _extractRoomEventsFromResponse(data || {});
  if (events.length) {
    const stamped = events.map((ev) => ({
      ...ev,
      _roomIndex: Number(data?.state?.room_index ?? lastState?.room_index ?? -1),
      _depth: Number(data?.state?.depth ?? lastState?.depth ?? lastStats?.depth ?? -1),
    }));
    const latest = stamped[stamped.length - 1];
    if (latest) {
      lastRoomResolution = _roomResolutionPayload(latest, data?.state || lastState || {});
    }
    recentRoomEvents = [...stamped.reverse(), ...recentRoomEvents].slice(0, 14);
  }
  if (!recentRoomEvents.length) {
    roomEventsEl.innerHTML = `<div class="small muted">--</div>`;
    updateCombatDetailBlocksVisibility();
    return;
  }
  roomEventsEl.innerHTML = recentRoomEvents.map((ev, idx) => {
    const meta = (ev._depth > 0 && ev._roomIndex >= 0) ? `D${ev._depth} R${ev._roomIndex}` : `#${idx + 1}`;
    return `<div class="log-line"><span class="small">[${meta}]</span> ${_roomEventLine(ev)}</div>`;
  }).join("");
  updateCombatDetailBlocksVisibility();
}

async function renderRunecraftingTab() {
  const state = await api("/runecrafting/state");
  if (state?.error) {
    tabContent.innerHTML = `<p class="small">Runecrafting unavailable: ${state.error}</p>`;
    return;
  }

  const recipes = Array.isArray(state?.recipes) ? state.recipes : [];
  const recipeCards = recipes.map((r) => {
    const locked = !r.unlocked;
    const range = Array.isArray(r.base_yield) ? `${r.base_yield[0]}-${r.base_yield[1]}` : "1-1";
    return `
      <article class="rune-card ${locked ? "locked" : ""}">
        <div class="rune-card-head">
          <h3>${r.name}</h3>
          <span class="risk-tag">Owned: ${r.owned}</span>
        </div>
        <p class="small">Unlock: Lv ${r.unlock}</p>
        <p class="small">Cost: ${r.essence_cost} Essence</p>
        <p class="small">Yield: ${range}</p>
        <p class="small">XP: ${r.xp}</p>
        ${locked
          ? `<p class="small">Locked until Runecrafting ${r.unlock}</p>`
          : `<div class="rune-actions">
              <button data-rune-craft="${r.id}" data-times="1">Craft x1</button>
              <button data-rune-craft="${r.id}" data-times="10" class="accent">Craft x10</button>
            </div>`
        }
      </article>
    `;
  }).join("");

  const ampRecipes = Array.isArray(state?.amplifier_recipes) ? state.amplifier_recipes : [];
  const ampCards = ampRecipes.map((r) => {
    const locked = !r.unlocked;
    return `
      <article class="rune-card ${locked ? "locked" : ""}">
        <div class="rune-card-head">
          <h3>${r.name}</h3>
          <span class="risk-tag">Owned: ${r.owned}</span>
        </div>
        <p class="small">Boosts all equipped rune effects by +${((r.amp_bonus || 0) * 100).toFixed(0)}%</p>
        <p class="small">Unlock: Lv ${r.unlock}</p>
        <p class="small">Cost: ${r.cost_supplies} Supplies + ${r.cost_gold}g</p>
        <p class="small">XP: ${r.xp}</p>
        ${locked
          ? `<p class="small">Locked until Runecrafting ${r.unlock}</p>`
          : `<div class="rune-actions">
              <button data-amp-craft="${r.id}" class="accent">Craft</button>
            </div>`
        }
      </article>
    `;
  }).join("");

  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>Runecrafting</h3>
        <div class="home-kv"><b>Level</b><span>${state.level}</span></div>
        <div class="home-kv"><b>XP</b><span>${state.xp} / ${state.xp_to_next}</span></div>
        <div class="home-kv"><b>Rune Essence</b><span>${state.essence}</span></div>
        <div class="home-kv"><b>Crafted Supplies</b><span>${state.crafted_supplies || 0}</span></div>
        <div class="home-kv"><b>Gold</b><span>${state.gold || 0}</span></div>
      </article>
      <article class="home-card">
        <h3>Rune Bag</h3>
        <div class="rune-list">
          ${Object.keys(state.runes || {}).length
            ? Object.entries(state.runes).map(([k, v]) => `<div class="home-kv"><b>${k}</b><span>${v}</span></div>`).join("")
            : `<p class="small muted">--</p>`
          }
        </div>
      </article>
    </section>
    <section class="rune-grid">
      ${recipeCards}
    </section>
    <section class="home-grid">
      <article class="home-card">
        <h3>Amplifier Runes</h3>
        <p class="small">Forged from crafted supplies (dismantle spare gear and runes). Equip one in the Runes tab to boost your whole rune loadout.</p>
      </article>
    </section>
    <section class="rune-grid">
      ${ampCards}
    </section>
  `;

  tabContent.querySelectorAll("button[data-amp-craft]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const recipe = btn.getAttribute("data-amp-craft") || "";
      const res = await api("/runecrafting/craft_amplifier", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipe }),
      });
      if (res?.error) {
        setDebug(`Amplifier craft failed: ${res.error}`);
      } else {
        setDebug(`Crafted ${res?.crafted?.name || recipe}. Equip it in the Runes tab.`);
      }
      await renderRunecraftingTab();
      await refreshStats();
    });
  });

  tabContent.querySelectorAll("button[data-rune-craft]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const rune = btn.getAttribute("data-rune-craft") || "";
      const times = Number(btn.getAttribute("data-times") || 1);
      const res = await api("/runecrafting/craft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rune, times }),
      });
      if (res?.error) {
        setDebug(`Runecrafting failed: ${res.error}`);
      } else {
        setDebug(`Crafted ${res?.crafted?.amount || 0} ${res?.crafted?.name || rune}.`);
      }
      await renderRunecraftingTab();
      await refreshStats();
    });
  });
}

async function renderSkillsTab() {
  const state = await api("/battle/skills/state");
  if (state?.error) {
    tabContent.innerHTML = `<p class="small">Battle skills unavailable: ${state.error}</p>`;
    return;
  }

  const skills = Array.isArray(state.skills) ? state.skills : [];
  const rollPreview = Array.isArray(state.roll_preview) ? state.roll_preview : skills;
  const catalog = state.catalog || {};
  const masteryCodex = state.mastery_codex || {};
  const masteryMilestones = Array.isArray(state.mastery_milestones) ? state.mastery_milestones : [5, 12, 25];
  const presets = state.presets || {};
  const corePresets = Array.isArray(state.core_presets) ? state.core_presets : [];
  const tree = state.tree || {};
  const treeCfg = state.tree_config || {};
  const manaCap = Number(state.mana_cap || 0);
  const manaUsed = Number(state.mana_used || 0);
  const manaProgress = state.mana_progress || {};
  const rerolls = Number(state.rerolls || 0);
  const rerollCap = Number(state.reroll_cap || 0);
  const curseCharge = Number(state.curse_charge || 0);
  const lastRoll = String(state.last_roll || "none").toUpperCase();
  const calcTreeEffect = (node, level) => {
    const lv = Number(level || 0);
    if (node === "power_training") return `+${(lv * 3).toFixed(0)}% rolled skill damage`;
    if (node === "iron_guard") return `${(lv * 3).toFixed(0)}% enemy damage reduction`;
    if (node === "echo_reroll") return `Reroll cap from echoes: ${1 + Math.min(2, lv)}`;
    if (node === "loaded_slot_one") return `Slot 1 roll weight +${(lv * 18).toFixed(0)}%`;
    if (node === "curse_attunement") return `Cursed roll weight -${(lv * 8).toFixed(0)}%, stronger curse charge`;
    if (node === "affliction_mastery") return `+${(lv * 5).toFixed(0)}% damage while debuffed`;
    return "No effect";
  };

  const catalogOptions = Object.entries(catalog)
    .map(([id, row]) => {
      const name = row?.name || id;
      const kind = row?.kind || "normal";
      const mana = Number(row?.mana_cost || 0);
      const req = Number(row?.unlock_level || 1);
      const unlocked = Boolean(row?.unlocked);
      const lockText = unlocked ? "" : ` | Lv ${req}`;
      return `<option value="${id}" ${unlocked ? "" : "disabled"}>${name} [${kind}] M${mana}${lockText}</option>`;
    })
    .join("");

  const loadoutRows = Array.from({ length: 6 }).map((_, i) => {
    const row = skills[i] || {};
    const sid = String(row.id || "");
    const name = row.name || "Empty";
    const kind = row.kind || "-";
    const mana = Number(row.mana_cost || 0);
    const masteryLevel = Number(row?.mastery?.level || 1).toFixed(1);
    return `
      <div class="battle-slot-card" data-slot-card="${i}">
        <div class="battle-slot-head">
          <b>Slot ${i + 1}</b>
          <span class="risk-tag">${kind}</span>
        </div>
        <div class="battle-slot-name">${name}</div>
        <div class="battle-slot-meta">M${mana} • Mastery ${masteryLevel}</div>
        <select class="idle-tune-input battle-skill-select" data-battle-slot="${i}">
          ${catalogOptions}
        </select>
        <div class="battle-slot-note small muted"></div>
      </div>
    `;
  }).join("");

  const presetLoadouts = {
    starter: ["quick_slash", "cleave", "guard_stance", "focus_channel", "self_bleed", "blank_stumble"],
    striker: ["arc_surge", "cleave", "quick_slash", "guard_stance", "self_bleed", "frail_guard"],
    affliction: ["rupture_strike", "focus_channel", "quick_slash", "guard_stance", "self_bleed", "frail_guard"],
    ...presets,
  };
  const presetLabels = {
    starter: "Starter",
    striker: "Striker",
    affliction: "Affliction",
  };
  const presetOptions = Object.keys(presetLoadouts)
    .sort()
    .map((pid) => `<option value="${pid}">${presetLabels[pid] || pid}</option>`)
    .join("");

  const previewRows = rollPreview.map((r) => {
    const chance = (Number(r.roll_chance || 0) * 100).toFixed(1);
    const m = r?.mastery || {};
    const mLvl = Number(m.level || 1).toFixed(1);
    return `<div class="home-kv"><b>${r.name}</b><span>${chance}% (w=${Number(r.effective_weight || 0).toFixed(2)}) | M${mLvl}</span></div>`;
  }).join("");

  const nodeCards = Object.entries(treeCfg).map(([node, row]) => {
    const lvl = Number(tree[node] || 0);
    const maxLvl = Number(row?.max_level || 1);
    const cost = Math.max(1, Math.round(Number(row?.base_cost_gold || 500) * (Number(row?.cost_mult || 1.7) ** lvl)));
    const statusLabel = lvl >= maxLvl ? "MAXED" : (lvl > 0 ? "ACTIVE" : "LOCKED");
    return `
      <div class="rune-card skill-progression-card">
        <div class="rune-card-head skill-progression-head">
          <h3>${row?.name || node}</h3>
          <span class="risk-tag">${statusLabel}</span>
        </div>
        <div class="home-kv"><b>Level</b><span>${lvl}/${maxLvl}</span></div>
        <p class="small area-lore">${row?.desc || "No description."}</p>
        <div class="skill-progression-effect">${calcTreeEffect(node, lvl)}</div>
        <div class="home-kv"><b>Next Cost</b><span>${lvl >= maxLvl ? "MAX" : `${cost} gold`}</span></div>
        <button data-tree-upgrade="${node}" ${lvl >= maxLvl ? "disabled" : ""}>Upgrade</button>
      </div>
    `;
  }).join("");

  const masteryCards = Object.entries(catalog)
    .sort((a, b) => {
      const ma = Number(masteryCodex?.[a[0]]?.level || 1);
      const mb = Number(masteryCodex?.[b[0]]?.level || 1);
      return mb - ma;
    })
    .map(([sid, row]) => {
      const m = masteryCodex?.[sid] || {};
      const level = Number(m.level || 1).toFixed(1);
      const xp = Number(m.xp || 0);
      const xpToNext = Math.max(1, Number(m.xp_to_next || 100));
      const pct = Math.max(0, Math.min(100, (xp / xpToNext) * 100));
      const tier = Number(m.tier || 0);
      const nextMs = Number(m.next_milestone || masteryMilestones[masteryMilestones.length - 1] || 0);
      const req = Number(row?.unlock_level || 1);
      const unlocked = Boolean(row?.unlocked);
      return `
        <div class="rune-card skill-mastery-card ${unlocked ? "" : "locked"}">
          <div class="rune-card-head skill-progression-head">
            <h3>${row?.name || sid}</h3>
            <span class="risk-tag">${row?.kind || "normal"}</span>
          </div>
          <div class="home-kv"><b>Unlock</b><span>Lv ${req}${unlocked ? "" : " (Locked)"}</span></div>
          <div class="home-kv"><b>Mastery</b><span>Lv ${level} • Tier ${tier}</span></div>
          <div class="resource-track-wrap">
            <div class="resource-track-label"><span>XP</span><b>${xp.toFixed(1)} / ${xpToNext.toFixed(1)}</b></div>
            <div class="resource-track"><span style="width:${pct.toFixed(1)}%"></span></div>
          </div>
          <div class="skill-progression-effect">Next milestone at Lv ${nextMs}</div>
        </div>
      `;
    })
    .join("");

  tabContent.innerHTML = `
    <section class="home-grid">
      <article class="home-card">
        <h3>Battle Loadout</h3>
        <div class="home-kv"><b>Mana</b><span>${manaUsed} / ${manaCap}</span></div>
        <div class="home-kv"><b>Rerolls</b><span>${rerolls} / ${rerollCap}</span></div>
        <div class="home-kv"><b>Curse Charge</b><span>${curseCharge.toFixed(2)}</span></div>
        <div class="home-kv"><b>Last Roll</b><span>${lastRoll}</span></div>
        <div class="home-actions">
          <button data-battle-preset="starter" class="subtle">Starter</button>
          <button data-battle-preset="striker" class="subtle">Striker</button>
          <button data-battle-preset="affliction" class="subtle">Affliction</button>
        </div>
        <div class="home-kv"><b>Presets</b><span><select id="battlePresetSelect" class="idle-tune-input">${presetOptions || '<option value="">none</option>'}</select></span></div>
        <div class="home-kv"><b>Save As</b><span><input id="battlePresetName" class="idle-tune-input" placeholder="my_build" /></span></div>
        <div class="home-actions">
          <button data-battle-preset-apply="1">Apply Preset</button>
          <button data-battle-preset-save="1" class="subtle">Save Preset</button>
          <button data-battle-preset-delete="1" class="warn">Delete Preset</button>
        </div>
        <div class="battle-slot-grid">
          ${loadoutRows}
        </div>
        <div id="battleLoadoutHint" class="battle-loadout-status small muted">Checking current build...</div>
        <div class="home-actions">
          <button data-battle-save-loadout="1" class="accent">Save 6-Skill Loadout</button>
        </div>
      </article>
      <article class="home-card">
        <h3>Mana Cap</h3>
        <div class="home-kv"><b>Current Cap</b><span>${manaCap}</span></div>
        <div class="home-kv"><b>Next Cap</b><span>${Number(manaProgress.next_cap || manaCap)}</span></div>
        <div class="home-kv"><b>Upgrade Cost</b><span>${manaProgress.at_max ? "MAX" : `${Number(manaProgress.next_upgrade_cost || 0)} gold`}</span></div>
        <div class="home-actions">
          <button data-battle-upgrade-cap="1" class="accent" ${manaProgress.at_max ? "disabled" : ""}>Upgrade Mana Cap</button>
        </div>
        <div class="home-kv"><b>Set Cap</b><span><input id="battleManaCapInput" class="idle-tune-input" type="number" min="8" max="50" step="1" value="${manaCap}" /></span></div>
        <div class="home-actions">
          <button data-battle-set-cap="1">Update Mana Cap</button>
        </div>
        <div class="battle-rule-strip">
          <span>4 normal</span>
          <span>2 cursed</span>
          <span>Fit mana cap</span>
        </div>
        <p class="small area-lore">Build exactly 6 battle skills. Stronger skills cost more mana, cursed skills fill the 2 drawback slots, and tree nodes can bias the roll table.</p>
      </article>
    </section>
    <section class="home-grid">
      <article class="home-card">
        <h3>Roll Chance Preview</h3>
        ${previewRows || `<p class="small">No equipped skills.</p>`}
        <p class="small">Preview reflects current tree modifiers and slot weighting.</p>
      </article>
      <article class="home-card">
        <h3>Projected Roll</h3>
        <div id="battleProjectedPreview">
          <p class="small">Change the build to preview roll chances.</p>
        </div>
      </article>
    </section>
    <section class="home-grid">
      <article class="home-card">
        <h3>Skill Tree</h3>
        <p class="small area-lore">Spend gold to tilt rolls, improve damage lines, and add recovery tools. These upgrades shape the deck rather than raising raw stats only.</p>
      </article>
    </section>
    <section class="rune-grid skill-tree-grid">
      ${nodeCards}
    </section>
    <section class="home-grid">
      <article class="home-card">
        <h3>Mastery Codex</h3>
        <p class="small area-lore">Milestones: ${masteryMilestones.join(" / ")}. Every equipped skill grows its own mastery track and eventually gains stronger roll presence or bonuses.</p>
      </article>
    </section>
    <section class="rune-grid mastery-grid">
      ${masteryCards}
    </section>
  `;

  tabContent.querySelectorAll("select[data-battle-slot]").forEach((sel, i) => {
    const sid = String(skills?.[i]?.id || "");
    if (sid) sel.value = sid;
  });

  const setLoadoutHint = (message, tone = "muted") => {
    const hintEl = tabContent.querySelector("#battleLoadoutHint");
    if (!hintEl) return;
    hintEl.className = `battle-loadout-status small ${tone}`;
    hintEl.textContent = message;
  };

  const clearSlotStates = () => {
    tabContent.querySelectorAll(".battle-slot-card").forEach((card) => {
      card.classList.remove("slot-invalid", "slot-warning");
      const note = card.querySelector(".battle-slot-note");
      if (note) note.textContent = "";
    });
  };

  const markSlotState = (idx, message, tone = "invalid") => {
    const card = tabContent.querySelector(`.battle-slot-card[data-slot-card="${idx}"]`);
    if (!card) return;
    card.classList.remove("slot-invalid", "slot-warning");
    card.classList.add(tone === "warning" ? "slot-warning" : "slot-invalid");
    const note = card.querySelector(".battle-slot-note");
    if (note) note.textContent = message;
  };

  const renderProjectedLoadout = () => {
    const previewEl = tabContent.querySelector("#battleProjectedPreview");
    const picks = Array.from(tabContent.querySelectorAll("select[data-battle-slot]")).map((el) => String(el.value || ""));
    const rows = picks.map((id) => catalog[id]).filter((x) => x && typeof x === "object");
    clearSlotStates();
    if (!rows.length) {
      setLoadoutHint("Select skills to preview.", "muted");
      if (previewEl) previewEl.innerHTML = `<p class="small">No selections.</p>`;
      return;
    }

    const normalCount = rows.filter((r) => String(r.kind || "") === "normal").length;
    const cursedCount = rows.filter((r) => String(r.kind || "") === "cursed").length;
    const totalMana = rows.reduce((sum, r) => sum + Number(r?.mana_cost || 0), 0);
    const validCount = picks.length === 6 && !picks.some((x) => !x);
    const duplicates = picks.filter((sid, idx) => sid && picks.indexOf(sid) !== idx);
    const validUnique = duplicates.length === 0;
    const validRole = normalCount === 4 && cursedCount === 2;
    const validMana = totalMana <= manaCap;
    const lockedRows = rows.filter((r) => !Boolean(r?.unlocked));
    const validUnlock = lockedRows.length === 0;
    const valid = validCount && validUnique && validRole && validMana && validUnlock;
    const issues = [];
    if (!validCount) issues.push("choose 6 skills");
    if (!validUnique) issues.push("no duplicates");
    if (!validRole) issues.push("need 4 normal + 2 cursed");
    if (!validMana) issues.push(`mana ${totalMana}/${manaCap}`);
    if (!validUnlock) issues.push("locked skill selected");

    if (valid) setLoadoutHint(`Ready: ${normalCount} normal, ${cursedCount} cursed, mana ${totalMana}/${manaCap}.`, "ready");
    else setLoadoutHint(`Invalid build: ${issues.join(" | ")}`, "locked");

    const roleTargets = [0, 1, 2, 3].reduce((acc, idx) => ({ ...acc, [idx]: "normal" }), {});
    roleTargets[4] = "cursed";
    roleTargets[5] = "cursed";
    picks.forEach((sid, idx) => {
      const row = catalog[sid] || null;
      if (!sid) {
        markSlotState(idx, "Pick a skill", "warning");
        return;
      }
      if (!row) {
        markSlotState(idx, "Unknown skill", "invalid");
        return;
      }
      if (duplicates.includes(sid)) {
        markSlotState(idx, "Duplicate pick", "invalid");
        return;
      }
      if (!Boolean(row?.unlocked)) {
        markSlotState(idx, `Locked until Lv ${Number(row?.unlock_level || 1)}`, "invalid");
        return;
      }
      const expected = roleTargets[idx];
      const actual = String(row?.kind || "");
      if (expected && actual !== expected) {
        markSlotState(idx, expected === "normal" ? "Normal slot only" : "Cursed slot only", "invalid");
        return;
      }
    });
    if (!validMana) {
      const ordered = rows
        .map((row, idx) => ({ idx, mana: Number(row?.mana_cost || 0) }))
        .sort((a, b) => b.mana - a.mana);
      let overflow = totalMana - manaCap;
      ordered.forEach(({ idx, mana }) => {
        if (overflow > 0 && mana > 0) {
          markSlotState(idx, "Too much mana", "warning");
          overflow -= mana;
        }
      });
    }

    const slotOneBonus = Number(tree?.loaded_slot_one || 0);
    const curseTune = Number(tree?.curse_attunement || 0);
    const weighted = picks.map((sid, idx) => {
      const row = catalog[sid] || {};
      let w = Number(row?.base_weight || 1.0);
      if (idx === 0 && slotOneBonus > 0) w *= (1 + (0.18 * slotOneBonus));
      if (String(row?.kind || "") === "cursed" && curseTune > 0) w *= Math.max(0.52, 1 - (0.08 * curseTune));
      return { sid, name: row?.name || sid || "-", w: Math.max(0.05, w) };
    });
    const sum = weighted.reduce((acc, x) => acc + Number(x.w || 0), 0);
    const lines = weighted.map((x) => {
      const chance = sum > 0 ? ((x.w / sum) * 100) : 0;
      return `<div class="home-kv"><b>${x.name}</b><span>${chance.toFixed(1)}% (w=${x.w.toFixed(2)})</span></div>`;
    }).join("");
    if (previewEl) {
      previewEl.innerHTML = lines || `<p class="small">No projected roll data.</p>`;
    }
  };

  tabContent.querySelectorAll("select[data-battle-slot]").forEach((sel) => {
    sel.addEventListener("change", renderProjectedLoadout);
  });

  tabContent.querySelector('button[data-battle-save-loadout="1"]')?.addEventListener("click", async () => {
    const picks = Array.from(tabContent.querySelectorAll("select[data-battle-slot]")).map((el) => String(el.value || ""));
    if (picks.length !== 6 || picks.some((x) => !x)) {
      setLoadoutHint("Invalid build: choose exactly 6 skills.", "locked");
      setDebug("Loadout invalid: choose exactly 6 skills.");
      return;
    }
    const rows = picks.map((id) => catalog[id]).filter((x) => x && typeof x === "object");
    if (rows.length !== 6) {
      setLoadoutHint("Invalid build: unknown skill selected.", "locked");
      setDebug("Loadout invalid: unknown skill selected.");
      return;
    }
    const duplicatePick = picks.find((sid, idx) => sid && picks.indexOf(sid) !== idx);
    if (duplicatePick) {
      const name = String(catalog?.[duplicatePick]?.name || duplicatePick);
      setLoadoutHint(`Invalid build: duplicate skill selected (${name}).`, "locked");
      setDebug(`Loadout invalid: duplicate skill selected (${name}).`);
      return;
    }
    const normalCount = rows.filter((r) => String(r.kind || "") === "normal").length;
    const cursedCount = rows.filter((r) => String(r.kind || "") === "cursed").length;
    const lockedRows = rows.filter((r) => !Boolean(r?.unlocked));
    if (lockedRows.length > 0) {
      const first = lockedRows[0] || {};
      const req = Number(first?.unlock_level || 1);
      setLoadoutHint(`Invalid build: locked skill selected (level ${req}).`, "locked");
      setDebug(`Loadout invalid: locked skill selected (requires level ${req}).`);
      return;
    }
    if (normalCount !== 4 || cursedCount !== 2) {
      setLoadoutHint(`Invalid build: need 4 normal and 2 cursed (${normalCount}/${cursedCount}).`, "locked");
      setDebug(`Loadout invalid: need 4 normal + 2 cursed (got ${normalCount} normal, ${cursedCount} cursed).`);
      return;
    }
    const totalMana = rows.reduce((sum, r) => sum + Number(r?.mana_cost || 0), 0);
    if (totalMana > manaCap) {
      setLoadoutHint(`Invalid build: mana cap exceeded (${totalMana}/${manaCap}).`, "locked");
      setDebug(`Loadout invalid: mana cap exceeded (${totalMana}/${manaCap}).`);
      return;
    }
    const res = await api("/battle/skills/equip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skills: picks }),
    });
    if (res?.error) {
      setLoadoutHint(`Save failed: ${res.error}`, "locked");
      setDebug(`Battle loadout failed: ${res.error}`);
    } else {
      setLoadoutHint("Battle loadout saved.", "ready");
      setDebug("Battle loadout saved.");
    }
    await renderSkillsTab();
    await refreshStats();
    if (!res?.error) await syncProgressSave("skills saved");
  });

  tabContent.querySelectorAll("button[data-battle-preset]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const pid = String(btn.getAttribute("data-battle-preset") || "");
      const preset = presetLoadouts[pid];
      if (!Array.isArray(preset) || preset.length !== 6) return;
      const selects = Array.from(tabContent.querySelectorAll("select[data-battle-slot]"));
      selects.forEach((sel, idx) => {
        sel.value = String(preset[idx] || "");
      });
      renderProjectedLoadout();
      setDebug(`Applied preset: ${pid}. Click Save 6-Skill Loadout.`);
    });
  });

  tabContent.querySelector('button[data-battle-preset-apply="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector("#battlePresetSelect");
    const preset = String(sel?.value || "");
    if (!preset) {
      setDebug("Preset apply failed: select a preset.");
      return;
    }
    const res = await api("/battle/presets/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset }),
    });
    if (res?.error) setDebug(`Preset apply failed: ${res.error}`);
    else setDebug(`Preset applied: ${preset}`);
    await renderSkillsTab();
    await refreshStats();
  });

  tabContent.querySelector('button[data-battle-preset-save="1"]')?.addEventListener("click", async () => {
    const nameEl = tabContent.querySelector("#battlePresetName");
    const sel = tabContent.querySelector("#battlePresetSelect");
    const preset = String(nameEl?.value || sel?.value || "").trim().toLowerCase();
    if (!preset) {
      setDebug("Preset save failed: name required.");
      return;
    }
    const picks = Array.from(tabContent.querySelectorAll("select[data-battle-slot]")).map((el) => String(el.value || ""));
    const res = await api("/battle/presets/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset, skills: picks }),
    });
    if (res?.error) setDebug(`Preset save failed: ${res.error}`);
    else setDebug(`Preset saved: ${preset}`);
    await renderSkillsTab();
    await refreshStats();
    if (!res?.error) await syncProgressSave("preset saved");
  });

  tabContent.querySelector('button[data-battle-preset-delete="1"]')?.addEventListener("click", async () => {
    const sel = tabContent.querySelector("#battlePresetSelect");
    const preset = String(sel?.value || "");
    if (!preset) {
      setDebug("Preset delete failed: select a preset.");
      return;
    }
    const res = await api("/battle/presets/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset }),
    });
    if (res?.error) setDebug(`Preset delete failed: ${res.error}`);
    else setDebug(`Preset deleted: ${preset}`);
    await renderSkillsTab();
    await refreshStats();
  });

  renderProjectedLoadout();

  tabContent.querySelector('button[data-battle-set-cap="1"]')?.addEventListener("click", async () => {
    const input = tabContent.querySelector("#battleManaCapInput");
    const mana_cap = Math.max(8, Math.min(50, Number(input?.value || manaCap)));
    const res = await api("/battle/mana/cap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mana_cap }),
    });
    if (res?.error) {
      setDebug(`Mana cap update failed: ${res.error}`);
    } else {
      setDebug(`Mana cap updated: ${mana_cap}`);
    }
    await renderSkillsTab();
    await refreshStats();
    if (!res?.error) await syncProgressSave("mana saved");
  });

  tabContent.querySelector('button[data-battle-upgrade-cap="1"]')?.addEventListener("click", async () => {
    const res = await api("/battle/mana/upgrade", { method: "POST" });
    if (res?.error) {
      setDebug(`Mana cap upgrade failed: ${res.error}`);
    } else {
      setDebug(`Mana cap upgraded to ${res?.mana_cap || "?"} (cost ${res?.cost || 0} gold).`);
    }
    await renderSkillsTab();
    await refreshStats();
    if (!res?.error) await syncProgressSave("mana saved");
  });

  tabContent.querySelectorAll("button[data-tree-upgrade]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const node = btn.getAttribute("data-tree-upgrade") || "";
      const res = await api("/battle/tree/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node }),
      });
      if (res?.error) {
        setDebug(`Tree upgrade failed: ${res.error}`);
      } else {
        setDebug(`Tree upgraded: ${node} -> Lv ${res?.level || "?"}`);
      }
      await renderSkillsTab();
      await refreshStats();
      if (!res?.error) await syncProgressSave("tree saved");
    });
  });
}

async function renderBankTab() {
  const data = await api("/player/stash");
  const stash = Array.isArray(data?.stash) ? data.stash : [];

  const filtered = stash
    .map((item, idx) => ({ item, idx }))
    .filter((entry) => matchesItemFilters(entry.item, bankFilters));

  const sorted = sortEntries(filtered, bankFilters.sort, "bank");
  if (selectedBankIndex < 0 || selectedBankIndex >= stash.length) {
    selectedBankIndex = sorted.length ? sorted[0].idx : -1;
  }

  const selected = selectedBankIndex >= 0 ? stash[selectedBankIndex] : null;

  tabContent.innerHTML = `
    <section class="bank-shell">
      <div class="bank-toolbar">
        <button data-bank-sort="power_desc">Sort</button>
        <button data-bank-toggle-sell="1" class="${bankSellMode ? "warn" : "subtle"}">${bankSellMode ? "Sell Mode: ON" : "Toggle Sell Mode"}</button>
        <input id="bankSearch" placeholder="Search bank" value="${bankFilters.search || ""}" />
      </div>

      <div class="bank-meta">
        <span>Space: ${stash.length}</span>
        <span>Gold: ${lastStats?.gold ?? "-"}</span>
        <span>Filtered: ${sorted.length}</span>
        <span>${bankFilters.sort === "power_desc" ? "Power sort" : "Rarity sort"}</span>
      </div>

      <div class="bank-layout">
        <div class="bank-grid">
          ${sorted.map(({ item, idx }) => {
            const active = idx === selectedBankIndex ? "active" : "";
            const source = item.source === "ai" ? "AI" : "SYS";
            return `
              <button class="bank-cell ${active} ${item.rarity || ""}" data-bank-pick="${idx}" title="${item.name}
P${item.power} ${item.slot}">
                <span class="risk-tag">${item.rarity || "common"}</span>
                <span class="bank-cell-name">${item.name}</span>
                <span class="bank-cell-meta">P${item.power} | ${item.slot} | ${source}</span>
              </button>
            `;
          }).join("")}
          ${sorted.length === 0 ? `<p class="small">No items match your filters.</p>` : ""}
        </div>

        <aside class="bank-inspector">
          ${selected ? `
            <h3>${selected.name}</h3>
            <div class="battle-rule-strip compact">
              <span>${selected.rarity}</span>
              <span>${selected.slot}</span>
              <span>P${selected.power}</span>
              <span>${selected.source === "ai" ? "AI" : "System"}</span>
            </div>
            <div class="bank-inspector-actions">
              <button data-bank-equip="${selectedBankIndex}">Equip</button>
              <button data-bank-list="${selectedBankIndex}" class="subtle">List</button>
              <button data-bank-inspect="${selectedBankIndex}" class="subtle">Details</button>
              ${bankSellMode ? `<button data-bank-sell="${selectedBankIndex}" class="warn">Sell</button>` : ""}
            </div>
          ` : `<p class="small">No item selected.</p>`}
        </aside>
      </div>
    </section>
  `;

  const search = tabContent.querySelector("#bankSearch");
  search?.addEventListener("input", async () => {
    bankFilters.search = search.value || "";
    await renderBankTab();
  });

  tabContent.querySelector('button[data-bank-sort="power_desc"]')?.addEventListener("click", async () => {
    bankFilters.sort = bankFilters.sort === "power_desc" ? "rarity_desc" : "power_desc";
    await renderBankTab();
  });

  tabContent.querySelector('button[data-bank-toggle-sell="1"]')?.addEventListener("click", async () => {
    bankSellMode = !bankSellMode;
    await renderBankTab();
  });

  tabContent.querySelectorAll("button[data-bank-pick]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      selectedBankIndex = Number(btn.getAttribute("data-bank-pick"));
      await renderBankTab();
    });
  });

  tabContent.querySelectorAll("button[data-bank-equip]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = Number(btn.getAttribute("data-bank-equip"));
      const res = await api(`/player/equip?stash_index=${idx}`, { method: "POST" });
      show(res);
      await renderBankTab();
      if (!res?.error) await syncProgressSave("gear saved");
    });
  });

  tabContent.querySelectorAll("button[data-bank-list]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = Number(btn.getAttribute("data-bank-list"));
      const raw = prompt("List price:", "100");
      if (raw === null) return;
      const price = Number(raw);
      if (!Number.isFinite(price) || price <= 0) {
        setDebug("Invalid price.");
        return;
      }
      const res = await api(`/auction/list?item_index=${idx}&price=${Math.floor(price)}`, { method: "POST" });
      show(res);
      await renderBankTab();
      if (!res?.error) await syncProgressSave("market saved");
    });
  });

  tabContent.querySelectorAll("button[data-bank-inspect]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.getAttribute("data-bank-inspect"));
      renderItemDetails(stash[idx] || null);
    });
  });

  tabContent.querySelectorAll("button[data-bank-sell]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = Number(btn.getAttribute("data-bank-sell"));
      const res = await api(`/player/sell?stash_index=${idx}`, { method: "POST" });
      if (res?.error) {
        setDebug(`Sell failed: ${res.error}`);
      } else {
        setDebug(`Sold ${res?.sold?.name || "item"} for ${res?.sold?.value || 0} gold.`);
      }
      await refreshStats();
      await loadInventory();
      await renderBankTab();
      if (!res?.error) await syncProgressSave("bank saved");
    });
  });
}

async function renderShopTab() {
  const listings = await api("/auction");
  const mineState = await api("/auction/mine");
  const tradeState = await api("/trade/requests");
  latestTradeInboxAt = (Array.isArray(tradeState?.inbox) ? tradeState.inbox : []).reduce((maxTs, row) => {
    const ts = Number(row?.updated_at || row?.created_at || 0);
    return Math.max(maxTs, ts);
  }, 0);
  markTradeInboxSeen();
  renderTradeAlert(tradeState || null);
  lastShopListings = Array.isArray(listings) ? listings : [];
  const myListings = Array.isArray(mineState?.listings) ? mineState.listings : [];
  const tradeInbox = Array.isArray(tradeState?.inbox) ? tradeState.inbox : [];
  const tradeOutbox = Array.isArray(tradeState?.outbox) ? tradeState.outbox : [];
  const tradeHistory = Array.isArray(tradeState?.history) ? tradeState.history : [];
  const tradeTargets = Array.isArray(tradeState?.targets) ? tradeState.targets : [];
  const tradeSummary = tradeState?.summary || {};
  if (!Array.isArray(tradeComposer?.stash) || !tradeComposer.stash.length) {
    const stashData = await api("/player/stash");
    tradeComposer.stash = Array.isArray(stashData?.stash) ? stashData.stash : [];
  }
  const myHistory = mineState?.history || {};
  const mySales = Array.isArray(myHistory?.sales) ? myHistory.sales : [];
  const myTradeCount = Number(myHistory?.total_trades || 0);
  const myTradeGold = Number(myHistory?.total_gold || 0);
  const sellerSummaryHtml = (myListings.length || myTradeCount) ? `
    <section class="stack-block">
      <div class="block-head">
        <h3>Seller Summary</h3>
        <span class="small">${mineState?.account || "account"}</span>
      </div>
      <div class="battle-rule-strip compact telemetry-strip">
        <span>Live ${myListings.length}</span>
        <span>Sales ${myTradeCount}</span>
        <span>Gold ${myTradeGold}</span>
      </div>
      ${mySales.length ? `
        <div class="shop-sales-list">
          ${mySales.slice(0, 6).map((row) => {
            const paid = Number(row?.paid || 0);
            const offerPower = Number(row?.offered_power || 0);
            const method = String(row?.method || "gold");
            const valueText = method === "gold" ? `${paid}g` : `Offer ${offerPower}`;
            return `
              <div class="shop-sale-row">
                <span>${row?.name || "Sale"} • ${valueText}</span>
                <span class="small muted">${method === "gold" ? "Gold" : "Trade"}</span>
              </div>
            `;
          }).join("")}
        </div>
      ` : `<div class="small muted shop-sales-empty">No completed sales yet.</div>`}
    </section>
  ` : "";
  if (!Array.isArray(listings) || listings.length === 0) {
    tabContent.innerHTML = `
      ${renderFilterControls("shop", shopFilters)}
      ${renderTradeComposer(tradeTargets, tradeInbox, tradeOutbox)}
      <section class="stack-block">
        <div class="block-head">
          <h3>Trade Summary</h3>
          <span class="small">${tradeState?.account || "account"}</span>
        </div>
        <div class="battle-rule-strip compact telemetry-strip">
          <span>Inbox ${Number(tradeSummary.pending_inbox || 0)}</span>
          <span>Outbox ${Number(tradeSummary.pending_outbox || 0)}</span>
          <span>Accepted ${Number(tradeSummary.accepted || 0)}</span>
          <span>Expired ${Number(tradeSummary.expired || 0)}</span>
          <span>Closed ${Number(tradeSummary.completed || 0)}</span>
        </div>
      </section>
      ${renderTradeRows("Trade Inbox", tradeInbox, "inbox")}
      ${renderTradeRows("Trade Outbox", tradeOutbox, "outbox")}
      ${renderTradeRows("Recent Trade History", tradeHistory, "history")}
      ${sellerSummaryHtml}
      ${myListings.length ? `
      <section class="stack-block">
        <div class="block-head">
          <h3>My Listings</h3>
          <span class="small">${myListings.length}</span>
        </div>
        <div class="shop-my-listings">
          ${myListings.map((row) => `
            <div class="shop-my-row">
              <span>${(row?.rune?.name || row?.item?.name || "Listing")} • ${row.price}g</span>
              <button data-auction-cancel="${row.id}" class="warn">Cancel</button>
            </div>
          `).join("")}
        </div>
      </section>
      ` : ``}
      <p class="small">No auction listings right now.</p>
    `;
    bindTradeControls();
    return;
  }
  const filtered = listings
    .map((entry, idx) => ({ entry, idx, entity: listingToDisplayItem(entry) }))
    .filter(({ entity }) => matchesItemFilters(entity, shopFilters));
  const sorted = sortEntries(filtered, shopFilters.sort, "shop");
  const { pageItems, totalPages, clampedPage } = paginateEntries(sorted, shopPage);
  shopPage = clampedPage;
  const offerPickerHtml = renderShopOfferPicker();

  tabContent.innerHTML = `
    ${renderFilterControls("shop", shopFilters)}
    ${offerPickerHtml}
    ${renderTradeComposer(tradeTargets, tradeInbox, tradeOutbox)}
    <section class="stack-block">
      <div class="block-head">
        <h3>Trade Summary</h3>
        <span class="small">${tradeState?.account || "account"}</span>
      </div>
      <div class="battle-rule-strip compact telemetry-strip">
        <span>Inbox ${Number(tradeSummary.pending_inbox || 0)}</span>
        <span>Outbox ${Number(tradeSummary.pending_outbox || 0)}</span>
        <span>Accepted ${Number(tradeSummary.accepted || 0)}</span>
        <span>Expired ${Number(tradeSummary.expired || 0)}</span>
        <span>Closed ${Number(tradeSummary.completed || 0)}</span>
      </div>
    </section>
    ${renderTradeRows("Trade Inbox", tradeInbox, "inbox")}
    ${renderTradeRows("Trade Outbox", tradeOutbox, "outbox")}
    ${renderTradeRows("Recent Trade History", tradeHistory, "history")}
    ${sellerSummaryHtml}
    ${myListings.length ? `
    <section class="stack-block">
      <div class="block-head">
        <h3>My Listings</h3>
        <span class="small">${myListings.length}</span>
      </div>
      <div class="shop-my-listings">
        ${myListings.map((row) => `
          <div class="shop-my-row">
            <span>${(row?.rune?.name || row?.item?.name || "Listing")} • ${row.price}g</span>
            <button data-auction-cancel="${row.id}" class="warn">Cancel</button>
          </div>
        `).join("")}
      </div>
    </section>
    ` : ``}
    <section class="shop-summary-strip">
      <span>${sorted.length} listing${sorted.length === 1 ? "" : "s"}</span>
      <span>Page ${shopPage + 1}/${Math.max(1, totalPages)}</span>
      <span>${shopFilters.sort === "power_desc" ? "Power sort" : "Rarity sort"}</span>
    </section>
    <section class="shop-card-grid">
      ${pageItems.map(({ entry: a, idx, entity }) => `
      <article class="shop-card ${entity.rarity || ""}">
        <div class="shop-card-head">
          <div>
            <h3>${entity.name || "Item"}</h3>
            <div class="shop-card-sub">${entity.slot || "-"} • ${entity.kind === "rune" ? "Rune" : (entity.source === "ai" ? "AI" : "System")} • P${entity.power || 0}</div>
          </div>
          <span class="risk-tag">${entity.rarity || "common"}</span>
        </div>
        <div class="battle-rule-strip compact">
          <span>Price ${a.price ?? "?"}</span>
          <span>${String(a.kind || entity.kind || "item").toUpperCase()}</span>
          <span>${a.seller || "player"}</span>
        </div>
        <div class="shop-card-meta">${a.allow_item_offers ? `Barter min power ${Number(a.min_offer_power || 0)}` : "Barter disabled"}</div>
        <div class="shop-card-actions">
          <button data-shop-inspect="${idx}">Inspect</button>
          <button data-auction-buy="${a.id}" class="accent">Buy</button>
          <button data-auction-offer="${a.id}" ${a.allow_item_offers ? "" : "disabled"}>Offer Items</button>
        </div>
      </article>
      `).join("")}
    </section>
    ${sorted.length === 0 ? `<p class="small">No listings match current filters.</p>` : renderPager("shop", shopPage, totalPages)}
  `;

  bindFilterControls("shop", shopFilters, renderShopTab);
  bindPager("shop", shopPage, totalPages, renderShopTab);

  bindTradeControls();

  tabContent.querySelectorAll("button[data-shop-inspect]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.getAttribute("data-shop-inspect"));
      const listing = lastShopListings[idx];
      if (normalizeText(listing?.kind) === "rune") {
        const r = listing?.rune || {};
        const inspect = {
          name: r.name || "Rune",
          rarity: r.rarity || "common",
          slot: "rune",
          power: runePowerScore(r),
          source: "system",
          passives: (Array.isArray(r.effects) ? r.effects : []).map((e) => `${e.type}: ${(Number(e.value || 0) * 100).toFixed(1)}%`),
        };
        renderItemDetails(inspect);
      } else {
        renderItemDetails(listing?.item || null);
      }
    });
  });

  tabContent.querySelectorAll("button[data-auction-buy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const auctionId = btn.getAttribute("data-auction-buy");
      if (!auctionId) return;
      const res = await api(`/auction/buy?auction_id=${encodeURIComponent(auctionId)}`, { method: "POST" });
      if (res?.error) setDebug(`Auction buy failed: ${res.error}`);
      else {
        if (String(shopOfferPicker?.auctionId || "") === String(auctionId)) {
          shopOfferPicker = { auctionId: "", stash: [], selected: [] };
        }
        setDebug(`Purchased listing for ${res?.paid || 0} gold.`);
      }
      await refreshStats();
      await loadInventory();
      await renderShopTab();
      if (!res?.error) await syncProgressSave("market saved");
    });
  });

  tabContent.querySelectorAll("button[data-auction-cancel]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const auctionId = btn.getAttribute("data-auction-cancel");
      if (!auctionId) return;
      const res = await api("/auction/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auction_id: auctionId }),
      });
      if (res?.error) setDebug(`Cancel failed: ${res.error}`);
      else setDebug("Listing cancelled and returned.");
      await refreshStats();
      await loadInventory();
      await renderShopTab();
      if (!res?.error) await syncProgressSave("market saved");
    });
  });

  tabContent.querySelectorAll("button[data-auction-offer]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const auctionId = btn.getAttribute("data-auction-offer");
      if (!auctionId) return;
      const stashData = await api("/player/stash");
      const stash = Array.isArray(stashData?.stash) ? stashData.stash : [];
      shopOfferPicker = { auctionId: String(auctionId), stash, selected: [] };
      await renderShopTab();
    });
  });

  tabContent.querySelectorAll("button[data-offer-pick]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = Number(btn.getAttribute("data-offer-pick"));
      const selected = new Set(Array.isArray(shopOfferPicker?.selected) ? shopOfferPicker.selected : []);
      if (selected.has(idx)) selected.delete(idx);
      else selected.add(idx);
      shopOfferPicker.selected = Array.from(selected).sort((a, b) => a - b);
      await renderShopTab();
    });
  });

  tabContent.querySelector('button[data-offer-clear="1"]')?.addEventListener("click", async () => {
    shopOfferPicker.selected = [];
    await renderShopTab();
  });

  tabContent.querySelector('button[data-offer-cancel="1"]')?.addEventListener("click", async () => {
    shopOfferPicker = { auctionId: "", stash: [], selected: [] };
    await renderShopTab();
  });

  tabContent.querySelector('button[data-offer-inspect-target]')?.addEventListener("click", () => {
    const auctionId = tabContent.querySelector('button[data-offer-inspect-target]')?.getAttribute("data-offer-inspect-target");
    const listing = (Array.isArray(lastShopListings) ? lastShopListings : []).find((x) => String(x?.id || "") === String(auctionId || ""));
    if (!listing) return;
    if (normalizeText(listing?.kind) === "rune") {
      const r = listing?.rune || {};
      renderItemDetails({
        name: r.name || "Rune",
        rarity: r.rarity || "common",
        slot: "rune",
        power: runePowerScore(r),
        source: "system",
        passives: (Array.isArray(r.effects) ? r.effects : []).map((e) => `${e.type}: ${(Number(e.value || 0) * 100).toFixed(1)}%`),
      });
      return;
    }
    renderItemDetails(listing?.item || null);
  });

  tabContent.querySelector('button[data-offer-submit]')?.addEventListener("click", async () => {
    const auctionId = tabContent.querySelector('button[data-offer-submit]')?.getAttribute("data-offer-submit");
    if (!auctionId) return;
    const item_indices = Array.isArray(shopOfferPicker?.selected) ? shopOfferPicker.selected : [];
    if (!item_indices.length) {
      setDebug("Select at least one item for your offer.");
      return;
    }
    const res = await api("/auction/offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auction_id: auctionId, item_indices }),
    });
    if (res?.error) {
      setDebug(`Offer failed: ${res.error}`);
    } else if (res?.accepted) {
      shopOfferPicker = { auctionId: "", stash: [], selected: [] };
      setDebug(`Offer accepted with ${res?.offered_count || 0} item(s).`);
    } else {
      setDebug(`Offer rejected (${res?.offered_power || 0}/${res?.required_offer_power || 0}).`);
    }
    await refreshStats();
    await loadInventory();
    await renderShopTab();
    if (!res?.error && res?.accepted) await syncProgressSave("market saved");
  });
}

async function renderActiveTab() {
  syncActiveTabButtons();
  document.body.dataset.view = activeTab === "combat" ? "combat" : "menu";
  document.body.dataset.menuTab = activeTab === "combat" ? "" : String(activeTab || "home");
  rightPanelEl?.classList.remove("hidden", "combat-collapsed");
  leftPanelEl?.classList.remove("hidden");
  refreshCombatLayoutMode();
  if (activeTab === "combat") {
    collapseCombatPanels();
    hudBarEl?.classList.add("hidden");
    combatView.classList.remove("hidden");
    tabView.classList.add("hidden");
    if (combatView) combatView.style.display = "block";
    if (tabView) tabView.style.display = "none";
    updateActionDockVisibility();
    updateArenaShellVisibility();
    updateCombatToplineVisibility();
    updateCombatMiniNavState();
    updateCombatEmptyStateVisibility();
    return;
  }

  hudBarEl?.classList.add("hidden");
  combatView.classList.add("hidden");
  tabView.classList.remove("hidden");
  if (combatView) combatView.style.display = "none";
  if (tabView) tabView.style.display = "block";
  if (activeTab === "home") {
    rightPanelEl?.classList.add("hidden");
  }
  updateCombatSetupToggle();
  updateCombatDetailsToggle();
  updateCombatUtilityToggle();
  updateActionDockVisibility();
  updateArenaShellVisibility();
  updateCombatToplineVisibility();
  updateCombatMiniNavState();
  updateCombatEmptyStateVisibility();

  if (activeTab === "home") {
    tabTitle.textContent = "Home";
    try {
      await renderHomeTab();
    } catch (error) {
      console.error(error);
      tabContent.innerHTML = `
        <section class="home-grid">
          <article class="home-card">
            <h3>Home</h3>
            <p class="small">Dashboard render failed.</p>
            <p class="small muted">${String(error?.message || error || "Unknown error")}</p>
          </article>
        </section>
      `;
    }
    return;
  }
  if (activeTab === "tracker") {
    tabTitle.textContent = "Action Tracker";
    await renderTrackerTab();
    return;
  }
  if (activeTab === "eventlog") {
    tabTitle.textContent = "Event Log";
    await renderEventLogTab();
    return;
  }
  if (activeTab === "codex") {
    tabTitle.textContent = "Codex";
    await renderCodexTab();
    return;
  }
  if (activeTab === "areas") {
    tabTitle.textContent = "Routes";
    await renderAreasTab();
    return;
  }
  if (activeTab === "skills") {
    tabTitle.textContent = "Skills";
    await renderSkillsTab();
    return;
  }
  if (activeTab === "bank") {
    tabTitle.textContent = "Bank";
    await renderBankTab();
    return;
  }
  if (activeTab === "shop") {
    tabTitle.textContent = "Shop";
    await renderShopTab();
    return;
  }
  if (activeTab === "runecrafting") {
    tabTitle.textContent = "Runecrafting";
    await renderRunecraftingTab();
    return;
  }
  if (activeTab === "runes") {
    tabTitle.textContent = "Runes";
    await renderRunesTab();
    return;
  }
  if (activeTab === "woodcutting") {
    tabTitle.textContent = "Woodcutting";
    await renderIdleTab("woodcutting");
    return;
  }
  if (activeTab === "fishing") {
    tabTitle.textContent = "Fishing";
    await renderIdleTab("fishing");
    return;
  }
  if (activeTab === "mining") {
    tabTitle.textContent = "Mining";
    await renderIdleTab("mining");
    return;
  }
  if (activeTab === "herblore") {
    tabTitle.textContent = "Crafting";
    await renderIdleTab("herblore");
    return;
  }
  if (activeTab === "slayer") {
    tabTitle.textContent = "Slayer";
    await renderSlayerTab();
    return;
  }
  if (activeTab === "prayer") {
    tabTitle.textContent = "Prayer";
    await renderPrayerTab();
    return;
  }
}

async function resolveTurn(useReroll = false) {
  if (awaitingEnemyPhase) {
    setDebug("Enemy phase pending. Complete dodge first.");
    return;
  }

  telemetry.turns_started += 1;
  emitTelemetry("turn_started", { total: telemetry.turns_started, action: selectedAction });

  const data = await api("/combat/player_phase", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: selectedAction, use_reroll: Boolean(useReroll) })
  });

  if (data?.error) {
    telemetry.actions_failed += 1;
    emitTelemetry("action_failed", { total: telemetry.actions_failed, action: selectedAction, error: data?.error || "unknown" });
    const cd = data?.cooldown ? ` | cooldown ${data.cooldown}` : "";
    const req = data?.required ? ` | need ${data.required} stamina` : "";
    setDebug(`Attack failed: ${data.error}${cd}${req}`);
    updateActionButtons(data?.resources?.action_cooldowns || lastStats?.action_cooldowns || {});
    show(data);
    return;
  }

  show(data);
  if (data?.awaiting_enemy_phase) {
    startDodge();
    const rollName = data?.combat?.skill_roll?.name || selectedAction.toUpperCase();
    setDebug(`${useReroll ? "[Reroll] " : ""}Rolled ${rollName}. Dodge now.`);
  } else {
    const rollName = data?.combat?.skill_roll?.name || selectedAction.toUpperCase();
    setDebug(`${useReroll ? "[Reroll] " : ""}Rolled ${rollName}.`);
  }
}

async function enemyPhase(dodgeSuccess = false) {
  const data = await api("/combat/enemy_phase", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dodge_success: Boolean(dodgeSuccess) })
  });

  lastDodgeSuccess = false;
  stopDodge();
  markerPos = 0;
  markerDir = 1;
  if (marker) marker.style.left = "0%";
  setDodgeResultText("Not started.");
  setDodgeUiState("idle", "Idle", "Safe window waiting.");

  if (data?.error) {
    setDodgeResultText("Not started.");
    show(data);
    return;
  }

  setDodgeResultText("Not started.");
  setDodgeUiState("idle", "Idle", "Safe window waiting.");
  show(data);
}

async function enemyAttack() {
  await enemyPhase(lastDodgeSuccess);
}

async function handleDodgeInput() {
  if (!awaitingEnemyPhase) {
    setDodgeResultText("No enemy attack is pending.", true);
    setDodgeUiState("idle", "Locked", "No incoming enemy action to dodge.");
    return;
  }
  if (dodgeInterval) {
    await clickDodge();
  } else {
    await startDodge();
  }
}

async function viewStash() { show(await api("/player/stash")); }
async function prestige() { show(await api("/player/prestige", { method: "POST" })); }
async function leaveDungeon() {
  const data = await api("/dungeon/leave", { method: "POST" });
  if (data?.error) {
    setDebug(`Leave blocked: ${data.error}`);
  } else if (data?.cleared) {
    setDebug("Dungeon completed and exited.");
  }
  show(data);
}

btnStart.addEventListener("click", startDungeon);
btnTurn.addEventListener("click", resolveTurn);
btnReroll?.addEventListener("click", () => resolveTurn(true));
btnPAtk.addEventListener("click", playerAttack);
btnDodgeAction?.addEventListener("click", handleDodgeInput);
btnLeave?.addEventListener("click", leaveDungeon);
btnEAtk.addEventListener("click", enemyAttack);
btnStash.addEventListener("click", viewStash);
btnPrestige.addEventListener("click", prestige);
btnClearLog?.addEventListener("click", () => {
  if (!combatLogEl) return;
  combatLogEl.innerHTML = `<div class="small">Combat log view cleared.</div>`;
});
btnClearDrops?.addEventListener("click", () => {
  recentDrops = [];
  renderRecentDrops({});
});
btnOfflineClose?.addEventListener("click", () => {
  offlineModalEl?.classList.add("hidden");
});
offlineModalEl?.addEventListener("click", (e) => {
  if (e.target === offlineModalEl) {
    offlineModalEl.classList.add("hidden");
  }
});
btnOfflineClaim?.addEventListener("click", async () => {
  const res = await api("/idle/summary/claim", { method: "POST" });
  if (res?.error) {
    setDebug(`Idle summary: ${res.error}`);
  }
  offlineModalEl?.classList.add("hidden");
  await refreshStats();
  if (["woodcutting", "fishing", "mining", "herblore"].includes(activeTab)) {
    await renderActiveTab();
  }
});
btnGuideClose?.addEventListener("click", () => {
  hideGuideModal(true);
});
guideModalEl?.addEventListener("click", (e) => {
  if (e.target === guideModalEl) {
    hideGuideModal(true);
  }
});
btnGuideHide?.addEventListener("click", async () => {
  const res = await api("/guide/dismiss", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dismissed: true }),
  });
  if (res?.error) {
    setDebug(`Guide update failed: ${res.error}`);
  } else {
    latestGuideState = res?.guide || latestGuideState;
  }
  hideGuideModal(true);
  await refreshStats();
  if (activeTab === "home") {
    await renderHomeTab();
  }
});
btnGuidePrimary?.addEventListener("click", async () => {
  hideGuideModal(true);
  await setActiveTab(guideModalActionTab || "home");
});
btnRunClearClose?.addEventListener("click", () => {
  hideRunClearModal();
});
runClearModalEl?.addEventListener("click", (e) => {
  if (e.target === runClearModalEl) {
    hideRunClearModal();
  }
});
btnRunClearHome?.addEventListener("click", async () => {
  hideRunClearModal();
  await setActiveTab("home");
});
btnRunClearContinue?.addEventListener("click", () => {
  hideRunClearModal();
});
btnAccountUse?.addEventListener("click", async () => {
  const selected = accountSelectEl?.value || "";
  await useAccount(selected, false);
});
btnAccountCreate?.addEventListener("click", async () => {
  const name = accountInputEl?.value || "";
  await useAccount(name, true);
  if (accountInputEl) accountInputEl.value = "";
});
btnAccountSave?.addEventListener("click", async () => {
  await saveActiveAccount(false);
});
btnAccountRename?.addEventListener("click", async () => {
  const selected = accountSelectEl?.value || "";
  const newName = accountInputEl?.value || "";
  const payload = {
    account: normalizeAccountName(selected),
    new_name: normalizeAccountName(newName),
  };
  if (!payload.account || !payload.new_name) {
    setDebug("Rename failed: select account and enter a new name.");
    return;
  }
  const res = await api("/account/rename", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res?.error) {
    setDebug(`Rename failed: ${res.error}`);
    await refreshAccountState();
    return;
  }
  renderAccountState(res?.state || null);
  if (accountInputEl) accountInputEl.value = "";
  setDebug(`Account renamed: ${payload.account} -> ${payload.new_name}`);
  await refreshStats();
});
btnAccountDelete?.addEventListener("click", async () => {
  const selected = normalizeAccountName(accountSelectEl?.value || "");
  if (!selected) {
    setDebug("Delete failed: no account selected.");
    return;
  }
  if (!window.confirm(`Delete account "${selected}" permanently?`)) {
    return;
  }
  const res = await api("/account/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account: selected }),
  });
  if (res?.error) {
    setDebug(`Delete failed: ${res.error}`);
    await refreshAccountState();
    return;
  }
  renderAccountState(res?.state || null);
  setDebug(`Deleted account: ${selected}`);
});
accountSelectEl?.addEventListener("change", () => {
  const selected = accountSelectEl?.value || "";
  if (selected) setDebug(`Selected account: ${selected}. Click Use to switch.`);
});
tradeAlertChipEl?.addEventListener("click", async () => {
  await setActiveTab("shop");
});
btnToggleStats?.addEventListener("click", () => {
  if (!statsPanel) return;
  const hidden = statsPanel.classList.contains("hidden");
  if (hidden) {
    statsPanel.classList.remove("hidden");
    btnToggleStats.textContent = "Hide Stats Panel";
  } else {
    statsPanel.classList.add("hidden");
    btnToggleStats.textContent = "Open Stats Panel";
  }
});
actionButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    selectedAction = btn.dataset.action || "basic";
    actionButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderCombatQuickBar();
    setDebug(`Selected action: ${selectedAction.toUpperCase()}`);
  });
});
initActionButtonsUi();
btnAdvanced.addEventListener("click", () => {
  const hidden = advancedControls.classList.contains("hidden");
  if (hidden) {
    advancedControls.classList.remove("hidden");
    btnAdvanced.textContent = "Hide Advanced";
  } else {
    advancedControls.classList.add("hidden");
    btnAdvanced.textContent = "Advanced";
  }
});
tabs.forEach((tab) => {
  tab.addEventListener("click", async () => {
    await setActiveTab(tab.dataset.tab || "home");
  });
});

combatNavButtons.forEach((tab) => {
  tab.addEventListener("click", async () => {
    await setActiveTab(tab.dataset.combatNav || "combat");
  });
});

combatEmptyCtaEl?.addEventListener("click", async () => {
  const risk = Number(combatEmptyCtaEl.dataset.riskStart || "");
  if (Number.isFinite(risk)) {
    await startDungeonWithRisk(risk);
    await setActiveTab("combat");
    return;
  }
  await setActiveTab("areas");
});

combatUtilityToggleEl?.addEventListener("click", () => {
  openCombatOverlay("utility");
});

combatDetailsToggleEl?.addEventListener("click", () => {
  openCombatOverlay("details");
});

combatSetupToggleEl?.addEventListener("click", () => {
  openCombatOverlay("setup");
});

dodgeOverlayEl?.addEventListener("click", async (event) => {
  if (!awaitingEnemyPhase) return;
  if (!(event.target instanceof HTMLElement)) return;
  event.preventDefault();
  await handleDodgeInput();
});

dodgeOverlayActionEl?.addEventListener("click", (event) => {
  event.preventDefault();
  void handleDodgeInput();
});

dodgeOverlayActionEl?.addEventListener("keydown", (event) => {
  if (event.key === " " || event.key === "Enter" || event.key === "Spacebar") {
    event.preventDefault();
    void handleDodgeInput();
  }
});

dodgeOverlayCardEl?.addEventListener("keydown", async (e) => {
  if (!awaitingEnemyPhase) return;
  if (e.repeat) return;
  if (e.key === " " || e.key === "Enter" || e.key === "Spacebar") {
    e.preventDefault();
    await handleDodgeInput();
  }
});

document.addEventListener("keydown", (e) => {
  const isSpace = e.code === "Space" || e.key === " " || e.key === "Spacebar";
  const isTargetInput = ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName || "");
  if (e.repeat) return;
  if (e.key === "Escape" && offlineModalEl && !offlineModalEl.classList.contains("hidden")) {
    offlineModalEl.classList.add("hidden");
    e.preventDefault();
    return;
  }
  if (e.key === "Escape" && guideModalEl && !guideModalEl.classList.contains("hidden")) {
    hideGuideModal(true);
    e.preventDefault();
    return;
  }
  if (e.key === "Escape" && runClearModalEl && !runClearModalEl.classList.contains("hidden")) {
    hideRunClearModal();
    e.preventDefault();
    return;
  }
  if (e.key === "Escape" && activeTab === "combat" && (combatSetupOpen || combatDetailsOpen || combatUtilityOpen)) {
    collapseCombatPanels();
    e.preventDefault();
    return;
  }
  if (activeTab !== "combat") return;
  if (!awaitingEnemyPhase && ["1", "2", "3", "4", "5"].includes(e.key) && !isTargetInput) {
    const next = actionButtons.find((btn) => btn.dataset.key === e.key && !btn.disabled);
    if (next) {
      selectedAction = next.dataset.action || "basic";
      actionButtons.forEach((b) => b.classList.remove("active"));
      next.classList.add("active");
      next.focus();
      renderCombatQuickBar();
      setDebug(`Selected action: ${(ACTION_META[selectedAction]?.label || selectedAction).toUpperCase()}`);
      e.preventDefault();
      return;
    }
  }
  if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
    const enabled = actionButtons.filter((b) => !b.disabled);
    if (!enabled.length) return;
    const currentIdx = enabled.findIndex((b) => (b.dataset.action || "") === selectedAction);
    const step = e.key === "ArrowRight" ? 1 : -1;
    const idx = currentIdx >= 0 ? (currentIdx + step + enabled.length) % enabled.length : 0;
    const next = enabled[idx];
    if (!next) return;
    selectedAction = next.dataset.action || "basic";
    actionButtons.forEach((b) => b.classList.remove("active"));
    next.classList.add("active");
    next.focus();
    setDebug(`Selected action: ${selectedAction.toUpperCase()}`);
    e.preventDefault();
  }

  if (e.key === "Enter" && document.activeElement?.classList?.contains("action-btn")) {
    resolveTurn();
    e.preventDefault();
  }

  if ((isSpace || e.key === "Enter") && awaitingEnemyPhase && !isTargetInput) {
    void handleDodgeInput();
    e.preventDefault();
  }
});

document.addEventListener("click", (event) => {
  if (activeTab !== "combat") return;
  if (!(event.target instanceof HTMLElement)) return;
  if (!combatSetupOpen && !combatDetailsOpen && !combatUtilityOpen) return;
  if (
    event.target.closest("#combatSetupWrap") ||
    event.target.closest("#combatDetailsWrap") ||
    event.target.closest(".right-panel") ||
    event.target.closest("#combatSetupToggle") ||
    event.target.closest("#combatDetailsToggle") ||
    event.target.closest("#combatUtilityToggle")
  ) {
    return;
  }
  collapseCombatPanels();
});

refreshStats();
loadInventory();
renderActiveTab();
refreshAccountState();
if (!autosaveTimer) {
  autosaveTimer = setInterval(() => {
    saveActiveAccount(true);
  }, 120000);
}
api("/ai/status").then(renderAiStatus);
api("/dungeon/state").then(renderCombatLogFromResponse);
renderTurnSummary({});
renderPassiveFeed({});
renderRecentDrops({});
renderRoomEvents({});
syncTurnFlowState({ awaiting_enemy_phase: false });
renderTopRunContext();
renderHud();
renderRollHistory();
setDebug("Loaded tactical flow: Attack -> Auto Dodge -> Enemy attack.");


