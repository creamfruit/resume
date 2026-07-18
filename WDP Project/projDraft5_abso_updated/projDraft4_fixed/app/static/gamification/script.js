// RE:CONNECT SG - Main JavaScript
// Updated to work with Bootstrap 5.3.2

// # Landmarks catalog used for map rendering and quiz content
const LANDMARKS = [
  { id: 1, name: "Jurong", icon: "\u{1F3ED}", x: 220, y: 310,
    story: "Singapore's industrial heartland that transformed into a hub for innovation, featuring Jurong Bird Park and the upcoming Jurong Lake District.",
    question: "What is Jurong best known for today?",
    options: ["Shopping malls", "Innovation hub", "Beach resorts", "Historic temples"], answer: 1 },

  { id: 2, name: "Chinatown", icon: "\u{1F3EE}", x: 410, y: 350,
    story: "A vibrant district preserving Chinese heritage and culture, where traditional shophouses blend with modern businesses, creating a unique fusion of old and new Singapore.",
    question: "What makes Chinatown special?",
    options: ["Modern skyscrapers", "Blend of heritage and modern life", "Beach activities", "Industrial sites"], answer: 1 },

  { id: 3, name: "Marina Bay", icon: "\u{1F3D9}", x: 490, y: 340,
    story: "This iconic waterfront area features Marina Bay Sands with three towers connected by a sky park 200 meters above ground, offering stunning views of Singapore's skyline.",
    question: "How many towers does Marina Bay Sands have?",
    options: ["2", "3", "4", "5"], answer: 1 },

  { id: 4, name: "Orchard Road", icon: "\u{1F6CD}", x: 380, y: 290,
    story: "Singapore's premier shopping district with over 20 shopping malls. It was once lined with fruit orchards and nutmeg plantations in the 1800s.",
    question: "What was Orchard Road before becoming a shopping district?",
    options: ["Industrial area", "Fruit orchards", "Residential zone", "Fishing village"], answer: 1 },

  { id: 5, name: "Kampong Glam", icon: "\u{1F54C}", x: 520, y: 285,
    story: "The historic Malay-Muslim quarter centered around the golden-domed Sultan Mosque, showcasing rich Islamic heritage and modern creative culture.",
    question: "What is the famous mosque in Kampong Glam?",
    options: ["Blue Mosque", "Sultan Mosque", "Crystal Mosque", "Grand Mosque"], answer: 1 },

  { id: 6, name: "Little India", icon: "\u{1F3DB}", x: 460, y: 270,
    story: "An ethnic district that celebrates Indian culture, featuring colorful streets, aromatic spices, and vibrant festivals like Deepavali that bring the community together.",
    question: "Which festival is famously celebrated in Little India?",
    options: ["Christmas", "Deepavali", "Chinese New Year", "Hari Raya"], answer: 1 },

  { id: 7, name: "Botanic Gardens", icon: "\u{1FAB4}", x: 310, y: 250,
    story: "A UNESCO World Heritage Site founded in 1859, featuring 82 hectares of lush greenery and home to the National Orchid Garden.",
    question: "When was the Singapore Botanic Gardens founded?",
    options: ["1819", "1859", "1900", "1965"], answer: 1 },

  { id: 8, name: "Marina Bay Sands", icon: "\u{1F3E2}", x: 550, y: 325,
    story: "Marina Bay Sands features three towers connected by a sky park 200 meters above ground.",
    question: "How many towers does Marina Bay Sands have?",
    options: ["2", "3", "4", "5"], answer: 1 },

  { id: 9, name: "Changi", icon: "\u{2708}", x: 620, y: 285,
    story: "Home to Changi Airport, consistently rated the world's best airport, and Changi Village with its rich coastal heritage.",
    question: "What is Changi best known for?",
    options: ["Shopping malls", "World-class airport", "Historical museums", "Nature parks"], answer: 1 },

  { id: 10, name: "Sentosa", icon: "\u{1F3DD}", x: 370, y: 470,
    story: "Singapore's island resort destination offering beaches, attractions, and entertainment. The name Sentosa means 'peace and tranquility' in Malay.",
    question: "What does 'Sentosa' mean in Malay?",
    options: ["Peace and tranquility", "Beautiful island", "Paradise beach", "Golden sands"], answer: 0 },
];

// # Default quest catalog for fallback/local usage
const QUESTS = [
    {id: 1, title: 'Join Your First Learning Circle', description: 'Connect with others to learn or share a skill together', reward: 1500, progress: 0, total: 1},
    {id: 2, title: 'Reply in the Community Forum', description: 'Share your thoughts or help answer someone\'s question', reward: 75, progress: 0, total: 1},
    {id: 3, title: 'Share a Skill', description: 'Teach something you know - cooking, language, crafts, anything!', reward: 200, progress: 0, total: 1},
    {id: 4, title: 'Thank a Connection', description: 'Send appreciation to someone who helped you', reward: 50, progress: 0, total: 1},
    {id: 5, title: 'Complete 3 Learning Sessions', description: 'Keep learning and growing with the community', reward: 300, progress: 0, total: 3}
];

// # Badge groups with thresholds and requirement types
const BADGES = {
    'Journey Badges': [
        {id: 1, name: 'First Steps', icon: '\u{1F947}', description: 'Unlock your first landmark', threshold: 1, current: 0, requirement: 'landmarks'},
        {id: 2, name: 'City Explorer', icon: '\u{1F9ED}', description: 'Complete 3 landmarks', threshold: 3, current: 0, requirement: 'landmarks'},
        {id: 3, name: 'Island Voyager', icon: '\u{1F5FA}', description: 'Complete all 10 landmarks', threshold: 10, current: 0, requirement: 'landmarks'}
    ],
    'Community Badges': [
        {id: 4, name: 'Community Builder', icon: '\u{1F9F1}', description: 'Complete 5 quests', threshold: 5, current: 0, requirement: 'quests'},
        {id: 5, name: 'Helpful Guide', icon: '\u{1F9D1}\u{200D}\u{1F3EB}', description: 'Complete 10 quests', threshold: 10, current: 0, requirement: 'quests'},
        {id: 6, name: 'Master Connector', icon: '\u{1F517}', description: 'Complete 20 quests', threshold: 20, current: 0, requirement: 'quests'}
    ],
    'Progress Badges': [
        {id: 7, name: 'Point Collector', icon: '\u{1FA99}', description: 'Earn 1,000 points', threshold: 1000, current: 0, requirement: 'points'},
        {id: 8, name: 'Point Master', icon: '\u{1F3C6}', description: 'Earn 5,000 points', threshold: 5000, current: 0, requirement: 'points'},
        {id: 9, name: 'Tier Ascender', icon: '\u{1F680}', description: 'Reach Tier 3', threshold: 3, current: 1, requirement: 'tier'}
    ]
};

// # Rewards catalog with point costs
const REWARDS = [
    {id: 1, name: '$2 GrabFood Voucher', icon: '\u{1F381}', cost: 500},
    {id: 2, name: '$3 Starbucks Voucher', icon: '\u{2615}', cost: 750},
    {id: 3, name: '$5 Popular Bookstore', icon: '\u{1F4DA}', cost: 1250},
    {id: 4, name: '$5 Kopitiam Voucher', icon: '\u{1FAD6}', cost: 1250},
    {id: 5, name: '$10 NTUC Voucher', icon: '\u{1F6D2}', cost: 2500},
    {id: 6, name: '$10 Watsons Voucher', icon: '\u{1F9F4}', cost: 2500},
    {id: 7, name: '$15 Movie Voucher', icon: '\u{1F39F}', cost: 3750},
    {id: 8, name: '$15 Uniqlo Voucher', icon: '\u{1F455}', cost: 3750}
];

// # Client-side user state (filled by API calls)
let landmarksData = [];
let userData = {
    username: 'Friend',
    totalPoints: 0,
    availablePoints: 0,
    activeDays: 1,
    currentTier: 1,
    currentStreak: 0,
    isAdmin: false,
    landmarksVisited: 0,
    questsCompleted: 0,
    landmarks: [],
    quests: [],
    badges: {}
};

// # Cached API data collections for rendering
let rewardsData = [];
let questsCatalog = [];
let badgesCatalog = [];
let leaderboardData = [];
let checkinDates = new Set();
let skillsData = [];
// # Current user id for API requests
let currentUserId = null;
// # Demo mode flag (used when embedded inside the main app without gamification APIs)
const DEMO_MODE = window.RECONNECT_GAMIFICATION_DEMO === true;
const DB_MODE = window.RECONNECT_GAMIFICATION_DB === true;
const DEMO_USERNAME = window.RECONNECT_USERNAME || 'Friend';
const DEMO_STORAGE_KEY = 'reconnect_gamification_demo_v1';

function demoHeaders(extra) {
    const headers = extra ? { ...extra } : {};
    try {
        const demoId = sessionStorage.getItem('demo_user_id');
        if (demoId) headers['X-Demo-User'] = demoId;
    } catch (e) {
    }
    return headers;
}

function loadDemoState() {
    try {
        const raw = localStorage.getItem(DEMO_STORAGE_KEY);
        if (!raw) return null;
        return JSON.parse(raw);
    } catch (e) {
        return null;
    }
}

function saveDemoState() {
    if (!DEMO_MODE) return;
    try {
        const state = {
            user: {
                username: userData.username,
                totalPoints: userData.totalPoints,
                availablePoints: userData.availablePoints,
                activeDays: userData.activeDays,
                currentTier: userData.currentTier,
                currentStreak: userData.currentStreak,
                landmarksVisited: userData.landmarksVisited
            },
            quests: userData.quests,
            rewards: rewardsData,
            landmarks: userData.landmarks,
            skills: skillsData,
            checkins: Array.from(checkinDates)
        };
        localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
    }
}

function syncDemoRewards() {
    if (!DEMO_MODE) return;
    rewardsData = rewardsData.map(reward => {
        if (reward.status === 'redeemed') return reward;
        const status = userData.availablePoints >= reward.cost ? 'available' : 'locked';
        return { ...reward, status };
    });
}

// # Build a demo skill tree when APIs are not available
function getDemoSkills() {
    return [
        {id: 1, name: 'WhatsApp Basics', description: 'Start a new chat and send a message.', category: 'Digital Basics', icon: 'whatsapp', required_count: 1, progress: 1, completed: true, parent_id: null},
        {id: 2, name: 'Voice Notes', description: 'Record and send a voice message.', category: 'Digital Basics', icon: 'voice', required_count: 2, progress: 1, completed: false, parent_id: 1},
        {id: 3, name: 'Photo Sharing', description: 'Share photos with a connection.', category: 'Digital Basics', icon: 'attachment', required_count: 2, progress: 0, completed: false, parent_id: 1},
        {id: 4, name: 'Online Safety', description: 'Identify suspicious links and scams.', category: 'Safety & Security', icon: 'scam', required_count: 3, progress: 1, completed: false, parent_id: null}
    ];
}

// # Initialize a demo data set for standalone rendering
function initDemo() {
    const saved = loadDemoState();

    userData.username = DEMO_USERNAME;
    userData.isAdmin = false;

    landmarksData = getDefaultLandmarks();

    if (saved) {
        userData.totalPoints = saved.user?.totalPoints ?? 1850;
        userData.availablePoints = saved.user?.availablePoints ?? 900;
        userData.currentTier = saved.user?.currentTier ?? 2;
        userData.activeDays = saved.user?.activeDays ?? 12;
        userData.currentStreak = saved.user?.currentStreak ?? 4;
        userData.landmarksVisited = saved.user?.landmarksVisited ?? 0;

        userData.landmarks = Array.isArray(saved.landmarks)
            ? saved.landmarks
            : landmarksData.map((l, idx) => ({
                id: l.id,
                unlocked: idx < 5,
                completed: idx < 3
            }));

        userData.quests = Array.isArray(saved.quests)
            ? saved.quests
            : QUESTS.map((q, idx) => {
                const progress = idx === 0 ? 1 : (idx === 1 ? 0 : Math.min(q.total - 1, q.total));
                const completed = progress >= q.total;
                return {
                    id: q.id,
                    title: q.title,
                    description: q.description,
                    reward: q.reward,
                    progress,
                    total: q.total,
                    completed
                };
            });

        rewardsData = Array.isArray(saved.rewards)
            ? saved.rewards
            : REWARDS.map(reward => ({
                ...reward,
                status: userData.availablePoints >= reward.cost ? 'available' : 'locked'
            }));

        skillsData = Array.isArray(saved.skills) ? saved.skills : getDemoSkills();
        checkinDates = new Set(Array.isArray(saved.checkins) ? saved.checkins : []);
    } else {
        userData.totalPoints = 1850;
        userData.availablePoints = 900;
        userData.currentTier = 2;
        userData.activeDays = 12;
        userData.currentStreak = 4;

        userData.landmarks = landmarksData.map((l, idx) => ({
            id: l.id,
            unlocked: idx < 5,
            completed: idx < 3
        }));
        userData.landmarksVisited = userData.landmarks.filter(l => l.completed).length;

        userData.quests = QUESTS.map((q, idx) => {
            const progress = idx === 0 ? 1 : (idx === 1 ? 0 : Math.min(q.total - 1, q.total));
            const completed = progress >= q.total;
            return {
                id: q.id,
                title: q.title,
                description: q.description,
                reward: q.reward,
                progress,
                total: q.total,
                completed
            };
        });

        rewardsData = REWARDS.map(reward => ({
            ...reward,
            status: userData.availablePoints >= reward.cost ? 'available' : 'locked'
        }));

        checkinDates = new Set();
        const today = new Date();
        for (let i = 0; i < 10; i++) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            checkinDates.add(d.toISOString().slice(0, 10));
        }

        skillsData = getDemoSkills();
    }

    userData.landmarksVisited = userData.landmarks.filter(l => l.completed).length;
    userData.questsCompleted = userData.quests.filter(q => q.completed).length;
    syncDemoRewards();

    const badgeGroups = {};
    Object.keys(BADGES).forEach(group => {
        badgeGroups[group] = BADGES[group].map(badge => {
            let current = 0;
            if (badge.requirement === 'landmarks') current = userData.landmarksVisited;
            if (badge.requirement === 'quests') current = userData.questsCompleted;
            if (badge.requirement === 'points') current = userData.totalPoints;
            if (badge.requirement === 'tier') current = userData.currentTier;
            const earned = current >= badge.threshold;
            return {
                id: badge.id,
                name: badge.name,
                icon: badge.icon,
                description: badge.description,
                threshold: badge.threshold,
                earned,
                current
            };
        });
    });
    userData.badges = badgeGroups;

    leaderboardData = [
        {username: 'Auntie Mary', total_points: 4200, current_tier: 3},
        {username: 'Uncle Tan', total_points: 3800, current_tier: 3},
        {username: 'You', total_points: userData.totalPoints, current_tier: userData.currentTier},
        {username: 'Mdm Chen', total_points: 1650, current_tier: 2},
        {username: 'Sam', total_points: 1200, current_tier: 1}
    ];

    renderHeader();
    renderTierProgress();
    renderLandmarks();
    renderQuests();
    renderBadges();
    renderRewards();
    renderRedeemedCart();
    renderLeaderboard();
    renderCheckinCalendar();
    renderSkillTree();
    saveDemoState();
}

function applyAchievementsData(payload) {
    if (!payload) return;
    const user = payload.user || {};
    userData.username = user.username || userData.username;
    userData.totalPoints = user.total_points ?? user.totalPoints ?? userData.totalPoints;
    userData.availablePoints = user.available_points ?? user.availablePoints ?? userData.availablePoints;
    userData.activeDays = user.active_days ?? user.activeDays ?? userData.activeDays;
    userData.currentTier = user.current_tier ?? user.currentTier ?? userData.currentTier;
    userData.currentStreak = user.current_streak ?? user.currentStreak ?? userData.currentStreak;

    if (Array.isArray(payload.landmarks)) {
        landmarksData = payload.landmarks.map(l => ({
            id: l.id,
            name: l.name,
            icon: l.icon,
            x: l.x,
            y: l.y,
            story: l.story,
            question: l.question,
            options: Array.isArray(l.options) ? l.options : [],
            answer: l.answer ?? 0
        }));
        userData.landmarks = payload.landmarks.map(l => ({
            id: l.id,
            unlocked: Boolean(l.unlocked),
            completed: Boolean(l.completed)
        }));
    }

    if (Array.isArray(payload.quests)) {
        userData.quests = payload.quests.map(q => ({
            id: q.id,
            title: q.title,
            description: q.description,
            reward: q.reward,
            progress: q.progress ?? 0,
            total: q.total ?? 1,
            completed: Boolean(q.completed)
        }));
    }

    if (payload.badges) {
        userData.badges = payload.badges;
    }

    if (Array.isArray(payload.rewards)) {
        rewardsData = payload.rewards;
    }

    if (Array.isArray(payload.leaderboard)) {
        leaderboardData = payload.leaderboard;
    }

    if (Array.isArray(payload.checkins)) {
        checkinDates = new Set(payload.checkins);
    }

    if (Array.isArray(payload.skills)) {
        skillsData = payload.skills;
    }

    userData.landmarksVisited = userData.landmarks.filter(l => l.completed).length;
    userData.questsCompleted = userData.quests.filter(q => q.completed).length;
}

async function loadAchievements() {
    const res = await fetch('/api/achievements', { headers: demoHeaders() });
    if (!res.ok) return;
    const data = await res.json().catch(() => null);
    if (!data || !data.ok) return;
    applyAchievementsData(data.data);
}

// # Build a safe, normalized landmark list from defaults
function getDefaultLandmarks() {
    return LANDMARKS.map(l => ({
        id: l.id,
        name: l.name,
        icon: l.icon,
        x: l.x,
        y: l.y,
        story: l.story,
        question: l.question,
        options: Array.isArray(l.options) ? l.options : [],
        answer: l.answer ?? 0
    }));
}

// # Resolve the icon shown on the map (fallback to defaults)
function getLandmarkIcon(landmark) {
    if (!landmark) return '';
    const iconText = landmark.icon ? String(landmark.icon).trim() : '';
    if (iconText && iconText.toLowerCase() !== 'pin') {
        return iconText;
    }
    const fallback = LANDMARKS.find(l => l.id === landmark.id || l.name === landmark.name);
    if (fallback && fallback.icon) {
        return fallback.icon;
    }
    return iconText || 'pin';
}

// # Load current session user or redirect to login
async function loadSessionUser() {
    try {
        const res = await fetch('/api/users/current');
        if (!res.ok) {
            window.location.href = '/login';
            return;
        }
        const data = await res.json();
        if (!data.success) {
            window.location.href = '/login';
            return;
        }
        const user = data.user;
        currentUserId = user.id;
        userData.username = user.username || userData.username;
        userData.totalPoints = user.total_points ?? userData.totalPoints;
        userData.availablePoints = user.available_points ?? userData.availablePoints;
        userData.currentTier = user.current_tier ?? userData.currentTier;
        userData.activeDays = user.active_days ?? userData.activeDays;
        userData.currentStreak = user.current_streak ?? userData.currentStreak;
        userData.isAdmin = Boolean(user.is_admin);
    } catch (err) {
        window.location.href = '/login';
    }
}

// # Normalize landmark rows from API to a consistent shape
function normalizeLandmark(row) {
    if (!row) return null;
    return {
        id: row.id,
        name: row.name,
        icon: row.icon,
        x: row.x_coord ?? row.x,
        y: row.y_coord ?? row.y,
        story: row.story,
        question: row.question,
        options: Array.isArray(row.options) ? row.options : [],
        answer: row.correct_answer ?? row.answer ?? 0
    };
}

// # Fetch landmarks, fallback to defaults on error
async function loadLandmarks() {
    try {
        const res = await fetch('/api/landmarks/');
        if (!res.ok) {
            landmarksData = getDefaultLandmarks();
            return;
        }
        const data = await res.json();
        if (data && data.success && Array.isArray(data.landmarks) && data.landmarks.length) {
            landmarksData = data.landmarks
                .map(normalizeLandmark)
                .filter(Boolean);
        } else {
            landmarksData = getDefaultLandmarks();
        }
    } catch (err) {
        landmarksData = getDefaultLandmarks();
    }
}

// # Fetch quest catalog used for quest metadata
async function loadQuestsCatalog() {
    try {
        const res = await fetch('/quests');
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data) && data.length) {
            questsCatalog = data;
        }
    } catch (err) {
    }
}

// # Fetch badge catalog used for badge metadata
async function loadBadgesCatalog() {
    try {
        const res = await fetch('/api/badges/');
        if (!res.ok) return;
        const data = await res.json();
        if (data && data.success && Array.isArray(data.badges)) {
            badgesCatalog = data.badges;
        }
    } catch (err) {
    }
}

// # Fetch rewards for the current user
async function loadRewards() {
    if (!currentUserId) return;
    const res = await fetch(`/api/rewards/?user_id=${currentUserId}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && Array.isArray(data.rewards)) {
        rewardsData = data.rewards;
        if (typeof data.available_points === 'number') {
            userData.availablePoints = data.available_points;
        }
    }
}

// # Fetch dashboard snapshot and merge progress data
async function loadDashboard() {
    if (!currentUserId) return;
    const res = await fetch(`/api/users/${currentUserId}/dashboard`);
    if (!res.ok) return;
    const data = await res.json();
    if (!data || !data.quests) return;
    if (data.user) {
        userData.totalPoints = data.user.total_points ?? userData.totalPoints;
        userData.availablePoints = data.user.available_points ?? userData.availablePoints;
        userData.currentTier = data.user.current_tier ?? userData.currentTier;
        userData.activeDays = data.user.active_days ?? userData.activeDays;
        userData.currentStreak = data.user.current_streak ?? userData.currentStreak;
    }
    const questRows = Array.isArray(data.quests) ? data.quests : [];
    const questProgressMap = new Map();
    questRows.forEach(q => {
        const id = q && q.id != null ? Number(q.id) : null;
        if (id != null && !questProgressMap.has(id)) {
            questProgressMap.set(id, q);
        }
    });
    const questSourceRaw = questsCatalog.length ? questsCatalog : questRows;
    const questSourceMap = new Map();
    questSourceRaw.forEach(q => {
        const id = q && q.id != null ? Number(q.id) : null;
        if (id != null && !questSourceMap.has(id)) {
            questSourceMap.set(id, q);
        }
    });
    userData.quests = Array.from(questSourceMap.values()).map(q => {
        const id = q && q.id != null ? Number(q.id) : null;
        const progressRow = questProgressMap.get(id) || {};
        const totalRequired = Number(q.total_required ?? q.total ?? progressRow.total_required ?? progressRow.total ?? 1);
        const progress = Number(progressRow.progress ?? 0);
        const completedFlag = Number(progressRow.completed ?? 0) === 1;
        const completed = completedFlag || progress >= totalRequired;
        return {
            id,
            title: q.title ?? progressRow.title,
            description: q.description ?? progressRow.description,
            reward: q.reward ?? progressRow.reward,
            progress,
            total: totalRequired,
            completed
        };
    });
    userData.questsCompleted = userData.quests.filter(q => q.completed).length;

    const landmarkStatus = new Map();
    if (Array.isArray(data.landmarks)) {
        data.landmarks.forEach(l => {
            const id = l && l.id != null ? Number(l.id) : null;
            if (id != null && !landmarkStatus.has(id)) {
                landmarkStatus.set(id, l);
            }
        });
        if (!landmarksData.length) {
            landmarksData = data.landmarks
                .map(normalizeLandmark)
                .filter(Boolean);
        }
    }
    userData.landmarks = landmarksData.map(l => {
        const id = l && l.id != null ? Number(l.id) : null;
        const db = landmarkStatus.get(id);
        return {
            id,
            unlocked: db ? Boolean(db.unlocked) : false,
            completed: db ? Boolean(db.completed) : false
        };
    });
    if (!userData.landmarks.length && landmarksData.length) {
        userData.landmarks = landmarksData.map(l => ({
            id: l.id,
            unlocked: false,
            completed: false
        }));
    }
    userData.landmarksVisited = userData.landmarks.filter(l => l.completed).length;

    if (Array.isArray(data.badges) || badgesCatalog.length) {
        const grouped = {};
        const badgeProgressMap = new Map();
        (Array.isArray(data.badges) ? data.badges : []).forEach(badge => {
            const id = badge && badge.id != null ? Number(badge.id) : null;
            if (id != null && !badgeProgressMap.has(id)) {
                badgeProgressMap.set(id, badge);
            }
        });
        const badgeSourceRaw = badgesCatalog.length ? badgesCatalog : (Array.isArray(data.badges) ? data.badges : []);
        const badgeSourceMap = new Map();
        badgeSourceRaw.forEach(badge => {
            const id = badge && badge.id != null ? Number(badge.id) : null;
            if (id != null && !badgeSourceMap.has(id)) {
                badgeSourceMap.set(id, badge);
            }
        });
        Array.from(badgeSourceMap.values()).forEach(badge => {
            const id = badge && badge.id != null ? Number(badge.id) : null;
            const progressRow = badgeProgressMap.get(id) || {};
            const category = badge.category || progressRow.category || "Badges";
            if (!grouped[category]) {
                grouped[category] = [];
            }
            const threshold = Number(badge.threshold ?? progressRow.threshold ?? 1);
            const rawCurrent = progressRow.current;
            const current = Number.isFinite(rawCurrent) ? Number(rawCurrent) : null;
            grouped[category].push({
                id,
                name: badge.name ?? progressRow.name,
                icon: badge.icon ?? progressRow.icon,
                description: badge.description ?? progressRow.description,
                threshold,
                earned: Number(progressRow.earned ?? 0) === 1,
                current
            });
        });
        userData.badges = grouped;
    }

    if (Array.isArray(data.rewards)) {
        rewardsData = data.rewards;
    }
}

// # Fetch leaderboard rows
async function loadLeaderboard() {
    const res = await fetch('/api/users/leaderboard');
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && Array.isArray(data.leaders)) {
        leaderboardData = data.leaders;
    }
}

// # Fetch user check-in history
async function loadCheckins() {
    if (!currentUserId) return;
    const res = await fetch(`/api/users/${currentUserId}/checkins`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && Array.isArray(data.checkins)) {
        checkinDates = new Set(data.checkins);
        if (typeof data.current_streak === 'number') {
            userData.currentStreak = data.current_streak;
        }
    }
}

// # Fetch user skill tree progress
async function loadSkills() {
    if (!currentUserId) return;
    const res = await fetch(`/api/users/${currentUserId}/skills`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && Array.isArray(data.skills)) {
        skillsData = data.skills;
    }
}

// # Hook logout button to session endpoint
function setupLogout() {
    const btn = document.getElementById('logoutBtn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        try {
            await fetch('/api/users/logout', {method: 'POST'});
        } catch (err) {
        }
        window.location.href = '/login';
    });
}

// # Show/hide admin link based on user role
function setupAdminLink() {
    const link = document.getElementById('adminLink');
    if (!link) return;
    if (userData.isAdmin) {
        link.classList.remove('d-none');
    } else {
        link.classList.add('d-none');
    }
}

// # Map short icon names to emoji
function normalizeIcon(icon) {
    const map = {
        gift: "\u{1F381}",
        cup: "\u{2615}",
        book: "\u{1F4DA}",
        pin: "\u{1F4CD}",
        star: "\u{2B50}",
        heart: "\u{1FAF6}",
        coin: "\u{1FA99}",
        badge: "\u{1F3C5}",
        bread: "\u{1FAD6}",
        cart: "\u{1F6D2}",
        bag: "\u{1F9F4}",
        ticket: "\u{1F39F}",
        shirt: "\u{1F455}"
    };
    if (!icon) return "\u{1F3C5}";
    const text = String(icon).trim();
    if (text.length <= 2) return text;
    const lower = text.toLowerCase();
    if (/^[a-z]+$/.test(lower)) {
        return map[lower] || "\u{1F3C5}";
    }
    return "\u{1F3C5}";
}

// # Resolve badge emoji based on name or custom icon
function getBadgeIcon(badge, earned) {
    if (!earned) {
        return '\u{1F512}';
    }
    const name = (badge && badge.name ? badge.name : '').toLowerCase();
    if (name.includes('first')) return '\u{1F947}';
    if (name.includes('explorer')) return '\u{1F9ED}';
    if (name.includes('voyager')) return '\u{1F5FA}';
    if (name.includes('builder')) return '\u{1F9F1}';
    if (name.includes('guide')) return '\u{1F9D1}\u{200D}\u{1F3EB}';
    if (name.includes('connector')) return '\u{1F517}';
    if (name.includes('collector')) return '\u{1FA99}';
    if (name.includes('master')) return '\u{1F3C6}';
    if (name.includes('tier')) return '\u{1F680}';
    return normalizeIcon(badge.icon);
}

// # Ask backend to evaluate badge progress, then re-render
async function syncBadges() {
    if (DEMO_MODE) {
        renderBadges();
        return;
    }
    if (DB_MODE) {
        return;
    }
    if (!currentUserId) return;
    try {
        await fetch(`/api/users/${currentUserId}/achievements/check`, {method: 'POST'});
    } catch (err) {
    }
    await loadDashboard();
    renderHeader();
    renderTierProgress();
    renderLandmarks();
    renderQuests();
    renderBadges();
    renderRewards();
    renderRedeemedCart();
}

// Initialize
// # App entry point
function init() {
    if (DEMO_MODE) {
        initDemo();
        return;
    }
    if (DB_MODE) {
        (async () => {
            await loadAchievements();
            renderHeader();
            renderTierProgress();
            renderLandmarks();
            renderQuests();
            renderBadges();
            renderRewards();
            renderRedeemedCart();
            renderLeaderboard();
            renderCheckinCalendar();
            renderSkillTree();
        })();
        return;
    }
    (async () => {
        await loadSessionUser();
        await loadQuestsCatalog();
        await loadBadgesCatalog();
        await loadLandmarks();
        await loadRewards();
        await loadDashboard();
        await loadLeaderboard();
        await loadCheckins();
        await loadSkills();
        await syncBadges();
        setupLogout();
        setupAdminLink();
        renderLeaderboard();
        renderCheckinCalendar();
        renderSkillTree();
    })();
}

// Render Header
function renderHeader() {
    document.getElementById('userName').textContent = userData.username;
    document.getElementById('tierBadge').textContent = `Tier ${userData.currentTier}`;
    document.getElementById('multiplierBadge').textContent = 'Multiplier set by server';
    document.getElementById('totalPoints').textContent = userData.totalPoints;
    document.getElementById('landmarkCount').textContent = userData.landmarksVisited;
    document.getElementById('activeDays').textContent = userData.activeDays;
    const streakEl = document.getElementById('streakCount');
    if (streakEl) streakEl.textContent = userData.currentStreak;
}

// Render Tier Progress
function renderTierProgress() {
    document.getElementById('tierProgressPoints').textContent = `${userData.totalPoints} total points`;
    document.getElementById('tierProgressFill').style.width = '0%';
    document.querySelector('.tier-progress-hint').textContent =
        'Tier progress and multipliers are calculated on the server.';
    const countdown = document.getElementById('tierCountdown');
    if (countdown) countdown.textContent = `Current tier: ${userData.currentTier}`;
}

// Render Landmarks on Map
function renderLandmarks() {
    const container = document.getElementById('landmarkMarkers');
    if (!container) return;
    
    container.innerHTML = '';

    if (!landmarksData.length || !userData.landmarks.length) {
        document.getElementById('nextLandmarkProgress').style.width = '0%';
        document.getElementById('nextLandmarkText').innerHTML = 'No landmarks available yet.';
        return;
    }
    
    const nextUnlockedIndex = userData.landmarks.findIndex(l => !l.unlocked);
    const pointsToNext = (nextUnlockedIndex === -1) ? 0 : (nextUnlockedIndex + 1) * 1000;
    
    // Update progress bar
    if (nextUnlockedIndex === -1) {
        document.getElementById('nextLandmarkProgress').style.width = '100%';
        document.getElementById('nextLandmarkText').innerHTML = 'All landmarks visited! \u{1F389}';
    } else {
        const progress = ((userData.totalPoints % 1000) / 1000) * 100;
        const remaining = pointsToNext - userData.totalPoints;
        
        document.getElementById('nextLandmarkProgress').style.width = progress + '%';
        document.getElementById('nextLandmarkText').innerHTML = 
            `Earn <strong>${remaining} more points</strong> to unlock ${landmarksData[nextUnlockedIndex].name}`;
    }
    
    // Render each landmark
    landmarksData.forEach((landmark, index) => {
        const userLandmark = userData.landmarks[index];
        const isLocked = !userLandmark.unlocked;
        const isCurrent = index === nextUnlockedIndex && userData.totalPoints >= pointsToNext;
        const isCompleted = userLandmark.completed;
        
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', `landmark-marker ${isLocked ? 'locked' : ''} ${isCurrent ? 'current' : ''}`);
        g.style.pointerEvents = 'bounding-box';
        
        // Circle background
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', landmark.x);
        circle.setAttribute('cy', landmark.y);
        circle.setAttribute('r', 28);
        circle.style.pointerEvents = 'none';
        
        if (isLocked) {
            circle.setAttribute('fill', '#E5E5E5');
            circle.setAttribute('stroke', '#A3A3A3');
        } else if (isCompleted) {
            circle.setAttribute('fill', '#FF8C5F');
            circle.setAttribute('stroke', '#FF6B35');
        } else if (isCurrent) {
            circle.setAttribute('fill', '#FF6B35');
            circle.setAttribute('stroke', '#FF6B35');
        } else {
            circle.setAttribute('fill', '#00ADB5');
            circle.setAttribute('stroke', '#00ADB5');
        }
        circle.setAttribute('stroke-width', 2.5);
        g.appendChild(circle);
        
        // Icon
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', landmark.x);
        text.setAttribute('y', landmark.y + 9);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', 22);
        text.style.pointerEvents = 'none';
        text.textContent = isLocked ? '\u{1F512}' : normalizeIcon(getLandmarkIcon(landmark));
        g.appendChild(text);
        
        // Checkmark for completed
        if (isCompleted) {
            const check = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            check.setAttribute('x', landmark.x + 16);
            check.setAttribute('y', landmark.y - 12);
            check.setAttribute('font-size', 16);
            check.setAttribute('fill', '#FFFFFF');
            check.style.pointerEvents = 'none';
            check.textContent = '\u{2705}';
            g.appendChild(check);
        }
        
        // Click handler
        if (isCurrent) {
            g.style.cursor = 'pointer';
            g.addEventListener('click', () => unlockLandmark(index));
        } else if (!isLocked && !isCompleted) {
            g.style.cursor = 'pointer';
            g.addEventListener('click', () => showQuiz(index));
        }
        
        container.appendChild(g);
    });
}

// Unlock Landmark
function unlockLandmark(index) {
    const pointsNeeded = (index + 1) * 1000;
    if (userData.totalPoints < pointsNeeded) {
        showNotification('Not enough points yet!', 'info');
        return;
    }

    const landmark = userData.landmarks[index];
    if (DEMO_MODE) {
        landmark.unlocked = true;
        renderHeader();
        renderLandmarks();
        showNotification(`🗺️ ${landmarksData[index].name} unlocked!`, 'success');
        setTimeout(() => showQuiz(index), 400);
        saveDemoState();
        return;
    }
    if (DB_MODE) {
        fetch(`/api/achievements/landmarks/${landmark.id}/unlock`, {method: 'POST', headers: demoHeaders()})
            .then(res => res.json())
            .then(data => {
                if (!data || !data.ok) {
                    showNotification((data && data.error) || 'Unable to unlock landmark', 'warning');
                    return;
                }
                applyAchievementsData(data.data);
                renderHeader();
                renderLandmarks();
                showNotification(`🗺️ ${landmarksData[index].name} unlocked!`, 'success');
                setTimeout(() => showQuiz(index), 400);
            })
            .catch(() => showNotification('Unable to unlock landmark', 'warning'));
        return;
    }
    fetch(`/api/users/${currentUserId}/landmarks/${landmark.id}/unlock`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'warning');
                return;
            }
            landmark.unlocked = true;
            renderHeader();
            renderLandmarks();
            showNotification(`\u{1F5FA} ${landmarksData[index].name} unlocked!`, 'success');
            setTimeout(() => showQuiz(index), 500);
        })
        .catch(() => showNotification('Unable to unlock landmark', 'warning'));
}

// Show Quiz Modal using Bootstrap
function showQuiz(index) {
    const landmark = landmarksData[index];
    
    document.getElementById('modalIcon').textContent = normalizeIcon(getLandmarkIcon(landmark));
    document.getElementById('modalTitle').textContent = landmark.name;
    document.getElementById('modalStory').textContent = landmark.story;
    document.getElementById('modalQuestion').textContent = landmark.question;
    
    const optionsContainer = document.getElementById('quizOptions');
    optionsContainer.innerHTML = '';

    if (!Array.isArray(landmark.options) || !landmark.options.length) {
        optionsContainer.innerHTML = '<div class="text-muted">No quiz options available for this landmark yet.</div>';
    } else {
        landmark.options.forEach((option, i) => {
            const btn = document.createElement('button');
            btn.className = 'btn btn-outline-secondary quiz-option';
            btn.textContent = option;
            btn.onclick = () => checkAnswer(index, i);
            optionsContainer.appendChild(btn);
        });
    }
    
    const feedback = document.getElementById('quizFeedback');
    feedback.classList.add('d-none');
    feedback.classList.remove('alert-success', 'alert-danger');
    
    document.getElementById('modalAction').classList.add('d-none');
    
    const modal = new bootstrap.Modal(document.getElementById('landmarkModal'));
    modal.show();
}

// Check Answer
function checkAnswer(landmarkIndex, answerIndex) {
    const landmark = landmarksData[landmarkIndex];
    const feedback = document.getElementById('quizFeedback');
    const options = document.querySelectorAll('.quiz-option');
    
    if (answerIndex === landmark.answer) {
        options[answerIndex].classList.remove('btn-outline-secondary');
        options[answerIndex].classList.add('btn-success', 'correct');
        
        feedback.classList.remove('d-none', 'alert-danger');
        feedback.classList.add('alert-success');
        feedback.textContent = '\u{2705} Correct! Updating your rewards...';

        const userLandmark = userData.landmarks[landmarkIndex];
        if (DEMO_MODE) {
            const earnedPoints = 200;
            userLandmark.completed = true;
            userData.totalPoints += earnedPoints;
            userData.availablePoints += earnedPoints;
            userData.landmarksVisited = userData.landmarks.filter(l => l.completed).length;
            syncDemoRewards();
            feedback.textContent = `\u{2705} Correct! You earned ${earnedPoints} points`;
            renderHeader();
            renderTierProgress();
            renderLandmarks();
            renderBadges();
            renderRewards();
            renderRedeemedCart();
            document.getElementById('quizOptions').style.display = 'none';
            document.getElementById('modalAction').classList.remove('d-none');
            saveDemoState();
            return;
        }
    if (DB_MODE) {
        fetch(`/api/achievements/landmarks/${userLandmark.id}/complete`, {method: 'POST', headers: demoHeaders()})
            .then(res => res.json())
            .then(data => {
                    if (!data || !data.ok) {
                        showNotification((data && data.error) || 'Unable to complete landmark', 'warning');
                        return;
                    }
                    applyAchievementsData(data.data);
                    const earnedPoints = data.awarded_points ?? 0;
                    feedback.textContent = `\u2705 Correct! You earned ${earnedPoints} points`;
                    renderHeader();
                    renderTierProgress();
                    renderLandmarks();
                    renderBadges();
                    renderRewards();
                    renderRedeemedCart();
                })
                .catch(() => showNotification('Unable to complete landmark', 'warning'));
            document.getElementById('quizOptions').style.display = 'none';
            document.getElementById('modalAction').classList.remove('d-none');
            renderLandmarks();
            return;
        }
        fetch(`/api/users/${currentUserId}/landmarks/${userLandmark.id}/complete`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        })
            .then(res => res.json())
            .then(async data => {
                if (data.error) {
                    showNotification(data.error, 'warning');
                    return;
                }
                const earnedPoints = data.awarded_points ?? 0;
                feedback.textContent = `\u{2705} Correct! You earned ${earnedPoints} points`;
                userLandmark.completed = true;
                userData.landmarksVisited = userData.landmarks.filter(l => l.completed).length;
                await loadDashboard();
                renderHeader();
                renderTierProgress();
                renderLandmarks();
                renderBadges();
                renderRewards();
                renderRedeemedCart();
            })
            .catch(() => showNotification('Unable to complete landmark', 'warning'));
        
        document.getElementById('quizOptions').style.display = 'none';
        document.getElementById('modalAction').classList.remove('d-none');
        
        renderLandmarks();
    } else {
        options[answerIndex].classList.remove('btn-outline-secondary');
        options[answerIndex].classList.add('btn-danger', 'incorrect');
        
        feedback.classList.remove('d-none', 'alert-success');
        feedback.classList.add('alert-danger');
        feedback.textContent = 'Not quite. Try again!';
        
        setTimeout(() => {
            options[answerIndex].classList.remove('btn-danger', 'incorrect');
            options[answerIndex].classList.add('btn-outline-secondary');
            feedback.classList.add('d-none');
        }, 1500);
    }
}

// Continue Journey
function continueJourney() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('landmarkModal'));
    modal.hide();
    showNotification('Keep going! Your next landmark awaits.', 'info');
}

// Close Modal (no longer needed with Bootstrap, but kept for compatibility)
function closeModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('landmarkModal'));
    if (modal) modal.hide();
}

// Render Quests
// # Render quests into active/completed lists
function renderQuests() {
    const activeContainer = document.getElementById('activeQuestList');
    const completedContainer = document.getElementById('completedQuestList');
    if (activeContainer) activeContainer.innerHTML = '';
    if (completedContainer) completedContainer.innerHTML = '';
    
    userData.quests.forEach(quest => {
        const progressPercent = (quest.progress / quest.total) * 100;
        const isCompleted = quest.completed || quest.progress >= quest.total;
        
        const questCard = document.createElement('div');
        questCard.className = 'card mb-3';
        questCard.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="card-title mb-0">${quest.title}</h5>
                    <span class="badge quest-reward-badge rounded-pill">+${quest.reward} pts</span>
                </div>
                <p class="card-text text-muted small mb-3">${quest.description}</p>
                <div class="d-flex align-items-center gap-2 mb-2">
                    <div class="progress flex-grow-1" style="height: 8px;">
                        <div class="progress-bar bg-info" role="progressbar" style="width: ${progressPercent}%" aria-valuenow="${quest.progress}" aria-valuemin="0" aria-valuemax="${quest.total}"></div>
                    </div>
                    <small class="text-muted fw-semibold">${quest.progress}/${quest.total}</small>
                </div>
                  <div class="small ${isCompleted ? 'text-success fw-semibold' : 'text-muted'}">
                      ${isCompleted ? 'Completed' : 'In progress'}
                  </div>
              </div>
          `;
        if (isCompleted) {
            if (completedContainer) completedContainer.appendChild(questCard);
        } else if (activeContainer) {
            activeContainer.appendChild(questCard);
        }
    });

    if (completedContainer && !completedContainer.children.length) {
        completedContainer.innerHTML = '<div class="text-muted">No completed quests yet.</div>';
    }
}

// Start Quest (no auto-complete)
function startQuest(questId) {
    const quest = userData.quests.find(q => q.id === questId);
    if (!quest) return;
    const title = (quest.title || '').toLowerCase();
    if (title.includes('forum')) {
        window.location.href = '/forum';
        return;
    }
    if (title.includes('chat') || title.includes('message')) {
        window.location.href = '/messages';
        return;
    }
    if (title.includes('match') || title.includes('connect')) {
        window.location.href = '/matching';
        return;
    }
    showNotification('Quest started! Complete the activity to gain progress.', 'info');
}

// Complete Quest
// # Increment quest progress and refresh dashboard data
function completeQuest(questId) {
    if (DEMO_MODE) {
        const quest = userData.quests.find(q => q.id === questId);
        if (!quest || quest.progress >= quest.total) return;
        quest.progress += 1;
        if (quest.progress >= quest.total) {
            quest.completed = true;
            userData.totalPoints += quest.reward;
            userData.availablePoints += quest.reward;
        }
        userData.questsCompleted = userData.quests.filter(q => q.completed).length;
        syncDemoRewards();
        renderHeader();
        renderQuests();
        renderBadges();
        renderRewards();
        renderRedeemedCart();
        saveDemoState();
        showNotification(quest.completed ? 'Quest completed!' : 'Progress made!', quest.completed ? 'success' : 'info');
        return;
    }
    if (DB_MODE) {
        fetch(`/api/achievements/quests/${questId}/progress`, {method: 'POST', headers: demoHeaders()})
            .then(res => res.json())
            .then(data => {
                if (!data || !data.ok) {
                    showNotification('Unable to update quest', 'warning');
                    return;
                }
                applyAchievementsData(data.data);
                renderHeader();
                renderQuests();
                renderBadges();
                renderRewards();
                renderRedeemedCart();
                showNotification('Progress updated!', 'success');
            })
            .catch(() => showNotification('Unable to update quest', 'warning'));
        return;
    }
    if (!currentUserId) {
        showNotification('Please log in to start quests', 'warning');
        return;
    }
    const quest = userData.quests.find(q => q.id === questId);
    if (!quest || quest.progress >= quest.total) return;

    fetch(`/api/users/${currentUserId}/quests/${questId}/progress`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({increment: 1})
    })
        .then(async res => {
            if (res.status === 401) {
                window.location.href = '/login';
                return null;
            }
            const data = await res.json().catch(() => null);
            if (!res.ok || !data) {
                showNotification('Unable to update quest', 'warning');
                return null;
            }
            return data;
        })
        .then(async data => {
            if (!data) return;
            if (data.error) {
                showNotification(data.error, 'warning');
                return;
            }
            await loadDashboard();
            renderHeader();
            renderTierProgress();
            renderQuests();
            renderBadges();
            renderRewards();
            renderRedeemedCart();
            if (data.completed) {
                showNotification(`\u{2705} Quest completed!`, 'success');
                syncBadges();
            } else {
                showNotification('Progress made!', 'info');
            }
        })
        .catch(() => {
            showNotification('Unable to update quest', 'warning');
        });
}

// Render Badges
// # Render badge groups with progress indicators
function renderBadges() {
    const container = document.getElementById('badgeGroups');
    container.innerHTML = '';
    
    Object.keys(userData.badges).forEach(groupName => {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'mb-4';
        
        const title = document.createElement('h5');
        title.className = 'border-bottom pb-2 mb-3';
        title.textContent = groupName;
        groupDiv.appendChild(title);
        
        const row = document.createElement('div');
        row.className = 'row g-3';
        
        userData.badges[groupName].forEach(badge => {
            const hasProgress = Number.isFinite(badge.current);
            const earned = Boolean(badge.earned);
            const inProgress = hasProgress && badge.current > 0 && !earned;
            const progressPercent = hasProgress
                ? Math.min((badge.current / badge.threshold) * 100, 100)
                : 0;
            
            const col = document.createElement('div');
            col.className = 'col-md-4 col-lg-3';
            
            const card = document.createElement('div');
            card.className = 'card h-100 badge-card';
            if (earned) card.classList.add('earned');
            if (inProgress) card.classList.add('in-progress');
            
            card.innerHTML = `
                <div class="card-body text-center">
                    <div class="display-4 mb-2">${getBadgeIcon(badge, earned)}</div>
                    <h6 class="card-title">${badge.name}</h6>
                    <p class="card-text small text-muted">${badge.description}</p>
                    ${!earned && hasProgress ? `
                        <div class="progress mt-2" style="height: 4px;">
                            <div class="progress-bar bg-info" role="progressbar" style="width: ${progressPercent}%"></div>
                        </div>
                    ` : ''}
                </div>
            `;
            
            col.appendChild(card);
            row.appendChild(col);
        });
        
        groupDiv.appendChild(row);
        container.appendChild(groupDiv);
    });
}

// Render Rewards
// # Render rewards grid and redeem buttons
function renderRewards() {
    const container = document.getElementById('rewardGrid');
    container.innerHTML = '';
    
    rewardsData.forEach(reward => {
        const progressPercent = Math.min((userData.availablePoints / reward.cost) * 100, 100);
        const remaining = Math.max(reward.cost - userData.availablePoints, 0);
        const status = reward.status || (userData.availablePoints >= reward.cost ? 'available' : 'locked');
        const canRedeem = status === 'available';
        const isRedeemed = status === 'redeemed';
        
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4';
        
        const card = document.createElement('div');
        card.className = 'card h-100';
        card.innerHTML = `
            <div class="card-body">
                <div class="text-center mb-3">
                    <div class="display-4">${normalizeIcon(reward.icon)}</div>
                </div>
                <h5 class="card-title">${reward.name}</h5>
                <p class="h4 text-primary mb-3">$${reward.cost / 250}</p>
                <div class="progress mb-2" style="height: 8px;">
                    <div class="progress-bar bg-info" role="progressbar" style="width: ${progressPercent}%"></div>
                </div>
                <p class="small text-muted mb-3">${isRedeemed ? 'Redeemed' : (canRedeem ? 'Ready to redeem!' : remaining + ' points needed')}</p>
                <button class="btn btn-orange w-100" onclick="redeemReward(${reward.id})" ${(!canRedeem || isRedeemed) ? 'disabled' : ''}>
                    ${isRedeemed ? 'Redeemed' : 'Redeem'}
                </button>
            </div>
        `;
        
        col.appendChild(card);
        container.appendChild(col);
    });
}

// Redeem Reward
// # Redeem a reward and refresh balances
async function redeemReward(rewardId) {
    if (DEMO_MODE) {
        const reward = rewardsData.find(r => r.id === rewardId);
        if (!reward) return;
        if (userData.availablePoints < reward.cost) {
            showNotification('Not enough points to redeem this reward', 'warning');
            return;
        }
        reward.status = 'redeemed';
        userData.availablePoints -= reward.cost;
        syncDemoRewards();
        showNotification(`🎁 Redeemed ${reward.name}!`, 'success');
        renderHeader();
        renderRewards();
        renderRedeemedCart();
        saveDemoState();
        return;
    }
    if (DB_MODE) {
        const res = await fetch(`/api/achievements/rewards/${rewardId}/redeem`, {method: 'POST', headers: demoHeaders()});
        const data = await res.json().catch(() => null);
        if (!data || !data.ok) {
            showNotification((data && data.error) || 'Unable to redeem reward', 'warning');
            return;
        }
        applyAchievementsData(data.data);
        renderHeader();
        renderRewards();
        renderRedeemedCart();
        showNotification('Redeemed reward!', 'success');
        return;
    }
    const reward = rewardsData.find(r => r.id === rewardId);
    if (!reward) return;

    const res = await fetch(`/api/rewards/${rewardId}/redeem`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: currentUserId})
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
        showNotification(data.error || 'Unable to redeem reward', 'warning');
        return;
    }

    if (typeof data.remaining_points === 'number') {
        userData.availablePoints = data.remaining_points;
    }

    showNotification(`\u{1F381} Redeemed ${reward.name}!`, 'success');
    await loadRewards();
    renderHeader();
    renderRewards();
    renderRedeemedCart();
}

// # Render list of redeemed rewards
function renderRedeemedCart() {
    const container = document.getElementById('redeemedCart');
    if (!container) return;
    const redeemed = rewardsData.filter(r => r.status === 'redeemed');
    if (!redeemed.length) {
        container.innerHTML = '<div class="text-muted">No redeemed rewards yet.</div>';
        return;
    }
    container.innerHTML = redeemed.map(r => `
        <div class="d-flex justify-content-between align-items-center border-bottom py-2">
            <div>${r.name}</div>
            <span class="badge bg-success">Redeemed</span>
        </div>
    `).join('');
}

// # Render leaderboard table rows
function renderLeaderboard() {
    const container = document.getElementById('leaderboardRows');
    if (!container) return;
    if (!leaderboardData.length) {
        container.innerHTML = '<tr><td colspan="4" class="text-muted">No leaderboard data yet.</td></tr>';
        return;
    }
    container.innerHTML = leaderboardData.map((row, index) => `
        <tr>
            <td>${index + 1}</td>
            <td>${row.username}</td>
            <td>${row.total_points}</td>
            <td>${row.current_tier}</td>
        </tr>
    `).join('');
}

// # Render a 30-day check-in grid
function renderCheckinCalendar() {
    const container = document.getElementById('checkinCalendar');
    if (!container) return;
    const summary = document.getElementById('checkinSummary');
    if (summary) {
        summary.textContent = `${userData.currentStreak} day streak`;
    }
    const today = new Date();
    const days = 30;
    const cells = [];
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const iso = d.toISOString().slice(0, 10);
        const checked = checkinDates.has(iso);
        const label = d.getDate();
        const classes = ['checkin-cell'];
        if (checked) {
            classes.push('checked');
        } else if (d < today) {
            classes.push('missed');
        }
        cells.push(`<div class="${classes.join(' ')}" title="${iso}">${label}</div>`);
    }
    container.innerHTML = cells.join('');
}

// # Render skill tree groups and progress
function renderSkillTree() {
    const container = document.getElementById('skillTree');
    if (!container) return;
    if (!skillsData.length) {
        container.innerHTML = '<div class="text-muted">No skills available yet.</div>';
        return;
    }

    const skillMap = new Map();
    skillsData.forEach(skill => skillMap.set(skill.id, skill));

    const totalSkills = skillsData.length;
    const completedSkills = skillsData.filter(skill => skill.completed).length;
    const overallPercent = totalSkills ? Math.round((completedSkills / totalSkills) * 100) : 0;

    const iconMap = {
        whatsapp: '\u{1F4F1}',
        emoji: '\u{1F63A}',
        voice: '\u{1F3A4}',
        video: '\u{1F4F9}',
        group: '\u{1F465}',
        email: '\u{1F4E7}',
        attachment: '\u{1F4CE}',
        bank: '\u{1F3E6}',
        balance: '\u{1F4B0}',
        transfer: '\u{1F4B8}',
        bill: '\u{1F9FE}',
        scam: '\u{1F6A8}',
        password: '\u{1F511}',
        privacy: '\u{1F512}',
    };

    const getLevel = (skill) => {
        let level = 0;
        let parentId = skill.parent_id;
        while (parentId) {
            level += 1;
            const parent = skillMap.get(parentId);
            parentId = parent ? parent.parent_id : null;
        }
        return level;
    };

    const grouped = {};
    skillsData.forEach(skill => {
        grouped[skill.category] = grouped[skill.category] || [];
        grouped[skill.category].push(skill);
    });

    const groupBlocks = Object.keys(grouped).map(category => {
        const groupSkills = grouped[category];
        const groupCompleted = groupSkills.filter(skill => skill.completed).length;
        const groupPercent = groupSkills.length ? Math.round((groupCompleted / groupSkills.length) * 100) : 0;

        const items = groupSkills.map(skill => {
            const level = getLevel(skill);
            const progress = Math.min((skill.progress / skill.required_count) * 100, 100);
            const completed = Boolean(skill.completed);
            const parent = skill.parent_id ? skillMap.get(skill.parent_id) : null;
            const locked = parent && !parent.completed;
            const status = completed ? 'completed' : (locked ? 'locked' : (skill.progress > 0 ? 'progress' : 'available'));
            const buttonLabel = completed ? 'Completed' : (locked ? 'Locked' : 'Mark as Taught');
            const icon = iconMap[skill.icon] || '\u{1F4DA}';
            const requirement = parent ? `Requires ${parent.name}` : '';
            return `
                <div class="skill-node skill-${status}" style="margin-left:${level * 20}px">
                    <div class="skill-title">
                        <span class="skill-name">${icon} ${skill.name}</span>
                        <span class="skill-status">${skill.progress}/${skill.required_count}</span>
                    </div>
                    <div class="skill-desc">${skill.description}</div>
                    ${locked ? `<div class="skill-req">${requirement}</div>` : ''}
                    <div class="progress mb-2" style="height: 6px;">
                        <div class="progress-bar bg-info" style="width:${progress}%"></div>
                    </div>
                    <button class="btn btn-sm btn-outline-teal" ${completed || locked ? 'disabled' : ''} onclick="updateSkillProgress(${skill.id})">
                        ${buttonLabel}
                    </button>
                </div>
            `;
        }).join('');
        return `
            <div class="skill-group">
                <div class="skill-group-header">
                    <h6 class="skill-group-title">${category}</h6>
                    <span class="skill-group-progress">${groupPercent}% complete</span>
                </div>
                ${items}
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="skill-summary mb-3">
            <div class="skill-summary-title">Digital Literacy Mastery</div>
            <div class="skill-summary-progress">${overallPercent}% complete</div>
            <div class="progress mt-2" style="height: 8px;">
                <div class="progress-bar bg-info" style="width:${overallPercent}%"></div>
            </div>
            <div class="small text-muted mt-1">${completedSkills} / ${totalSkills} skills mastered</div>
        </div>
        ${groupBlocks}
    `;
}

// # Update skill progress and show notifications
async function updateSkillProgress(skillId) {
    if (DEMO_MODE) {
        const skill = skillsData.find(s => s.id === skillId);
        if (!skill || skill.completed) return;
        skill.progress = Math.min(skill.progress + 1, skill.required_count);
        if (skill.progress >= skill.required_count) {
            skill.completed = true;
            userData.totalPoints += 50;
            userData.availablePoints += 50;
            showNotification('Skill completed! +50 pts', 'success');
        } else {
            showNotification('Skill progress updated!', 'info');
        }
        syncDemoRewards();
        renderHeader();
        renderSkillTree();
        saveDemoState();
        return;
    }
    if (DB_MODE) {
        const res = await fetch(`/api/achievements/skills/${skillId}/progress`, {method: 'POST', headers: demoHeaders()});
        const data = await res.json().catch(() => null);
        if (!data || !data.ok) {
            showNotification((data && data.error) || 'Unable to update skill', 'warning');
            return;
        }
        applyAchievementsData(data.data);
        renderHeader();
        renderSkillTree();
        showNotification('Skill updated!', 'success');
        return;
    }
    const res = await fetch(`/api/users/${currentUserId}/skills/${skillId}/progress`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({increment: 1})
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
        showNotification(data.error || 'Unable to update skill', 'warning');
        return;
    }
    await loadSkills();
    renderSkillTree();
    syncBadges();
    if (data.completed && typeof data.points_awarded === 'number') {
        const combo = data.combo_multiplier ? ` (x${data.combo_multiplier.toFixed(1)})` : '';
        showNotification(`Skill completed! +${data.points_awarded} pts${combo}`, 'success');
    } else {
        showNotification('Skill progress updated!', 'info');
    }
    if (data.milestone_bonus) {
        showNotification(`Milestone bonus +${data.milestone_bonus} pts`, 'success');
    }
}

// Show Notification
// # Toast-style alert notifications
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification shadow`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Initialize on load
window.onload = init;
