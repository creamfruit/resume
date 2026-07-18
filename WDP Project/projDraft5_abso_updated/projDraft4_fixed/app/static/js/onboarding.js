let currentStep = 1;
const totalSteps = 8;
let selectedUserType = null;
let selectedInterests = [];
let selectedTeach = [];
let selectedLearn = [];
let selectedDays = [];
let selectedTimes = [];
let selectedLanguages = [];
let selectedLanguageProficiency = {};
let selectedStations = [];
let selectedLandmarks = [];

const params = new URLSearchParams(window.location.search);
const isEditMode = params.get('edit') === '1';
const editStep = Number(params.get('step') || '0');
const editSection = String(params.get('section') || '').trim().toLowerCase();
const preloaded = window.preloadedOnboarding || {};

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
const interestChips = document.querySelectorAll('#step-2 .interest-chip[data-interest]');
const teachChips = document.querySelectorAll('#step-3 .interest-chip[data-teach]');
const learnChips = document.querySelectorAll('#step-4 .interest-chip[data-learn]');
const nextBtn2 = document.getElementById('next-2');
const backBtn2 = document.getElementById('back-2');

function updateInterestNextButton() {
  const btn = document.getElementById('next-2');
  if (!btn) return;
  btn.disabled = selectedInterests.length < 1;
}

interestChips.forEach(chip => {
  chip.addEventListener('click', function() {
    const interest = this.dataset.interest;

    if (this.classList.contains('selected')) {
      this.classList.remove('selected');
      if (interest) selectedInterests = selectedInterests.filter(i => i !== interest);
    } else {
      this.classList.add('selected');
      if (interest) selectedInterests.push(interest);
    }

    updateInterestNextButton();
  });
});

nextBtn2.addEventListener('click', function() {
  goToStep(3);
});

backBtn2.addEventListener('click', function() {
  goToStep(1);
});

// Step 3: Skills I Can Teach
const backBtn3 = document.getElementById('back-3');
const nextBtn3 = document.getElementById('next-3');

function updateTeachNextButton() {
  const btn = document.getElementById('next-3');
  if (!btn) return;
  btn.disabled = false;
}

teachChips.forEach(chip => {
  chip.addEventListener('click', function() {
    const teach = this.dataset.teach;
    if (!teach) return;
    if (this.classList.contains('selected')) {
      this.classList.remove('selected');
      selectedTeach = selectedTeach.filter(i => i !== teach);
    } else {
      this.classList.add('selected');
      selectedTeach.push(teach);
    }
    updateTeachNextButton();
  });
});

backBtn3.addEventListener('click', function() {
  goToStep(2);
});

if (nextBtn3) {
  nextBtn3.addEventListener('click', function() {
    goToStep(4);
  });
}

// Step 4: Skills I Want to Learn
const backBtn4 = document.getElementById('back-4');
const nextBtn4 = document.getElementById('next-4');

function updateLearnNextButton() {
  const btn = document.getElementById('next-4');
  if (!btn) return;
  btn.disabled = false;
}

learnChips.forEach(chip => {
  chip.addEventListener('click', function() {
    const learn = this.dataset.learn;
    if (!learn) return;
    if (this.classList.contains('selected')) {
      this.classList.remove('selected');
      selectedLearn = selectedLearn.filter(i => i !== learn);
    } else {
      this.classList.add('selected');
      selectedLearn.push(learn);
    }
    updateLearnNextButton();
  });
});

if (backBtn4) {
  backBtn4.addEventListener('click', function() {
    goToStep(3);
  });
}

if (nextBtn4) {
  nextBtn4.addEventListener('click', function() {
    goToStep(5);
  });
}

// Step 5: Availability Selection
const dayChips = document.querySelectorAll('.day-chip');
const timeChips = document.querySelectorAll('.time-chip');
const finishBtn = document.getElementById('finish');
const backBtn5 = document.getElementById('back-5');
const nextBtn5 = document.getElementById('next-5');
const backBtn6 = document.getElementById('back-6');
const nextBtn6 = document.getElementById('next-6');
const backBtn7 = document.getElementById('back-7');
const nextBtn7 = document.getElementById('next-7');
const backBtn8 = document.getElementById('back-8');
const languageChecks = document.querySelectorAll('.language-checkbox');
const languageSelects = document.querySelectorAll('.language-proficiency');

function updateLanguageSelection() {
  selectedLanguages = [];
  selectedLanguageProficiency = {};
  languageChecks.forEach(function (cb) {
    const language = cb.dataset.language;
    const select = document.querySelector('.language-proficiency[data-language="' + language + '"]');
    if (!language || !select) return;
    select.disabled = !cb.checked;
    if (cb.checked) {
      selectedLanguages.push(language);
      selectedLanguageProficiency[language] = select.value || 'Beginner';
    }
  });
  var languageActionBtn = document.getElementById('next-6');
  if (languageActionBtn) languageActionBtn.disabled = selectedLanguages.length < 1;
}

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
    const time = this.dataset.time;
    if (this.classList.contains('selected')) {
      this.classList.remove('selected');
      selectedTimes = selectedTimes.filter(t => t !== time);
    } else {
      this.classList.add('selected');
      selectedTimes.push(time);
    }
  });
});

languageChecks.forEach(function (cb) {
  cb.addEventListener('change', updateLanguageSelection);
});

languageSelects.forEach(function (select) {
  select.addEventListener('change', updateLanguageSelection);
});

document.querySelectorAll('.language-row').forEach(function (row) {
  row.addEventListener('click', function (event) {
    const selectEl = event.target && event.target.closest
      ? (event.target.closest('select') || event.target.closest('.language-proficiency'))
      : null;
    // Allow clicks on disabled dropdowns to toggle the row; only block when the dropdown is active.
    if (selectEl && !selectEl.disabled) return;
    const cb = row.querySelector('.language-checkbox');
    if (!cb) return;
    if (event.target === cb) return;
    cb.checked = !cb.checked;
    updateLanguageSelection();
  });
});

if (backBtn5) {
  backBtn5.addEventListener('click', function() {
    goToStep(4);
  });
}

if (nextBtn5) {
  nextBtn5.addEventListener('click', function() {
    goToStep(6);
  });
}

if (backBtn6) {
  backBtn6.addEventListener('click', function() {
    goToStep(5);
  });
}

if (nextBtn6) {
  nextBtn6.addEventListener('click', function() {
    goToStep(7);
  });
}

if (backBtn7) {
  backBtn7.addEventListener('click', function() {
    goToStep(6);
  });
}

if (nextBtn7) {
  nextBtn7.addEventListener('click', function() {
    goToStep(8);
  });
}

if (backBtn8) {
  backBtn8.addEventListener('click', function() {
    goToStep(7);
  });
}

async function saveOnboardingPayload() {
  var payload = {
    memberType: selectedUserType || '',
    interests: selectedInterests || [],
    skills_teach: selectedTeach || [],
    skills_learn: selectedLearn || [],
    languages: selectedLanguages || [],
    language_proficiency: selectedLanguageProficiency || {},
    days: selectedDays || [],
    time: selectedTimes || [],
    stations: selectedStations || [],
    landmarks: selectedLandmarks || []
  };

  var res = await fetch('/api/onboarding', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  var out = await res.json().catch(function () { return {}; });
  if (!res.ok) {
    if (res.status === 401) {
      alert('Please sign up or log in first.');
      window.location.href = '/signup';
      return false;
    }
    alert(out.error || 'Could not save your onboarding details.');
    return false;
  }
  return true;
}

finishBtn.addEventListener('click', async function() {
  try {
    const ok = await saveOnboardingPayload();
    if (!ok) return;
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

  const progressPercent = (stepNumber / totalSteps) * 100;
  document.getElementById('progress-fill').style.width = `${progressPercent}%`;

  // Scroll to top
  window.scrollTo(0, 0);

  if (stepNumber === 7 && mrtViewMode === "map") {
    setTimeout(function () {
      if (realMap) realMap.invalidateSize();
    }, 220);
  }
}

// Preload selections for edit mode
document.addEventListener('DOMContentLoaded', function() {
  if (preloaded && preloaded.memberType) {
    selectedUserType = preloaded.memberType;
    userTypeCards.forEach(card => {
      if (card.dataset.type === selectedUserType) {
        card.classList.add('selected');
      }
    });
    nextBtn1.disabled = false;
  }

  if (preloaded && Array.isArray(preloaded.interests)) {
    selectedInterests = [...preloaded.interests];
    preloaded.interests.forEach(function(interest) {
      var chip = document.querySelector('.interest-chip[data-interest="' + interest + '"]');
      if (chip) chip.classList.add('selected');
    });
  }

  if (preloaded && Array.isArray(preloaded.skills_teach)) {
    selectedTeach = [...preloaded.skills_teach];
    teachChips.forEach(function (chip) { chip.classList.remove('selected'); });
    selectedTeach.forEach(function (skill) {
      var teachChip = document.querySelector('.interest-chip[data-teach="' + skill + '"]');
      if (teachChip) teachChip.classList.add('selected');
    });
  }

  if (preloaded && Array.isArray(preloaded.skills_learn)) {
    selectedLearn = [...preloaded.skills_learn];
    learnChips.forEach(function (chip) { chip.classList.remove('selected'); });
    selectedLearn.forEach(function (skill) {
      var learnChip = document.querySelector('.interest-chip[data-learn="' + skill + '"]');
      if (learnChip) learnChip.classList.add('selected');
    });
  }

  updateInterestNextButton();
  updateTeachNextButton();
  updateLearnNextButton();

  if (preloaded && Array.isArray(preloaded.days)) {
    selectedDays = [...preloaded.days];
    preloaded.days.forEach(function(day) {
      var chip = document.querySelector('.day-chip[data-day="' + day + '"]');
      if (chip) chip.classList.add('selected');
    });
  }

  if (preloaded && Array.isArray(preloaded.time)) {
    selectedTimes = [...preloaded.time];
    preloaded.time.forEach(function(t) {
      var chip = document.querySelector('.time-chip[data-time="' + t + '"]');
      if (chip) chip.classList.add('selected');
    });
  }

  if (preloaded && Array.isArray(preloaded.languages)) {
    const preloadedProf = preloaded.language_proficiency && typeof preloaded.language_proficiency === 'object'
      ? preloaded.language_proficiency
      : {};
    languageChecks.forEach(function (cb) {
      const language = cb.dataset.language;
      if (!language) return;
      const checked = preloaded.languages.indexOf(language) !== -1;
      cb.checked = checked;
      const select = document.querySelector('.language-proficiency[data-language="' + language + '"]');
      if (!select) return;
      if (checked && preloadedProf[language]) {
        select.value = preloadedProf[language];
      }
      select.disabled = !checked;
    });
  }

  updateLanguageSelection();

  if (preloaded && Array.isArray(preloaded.stations)) {
    selectedStations = [...preloaded.stations];
  }

  const resolvedEditStep = (isEditMode && editStep === 5 && editSection === 'languages') ? 6 : editStep;

  if (isEditMode && resolvedEditStep >= 2 && resolvedEditStep <= 6) {
    document.body.classList.add('onboarding-edit-single-step');
    goToStep(resolvedEditStep);

    document.querySelectorAll('.onboarding-step').forEach(function(stepEl) {
      if (stepEl.id !== ('step-' + resolvedEditStep)) {
        stepEl.style.display = 'none';
      }
    });

    var backBtn = document.getElementById('back-' + resolvedEditStep);
    var nextBtn = document.getElementById('next-' + resolvedEditStep);
    var stepEl = document.getElementById('step-' + resolvedEditStep);
    var buttonGroup = stepEl ? stepEl.querySelector('.button-group') : null;
    if (resolvedEditStep === 5 && stepEl) {
      var sections = stepEl.querySelectorAll('.availability-section');
      var titleEl = stepEl.querySelector('h1');
      var subtitleEl = stepEl.querySelector('.step-subtitle');
      if (editSection === 'languages') {
        if (sections[0]) sections[0].style.display = 'none';
        if (sections[1]) sections[1].style.display = 'none';
        if (titleEl) titleEl.textContent = 'Languages and Proficiency';
        if (subtitleEl) subtitleEl.textContent = 'Update your languages and proficiency.';
      } else if (editSection === 'availability') {
        if (sections[2]) sections[2].style.display = 'none';
        if (titleEl) titleEl.textContent = 'When are you available?';
        if (subtitleEl) subtitleEl.textContent = 'Update your preferred days and times.';
      }
    }
    if (backBtn) backBtn.style.display = 'none';
    if (buttonGroup) {
      buttonGroup.innerHTML = '';
    }
    if (nextBtn && buttonGroup) {
      var saveBtn = nextBtn.cloneNode(false);
      if (!saveBtn.id) saveBtn.id = 'next-' + resolvedEditStep;
      saveBtn.textContent = 'Save';
      saveBtn.classList.add('btn-full');
      saveBtn.disabled = (resolvedEditStep === 2) ? (selectedInterests.length < 1) : ((resolvedEditStep === 6) ? (selectedLanguages.length < 1) : false);
      buttonGroup.appendChild(saveBtn);
      saveBtn.addEventListener('click', async function () {
        const valid = (resolvedEditStep === 2 && selectedInterests.length >= 1) ||
                      (resolvedEditStep === 3) ||
                      (resolvedEditStep === 4) ||
                      (resolvedEditStep === 5) ||
                      (resolvedEditStep === 6 && selectedLanguages.length >= 1);
        if (!valid) {
          alert(resolvedEditStep === 6 ? 'Please select at least 1 language.' : 'Please select at least 1 interest.');
          return;
        }
        try {
          const ok = await saveOnboardingPayload();
          if (!ok) return;
          window.location.href = '/profile';
        } catch (_) {
          alert('Could not reach the server. Please try again.');
        }
      });
    }
  }
});

// MRT Station Picker
const mrtStations = [
  "Admiralty","Aljunied","Ang Mo Kio","Bartley","Bayfront","Beauty World","Bedok","Bedok North","Bedok Reservoir",
  "Bencoolen","Bendemeer","Bishan","Boon Keng","Boon Lay","Botanic Gardens","Braddell","Bras Basah","Bright Hill",
  "Bayshore",
  "Bugis","Buona Vista","Buangkok","Bukit Batok","Bukit Gombak","Bukit Panjang","Caldecott","Canberra","Cashew",
  "Changi Airport","Chinatown","Choa Chu Kang","Chinese Garden","City Hall","Clarke Quay","Clementi","Commonwealth",
  "Dakota","Dhoby Ghaut","Dover","Downtown","Eunos","Expo","Farrer Park","Farrer Road","Fort Canning",
  "Gardens by the Bay","Geylang Bahru","Great World","Gul Circle","Havelock","Haw Par Villa","HarbourFront",
  "Hillview","Holland Village","Hougang","Jalan Besar","Joo Koon","Jurong East","Kaki Bukit","Kallang","Katong Park",
  "Kembangan","Kent Ridge","Khatib","King Albert Park","Kovan","Kranji","Labrador Park","Lakeside","Lavender",
  "Lentor","Little India","Lorong Chuan","MacPherson","Marina Bay","Marina South Pier","Marine Parade","Marsiling",
  "Marine Terrace","Marymount","Mattar","Maxwell","Mayflower","Mountbatten","Napier","Nicoll Highway","Novena",
  "Newton",
  "one-north","Orchard","Orchard Boulevard","Outram Park","Pasir Panjang","Pasir Ris","Paya Lebar","Pioneer",
  "Potong Pasir","Promenade","Punggol","Queenstown","Raffles Place","Redhill","Rochor","Sembawang","Sengkang",
  "Serangoon","Shenton Way","Simei","Siglap","Sixth Avenue","Somerset","Springleaf","Stadium","Stevens","Tai Seng",
  "Tampines","Tampines East","Tampines West","Tan Kah Kee","Tanah Merah","Tanjong Katong","Tanjong Pagar",
  "Tanjong Rhu","Telok Ayer","Telok Blangah","Tiong Bahru","Toa Payoh","Tuas Crescent","Tuas Link","Tuas West Road",
  "Ubi","Upper Changi","Upper Thomson","Woodlands","Woodlands North","Woodlands South","Woodleigh","Yew Tee",
  "Yio Chu Kang","Yishun"
];

const mrtLineGroups = [
  { key: "NSL", label: "North South Line", stations: ["Jurong East","Bukit Batok","Bukit Gombak","Choa Chu Kang","Yew Tee","Kranji","Marsiling","Woodlands","Admiralty","Sembawang","Canberra","Yishun","Khatib","Yio Chu Kang","Ang Mo Kio","Bishan","Braddell","Toa Payoh","Novena","Newton","Orchard","Somerset","Dhoby Ghaut","City Hall","Raffles Place","Marina Bay","Marina South Pier"] },
  { key: "EWL", label: "East West Line", stations: ["Tuas Link","Tuas West Road","Tuas Crescent","Gul Circle","Joo Koon","Pioneer","Boon Lay","Lakeside","Chinese Garden","Jurong East","Clementi","Dover","Buona Vista","Commonwealth","Queenstown","Redhill","Tiong Bahru","Outram Park","Tanjong Pagar","Raffles Place","City Hall","Bugis","Lavender","Kallang","Aljunied","Paya Lebar","Eunos","Kembangan","Bedok","Tanah Merah","Expo","Changi Airport","Pasir Ris","Simei"] },
  { key: "DTL", label: "Downtown Line", stations: ["Bayfront","Beauty World","Bedok North","Bedok Reservoir","Bencoolen","Bendemeer","Botanic Gardens","Bukit Panjang","Cashew","Chinatown","Downtown","Expo","Fort Canning","Geylang Bahru","Hillview","Jalan Besar","Kaki Bukit","King Albert Park","Little India","MacPherson","Mattar","Newton","Promenade","Rochor","Sixth Avenue","Stevens","Tan Kah Kee","Telok Ayer","Tampines","Tampines East","Tampines West","Ubi","Upper Changi"] },
  { key: "NEL", label: "North East Line", stations: ["Buangkok","Chinatown","Clarke Quay","Dhoby Ghaut","Farrer Park","HarbourFront","Hougang","Kovan","Little India","Outram Park","Potong Pasir","Punggol","Sengkang","Serangoon","Woodleigh"] },
  { key: "CCL", label: "Circle Line", stations: ["Dhoby Ghaut","Bras Basah","Esplanade","Promenade","Nicoll Highway","Stadium","Mountbatten","Dakota","Paya Lebar","MacPherson","Tai Seng","Bartley","Serangoon","Lorong Chuan","Bishan","Marymount","Caldecott","Botanic Gardens","Farrer Road","Holland Village","Buona Vista","one-north","Kent Ridge","Haw Par Villa","Pasir Panjang","Labrador Park","Telok Blangah","HarbourFront","Marina Bay","Bayfront"] },
  { key: "TEL", label: "Thomson-East Coast Line", stations: ["Woodlands North","Woodlands","Woodlands South","Springleaf","Lentor","Mayflower","Bright Hill","Upper Thomson","Caldecott","Stevens","Orchard Boulevard","Orchard","Great World","Havelock","Outram Park","Maxwell","Shenton Way","Marina Bay","Gardens by the Bay","Tanjong Rhu","Katong Park","Tanjong Katong","Marine Parade","Marine Terrace","Siglap","Bayshore","Napier"] }
];

const mrtLineColor = {
  NSL: "#ef4444",
  EWL: "#22c55e",
  DTL: "#3b82f6",
  NEL: "#a855f7",
  CCL: "#f59e0b",
  TEL: "#8b5e3c",
  OTHER: "#64748b"
};

const MRT_LINE_CODE_PREFIX = {
  NSL: "NS",
  EWL: "EW",
  CCL: "CC",
  DTL: "DT",
  NEL: "NE",
  TEL: "TE"
};

const MRT_ROUTE_RULES = {
  minutesPerStop: 2,
  transferPenalty: 6
};

let routeGraph = null;
let routeNodesByStation = null;
const routeMinutesCache = new Map();

function buildRouteGraph() {
  if (routeGraph && routeNodesByStation) {
    return { graph: routeGraph, nodesByStation: routeNodesByStation };
  }

  const graph = new Map();
  const nodesByStation = new Map();

  function addNode(nodeId) {
    if (!graph.has(nodeId)) {
      graph.set(nodeId, []);
    }
  }

  function addEdge(a, b, minutes, type) {
    addNode(a);
    addNode(b);
    graph.get(a).push({ to: b, minutes: minutes, type: type });
  }

  mrtLineGroups.forEach(function (line) {
    line.stations.forEach(function (stationName) {
      const nodeId = line.key + "::" + stationName;
      addNode(nodeId);
      if (!nodesByStation.has(stationName)) {
        nodesByStation.set(stationName, []);
      }
      nodesByStation.get(stationName).push(nodeId);
    });

    for (let i = 0; i < line.stations.length - 1; i += 1) {
      const a = line.key + "::" + line.stations[i];
      const b = line.key + "::" + line.stations[i + 1];
      addEdge(a, b, MRT_ROUTE_RULES.minutesPerStop, "ride");
      addEdge(b, a, MRT_ROUTE_RULES.minutesPerStop, "ride");
    }
  });

  nodesByStation.forEach(function (nodes) {
    if (nodes.length < 2) return;
    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        addEdge(nodes[i], nodes[j], MRT_ROUTE_RULES.transferPenalty, "transfer");
        addEdge(nodes[j], nodes[i], MRT_ROUTE_RULES.transferPenalty, "transfer");
      }
    }
  });

  routeGraph = graph;
  routeNodesByStation = nodesByStation;
  return { graph: routeGraph, nodesByStation: routeNodesByStation };
}

function shortestMinutesBetweenStations(startStation, endStation) {
  if (!startStation || !endStation) return null;
  if (startStation === endStation) return 0;
  const cacheKey = startStation + ">>" + endStation;
  if (routeMinutesCache.has(cacheKey)) {
    return routeMinutesCache.get(cacheKey);
  }

  const built = buildRouteGraph();
  const graph = built.graph;
  const nodesByStation = built.nodesByStation;
  const startNodes = nodesByStation.get(startStation) || [];
  const goalNodes = new Set(nodesByStation.get(endStation) || []);
  if (!startNodes.length || !goalNodes.size) {
    routeMinutesCache.set(cacheKey, null);
    return null;
  }

  const dist = new Map();
  const visited = new Set();
  const queue = [];

  startNodes.forEach(function (nodeId) {
    dist.set(nodeId, 0);
    queue.push({ node: nodeId, d: 0 });
  });

  function push(nodeId, d) {
    queue.push({ node: nodeId, d: d });
    queue.sort(function (a, b) { return a.d - b.d; });
  }

  let best = null;
  while (queue.length) {
    const current = queue.shift();
    if (visited.has(current.node)) continue;
    visited.add(current.node);

    if (goalNodes.has(current.node)) {
      best = current.d;
      break;
    }

    const edges = graph.get(current.node) || [];
    edges.forEach(function (edge) {
      const nextDist = current.d + edge.minutes;
      const prevDist = dist.has(edge.to) ? dist.get(edge.to) : Infinity;
      if (nextDist < prevDist) {
        dist.set(edge.to, nextDist);
        push(edge.to, nextDist);
      }
    });
  }

  routeMinutesCache.set(cacheKey, best);
  routeMinutesCache.set(endStation + ">>" + startStation, best);
  return best;
}

function shortestRouteDetails(startStation, endStation) {
  if (!startStation || !endStation) return null;
  if (startStation === endStation) return { minutes: 0, transfers: 0 };

  const built = buildRouteGraph();
  const graph = built.graph;
  const nodesByStation = built.nodesByStation;
  const startNodes = nodesByStation.get(startStation) || [];
  const goalNodes = new Set(nodesByStation.get(endStation) || []);
  if (!startNodes.length || !goalNodes.size) return null;

  const dist = new Map();
  const prev = new Map();
  const visited = new Set();
  const queue = [];

  function push(nodeId, d) {
    queue.push({ node: nodeId, d: d });
    queue.sort(function (a, b) { return a.d - b.d; });
  }

  startNodes.forEach(function (nodeId) {
    dist.set(nodeId, 0);
    push(nodeId, 0);
  });

  let targetNode = null;
  while (queue.length) {
    const current = queue.shift();
    if (visited.has(current.node)) continue;
    visited.add(current.node);

    if (goalNodes.has(current.node)) {
      targetNode = current.node;
      break;
    }

    (graph.get(current.node) || []).forEach(function (edge) {
      const nextDist = current.d + edge.minutes;
      const prevDist = dist.has(edge.to) ? dist.get(edge.to) : Infinity;
      if (nextDist < prevDist) {
        dist.set(edge.to, nextDist);
        prev.set(edge.to, { node: current.node, type: edge.type });
        push(edge.to, nextDist);
      }
    });
  }

  if (!targetNode) return null;
  let transfers = 0;
  let cursor = targetNode;
  while (prev.has(cursor)) {
    const step = prev.get(cursor);
    if (step.type === "transfer") transfers += 1;
    cursor = step.node;
  }
  return { minutes: dist.get(targetNode), transfers: transfers };
}

let mrtViewMode = "list";
let selectedLineKeys = ["NSL"];

function stationLineKey(name) {
  for (var i = 0; i < mrtLineGroups.length; i += 1) {
    if (mrtLineGroups[i].stations.indexOf(name) !== -1) return mrtLineGroups[i].key;
  }
  return "OTHER";
}

function stationLineKeys(name) {
  var keys = [];
  for (var i = 0; i < mrtLineGroups.length; i += 1) {
    if (mrtLineGroups[i].stations.indexOf(name) !== -1) keys.push(mrtLineGroups[i].key);
  }
  if (!keys.length) keys.push("OTHER");
  return keys;
}

function stationLineGradient(name) {
  var keys = stationLineKeys(name);
  var colors = keys.map(function (k) { return mrtLineColor[k] || mrtLineColor.OTHER; });
  if (colors.length <= 1) return null;
  var step = 100 / colors.length;
  var stops = colors.map(function (c, idx) {
    var start = Math.round(idx * step);
    var end = Math.round((idx + 1) * step);
    return c + " " + start + "% " + end + "%";
  }).join(", ");
  return "linear-gradient(180deg, " + stops + ")";
}

function stationLineLabel(key) {
  var found = mrtLineGroups.find(function (g) { return g.key === key; });
  return found ? found.label : "Other Lines";
}

function renderStationOptions(list, selected) {
  const container = document.getElementById('mrt-options');
  if (!container) return;
  container.innerHTML = '';
  container.classList.toggle("map-view-mode", mrtViewMode === "map");

  const grouped = {};
  list.forEach(function (name) {
    var key = stationLineKey(name);
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(name);
  });

  const orderedKeys = mrtLineGroups.map(function (g) { return g.key; }).concat(["OTHER"]);
  orderedKeys.forEach(function (lineKey) {
    var stations = grouped[lineKey];
    if (!stations || !stations.length) return;

    const section = document.createElement("section");
    section.className = "mrt-line-group";
    section.style.borderColor = mrtViewMode === "map" ? mrtLineColor[lineKey] || mrtLineColor.OTHER : "";

    const title = document.createElement("h4");
    title.className = "mrt-line-title";
    title.textContent = "🚇 " + stationLineLabel(lineKey);
    if (mrtViewMode === "map") {
      title.style.color = mrtLineColor[lineKey] || mrtLineColor.OTHER;
    } else {
      title.style.color = "#475569";
    }

    const grid = document.createElement("div");
    grid.className = "station-grid";

    stations.forEach(function (name) {
      const checked = selected.indexOf(name) !== -1;
      const item = document.createElement("button");
      item.type = "button";
      item.className = "station-chip" + (checked ? " selected" : "");
      item.innerHTML = "<span>" + name + "</span>";
      item.setAttribute("aria-pressed", checked ? "true" : "false");
      item.addEventListener("click", function () {
        toggleStation(name);
        const stationSearch = document.getElementById("mrt-search");
        filterStations(stationSearch ? stationSearch.value : "");
      });
      grid.appendChild(item);
    });

    section.appendChild(title);
    section.appendChild(grid);
    container.appendChild(section);
  });
}

function renderSchematicMap(list, selected) {
  const board = document.getElementById("mrt-schematic-lines");
  if (!board) return;
  board.innerHTML = "";

  const filteredSet = new Set(list);
  mrtLineGroups.forEach(function (group) {
    const stations = group.stations.filter(function (name) { return filteredSet.has(name); });
    if (!stations.length) return;

    const row = document.createElement("div");
    row.className = "mrt-line-row";

    const label = document.createElement("div");
    label.className = "mrt-line-chip";
    label.style.background = mrtLineColor[group.key] || mrtLineColor.OTHER;
    label.textContent = group.label;

    const stationWrap = document.createElement("div");
    stationWrap.className = "mrt-line-stations";

    stations.forEach(function (name) {
      const active = selected.indexOf(name) !== -1;
      const node = document.createElement("button");
      node.type = "button";
      node.className = "station-node" + (active ? " selected" : "");
      node.textContent = name;
      node.setAttribute("aria-pressed", active ? "true" : "false");
      node.addEventListener("click", function () {
        toggleStation(name);
        const stationSearch = document.getElementById("mrt-search");
        filterStations(stationSearch ? stationSearch.value : "");
      });
      stationWrap.appendChild(node);
    });

    row.appendChild(label);
    row.appendChild(stationWrap);
    board.appendChild(row);
  });
}

function stationToMapPercent(stationName) {
  const coord = STATION_CENTER[stationName];
  if (!coord) return null;
  const lat = coord[0];
  const lng = coord[1];
  const minLat = 1.23;
  const maxLat = 1.47;
  const minLng = 103.60;
  const maxLng = 104.02;
  const x = ((lng - minLng) / (maxLng - minLng)) * 100;
  const y = (1 - ((lat - minLat) / (maxLat - minLat))) * 100;
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return { x: Math.max(2, Math.min(98, x)), y: Math.max(2, Math.min(98, y)) };
}

function getMrtImageGeometry() {
  const wrap = document.getElementById("mrt-map-wrap");
  const img = document.querySelector(".mrt-map-img");
  if (!wrap || !img) return null;
  const wrapRect = wrap.getBoundingClientRect();
  const naturalW = img.naturalWidth || 2048;
  const naturalH = img.naturalHeight || 1576;
  const imageRatio = naturalW / naturalH;
  const boxRatio = wrapRect.width / wrapRect.height;
  let renderW = wrapRect.width;
  let renderH = wrapRect.height;
  if (boxRatio > imageRatio) {
    renderW = wrapRect.height * imageRatio;
  } else {
    renderH = wrapRect.width / imageRatio;
  }
  const offsetX = (wrapRect.width - renderW) / 2;
  const offsetY = (wrapRect.height - renderH) / 2;
  return { wrap, img, wrapRect, naturalW, naturalH, renderW, renderH, offsetX, offsetY };
}

function buildStationImageCoords(naturalW, naturalH) {
  return Object.keys(STATION_CENTER).map(function (stationName) {
    const p = stationToMapPercent(stationName);
    if (!p) return null;
    return {
      name: stationName,
      x: (p.x / 100) * naturalW,
      y: (p.y / 100) * naturalH
    };
  }).filter(Boolean);
}

let mrtMapClickBound = false;
const MRT_MAP_DEBUG = (new URLSearchParams(window.location.search).get("mrtdebug") === "1");

function ensureMrtDebugDot(container) {
  if (!container) return null;
  let dot = container.querySelector(".mrt-debug-dot");
  if (!dot) {
    dot = document.createElement("div");
    dot.className = "mrt-debug-dot";
    dot.style.display = "none";
    container.appendChild(dot);
  }
  return dot;
}

function renderMrtImageHotspots(selected) {
  const geo = getMrtImageGeometry();
  const overlay = document.getElementById("mrt-map-hotspots");
  if (!overlay || !geo) return;
  overlay.innerHTML = "";
  const coords = buildStationImageCoords(geo.naturalW, geo.naturalH);
  coords.forEach(function (station) {
    const left = geo.offsetX + (station.x / geo.naturalW) * geo.renderW;
    const top = geo.offsetY + (station.y / geo.naturalH) * geo.renderH;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "mrt-map-hotspot" + (selected.indexOf(station.name) !== -1 ? " selected" : "");
    btn.style.left = left + "px";
    btn.style.top = top + "px";
    btn.title = station.name;
    btn.setAttribute("aria-label", station.name);
    btn.addEventListener("click", function () {
      toggleStation(station.name);
      const stationSearch = document.getElementById("mrt-search");
      filterStations(stationSearch ? stationSearch.value : "");
    });
    overlay.appendChild(btn);
  });

  if (!mrtMapClickBound) {
    mrtMapClickBound = true;
    geo.wrap.addEventListener("click", function (event) {
      if (event.target && event.target.classList && event.target.classList.contains("mrt-map-hotspot")) {
        return;
      }
      const currentGeo = getMrtImageGeometry();
      if (!currentGeo) return;
      const xInWrap = event.clientX - currentGeo.wrapRect.left;
      const yInWrap = event.clientY - currentGeo.wrapRect.top;

      if (
        xInWrap < currentGeo.offsetX ||
        xInWrap > currentGeo.offsetX + currentGeo.renderW ||
        yInWrap < currentGeo.offsetY ||
        yInWrap > currentGeo.offsetY + currentGeo.renderH
      ) {
        return;
      }

      const xOriginal = ((xInWrap - currentGeo.offsetX) / currentGeo.renderW) * currentGeo.naturalW;
      const yOriginal = ((yInWrap - currentGeo.offsetY) / currentGeo.renderH) * currentGeo.naturalH;
      const stations = buildStationImageCoords(currentGeo.naturalW, currentGeo.naturalH);
      let nearest = null;
      let bestDist = Infinity;
      stations.forEach(function (station) {
        const dx = xOriginal - station.x;
        const dy = yOriginal - station.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < bestDist) {
          bestDist = dist;
          nearest = station;
        }
      });

      const maxClickRadiusDisplayPx = 26;
      const scaleX = currentGeo.naturalW / currentGeo.renderW;
      const maxClickRadiusOriginalPx = maxClickRadiusDisplayPx * scaleX;
      if (MRT_MAP_DEBUG) {
        const dot = ensureMrtDebugDot(currentGeo.wrap);
        if (dot) {
          dot.style.left = xInWrap + "px";
          dot.style.top = yInWrap + "px";
          dot.style.display = "block";
        }
        console.log("[MRT DEBUG]", {
          click_display: { x: Number(xInWrap.toFixed(2)), y: Number(yInWrap.toFixed(2)) },
          click_original: { x: Number(xOriginal.toFixed(2)), y: Number(yOriginal.toFixed(2)) },
          nearest_station: nearest ? nearest.name : null,
          nearest_distance_original_px: Number(bestDist.toFixed(2)),
          threshold_original_px: Number(maxClickRadiusOriginalPx.toFixed(2))
        });
      }
      if (nearest && bestDist <= maxClickRadiusOriginalPx) {
        toggleStation(nearest.name);
        const stationSearch = document.getElementById("mrt-search");
        filterStations(stationSearch ? stationSearch.value : "");
      }
    });
  }
}

function stationCode(lineKey, index) {
  return (MRT_LINE_CODE_PREFIX[lineKey] || lineKey) + String(index + 1);
}

function renderLineChips() {
  const wrap = document.getElementById("mrt-line-chips");
  if (!wrap) return;
  wrap.innerHTML = "";
  mrtLineGroups.forEach(function (line) {
    const isActive = selectedLineKeys.indexOf(line.key) !== -1;
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "mrt-line-chip" + (isActive ? " active" : "");
    chip.style.background = isActive ? (mrtLineColor[line.key] || "#0f172a") : "#ffffff";
    chip.textContent = (MRT_LINE_CODE_PREFIX[line.key] || line.key) + " • " + line.label;
    chip.setAttribute("aria-pressed", isActive ? "true" : "false");
    chip.addEventListener("click", function () {
      const idx = selectedLineKeys.indexOf(line.key);
      if (idx === -1) {
        selectedLineKeys.push(line.key);
      } else if (selectedLineKeys.length > 1) {
        selectedLineKeys.splice(idx, 1);
      }
      renderLineChips();
      renderLineStations();
    });
    wrap.appendChild(chip);
  });
}

function renderLineStations() {
  const wrap = document.getElementById("mrt-station-buttons");
  if (!wrap) return;
  wrap.innerHTML = "";
  const selectedLines = mrtLineGroups.filter(function (line) {
    return selectedLineKeys.indexOf(line.key) !== -1;
  });
  const linesToRender = selectedLines.length ? selectedLines : (mrtLineGroups[0] ? [mrtLineGroups[0]] : []);
  const seen = new Set();

  linesToRender.forEach(function (line) {
    line.stations.forEach(function (stationName, idx) {
      const normalized = stationName.toLowerCase();
      if (seen.has(normalized)) return;
      seen.add(normalized);

      const code = stationCode(line.key, idx);
      const selected = selectedStations.indexOf(stationName) !== -1;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "mrt-station-btn" + (selected ? " selected" : "");
      const splitGradient = stationLineGradient(stationName);
      btn.style.setProperty("--station-stripe", splitGradient || (mrtLineColor[line.key] || "#cbd5e1"));
      btn.innerHTML = "<strong>" + stationName + "</strong><span>" + code + "</span>";
      btn.setAttribute("aria-pressed", selected ? "true" : "false");
      btn.addEventListener("click", function () {
        toggleStation(stationName);
      });
      wrap.appendChild(btn);
    });
  });
}

function filterStations(query) {
  const q = (query || '').toLowerCase();
  const filtered = mrtStations.filter(s => s.toLowerCase().includes(q));
  renderStationOptions(filtered, selectedStations);
  renderSchematicMap(filtered, selectedStations);
  renderMrtImageHotspots(selectedStations);
}

function toggleStation(name) {
  const isSameSelection = selectedStations.length === 1 && selectedStations[0] === name;
  selectedStations = isSameSelection ? [] : [name];
  renderLineStations();
  renderSelectedStations();
  refreshSafeVenues();
}

function removeStation(name) {
  selectedStations = selectedStations.filter(function (s) { return s !== name; });
  renderLineStations();
  renderSelectedStations();
}

function renderSelectedStations() {
  const tags = document.getElementById('selected-stations-tags');
  const listEl = document.getElementById('selected-stations-list');
  if (!tags) return;
  tags.innerHTML = '';
  if (listEl) listEl.innerHTML = '';
  if (!selectedStations.length) {
    tags.innerHTML = '<span class="selected-stations-empty">No stations selected yet.</span>';
    if (listEl) listEl.innerHTML = '<li>No station selected</li>';
    updateMidpointSuggestion();
    return;
  }
  selectedStations.forEach(function (name) {
    const tag = document.createElement('span');
    tag.className = 'station-tag';
    tag.innerHTML = `
      <span>${name}</span>
      <button type="button" class="station-tag-remove" aria-label="Remove ${name}">x</button>
    `;
    const removeBtn = tag.querySelector('.station-tag-remove');
    if (removeBtn) {
      removeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        removeStation(name);
      });
    }
    tags.appendChild(tag);
    if (listEl) {
      const li = document.createElement("li");
      li.textContent = name;
      listEl.appendChild(li);
    }
  });
  updateMidpointSuggestion();
}

function suggestMidpoint(stations) {
  if (!stations || stations.length < 2) return null;
  const built = buildRouteGraph();
  const candidates = Array.from(built.nodesByStation.keys());
  if (!candidates.length) return null;

  const uniqueStarts = Array.from(new Set(stations)).filter(function (name) {
    return built.nodesByStation.has(name);
  });
  if (uniqueStarts.length < 2) return null;

  let bestStation = null;
  let bestFairness = Infinity;
  let bestTotal = Infinity;

  candidates.forEach(function (candidate) {
    const times = uniqueStarts
      .map(function (startStation) {
        return shortestMinutesBetweenStations(startStation, candidate);
      })
      .filter(function (minutes) { return minutes !== null; });

    if (times.length !== uniqueStarts.length) return;

    const minTime = Math.min.apply(null, times);
    const maxTime = Math.max.apply(null, times);
    const fairness = maxTime - minTime;
    const total = times.reduce(function (sum, value) { return sum + value; }, 0);

    if (fairness < bestFairness || (fairness === bestFairness && total < bestTotal)) {
      bestFairness = fairness;
      bestTotal = total;
      bestStation = candidate;
    }
  });

  return bestStation;
}

const STATION_CENTER = {
  "Toa Payoh": [1.3320, 103.8474],
  "Bishan": [1.3508, 103.8480],
  "Serangoon": [1.3497, 103.8737],
  "Bugis": [1.3009, 103.8552],
  "City Hall": [1.2931, 103.8520],
  "Dhoby Ghaut": [1.2993, 103.8458],
  "Paya Lebar": [1.3174, 103.8921],
  "Jurong East": [1.3332, 103.7422],
  "Outram Park": [1.2819, 103.8392],
};

let realMap = null;
let realMapMarkers = [];
let realMapHeatCircles = [];

function midpointCenter(midpoint) {
  return STATION_CENTER[midpoint] || [1.3521, 103.8198];
}

function centerFromStations(stations) {
  const points = (stations || [])
    .map(function (s) { return STATION_CENTER[s]; })
    .filter(Boolean);
  if (!points.length) return [1.3521, 103.8198];
  const sum = points.reduce(function (acc, point) {
    return [acc[0] + point[0], acc[1] + point[1]];
  }, [0, 0]);
  return [sum[0] / points.length, sum[1] / points.length];
}

function clearLeafletMarkers() {
  if (!realMapMarkers.length) return;
  realMapMarkers.forEach(function (marker) {
    if (realMap) realMap.removeLayer(marker);
  });
  realMapMarkers = [];
}

function clearLeafletHeatmap() {
  if (!realMapHeatCircles.length) return;
  realMapHeatCircles.forEach(function (circle) {
    if (realMap) realMap.removeLayer(circle);
  });
  realMapHeatCircles = [];
}

function initRealMap() {
  if (realMap || typeof window.L === "undefined") return;
  const mapEl = document.getElementById("realMap");
  if (!mapEl) return;

  realMap = window.L.map("realMap", { zoomControl: true }).setView([1.3521, 103.8198], 12);
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
    maxZoom: 19
  }).addTo(realMap);
}

function iconForVenueType(type) {
  var t = (type || "").toLowerCase();
  if (t.indexOf("library") !== -1) return "📚";
  if (t.indexOf("community") !== -1) return "🏢";
  if (t.indexOf("senior") !== -1) return "🧓";
  if (t.indexOf("cafe") !== -1 || t.indexOf("coffee") !== -1) return "☕";
  if (t.indexOf("park") !== -1) return "🌳";
  return "📍";
}

async function fetchSafeVenues(stations) {
  if (!stations || !stations.length) return [];
  const qs = encodeURIComponent(stations.join(","));
  const res = await fetch("/api/safe_locations?stations=" + qs);
  if (!res.ok) return [];
  const rows = await res.json().catch(function () { return []; });
  if (!Array.isArray(rows)) return [];
  return rows.map(function (row, idx) {
    return {
      id: "venue-" + idx + "-" + (row.place_name || "").replace(/\s+/g, "-").toLowerCase(),
      icon: iconForVenueType(row.venue_type),
      type: row.venue_type || "venue",
      name: row.place_name || "Safe venue",
      walk: row.walking_mins ? (row.walking_mins + " min walk from " + row.station_name + " MRT") : ("Near " + row.station_name + " MRT"),
      station_name: row.station_name || "",
      address: row.address || "",
      lat: Number(row.lat),
      lng: Number(row.lng),
      walking_mins: row.walking_mins
    };
  }).filter(function (row) {
    return Number.isFinite(row.lat) && Number.isFinite(row.lng);
  });
}

function updateMidpointSuggestion() {
  const midpointEl = document.getElementById("midpoint-station");
  const midpointMetaEl = document.querySelector(".midpoint-meta");
  const breakdownEl = document.getElementById("midpoint-breakdown");
  const midpoint = suggestMidpoint(selectedStations);
  if (midpointEl) {
    midpointEl.textContent = midpoint ? ("📍 " + midpoint + " MRT") : "Midpoint unavailable.";
  }
  if (midpointMetaEl) {
    midpointMetaEl.textContent = midpoint
      ? "Travel time balanced for both users"
      : "Select stations to calculate a midpoint.";
  }
  if (breakdownEl) {
    if (midpoint && selectedStations.length >= 2) {
      const userA = selectedStations[0];
      const userB = selectedStations[1];
      const routeA = shortestRouteDetails(userA, midpoint);
      const routeB = shortestRouteDetails(userB, midpoint);
      const lineA = routeA ? `User A (${userA}) → ${routeA.minutes} mins, transfers ${routeA.transfers}` : "";
      const lineB = routeB ? `User B (${userB}) → ${routeB.minutes} mins, transfers ${routeB.transfers}` : "";
      breakdownEl.innerHTML = `<div>${lineA}</div><div>${lineB}</div>`;
    } else {
      breakdownEl.innerHTML = "";
    }
  }
}

function renderRealMapPopup(venue) {
  const icon = document.getElementById("real-map-popup-icon");
  const name = document.getElementById("real-map-popup-name");
  const type = document.getElementById("real-map-popup-type");
  const walk = document.getElementById("real-map-popup-walk");
  if (icon) icon.textContent = venue.icon;
  if (name) name.textContent = venue.name;
  if (type) type.textContent = venue.type;
  if (walk) walk.textContent = venue.walk;
}

function renderMapMarkers(venues, activeId) {
  if (realMap) {
    clearLeafletMarkers();
    venues.forEach(function (venue) {
      const icon = window.L.divIcon({
        className: "leaflet-venue-icon",
        html: '<div style="width:34px;height:34px;border-radius:999px;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 16px rgba(15,23,42,.24);border:2px solid ' + (venue.id === activeId ? "#14b8a6" : "#ffffff") + ';">' + venue.icon + "</div>",
        iconSize: [34, 34],
        iconAnchor: [17, 17]
      });
      const marker = window.L.marker([venue.lat, venue.lng], { icon: icon }).addTo(realMap);
      marker.on("click", function () {
        setActiveVenue(venue.id);
      });
      marker.bindPopup(
        "<strong>" + venue.name + "</strong><br>" +
        venue.type + "<br>" +
        venue.walk
      );
      realMapMarkers.push(marker);
    });
    return;
  }

  const markers = document.getElementById("real-map-markers");
  if (!markers) return;
  markers.innerHTML = "";
  venues.forEach(function (venue) {
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = "map-marker" + (venue.id === activeId ? " active" : "");
    marker.style.left = venue.position.x + "%";
    marker.style.top = venue.position.y + "%";
    marker.textContent = venue.icon;
    marker.setAttribute("aria-label", venue.name);
    marker.addEventListener("click", function () {
      setActiveVenue(venue.id);
    });
    markers.appendChild(marker);
  });
}

let currentVenues = [];
let currentActiveVenueId = "library";

function setActiveVenue(venueId) {
  currentActiveVenueId = venueId;
  const venue = currentVenues.find(function (v) { return v.id === venueId; }) || currentVenues[0];
  if (!venue) return;
  const popup = document.getElementById("real-map-popup");
  if (popup) popup.style.display = "";
  document.querySelectorAll(".venue-card").forEach(function (card) {
    card.classList.toggle("active", card.getAttribute("data-venue-id") === venue.id);
  });
  renderRealMapPopup(venue);
  renderMapMarkers(currentVenues, venue.id);
  if (realMap) {
    realMap.flyTo([venue.lat, venue.lng], 14, { duration: 0.45 });
  }
}

function renderSafeVenueCards(midpoint) {
  const grid = document.getElementById("safe-venue-list");
  if (!grid) return;
  if (!midpoint) {
    grid.innerHTML = '<div class="selected-stations-empty">Select at least 2 stations to get midpoint-based venue recommendations.</div>';
    return;
  }
  if (!currentVenues.length) {
    grid.innerHTML = '<div class="selected-stations-empty">No curated safe venues found for ' + midpoint + ' yet.</div>';
    return;
  }
  grid.innerHTML = currentVenues.map(function (spot) {
    return (
      '<article class="safe-venue-card">' +
      '<h5>' + spot.icon + " " + spot.name + "</h5>" +
      '<p>' + spot.walk + "</p>" +
      "</article>"
    );
  }).join("");
}

async function refreshSafeVenues() {
  const midpoint = suggestMidpoint(selectedStations);
  if (!midpoint) {
    currentVenues = [];
    renderSafeVenueCards(null);
    return;
  }
  try {
    currentVenues = await fetchSafeVenues([midpoint]);
  } catch (err) {
    currentVenues = [];
  }
  renderSafeVenueCards(midpoint);
}

function setMrtViewMode(mode) {
  mrtViewMode = mode === "map" ? "map" : "list";
  const isRealMap = mrtViewMode === "map";
  const schematic = document.getElementById("mrt-schematic");
  const realMapPanel = document.getElementById("real-map-panel");
  const options = document.getElementById("mrt-options");

  if (schematic) schematic.hidden = isRealMap;
  if (realMapPanel) realMapPanel.hidden = !isRealMap;
  if (options) options.hidden = true;

  if (isRealMap) {
    initRealMap();
    setTimeout(function () {
      if (realMap) {
        realMap.invalidateSize();
      }
    }, 220);
  }

  document.querySelectorAll(".mrt-view-btn").forEach(function (b) {
    const active = (b.getAttribute("data-mrt-view") || "list") === mrtViewMode;
    b.classList.toggle("active", active);
    b.setAttribute("aria-selected", active ? "true" : "false");
  });
}

const stationSearch = document.getElementById('mrt-search');
if (stationSearch) {
  stationSearch.addEventListener('input', function () {
    filterStations(stationSearch.value);
  });
}

document.querySelectorAll(".mrt-view-btn").forEach(function (btn) {
  btn.addEventListener("click", function () {
    setMrtViewMode(btn.getAttribute("data-mrt-view") || "list");
    const stationSearch = document.getElementById("mrt-search");
    filterStations(stationSearch ? stationSearch.value : "");
  });
});

const findSafeBtn = document.getElementById("find-safe-locations");
if (findSafeBtn) {
  findSafeBtn.addEventListener("click", function () {
    refreshSafeVenues();
  });
}

const heatToggle = document.getElementById("real-map-heat-toggle");
const heatOverlay = document.getElementById("real-map-heat-overlay");
const heatLabel = document.getElementById("real-map-heat-label");
function applyHeatmapState() {
  const on = !!(heatToggle && heatToggle.checked);
  if (heatOverlay) heatOverlay.classList.toggle("show", on);
  if (heatLabel) heatLabel.textContent = on ? "ON" : "OFF";
  if (!realMap) return;
  clearLeafletHeatmap();
  if (!on) return;
  currentVenues.forEach(function (venue) {
    const circle = window.L.circle([venue.lat, venue.lng], {
      radius: 500,
      color: "#14b8a6",
      fillColor: "#14b8a6",
      fillOpacity: 0.15,
      weight: 1
    }).addTo(realMap);
    realMapHeatCircles.push(circle);
  });
}

if (heatToggle) {
  heatToggle.addEventListener("change", function () {
    applyHeatmapState();
  });
}

const clearSelectionBtn = document.getElementById("mrt-clear-selection");
if (clearSelectionBtn) {
  clearSelectionBtn.addEventListener("click", function () {
    selectedStations = [];
    renderLineStations();
    renderSelectedStations();
  });
}

if (preloaded && Array.isArray(preloaded.stations)) {
  selectedStations = [...preloaded.stations].slice(0, 1);
}

renderStationOptions(mrtStations, selectedStations);
renderSelectedStations();
renderSchematicMap(mrtStations, selectedStations);
renderMrtImageHotspots(selectedStations);
setMrtViewMode(mrtViewMode);
renderLineChips();
renderLineStations();
window.addEventListener("resize", function () {
  renderMrtImageHotspots(selectedStations);
});

// Landmarks
if (preloaded && Array.isArray(preloaded.landmarks)) {
  selectedLandmarks = [...preloaded.landmarks];
}

document.querySelectorAll('.picker-tab').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var target = btn.getAttribute('data-picker');
    document.querySelectorAll('.picker-tab').forEach(b => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.picker-panel').forEach(p => {
      p.classList.toggle('active', p.id === target);
    });
  });
});

// Landmark selection - positions are now set in HTML via inline styles
document.querySelectorAll('.landmark-dot').forEach(function (dot) {
  const name = dot.getAttribute('data-landmark');
  if (selectedLandmarks.indexOf(name) !== -1) {
    dot.classList.add('selected');
  }
  dot.addEventListener('click', function () {
    if (dot.classList.contains('selected')) {
      dot.classList.remove('selected');
      selectedLandmarks = selectedLandmarks.filter(l => l !== name);
    } else {
      dot.classList.add('selected');
      if (selectedLandmarks.indexOf(name) === -1) selectedLandmarks.push(name);
    }
  });
});

// Landmark map zoom controls
(function initLandmarkZoom() {
  const layer = document.getElementById('landmark-layer');
  const mapImg = document.getElementById('landmark-map-image');
  const overlay = layer ? layer.querySelector('.landmark-overlay') : null;
  if (!layer || !overlay) return;
  let zoom = 1;

  function applyZoom() {
    const scale = `scale(${zoom})`;
    overlay.style.transform = scale;
    if (mapImg) mapImg.style.transform = scale;
  }

  function setZoom(next) {
    zoom = Math.max(0.9, Math.min(2.2, next));
    applyZoom();
  }

  document.querySelectorAll('.map-zoom-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const action = btn.getAttribute('data-zoom');
      if (action === 'in') setZoom(zoom + 0.1);
      if (action === 'out') setZoom(zoom - 0.1);
      if (action === 'reset') setZoom(1);
    });
  });

  layer.addEventListener('wheel', function (e) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(zoom + delta);
  });

  applyZoom();
})();
