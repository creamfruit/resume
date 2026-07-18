import json
import time
import re
import random
import hashlib
import base64
import secrets
import logging
import smtplib
from functools import wraps
from collections import deque
from difflib import SequenceMatcher
from datetime import datetime
from flask import Response
from email.message import EmailMessage

import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR / "projDraft4_fixed"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask, send_from_directory, request, jsonify, session, redirect, render_template, flash, send_file, abort, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import DatabaseError

from app.extensions import db, migrate
from app.models import User, UserSetting, AuthEvent, CircleSignup, AchievementState


TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static", template_folder=str(TEMPLATES_DIR))

# Core config
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "reconnect-secret-key")
app.config["DEBUG"] = (os.getenv("FLASK_DEBUG", "0") == "1")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (os.getenv("SESSION_COOKIE_SECURE", "0") == "1")
app.config["PROPAGATE_EXCEPTIONS"] = False

# Demo fallback key for local/dev runs when GOOGLE_MAPS_KEY is not set.
DEMO_GOOGLE_MAPS_KEY = "AIzaSyDp-94SYm9yTMqXqf7-MJo6O5c_06so0-w"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reconnect")


def _google_maps_key() -> str:
    return os.getenv("GOOGLE_MAPS_KEY", "").strip() or DEMO_GOOGLE_MAPS_KEY

# Admin credentials (set environment variables in production)
ADMIN_ID = os.getenv("ADMIN_ID", "1234")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "5678")
ADMIN_EMAILS = {
    "ryanadmin",
    "seanadmin",
    "nicholasadmin",
    "adenadmin",
}
ADMIN_EMAIL_PASSWORDS = {
    "ryanadmin": os.getenv("ADMIN_PW_RYANADMIN", "Ryan123!"),
    "seanadmin": os.getenv("ADMIN_PW_SEANADMIN", "Sean123!"),
    "nicholasadmin": os.getenv("ADMIN_PW_NICHOLASADMIN", "Nicholas123!"),
    "adenadmin": os.getenv("ADMIN_PW_ADENADMIN", "Aden123!"),
}

FORUM_CATEGORIES = {"Money", "Career", "Relationships", "Life Skills", "Health"}
FORUM_TITLE_MAX = 140
FORUM_CONTENT_MAX = 3000
FORUM_PAGE_SIZE = 12
FORUM_BAD_WORDS = {"idiot", "stupid", "dumb", "hate you"}
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{3,30}$")
REPORT_REASON_MIN = 5
REPORT_REASON_MAX = 300
_RATE_LIMIT_BUCKETS = {}

COACH_LIBRARY = {
    "general": {
        "icebreakers": [
            "Hi! How has your day been so far?",
            "What’s something small that made you smile today?",
            "If you could do one relaxing thing this week, what would it be?",
        ],
        "questions": [
            "What hobbies do you enjoy most these days?",
            "Do you have a favourite place in Singapore to visit?",
            "What’s a simple memory you treasure?",
        ],
        "respectful": [
            "It’s nice to chat with you today.",
            "I appreciate you sharing that with me.",
        ],
    },
    "hawker": {
        "icebreakers": [
            "Do you have a favourite hawker stall or dish?",
            "Have you tried any new food places recently?",
        ],
        "questions": [
            "What’s your go-to comfort food?",
            "Which hawker centre do you enjoy most?",
        ],
    },
    "family": {
        "icebreakers": [
            "Do you have a favourite family tradition?",
            "What’s a lovely family memory you like to share?",
        ],
        "questions": [
            "Who in your family inspires you the most?",
            "What’s a family story you enjoy telling?",
        ],
    },
    "childhood": {
        "icebreakers": [
            "What was your favourite childhood game?",
            "What did you enjoy doing after school as a kid?",
        ],
        "questions": [
            "What was a popular snack when you were young?",
            "Do you remember your childhood neighbourhood?",
        ],
    },
    "hobbies": {
        "icebreakers": [
            "What hobby are you enjoying lately?",
            "Have you picked up any new activities recently?",
        ],
        "questions": [
            "What do you like to do on weekends?",
            "Is there a skill you’d like to learn this year?",
        ],
    },
    "tech": {
        "icebreakers": [
            "Would you like help with phone or app tips?",
            "What’s one app you find useful?",
        ],
        "questions": [
            "Is there a digital skill you want to improve?",
            "Have you tried video calling with family?",
        ],
    },
    "singapore": {
        "icebreakers": [
            "Which part of Singapore do you enjoy visiting?",
            "Do you prefer the city or parks here?",
        ],
        "questions": [
            "What’s a place in Singapore you’d recommend?",
            "Any favourite festivals or celebrations here?",
        ],
    },
    "support": {
        "icebreakers": [
            "I’m here with you. Want to share how you’re feeling?",
            "Would a gentle chat help today?",
        ],
        "questions": [
            "What usually helps you feel a bit better?",
            "Would you like a simple, comforting topic to talk about?",
        ],
        "respectful": [
            "Thank you for trusting me with this.",
            "It’s okay to take things one step at a time.",
        ],
    },
    "meetup": {
        "icebreakers": [
            "Would you like to plan a simple meetup at a community place?",
            "Maybe we can meet at a café or library nearby?",
        ],
        "questions": [
            "What day works best for you?",
            "Would you prefer a quiet or lively place?",
        ],
    },
}

COACH_REWRITE_MAP = {
    "bro": "my friend",
    "lol": "that’s amusing",
    "u": "you",
    "ur": "your",
    "wtf": "",
    "omg": "oh my",
}

ONBOARDING_LANDMARKS = [
    "Marina Bay Sands",
    "Gardens by the Bay",
    "Merlion Park",
    "Esplanade",
    "Chinatown",
    "Clarke Quay",
    "Orchard Road",
    "Botanic Gardens",
    "National Museum",
    "Sentosa",
    "VivoCity",
    "East Coast Park",
    "Changi Airport",
    "Jewel Changi",
    "Singapore Zoo",
    "Night Safari",
    "Bird Paradise",
    "Pulau Ubin",
    "Haji Lane",
    "Little India",
]

WELLBEING_MOOD_META = {
    "happy": {"emoji": "😊", "label": "Happy", "score": 5},
    "good": {"emoji": "🙂", "label": "Good", "score": 4},
    "neutral": {"emoji": "😐", "label": "Neutral", "score": 3},
    "stressed": {"emoji": "😟", "label": "Stressed", "score": 2},
    "sad": {"emoji": "😞", "label": "Sad", "score": 1},
}
WELLBEING_MOOD_SCORES = {k: v["score"] for k, v in WELLBEING_MOOD_META.items()}


INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DB_PATH = (BASE_DIR.parent.parent / "database" / "ryan_WDP_Final_reconnect.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialise extensions
# Flask-Migrate is optional for running, but useful when you start changing models.
db.init_app(app)
migrate.init_app(app, db)



CHAT_DB_PATH = DB_PATH
FORUM_DB_PATH = DB_PATH


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _get_chat_conn():
    conn = sqlite3.connect(CHAT_DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn


def _init_chat_schema():
    conn = _get_chat_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            match_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            avatar TEXT NOT NULL,
            location TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS match_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            sender_seen INTEGER NOT NULL DEFAULT 0,
            receiver_seen INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            edited_at TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS admin_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS circle_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            circle_title TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS profanities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            level TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS pair_plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_a_id INTEGER NOT NULL,
            user_b_id INTEGER NOT NULL,
            plant_type TEXT NOT NULL DEFAULT 'sprout',
            stage INTEGER NOT NULL DEFAULT 1,
            plant_xp INTEGER NOT NULL DEFAULT 0,
            streak_count INTEGER NOT NULL DEFAULT 0,
            longest_streak INTEGER NOT NULL DEFAULT 0,
            last_streak_date TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            UNIQUE(user_a_id, user_b_id)
        );
        CREATE INDEX IF NOT EXISTS idx_pair_plants_pair ON pair_plants(user_a_id, user_b_id);
        CREATE INDEX IF NOT EXISTS idx_pair_plants_last_date ON pair_plants(last_streak_date);
        """
    )
    cols = {row["name"] for row in cur.execute("PRAGMA table_info(matches)").fetchall()}
    if "user_id" not in cols:
        cur.execute("ALTER TABLE matches ADD COLUMN user_id INTEGER")
    req_cols = {row["name"] for row in cur.execute("PRAGMA table_info(match_requests)").fetchall()}
    if "sender_seen" not in req_cols:
        cur.execute("ALTER TABLE match_requests ADD COLUMN sender_seen INTEGER NOT NULL DEFAULT 0")
        req_cols.add("sender_seen")
    if "receiver_seen" not in req_cols:
        cur.execute("ALTER TABLE match_requests ADD COLUMN receiver_seen INTEGER NOT NULL DEFAULT 0")
        req_cols.add("receiver_seen")
    if "updated_at" not in req_cols:
        cur.execute("ALTER TABLE match_requests ADD COLUMN updated_at TEXT")
        req_cols.add("updated_at")
    conn.commit()
    conn.close()


def _chat_match_to_dict(row):
    return {
        "match_id": row["match_id"],
        "name": row["name"],
        "avatar": row["avatar"],
        "location": row["location"] or "",
        "created_at": row["created_at"],
    }


def _chat_message_to_dict(row):
    return {
        "id": row["id"],
        "chat_id": row["chat_id"],
        "sender": row["sender"],
        "text": row["text"],
        "created_at": row["created_at"],
        "edited_at": row["edited_at"],
        "is_deleted": bool(row["is_deleted"]),
        "deleted_at": row["deleted_at"],
    }




def normalize_pair(user1: int, user2: int) -> tuple[int, int]:
    a = int(user1)
    b = int(user2)
    return (a, b) if a < b else (b, a)


def sg_today() -> str:
    sg_now = datetime.utcnow() + timedelta(hours=8)
    return sg_now.date().isoformat()


def is_meaningful_message(text: str, has_media: bool) -> bool:
    return bool(has_media or len((text or "").strip()) >= 5)


def _pair_stage_from_streak(streak: int) -> int:
    s = max(0, int(streak or 0))
    if s <= 1:
        return 1
    if s <= 3:
        return 2
    if s <= 6:
        return 3
    if s <= 10:
        return 4
    if s <= 14:
        return 5
    if s <= 29:
        return 6
    return 7


def _pair_stage_bounds(stage: int) -> tuple[int, int]:
    mapping = {
        1: (0, 1),
        2: (1, 3),
        3: (3, 6),
        4: (6, 10),
        5: (10, 14),
        6: (14, 30),
        7: (30, 30),
    }
    return mapping.get(int(stage or 1), (0, 1))


def _pair_progress_pct(stage: int, streak: int) -> int:
    floor, ceiling = _pair_stage_bounds(stage)
    s = max(0, int(streak or 0))
    if ceiling <= floor:
        return 100
    pct = int(round(((s - floor) / (ceiling - floor)) * 100))
    return max(0, min(100, pct))


def _pair_plant_state_from_row(row) -> dict:
    streak = int(row["streak_count"] or 0)
    longest = int(row["longest_streak"] or 0)
    stage = int(row["stage"] or 1)
    return {
        "streak": streak,
        "longest": longest,
        "stage": stage,
        "progressPct": _pair_progress_pct(stage, streak),
        "gained_xp": 0,
        "changed": False,
    }


def get_or_create_pair_plant(conn, user_a_id: int, user_b_id: int):
    a, b = normalize_pair(user_a_id, user_b_id)
    row = conn.execute(
        "SELECT * FROM pair_plants WHERE user_a_id = ? AND user_b_id = ? LIMIT 1",
        (a, b),
    ).fetchone()
    if row:
        return row
    now_ts = int(time.time())
    conn.execute(
        """
        INSERT INTO pair_plants (
            user_a_id, user_b_id, plant_type, stage, plant_xp, streak_count, longest_streak,
            last_streak_date, created_at, updated_at
        ) VALUES (?, ?, 'sprout', 1, 0, 0, 0, NULL, ?, ?)
        """,
        (a, b, now_ts, now_ts),
    )
    return conn.execute(
        "SELECT * FROM pair_plants WHERE user_a_id = ? AND user_b_id = ? LIMIT 1",
        (a, b),
    ).fetchone()


def _can_access_pair_conversation(viewer_id: int, other_user_id: int, chat_id: str | None = None) -> bool:
    viewer = int(viewer_id)
    other = int(other_user_id)
    if viewer <= 0 or other <= 0 or viewer == other:
        return False
    if _is_blocked_between(viewer, other):
        return False
    if _are_friends(viewer, other):
        return True

    canonical = _canonical_chat_id(chat_id or f"dm:{min(viewer, other)}-{max(viewer, other)}", viewer)
    conn = _get_chat_conn()
    has_messages = conn.execute(
        "SELECT 1 FROM messages WHERE chat_id = ? LIMIT 1",
        (canonical,),
    ).fetchone()
    conn.close()
    return bool(has_messages)


def _current_pair_plant_state(conn, viewer_id: int, other_user_id: int) -> dict:
    row = get_or_create_pair_plant(conn, viewer_id, other_user_id)
    return _pair_plant_state_from_row(row)


def award_pair_plant_growth(conn, sender_id: int, receiver_id: int, message_text: str, has_media: bool) -> dict:
    row = get_or_create_pair_plant(conn, sender_id, receiver_id)
    state = _pair_plant_state_from_row(row)

    if not is_meaningful_message(message_text, has_media):
        return state

    today = sg_today()
    last_date = (row["last_streak_date"] or "").strip()
    if last_date == today:
        return state

    streak = int(row["streak_count"] or 0)
    yesterday = (datetime.fromisoformat(today) - timedelta(days=1)).date().isoformat()
    if last_date == yesterday:
        streak += 1
    else:
        streak = 1

    longest = max(int(row["longest_streak"] or 0), streak)
    gained_xp = 10 + min(streak, 20)
    xp_total = int(row["plant_xp"] or 0) + gained_xp
    stage = _pair_stage_from_streak(streak)
    now_ts = int(time.time())

    conn.execute(
        """
        UPDATE pair_plants
           SET stage = ?,
               plant_xp = ?,
               streak_count = ?,
               longest_streak = ?,
               last_streak_date = ?,
               updated_at = ?
         WHERE id = ?
        """,
        (stage, xp_total, streak, longest, today, now_ts, int(row["id"])),
    )

    return {
        "streak": streak,
        "longest": longest,
        "stage": stage,
        "progressPct": _pair_progress_pct(stage, streak),
        "gained_xp": gained_xp,
        "changed": True,
    }


def _get_forum_conn():
    conn = sqlite3.connect(FORUM_DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn


def _init_forum_schema():
    conn = _get_forum_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            author TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            likes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_id INTEGER,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS post_likes (
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category, id DESC);
        CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_comments_post_id_id ON comments(post_id, id DESC);
        CREATE INDEX IF NOT EXISTS idx_post_likes_post_id ON post_likes(post_id);
        """
    )
    conn.commit()
    conn.close()


def _forum_current_user_name():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    return user.full_name if user else None


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": _csrf_token()}


def _validate_csrf() -> bool:
    session_token = session.get("csrf_token") or ""
    request_token = (
        request.headers.get("X-CSRF-Token")
        or request.form.get("csrf_token")
        or (request.get_json(silent=True) or {}).get("csrf_token")
        or ""
    )
    return bool(session_token and request_token and session_token == request_token)


def _rate_limit_check(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    now = time.time()
    window_start = now - window_seconds
    events = _RATE_LIMIT_BUCKETS.get(key, [])
    events = [stamp for stamp in events if stamp >= window_start]
    if len(events) >= limit:
        retry_after = int(max(1, window_seconds - (now - events[0])))
        _RATE_LIMIT_BUCKETS[key] = events
        return False, retry_after
    events.append(now)
    _RATE_LIMIT_BUCKETS[key] = events
    return True, 0


def _normalize_forum_category(value: str) -> str:
    category = (value or "").strip()
    if category in FORUM_CATEGORIES:
        return category
    return "Life Skills"


def _validate_forum_text(title: str, content: str) -> str | None:
    if not title or not content:
        return "Title and content are required."
    if len(title) > FORUM_TITLE_MAX:
        return f"Title must be {FORUM_TITLE_MAX} characters or fewer."
    if len(content) > FORUM_CONTENT_MAX:
        return f"Content must be {FORUM_CONTENT_MAX} characters or fewer."
    return None


def _forum_content_guard(text: str) -> str | None:
    lowered = (text or "").casefold()
    for word in FORUM_BAD_WORDS:
        if word in lowered:
            return "Please keep posts respectful. Avoid offensive language."
    if lowered.count("http://") + lowered.count("https://") > 3:
        return "Too many links in one post."
    if re.search(r"(.)\1{10,}", lowered):
        return "Please avoid spam-like repeated characters."
    return None


def _forum_blocked_user_ids(viewer_user_id: int | None) -> list[int]:
    if not viewer_user_id:
        return []
    conn = _get_main_conn()
    rows = conn.execute(
        "SELECT blocked_user_id FROM user_blocks WHERE user_id = ?",
        (viewer_user_id,),
    ).fetchall()
    conn.close()
    return [int(r["blocked_user_id"]) for r in rows if r["blocked_user_id"] is not None]


def _is_blocked_between(user_a_id: int | None, user_b_id: int | None) -> bool:
    if not user_a_id or not user_b_id:
        return False
    conn = _get_main_conn()
    row = conn.execute(
        """
        SELECT 1
        FROM user_blocks
        WHERE (user_id = ? AND blocked_user_id = ?)
           OR (user_id = ? AND blocked_user_id = ?)
        LIMIT 1
        """,
        (int(user_a_id), int(user_b_id), int(user_b_id), int(user_a_id)),
    ).fetchone()
    conn.close()
    return bool(row)


def _are_friends(user_a_id: int | None, user_b_id: int | None) -> bool:
    if not user_a_id or not user_b_id:
        return False
    if int(user_a_id) == int(user_b_id):
        return True
    conn = _get_chat_conn()
    row = conn.execute(
        """
        SELECT 1
        FROM match_requests
        WHERE status = 'accepted'
          AND ((sender_id = ? AND receiver_id = ?)
            OR (sender_id = ? AND receiver_id = ?))
        LIMIT 1
        """,
        (int(user_a_id), int(user_b_id), int(user_b_id), int(user_a_id)),
    ).fetchone()
    conn.close()
    return bool(row)


def _friend_state(user_a_id: int | None, user_b_id: int | None) -> dict:
    state = {"status": "none", "request_id": None}
    if not user_a_id or not user_b_id:
        return state
    a = int(user_a_id)
    b = int(user_b_id)
    if a == b:
        return {"status": "self", "request_id": None}
    if _is_blocked_between(a, b):
        return {"status": "blocked", "request_id": None}
    conn = _get_chat_conn()
    row = conn.execute(
        """
        SELECT id, sender_id, receiver_id, status
        FROM match_requests
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY id DESC
        LIMIT 1
        """,
        (a, b, b, a),
    ).fetchone()
    conn.close()
    if not row:
        return state
    status = (row["status"] or "").strip().lower()
    if status == "accepted":
        return {"status": "friends", "request_id": int(row["id"])}
    if status == "pending":
        if int(row["sender_id"]) == a:
            return {"status": "pending_sent", "request_id": int(row["id"])}
        return {"status": "pending_received", "request_id": int(row["id"])}
    return state


def _trust_badge_label(score: int) -> str:
    if score >= 80:
        return "Trusted"
    if score >= 60:
        return "Good standing"
    if score >= 40:
        return "Caution"
    return "Restricted"


def _normalize_visibility(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v == "public":
        return "community"
    if v == "circle":
        return "friends"
    if v in {"private", "friends", "community"}:
        return v
    return "private"


def _can_view_scrapbook_entry(viewer_user_id: int | None, owner_user_id: int | None, visibility: str | None) -> bool:
    if not viewer_user_id or not owner_user_id:
        return False
    viewer_id = int(viewer_user_id)
    owner_id = int(owner_user_id)
    if viewer_id == owner_id:
        return True
    if is_blocked(viewer_id, owner_id):
        return False
    if not can_view_profile(viewer_id, owner_id, _is_private_profile(owner_id)):
        return False
    normalized = _normalize_visibility(visibility)
    if normalized == "community":
        return True
    if normalized == "friends":
        return follow_status(viewer_id, owner_id) == "accepted" or _are_friends(viewer_id, owner_id)
    return False


def _profile_completeness(onboarding: dict, user_settings: dict) -> dict:
    onboarding = onboarding if isinstance(onboarding, dict) else {}
    user_settings = user_settings if isinstance(user_settings, dict) else {}

    bio = (user_settings.get("bio") or "").strip()
    avatar_url = (user_settings.get("avatar_url") or "").strip()
    banner_url = (user_settings.get("banner_url") or "").strip()
    interests = onboarding.get("interests") or []
    skills_teach = onboarding.get("skills_teach") or _safe_json(user_settings.get("skills_teach", "[]"), [])
    skills_learn = onboarding.get("skills_learn") or _safe_json(user_settings.get("skills_learn", "[]"), [])
    days = onboarding.get("days") or []
    times = onboarding.get("time") or []
    stations = onboarding.get("stations") or []
    languages = onboarding.get("languages") or _safe_json(user_settings.get("languages", "[]"), [])
    language_proficiency = onboarding.get("language_proficiency") or _safe_json(
        user_settings.get("language_proficiency", "{}"), {}
    )
    emergency = _safe_json(user_settings.get("emergency_contact", "{}"), {})
    verified_with = (user_settings.get("verified_with") or "").strip().lower()

    interest_count = len([x for x in interests if str(x).strip()])
    teach_count = len([x for x in skills_teach if str(x).strip()])
    learn_count = len([x for x in skills_learn if str(x).strip()])
    day_count = len([x for x in days if str(x).strip()])
    time_count = len([x for x in times if str(x).strip()])
    station_count = len([x for x in stations if str(x).strip()])
    lang_count = len([x for x in languages if str(x).strip()])
    prof_count = 0
    if isinstance(language_proficiency, dict):
        prof_count = sum(
            1
            for lang in languages
            if str(lang).strip() and str(language_proficiency.get(lang, "")).strip()
        )

    emergency_name = str((emergency or {}).get("name", "")).strip()
    emergency_rel = str((emergency or {}).get("relationship", "")).strip()
    emergency_phone = str((emergency or {}).get("phone", "")).strip()

    checks = [
        bool(avatar_url),                           # 1 avatar
        bool(banner_url),                           # 2 banner
        len(bio) >= 20,                             # 3 meaningful bio
        interest_count >= 1,                        # 4 interests started
        interest_count >= 3,                        # 5 interests fuller
        teach_count >= 1,                           # 6 can teach
        learn_count >= 1,                           # 7 want to learn
        day_count >= 1,                             # 8 availability days
        time_count >= 1,                            # 9 availability times
        station_count >= 1,                         # 10 MRT selected
        lang_count >= 1,                            # 11 languages selected
        prof_count >= 1,                            # 12 language proficiency set
        bool(emergency_name),                       # 13 emergency name
        bool(emergency_rel),                        # 14 emergency relationship
        bool(emergency_phone),                      # 15 emergency phone
        verified_with in {"phone", "email", "nric", "singpass"},  # 16 verified
    ]

    completed = sum(1 for c in checks if c)
    total = len(checks)
    percent = int(round((completed / total) * 100)) if total else 0
    return {"completed": completed, "total": total, "percent": percent}


def _forum_redirect_back(default_path: str = "/forum"):
    ref = (request.referrer or "").strip()
    if ref and ref.startswith(request.host_url):
        parsed = urllib.parse.urlparse(ref)
        # Keep forum actions on forum URLs instead of bouncing to dashboard.
        if parsed.path.startswith("/forum"):
            return redirect(ref)
    if default_path.startswith("/forum"):
        return redirect(default_path)
    if ref and ref.startswith(request.host_url):
        return redirect(ref)
    return redirect(default_path)


def _forum_list_posts(
    selected_category: str,
    page: int | None = None,
    per_page: int = FORUM_PAGE_SIZE,
    search: str = "",
    sort: str = "newest",
    viewer_user_id: int | None = None,
):
    conn = _get_forum_conn()
    clauses = []
    params = []
    if selected_category != "all":
        clauses.append("p.category = ?")
        params.append(selected_category)
    query_text = (search or "").strip()
    if query_text:
        clauses.append("(LOWER(p.title) LIKE ? OR LOWER(p.content) LIKE ? OR LOWER(p.author) LIKE ?)")
        wildcard = f"%{query_text.lower()}%"
        params.extend([wildcard, wildcard, wildcard])
    blocked_ids = _forum_blocked_user_ids(viewer_user_id)
    if blocked_ids:
        placeholders = ",".join(["?"] * len(blocked_ids))
        clauses.append(f"(p.author_id IS NULL OR p.author_id NOT IN ({placeholders}))")
        params.extend(blocked_ids)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_sql = "ORDER BY p.id DESC"
    if sort == "likes":
        order_sql = "ORDER BY p.likes DESC, p.id DESC"
    elif sort == "comments":
        order_sql = "ORDER BY comment_count DESC, p.id DESC"

    if page is not None:
        safe_page = max(1, int(page))
        safe_per_page = max(1, min(50, int(per_page)))
        offset = (safe_page - 1) * safe_per_page
        total_row = conn.execute(
            f"SELECT COUNT(*) AS c FROM posts p {where_sql}",
            tuple(params),
        ).fetchone()
        rows = conn.execute(
            f"""
            SELECT p.*, (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comment_count
            FROM posts p
            {where_sql}
            {order_sql}
            LIMIT ? OFFSET ?
            """,
            tuple(params + [safe_per_page, offset]),
        ).fetchall()
        conn.close()
        total = int(total_row["c"] if total_row else 0)
        return rows, total
    else:
        rows = conn.execute(
            f"""
            SELECT p.*, (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comment_count
            FROM posts p
            {where_sql}
            {order_sql}
            """,
            tuple(params),
        ).fetchall()
    conn.close()
    return rows

# Create tables automatically for this prototype
with app.app_context():
    db.create_all()
    _init_chat_schema()
    _init_forum_schema()


PAGES = {
    "dashboard": "dashboard.html",
    "feed": "feed.html",
    "events": "events.html",
    "hangouts": "hangouts.html",
    "login": "login.html",
    "login-2fa": "login_2fa.html",
    "signup": "signup.html",
    "signup-2fa": "signup_2fa.html",
    "onboarding": "onboarding.html",
    "profile": "profile.html",
    "explore": "explore.html",
    "messages": "messages.html",
    "circle-confirmation": "circle_confirmation.html",
    "learning-circles": "learning_circles.html",
    "discover": "discover.html",
    "forum": "forum.html",
    "challenges": "challenges.html",
    "terms": "terms.html",
    "safety": "safety.html",
    "achievements": "achievements.html",
    "wellbeing": "wellbeing.html",
    "scrapbook": "scrapbook.html",
    "avatar": "avatar_builder.html",
    "admin-login": "admin_login.html",
    "admin-dashboard": "admin_dashboard.html",
}

AVATAR_DEFAULT_CONFIG = {
    "avatar_name": "",
    "pose": "waving",
    "gender": "girl",
    "skin_tone": "light",
    "base": "body_waving",
    "face": "face_light",
    "eyes": "eyes_1",
    "mouth": "mouth_1",
    "hair": "hair_1",
    "glasses": "none",
    "top": "top_1",
}

AVATAR_OPTIONS = {
    "avatar_name": [],
    "pose": ["waving", "standing", "smiling"],
    "gender": ["girl", "boy"],
    "skin_tone": ["light", "tan", "dark"],
    "base": ["body_waving", "body_standing", "body_smiling"],
    "face": ["face_light", "face_tan", "face_dark"],
    "eyes": ["eyes_1", "eyes_2"],
    "mouth": ["mouth_1", "mouth_2"],
    "hair": ["hair_1", "hair_2"],
    "glasses": ["none", "glasses_1"],
    "top": ["top_1", "top_2"],
}


LANDMARKS = [
    {
        "id": 1,
        "name": "Jurong",
        "icon": "🏭",
        "x": 220,
        "y": 310,
        "story": "Singapore's industrial heartland that transformed into a hub for innovation, featuring Jurong Bird Park and the upcoming Jurong Lake District.",
        "question": "What is Jurong best known for today?",
        "options": ["Shopping malls", "Innovation hub", "Beach resorts", "Historic temples"],
        "answer": 1,
    },
    {
        "id": 2,
        "name": "Chinatown",
        "icon": "🏮",
        "x": 410,
        "y": 350,
        "story": "A vibrant district preserving Chinese heritage and culture, where traditional shophouses blend with modern businesses.",
        "question": "What makes Chinatown special?",
        "options": ["Modern skyscrapers", "Blend of heritage and modern life", "Beach activities", "Industrial sites"],
        "answer": 1,
    },
    {
        "id": 3,
        "name": "Marina Bay",
        "icon": "🏙",
        "x": 490,
        "y": 340,
        "story": "This iconic waterfront area features Marina Bay Sands with three towers connected by a sky park.",
        "question": "How many towers does Marina Bay Sands have?",
        "options": ["2", "3", "4", "5"],
        "answer": 1,
    },
    {
        "id": 4,
        "name": "Orchard Road",
        "icon": "🛍",
        "x": 380,
        "y": 290,
        "story": "Singapore's premier shopping district with over 20 shopping malls. It was once lined with fruit orchards.",
        "question": "What was Orchard Road before becoming a shopping district?",
        "options": ["Industrial area", "Fruit orchards", "Residential zone", "Fishing village"],
        "answer": 1,
    },
    {
        "id": 5,
        "name": "Kampong Glam",
        "icon": "🕌",
        "x": 520,
        "y": 285,
        "story": "The historic Malay-Muslim quarter centered around the golden-domed Sultan Mosque.",
        "question": "What is the famous mosque in Kampong Glam?",
        "options": ["Blue Mosque", "Sultan Mosque", "Crystal Mosque", "Grand Mosque"],
        "answer": 1,
    },
    {
        "id": 6,
        "name": "Little India",
        "icon": "🏛",
        "x": 460,
        "y": 270,
        "story": "An ethnic district that celebrates Indian culture, featuring colorful streets and vibrant festivals.",
        "question": "Which festival is famously celebrated in Little India?",
        "options": ["Christmas", "Deepavali", "Chinese New Year", "Hari Raya"],
        "answer": 1,
    },
    {
        "id": 7,
        "name": "Botanic Gardens",
        "icon": "🪴",
        "x": 310,
        "y": 250,
        "story": "A UNESCO World Heritage Site founded in 1859, featuring 82 hectares of lush greenery.",
        "question": "When was the Singapore Botanic Gardens founded?",
        "options": ["1819", "1859", "1900", "1965"],
        "answer": 1,
    },
    {
        "id": 8,
        "name": "Marina Bay Sands",
        "icon": "🏢",
        "x": 550,
        "y": 325,
        "story": "Marina Bay Sands features three towers connected by a sky park 200 meters above ground.",
        "question": "How many towers does Marina Bay Sands have?",
        "options": ["2", "3", "4", "5"],
        "answer": 1,
    },
    {
        "id": 9,
        "name": "Changi",
        "icon": "✈️",
        "x": 620,
        "y": 285,
        "story": "Home to Changi Airport, consistently rated the world's best airport.",
        "question": "What is Changi best known for?",
        "options": ["Shopping malls", "World-class airport", "Historical museums", "Nature parks"],
        "answer": 1,
    },
    {
        "id": 10,
        "name": "Sentosa",
        "icon": "🏝",
        "x": 370,
        "y": 470,
        "story": "Singapore's island resort destination offering beaches and attractions.",
        "question": "What does 'Sentosa' mean in Malay?",
        "options": ["Peace and tranquility", "Beautiful island", "Paradise beach", "Golden sands"],
        "answer": 0,
    },
]

QUESTS = [
    {"id": 1, "title": "Join Your First Learning Circle", "description": "Connect with others to learn or share a skill together", "reward": 1500, "total": 1},
    {"id": 2, "title": "Reply in the Community Forum", "description": "Share your thoughts or help answer someone's question", "reward": 75, "total": 1},
    {"id": 3, "title": "Share a Skill", "description": "Teach something you know - cooking, language, crafts, anything!", "reward": 200, "total": 1},
    {"id": 4, "title": "Thank a Connection", "description": "Send appreciation to someone who helped you", "reward": 50, "total": 1},
    {"id": 5, "title": "Complete 3 Learning Sessions", "description": "Keep learning and growing with the community", "reward": 300, "total": 3},
]

REWARDS = [
    {"id": 1, "name": "$2 GrabFood Voucher", "icon": "🎁", "cost": 500},
    {"id": 2, "name": "$3 Starbucks Voucher", "icon": "☕", "cost": 750},
    {"id": 3, "name": "$5 Popular Bookstore", "icon": "📚", "cost": 1250},
    {"id": 4, "name": "$5 Kopitiam Voucher", "icon": "🥖", "cost": 1250},
    {"id": 5, "name": "$10 NTUC Voucher", "icon": "🛒", "cost": 2500},
    {"id": 6, "name": "$10 Watsons Voucher", "icon": "🧴", "cost": 2500},
    {"id": 7, "name": "$15 Movie Voucher", "icon": "🎟", "cost": 3750},
    {"id": 8, "name": "$15 Uniqlo Voucher", "icon": "👕", "cost": 3750},
]

BADGE_GROUPS = {
    "Journey Badges": [
        {"id": 1, "name": "First Steps", "icon": "🥇", "description": "Unlock your first landmark", "threshold": 1, "requirement": "landmarks"},
        {"id": 2, "name": "City Explorer", "icon": "🧭", "description": "Complete 3 landmarks", "threshold": 3, "requirement": "landmarks"},
        {"id": 3, "name": "Island Voyager", "icon": "🗺", "description": "Complete all 10 landmarks", "threshold": 10, "requirement": "landmarks"},
    ],
    "Community Badges": [
        {"id": 4, "name": "Community Builder", "icon": "🧱", "description": "Complete 5 quests", "threshold": 5, "requirement": "quests"},
        {"id": 5, "name": "Helpful Guide", "icon": "🧑‍🏫", "description": "Complete 10 quests", "threshold": 10, "requirement": "quests"},
        {"id": 6, "name": "Master Connector", "icon": "🔗", "description": "Complete 20 quests", "threshold": 20, "requirement": "quests"},
    ],
    "Progress Badges": [
        {"id": 7, "name": "Point Collector", "icon": "🪙", "description": "Earn 1,000 points", "threshold": 1000, "requirement": "points"},
        {"id": 8, "name": "Point Master", "icon": "🏆", "description": "Earn 5,000 points", "threshold": 5000, "requirement": "points"},
        {"id": 9, "name": "Tier Ascender", "icon": "🚀", "description": "Reach Tier 3", "threshold": 3, "requirement": "tier"},
    ],
}

SKILLS = [
    {"id": 1, "name": "WhatsApp Basics", "description": "Start a new chat and send a message.", "category": "Digital Basics", "icon": "whatsapp", "required_count": 1, "progress": 1, "completed": True, "parent_id": None},
    {"id": 2, "name": "Voice Notes", "description": "Record and send a voice message.", "category": "Digital Basics", "icon": "voice", "required_count": 2, "progress": 1, "completed": False, "parent_id": 1},
    {"id": 3, "name": "Photo Sharing", "description": "Share photos with a connection.", "category": "Digital Basics", "icon": "attachment", "required_count": 2, "progress": 0, "completed": False, "parent_id": 1},
    {"id": 4, "name": "Online Safety", "description": "Identify suspicious links and scams.", "category": "Safety & Security", "icon": "scam", "required_count": 3, "progress": 1, "completed": False, "parent_id": None},
]


def _default_achievements(user: User) -> dict:
    checkins = []

    landmarks = []
    for lm in LANDMARKS:
        landmarks.append({**lm, "unlocked": False, "completed": False})

    quests = []
    for q in QUESTS:
        quests.append({**q, "progress": 0, "completed": False})

    rewards = []
    for r in REWARDS:
        rewards.append({**r, "status": "locked"})

    return {
        "user": {
            "id": user.id,
            "username": user.full_name,
            "total_points": 0,
            "available_points": 0,
            "active_days": 0,
            "current_tier": 1,
            "current_streak": 0,
        },
        "landmarks": landmarks,
        "quests": quests,
        "rewards": rewards,
        "badges": {},
        "leaderboard": [
            {"username": "Auntie Mary", "total_points": 4200, "current_tier": 3},
            {"username": "Uncle Tan", "total_points": 3800, "current_tier": 3},
            {"username": user.full_name, "total_points": 1850, "current_tier": 2},
            {"username": "Mdm Chen", "total_points": 1650, "current_tier": 2},
            {"username": "Sam", "total_points": 1200, "current_tier": 1},
        ],
        "checkins": checkins,
        "skills": SKILLS,
    }


def _recompute_badges(state: dict) -> None:
    quests_completed = len([q for q in state["quests"] if q.get("completed")])
    landmarks_completed = len([l for l in state["landmarks"] if l.get("completed")])
    points = state["user"]["total_points"]
    tier = state["user"]["current_tier"]

    grouped = {}
    for group, badges in BADGE_GROUPS.items():
        grouped[group] = []
        for badge in badges:
            requirement = badge["requirement"]
            current = 0
            if requirement == "landmarks":
                current = landmarks_completed
            elif requirement == "quests":
                current = quests_completed
            elif requirement == "points":
                current = points
            elif requirement == "tier":
                current = tier
            grouped[group].append(
                {
                    "id": badge["id"],
                    "name": badge["name"],
                    "icon": badge["icon"],
                    "description": badge["description"],
                    "threshold": badge["threshold"],
                    "earned": current >= badge["threshold"],
                    "current": current,
                }
            )
    state["badges"] = grouped


def _sync_rewards(state: dict) -> None:
    available = state["user"]["available_points"]
    for reward in state["rewards"]:
        if reward.get("status") == "redeemed":
            continue
        reward["status"] = "available" if available >= reward["cost"] else "locked"


def _refresh_leaderboard(state: dict, user: User) -> None:
    base = [
        {"username": "Auntie Mary", "total_points": 4200, "current_tier": 3},
        {"username": "Uncle Tan", "total_points": 3800, "current_tier": 3},
        {"username": "Mdm Chen", "total_points": 1650, "current_tier": 2},
        {"username": "Sam", "total_points": 1200, "current_tier": 1},
    ]
    me = {
        "username": user.full_name,
        "total_points": state["user"]["total_points"],
        "current_tier": state["user"]["current_tier"],
    }
    combined = base + [me]
    combined.sort(key=lambda r: r["total_points"], reverse=True)
    state["leaderboard"] = combined[:10]


def _load_achievements(user_id: int) -> dict:
    row = AchievementState.query.filter_by(user_id=user_id).first()
    if not row:
        user = db.session.get(User, user_id)
        data = _default_achievements(user)
        _recompute_badges(data)
        _refresh_leaderboard(data, user)
        row = AchievementState(user_id=user_id, data_json=json.dumps(data))
        db.session.add(row)
        db.session.commit()
        return data
    data = json.loads(row.data_json)
    user = db.session.get(User, user_id)
    if user:
        _refresh_leaderboard(data, user)
    return data


def _save_achievements(user_id: int, state: dict) -> None:
    row = AchievementState.query.filter_by(user_id=user_id).first()
    if not row:
        row = AchievementState(user_id=user_id, data_json=json.dumps(state))
        db.session.add(row)
    else:
        row.data_json = json.dumps(state)
        row.updated_at = datetime.utcnow()
    db.session.commit()



@app.get("/")
def home():
    explore_cards = _list_home_explore_cards()
    return render_template("index.html", explore_cards=explore_cards)



@app.get("/community")
def community_page():
    if not _require_login():
        return redirect("/login")
    return redirect("/feed")


@app.get("/admin-login")
def admin_login_page():
    return render_template("admin_login.html")


@app.get("/admin-dashboard")
def admin_dashboard_page():
    if not _require_admin():
        return redirect("/admin-login")
    return render_template("admin_dashboard.html")


@app.get("/logout")
def logout_page():
    session.pop("user_id", None)
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    return redirect("/login")


@app.post("/dashboard")
@app.post("/forum")
def dashboard_forum_post():
    user_id = _require_login()
    if not user_id:
        return redirect("/login")
    if not _validate_csrf():
        return ("Invalid CSRF token", 400)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, _ = _rate_limit_check(f"forum_post:{user_id}:{ip}", limit=8, window_seconds=60)
    if not allowed:
        return ("Too many posts, please try again shortly.", 429)

    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    category = _normalize_forum_category(request.form.get("category") or "")

    err = _validate_forum_text(title, content)
    if err:
        return redirect("/forum")
    guard = _forum_content_guard(f"{title}\n{content}")
    if guard:
        return redirect("/forum")

    user = db.session.get(User, user_id)
    author_name = user.full_name if user else "User"

    conn = _get_forum_conn()
    conn.execute(
        "INSERT INTO posts (author_id, author, title, content, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, author_name, title, content, category, datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()
    _log_audit("wisdom_forum", "post", user_id, {"title": title, "category": category})
    _increment_quest_progress(user_id, 2)
    _add_notification(user_id, "forum_post", "Posted in the Wisdom Forum.", {"title": title})

    return redirect("/forum")


@app.route("/forum/posts/<int:post_id>", methods=["GET", "POST"])
def forum_post_detail(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    user = db.session.get(User, user_id)
    forum_user_name = user.full_name if user else "User"

    conn = _get_forum_conn()
    if request.method == "POST":
        if not _validate_csrf():
            conn.close()
            return ("Invalid CSRF token", 400)
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
        allowed, _ = _rate_limit_check(f"forum_comment:{user_id}:{ip}:{post_id}", limit=12, window_seconds=60)
        if not allowed:
            conn.close()
            return _forum_redirect_back(f"/forum/posts/{post_id}")
        comment = (request.form.get("comment") or "").strip()
        if comment:
            if len(comment) > FORUM_CONTENT_MAX:
                conn.close()
                return _forum_redirect_back(f"/forum/posts/{post_id}")
            guard = _forum_content_guard(comment)
            if guard:
                conn.close()
                return _forum_redirect_back(f"/forum/posts/{post_id}")
            conn.execute(
                "INSERT INTO comments (post_id, author_id, author, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (post_id, user_id, forum_user_name, comment, datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
            )
            conn.commit()
            _log_audit("wisdom_forum", "comment", user_id, {"post_id": post_id})
            _increment_quest_progress(user_id, 2)
            _add_notification(user_id, "forum_comment", "Replied in the Wisdom Forum.", {"post_id": post_id})
            parent = conn.execute("SELECT author_id FROM posts WHERE id = ?", (post_id,)).fetchone()
            parent_author_id = int(parent["author_id"]) if parent and parent["author_id"] is not None else None
            if parent_author_id and parent_author_id != user_id:
                _add_notification(
                    parent_author_id,
                    "forum_comment_received",
                    f"{forum_user_name} replied to your forum post.",
                    {"post_id": post_id},
                )

    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return ("Not found", 404)

    comments = conn.execute(
        "SELECT * FROM comments WHERE post_id = ? ORDER BY id DESC",
        (post_id,),
    ).fetchall()
    conn.close()

    return render_template("post.html", post=post, comments=comments, is_admin=_require_admin(), forum_user_name=forum_user_name)


@app.post("/forum/posts/<int:post_id>/comments/<int:comment_id>/delete")
def forum_delete_comment(post_id: int, comment_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")
    if not _validate_csrf():
        return ("Invalid CSRF token", 400)

    forum_user_name = _forum_current_user_name()
    conn = _get_forum_conn()
    comment = conn.execute(
        "SELECT author_id, author FROM comments WHERE id = ? AND post_id = ?",
        (comment_id, post_id),
    ).fetchone()

    if comment and (_require_admin() or comment["author_id"] == user_id or comment["author"] == (forum_user_name or "")):
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()
        _log_audit("wisdom_forum", "comment_delete", user_id, {"post_id": post_id})

    conn.close()
    return redirect(f"/forum/posts/{post_id}")


@app.post("/forum/posts/<int:post_id>/delete")
def forum_delete_post(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")
    if not _validate_csrf():
        return ("Invalid CSRF token", 400)

    forum_user_name = _forum_current_user_name()
    conn = _get_forum_conn()
    post = conn.execute("SELECT author_id, author FROM posts WHERE id = ?", (post_id,)).fetchone()

    if post and (_require_admin() or post["author_id"] == user_id or post["author"] == (forum_user_name or "")):
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        _log_audit("wisdom_forum", "post_delete", user_id, {"post_id": post_id})

    conn.close()
    return _forum_redirect_back("/forum")


@app.post("/forum/posts/<int:post_id>/edit")
def forum_edit_post(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")
    if not _validate_csrf():
        return ("Invalid CSRF token", 400)

    forum_user_name = _forum_current_user_name()
    content = (request.form.get("content") or "").strip()
    if not content:
        return _forum_redirect_back("/forum")
    if len(content) > FORUM_CONTENT_MAX:
        return _forum_redirect_back("/forum")
    guard = _forum_content_guard(content)
    if guard:
        return _forum_redirect_back("/forum")

    conn = _get_forum_conn()
    post = conn.execute("SELECT author_id, author FROM posts WHERE id = ?", (post_id,)).fetchone()

    if post and (post["author_id"] == user_id or post["author"] == (forum_user_name or "")):
        conn.execute("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
        conn.commit()
        _log_audit("wisdom_forum", "post_edit", user_id, {"post_id": post_id})

    conn.close()
    return _forum_redirect_back("/forum")


@app.post("/forum/posts/<int:post_id>/like")
def forum_like_post(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")
    if not _validate_csrf():
        return ("Invalid CSRF token", 400)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, _ = _rate_limit_check(f"forum_like:{user_id}:{ip}", limit=40, window_seconds=60)
    if not allowed:
        return _forum_redirect_back("/forum")

    conn = _get_forum_conn()
    existing = conn.execute(
        "SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?",
        (user_id, post_id),
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM post_likes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE id = ?", (post_id,))
        _log_audit("wisdom_forum", "like_remove", user_id, {"post_id": post_id})
    else:
        conn.execute("INSERT INTO post_likes (user_id, post_id) VALUES (?, ?)", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        _log_audit("wisdom_forum", "like_add", user_id, {"post_id": post_id})

    conn.commit()
    conn.close()
    return _forum_redirect_back("/forum")


@app.get("/api/forum/posts")
def api_forum_posts():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    category = (request.args.get("category") or "all").strip()
    if category != "all" and category not in FORUM_CATEGORIES:
        category = "all"
    search = (request.args.get("q") or "").strip()
    sort = (request.args.get("sort") or "newest").strip().lower()
    if sort not in {"newest", "likes", "comments"}:
        sort = "newest"
    page_num = max(1, request.args.get("page", type=int) or 1)
    rows, total = _forum_list_posts(
        category,
        page=page_num,
        per_page=FORUM_PAGE_SIZE,
        search=search,
        sort=sort,
        viewer_user_id=user_id,
    )
    current_name = _forum_current_user_name() or ""
    is_admin = _require_admin()
    posts = []
    for r in rows:
        posts.append(
            {
                "id": r["id"],
                "author": r["author"],
                "title": r["title"],
                "content": r["content"],
                "category": r["category"],
                "likes": r["likes"],
                "comment_count": r["comment_count"],
                "created_at": r["created_at"],
                "author_id": r["author_id"],
                "can_edit": bool(is_admin or r["author_id"] == user_id or r["author"] == current_name),
            }
        )
    total_pages = max(1, (total + FORUM_PAGE_SIZE - 1) // FORUM_PAGE_SIZE)
    return jsonify({"ok": True, "posts": posts, "total": total, "page": page_num, "total_pages": total_pages})


@app.post("/api/forum/posts")
def api_forum_create_post():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, retry_after = _rate_limit_check(f"api_forum_post:{user_id}:{ip}", limit=8, window_seconds=60)
    if not allowed:
        return jsonify({"ok": False, "error": "Rate limit exceeded", "retry_after": retry_after}), 429

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    category = _normalize_forum_category(data.get("category") or "")
    err = _validate_forum_text(title, content)
    if err:
        return jsonify({"ok": False, "error": err}), 400
    guard = _forum_content_guard(f"{title}\n{content}")
    if guard:
        return jsonify({"ok": False, "error": guard}), 400

    user = db.session.get(User, user_id)
    author = user.full_name if user else "User"

    conn = _get_forum_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO posts (author_id, author, title, content, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, author, title, content, category, datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
    )
    post_id = cur.lastrowid
    conn.commit()
    row = conn.execute(
        "SELECT p.*, (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comment_count FROM posts p WHERE p.id = ?",
        (post_id,),
    ).fetchone()
    conn.close()
    _log_audit("wisdom_forum", "post", user_id, {"title": title, "category": category})
    return jsonify(
        {
            "ok": True,
            "post": {
                "id": row["id"],
                "author": row["author"],
                "title": row["title"],
                "content": row["content"],
                "category": row["category"],
                "likes": row["likes"],
                "comment_count": row["comment_count"],
                "created_at": row["created_at"],
                "can_edit": True,
            },
        }
    )


@app.post("/api/forum/posts/<int:post_id>/like")
def api_forum_like(post_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, retry_after = _rate_limit_check(f"api_forum_like:{user_id}:{ip}", limit=50, window_seconds=60)
    if not allowed:
        return jsonify({"ok": False, "error": "Rate limit exceeded", "retry_after": retry_after}), 429

    conn = _get_forum_conn()
    existing = conn.execute(
        "SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?",
        (user_id, post_id),
    ).fetchone()
    liked = False
    if existing:
        conn.execute("DELETE FROM post_likes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE id = ?", (post_id,))
        _log_audit("wisdom_forum", "like_remove", user_id, {"post_id": post_id})
        liked = False
    else:
        conn.execute("INSERT INTO post_likes (user_id, post_id) VALUES (?, ?)", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        _log_audit("wisdom_forum", "like_add", user_id, {"post_id": post_id})
        liked = True
    conn.commit()
    likes = conn.execute("SELECT likes FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return jsonify({"ok": True, "likes": likes["likes"] if likes else 0, "liked": liked})


@app.put("/api/forum/posts/<int:post_id>")
def api_forum_edit(post_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Content is required"}), 400
    if len(content) > FORUM_CONTENT_MAX:
        return jsonify({"ok": False, "error": f"Content must be {FORUM_CONTENT_MAX} characters or fewer."}), 400
    guard = _forum_content_guard(content)
    if guard:
        return jsonify({"ok": False, "error": guard}), 400

    conn = _get_forum_conn()
    post = conn.execute("SELECT author_id, author FROM posts WHERE id = ?", (post_id,)).fetchone()
    forum_user_name = _forum_current_user_name()
    if not post or not (_require_admin() or post["author_id"] == user_id or post["author"] == (forum_user_name or "")):
        conn.close()
        return jsonify({"ok": False, "error": "Not authorised"}), 403
    conn.execute("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
    conn.commit()
    conn.close()
    _log_audit("wisdom_forum", "post_edit", user_id, {"post_id": post_id})
    return jsonify({"ok": True})


@app.delete("/api/forum/posts/<int:post_id>")
def api_forum_delete(post_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    conn = _get_forum_conn()
    post = conn.execute("SELECT author_id, author FROM posts WHERE id = ?", (post_id,)).fetchone()
    forum_user_name = _forum_current_user_name()
    if not post or not (_require_admin() or post["author_id"] == user_id or post["author"] == (forum_user_name or "")):
        conn.close()
        return jsonify({"ok": False, "error": "Not authorised"}), 403
    conn.execute("DELETE FROM post_likes WHERE post_id = ?", (post_id,))
    conn.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    _log_audit("wisdom_forum", "post_delete", user_id, {"post_id": post_id})
    return jsonify({"ok": True})


@app.post("/api/forum/posts/<int:post_id>/delete")
def api_forum_delete_post(post_id: int):
    # Backward-compatible delete endpoint for clients still sending POST.
    return api_forum_delete(post_id)


@app.post("/api/forum/posts/<int:post_id>/edit")
def api_forum_edit_post(post_id: int):
    # Backward-compatible edit endpoint for clients still sending POST.
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    content = (request.form.get("content") or "").strip()
    if not content:
        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Content is required"}), 400
    if len(content) > FORUM_CONTENT_MAX:
        return jsonify({"ok": False, "error": f"Content must be {FORUM_CONTENT_MAX} characters or fewer."}), 400
    guard = _forum_content_guard(content)
    if guard:
        return jsonify({"ok": False, "error": guard}), 400

    conn = _get_forum_conn()
    post = conn.execute("SELECT author_id, author FROM posts WHERE id = ?", (post_id,)).fetchone()
    forum_user_name = _forum_current_user_name()
    if not post or not (_require_admin() or post["author_id"] == user_id or post["author"] == (forum_user_name or "")):
        conn.close()
        return jsonify({"ok": False, "error": "Not authorised"}), 403
    conn.execute("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
    conn.commit()
    conn.close()
    _log_audit("wisdom_forum", "post_edit", user_id, {"post_id": post_id})
    return jsonify({"ok": True})


@app.post("/api/forum/posts/<int:post_id>/report")
def api_forum_report(post_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "other").strip().lower()
    details = (data.get("details") or "").strip()
    if reason not in {"spam", "abuse", "harassment", "misinformation", "other"}:
        reason = "other"

    fconn = _get_forum_conn()
    exists = fconn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
    fconn.close()
    if not exists:
        return jsonify({"ok": False, "error": "Post not found"}), 404

    conn = _get_main_conn()
    conn.execute(
        "INSERT INTO forum_post_reports (post_id, reporter_id, reason, details, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (post_id, user_id, reason, details[:600], _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    _log_audit("wisdom_forum", "post_report", user_id, {"post_id": post_id, "reason": reason})
    return jsonify({"ok": True})


@app.post("/api/forum/blocks/<int:blocked_user_id>")
def api_forum_block_user(blocked_user_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    if blocked_user_id == user_id:
        return jsonify({"ok": False, "error": "Cannot block yourself"}), 400

    conn = _get_main_conn()
    conn.execute(
        "INSERT OR IGNORE INTO user_blocks (user_id, blocked_user_id, created_at) VALUES (?, ?, ?)",
        (user_id, blocked_user_id, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    _log_audit("safety", "block_user", user_id, {"blocked_user_id": blocked_user_id})
    return jsonify({"ok": True})


@app.delete("/api/forum/blocks/<int:blocked_user_id>")
def api_forum_unblock_user(blocked_user_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "Invalid CSRF token"}), 400
    conn = _get_main_conn()
    conn.execute(
        "DELETE FROM user_blocks WHERE user_id = ? AND blocked_user_id = ?",
        (user_id, blocked_user_id),
    )
    conn.commit()
    conn.close()
    _log_audit("safety", "unblock_user", user_id, {"blocked_user_id": blocked_user_id})
    return jsonify({"ok": True})


@app.get("/api/forum/blocks")
def api_forum_blocks():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    blocked = _forum_blocked_user_ids(user_id)
    return jsonify({"ok": True, "blocked_user_ids": blocked})


@app.get("/api/session")
def api_session():
    user_id = _require_login()
    if not user_id:
        return jsonify({"logged_in": False})

    user = db.session.get(User, user_id)
    name = user.full_name if user else "User"
    role = (user.member_type or "youth") if user else "youth"
    settings = _get_user_settings_map(user_id)
    avatar_url = settings.get("avatar_url", "")
    return jsonify({
        "logged_in": True,
        "user_id": user_id,
        "name": name,
        "role": role,
        "is_admin": bool(session.get("is_admin")),
        "avatar_url": avatar_url,
    })


def _coach_interests(user_id: int) -> list:
    settings = _get_user_settings_map(user_id)
    onboarding = _safe_json(settings.get("onboarding", "{}"), {})
    return onboarding.get("interests") or []


def _coach_pick_items(keys: list, field: str, limit: int = 4) -> list:
    out = []
    for key in keys:
        items = COACH_LIBRARY.get(key, {}).get(field, [])
        for item in items:
            if item not in out:
                out.append(item)
            if len(out) >= limit:
                return out
    return out


def _coach_topic_keys(interests: list, mood: str, stage: str) -> list:
    keys = ["general"]
    interest_text = " ".join(interests or []).lower()
    if any(k in interest_text for k in ["food", "hawker", "cooking"]):
        keys.append("hawker")
    if any(k in interest_text for k in ["family", "grand", "parent"]):
        keys.append("family")
    if any(k in interest_text for k in ["childhood", "school", "memories"]):
        keys.append("childhood")
    if any(k in interest_text for k in ["tech", "phone", "digital", "computer"]):
        keys.append("tech")
    if any(k in interest_text for k in ["hobby", "music", "art", "gardening", "exercise"]):
        keys.append("hobbies")
    if any(k in interest_text for k in ["singapore", "travel", "places"]):
        keys.append("singapore")
    if mood == "lonely":
        keys.insert(0, "support")
    if stage == "meetup":
        keys.append("meetup")
    return keys


def _coach_rewrite(text: str) -> str:
    if not text:
        return ""
    out = text
    for word, repl in COACH_REWRITE_MAP.items():
        out = re.sub(rf"\\b{re.escape(word)}\\b", repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\\s{2,}", " ", out).strip()
    return out


@app.get("/api/coach")
def api_coach_suggestions():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    stage = (request.args.get("stage") or "first").strip().lower()
    mood = (request.args.get("mood") or "").strip().lower()
    interests = _coach_interests(user_id)
    keys = _coach_topic_keys(interests, mood, stage)
    icebreakers = _coach_pick_items(keys, "icebreakers", limit=4)
    questions = _coach_pick_items(keys, "questions", limit=4)
    respectful = _coach_pick_items(keys, "respectful", limit=3)
    return jsonify({
        "ok": True,
        "icebreakers": icebreakers,
        "questions": questions,
        "respectful": respectful,
    })


@app.post("/api/coach/rewrite")
def api_coach_rewrite():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    rewritten = _coach_rewrite(text)
    return jsonify({"ok": True, "text": rewritten})


@app.get("/api/matching/profiles")
def api_matching_profiles():
    user_id = _require_login()
    if not user_id:
        return jsonify({"profiles": []})

    viewer_settings = _get_user_settings_map(user_id)
    viewer_onboarding = _safe_json(viewer_settings.get("onboarding", "{}"), {})
    viewer_interests = viewer_onboarding.get("interests") or []
    viewer_skills_teach = viewer_onboarding.get("skills_teach") or _safe_json(viewer_settings.get("skills_teach", "[]"), [])
    viewer_skills_learn = viewer_onboarding.get("skills_learn") or _safe_json(viewer_settings.get("skills_learn", "[]"), [])

    users = User.query.filter(User.id != user_id).order_by(User.created_at.desc()).all()
    profiles = []
    for u in users:
        if _is_blocked_between(user_id, u.id):
            continue
        settings_map = _get_user_settings_map(u.id)
        profiles.append(
            _build_match_profile(
                u,
                settings_map,
                viewer_interests,
                viewer_skills_teach,
                viewer_skills_learn,
            )
        )

    return jsonify({"profiles": profiles})


@app.get("/api/search/users")
def api_search_users():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    query_text = (request.args.get("q") or "").strip().lower()
    users = User.query.filter(User.id != user_id).order_by(User.created_at.desc()).limit(250).all()
    results = []
    for u in users:
        if _is_blocked_between(user_id, u.id):
            continue

        settings_map = _get_user_settings_map(u.id)
        onboarding = _safe_json(settings_map.get("onboarding", "{}"), {})
        interests = [str(i).strip() for i in (onboarding.get("interests") or []) if str(i).strip()]
        bio = (settings_map.get("bio") or "").strip()
        haystack = " ".join([
            (u.full_name or "").strip().lower(),
            bio.lower(),
            " ".join(i.lower() for i in interests),
        ]).strip()
        if query_text and query_text not in haystack:
            continue

        relationship = _friend_state(user_id, u.id)
        safety = _get_safety_snapshot(u.id)
        trust_score = int(safety.get("score", 50))
        identity = _get_user_identity(u.id)
        username = identity.get("username", _username_slug(u.full_name or f"user_{u.id}", u.id))
        results.append(
            {
                "user_id": u.id,
                "username": username,
                "avatar_url": settings_map.get("avatar_url")
                or f"https://api.dicebear.com/7.x/avataaars/svg?seed={urllib.parse.quote(u.full_name or f'User {u.id}')}",
                "bio": bio or "Looking to connect and share experiences.",
                "interests": interests[:5],
                "member_type": (u.member_type or "").strip(),
                "trust_score": trust_score,
                "trust_badge": _trust_badge_label(trust_score),
                "friend_status": relationship["status"],
                "request_id": relationship["request_id"],
                "profile_url": f"/profile/{username}",
            }
        )

    return jsonify({"ok": True, "results": results[:50]})


@app.get("/api/clubs")
def api_list_clubs():
    viewer_id = _require_login()
    if not viewer_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    viewer_id = int(viewer_id)
    query = (request.args.get("q") or "").strip()[:80]
    clubs = _list_clubs(query, limit=120)
    joined = {int(row["id"]) for row in _list_user_joined_clubs(viewer_id)}
    payload = []
    for club in clubs:
        payload.append(
            {
                "id": int(club["id"]),
                "name": club["name"],
                "description": club.get("description") or "",
                "category": club.get("category") or "",
                "banner_path": club.get("banner_path") or "",
                "member_count": int(club.get("member_count") or 0),
                "is_joined": int(club["id"]) in joined,
                "detail_url": f"/clubs/{int(club['id'])}",
            }
        )
    return jsonify({"ok": True, "clubs": payload})


@app.get("/clubs/<int:club_id>")
def club_detail(club_id: int):
    viewer_id = _require_login()
    if not viewer_id:
        return redirect("/login")
    viewer_id = int(viewer_id)
    conn = _get_main_conn()
    row = conn.execute(
        """
        SELECT c.id, c.name, c.description, c.category, c.banner_path, c.created_at,
               (SELECT COUNT(*) FROM club_memberships cm WHERE cm.club_id = c.id) AS member_count
        FROM clubs c
        WHERE c.id = ?
        LIMIT 1
        """,
        (int(club_id),),
    ).fetchone()
    conn.close()
    if not row:
        return ("Not found", 404)
    club = dict(row)
    return render_template(
        "club_detail.html",
        club=club,
        is_member=_is_club_member(viewer_id, int(club_id)),
        sessions=_club_upcoming_sessions(int(club_id)),
    )


@app.post("/api/clubs/<int:club_id>/join")
def api_join_club(club_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    user_id = int(user_id)
    conn = _get_main_conn()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM clubs WHERE id = ?", (int(club_id),)).fetchone()
    if not exists:
        conn.close()
        return jsonify({"ok": False, "error": "Club not found"}), 404
    cur.execute(
        """
        INSERT OR IGNORE INTO club_memberships (user_id, club_id, joined_at)
        VALUES (?, ?, ?)
        """,
        (user_id, int(club_id), _utc_now_iso()),
    )
    conn.commit()
    member_count = int(
        cur.execute("SELECT COUNT(*) FROM club_memberships WHERE club_id = ?", (int(club_id),)).fetchone()[0] or 0
    )
    conn.close()
    _log_audit("social", "club_join", user_id, {"club_id": int(club_id)})
    return jsonify({"ok": True, "is_joined": True, "member_count": member_count})


@app.post("/api/clubs/<int:club_id>/leave")
def api_leave_club(club_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    user_id = int(user_id)
    conn = _get_main_conn()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM clubs WHERE id = ?", (int(club_id),)).fetchone()
    if not exists:
        conn.close()
        return jsonify({"ok": False, "error": "Club not found"}), 404
    cur.execute(
        "DELETE FROM club_memberships WHERE user_id = ? AND club_id = ?",
        (user_id, int(club_id)),
    )
    conn.commit()
    member_count = int(
        cur.execute("SELECT COUNT(*) FROM club_memberships WHERE club_id = ?", (int(club_id),)).fetchone()[0] or 0
    )
    conn.close()
    _log_audit("social", "club_leave", user_id, {"club_id": int(club_id)})
    return jsonify({"ok": True, "is_joined": False, "member_count": member_count})


@app.post("/api/match_requests")
def api_create_match_request():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    receiver_raw = data.get("receiver_id")
    try:
        receiver_id = int(receiver_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "receiver_id is required"}), 400

    if receiver_id == user_id:
        return jsonify({"ok": False, "error": "Cannot request yourself"}), 400

    receiver = db.session.get(User, receiver_id)
    if not receiver:
        return jsonify({"ok": False, "error": "User not found"}), 404
    if _is_blocked_between(user_id, receiver_id):
        return jsonify({"ok": False, "error": "Cannot send request due to privacy settings"}), 403

    conn = _get_chat_conn()
    existing = conn.execute(
        """SELECT id, status FROM match_requests
           WHERE sender_id = ? AND receiver_id = ?
           ORDER BY id DESC LIMIT 1""",
        (user_id, receiver_id),
    ).fetchone()
    if existing and existing["status"] == "pending":
        conn.close()
        return jsonify({"ok": True, "status": "pending", "request_id": existing["id"]}), 200
    if existing and existing["status"] == "accepted":
        conn.close()
        return jsonify({"ok": True, "status": "accepted", "request_id": existing["id"]}), 200

    now = _utc_now_iso()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO match_requests (sender_id, receiver_id, status, created_at, updated_at, sender_seen, receiver_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, receiver_id, "pending", now, None, 1, 0),
    )
    conn.commit()
    request_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "status": "pending", "request_id": request_id}), 201


@app.post("/api/friends/request")
def api_friends_request():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    receiver_raw = data.get("user_id") or data.get("receiver_id")
    try:
        receiver_id = int(receiver_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "user_id is required"}), 400

    if receiver_id == user_id:
        return jsonify({"ok": False, "error": "Cannot request yourself"}), 400
    if _is_blocked_between(user_id, receiver_id):
        return jsonify({"ok": False, "error": "Cannot send request due to privacy settings"}), 403
    receiver = db.session.get(User, receiver_id)
    if not receiver:
        return jsonify({"ok": False, "error": "User not found"}), 404

    conn = _get_chat_conn()
    existing = conn.execute(
        """SELECT id, status FROM match_requests
           WHERE sender_id = ? AND receiver_id = ?
           ORDER BY id DESC LIMIT 1""",
        (user_id, receiver_id),
    ).fetchone()
    if existing and existing["status"] in {"pending", "accepted"}:
        conn.close()
        return jsonify({"ok": True, "status": existing["status"], "request_id": existing["id"]}), 200

    reverse_pending = conn.execute(
        """SELECT id FROM match_requests
           WHERE sender_id = ? AND receiver_id = ? AND status = 'pending'
           ORDER BY id DESC LIMIT 1""",
        (receiver_id, user_id),
    ).fetchone()
    if reverse_pending:
        conn.close()
        return _respond_match_request_action(user_id, int(reverse_pending["id"]), "accept")

    now = _utc_now_iso()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO match_requests (sender_id, receiver_id, status, created_at, updated_at, sender_seen, receiver_seen)
           VALUES (?, ?, 'pending', ?, ?, 1, 0)""",
        (user_id, receiver_id, now, None),
    )
    conn.commit()
    request_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "status": "pending", "request_id": request_id}), 201


@app.get("/api/match_requests/incoming")
def api_list_incoming_match_requests():
    user_id = _require_login()
    if not user_id:
        return jsonify({"requests": []})

    conn = _get_chat_conn()
    rows = conn.execute(
        """SELECT id, sender_id, status, created_at FROM match_requests
           WHERE receiver_id = ? AND status = 'pending'
           ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()

    output = []
    for row in rows:
        if _is_blocked_between(user_id, row["sender_id"]):
            continue
        sender = db.session.get(User, row["sender_id"])
        if not sender:
            continue
        meta = _match_card_for_user(sender)
        output.append(
            {
                "id": row["id"],
                "sender_id": sender.id,
                "sender_name": meta["name"],
                "sender_avatar": meta["avatar"],
                "sender_location": meta["location"],
                "created_at": row["created_at"],
            }
        )
    return jsonify({"requests": output})


def _respond_match_request_action(user_id: int, request_id: int, action: str):
    if action not in {"accept", "decline"}:
        return jsonify({"ok": False, "error": "action must be accept or decline"}), 400

    conn = _get_chat_conn()
    req = conn.execute(
        "SELECT id, sender_id, receiver_id, status FROM match_requests WHERE id = ?",
        (request_id,),
    ).fetchone()
    if not req or req["receiver_id"] != user_id:
        conn.close()
        return jsonify({"ok": False, "error": "Request not found"}), 404
    if _is_blocked_between(req["sender_id"], req["receiver_id"]):
        conn.close()
        return jsonify({"ok": False, "error": "Request is blocked by privacy settings"}), 403
    if req["status"] != "pending":
        conn.close()
        return jsonify({"ok": True, "status": req["status"]}), 200

    next_status = "accepted" if action == "accept" else "declined"
    response_payload = {"ok": True, "status": next_status}
    sender = None
    receiver = None
    should_increment_quest = False
    pending_notifications = []
    try:
        conn.execute(
            """UPDATE match_requests
               SET status = ?, updated_at = ?, receiver_seen = 1, sender_seen = 0
               WHERE id = ?""",
            (next_status, _utc_now_iso(), request_id),
        )

        if next_status == "accepted":
            sender = db.session.get(User, req["sender_id"])
            receiver = db.session.get(User, req["receiver_id"])
            if sender and receiver:
                _ensure_match_row(conn, sender.id, receiver)
                _ensure_match_row(conn, receiver.id, sender)
                response_payload["match"] = {
                    "name": sender.full_name,
                    "chat_id": f"{receiver.id}:user-{sender.id}",
                }
                should_increment_quest = True
                pending_notifications.append(
                    (
                        req["sender_id"],
                        "match_accept",
                        f"{receiver.full_name} accepted your match request.",
                        {"request_id": request_id},
                    )
                )
                pending_notifications.append(
                    (
                        req["receiver_id"],
                        "match_accept",
                        f"You connected with {sender.full_name}.",
                        {"request_id": request_id},
                    )
                )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": str(exc)}), 500

    conn.close()
    if should_increment_quest:
        try:
            _increment_quest_progress(user_id, 4)
        except Exception:
            pass
    for notif_user_id, notif_type, notif_msg, notif_meta in pending_notifications:
        try:
            _add_notification(notif_user_id, notif_type, notif_msg, notif_meta)
        except Exception:
            pass
    return jsonify(response_payload)


@app.post("/api/match_requests/<int:request_id>/respond")
def api_respond_match_request(request_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip().lower()
    return _respond_match_request_action(user_id, request_id, action)


@app.post("/api/friends/accept")
def api_friends_accept():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    request_id = data.get("request_id")
    try:
        request_id = int(request_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "request_id is required"}), 400
    return _respond_match_request_action(user_id, request_id, "accept")


@app.post("/api/friends/decline")
def api_friends_decline():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    request_id = data.get("request_id")
    try:
        request_id = int(request_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "request_id is required"}), 400
    return _respond_match_request_action(user_id, request_id, "decline")


@app.post("/api/friends/unfriend")
def api_friends_unfriend():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    target_raw = data.get("user_id")
    try:
        target_user_id = int(target_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "user_id is required"}), 400
    if target_user_id == user_id:
        return jsonify({"ok": False, "error": "Cannot unfriend yourself"}), 400

    conn = _get_chat_conn()
    conn.execute(
        """
        UPDATE match_requests
        SET status = 'declined', updated_at = ?, sender_seen = 0, receiver_seen = 0
        WHERE status = 'accepted'
          AND ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        """,
        (_utc_now_iso(), user_id, target_user_id, target_user_id, user_id),
    )
    own_match_key = f"{user_id}:user-{target_user_id}"
    other_match_key = f"{target_user_id}:user-{user_id}"
    canonical = f"dm:{min(user_id, target_user_id)}-{max(user_id, target_user_id)}"
    conn.execute("DELETE FROM matches WHERE (user_id = ? AND match_id = ?) OR (user_id = ? AND match_id = ?)", (user_id, own_match_key, target_user_id, other_match_key))
    conn.execute("DELETE FROM messages WHERE chat_id IN (?, ?, ?)", (own_match_key, other_match_key, canonical))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/friends/block")
def api_friends_block():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    data = request.get_json(silent=True) or {}
    target_raw = data.get("user_id")
    try:
        target_user_id = int(target_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "user_id is required"}), 400
    if target_user_id == user_id:
        return jsonify({"ok": False, "error": "Cannot block yourself"}), 400

    conn = _get_main_conn()
    conn.execute(
        "INSERT OR IGNORE INTO user_blocks (user_id, blocked_user_id, created_at) VALUES (?, ?, ?)",
        (user_id, target_user_id, _utc_now_iso()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO blocks (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
        (user_id, target_user_id, _utc_now_iso()),
    )
    conn.execute(
        "DELETE FROM follows WHERE (follower_id = ? AND followed_id = ?) OR (follower_id = ? AND followed_id = ?)",
        (user_id, target_user_id, target_user_id, user_id),
    )
    conn.commit()
    conn.close()

    cconn = _get_chat_conn()
    cconn.execute(
        """
        UPDATE match_requests
        SET status = 'declined', updated_at = ?, sender_seen = 0, receiver_seen = 0
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        """,
        (_utc_now_iso(), user_id, target_user_id, target_user_id, user_id),
    )
    own_match_key = f"{user_id}:user-{target_user_id}"
    other_match_key = f"{target_user_id}:user-{user_id}"
    canonical = f"dm:{min(user_id, target_user_id)}-{max(user_id, target_user_id)}"
    cconn.execute("DELETE FROM matches WHERE (user_id = ? AND match_id = ?) OR (user_id = ? AND match_id = ?)", (user_id, own_match_key, target_user_id, other_match_key))
    cconn.execute("DELETE FROM messages WHERE chat_id IN (?, ?, ?)", (own_match_key, other_match_key, canonical))
    cconn.commit()
    cconn.close()
    _log_audit("safety", "block_user", user_id, {"blocked_user_id": target_user_id})
    return jsonify({"ok": True})


@app.get("/api/notifications")
def api_notifications():
    user_id = _require_login()
    if not user_id:
        return jsonify({"notifications": [], "unread_count": 0})
    _run_reminder_notifications_for_user(user_id)

    conn = _get_chat_conn()
    pending = conn.execute(
        """SELECT id, sender_id, created_at, receiver_seen
           FROM match_requests
           WHERE receiver_id = ? AND status = 'pending'
           ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    decisions = conn.execute(
        """SELECT id, receiver_id, status, COALESCE(updated_at, created_at) AS ts
           FROM match_requests
           WHERE sender_id = ? AND status IN ('accepted', 'declined') AND sender_seen = 0
           ORDER BY ts DESC""",
        (user_id,),
    ).fetchall()
    conn.close()

    notifications = []
    unread_count = 0

    for row in pending:
        sender = db.session.get(User, row["sender_id"])
        if not sender:
            continue
        meta = _match_card_for_user(sender)
        is_unread = row["receiver_seen"] == 0
        if is_unread:
            unread_count += 1
        notifications.append(
            {
                "id": f"req-{row['id']}",
                "type": "match_request",
                "request_id": row["id"],
                "sender_id": sender.id,
                "sender_name": meta["name"],
                "sender_avatar": meta["avatar"],
                "sender_location": meta["location"],
                "created_at": row["created_at"],
                "unread": is_unread,
            }
        )

    for row in decisions:
        receiver = db.session.get(User, row["receiver_id"])
        if not receiver:
            continue
        meta = _match_card_for_user(receiver)
        notifications.append(
            {
                "id": f"dec-{row['id']}",
                "type": "match_decision",
                "request_id": row["id"],
                "status": row["status"],
                "receiver_id": receiver.id,
                "receiver_name": meta["name"],
                "receiver_avatar": meta["avatar"],
                "created_at": row["ts"],
                "unread": True,
            }
        )
        unread_count += 1

    conn = _get_main_conn()
    extra_rows = conn.execute(
        """SELECT id, user_id, type, message, meta_json, is_read, created_at
           FROM notifications
           WHERE user_id = ? OR user_id IS NULL
           ORDER BY created_at DESC
           LIMIT 50""",
        (user_id,),
    ).fetchall()
    conn.close()
    for row in extra_rows:
        is_global = row["user_id"] is None
        is_unread = (row["is_read"] == 0) and not is_global and row["user_id"] == user_id
        if is_unread:
            unread_count += 1
        notifications.append(
            {
                "id": f"sys-{row['id']}",
                "type": row["type"] or "system",
                "message": row["message"],
                "created_at": row["created_at"],
                "unread": is_unread,
            }
        )

    notifications.sort(key=lambda n: n.get("created_at") or "", reverse=True)
    return jsonify({"notifications": notifications, "unread_count": unread_count})


@app.post("/api/notifications/mark_read")
def api_notifications_mark_read():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_chat_conn()
    conn.execute(
        "UPDATE match_requests SET receiver_seen = 1 WHERE receiver_id = ? AND status = 'pending'",
        (user_id,),
    )
    conn.execute(
        "UPDATE match_requests SET sender_seen = 1 WHERE sender_id = ? AND status IN ('accepted', 'declined')",
        (user_id,),
    )
    conn.commit()
    conn.close()
    conn = _get_main_conn()
    conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "redirect_url": "/dashboard#tab-challenges"})


@app.get("/api/avatar")
def api_avatar_proxy():
    params = request.args.to_dict(flat=True)
    qs = urllib.parse.urlencode(params)
    remote_url = f"https://api.dicebear.com/6.x/avataaars/svg?{qs}"
    try:
        with urllib.request.urlopen(remote_url, timeout=5) as resp:
            data = resp.read()
        return Response(data, mimetype="image/svg+xml")
    except Exception:
        return Response("", status=502)


@app.get("/api/avatar/options")
def api_avatar_options():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    return jsonify({"ok": True, "options": AVATAR_OPTIONS, "default": AVATAR_DEFAULT_CONFIG})


@app.get("/api/avatar/me")
def api_avatar_me():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    conn = _get_main_conn()
    row = conn.execute(
        "SELECT config_json FROM user_avatar WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"ok": True, "config": AVATAR_DEFAULT_CONFIG, "source": "default"})

    try:
        loaded = json.loads(row["config_json"] or "{}")
        if not isinstance(loaded, dict):
            loaded = {}
    except Exception:
        loaded = {}
    merged = {**AVATAR_DEFAULT_CONFIG, **loaded}
    return jsonify({"ok": True, "config": merged, "source": "db"})


@app.post("/api/avatar/me")
def api_avatar_me_save():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    config = data.get("config")
    if not isinstance(config, dict):
        return jsonify({"ok": False, "error": "config must be an object"}), 400

    cleaned = {}
    for key, allowed in AVATAR_OPTIONS.items():
        if key == "avatar_name":
            name_value = str(config.get("avatar_name", AVATAR_DEFAULT_CONFIG["avatar_name"]) or "").strip()
            cleaned["avatar_name"] = name_value[:40]
            continue
        selected = config.get(key, AVATAR_DEFAULT_CONFIG[key])
        if selected not in allowed:
            selected = AVATAR_DEFAULT_CONFIG[key]
        cleaned[key] = selected

    conn = _get_main_conn()
    conn.execute(
        """
        INSERT INTO user_avatar (user_id, config_json, updated_at, snapshot_path)
        VALUES (?, ?, ?, NULL)
        ON CONFLICT(user_id) DO UPDATE SET
            config_json = excluded.config_json,
            updated_at = excluded.updated_at
        """,
        (user_id, json.dumps(cleaned), _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "config": cleaned})


@app.get("/api/admin/chat/messages")
def api_admin_chat_messages():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 403
    conn = _get_chat_conn()
    rows = conn.execute(
        "SELECT id, sender, text, created_at FROM admin_messages ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return jsonify([{
        "id": r["id"],
        "sender": r["sender"],
        "text": r["text"],
        "created_at": r["created_at"],
    } for r in rows])


@app.post("/api/admin/chat/messages")
def api_admin_chat_send():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 403
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Message is required"}), 400
    sender = session.get("admin_id") or "admin"
    conn = _get_chat_conn()
    conn.execute(
        "INSERT INTO admin_messages (sender, text, created_at) VALUES (?, ?, ?)",
        (sender, text, _utc_now_iso()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, sender, text, created_at FROM admin_messages WHERE id = last_insert_rowid()"
    ).fetchone()
    conn.close()
    return jsonify({
        "id": row["id"],
        "sender": row["sender"],
        "text": row["text"],
        "created_at": row["created_at"],
    }), 201


@app.get("/api/circle/chat/messages")
def api_circle_chat_messages():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    title = (request.args.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "title is required"}), 400
    conn = _get_chat_conn()
    rows = conn.execute(
        "SELECT id, circle_title, sender, text, created_at FROM circle_messages WHERE circle_title = ? ORDER BY id ASC",
        (title,),
    ).fetchall()
    conn.close()
    return jsonify([{
        "id": r["id"],
        "circle_title": r["circle_title"],
        "sender": r["sender"],
        "text": r["text"],
        "created_at": r["created_at"],
    } for r in rows])


@app.post("/api/circle/chat/messages")
def api_circle_chat_send():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    text = (data.get("text") or "").strip()
    if not title or not text:
        return jsonify({"ok": False, "error": "title and text are required"}), 400

    user = db.session.get(User, user_id)
    sender_name = user.full_name if user else "User"

    conn = _get_chat_conn()
    conn.execute(
        "INSERT INTO circle_messages (circle_title, sender, text, created_at) VALUES (?, ?, ?, ?)",
        (title, sender_name, text, _utc_now_iso()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id, circle_title, sender, text, created_at FROM circle_messages WHERE id = last_insert_rowid()",
    ).fetchone()
    conn.close()
    return jsonify({
        "id": row["id"],
        "circle_title": row["circle_title"],
        "sender": row["sender"],
        "text": row["text"],
        "created_at": row["created_at"],
    }), 201


@app.get("/api/matches")
def api_list_matches():
    user_id = _require_login()
    if not user_id:
        return jsonify([]), 200
    conn = _get_chat_conn()
    rows = conn.execute(
        "SELECT match_id, name, avatar, location, created_at FROM matches WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return jsonify([_chat_match_to_dict(r) for r in rows])


def _other_user_id_from_match_id(viewer_id: int, match_id: str) -> int | None:
    raw = (match_id or "").strip()
    if not raw:
        return None
    m = re.match(r"^dm:(\d+)-(\d+)$", raw)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        if a == int(viewer_id):
            return b
        if b == int(viewer_id):
            return a
    m = re.match(r"^\d+:user-(\d+)$", raw)
    if m:
        return int(m.group(1))
    m = re.match(rf"^{viewer_id}:user-(\d+)$", raw)
    if m:
        return int(m.group(1))
    m = re.match(r"^user-(\d+)$", raw)
    if m:
        return int(m.group(1))
    m = re.match(r"^\d+:(\d+)$", raw)
    if m:
        return int(m.group(1))
    return None


def _canonical_chat_id(raw_chat_id: str, viewer_id: int | None) -> str:
    raw = str(raw_chat_id or "").strip()
    if not raw:
        return ""
    if raw.startswith("dm:"):
        return raw
    if viewer_id:
        other_id = _other_user_id_from_match_id(viewer_id, raw)
        if other_id:
            lo, hi = sorted([int(viewer_id), int(other_id)])
            return f"dm:{lo}-{hi}"
    return raw


def _normalize_sender_role(value: str) -> str:
    role = str(value or "").strip().lower()
    if role in ("senior", "elderly", "old", "older"):
        return "elderly"
    return "youth"


def _chat_contains_restricted(text: str) -> bool:
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return False
    conn = _get_chat_conn()
    rows = conn.execute("SELECT word FROM profanities").fetchall()
    conn.close()
    for row in rows:
        word = str(row["word"] or "").strip().lower()
        if not word:
            continue
        if " " in word:
            if word in cleaned:
                return True
        else:
            if re.search(rf"\b{re.escape(word)}\b", cleaned):
                return True
    return False


def _record_chat_moderation_strike(user_id: int, text: str, chat_id: str = "") -> dict:
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT COALESCE(strike_count, 0) AS strike_count FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    strike = int(row["strike_count"] if row else 0) + 1
    cooldown_until = None
    action = "warning"
    trust_delta = 0
    if strike == 2:
        action = "cooldown"
        cooldown_until = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    elif strike >= 3:
        action = "trust_penalty"
        trust_delta = -3
    cur.execute(
        "UPDATE users SET strike_count = ?, chat_cooldown_until = COALESCE(?, chat_cooldown_until) WHERE id = ?",
        (strike, cooldown_until, user_id),
    )
    cur.execute(
        "INSERT INTO moderation_events (user_id, message_preview, action, created_at) VALUES (?, ?, ?, ?)",
        (user_id, (text or "")[:180], action, _utc_now_iso()),
    )
    if strike >= 3:
        incident_date = datetime.utcnow().date().isoformat()
        cur.execute(
            """
            INSERT INTO reports (user_id, reporter_id, reported_id, context_type, context_id, reason, incident_date, details, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                user_id,
                user_id,
                user_id,
                "chat",
                chat_id or None,
                "inappropriate messages",
                incident_date,
                "Auto-generated moderation report (strike ladder).",
                _utc_now_iso(),
            ),
        )
    conn.commit()
    conn.close()
    if trust_delta:
        _apply_trust_delta(user_id, trust_delta, "Repeated chat moderation strikes")
    return {"strike_count": strike, "action": action, "cooldown_until": cooldown_until}


@app.get("/api/matches/<path:match_id>/overview")
def api_match_overview(match_id: str):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    target_user_id = _other_user_id_from_match_id(user_id, match_id)
    if not target_user_id:
        return jsonify({"ok": False, "error": "Could not determine connected user"}), 400

    target_user = db.session.get(User, target_user_id)
    if not target_user:
        return jsonify({"ok": False, "error": "Connected user not found"}), 404

    viewer_settings = _get_user_settings_map(user_id)
    target_settings = _get_user_settings_map(target_user_id)
    viewer_onboarding = _safe_json(viewer_settings.get("onboarding", "{}"), {})
    target_onboarding = _safe_json(target_settings.get("onboarding", "{}"), {})

    viewer_stations = _extract_stations(viewer_onboarding, viewer_settings.get("location_name", ""))
    target_stations = _extract_stations(target_onboarding, target_settings.get("location_name", ""))
    midpoint_station = _pick_midpoint_station(viewer_stations, target_stations)
    safe_locations = _safe_locations_for_stations([midpoint_station], limit=4) if midpoint_station else []

    interests = target_onboarding.get("interests") or []
    skills_teach = target_onboarding.get("skills_teach") or _safe_json(target_settings.get("skills_teach", "[]"), [])
    skills_learn = target_onboarding.get("skills_learn") or _safe_json(target_settings.get("skills_learn", "[]"), [])

    payload = {
        "ok": True,
        "profile": {
            "user_id": target_user.id,
            "name": target_user.full_name or "User",
            "member_type": (target_user.member_type or target_onboarding.get("memberType") or "").strip(),
            "avatar_url": target_settings.get("avatar_url") or f"https://api.dicebear.com/7.x/avataaars/svg?seed={urllib.parse.quote(target_user.full_name or 'User')}",
            "interests": interests[:6],
            "skills_teach": (skills_teach or [])[:4],
            "skills_learn": (skills_learn or [])[:4],
            "stations": target_stations[:6],
            "midpoint_station": midpoint_station,
            "safe_locations": safe_locations,
            "profile_url": f"/profile/{target_user.id}",
        },
    }
    return jsonify(payload)


@app.post("/api/matches")
def api_create_match():
    user_id = _require_login()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    match_id = (data.get("match_id") or "").strip()
    if match_id:
        prefix = f"{user_id}:"
        match_key = match_id if match_id.startswith(prefix) else f"{prefix}{match_id}"
    else:
        match_key = ""
    name = (data.get("name") or "").strip()
    avatar = (data.get("avatar") or "").strip()
    location = (data.get("location") or "").strip()

    if not match_id or not name or not avatar:
        return jsonify({"error": "match_id, name, avatar are required"}), 400

    conn = _get_chat_conn()
    existing = conn.execute(
        "SELECT match_id, name, avatar, location, created_at FROM matches WHERE match_id = ? AND user_id = ?",
        (match_key, user_id),
    ).fetchone()
    if existing:
        conn.close()
        return jsonify(_chat_match_to_dict(existing)), 200

    conn.execute(
        "INSERT INTO matches (user_id, match_id, name, avatar, location, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, match_key, name, avatar, location or None, _utc_now_iso()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT match_id, name, avatar, location, created_at FROM matches WHERE match_id = ? AND user_id = ?",
        (match_key, user_id),
    ).fetchone()
    conn.close()
    _log_audit("matches", "create", user_id, {"match_id": match_id})
    return jsonify(_chat_match_to_dict(row)), 201


@app.delete("/api/matches")
def api_clear_matches():
    user_id = _require_login()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    conn = _get_chat_conn()
    match_ids = conn.execute(
        "SELECT match_id FROM matches WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    conn.execute("DELETE FROM messages WHERE chat_id IN (SELECT match_id FROM matches WHERE user_id = ?)", (user_id,))
    conn.execute("DELETE FROM matches WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    _log_audit("matches", "clear", user_id, {"count": len(match_ids)})
    return jsonify({"ok": True})


@app.delete("/api/matches/<match_id>")
def api_delete_match(match_id):
    user_id = _require_login()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    conn = _get_chat_conn()
    existing = conn.execute(
        "SELECT match_id FROM matches WHERE match_id = ? AND user_id = ?",
        (match_id, user_id),
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "match not found"}), 404

    conn.execute("DELETE FROM messages WHERE chat_id = ?", (match_id,))
    conn.execute("DELETE FROM matches WHERE match_id = ? AND user_id = ?", (match_id, user_id))
    conn.commit()
    conn.close()
    _log_audit("matches", "clear", user_id)
    return jsonify({"ok": True})


@app.get("/api/messages/<chat_id>")
def api_list_messages(chat_id):
    viewer_id = _require_login()
    if not viewer_id:
        return jsonify({"error": "Not logged in"}), 401
    other_user_id = _other_user_id_from_match_id(viewer_id, str(chat_id))
    if other_user_id and _is_blocked_between(viewer_id, other_user_id):
        return jsonify({"error": "This chat is unavailable due to privacy settings"}), 403
    if other_user_id and not _can_access_pair_conversation(int(viewer_id), int(other_user_id), str(chat_id)):
        return jsonify({"error": "Not allowed to access this conversation"}), 403
    canonical_chat_id = _canonical_chat_id(chat_id, viewer_id)
    chat_ids = [chat_id]
    if canonical_chat_id and canonical_chat_id not in chat_ids:
        chat_ids.append(canonical_chat_id)
    conn = _get_chat_conn()
    if len(chat_ids) == 1:
        rows = conn.execute(
            "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
            (chat_ids[0],),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE chat_id IN (?, ?) ORDER BY created_at ASC",
            (chat_ids[0], chat_ids[1]),
        ).fetchall()
    conn.close()
    return jsonify([_chat_message_to_dict(r) for r in rows])


@app.post("/api/messages/<chat_id>")
def api_create_message(chat_id):
    viewer_id = _require_login()
    if not viewer_id:
        return jsonify({"error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403

    user_ok, user_retry = _rate_limit_check(f"msg:user:{int(viewer_id)}", limit=10, window_seconds=10)
    if not user_ok:
        return jsonify({"error": "Too many messages. Slow down.", "retry_after": user_retry}), 429
    client_ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "unknown").split(",")[0].strip()[:80]
    ip_ok, ip_retry = _rate_limit_check(f"msg:ip:{client_ip}", limit=30, window_seconds=10)
    if not ip_ok:
        return jsonify({"error": "Too many requests from this IP.", "retry_after": ip_retry}), 429

    data = request.get_json(silent=True) or {}
    sender = _normalize_sender_role(data.get("sender") or "youth")
    text = (data.get("text") or "").strip()
    has_media = bool(data.get("has_media") or data.get("media_id") or (data.get("media_url") or "").strip())
    target_chat_id = _canonical_chat_id(chat_id, viewer_id) or str(chat_id or "").strip()
    other_user_id = _other_user_id_from_match_id(viewer_id, target_chat_id) or _other_user_id_from_match_id(viewer_id, str(chat_id))
    if not other_user_id:
        return jsonify({"error": "Invalid conversation target"}), 400
    if other_user_id and _is_blocked_between(viewer_id, other_user_id):
        return jsonify({"error": "Cannot message this user due to privacy settings"}), 403
    if not _can_access_pair_conversation(int(viewer_id), int(other_user_id), target_chat_id):
        return jsonify({"error": "Not allowed to message this user"}), 403

    if not text and not has_media:
        return jsonify({"error": "text is required"}), 400

    u = db.session.get(User, viewer_id)
    if u and getattr(u, "chat_cooldown_until", None):
        cooldown_dt = _parse_iso_dt(u.chat_cooldown_until)
        if cooldown_dt and datetime.utcnow() < cooldown_dt:
            retry_after = int((cooldown_dt - datetime.utcnow()).total_seconds())
            return jsonify({"error": "Chat cooldown active", "retry_after": max(1, retry_after)}), 429

    if _chat_contains_restricted(text):
        result = _record_chat_moderation_strike(viewer_id, text, str(target_chat_id))
        strike = int(result.get("strike_count", 1))
        if result.get("action") == "cooldown":
            return jsonify({"error": "Please keep chat respectful. 10-minute cooldown applied.", "strike_count": strike}), 429
        if result.get("action") == "trust_penalty":
            return jsonify({"error": "Please keep chat respectful. Message blocked and safety review queued.", "strike_count": strike}), 400
        return jsonify({"error": "Please keep chat respectful. Message blocked.", "strike_count": strike}), 400

    conn = _get_chat_conn()
    conn.execute(
        "INSERT INTO messages (chat_id, sender, text, created_at) VALUES (?, ?, ?, ?)",
        (target_chat_id, sender, text, _utc_now_iso()),
    )
    msg = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = last_insert_rowid()",
    ).fetchone()
    plant_state = award_pair_plant_growth(
        conn,
        int(viewer_id),
        int(other_user_id),
        text,
        bool(has_media),
    )
    conn.commit()
    conn.close()
    payload = _chat_message_to_dict(msg)
    payload["ok"] = True
    payload["message_id"] = payload.get("id")
    payload["plant"] = plant_state
    return jsonify(payload), 201


@app.get("/api/plants/pair")
def api_pair_plant_state():
    viewer_id = _require_login()
    if not viewer_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    raw_other = request.args.get("user_id", "")
    if not str(raw_other).strip().isdigit():
        return jsonify({"ok": False, "error": "user_id must be an integer"}), 400
    other_user_id = int(raw_other)
    if other_user_id <= 0:
        return jsonify({"ok": False, "error": "user_id must be positive"}), 400
    if int(other_user_id) == int(viewer_id):
        return jsonify({"ok": False, "error": "pair must include another user"}), 400

    if _is_blocked_between(int(viewer_id), int(other_user_id)):
        return jsonify({"ok": False, "error": "Conversation unavailable"}), 403
    if not _can_access_pair_conversation(int(viewer_id), int(other_user_id), f"dm:{min(int(viewer_id), int(other_user_id))}-{max(int(viewer_id), int(other_user_id))}"):
        return jsonify({"ok": False, "error": "Not allowed"}), 403

    conn = _get_chat_conn()
    state = _current_pair_plant_state(conn, int(viewer_id), int(other_user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "plant": state})


@app.put("/api/messages/<int:message_id>")
def api_update_message(message_id):
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    conn = _get_chat_conn()
    msg = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    if not msg:
        conn.close()
        return jsonify({"error": "message not found"}), 404
    if msg["is_deleted"]:
        conn.close()
        return jsonify({"error": "cannot edit deleted message"}), 400

    conn.execute(
        "UPDATE messages SET text = ?, edited_at = ? WHERE id = ?",
        (text, _utc_now_iso(), message_id),
    )
    conn.commit()
    updated = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    conn.close()
    return jsonify(_chat_message_to_dict(updated))


@app.delete("/api/messages/<int:message_id>")
def api_delete_message(message_id):
    conn = _get_chat_conn()
    msg = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    if not msg:
        conn.close()
        return jsonify({"error": "message not found"}), 404

    conn.execute(
        "UPDATE messages SET is_deleted = 1, deleted_at = ? WHERE id = ?",
        (_utc_now_iso(), message_id),
    )
    conn.commit()
    deleted = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    conn.close()
    return jsonify(_chat_message_to_dict(deleted))


@app.post("/api/messages/<int:message_id>/restore")
def api_restore_message(message_id):
    conn = _get_chat_conn()
    msg = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    if not msg:
        conn.close()
        return jsonify({"error": "message not found"}), 404

    conn.execute(
        "UPDATE messages SET is_deleted = 0, deleted_at = NULL WHERE id = ?",
        (message_id,),
    )
    conn.commit()
    restored = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    conn.close()
    return jsonify(_chat_message_to_dict(restored))


@app.get("/api/profanities")
def api_list_profanities():
    level = (request.args.get("level") or "").strip().lower()
    if level and level not in ("mild", "strong", "extreme"):
        return jsonify({"error": "level must be mild, strong, or extreme"}), 400

    conn = _get_chat_conn()
    if level:
        rows = conn.execute(
            "SELECT id, word, level, created_at, updated_at FROM profanities WHERE level = ? ORDER BY word ASC",
            (level,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, word, level, created_at, updated_at FROM profanities ORDER BY word ASC",
        ).fetchall()
    conn.close()
    return jsonify([{
        "id": r["id"],
        "word": r["word"],
        "level": r["level"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    } for r in rows])


@app.post("/api/profanity-block")
def api_profanity_block():
    data = request.get_json(silent=True) or {}
    chat_id = (data.get("chat_id") or "").strip()
    text = (data.get("text") or "").strip()
    if not chat_id or not text:
        return jsonify({"error": "chat_id and text are required"}), 400
    return jsonify({"ok": True}), 201

@app.get("/<path:page>")
def page(page: str):
    if page.endswith(".html"):
        page = page[:-5]

    if page in PAGES:
        if page == "dashboard":
            selected_category = (request.args.get("filter") or "all").strip()
            allowed = {"all", *FORUM_CATEGORIES}
            if selected_category not in allowed:
                selected_category = "all"
            posts = _forum_list_posts(selected_category, viewer_user_id=_require_login())
            user_id = _require_login()
            connections_count = 0
            memories_count = 0
            repoints_count = 0
            circles_count = 0
            badges_count = 0
            if user_id:
                conn = _get_chat_conn()
                connections_count = conn.execute(
                    "SELECT COUNT(*) AS c FROM matches WHERE user_id = ?", (user_id,)
                ).fetchone()["c"]
                conn.close()

                conn = _get_main_conn()
                memories_count = conn.execute(
                    "SELECT COUNT(*) AS c FROM challenge_entries WHERE user_id = ?", (user_id,)
                ).fetchone()["c"]
                badges_count = conn.execute(
                    "SELECT COUNT(*) AS c FROM user_badges WHERE user_id = ? AND earned = 1",
                    (user_id,),
                ).fetchone()["c"]
                conn.close()

                u = db.session.get(User, user_id)
                repoints_count, _ = _get_user_points(user_id)
                circles_count = CircleSignup.query.filter_by(user_id=user_id).count()

            return render_template(
                PAGES[page],
                posts=posts,
                selected_category=selected_category,
                is_admin=_require_admin(),
                forum_user_name=_forum_current_user_name(),
                connections_count=connections_count,
                memories_count=memories_count,
                repoints_count=repoints_count,
                circles_count=circles_count,
                badges_count=badges_count,
            )
        if page == "login-2fa":
            pending_email = (session.get("pending_2fa_email") or "").strip()
            if not pending_email:
                return redirect("/login")
            return render_template(
                PAGES[page],
                pending_email=pending_email,
                delivery=(session.get("pending_2fa_delivery") or "email"),
                dev_code=(session.get("pending_2fa_dev_code") or ""),
                resend_available_in=_seconds_until_iso(session.get("pending_2fa_expires_at")),
            )
        if page == "signup-2fa":
            pending_email = (session.get("pending_signup_email") or "").strip()
            if not pending_email:
                return redirect("/signup")
            return render_template(
                PAGES[page],
                pending_email=pending_email,
                delivery=(session.get("pending_signup_delivery") or "email"),
                dev_code=(session.get("pending_signup_dev_code") or ""),
                resend_available_in=_seconds_until_iso(session.get("pending_signup_expires_at")),
            )
        if page == "forum":
            selected_category = (request.args.get("filter") or "all").strip()
            allowed = {"all", *FORUM_CATEGORIES}
            if selected_category not in allowed:
                selected_category = "all"
            search = (request.args.get("q") or "").strip()
            sort = (request.args.get("sort") or "newest").strip().lower()
            if sort not in {"newest", "likes", "comments"}:
                sort = "newest"
            page_num = request.args.get("page", type=int) or 1
            user_id = _require_login()
            posts, total_posts = _forum_list_posts(
                selected_category,
                page=page_num,
                per_page=FORUM_PAGE_SIZE,
                search=search,
                sort=sort,
                viewer_user_id=user_id,
            )
            total_pages = max(1, (total_posts + FORUM_PAGE_SIZE - 1) // FORUM_PAGE_SIZE)
            page_num = min(max(1, page_num), total_pages)
            if total_posts and not posts and page_num > 1:
                posts, _ = _forum_list_posts(
                    selected_category,
                    page=page_num,
                    per_page=FORUM_PAGE_SIZE,
                    search=search,
                    sort=sort,
                    viewer_user_id=user_id,
                )
            return render_template(
                PAGES[page],
                posts=posts,
                selected_category=selected_category,
                is_admin=_require_admin(),
                forum_user_name=_forum_current_user_name(),
                user_id=user_id,
                page_num=page_num,
                total_pages=total_pages,
                total_posts=total_posts,
                forum_q=search,
                forum_sort=sort,
            )
        if page == "profile":
            viewer_user_id = _require_login()
            if not viewer_user_id:
                return redirect("/login")
            target_user_id = request.args.get("user_id", type=int) or int(viewer_user_id)
            return _render_profile_page(int(viewer_user_id), int(target_user_id))
        if page == "explore":
            viewer_user_id = _require_login()
            if not viewer_user_id:
                return redirect("/login")
            explore_type = (request.args.get("type") or "people").strip().lower()
            if explore_type not in {"people", "clubs"}:
                explore_type = "people"
            explore_query = (request.args.get("q") or "").strip()[:80]
            clubs = _list_clubs(explore_query if explore_type == "clubs" else "", limit=120)
            joined = {int(row["id"]) for row in _list_user_joined_clubs(int(viewer_user_id))}
            for club in clubs:
                club["is_joined"] = int(club["id"]) in joined
            return render_template(
                PAGES[page],
                explore_type=explore_type,
                explore_query=explore_query,
                clubs=clubs,
            )
        if page == "wellbeing":
            if not _require_login():
                return redirect("/login")
            user_id = session["user_id"]
            u = db.session.get(User, user_id)
            return render_template(PAGES[page], user=u)
        if page in {"events", "hangouts"}:
            if not _require_login():
                return redirect("/login")
            user_id = session["user_id"]
            u = db.session.get(User, user_id)
            if page == "events":
                return render_template(PAGES[page], user=u, google_maps_key=_google_maps_key())
            return render_template(PAGES[page], user=u)
        if page == "avatar":
            if not _require_login():
                return redirect("/login")
            return render_template(PAGES[page])
        if page == "scrapbook":
            if not _require_login():
                return redirect("/login")
            user_id = session["user_id"]
            u = db.session.get(User, user_id)
            return render_template(PAGES[page], user=u)
        if page == "feed":
            if not _require_login():
                return redirect("/login")
            user_id = session["user_id"]
            u = db.session.get(User, user_id)
            return render_template(PAGES[page], user=u)
        if page == "onboarding":
            user_id = _require_login()
            if user_id:
                settings = UserSetting.query.filter_by(user_id=user_id).all()
                user_settings = {s.key: s.value for s in settings}
                onboarding = json.loads(user_settings.get("onboarding", "{}"))
                return render_template(PAGES[page], onboarding=onboarding)
            else:
                return render_template(PAGES[page], onboarding={})
        if page == "achievements":
            user_id = _require_login()
            if not user_id:
                return redirect("/login")
            u = db.session.get(User, user_id)
            return render_template(PAGES[page], user=u)
        return render_template(PAGES[page])

    return ("Not found", 404)


def _require_login():
    demo_user = request.headers.get("X-Demo-User")
    if demo_user:
        try:
            demo_id = int(demo_user)
        except (TypeError, ValueError):
            return None
        user = db.session.get(User, demo_id)
        return demo_id if user else None

    user_id = session.get("user_id")
    if not user_id:
        return None
    return user_id


def login_required(view_func):
    @wraps(view_func)
    def _wrapped(*args, **kwargs):
        user_id = _require_login()
        if not user_id:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Not logged in"}), 401
            return redirect("/login")
        g.current_user_id = int(user_id)
        return view_func(*args, **kwargs)
    return _wrapped


def _coerce_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_valid_username(username: str) -> bool:
    return bool(USERNAME_RE.fullmatch((username or "").strip()))


def _username_slug(seed: str, fallback_id: int | None = None) -> str:
    raw = re.sub(r"[^a-zA-Z0-9_.]+", "_", (seed or "").strip().lower()).strip("._")
    raw = re.sub(r"_+", "_", raw)
    if not raw:
        raw = "user"
    if len(raw) < 3:
        raw = (raw + "_user")[:30]
    raw = raw[:30]
    if fallback_id is not None and len(raw) < 30:
        suffix = f"_{int(fallback_id)}"
        if len(raw) + len(suffix) <= 30:
            raw = f"{raw}{suffix}"
    return raw


def _get_user_identity(user_id: int) -> dict:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT id, username, is_private, full_name, email FROM users WHERE id = ? LIMIT 1",
        (int(user_id),),
    ).fetchone()
    conn.close()
    if not row:
        return {}
    username = (row["username"] or "").strip()
    if not _is_valid_username(username):
        username = _username_slug(row["full_name"] or row["email"] or f"user_{int(user_id)}", int(user_id))
    return {
        "id": int(row["id"]),
        "username": username,
        "is_private": int(row["is_private"] or 0),
    }


def _get_user_by_username(username: str):
    cleaned = (username or "").strip()
    if not _is_valid_username(cleaned):
        return None
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT id, full_name, email FROM users WHERE lower(username) = lower(?) LIMIT 1",
        (cleaned,),
    ).fetchone()
    conn.close()
    return row


def is_owner(viewer_id: int | None, profile_user_id: int | None) -> bool:
    return bool(viewer_id and profile_user_id and int(viewer_id) == int(profile_user_id))


def is_blocked(viewer_id: int | None, profile_user_id: int | None) -> bool:
    if not viewer_id or not profile_user_id:
        return False
    a = int(viewer_id)
    b = int(profile_user_id)
    if a == b:
        return False
    conn = _get_main_conn()
    row = conn.execute(
        """
        SELECT 1
          FROM blocks
         WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)
         LIMIT 1
        """,
        (a, b, b, a),
    ).fetchone()
    if not row:
        row = conn.execute(
            """
            SELECT 1
              FROM user_blocks
             WHERE (user_id = ? AND blocked_user_id = ?) OR (user_id = ? AND blocked_user_id = ?)
             LIMIT 1
            """,
            (a, b, b, a),
        ).fetchone()
    conn.close()
    return bool(row)


def follow_status(viewer_id: int | None, profile_user_id: int | None) -> str:
    if not viewer_id or not profile_user_id:
        return "none"
    if int(viewer_id) == int(profile_user_id):
        return "self"
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT status FROM follows WHERE follower_id = ? AND followed_id = ? LIMIT 1",
        (int(viewer_id), int(profile_user_id)),
    ).fetchone()
    conn.close()
    return (row["status"] if row else "none") or "none"


def _is_private_profile(profile_user_id: int | None) -> bool:
    if not profile_user_id:
        return True
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT is_private FROM users WHERE id = ? LIMIT 1",
        (int(profile_user_id),),
    ).fetchone()
    conn.close()
    return bool(int(row["is_private"] or 0)) if row else True


def can_view_profile(viewer_id: int | None, profile_user_id: int | None, is_private_profile: bool | int) -> bool:
    if not viewer_id or not profile_user_id:
        return False
    v = int(viewer_id)
    p = int(profile_user_id)
    if v == p:
        return True
    if is_blocked(v, p):
        return False
    if not bool(is_private_profile):
        return True
    return follow_status(v, p) == "accepted"


def _social_action_allowed(actor_id: int, action: str, target_id: int | None, cooldown_seconds: int = 15) -> tuple[bool, int]:
    now = datetime.utcnow()
    conn = _get_main_conn()
    row = conn.execute(
        """
        SELECT created_at
          FROM social_actions
         WHERE actor_id = ? AND action = ? AND COALESCE(target_id, -1) = COALESCE(?, -1)
         ORDER BY id DESC
         LIMIT 1
        """,
        (int(actor_id), action, int(target_id) if target_id is not None else None),
    ).fetchone()
    if row and row["created_at"]:
        try:
            then = datetime.fromisoformat(str(row["created_at"]))
            elapsed = (now - then).total_seconds()
            if elapsed < cooldown_seconds:
                conn.close()
                return False, int(cooldown_seconds - elapsed)
        except Exception:
            pass
    conn.execute(
        "INSERT INTO social_actions (actor_id, action, target_id, created_at) VALUES (?, ?, ?, ?)",
        (int(actor_id), action, int(target_id) if target_id is not None else None, now.isoformat()),
    )
    conn.commit()
    conn.close()
    return True, 0


def _protected_media_url(media_id, fallback_path: str | None = None) -> str:
    mid = _coerce_int(media_id)
    if mid:
        return f"/media/{mid}"
    return (fallback_path or "")


def _list_clubs(search_text: str = "", limit: int = 80) -> list[dict]:
    safe_limit = max(1, min(int(limit or 80), 200))
    query = (search_text or "").strip().lower()
    conn = _get_main_conn()
    cur = conn.cursor()
    if query:
        wildcard = f"%{query}%"
        rows = cur.execute(
            """
            SELECT c.id, c.name, c.description, c.category, c.banner_path, c.created_at,
                   (SELECT COUNT(*) FROM club_memberships cm WHERE cm.club_id = c.id) AS member_count
            FROM clubs c
            WHERE lower(c.name) LIKE ? OR lower(COALESCE(c.description, '')) LIKE ? OR lower(COALESCE(c.category, '')) LIKE ?
            ORDER BY c.id DESC
            LIMIT ?
            """,
            (wildcard, wildcard, wildcard, safe_limit),
        ).fetchall()
    else:
        rows = cur.execute(
            """
            SELECT c.id, c.name, c.description, c.category, c.banner_path, c.created_at,
                   (SELECT COUNT(*) FROM club_memberships cm WHERE cm.club_id = c.id) AS member_count
            FROM clubs c
            ORDER BY c.id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _list_user_joined_clubs(user_id: int) -> list[dict]:
    conn = _get_main_conn()
    rows = conn.execute(
        """
        SELECT c.id, c.name, c.description, c.category, c.banner_path, cm.joined_at
        FROM club_memberships cm
        JOIN clubs c ON c.id = cm.club_id
        WHERE cm.user_id = ?
        ORDER BY cm.joined_at DESC, c.name ASC
        """,
        (int(user_id),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _is_club_member(user_id: int, club_id: int) -> bool:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT 1 FROM club_memberships WHERE user_id = ? AND club_id = ? LIMIT 1",
        (int(user_id), int(club_id)),
    ).fetchone()
    conn.close()
    return bool(row)


def _club_upcoming_sessions(club_id: int) -> list[dict]:
    templates = [
        {"title": "Welcome Circle", "days": 2, "time": "6:30 PM", "place": "Community Hub Room A"},
        {"title": "Skill Exchange Meetup", "days": 5, "time": "10:00 AM", "place": "Library Learning Pod"},
        {"title": "Weekend Social", "days": 9, "time": "4:00 PM", "place": "Neighbourhood Pavilion"},
        {"title": "Support Check-In", "days": 12, "time": "7:00 PM", "place": "Online Video Room"},
        {"title": "Interest Workshop", "days": 15, "time": "2:00 PM", "place": "Community Club Studio"},
    ]
    offset = int(club_id) % len(templates)
    now = datetime.utcnow()
    sessions = []
    for i in range(3):
        base = templates[(offset + i) % len(templates)]
        dt = now + timedelta(days=base["days"] + i)
        sessions.append(
            {
                "title": base["title"],
                "when": dt.strftime("%a, %d %b %Y"),
                "time": base["time"],
                "location": base["place"],
            }
        )
    return sessions


def _deterministic_placeholder_scrapbook(profile_user_id: int, username: str) -> list[dict]:
    seed = int(hashlib.sha256(f"{int(profile_user_id)}:{username}".encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    titles = [
        "Morning Reflection",
        "Community Catch-up",
        "Small Win This Week",
        "Learning Note",
        "Neighbourhood Moment",
        "Kindness Highlight",
    ]
    captions = [
        "A calm session and meaningful conversations made the day lighter.",
        "Shared stories and practical tips with friends from the community.",
        "Tried something new and felt more confident after practice.",
        "Documented progress from a skill-building session.",
        "Enjoyed a familiar corner in the neighbourhood and took notes.",
        "A short meetup that ended with good energy and new ideas.",
    ]
    emojis = ["🌿", "📘", "🤝", "☀️", "💬", "🎨"]
    count = 3 + (seed % 4)
    items = []
    for idx in range(count):
        title = titles[(idx + rng.randint(0, len(titles) - 1)) % len(titles)]
        caption = captions[(idx + rng.randint(0, len(captions) - 1)) % len(captions)]
        emoji = emojis[(idx + rng.randint(0, len(emojis) - 1)) % len(emojis)]
        stamp = datetime(2025, 1, 1) + timedelta(days=((seed + idx * 11) % 360))
        items.append(
            {
                "id": -((int(profile_user_id) * 100) + idx + 1),
                "entry_type": "memory",
                "title": f"{emoji} {title}",
                "content": caption,
                "visibility": "community",
                "featured": False,
                "campaign_tag": "",
                "created_at": stamp.isoformat(),
                "related_user_id": None,
                "circle_title": "",
                "mood_tag": "",
                "location": "",
                "pinned": 0,
                "media_url": "",
            }
        )
    return items


def _get_user_settings_map(user_id: int) -> dict:
    try:
        settings = UserSetting.query.filter_by(user_id=user_id).all()
        return {s.key: s.value for s in settings}
    except DatabaseError:
        db.session.rollback()
        return {}


def _set_user_setting(user_id: int, key: str, value: str) -> None:
    try:
        setting = UserSetting.query.filter_by(user_id=user_id, key=key).first()
        if setting is None:
            setting = UserSetting(user_id=user_id, key=key, value=value)
            db.session.add(setting)
        else:
            setting.value = value
    except DatabaseError:
        db.session.rollback()


def _safe_json(value: str, default):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _normalize_station_list(stations) -> list[str]:
    cleaned = []
    seen = set()
    for item in stations or []:
        name = str(item or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
    return cleaned


def _extract_stations(onboarding: dict, location_name: str) -> list[str]:
    from_onboarding = onboarding.get("stations") if isinstance(onboarding, dict) else []
    if isinstance(from_onboarding, list) and from_onboarding:
        return _normalize_station_list(from_onboarding)
    fallback = []
    for token in (location_name or "").split(","):
        t = token.strip()
        if t:
            fallback.append(t)
    return _normalize_station_list(fallback)


MRT_LINES_FOR_MIDPOINT = [
    ["Admiralty", "Ang Mo Kio", "Bishan", "Braddell", "Bukit Batok", "Bukit Gombak", "Canberra", "Choa Chu Kang", "City Hall", "Dhoby Ghaut", "Jurong East", "Khatib", "Kranji", "Marina Bay", "Marina South Pier", "Novena", "Orchard", "Raffles Place", "Sembawang", "Somerset", "Toa Payoh", "Woodlands", "Yew Tee", "Yio Chu Kang", "Yishun"],
    ["Aljunied", "Bedok", "Boon Lay", "Bugis", "Buona Vista", "Changi Airport", "Chinese Garden", "City Hall", "Clementi", "Commonwealth", "Dover", "Eunos", "Expo", "Gul Circle", "Joo Koon", "Jurong East", "Kallang", "Kembangan", "Lakeside", "Lavender", "Outram Park", "Pasir Ris", "Paya Lebar", "Pioneer", "Queenstown", "Raffles Place", "Redhill", "Simei", "Tanah Merah", "Tanjong Pagar", "Tiong Bahru", "Tuas Crescent", "Tuas Link", "Tuas West Road"],
    ["Bayfront", "Beauty World", "Bedok North", "Bedok Reservoir", "Bencoolen", "Bendemeer", "Botanic Gardens", "Bugis", "Bukit Panjang", "Cashew", "Chinatown", "Downtown", "Expo", "Fort Canning", "Geylang Bahru", "Hillview", "Jalan Besar", "Kaki Bukit", "King Albert Park", "Little India", "MacPherson", "Mattar", "Promenade", "Rochor", "Sixth Avenue", "Stevens", "Tan Kah Kee", "Telok Ayer", "Tampines", "Tampines East", "Tampines West", "Ubi", "Upper Changi"],
    ["Boon Keng", "Buangkok", "Chinatown", "Clarke Quay", "Dhoby Ghaut", "Farrer Park", "HarbourFront", "Hougang", "Kovan", "Little India", "Outram Park", "Potong Pasir", "Punggol", "Sengkang", "Serangoon", "Woodleigh"],
    ["Bartley", "Bayfront", "Botanic Gardens", "Bras Basah", "Buona Vista", "Caldecott", "Dakota", "Dhoby Ghaut", "Farrer Road", "HarbourFront", "Haw Par Villa", "Holland Village", "Kent Ridge", "Labrador Park", "Lorong Chuan", "MacPherson", "Marina Bay", "Marymount", "Mountbatten", "Nicoll Highway", "one-north", "Pasir Panjang", "Promenade", "Serangoon", "Stadium", "Tai Seng"],
    ["Bright Hill", "Caldecott", "Gardens by the Bay", "Great World", "Havelock", "Lentor", "Marine Parade", "Marine Terrace", "Maxwell", "Mayflower", "Napier", "Orchard Boulevard", "Outram Park", "Shenton Way", "Siglap", "Springleaf", "Stevens", "Tanjong Katong", "Tanjong Rhu", "Upper Thomson", "Woodlands North", "Woodlands South"],
]

_MRT_GRAPH: dict[str, set[str]] | None = None
_MRT_CANON: dict[str, str] | None = None


def _build_mrt_graph() -> tuple[dict[str, set[str]], dict[str, str]]:
    global _MRT_GRAPH, _MRT_CANON
    if _MRT_GRAPH is not None and _MRT_CANON is not None:
        return _MRT_GRAPH, _MRT_CANON

    graph: dict[str, set[str]] = {}
    canon: dict[str, str] = {}
    for line in MRT_LINES_FOR_MIDPOINT:
        for idx, station in enumerate(line):
            key = station.casefold()
            canon.setdefault(key, station)
            graph.setdefault(key, set())
            if idx > 0:
                prev_key = line[idx - 1].casefold()
                graph.setdefault(prev_key, set())
                graph[key].add(prev_key)
                graph[prev_key].add(key)
    _MRT_GRAPH = graph
    _MRT_CANON = canon
    return graph, canon


def _shortest_station_hops(graph: dict[str, set[str]], start: str, end: str) -> int | None:
    if start == end:
        return 0
    if start not in graph or end not in graph:
        return None
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        node, dist = queue.popleft()
        for nb in graph.get(node, set()):
            if nb == end:
                return dist + 1
            if nb in seen:
                continue
            seen.add(nb)
            queue.append((nb, dist + 1))
    return None


def _pick_midpoint_station(viewer_stations: list[str], friend_stations: list[str]) -> str:
    viewer = _normalize_station_list(viewer_stations)
    friend = _normalize_station_list(friend_stations)
    if not viewer or not friend:
        return ""
    graph, canon = _build_mrt_graph()
    viewer_keys = [s.casefold() for s in viewer if s.casefold() in canon]
    friend_keys = [s.casefold() for s in friend if s.casefold() in canon]
    if not viewer_keys or not friend_keys:
        return friend[0]

    viewer_set = set(viewer_keys)
    for station in friend_keys:
        if station in viewer_set:
            return canon.get(station, friend[0])

    def closest_distance(candidate: str, sources: list[str]) -> int | None:
        distances = [_shortest_station_hops(graph, source, candidate) for source in sources]
        reachable = [d for d in distances if d is not None]
        return min(reachable) if reachable else None

    best_station = None
    best_score = None
    for candidate in graph.keys():
        dv = closest_distance(candidate, viewer_keys)
        df = closest_distance(candidate, friend_keys)
        if dv is None or df is None:
            continue
        score = (abs(dv - df), dv + df, max(dv, df), candidate)
        if best_score is None or score < best_score:
            best_score = score
            best_station = candidate

    if best_station:
        return canon.get(best_station, friend[0])
    return friend[0]


def _safe_locations_for_stations(stations: list[str], limit: int = 4) -> list[dict]:
    cleaned = _normalize_station_list(stations)
    if not cleaned:
        return []
    placeholders = ",".join(["?"] * len(cleaned))
    conn = _get_main_conn()
    rows = conn.execute(
        f"""
        SELECT place_name, venue_type, address, lat, lng, station_name, walking_mins
          FROM safe_locations
         WHERE station_name IN ({placeholders})
         ORDER BY station_name, walking_mins ASC, place_name ASC
         LIMIT ?
        """,
        tuple(cleaned + [max(1, int(limit))]),
    ).fetchall()
    conn.close()
    return [
        {
            "place_name": row["place_name"],
            "venue_type": row["venue_type"],
            "address": row["address"] or "",
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "station_name": row["station_name"],
            "walking_mins": row["walking_mins"],
        }
        for row in rows
    ]


ALLOWED_PROFILE_LANGUAGES = [
    "English",
    "Chinese (Mandarin)",
    "Malay",
    "Tamil",
    "Hokkien",
]


def _load_user_languages(user_id: int) -> list[str]:
    user_settings = _get_user_settings_map(user_id)
    parsed = _safe_json(user_settings.get("languages", "[]") or "[]", [])
    if not isinstance(parsed, list):
        return []
    allowed = set(ALLOWED_PROFILE_LANGUAGES)
    cleaned = []
    for language in parsed:
        value = str(language).strip()
        if value and value in allowed and value not in cleaned:
            cleaned.append(value)
    return cleaned


def _save_user_languages(user_id: int, selected_languages: list[str]) -> list[str]:
    allowed = set(ALLOWED_PROFILE_LANGUAGES)
    cleaned = []
    for language in selected_languages or []:
        value = str(language).strip()
        if value and value in allowed and value not in cleaned:
            cleaned.append(value)
    _set_user_setting(user_id, "languages", json.dumps(cleaned))
    return cleaned


def _time_bucket_now() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _availability_label(onboarding: dict) -> str:
    day_map = {
        0: "monday",
        1: "tuesday",
        2: "wednesday",
        3: "thursday",
        4: "friday",
        5: "saturday",
        6: "sunday",
    }
    days = [str(d).strip().lower() for d in (onboarding.get("days") or []) if str(d).strip()]
    times = [str(t).strip().lower() for t in (onboarding.get("time") or []) if str(t).strip()]
    if not days or not times:
        return "Availability not set"
    today = day_map.get(datetime.now().weekday(), "")
    now_bucket = _time_bucket_now()
    if today in days and now_bucket in times:
        return "Available now"
    labels = {"morning": "Morning", "afternoon": "Afternoon", "evening": "Evening"}
    next_slot = labels.get(times[0], times[0].capitalize() if times else "Soon")
    return f"Usually available {next_slot}"


def _build_match_profile(
    user: User,
    settings_map: dict,
    viewer_interests: list,
    viewer_skills_teach: list,
    viewer_skills_learn: list,
) -> dict:
    onboarding = _safe_json(settings_map.get("onboarding", "{}"), {})
    interests = onboarding.get("interests") or []
    skills_teach = onboarding.get("skills_teach") or _safe_json(settings_map.get("skills_teach", "[]"), [])
    skills_learn = onboarding.get("skills_learn") or _safe_json(settings_map.get("skills_learn", "[]"), [])
    stations = onboarding.get("stations") or []
    member_type = (user.member_type or onboarding.get("memberType") or "youth").strip().lower()
    privacy = _safe_json(settings_map.get("privacy", "{}"), {})
    show_age = privacy.get("show_age", True)
    show_location = privacy.get("show_location", True)
    allow_direct = privacy.get("allow_direct", True)

    name = user.full_name or "User"
    avatar_url = settings_map.get("avatar_url") or f"https://api.dicebear.com/7.x/avataaars/svg?seed={name}"
    location_name = settings_map.get("location_name", "")
    location = stations[0] if stations else (location_name.split(",")[0].strip() if location_name else "")

    viewer_i = {str(i).strip().casefold() for i in (viewer_interests or []) if str(i).strip()}
    viewer_teach = {str(i).strip().casefold() for i in (viewer_skills_teach or []) if str(i).strip()}
    viewer_learn = {str(i).strip().casefold() for i in (viewer_skills_learn or []) if str(i).strip()}
    cand_i = {str(i).strip().casefold() for i in interests if str(i).strip()}
    cand_teach = {str(i).strip().casefold() for i in skills_teach if str(i).strip()}
    cand_learn = {str(i).strip().casefold() for i in skills_learn if str(i).strip()}

    common_interests = sorted(viewer_i.intersection(cand_i))
    teach_to_viewer = viewer_learn.intersection(cand_teach)
    learn_from_viewer = viewer_teach.intersection(cand_learn)
    skill_match_count = len(teach_to_viewer) + len(learn_from_viewer)

    interests_component = min(15, len(common_interests) * 5)
    skills_component = min(35, skill_match_count * 18)
    match_score = max(40, min(98, 45 + interests_component + skills_component))
    if member_type == "senior":
        age = 65 + (user.id % 12)
    else:
        age = 20 + (user.id % 12)

    matched_tags = [x.title() for x in common_interests[:2]]
    matched_tags.extend([str(x) for x in list(teach_to_viewer)[:1]])
    if not matched_tags:
        matched_tags = [str(i) for i in (interests[:3] or ["Friendly", "Community-minded", "Open learner"])]
    if member_type == "senior":
        bio = "Enjoys community activities and sharing stories."
    else:
        bio = "Keen to connect with seniors and build community."

    return {
        "id": f"user-{user.id}",
        "user_id": user.id,
        "name": name,
        "age": age if show_age else None,
        "avatar": avatar_url,
        "location": location if show_location else "",
        "match": f"{match_score}%",
        "bio": bio,
        "matched": matched_tags,
        "interests": interests or ["Community", "Learning", "Sharing"],
        "teach": (skills_teach or [])[:4],
        "learn": (skills_learn or [])[:4],
        "days": onboarding.get("days") or [],
        "time": onboarding.get("time") or [],
        "availability": _availability_label(onboarding),
        "stations": stations,
        "allow_direct": bool(allow_direct),
        "is_real": True,
    }


def _match_card_for_user(user: User) -> dict:
    settings_map = _get_user_settings_map(user.id)
    onboarding = _safe_json(settings_map.get("onboarding", "{}"), {})
    stations = onboarding.get("stations") or []
    location_name = settings_map.get("location_name", "")
    location = stations[0] if stations else (location_name.split(",")[0].strip() if location_name else "")
    avatar_url = settings_map.get("avatar_url") or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.full_name}"
    return {"name": user.full_name, "avatar": avatar_url, "location": location}


def _ensure_match_row(conn, user_id: int, other_user: User) -> None:
    match_key = f"{user_id}:user-{other_user.id}"
    existing = conn.execute(
        "SELECT 1 FROM matches WHERE match_id = ? AND user_id = ?",
        (match_key, user_id),
    ).fetchone()
    if existing:
        return
    meta = _match_card_for_user(other_user)
    conn.execute(
        "INSERT INTO matches (user_id, match_id, name, avatar, location, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, match_key, meta["name"], meta["avatar"], meta["location"], _utc_now_iso()),
    )

def _require_admin():
    return bool(session.get("is_admin"))


def _render_profile_page(viewer_user_id: int, target_user_id: int):
    u = db.session.get(User, int(target_user_id))
    if not u:
        return ("User not found", 404)

    identity = _get_user_identity(int(target_user_id))
    profile_username = identity.get("username") or _username_slug(u.full_name or f"user_{u.id}", u.id)
    private_flag = bool(int(identity.get("is_private", 0)))
    owner_flag = is_owner(viewer_user_id, target_user_id)
    blocked_flag = is_blocked(viewer_user_id, target_user_id)
    follow_state = follow_status(viewer_user_id, target_user_id)
    can_view_flag = can_view_profile(viewer_user_id, target_user_id, private_flag)

    if blocked_flag and not owner_flag:
        return ("Not found", 404)

    user_settings = _get_user_settings_map(target_user_id)
    onboarding = json.loads(user_settings.get("onboarding", "{}"))
    avatar_config = _safe_json(user_settings.get("avatar_config", "{}"), {})
    avatar_background = str(avatar_config.get("background", "") or "").strip()
    avatar_background_map = {
        "Peach": "#fff3e6",
        "Mint": "#e6fff7",
        "Sky": "#eef4ff",
        "Studio": "#fff7ed",
        "Park": "#fef3c7",
        "None": "#f8fafc",
    }
    profile_theme_bg = avatar_background_map.get(avatar_background, "#f8fafc")
    user_languages = _load_user_languages(target_user_id)
    avatar_url = user_settings.get("avatar_url", "")
    banner_url = user_settings.get("banner_url", "")
    location_name = user_settings.get("location_name", "")
    verified_with = user_settings.get("verified_with", "")

    conn = _get_chat_conn()
    connections_count = conn.execute(
        "SELECT COUNT(*) AS c FROM matches WHERE user_id = ?", (target_user_id,)
    ).fetchone()["c"]
    conn.close()

    conn = _get_main_conn()
    memories_count = conn.execute(
        "SELECT COUNT(*) AS c FROM challenge_entries WHERE user_id = ?", (target_user_id,)
    ).fetchone()["c"]
    badges_count = conn.execute(
        "SELECT COUNT(*) AS c FROM user_badges WHERE user_id = ? AND earned = 1",
        (target_user_id,),
    ).fetchone()["c"]
    conn.close()

    repoints_count, _ = _get_user_points(target_user_id)
    circles_count = CircleSignup.query.filter_by(user_id=target_user_id).count()
    clubs_joined = _list_user_joined_clubs(int(target_user_id))
    titles_payload = _profile_titles_payload(target_user_id)
    verification_badges = _get_user_verification_badges(target_user_id)
    google_maps_key = _google_maps_key()
    meetup_midpoint_station = ""
    meetup_safe_locations = []
    is_friend_view = not owner_flag
    if is_friend_view and can_view_flag:
        viewer_settings = _get_user_settings_map(viewer_user_id)
        viewer_onboarding = _safe_json(viewer_settings.get("onboarding", "{}"), {})
        viewer_stations = _extract_stations(viewer_onboarding, viewer_settings.get("location_name", ""))
        friend_stations = _extract_stations(onboarding, location_name)
        meetup_midpoint_station = _pick_midpoint_station(viewer_stations, friend_stations)
        if meetup_midpoint_station:
            meetup_safe_locations = _safe_locations_for_stations([meetup_midpoint_station], limit=5)

    member_label = "Senior" if (u.member_type or "").strip().lower() in ("senior", "elderly") else "Youth"
    return render_template(
        "profile.html",
        user=u,
        onboarding=onboarding,
        profile_theme_bg=profile_theme_bg,
        user_languages=user_languages,
        avatar_url=avatar_url,
        banner_url=banner_url,
        location_name=location_name,
        verified_with=verified_with,
        connections_count=connections_count,
        memories_count=memories_count,
        repoints_count=repoints_count,
        circles_count=circles_count,
        clubs_joined=clubs_joined,
        badges_count=badges_count,
        total_volunteer_hours=float(getattr(u, "total_volunteer_hours", 0) or 0),
        equipped_title=titles_payload.get("equipped"),
        verification_badges=verification_badges,
        member_label=member_label,
        google_maps_key=google_maps_key,
        is_friend_view=is_friend_view,
        viewer_user_id=viewer_user_id,
        meetup_midpoint_station=meetup_midpoint_station,
        meetup_safe_locations=meetup_safe_locations,
        is_owner=owner_flag,
        is_private=private_flag,
        can_view=can_view_flag,
        follow_status=follow_state,
        is_blocked=blocked_flag,
        profile_username=profile_username,
    )


@app.get("/profile/<username>")
@login_required
def profile_by_username(username: str):
    row = _get_user_by_username(username)
    if not row:
        return ("Not found", 404)
    return _render_profile_page(int(g.current_user_id), int(row["id"]))


@app.get("/u/<int:target_user_id>")
@login_required
def profile_by_id(target_user_id: int):
    return _render_profile_page(int(g.current_user_id), int(target_user_id))


def _generate_2fa_code() -> str:
    return f"{random.randint(0, 999999):06d}"


OTP_CODE_MINUTES = 2


def _send_2fa_email(to_email: str, code: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int((os.getenv("SMTP_PORT", "587") or "587").strip())
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    from_email = os.getenv("SMTP_FROM", smtp_user or "no-reply@reconnect.local")
    use_tls = (os.getenv("SMTP_USE_TLS", "1") or "1").strip() == "1"

    if not smtp_host:
        print(f"[2FA DEV] email={to_email} code={code}")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Your Re:Connect verification code"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(
        "Your login verification code is: "
        + code
        + "\n\nThis code expires in 10 minutes.\nIf you did not request this, ignore this email."
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if smtp_user:
            smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)
    return True


def _send_verification_email(to_email: str, code: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int((os.getenv("SMTP_PORT", "587") or "587").strip())
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    from_email = os.getenv("SMTP_FROM", smtp_user or "no-reply@reconnect.local")
    use_tls = (os.getenv("SMTP_USE_TLS", "1") or "1").strip() == "1"

    if not smtp_host:
        print(f"[VERIFY EMAIL DEV] email={to_email} code={code}")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Your Re:Connect profile verification code"
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(
        "Your profile verification code is: "
        + code
        + "\n\nThis code expires in 10 minutes.\nIf you did not request this, ignore this email."
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls()
        if smtp_user:
            smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)
    return True


def _send_verification_sms(phone_e164: str, code: str) -> bool:
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio_from = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    if not twilio_sid or not twilio_token or not twilio_from:
        print(f"[VERIFY PHONE DEV] phone={phone_e164} code={code}")
        return False

    body = f"Your Re:Connect verification code is {code}. Expires in 10 minutes."
    url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
    payload = urllib.parse.urlencode({"To": phone_e164, "From": twilio_from, "Body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    token = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15):
        pass
    return True


def _twilio_verify_send_code(phone_e164: str) -> tuple[bool, str]:
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    verify_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID", "").strip()
    if not twilio_sid or not twilio_token or not verify_sid:
        return False, "Twilio Verify is not configured"

    url = f"https://verify.twilio.com/v2/Services/{verify_sid}/Verifications"
    payload = urllib.parse.urlencode({"To": phone_e164, "Channel": "sms"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    token = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "ignore")
            out = json.loads(body or "{}")
            status = str(out.get("status") or "").strip().lower()
            return status in {"pending", "sent"}, ""
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "ignore")
            msg = json.loads(detail).get("message") or detail
        except Exception:
            msg = str(e)
        return False, f"Twilio Verify send failed: {msg}"
    except Exception as e:
        return False, f"Twilio Verify send failed: {e}"


def _twilio_verify_check_code(phone_e164: str, code: str) -> tuple[bool, str]:
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    verify_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID", "").strip()
    if not twilio_sid or not twilio_token or not verify_sid:
        return False, "Twilio Verify is not configured"

    url = f"https://verify.twilio.com/v2/Services/{verify_sid}/VerificationCheck"
    payload = urllib.parse.urlencode({"To": phone_e164, "Code": code}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    token = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "ignore")
            out = json.loads(body or "{}")
            status = str(out.get("status") or "").strip().lower()
            return status == "approved", ""
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "ignore")
            msg = json.loads(detail).get("message") or detail
        except Exception:
            msg = str(e)
        return False, f"Twilio Verify check failed: {msg}"
    except Exception as e:
        return False, f"Twilio Verify check failed: {e}"


def _set_pending_contact_verification(channel: str, target: str, code: str) -> None:
    session[f"pending_verify_{channel}_target"] = target
    session[f"pending_verify_{channel}_code_sha256"] = hashlib.sha256(code.encode("utf-8")).hexdigest()
    session[f"pending_verify_{channel}_expires_at"] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()


def _clear_pending_contact_verification(channel: str) -> None:
    session.pop(f"pending_verify_{channel}_target", None)
    session.pop(f"pending_verify_{channel}_code_sha256", None)
    session.pop(f"pending_verify_{channel}_expires_at", None)
    session.pop(f"pending_verify_{channel}_mode", None)


def _normalize_phone_e164(country_code: str, phone_number: str) -> str:
    cc_digits = re.sub(r"\D", "", country_code or "")
    pn_digits = re.sub(r"\D", "", phone_number or "")
    if not cc_digits or not pn_digits:
        return ""
    combined = f"+{cc_digits}{pn_digits}"
    if len(combined) < 8 or len(combined) > 18:
        return ""
    return combined


def _set_pending_2fa(user: User, code: str, delivery: str = "email", dev_code: str = "") -> None:
    session["pending_2fa_user_id"] = user.id
    session["pending_2fa_email"] = user.email
    session["pending_2fa_code_sha256"] = hashlib.sha256(code.encode("utf-8")).hexdigest()
    session["pending_2fa_expires_at"] = (datetime.utcnow() + timedelta(minutes=OTP_CODE_MINUTES)).isoformat()
    session["pending_2fa_delivery"] = delivery
    if dev_code:
        session["pending_2fa_dev_code"] = dev_code
    else:
        session.pop("pending_2fa_dev_code", None)


def _clear_pending_2fa() -> None:
    session.pop("pending_2fa_user_id", None)
    session.pop("pending_2fa_email", None)
    session.pop("pending_2fa_code_sha256", None)
    session.pop("pending_2fa_expires_at", None)
    session.pop("pending_2fa_delivery", None)
    session.pop("pending_2fa_dev_code", None)


def _set_pending_signup(full_name: str, email: str, password_hash: str, code: str) -> None:
    session["pending_signup_full_name"] = full_name
    session["pending_signup_email"] = email
    session["pending_signup_password_hash"] = password_hash
    session["pending_signup_code_sha256"] = hashlib.sha256(code.encode("utf-8")).hexdigest()
    session["pending_signup_expires_at"] = (datetime.utcnow() + timedelta(minutes=OTP_CODE_MINUTES)).isoformat()


def _seconds_until_iso(iso_text: str | None) -> int:
    if not iso_text:
        return 0
    try:
        dt = datetime.fromisoformat(str(iso_text))
    except Exception:
        return 0
    return max(0, int((dt - datetime.utcnow()).total_seconds()))


def _clear_pending_signup() -> None:
    session.pop("pending_signup_full_name", None)
    session.pop("pending_signup_email", None)
    session.pop("pending_signup_password_hash", None)
    session.pop("pending_signup_code_sha256", None)
    session.pop("pending_signup_expires_at", None)
    session.pop("pending_signup_delivery", None)
    session.pop("pending_signup_dev_code", None)


def _validate_signup_payload(full_name: str, email: str, password: str) -> str | None:
    if not full_name or not email or not password:
        return "Missing required fields"
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not (
        any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
        and any(not c.isalnum() for c in password)
    ):
        return "Password must include uppercase, lowercase, number, and symbol"
    at_index = email.find("@")
    dot_after_at = email.find(".", at_index + 1) if at_index != -1 else -1
    if at_index <= 0 or dot_after_at == -1:
        return "Email must be an email address"
    if User.query.filter_by(email=email).first():
        return "Email already exists"
    return None


def _finalize_pending_signup() -> tuple[User | None, str | None]:
    full_name = (session.get("pending_signup_full_name") or "").strip()
    email = (session.get("pending_signup_email") or "").strip().lower()
    password_hash = (session.get("pending_signup_password_hash") or "").strip()
    if not full_name or not email or not password_hash:
        _clear_pending_signup()
        return None, "No pending signup verification"
    if User.query.filter_by(email=email).first():
        _clear_pending_signup()
        return None, "Email already exists"

    u = User(full_name=full_name, email=email)
    # Directly set the hash because the password was already validated and hashed before OTP.
    u.password_hash = password_hash
    db.session.add(u)
    db.session.commit()

    conn = _get_main_conn()
    uname = _username_slug(full_name or email or f"user_{u.id}", u.id)
    conn.execute("UPDATE users SET username = COALESCE(NULLIF(username, ''), ?) WHERE id = ?", (uname, u.id))
    conn.commit()
    conn.close()
    _ensure_ach_user(u)

    db.session.add(
        AuthEvent(
            user_id=u.id,
            event_type="signup",
            email=u.email,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
    )
    db.session.commit()

    session["user_id"] = u.id
    _log_audit("auth", "signup", u.id, {"email": u.email, "method": "email_otp"})
    _clear_pending_signup()
    return u, None

#Create Account
@app.post("/api/signup")
def api_signup():
    data = request.get_json(silent=True) or request.form

    full_name = (data.get("fullname") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    validation_error = _validate_signup_payload(full_name, email, password)
    if validation_error:
        status = 409 if validation_error == "Email already exists" else 400
        return jsonify({"ok": False, "error": validation_error}), status

    code = _generate_2fa_code()
    _set_pending_signup(full_name, email, generate_password_hash(password), code)
    delivered = False
    try:
        delivered = _send_2fa_email(email, code)
    except Exception:
        delivered = False
    session["pending_signup_delivery"] = "email" if delivered else "dev"
    if delivered:
        session.pop("pending_signup_dev_code", None)
    else:
        session["pending_signup_dev_code"] = code

    return jsonify(
        {
            "ok": True,
            "requires_2fa": True,
            "delivery": "email" if delivered else "dev",
            "dev_code": code if not delivered else None,
            "next": "/signup-2fa",
        }
    )


@app.post("/signup")
def signup():
    full_name = (request.form.get("fullname") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    validation_error = _validate_signup_payload(full_name, email, password)
    if validation_error:
        return render_template("signup.html", error=validation_error, full_name=full_name, email=email)

    code = _generate_2fa_code()
    _set_pending_signup(full_name, email, generate_password_hash(password), code)
    delivered = False
    try:
        delivered = _send_2fa_email(email, code)
    except Exception:
        delivered = False
    session["pending_signup_delivery"] = "email" if delivered else "dev"
    if delivered:
        session.pop("pending_signup_dev_code", None)
    else:
        session["pending_signup_dev_code"] = code
    return redirect("/signup-2fa")


@app.post("/api/signup/2fa/verify")
def api_signup_2fa_verify():
    pending_hash = session.get("pending_signup_code_sha256")
    pending_expires = session.get("pending_signup_expires_at")
    if not pending_hash or not pending_expires:
        return jsonify({"ok": False, "error": "No pending signup verification"}), 400

    try:
        expires_at = datetime.fromisoformat(pending_expires)
    except Exception:
        _clear_pending_signup()
        return jsonify({"ok": False, "error": "Verification expired"}), 400
    if datetime.utcnow() > expires_at:
        _clear_pending_signup()
        return jsonify({"ok": False, "error": "Verification code expired"}), 400

    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if len(code) != 6 or not code.isdigit():
        return jsonify({"ok": False, "error": "Enter a valid 6-digit code"}), 400
    if hashlib.sha256(code.encode("utf-8")).hexdigest() != pending_hash:
        return jsonify({"ok": False, "error": "Incorrect verification code"}), 400

    user, error = _finalize_pending_signup()
    if error:
        status = 409 if error == "Email already exists" else 400
        return jsonify({"ok": False, "error": error}), status
    return jsonify({"ok": True, "next": "/signup-avatar", "user_id": user.id})


@app.post("/api/signup/2fa/resend")
def api_signup_2fa_resend():
    full_name = (session.get("pending_signup_full_name") or "").strip()
    email = (session.get("pending_signup_email") or "").strip().lower()
    password_hash = (session.get("pending_signup_password_hash") or "").strip()
    if not full_name or not email or not password_hash:
        _clear_pending_signup()
        return jsonify({"ok": False, "error": "No pending signup verification"}), 400
    if User.query.filter_by(email=email).first():
        _clear_pending_signup()
        return jsonify({"ok": False, "error": "Email already exists"}), 409
    retry_after = _seconds_until_iso(session.get("pending_signup_expires_at"))
    if retry_after > 0:
        return jsonify({"ok": False, "error": f"You can resend in {retry_after}s", "retry_after": retry_after}), 429

    code = _generate_2fa_code()
    _set_pending_signup(full_name, email, password_hash, code)
    delivered = False
    try:
        delivered = _send_2fa_email(email, code)
    except Exception:
        delivered = False
    session["pending_signup_delivery"] = "email" if delivered else "dev"
    if delivered:
        session.pop("pending_signup_dev_code", None)
    else:
        session["pending_signup_dev_code"] = code
    return jsonify(
        {
            "ok": True,
            "delivery": "email" if delivered else "dev",
            "dev_code": code if not delivered else None,
            "email": email,
            "retry_after": OTP_CODE_MINUTES * 60,
        }
    )


@app.get("/signup-avatar")
def signup_avatar_page():
    user_id = _require_login()
    if not user_id:
        return redirect("/signup")

    settings = _get_user_settings_map(user_id)
    avatar_config = json.loads(settings.get("avatar_config", "{}") or "{}")
    avatar_url = settings.get("avatar_url", "")
    return render_template("signup_avatar.html", avatar_config=avatar_config, avatar_url=avatar_url)


@app.post("/signup-avatar")
def signup_avatar_save():
    user_id = _require_login()
    if not user_id:
        return redirect("/signup")

    data = request.form or {}
    seed = (data.get("seed") or "ReConnect").strip()
    top = (data.get("top") or "").strip()
    eyes = (data.get("eyes") or "").strip()
    mouth = (data.get("mouth") or "").strip()
    accessories = (data.get("accessories") or "").strip()
    skin = (data.get("skin") or "").strip()
    gender = (data.get("gender") or "").strip()
    background = (data.get("background") or "").strip()
    avatar_data = (data.get("avatar_data") or "").strip()
    edit_mode = (data.get("edit_mode") or "").strip() == "1"

    accessories_q = "" if accessories == "earbuds" else accessories

    config = {
        "seed": seed,
        "top": top,
        "eyes": eyes,
        "mouth": mouth,
        "accessories": accessories,
        "skin": skin,
        "gender": gender,
        "background": background,
    }

    qs = "&".join(
        [
            f"seed={urllib.parse.quote(seed)}",
            f"top={urllib.parse.quote(top)}",
            f"eyes={urllib.parse.quote(eyes)}",
            f"mouth={urllib.parse.quote(mouth)}",
            f"accessories={urllib.parse.quote(accessories_q)}",
            f"facialHair=Blank",
            f"skinColor={urllib.parse.quote(skin)}",
        ]
    )
    avatar_url = avatar_data or f"/api/avatar?{qs}"

    _set_user_setting(user_id, "avatar_config", json.dumps(config))
    _set_user_setting(user_id, "avatar_url", avatar_url)
    db.session.commit()

    return redirect("/profile" if edit_mode else "/onboarding")

#Log In
@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, retry_after = _rate_limit_check(f"login:{ip}", limit=10, window_seconds=60)
    if not allowed:
        return jsonify({"ok": False, "error": "Too many login attempts", "retry_after": retry_after}), 429

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    accept_terms_raw = data.get("accept_terms")
    accepted_terms = False
    if isinstance(accept_terms_raw, bool):
        accepted_terms = accept_terms_raw
    else:
        accepted_terms = str(accept_terms_raw or "").strip().lower() in {"1", "true", "yes", "on"}

    if not email or not password:
        return jsonify({"ok": False, "error": "Missing email or password"}), 400
    if not accepted_terms:
        return jsonify({"ok": False, "error": "Please accept Terms & Conditions to continue"}), 400

    if len(password) < 8:
        return jsonify({"ok": False, "error": "Password must be at least 8 characters"}), 400

    u = User.query.filter_by(email=email).first()
    if not u or not u.check_password(password):
        _log_audit("auth", "login_failed", None, {"email": email, "ip": ip})
        return jsonify({"ok": False, "error": "Invalid email or password"}), 401

    # Prevent duplicate OTP emails when the login button is clicked repeatedly:
    # if the same user already has a valid pending 2FA code in this session, reuse it.
    existing_pending_user_id = session.get("pending_2fa_user_id")
    existing_pending_email = (session.get("pending_2fa_email") or "").strip().lower()
    existing_pending_expires = session.get("pending_2fa_expires_at")
    if (
        existing_pending_user_id
        and str(existing_pending_user_id) == str(u.id)
        and existing_pending_email == email
        and existing_pending_expires
    ):
        try:
            existing_expires_at = datetime.fromisoformat(existing_pending_expires)
            if datetime.utcnow() <= existing_expires_at:
                existing_delivery = (session.get("pending_2fa_delivery") or "email").strip() or "email"
                existing_dev_code = (session.get("pending_2fa_dev_code") or "").strip()
                return jsonify(
                    {
                        "ok": True,
                        "requires_2fa": True,
                        "delivery": existing_delivery,
                        "dev_code": existing_dev_code if existing_delivery == "dev" and existing_dev_code else None,
                        "next": "/login-2fa",
                    }
                )
        except Exception:
            _clear_pending_2fa()

    code = _generate_2fa_code()
    delivered = False
    try:
        delivered = _send_2fa_email(u.email, code)
    except Exception:
        delivered = False
    _set_pending_2fa(
        u,
        code,
        delivery="email" if delivered else "dev",
        dev_code=code if not delivered else "",
    )

    return jsonify(
        {
            "ok": True,
            "requires_2fa": True,
            "delivery": "email" if delivered else "dev",
            "dev_code": code if not delivered else None,
            "next": "/login-2fa",
        }
    )


@app.post("/api/login/2fa/verify")
def api_login_2fa_verify():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, retry_after = _rate_limit_check(f"login_2fa_verify:{ip}", limit=20, window_seconds=60)
    if not allowed:
        return jsonify({"ok": False, "error": "Too many verification attempts", "retry_after": retry_after}), 429

    pending_user_id = session.get("pending_2fa_user_id")
    pending_hash = session.get("pending_2fa_code_sha256")
    pending_expires = session.get("pending_2fa_expires_at")
    if not pending_user_id or not pending_hash or not pending_expires:
        return jsonify({"ok": False, "error": "No pending verification"}), 400

    try:
        expires_at = datetime.fromisoformat(pending_expires)
    except Exception:
        _clear_pending_2fa()
        return jsonify({"ok": False, "error": "Verification expired"}), 400
    if datetime.utcnow() > expires_at:
        _clear_pending_2fa()
        return jsonify({"ok": False, "error": "Verification code expired"}), 400

    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if len(code) != 6 or not code.isdigit():
        return jsonify({"ok": False, "error": "Enter a valid 6-digit code"}), 400

    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if code_hash != pending_hash:
        return jsonify({"ok": False, "error": "Incorrect verification code"}), 400

    u = db.session.get(User, pending_user_id)
    if not u:
        _clear_pending_2fa()
        return jsonify({"ok": False, "error": "User not found"}), 404

    db.session.add(
        AuthEvent(
            user_id=u.id,
            event_type="login",
            email=u.email,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
    )
    db.session.commit()

    session["user_id"] = u.id
    _clear_pending_2fa()
    _log_audit("auth", "login", u.id, {"email": u.email, "method": "2fa_email"})
    return jsonify({"ok": True})


@app.post("/api/login/2fa/resend")
def api_login_2fa_resend():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, retry_after = _rate_limit_check(f"login_2fa_resend:{ip}", limit=6, window_seconds=60)
    if not allowed:
        return jsonify({"ok": False, "error": "Too many resend attempts", "retry_after": retry_after}), 429

    pending_user_id = session.get("pending_2fa_user_id")
    if not pending_user_id:
        return jsonify({"ok": False, "error": "No pending verification"}), 400

    u = db.session.get(User, pending_user_id)
    if not u:
        _clear_pending_2fa()
        return jsonify({"ok": False, "error": "User not found"}), 404
    retry_after = _seconds_until_iso(session.get("pending_2fa_expires_at"))
    if retry_after > 0:
        return jsonify({"ok": False, "error": f"You can resend in {retry_after}s", "retry_after": retry_after}), 429

    code = _generate_2fa_code()
    delivered = False
    try:
        delivered = _send_2fa_email(u.email, code)
    except Exception:
        delivered = False
    _set_pending_2fa(
        u,
        code,
        delivery="email" if delivered else "dev",
        dev_code=code if not delivered else "",
    )
    return jsonify(
        {
            "ok": True,
            "delivery": "email" if delivered else "dev",
            "dev_code": code if not delivered else None,
            "retry_after": OTP_CODE_MINUTES * 60,
        }
    )


@app.post("/api/logout")
def api_logout():
    session.pop("user_id", None)
    _clear_pending_2fa()
    _clear_pending_signup()
    return jsonify({"ok": True})


@app.get("/api/me")
def api_me():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "User not found"}), 404

    return jsonify(
        {
            "ok": True,
            "user": {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "member_type": u.member_type,
            },
        }
    )

#Edit Bio
@app.get("/api/profile")
def api_profile():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "User not found"}), 404

    user_settings = _get_user_settings_map(user_id)

    onboarding = json.loads(user_settings.get("onboarding", "{}"))
    languages = _load_user_languages(user_id)
    skills_teach = json.loads(user_settings.get("skills_teach", "[]") or "[]")
    skills_learn = json.loads(user_settings.get("skills_learn", "[]") or "[]")
    privacy = json.loads(user_settings.get("privacy", "{}") or "{}")
    notifications = json.loads(user_settings.get("notifications", "{}") or "{}")

    conn = _get_chat_conn()
    connections_count = conn.execute(
        "SELECT COUNT(*) AS c FROM matches WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]
    conn.close()

    conn = _get_main_conn()
    memories_count = conn.execute(
        "SELECT COUNT(*) AS c FROM challenge_entries WHERE user_id = ?", (user_id,)
    ).fetchone()["c"]
    badges_count = conn.execute(
        "SELECT COUNT(*) AS c FROM user_badges WHERE user_id = ? AND earned = 1",
        (user_id,),
    ).fetchone()["c"]
    vh_rows = conn.execute(
        """
        SELECT source_type, COUNT(*) AS c, COALESCE(SUM(hours), 0) AS h
        FROM volunteer_hours
        WHERE user_id = ?
        GROUP BY source_type
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    vh_map = {r["source_type"]: {"count": int(r["c"] or 0), "hours": float(r["h"] or 0)} for r in vh_rows}
    titles_payload = _profile_titles_payload(user_id)

    repoints, _ = _get_user_points(user_id)
    circles_count = CircleSignup.query.filter_by(user_id=user_id).count()
    safety = _get_safety_snapshot(user_id)
    completeness = _profile_completeness(onboarding, user_settings)

    return jsonify(
        {
            "ok": True,
            "profile": {
                "id": u.id,
                "full_name": u.full_name,
                "username": _get_user_identity(user_id).get("username", _username_slug(u.full_name or f"user_{u.id}", u.id)),
                "email": u.email,
                "member_type": u.member_type,
                "is_private": bool(int(_get_user_identity(user_id).get("is_private", 0))),
                "bio": user_settings.get("bio", ""),
                "onboarding": onboarding,
                "languages": languages,
                "skills_teach": skills_teach,
                "skills_learn": skills_learn,
                "privacy": privacy,
                "notifications": notifications,
                "avatar_url": user_settings.get("avatar_url", ""),
                "banner_url": user_settings.get("banner_url", ""),
                "location_name": user_settings.get("location_name", ""),
                "location_lat": user_settings.get("location_lat", ""),
                "location_lng": user_settings.get("location_lng", ""),
                "phone_number": (u.phone or user_settings.get("phone_number", "")),
                "verified_with": user_settings.get("verified_with", ""),
                "connections_count": connections_count,
                "memories_count": memories_count,
                "repoints": repoints,
                "circles_count": circles_count,
                "badges_count": badges_count,
                "verification_badges": _get_user_verification_badges(user_id),
                "total_volunteer_hours": float(getattr(u, "total_volunteer_hours", 0) or 0),
                "volunteer_breakdown": {
                    "meetups": vh_map.get("meetup", {"count": 0, "hours": 0}),
                    "learning_circles": vh_map.get("learning_circle", {"count": 0, "hours": 0}),
                    "events": vh_map.get("event", {"count": 0, "hours": 0}),
                    "workshops": vh_map.get("workshop", {"count": 0, "hours": 0}),
                },
                "equipped_title": titles_payload.get("equipped"),
                "titles": titles_payload.get("titles", []),
                "emergency_contact": json.loads(user_settings.get("emergency_contact", "{}") or "{}"),
                "safety": safety,
                "completeness": completeness,
            },
        }
    )


@app.post("/api/profile")
def api_update_profile():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403

    data = request.get_json(silent=True) or {}

    bio = data.get("bio", "").strip()
    languages = data.get("languages")
    skills_teach = data.get("skills_teach")
    skills_learn = data.get("skills_learn")
    privacy = data.get("privacy")
    interests = data.get("interests")
    notifications = data.get("notifications")
    location_name = (data.get("location_name") or "").strip()
    location_lat = (data.get("location_lat") or "").strip()
    location_lng = (data.get("location_lng") or "").strip()
    verified_with = data.get("verified_with")
    emergency_contact = data.get("emergency_contact")
    email_input = (data.get("email") or "").strip()
    phone_input = (data.get("phone") or "").strip()

    if bio:
        _set_user_setting(user_id, "bio", bio)
    if languages is not None:
        _save_user_languages(user_id, languages)
    if skills_teach is not None:
        _set_user_setting(user_id, "skills_teach", json.dumps(skills_teach))
    if skills_learn is not None:
        _set_user_setting(user_id, "skills_learn", json.dumps(skills_learn))
    if privacy is not None:
        _set_user_setting(user_id, "privacy", json.dumps(privacy))
    if interests is not None:
        existing = _safe_json(_get_user_settings_map(user_id).get("onboarding", "{}"), {})
        existing["interests"] = interests
        _set_user_setting(user_id, "onboarding", json.dumps(existing))
    if notifications is not None:
        _set_user_setting(user_id, "notifications", json.dumps(notifications))
    if location_name or location_lat or location_lng:
        _set_user_setting(user_id, "location_name", location_name)
        _set_user_setting(user_id, "location_lat", location_lat)
        _set_user_setting(user_id, "location_lng", location_lng)
    if verified_with is not None:
        cleaned = (verified_with or "").strip().lower()
        if cleaned and cleaned not in {"singpass", "nric", "email", "phone"}:
            return jsonify({"ok": False, "error": "Verification must be Singpass, NRIC, email or phone"}), 400
        _set_user_setting(user_id, "verified_with", cleaned)
    if emergency_contact is not None:
        _set_user_setting(user_id, "emergency_contact", json.dumps(emergency_contact))

    u = db.session.get(User, user_id)
    if u:
        if email_input:
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_input):
                return jsonify({"ok": False, "error": "Invalid email format"}), 400
            duplicate = User.query.filter(User.email == email_input, User.id != user_id).first()
            if duplicate:
                return jsonify({"ok": False, "error": "Email already in use"}), 400
            u.email = email_input
        if phone_input:
            normalized_phone = re.sub(r"[^\d+]", "", phone_input)
            if not re.match(r"^\+?\d{8,15}$", normalized_phone):
                return jsonify({"ok": False, "error": "Invalid phone format"}), 400
            try:
                conn = _get_main_conn()
                conn.execute("UPDATE users SET phone = ? WHERE id = ?", (normalized_phone, user_id))
                conn.commit()
                conn.close()
            except Exception:
                pass

    db.session.commit()
    return jsonify({"ok": True})


@app.get("/api/profile/titles")
def api_profile_titles():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    return jsonify({"ok": True, **_profile_titles_payload(user_id)})


@app.post("/api/profile/equip_title")
def api_profile_equip_title():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    title_id = data.get("title_id")
    try:
        title_id = int(title_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "title_id is required"}), 400
    conn = _get_main_conn()
    has_title = conn.execute(
        "SELECT 1 FROM user_titles WHERE user_id = ? AND title_id = ?",
        (user_id, title_id),
    ).fetchone()
    if not has_title:
        conn.close()
        return jsonify({"ok": False, "error": "Title not unlocked"}), 403
    conn.execute("UPDATE users SET equipped_title_id = ? WHERE id = ?", (title_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, **_profile_titles_payload(user_id)})


@app.post("/api/profile/privacy")
@login_required
def api_profile_privacy():
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    user_id = int(g.current_user_id)
    data = request.get_json(silent=True) or {}
    is_private = 1 if bool(data.get("is_private")) else 0
    conn = _get_main_conn()
    conn.execute("UPDATE users SET is_private = ? WHERE id = ?", (is_private, user_id))
    conn.commit()
    conn.close()
    _log_audit("privacy", "profile_privacy", user_id, {"is_private": bool(is_private)})
    return jsonify({"ok": True, "is_private": bool(is_private)})


def _resolve_target_user_id(data: dict):
    target_id = _coerce_int(data.get("target_user_id"))
    if target_id:
        return target_id
    username = (data.get("username") or "").strip()
    row = _get_user_by_username(username) if username else None
    return int(row["id"]) if row else None


@app.post("/api/follow/request")
@login_required
def api_follow_request():
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    viewer_id = int(g.current_user_id)
    data = request.get_json(silent=True) or {}
    target_id = _resolve_target_user_id(data)
    if not target_id:
        return jsonify({"ok": False, "error": "target_user_id is required"}), 400
    if target_id == viewer_id:
        return jsonify({"ok": False, "error": "Cannot follow yourself"}), 400
    if is_blocked(viewer_id, target_id):
        return jsonify({"ok": False, "error": "Follow unavailable due to block settings"}), 403

    allowed, retry_after = _social_action_allowed(viewer_id, "follow_request", target_id, cooldown_seconds=10)
    if not allowed:
        return jsonify({"ok": False, "error": "Please wait before sending another follow request", "retry_after": retry_after}), 429

    status = "accepted" if not _is_private_profile(target_id) else "pending"
    now = _utc_now_iso()
    conn = _get_main_conn()
    conn.execute(
        """
        INSERT INTO follows (follower_id, followed_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(follower_id, followed_id) DO UPDATE SET
            status = excluded.status,
            updated_at = excluded.updated_at
        """,
        (viewer_id, target_id, status, now, now),
    )
    conn.commit()
    conn.close()
    _log_audit("social", "follow_request", viewer_id, {"target_user_id": target_id, "status": status})
    return jsonify({"ok": True, "status": status})


@app.post("/api/follow/cancel")
@login_required
def api_follow_cancel():
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    viewer_id = int(g.current_user_id)
    data = request.get_json(silent=True) or {}
    target_id = _resolve_target_user_id(data)
    if not target_id:
        return jsonify({"ok": False, "error": "target_user_id is required"}), 400
    conn = _get_main_conn()
    conn.execute("DELETE FROM follows WHERE follower_id = ? AND followed_id = ?", (viewer_id, target_id))
    conn.commit()
    conn.close()
    _log_audit("social", "follow_cancel", viewer_id, {"target_user_id": target_id})
    return jsonify({"ok": True, "status": "none"})


@app.post("/api/follow/approve")
@login_required
def api_follow_approve():
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    owner_id = int(g.current_user_id)
    data = request.get_json(silent=True) or {}
    follower_id = _coerce_int(data.get("follower_id"))
    if not follower_id:
        return jsonify({"ok": False, "error": "follower_id is required"}), 400
    if is_blocked(owner_id, follower_id):
        return jsonify({"ok": False, "error": "Cannot approve blocked user"}), 403
    conn = _get_main_conn()
    cur = conn.cursor()
    updated = cur.execute(
        "UPDATE follows SET status = 'accepted', updated_at = ? WHERE follower_id = ? AND followed_id = ? AND status = 'pending'",
        (_utc_now_iso(), follower_id, owner_id),
    ).rowcount
    conn.commit()
    conn.close()
    if not updated:
        return jsonify({"ok": False, "error": "Pending follow request not found"}), 404
    _log_audit("social", "follow_approve", owner_id, {"follower_id": follower_id})
    return jsonify({"ok": True, "status": "accepted"})


@app.post("/api/follow/reject")
@login_required
def api_follow_reject():
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    owner_id = int(g.current_user_id)
    data = request.get_json(silent=True) or {}
    follower_id = _coerce_int(data.get("follower_id"))
    if not follower_id:
        return jsonify({"ok": False, "error": "follower_id is required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    updated = cur.execute(
        "UPDATE follows SET status = 'rejected', updated_at = ? WHERE follower_id = ? AND followed_id = ? AND status = 'pending'",
        (_utc_now_iso(), follower_id, owner_id),
    ).rowcount
    conn.commit()
    conn.close()
    if not updated:
        return jsonify({"ok": False, "error": "Pending follow request not found"}), 404
    _log_audit("social", "follow_reject", owner_id, {"follower_id": follower_id})
    return jsonify({"ok": True, "status": "rejected"})


@app.post("/api/block")
@login_required
def api_block_user():
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    blocker_id = int(g.current_user_id)
    data = request.get_json(silent=True) or {}
    blocked_id = _resolve_target_user_id(data)
    if not blocked_id:
        return jsonify({"ok": False, "error": "target_user_id is required"}), 400
    if blocked_id == blocker_id:
        return jsonify({"ok": False, "error": "Cannot block yourself"}), 400

    now = _utc_now_iso()
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO blocks (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
        (blocker_id, blocked_id, now),
    )
    cur.execute(
        "INSERT OR IGNORE INTO user_blocks (user_id, blocked_user_id, created_at) VALUES (?, ?, ?)",
        (blocker_id, blocked_id, now),
    )
    cur.execute(
        "DELETE FROM follows WHERE (follower_id = ? AND followed_id = ?) OR (follower_id = ? AND followed_id = ?)",
        (blocker_id, blocked_id, blocked_id, blocker_id),
    )
    conn.commit()
    conn.close()
    _log_audit("safety", "block_user", blocker_id, {"blocked_user_id": blocked_id})
    return jsonify({"ok": True})


@app.get("/volunteer/export")
def volunteer_export_csv():
    user_id = _require_login()
    if not user_id:
        return redirect("/login")
    conn = _get_main_conn()
    rows = conn.execute(
        """
        SELECT vh.source_type, vh.source_id, vh.hours, vh.notes, vh.created_at, e.organiser_type
        FROM volunteer_hours vh
        LEFT JOIN events e ON vh.source_type = 'event' AND e.id = vh.source_id
        WHERE vh.user_id = ?
        ORDER BY vh.created_at DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    lines = ["source_type,source_id,hours,bucket,notes,created_at"]
    for r in rows:
        bucket = ""
        if r["source_type"] == "event":
            otype = (r["organiser_type"] or "").strip().lower()
            if otype == "corporate":
                bucket = "Corporate Volunteering"
            elif otype == "government":
                bucket = "Gov Programme Hours"
        safe_notes = (r["notes"] or "").replace('"', '""')
        lines.append(f"{r['source_type']},{r['source_id']},{float(r['hours'] or 0):.2f},\"{bucket}\",\"{safe_notes}\",{r['created_at']}")
    csv_data = "\n".join(lines)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=volunteer_hours.csv"},
    )


@app.post("/api/verification/email/send")
def api_verification_email_send():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "User not found"}), 404

    code = _generate_2fa_code()
    _set_pending_contact_verification("email", u.email, code)
    try:
        delivered = _send_verification_email(u.email, code)
    except Exception:
        delivered = False
    return jsonify(
        {
            "ok": True,
            "delivery": "email" if delivered else "dev",
            "dev_code": code if not delivered else None,
            "email": u.email,
        }
    )


@app.post("/api/verification/email/verify")
def api_verification_email_verify():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    pending_target = session.get("pending_verify_email_target")
    pending_hash = session.get("pending_verify_email_code_sha256")
    pending_expires = session.get("pending_verify_email_expires_at")
    if not pending_target or not pending_hash or not pending_expires:
        return jsonify({"ok": False, "error": "No pending email verification"}), 400

    try:
        expires_at = datetime.fromisoformat(pending_expires)
    except Exception:
        _clear_pending_contact_verification("email")
        return jsonify({"ok": False, "error": "Verification expired"}), 400
    if datetime.utcnow() > expires_at:
        _clear_pending_contact_verification("email")
        return jsonify({"ok": False, "error": "Verification code expired"}), 400

    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if len(code) != 6 or not code.isdigit():
        return jsonify({"ok": False, "error": "Enter a valid 6-digit code"}), 400
    if hashlib.sha256(code.encode("utf-8")).hexdigest() != pending_hash:
        return jsonify({"ok": False, "error": "Incorrect verification code"}), 400

    _set_user_setting(user_id, "verified_with", "email")
    _set_user_setting(user_id, "verified_email", pending_target)
    db.session.commit()
    _clear_pending_contact_verification("email")
    return jsonify({"ok": True, "verified_with": "email"})


@app.post("/api/verification/phone/send")
def api_verification_phone_send():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    country_code = (data.get("country_code") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()
    phone_e164 = _normalize_phone_e164(country_code, phone_number)
    if not phone_e164:
        return jsonify({"ok": False, "error": "Enter a valid phone number"}), 400

    use_twilio_verify = all(
        [
            os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
            os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
            os.getenv("TWILIO_VERIFY_SERVICE_SID", "").strip(),
        ]
    )

    if use_twilio_verify:
        ok, err = _twilio_verify_send_code(phone_e164)
        if not ok:
            return jsonify({"ok": False, "error": err or "Could not send SMS code"}), 502
        _clear_pending_contact_verification("phone")
        session["pending_verify_phone_target"] = phone_e164
        session["pending_verify_phone_expires_at"] = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        session["pending_verify_phone_mode"] = "twilio_verify"
        return jsonify({"ok": True, "delivery": "sms", "dev_code": None, "phone_number": phone_e164})

    code = _generate_2fa_code()
    _set_pending_contact_verification("phone", phone_e164, code)
    session["pending_verify_phone_mode"] = "local"
    try:
        delivered = _send_verification_sms(phone_e164, code)
    except Exception:
        delivered = False
    return jsonify(
        {
            "ok": True,
            "delivery": "sms" if delivered else "dev",
            "dev_code": code if not delivered else None,
            "phone_number": phone_e164,
        }
    )


@app.post("/api/verification/phone/verify")
def api_verification_phone_verify():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    pending_target = session.get("pending_verify_phone_target")
    pending_hash = session.get("pending_verify_phone_code_sha256")
    pending_expires = session.get("pending_verify_phone_expires_at")
    pending_mode = (session.get("pending_verify_phone_mode") or "local").strip().lower()
    if not pending_target or not pending_expires:
        return jsonify({"ok": False, "error": "No pending phone verification"}), 400
    if pending_mode != "twilio_verify" and not pending_hash:
        return jsonify({"ok": False, "error": "No pending phone verification"}), 400

    try:
        expires_at = datetime.fromisoformat(pending_expires)
    except Exception:
        _clear_pending_contact_verification("phone")
        return jsonify({"ok": False, "error": "Verification expired"}), 400
    if datetime.utcnow() > expires_at:
        _clear_pending_contact_verification("phone")
        return jsonify({"ok": False, "error": "Verification code expired"}), 400

    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if len(code) != 6 or not code.isdigit():
        return jsonify({"ok": False, "error": "Enter a valid 6-digit code"}), 400

    if pending_mode == "twilio_verify":
        approved, err = _twilio_verify_check_code(pending_target, code)
        if not approved:
            return jsonify({"ok": False, "error": err or "Incorrect verification code"}), 400
    else:
        if hashlib.sha256(code.encode("utf-8")).hexdigest() != pending_hash:
            return jsonify({"ok": False, "error": "Incorrect verification code"}), 400

    _set_user_setting(user_id, "verified_with", "phone")
    _set_user_setting(user_id, "phone_number", pending_target)
    db.session.commit()
    _clear_pending_contact_verification("phone")
    return jsonify({"ok": True, "verified_with": "phone", "phone_number": pending_target})


@app.post("/profile/languages/save")
def save_profile_languages():
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    selected_languages = request.form.getlist("languages")
    _save_user_languages(user_id, selected_languages)
    db.session.commit()
    flash("Languages saved.", "success")
    return redirect("/profile")


@app.get("/api/safety_score")
def api_safety_score():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    snapshot = _get_safety_snapshot(user_id)
    return jsonify({"ok": True, "safety": snapshot})


@app.get("/api/wellbeing/summary")
def api_wellbeing_summary():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    checkin = _get_latest_checkin(user_id)
    recos = _load_wellbeing_recos(user_id)
    analytics = _wellbeing_analytics(user_id)
    insight = analytics["insights"][0] if analytics["insights"] else _wellbeing_insight(user_id)
    nudge = _wellbeing_nudge(user_id, analytics)
    return jsonify(
        {
            "ok": True,
            "checkin": {
                "id": checkin["id"],
                "mood": _normalize_mood(checkin["mood"]),
                "reason": checkin["reason"],
                "notes": checkin["notes"],
                "created_at": checkin["created_at"],
            }
            if checkin
            else None,
            "last_updated_human": _humanize_relative_time(checkin["created_at"]) if checkin else "",
            "recommendations": recos,
            "insight": insight,
            "trend": analytics["trend"],
            "activity": analytics["activity"],
            "risk": analytics["risk"],
            "score": analytics["score"],
            "nudge": nudge,
            "badges": analytics["badges"],
        }
    )


@app.post("/api/wellbeing/checkin")
def api_wellbeing_checkin():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    mood = (data.get("mood") or "").strip().lower()
    reason = (data.get("reason") or "").strip()
    notes = (data.get("notes") or "").strip()
    if mood not in WELLBEING_MOOD_SCORES:
        return jsonify({"ok": False, "error": "Mood must be one of: happy, good, neutral, stressed, sad"}), 400

    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO mood_checkins (user_id, mood, reason, notes, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, mood, reason or None, notes or None, _utc_now_iso()),
    )
    conn.commit()
    conn.close()

    recos = _build_wellbeing_recos(mood)
    _store_wellbeing_recos(user_id, mood, recos)
    _add_notification(user_id, "wellbeing", f"Mood check-in saved: {mood}.", {"mood": mood})
    analytics = _wellbeing_analytics(user_id)
    return jsonify(
        {
            "ok": True,
            "mood": mood,
            "recommendations": recos,
            "insight": analytics["insights"][0] if analytics["insights"] else _wellbeing_insight(user_id),
            "trend": analytics["trend"],
            "risk": analytics["risk"],
            "score": analytics["score"],
            "nudge": _wellbeing_nudge(user_id, analytics),
        }
    )


@app.get("/api/wellbeing/history")
def api_wellbeing_history():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    rows = _get_recent_checkins(user_id, limit=30)
    history = [
        {
            "mood": _normalize_mood(r["mood"]),
            "reason": r["reason"],
            "notes": r["notes"],
            "created_at": r["created_at"],
            "mood_score": WELLBEING_MOOD_SCORES.get(_normalize_mood(r["mood"]), 3),
        }
        for r in rows
    ]
    return jsonify({"ok": True, "history": history})


@app.get("/api/wellbeing/dashboard")
def api_wellbeing_dashboard():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    analytics = _wellbeing_analytics(user_id)
    latest = _get_latest_checkin(user_id)
    return jsonify(
        {
            "ok": True,
            "latest_checkin": {
                "mood": _normalize_mood(latest["mood"]),
                "created_at": latest["created_at"],
                "reason": latest["reason"],
                "notes": latest["notes"],
            }
            if latest
            else None,
            "last_updated_human": _humanize_relative_time(latest["created_at"]) if latest else "",
            "trend": analytics["trend"],
            "activity": analytics["activity"],
            "daily_activity_7d": analytics["daily_activity_7d"],
            "social_energy": analytics["social_energy"],
            "emotion_breakdown": analytics["emotion_breakdown"],
            "weekly_distribution": analytics["weekly_distribution"],
            "line_points_30d": analytics["line_points_30d"],
            "mood_points_7d": analytics["mood_points_7d"],
            "insights": analytics["insights"],
            "recommendations": analytics["recommendations"],
            "risk": analytics["risk"],
            "score": analytics["score"],
            "badges": analytics["badges"],
            "nudge": _wellbeing_nudge(user_id, analytics),
        }
    )


@app.get("/api/wellbeing/journal")
def api_wellbeing_journal():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, prompt, gratitude, reflection, created_at
        FROM wellbeing_journal
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 30
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "entries": [
                {
                    "id": r["id"],
                    "prompt": r["prompt"] or "",
                    "gratitude": r["gratitude"] or "",
                    "reflection": r["reflection"] or "",
                    "created_at": r["created_at"],
                }
                for r in rows
            ],
        }
    )


@app.post("/api/wellbeing/journal")
def api_wellbeing_journal_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    gratitude = (data.get("gratitude") or "").strip()
    reflection = (data.get("reflection") or "").strip()
    if not gratitude and not reflection:
        return jsonify({"ok": False, "error": "Write at least gratitude or reflection."}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO wellbeing_journal (user_id, prompt, gratitude, reflection, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, prompt or None, gratitude or None, reflection or None, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    _add_notification(user_id, "wellbeing", "Reflection journal saved.", {})
    return jsonify({"ok": True})


@app.get("/api/feed")
def api_feed():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    scope = (request.args.get("scope") or "community").strip().lower()
    if scope not in {"community", "friends"}:
        scope = "community"

    conn = _get_main_conn()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT e.id, e.owner_user_id, e.entry_type, e.title, e.content, e.visibility, e.featured, e.campaign_tag, e.created_at,
               (SELECT id FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_id,
               (SELECT file_path FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_url,
               COALESCE((SELECT full_name FROM users u WHERE u.id = e.owner_user_id LIMIT 1), 'User') AS owner_name,
               COALESCE((SELECT username FROM users u WHERE u.id = e.owner_user_id LIMIT 1), '') AS owner_username,
               COALESCE((SELECT value FROM user_settings s WHERE s.user_id = e.owner_user_id AND s.key = 'avatar_url' LIMIT 1), '') AS owner_avatar,
               (SELECT COUNT(*) FROM scrapbook_reactions r WHERE r.entry_id = e.id) AS like_count,
               (SELECT COUNT(*) FROM scrapbook_comments c WHERE c.entry_id = e.id) AS comment_count
        FROM scrapbook_entries e
        ORDER BY e.id DESC
        LIMIT 300
        """
    ).fetchall()
    conn.close()

    entries = []
    for r in rows:
        owner_id = int(r["owner_user_id"])
        visibility = _normalize_visibility(r["visibility"])
        if not _can_view_scrapbook_entry(user_id, owner_id, visibility):
            continue
        if scope == "community" and visibility != "community":
            continue
        if scope == "friends":
            if owner_id != int(user_id) and follow_status(user_id, owner_id) != "accepted" and not _are_friends(user_id, owner_id):
                continue
            if visibility not in {"friends", "community"}:
                continue
        entries.append(
            {
                "id": r["id"],
                "owner_user_id": owner_id,
                "owner_name": r["owner_name"] or "User",
                "owner_username": (r["owner_username"] or _username_slug(r["owner_name"] or f"user_{owner_id}", owner_id)),
                "owner_avatar": r["owner_avatar"] or "",
                "entry_type": r["entry_type"],
                "title": r["title"],
                "content": r["content"],
                "visibility": visibility,
                "featured": bool(r["featured"]),
                "campaign_tag": r["campaign_tag"] or "",
                "created_at": r["created_at"],
                "media_url": _protected_media_url(r["media_id"], r["media_url"]),
                "like_count": int(r["like_count"] or 0),
                "comment_count": int(r["comment_count"] or 0),
            }
        )

    featured_entries = [e for e in entries if e["featured"]]
    normal_entries = [e for e in entries if not e["featured"]]
    return jsonify({"ok": True, "scope": scope, "featured": featured_entries[:12], "entries": normal_entries})


def _scrapbook_user_meta(cur, user_id: int) -> dict:
    row = cur.execute(
        """
        SELECT
            COALESCE(NULLIF(username, ''), NULLIF(full_name, ''), 'user') AS username,
            COALESCE(NULLIF(full_name, ''), 'User') AS full_name,
            COALESCE(
                (SELECT value FROM user_settings WHERE user_id = ? AND key = 'avatar_url' LIMIT 1),
                ''
            ) AS avatar_url
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (int(user_id), int(user_id)),
    ).fetchone()
    if not row:
        return {"id": int(user_id), "username": "User", "avatar_url": ""}
    return {
        "id": int(user_id),
        "username": (row["username"] or _username_slug(row["full_name"] or f"user_{int(user_id)}", int(user_id))),
        "display_name": (row["full_name"] or "User"),
        "avatar_url": (row["avatar_url"] or ""),
    }


def _feed_post_payload(cur, row, viewer_user_id: int) -> dict:
    post_id = int(row["id"])
    owner_id = int(row["owner_user_id"])
    like_count = int(
        cur.execute(
            """
            SELECT COUNT(*)
            FROM scrapbook_reactions
            WHERE entry_id = ? AND reaction_type = 'heart'
            """,
            (post_id,),
        ).fetchone()[0]
        or 0
    )
    comment_count = int(
        cur.execute(
            "SELECT COUNT(*) FROM scrapbook_comments WHERE entry_id = ?",
            (post_id,),
        ).fetchone()[0]
        or 0
    )
    is_liked = bool(
        cur.execute(
            """
            SELECT 1
            FROM scrapbook_reactions
            WHERE entry_id = ? AND user_id = ? AND reaction_type = 'heart'
            LIMIT 1
            """,
            (post_id, int(viewer_user_id)),
        ).fetchone()
    )
    return {
        "id": post_id,
        "media_url": _protected_media_url(row["media_id"], row["media_url"]),
        "caption": (row["content"] or row["title"] or ""),
        "created_at": row["created_at"],
        "user": _scrapbook_user_meta(cur, owner_id),
        "like_count": like_count,
        "comment_count": comment_count,
        "is_liked": is_liked,
    }


@app.get("/media/<int:media_id>")
@login_required
def protected_media(media_id: int):
    viewer_id = int(g.current_user_id)
    conn = _get_main_conn()
    row = conn.execute(
        """
        SELECT m.id, m.file_path, e.owner_user_id, e.visibility
          FROM scrapbook_media m
          JOIN scrapbook_entries e ON e.id = m.entry_id
         WHERE m.id = ?
         LIMIT 1
        """,
        (int(media_id),),
    ).fetchone()
    conn.close()
    if not row:
        return ("Not found", 404)

    owner_id = int(row["owner_user_id"])
    if is_blocked(viewer_id, owner_id):
        return ("Forbidden", 403)
    if not can_view_profile(viewer_id, owner_id, _is_private_profile(owner_id)):
        return ("Forbidden", 403)
    if not _can_view_scrapbook_entry(viewer_id, owner_id, row["visibility"]):
        return ("Forbidden", 403)

    file_path = str(row["file_path"] or "").strip()
    if not file_path:
        return ("Not found", 404)
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return redirect(file_path)

    path_obj = Path(file_path)
    if file_path.startswith("/static/"):
        rel = file_path.replace("/static/", "", 1).lstrip("/")
        path_obj = STATIC_DIR / rel
    elif not path_obj.is_absolute():
        path_obj = BASE_DIR / file_path

    if not path_obj.exists() or not path_obj.is_file():
        return ("Not found", 404)
    return send_file(path_obj)


@app.get("/api/feed/community")
def api_feed_community():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    conn = _get_main_conn()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            e.id,
            e.owner_user_id,
            e.title,
            e.content,
            e.visibility,
            e.created_at,
            (SELECT id FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_id,
            (SELECT file_path FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_url
        FROM scrapbook_entries e
        ORDER BY e.id DESC
        LIMIT 240
        """
    ).fetchall()

    posts = []
    for row in rows:
        owner_id = int(row["owner_user_id"])
        if _normalize_visibility(row["visibility"]) != "community":
            continue
        if not _can_view_scrapbook_entry(user_id, owner_id, row["visibility"]):
            continue
        posts.append(_feed_post_payload(cur, row, int(user_id)))

    conn.close()
    return jsonify({"ok": True, "posts": posts})


@app.get("/api/posts/<int:post_id>")
def api_post_detail(post_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT
            e.id,
            e.owner_user_id,
            e.title,
            e.content,
            e.visibility,
            e.created_at,
            (SELECT id FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_id,
            (SELECT file_path FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_url
        FROM scrapbook_entries e
        WHERE e.id = ?
        LIMIT 1
        """,
        (post_id,),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Post not found"}), 404
    if not _can_view_scrapbook_entry(user_id, int(row["owner_user_id"]), row["visibility"]):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403

    comments_rows = cur.execute(
        """
        SELECT id, user_id, comment_text, created_at
        FROM scrapbook_comments
        WHERE entry_id = ?
        ORDER BY id ASC
        LIMIT 150
        """,
        (post_id,),
    ).fetchall()

    comments = []
    for c in comments_rows:
        comments.append(
            {
                "id": int(c["id"]),
                "user": _scrapbook_user_meta(cur, int(c["user_id"])),
                "body": c["comment_text"] or "",
                "created_at": c["created_at"],
            }
        )

    post_payload = _feed_post_payload(cur, row, int(user_id))
    conn.close()
    return jsonify({"ok": True, **post_payload, "comments": comments})


@app.post("/api/posts/<int:post_id>/like")
def api_post_like_toggle(post_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403

    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, owner_user_id, visibility FROM scrapbook_entries WHERE id = ?",
        (post_id,),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Post not found"}), 404
    if not _can_view_scrapbook_entry(user_id, int(row["owner_user_id"]), row["visibility"]):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403

    existing = cur.execute(
        """
        SELECT id
        FROM scrapbook_reactions
        WHERE entry_id = ? AND user_id = ? AND reaction_type = 'heart'
        LIMIT 1
        """,
        (post_id, int(user_id)),
    ).fetchone()
    if existing:
        cur.execute(
            "DELETE FROM scrapbook_reactions WHERE entry_id = ? AND user_id = ? AND reaction_type = 'heart'",
            (post_id, int(user_id)),
        )
        is_liked = False
    else:
        cur.execute(
            "INSERT INTO scrapbook_reactions (entry_id, user_id, reaction_type, created_at) VALUES (?, ?, 'heart', ?)",
            (post_id, int(user_id), _utc_now_iso()),
        )
        is_liked = True
    like_count = int(
        cur.execute(
            "SELECT COUNT(*) FROM scrapbook_reactions WHERE entry_id = ? AND reaction_type = 'heart'",
            (post_id,),
        ).fetchone()[0]
        or 0
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "like_count": like_count, "is_liked": is_liked})


@app.post("/api/posts/<int:post_id>/comments")
def api_post_comment_create(post_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400

    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, owner_user_id, visibility FROM scrapbook_entries WHERE id = ?",
        (post_id,),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Post not found"}), 404
    if not _can_view_scrapbook_entry(user_id, int(row["owner_user_id"]), row["visibility"]):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403

    now = _utc_now_iso()
    cur.execute(
        "INSERT INTO scrapbook_comments (entry_id, user_id, comment_text, created_at) VALUES (?, ?, ?, ?)",
        (post_id, int(user_id), text, now),
    )
    comment_id = int(cur.lastrowid)
    comment_count = int(
        cur.execute("SELECT COUNT(*) FROM scrapbook_comments WHERE entry_id = ?", (post_id,)).fetchone()[0]
        or 0
    )
    conn.commit()
    user_payload = _scrapbook_user_meta(cur, int(user_id))
    conn.close()
    return jsonify(
        {
            "ok": True,
            "comment_count": comment_count,
            "comment": {
                "id": comment_id,
                "user": user_payload,
                "body": text,
                "created_at": now,
            },
        }
    )


@app.post("/api/feed/feature")
def api_feed_feature():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    entry_id = data.get("entry_id")
    featured = 1 if data.get("featured") else 0
    campaign_tag = (data.get("campaign_tag") or "").strip()
    if not entry_id:
        return jsonify({"ok": False, "error": "entry_id required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM scrapbook_entries WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404
    cur.execute(
        "UPDATE scrapbook_entries SET featured = ?, campaign_tag = ? WHERE id = ?",
        (featured, campaign_tag or None, entry_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.get("/api/scrapbook/entries")
def api_scrapbook_entries():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    owner_raw = request.args.get("owner_user_id")
    owner_user_id = user_id
    if owner_raw not in (None, ""):
        try:
            owner_user_id = int(owner_raw)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "owner_user_id must be an integer"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    if owner_user_id != user_id and _is_blocked_between(user_id, owner_user_id):
        conn.close()
        return jsonify({"ok": True, "entries": []})
    rows = cur.execute(
        """
        SELECT e.id, e.owner_user_id, e.entry_type, e.title, e.content, e.visibility, e.featured, e.campaign_tag, e.created_at,
               e.related_user_id, e.circle_title, e.mood_tag, e.location, e.pinned,
               (SELECT id FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_id,
               (SELECT file_path FROM scrapbook_media m WHERE m.entry_id = e.id ORDER BY m.id DESC LIMIT 1) AS media_url
        FROM scrapbook_entries e
        WHERE e.owner_user_id = ?
        ORDER BY e.pinned DESC, e.id DESC
        LIMIT 200
        """,
        (owner_user_id,),
    ).fetchall()
    conn.close()
    visible_rows = [r for r in rows if _can_view_scrapbook_entry(user_id, r["owner_user_id"], r["visibility"])]
    if (
        not visible_rows
        and owner_user_id != user_id
        and can_view_profile(user_id, owner_user_id, _is_private_profile(owner_user_id))
    ):
        identity = _get_user_identity(owner_user_id)
        placeholders = _deterministic_placeholder_scrapbook(owner_user_id, identity.get("username", f"user_{owner_user_id}"))
        return jsonify({"ok": True, "entries": placeholders})
    return jsonify(
        {
            "ok": True,
            "entries": [
                {
                    "id": r["id"],
                    "entry_type": r["entry_type"],
                    "title": r["title"],
                    "content": r["content"],
                    "visibility": _normalize_visibility(r["visibility"]),
                    "featured": bool(r["featured"]),
                    "campaign_tag": r["campaign_tag"] or "",
                    "created_at": r["created_at"],
                    "related_user_id": r["related_user_id"],
                    "circle_title": r["circle_title"],
                    "mood_tag": r["mood_tag"],
                    "location": r["location"],
                    "pinned": r["pinned"],
                    "media_url": _protected_media_url(r["media_id"], r["media_url"]),
                }
                for r in visible_rows
            ],
        }
    )


@app.post("/api/scrapbook/entries")
def api_scrapbook_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    entry_type = (data.get("entry_type") or "chat").strip().lower()
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    visibility = (data.get("visibility") or "private").strip().lower()
    media_url = (data.get("media_url") or "").strip()
    related_user_id = data.get("related_user_id")
    circle_title = (data.get("circle_title") or "").strip()
    mood_tag = (data.get("mood_tag") or "").strip().lower()
    location = (data.get("location") or "").strip()
    featured = 1 if _require_admin() and data.get("featured") else 0
    campaign_tag = (data.get("campaign_tag") or "").strip()

    if entry_type not in {"chat", "meetup", "circle", "challenge"}:
        return jsonify({"ok": False, "error": "Invalid entry type"}), 400
    if visibility not in {"private", "friends", "community", "circle", "public"}:
        return jsonify({"ok": False, "error": "Invalid visibility"}), 400
    visibility = _normalize_visibility(visibility)
    if mood_tag and mood_tag not in {"happy", "neutral", "lonely"}:
        return jsonify({"ok": False, "error": "Invalid mood tag"}), 400
    if not title:
        return jsonify({"ok": False, "error": "Title is required"}), 400

    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scrapbook_entries (owner_user_id, related_user_id, circle_title, entry_type, title, content, visibility, featured, campaign_tag, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, related_user_id, circle_title or None, entry_type, title, content or None, visibility, featured, campaign_tag or None, _utc_now_iso()),
    )
    cur.execute(
        "UPDATE scrapbook_entries SET mood_tag = ?, location = ? WHERE id = ?",
        (mood_tag or None, location or None, cur.lastrowid),
    )
    entry_id = cur.lastrowid
    if media_url:
        media_type = "audio" if media_url.lower().endswith((".mp3", ".wav", ".ogg")) else "image"
        cur.execute(
            """
            INSERT INTO scrapbook_media (entry_id, media_type, file_path, uploaded_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entry_id, media_type, media_url, user_id, _utc_now_iso()),
        )
    conn.commit()
    conn.close()
    # Update streaks
    conn = _get_main_conn()
    cur = conn.cursor()
    now = datetime.utcnow()
    week_start = _week_start(now)
    prev = cur.execute(
        "SELECT total_entries, weekly_streak, last_entry_at FROM scrapbook_stats WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    total_entries = (prev["total_entries"] if prev else 0) + 1
    weekly_streak = prev["weekly_streak"] if prev else 0
    last_entry_at = prev["last_entry_at"] if prev else None
    if not last_entry_at:
        weekly_streak = 1
    else:
        try:
            last_dt = datetime.fromisoformat(last_entry_at)
            if last_dt < week_start:
                weekly_streak += 1
        except Exception:
            weekly_streak = 1
    cur.execute(
        "INSERT OR REPLACE INTO scrapbook_stats (user_id, total_entries, weekly_streak, last_entry_at) VALUES (?, ?, ?, ?)",
        (user_id, total_entries, weekly_streak, now.isoformat()),
    )
    conn.commit()
    conn.close()
    _add_notification(user_id, "scrapbook", f"Memory saved: {title}.", {"entry_id": entry_id})
    if visibility == "community":
        _check_and_unlock_titles(user_id)
    return jsonify({"ok": True, "id": entry_id})


@app.post("/api/storybook/create")
def api_storybook_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    place = (data.get("place") or "").strip()
    event = (data.get("event") or "").strip()
    feeling = (data.get("feeling") or "").strip()
    lesson = (data.get("lesson") or "").strip()
    media_url = (data.get("media_url") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Title is required"}), 400

    parts = []
    if place:
        parts.append(f"This story took place at {place}.")
    if event:
        parts.append(f"On that day, {event}.")
    if feeling:
        parts.append(f"I felt {feeling}.")
    if lesson:
        parts.append(f"The lesson I want to share is: {lesson}.")
    content = " ".join(parts).strip()

    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO storybook_drafts (user_id, title, place, event, feeling, lesson, media_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, title, place or None, event or None, feeling or None, lesson or None, media_url or None, _utc_now_iso()),
    )
    cur.execute(
        """
        INSERT INTO scrapbook_entries (owner_user_id, related_user_id, circle_title, entry_type, title, content, visibility, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, None, None, "storybook", title, content or None, "private", _utc_now_iso()),
    )
    entry_id = cur.lastrowid
    if media_url:
        cur.execute(
            """
            INSERT INTO scrapbook_media (entry_id, media_type, file_path, uploaded_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entry_id, "image", media_url, user_id, _utc_now_iso()),
        )
    conn.commit()
    conn.close()
    _add_notification(user_id, "scrapbook", f"Storybook saved: {title}.", {"entry_id": entry_id})
    return jsonify({"ok": True, "id": entry_id})


@app.post("/api/scrapbook/pin")
def api_scrapbook_pin():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    entry_id = data.get("entry_id")
    pinned = 1 if data.get("pinned") else 0
    if not entry_id:
        return jsonify({"ok": False, "error": "entry_id required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE scrapbook_entries SET pinned = ? WHERE id = ? AND owner_user_id = ?",
        (pinned, entry_id, user_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/scrapbook/reactions")
def api_scrapbook_reaction():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    data = request.get_json(silent=True) or {}
    entry_id = data.get("entry_id")
    reaction = (data.get("reaction") or "").strip()
    if reaction not in {"heart", "star", "thumbs"}:
        return jsonify({"ok": False, "error": "Invalid reaction"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    entry = cur.execute(
        "SELECT id, owner_user_id, visibility FROM scrapbook_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if not entry:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404
    if not _can_view_scrapbook_entry(user_id, entry["owner_user_id"], entry["visibility"]):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    cur.execute(
        "INSERT INTO scrapbook_reactions (entry_id, user_id, reaction_type, created_at) VALUES (?, ?, ?, ?)",
        (entry_id, user_id, reaction, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.get("/api/scrapbook/comments")
def api_scrapbook_comments():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    entry_id = request.args.get("entry_id")
    if not entry_id:
        return jsonify({"ok": False, "error": "entry_id required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    entry = cur.execute(
        "SELECT id, owner_user_id, visibility FROM scrapbook_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if not entry:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404
    if not _can_view_scrapbook_entry(user_id, entry["owner_user_id"], entry["visibility"]):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    rows = cur.execute(
        "SELECT id, entry_id, user_id, comment_text, created_at FROM scrapbook_comments WHERE entry_id = ? ORDER BY id DESC LIMIT 50",
        (entry_id,),
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "comments": [dict(r) for r in rows]})


@app.post("/api/scrapbook/comments")
def api_scrapbook_comment_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    data = request.get_json(silent=True) or {}
    entry_id = data.get("entry_id")
    text = (data.get("text") or "").strip()
    if not entry_id or not text:
        return jsonify({"ok": False, "error": "entry_id and text required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    entry = cur.execute(
        "SELECT id, owner_user_id, visibility FROM scrapbook_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if not entry:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404
    if not _can_view_scrapbook_entry(user_id, entry["owner_user_id"], entry["visibility"]):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    cur.execute(
        "INSERT INTO scrapbook_comments (entry_id, user_id, comment_text, created_at) VALUES (?, ?, ?, ?)",
        (entry_id, user_id, text, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.get("/api/scrapbook/settings")
def api_scrapbook_settings():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    return jsonify({"ok": True, "settings": _get_scrapbook_settings(user_id)})


@app.post("/api/scrapbook/settings")
def api_scrapbook_settings_update():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or "").strip().lower()
    view = (data.get("view") or "").strip().lower()
    if theme and theme not in {"minimal", "vintage", "kampung", "modern"}:
        return jsonify({"ok": False, "error": "Invalid theme"}), 400
    if view and view not in {"book", "timeline", "grid"}:
        return jsonify({"ok": False, "error": "Invalid view"}), 400
    _set_scrapbook_settings(user_id, theme or None, view or None)
    return jsonify({"ok": True})


@app.get("/api/scrapbook/suggest")
def api_scrapbook_suggest():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    # Placeholder AI suggestion
    title = "Shared Moments"
    content = "You and a friend shared meaningful stories this week. Would you like to save this memory?"
    return jsonify({"ok": True, "suggestion": {"title": title, "content": content, "entry_type": "chat"}})


@app.get("/api/scrapbook/family_viewer")
def api_scrapbook_family_viewer():
    access_key = (request.args.get("key") or "").strip()
    if not access_key:
        return jsonify({"ok": False, "error": "Missing key"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    viewer = cur.execute(
        "SELECT * FROM trusted_viewers WHERE access_key = ?",
        (access_key,),
    ).fetchone()
    if not viewer:
        conn.close()
        return jsonify({"ok": False, "error": "Invalid key"}), 404
    owner_id = viewer["owner_user_id"]
    latest_checkin = cur.execute(
        "SELECT mood, created_at FROM mood_checkins WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (owner_id,),
    ).fetchone()
    activity = {
        "circles": cur.execute("SELECT COUNT(*) AS c FROM circle_signups WHERE user_id = ?", (owner_id,)).fetchone()["c"],
        "challenges": cur.execute("SELECT COUNT(*) AS c FROM challenge_entries WHERE user_id = ?", (owner_id,)).fetchone()["c"],
    }
    conn.close()
    return jsonify(
        {
            "ok": True,
            "mood": dict(latest_checkin) if latest_checkin else None,
            "activity": activity,
            "alerts": [],
        }
    )


def _save_uploaded_image(file_storage, prefix: str, user_id: int) -> str:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Invalid filename")
    ext = Path(filename).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        raise ValueError("Unsupported file type")
    safe_name = f"{prefix}_{user_id}_{int(time.time())}{ext}"
    path = UPLOADS_DIR / safe_name
    file_storage.save(path)
    return f"/static/uploads/{safe_name}"


@app.post("/api/profile/avatar")
def api_profile_avatar():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403

    file = request.files.get("avatar")
    if not file:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    try:
        url = _save_uploaded_image(file, "avatar", user_id)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    _set_user_setting(user_id, "avatar_url", url)
    db.session.commit()
    return jsonify({"ok": True, "url": url})


@app.post("/api/profile/banner")
def api_profile_banner():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403

    file = request.files.get("banner")
    if not file:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    try:
        url = _save_uploaded_image(file, "banner", user_id)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    _set_user_setting(user_id, "banner_url", url)
    db.session.commit()
    return jsonify({"ok": True, "url": url})


@app.post("/api/report")
@login_required
def api_report():
    if not _validate_csrf():
        return jsonify({"ok": False, "error": "CSRF validation failed"}), 403
    reporter_id = int(g.current_user_id)
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    if len(reason) < REPORT_REASON_MIN or len(reason) > REPORT_REASON_MAX:
        return jsonify({"ok": False, "error": f"Reason must be {REPORT_REASON_MIN}..{REPORT_REASON_MAX} characters"}), 400

    reported_id = _coerce_int(data.get("reported_id") or data.get("target_user_id"))
    if reported_id is not None and reported_id == reporter_id:
        return jsonify({"ok": False, "error": "Cannot report yourself"}), 400

    allowed, retry_after = _social_action_allowed(reporter_id, "report", reported_id, cooldown_seconds=30)
    if not allowed:
        return jsonify({"ok": False, "error": "Please wait before sending another report", "retry_after": retry_after}), 429

    incident_date = (data.get("incident_date") or datetime.utcnow().date().isoformat()).strip()
    details = (data.get("details") or "").strip()
    now = _utc_now_iso()

    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reports (user_id, reporter_id, reported_id, reason, incident_date, details, status, created_at, context_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (reporter_id, reporter_id, reported_id, reason, incident_date, details or None, "pending", now, "profile" if reported_id else "general"),
    )
    conn.commit()
    conn.close()
    _log_audit("safety", "report", reporter_id, {"reported_id": reported_id, "reason": reason})
    return jsonify({"ok": True})


#Join Circle
@app.post("/api/circle_signup")
def api_circle_signup():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    time = (data.get("time") or "").strip()
    duration = (data.get("duration") or "").strip()

    if not title:
        return jsonify({"ok": False, "error": "Missing circle title"}), 400

    signup = CircleSignup(
        user_id=user_id,
        circle_title=title,
        circle_time=time,
        circle_duration=duration,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", ""),
    )
    db.session.add(signup)
    db.session.commit()
    _log_audit("learning_circle", "join", user_id, {"title": title})
    _increment_quest_progress(user_id, 1)
    _increment_quest_progress(user_id, 5)
    _add_notification(user_id, "learning_circle", f"Joined learning circle: {title}.", {"title": title})
    points = 3 if _is_partner_circle(title) else 2
    _add_safety_event(user_id, "circle_join", points, f"Joined circle: {title}")
    _record_volunteer_hours(user_id, "learning_circle", signup.id, _hours_from_text(duration, default_hours=2.0), f"Learning circle: {title}")
    _check_and_unlock_titles(user_id)
    return jsonify({"ok": True, "id": signup.id})


@app.post("/api/circle_leave")
def api_circle_leave():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Missing circle title"}), 400

    CircleSignup.query.filter_by(user_id=user_id, circle_title=title).delete()
    db.session.commit()
    _log_audit("learning_circle", "leave", user_id, {"title": title})
    return jsonify({"ok": True})


@app.get("/api/circle_signups")
def api_circle_signups():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    rows = CircleSignup.query.filter_by(user_id=user_id).all()
    return jsonify(
        {
            "ok": True,
            "circles": [
                {
                    "title": r.circle_title,
                    "time": r.circle_time,
                    "duration": r.circle_duration,
                }
                for r in rows
            ],
        }
    )


@app.get("/api/learning-circles/sessions")
def api_learning_circle_sessions():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    rows = conn.execute(
        """
        SELECT id, circle_title, partner_id, start_time, end_time, capacity, host_type, host_name, host_logo_path, topic_tags_json, created_at
        FROM circle_sessions
        ORDER BY start_time ASC, id DESC
        LIMIT 200
        """
    ).fetchall()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "sessions": [
                {
                    "id": r["id"],
                    "circle_title": r["circle_title"],
                    "partner_id": r["partner_id"],
                    "start_time": r["start_time"],
                    "end_time": r["end_time"],
                    "capacity": r["capacity"],
                    "host_type": (r["host_type"] or "user"),
                    "host_name": r["host_name"] or "",
                    "host_logo_path": r["host_logo_path"] or "",
                    "topic_tags": _safe_json(r["topic_tags_json"] or "[]", []),
                    "host_badge": _organiser_badge(r["host_type"] or "community"),
                    "created_at": r["created_at"],
                }
                for r in rows
            ],
        }
    )


@app.post("/api/learning-circles/sessions")
def api_learning_circle_session_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    circle_title = (data.get("circle_title") or "").strip()
    start_time = (data.get("start_time") or "").strip()
    end_time = (data.get("end_time") or "").strip()
    if not circle_title or not start_time or not end_time:
        return jsonify({"ok": False, "error": "circle_title, start_time and end_time are required"}), 400
    host_type = (data.get("host_type") or "user").strip().lower()
    if host_type not in {"user", "government", "corporate", "community"}:
        host_type = "user"
    if not _require_admin() and host_type == "user":
        host_type = "community"
    host_name = (data.get("host_name") or "").strip() or "Community Host"
    host_logo_path = (data.get("host_logo_path") or "").strip() or None
    topic_tags = data.get("topic_tags") or []
    capacity = int(data.get("capacity") or 20)
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO circle_sessions
            (circle_title, partner_id, start_time, end_time, capacity, host_type, host_name, host_logo_path, topic_tags_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            circle_title,
            data.get("partner_id"),
            start_time,
            end_time,
            max(1, capacity),
            host_type,
            host_name,
            host_logo_path,
            json.dumps(topic_tags),
            _utc_now_iso(),
        ),
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "session_id": session_id}), 201


@app.get("/api/challenges/current")
def api_challenge_current():
    user_id = _require_login()
    challenge = _get_current_challenge()
    if not challenge:
        return jsonify({"ok": False, "error": "No challenge available"}), 404

    try:
        requested_limit = int((request.args.get("limit") or "25").strip())
    except Exception:
        requested_limit = 25
    entry_limit = max(5, min(50, requested_limit))
    total_entries = _count_challenge_entries(challenge["id"])
    entries = _list_challenge_entries(challenge["id"], limit=entry_limit)
    has_submitted = False
    challenges_completed = 0
    user_points = 0
    if user_id:
        conn = _get_main_conn()
        row = conn.execute(
            "SELECT id FROM challenge_entries WHERE challenge_id = ? AND user_id = ? ORDER BY id ASC LIMIT 1",
            (challenge["id"], user_id),
        ).fetchone()
        completed_row = conn.execute(
            "SELECT COUNT(*) AS c FROM challenge_entries WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        has_submitted = bool(row)
        challenges_completed = int(completed_row["c"] if completed_row else 0)
        user_points, _ = _get_user_points(user_id)
    out_entries = []
    for e in entries:
        comments = _list_entry_comments(e["id"], limit=3)
        likes_count = _count_challenge_entry_likes(e["id"])
        liked = False
        if user_id:
            liked = _has_challenge_entry_like(e["id"], user_id)
        out_entries.append(
            {
                "id": e["id"],
                "author_name": e["author_name"],
                "content": e["content"],
                "image_url": e["image_url"],
                "created_at": e["created_at"],
                "likes": likes_count,
                "liked": liked,
                "can_edit": bool(user_id and e["user_id"] == user_id),
                "comments": [
                    {
                        "id": c["id"],
                        "author_name": c["author_name"],
                        "content": c["content"],
                        "created_at": c["created_at"],
                    }
                    for c in comments
                ],
            }
        )

    return jsonify(
        {
            "ok": True,
            "challenge": {
                "id": challenge["id"],
                "title": challenge["title"],
                "description": challenge["description"],
                "reward_points": challenge["reward_points"],
                "week_label": challenge["week_label"],
            },
            "total_entries": total_entries,
            "display_limit": entry_limit,
            "has_submitted": has_submitted,
            "user_points": user_points,
            "challenges_completed": challenges_completed,
            "entries": out_entries,
        }
    )


@app.post("/api/challenges/entries")
def api_create_challenge_entry():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Content is required"}), 400

    challenge = _get_current_challenge()
    if not challenge:
        return jsonify({"ok": False, "error": "No challenge available"}), 404

    user = db.session.get(User, user_id)
    author_name = user.full_name if user else "User"

    conn = _get_main_conn()
    cur = conn.cursor()
    existing = cur.execute(
        "SELECT id FROM challenge_entries WHERE challenge_id = ? AND user_id = ? ORDER BY id ASC LIMIT 1",
        (challenge["id"], user_id),
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"ok": False, "error": "You already submitted for this weekly challenge."}), 409
    try:
        cur.execute(
            "INSERT INTO challenge_entries (challenge_id, user_id, author_name, content, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (challenge["id"], user_id, author_name, content, image_url or None, _utc_now_iso()),
        )
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "You already submitted for this weekly challenge."}), 409

    reward_points = int(challenge["reward_points"] or 0)
    if reward_points > 0:
        cur.execute(
            "UPDATE users SET total_points = COALESCE(total_points, 0) + ?, available_points = COALESCE(available_points, 0) + ? WHERE id = ?",
            (reward_points, reward_points, user_id),
        )

    conn.commit()
    conn.close()
    updated_total_points, updated_available_points = _get_user_points(user_id)
    _log_audit("weekly_challenge", "entry", user_id, {"challenge_id": challenge["id"]})
    _add_notification(
        user_id,
        "weekly_challenge",
        f"Submitted a weekly challenge entry: {challenge['title']} (+{reward_points} pts).",
        {"challenge_id": challenge["id"], "reward_points": reward_points},
    )
    return jsonify(
        {
            "ok": True,
            "reward_points": reward_points,
            "total_points": updated_total_points,
            "available_points": updated_available_points,
        }
    )


@app.post("/api/challenges/entries/<int:entry_id>/comments")
def api_create_challenge_comment(entry_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Content is required"}), 400

    user = db.session.get(User, user_id)
    author_name = user.full_name if user else "User"

    conn = _get_main_conn()
    cur = conn.cursor()
    existing = cur.execute(
        "SELECT id, user_id, author_name FROM challenge_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404

    cur.execute(
        "INSERT INTO challenge_comments (entry_id, user_id, author_name, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (entry_id, user_id, author_name, content, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    _log_audit("weekly_challenge", "comment", user_id, {"entry_id": entry_id})
    if existing["user_id"] and existing["user_id"] != user_id:
        _add_notification(
            existing["user_id"],
            "weekly_challenge_comment",
            f"{author_name} commented on your challenge entry.",
            {"entry_id": entry_id},
        )
    return jsonify({"ok": True})


@app.post("/api/challenges/entries/<int:entry_id>/like")
def api_challenge_like(entry_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    conn = _get_main_conn()
    cur = conn.cursor()
    entry = cur.execute(
        "SELECT user_id FROM challenge_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if not entry:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404

    existing = cur.execute(
        "SELECT 1 FROM challenge_entry_likes WHERE entry_id = ? AND user_id = ?",
        (entry_id, user_id),
    ).fetchone()
    liked = False
    if existing:
        cur.execute(
            "DELETE FROM challenge_entry_likes WHERE entry_id = ? AND user_id = ?",
            (entry_id, user_id),
        )
        _log_audit("weekly_challenge", "like_remove", user_id, {"entry_id": entry_id})
        liked = False
    else:
        cur.execute(
            "INSERT INTO challenge_entry_likes (entry_id, user_id) VALUES (?, ?)",
            (entry_id, user_id),
        )
        _log_audit("weekly_challenge", "like_add", user_id, {"entry_id": entry_id})
        liked = True
    conn.commit()
    likes = cur.execute(
        "SELECT COUNT(*) AS c FROM challenge_entry_likes WHERE entry_id = ?",
        (entry_id,),
    ).fetchone()["c"]
    conn.close()
    return jsonify({"ok": True, "likes": likes, "liked": liked})


@app.put("/api/challenges/entries/<int:entry_id>")
def api_challenge_edit(entry_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    image_url = (data.get("image_url") or "").strip() or None
    if not content:
        return jsonify({"ok": False, "error": "Content is required"}), 400

    conn = _get_main_conn()
    cur = conn.cursor()
    entry = cur.execute(
        "SELECT user_id FROM challenge_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if not entry:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404
    if entry["user_id"] != user_id:
        conn.close()
        return jsonify({"ok": False, "error": "Not authorised"}), 403
    cur.execute(
        "UPDATE challenge_entries SET content = ?, image_url = ? WHERE id = ?",
        (content, image_url, entry_id),
    )
    conn.commit()
    conn.close()
    _log_audit("weekly_challenge", "entry_edit", user_id, {"entry_id": entry_id})
    return jsonify({"ok": True})


@app.delete("/api/challenges/entries/<int:entry_id>")
def api_challenge_delete(entry_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    entry = cur.execute(
        """SELECT e.user_id, e.challenge_id, COALESCE(w.reward_points, 0) AS reward_points
           FROM challenge_entries e
           LEFT JOIN weekly_challenges w ON w.id = e.challenge_id
           WHERE e.id = ?""",
        (entry_id,),
    ).fetchone()
    if not entry:
        conn.close()
        return jsonify({"ok": False, "error": "Entry not found"}), 404
    if entry["user_id"] != user_id:
        conn.close()
        return jsonify({"ok": False, "error": "Not authorised"}), 403

    reward_points = max(0, int(entry["reward_points"] or 0))
    if reward_points > 0:
        cur.execute(
            """UPDATE users
               SET total_points = CASE
                   WHEN COALESCE(total_points, 0) >= ? THEN COALESCE(total_points, 0) - ?
                   ELSE 0
               END,
               available_points = CASE
                   WHEN COALESCE(available_points, 0) >= ? THEN COALESCE(available_points, 0) - ?
                   ELSE 0
               END
               WHERE id = ?""",
            (reward_points, reward_points, reward_points, reward_points, user_id),
        )

    cur.execute("DELETE FROM challenge_entry_likes WHERE entry_id = ?", (entry_id,))
    cur.execute("DELETE FROM challenge_comments WHERE entry_id = ?", (entry_id,))
    cur.execute("DELETE FROM challenge_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

    updated_total_points, updated_available_points = _get_user_points(user_id)
    _log_audit("weekly_challenge", "entry_delete", user_id, {"entry_id": entry_id})
    return jsonify(
        {
            "ok": True,
            "deducted_points": reward_points,
            "total_points": updated_total_points,
            "available_points": updated_available_points,
        }
    )


@app.post("/api/challenges/entries/<int:entry_id>/delete")
def api_challenge_delete_post(entry_id: int):
    # Backward-compatible delete endpoint for clients that still POST.
    return api_challenge_delete(entry_id)


def _save_user_meetup_preferences(user_id: int, stations: list[str]):
    conn = _get_main_conn()
    cur = conn.cursor()
    cleaned = []
    seen = set()
    for station in stations or []:
        value = str(station).strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)

    cur.execute("DELETE FROM user_meetup_preferences WHERE user_id = ?", (user_id,))
    if cleaned:
        cur.executemany(
            "INSERT OR IGNORE INTO user_meetup_preferences (user_id, station_name) VALUES (?, ?)",
            [(user_id, station) for station in cleaned],
        )
    conn.commit()
    conn.close()


@app.post("/api/onboarding")
def api_onboarding():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}

    member_type = (data.get("memberType") or "").strip()
    interests = data.get("interests") or []
    skills_teach = data.get("skills_teach") or []
    skills_learn = data.get("skills_learn") or []
    languages = data.get("languages") or []
    language_proficiency = data.get("language_proficiency") or {}
    days = data.get("days") or []
    time = data.get("time") or []
    stations = data.get("stations") or []
    landmarks = data.get("landmarks") or []

    if not isinstance(interests, list):
        interests = []
    if not isinstance(skills_teach, list):
        skills_teach = []
    if not isinstance(skills_learn, list):
        skills_learn = []
    if not isinstance(languages, list):
        languages = []
    if not isinstance(language_proficiency, dict):
        language_proficiency = {}

    languages = _save_user_languages(user_id, languages)
    cleaned_language_proficiency = {}
    for language in languages:
        prof = str(language_proficiency.get(language, "Beginner")).strip() or "Beginner"
        if prof not in {"Beginner", "Intermediate", "Advanced", "Native"}:
            prof = "Beginner"
        cleaned_language_proficiency[language] = prof

    if len(interests) < 1:
        return jsonify({"ok": False, "error": "Please select at least 1 interest."}), 400

    # Update a field on the user table for quick access
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "User not found"}), 404

    if member_type:
        u.member_type = member_type

    payload = {
        "memberType": member_type,
        "interests": interests,
        "skills_teach": skills_teach,
        "skills_learn": skills_learn,
        "languages": languages,
        "language_proficiency": cleaned_language_proficiency,
        "days": days,
        "time": time,
        "stations": stations,
        "landmarks": landmarks,
    }

    setting = UserSetting.query.filter_by(user_id=user_id, key="onboarding").first()
    if setting is None:
        setting = UserSetting(user_id=user_id, key="onboarding", value=json.dumps(payload))
        db.session.add(setting)
    else:
        setting.value = json.dumps(payload)

    location_value = ", ".join(stations) if stations else ""
    location_setting = UserSetting.query.filter_by(user_id=user_id, key="location_name").first()
    if location_setting is None:
        location_setting = UserSetting(user_id=user_id, key="location_name", value=location_value)
        db.session.add(location_setting)
    else:
        location_setting.value = location_value

    skills_teach_setting = UserSetting.query.filter_by(user_id=user_id, key="skills_teach").first()
    if skills_teach_setting is None:
        skills_teach_setting = UserSetting(user_id=user_id, key="skills_teach", value=json.dumps(skills_teach))
        db.session.add(skills_teach_setting)
    else:
        skills_teach_setting.value = json.dumps(skills_teach)

    skills_learn_setting = UserSetting.query.filter_by(user_id=user_id, key="skills_learn").first()
    if skills_learn_setting is None:
        skills_learn_setting = UserSetting(user_id=user_id, key="skills_learn", value=json.dumps(skills_learn))
        db.session.add(skills_learn_setting)
    else:
        skills_learn_setting.value = json.dumps(skills_learn)

    db.session.commit()
    _save_user_meetup_preferences(user_id, stations)
    return jsonify({"ok": True})


@app.get("/api/safe_locations")
def api_safe_locations():
    stations_raw = (request.args.get("stations") or "").strip()
    if not stations_raw:
        return jsonify([])

    stations = []
    seen = set()
    for token in stations_raw.split(","):
        station = token.strip()
        if not station:
            continue
        key = station.casefold()
        if key in seen:
            continue
        seen.add(key)
        stations.append(station)

    if not stations:
        return jsonify([])

    placeholders = ",".join(["?"] * len(stations))
    conn = _get_main_conn()
    rows = conn.execute(
        f"""
        SELECT place_name, venue_type, address, lat, lng, station_name, walking_mins
          FROM safe_locations
         WHERE station_name IN ({placeholders})
         ORDER BY station_name, walking_mins ASC, place_name ASC
        """,
        tuple(stations),
    ).fetchall()
    conn.close()

    payload = [
        {
            "place_name": row["place_name"],
            "venue_type": row["venue_type"],
            "address": row["address"] or "",
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "station_name": row["station_name"],
            "walking_mins": row["walking_mins"],
        }
        for row in rows
    ]
    return jsonify(payload)


@app.get("/api/senior_friendly_spots")
def api_senior_friendly_spots():
    stations_raw = (request.args.get("stations") or "").strip()
    if not stations_raw:
        return jsonify([])
    stations = []
    seen = set()
    for token in stations_raw.split(","):
        station = token.strip()
        if not station:
            continue
        key = station.casefold()
        if key in seen:
            continue
        seen.add(key)
        stations.append(station)
    return jsonify(_safe_locations_for_stations(stations, limit=80))


@app.get("/api/hangouts")
def api_hangouts_list():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    category = (request.args.get("category") or "").strip().lower()
    conn = _get_main_conn()
    cur = conn.cursor()
    if category:
        rows = cur.execute(
            """
            SELECT id, user_id, name, category, description, mrt_nearby, accessibility_json, lat, lng, photo_path, source_type, is_verified, verified_label, created_at
            FROM hangout_spots
            WHERE category = ?
            ORDER BY id DESC
            LIMIT 300
            """,
            (category,),
        ).fetchall()
    else:
        rows = cur.execute(
            """
            SELECT id, user_id, name, category, description, mrt_nearby, accessibility_json, lat, lng, photo_path, source_type, is_verified, verified_label, created_at
            FROM hangout_spots
            ORDER BY id DESC
            LIMIT 300
            """
        ).fetchall()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "spots": [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "name": r["name"],
                    "category": r["category"],
                    "description": r["description"] or "",
                    "mrt_nearby": r["mrt_nearby"] or "",
                    "accessibility": _safe_json(r["accessibility_json"] or "{}", {}),
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "photo_path": r["photo_path"] or "",
                    "source_type": r["source_type"] or "user",
                    "is_verified": bool(r["is_verified"]),
                    "verified_label": r["verified_label"] or "",
                    "created_at": r["created_at"],
                }
                for r in rows
            ],
            "helper_text": "Senior-Friendly means seating, toilets nearby, accessible routes, well-lit, quieter environment. It does NOT imply other places are unsafe.",
        }
    )


@app.post("/api/hangouts")
def api_hangouts_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "community_centre").strip().lower()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    description = (data.get("description") or "").strip()
    mrt_nearby = (data.get("mrt_nearby") or "").strip()
    accessibility = data.get("accessibility") or {}
    lat = data.get("lat")
    lng = data.get("lng")
    photo_path = (data.get("photo_path") or "").strip() or None
    source_type = (data.get("source_type") or "user").strip().lower()
    if source_type not in {"user", "government", "community", "corporate"}:
        source_type = "user"
    is_verified = 1 if bool(data.get("is_verified")) and _require_admin() else 0
    verified_label = (data.get("verified_label") or "").strip() or None
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO hangout_spots (user_id, name, category, description, mrt_nearby, accessibility_json, lat, lng, photo_path, source_type, is_verified, verified_label, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, name, category, description or None, mrt_nearby or None, json.dumps(accessibility), lat, lng, photo_path, source_type, is_verified, verified_label, _utc_now_iso()),
    )
    conn.commit()
    spot_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": spot_id}), 201


@app.put("/api/hangouts/<int:spot_id>")
def api_hangouts_update(spot_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT user_id FROM hangout_spots WHERE id = ?", (spot_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Spot not found"}), 404
    if int(row["user_id"]) != int(user_id):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    cur.execute(
        """
        UPDATE hangout_spots
        SET name = COALESCE(?, name),
            category = COALESCE(?, category),
            description = COALESCE(?, description),
            mrt_nearby = COALESCE(?, mrt_nearby),
            accessibility_json = COALESCE(?, accessibility_json),
            lat = COALESCE(?, lat),
            lng = COALESCE(?, lng),
            photo_path = COALESCE(?, photo_path),
            source_type = COALESCE(?, source_type),
            is_verified = COALESCE(?, is_verified),
            verified_label = COALESCE(?, verified_label)
        WHERE id = ?
        """,
        (
            (data.get("name") or "").strip() or None,
            (data.get("category") or "").strip().lower() or None,
            (data.get("description") or "").strip() or None,
            (data.get("mrt_nearby") or "").strip() or None,
            json.dumps(data.get("accessibility")) if data.get("accessibility") is not None else None,
            data.get("lat"),
            data.get("lng"),
            (data.get("photo_path") or "").strip() or None,
            (data.get("source_type") or "").strip().lower() or None,
            (1 if bool(data.get("is_verified")) else 0) if _require_admin() and ("is_verified" in data) else None,
            (data.get("verified_label") or "").strip() or None,
            spot_id,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.delete("/api/hangouts/<int:spot_id>")
def api_hangouts_delete(spot_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT user_id FROM hangout_spots WHERE id = ?", (spot_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Spot not found"}), 404
    if int(row["user_id"]) != int(user_id):
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    cur.execute("DELETE FROM hangout_spots WHERE id = ?", (spot_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


def _meetup_other_user(meetup_row, user_id: int) -> int | None:
    if int(meetup_row["user1_id"]) == int(user_id):
        return int(meetup_row["user2_id"])
    if int(meetup_row["user2_id"]) == int(user_id):
        return int(meetup_row["user1_id"])
    return None


@app.post("/api/meetups")
def api_meetups_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    target_user_id = data.get("target_user_id")
    meetup_time = (data.get("meetup_time") or "").strip()
    spot_id = data.get("spot_id")
    chat_id = (data.get("chat_id") or "").strip()
    try:
        target_user_id = int(target_user_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "target_user_id is required"}), 400
    if target_user_id == user_id:
        return jsonify({"ok": False, "error": "Cannot create meetup with yourself"}), 400
    if _is_blocked_between(user_id, target_user_id):
        return jsonify({"ok": False, "error": "Cannot create meetup due to privacy settings"}), 403
    if not _are_friends(user_id, target_user_id):
        return jsonify({"ok": False, "error": "You can only create meetups with friends"}), 403
    if not meetup_time:
        return jsonify({"ok": False, "error": "meetup_time is required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO meetups (user1_id, user2_id, spot_id, meetup_time, status, created_at)
        VALUES (?, ?, ?, ?, 'proposed', ?)
        """,
        (user_id, target_user_id, spot_id, meetup_time, _utc_now_iso()),
    )
    meetup_id = cur.lastrowid
    conn.commit()
    conn.close()
    if chat_id:
        cconn = _get_chat_conn()
        cconn.execute(
            "INSERT INTO messages (chat_id, sender, text, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, "youth", f"__MEETUP__:{meetup_id}", _utc_now_iso()),
        )
        cconn.commit()
        cconn.close()
    _add_notification(target_user_id, "meetup", "New meetup proposed.", {"meetup_id": meetup_id})
    return jsonify({"ok": True, "meetup_id": meetup_id}), 201


@app.get("/api/meetups")
def api_meetups_list():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    rows = conn.execute(
        """
        SELECT id, user1_id, user2_id, spot_id, meetup_time, status, checked_in_user1, checked_in_user2, created_at
        FROM meetups
        WHERE user1_id = ? OR user2_id = ?
        ORDER BY meetup_time DESC, id DESC
        LIMIT 200
        """,
        (user_id, user_id),
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "meetups": [dict(r) for r in rows]})


@app.get("/api/meetups/<int:meetup_id>")
def api_meetup_detail(meetup_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    row = conn.execute(
        """
        SELECT m.*, h.name AS spot_name, h.category AS spot_category, h.mrt_nearby
        FROM meetups m
        LEFT JOIN hangout_spots h ON h.id = m.spot_id
        WHERE m.id = ?
        """,
        (meetup_id,),
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "Meetup not found"}), 404
    if int(user_id) not in {int(row["user1_id"]), int(row["user2_id"])} and not _require_admin():
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    return jsonify(
        {
            "ok": True,
            "meetup": {
                "id": row["id"],
                "user1_id": row["user1_id"],
                "user2_id": row["user2_id"],
                "spot_id": row["spot_id"],
                "spot_name": row["spot_name"] or "",
                "spot_category": row["spot_category"] or "",
                "mrt_nearby": row["mrt_nearby"] or "",
                "meetup_time": row["meetup_time"],
                "status": row["status"],
                "checked_in_user1": row["checked_in_user1"],
                "checked_in_user2": row["checked_in_user2"],
                "created_at": row["created_at"],
            }
        }
    )


def _update_meetup_status(meetup_id: int, user_id: int, status: str, meetup_time: str | None = None):
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM meetups WHERE id = ?", (meetup_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Meetup not found"}), 404
    if int(user_id) not in {int(row["user1_id"]), int(row["user2_id"])}:
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    other_user = _meetup_other_user(row, user_id)
    if status == "rescheduled" and meetup_time:
        cur.execute("UPDATE meetups SET status = ?, meetup_time = ? WHERE id = ?", (status, meetup_time, meetup_id))
    else:
        cur.execute("UPDATE meetups SET status = ? WHERE id = ?", (status, meetup_id))
    conn.commit()
    conn.close()
    if other_user:
        _add_notification(other_user, "meetup", f"Meetup status updated: {status}", {"meetup_id": meetup_id, "status": status})
    return jsonify({"ok": True, "status": status})


@app.post("/api/meetups/<int:meetup_id>/confirm")
def api_meetup_confirm(meetup_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    return _update_meetup_status(meetup_id, user_id, "confirmed")


@app.post("/api/meetups/<int:meetup_id>/reschedule")
def api_meetup_reschedule(meetup_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    meetup_time = (data.get("meetup_time") or "").strip()
    if not meetup_time:
        return jsonify({"ok": False, "error": "meetup_time is required"}), 400
    return _update_meetup_status(meetup_id, user_id, "rescheduled", meetup_time)


@app.post("/api/meetups/<int:meetup_id>/cancel")
def api_meetup_cancel(meetup_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    return _update_meetup_status(meetup_id, user_id, "cancelled")


@app.post("/api/meetups/<int:meetup_id>/checkin")
def api_meetup_checkin(meetup_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM meetups WHERE id = ?", (meetup_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Meetup not found"}), 404
    if int(user_id) not in {int(row["user1_id"]), int(row["user2_id"])}:
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    if not _is_checkin_window(row["meetup_time"]):
        conn.close()
        return jsonify({"ok": False, "error": "Check-in window closed"}), 400
    if int(user_id) == int(row["user1_id"]):
        cur.execute("UPDATE meetups SET checked_in_user1 = 1 WHERE id = ?", (meetup_id,))
    else:
        cur.execute("UPDATE meetups SET checked_in_user2 = 1 WHERE id = ?", (meetup_id,))
    conn.commit()
    conn.close()
    _apply_trust_delta(user_id, 2, "Meetup check-in completed")
    _add_notification(user_id, "meetup_checkin", "Check-in recorded.", {"meetup_id": meetup_id})
    return jsonify({"ok": True})


@app.post("/api/meetups/<int:meetup_id>/complete")
def api_meetup_complete(meetup_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    row = conn.execute("SELECT * FROM meetups WHERE id = ?", (meetup_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "Meetup not found"}), 404
    if int(user_id) not in {int(row["user1_id"]), int(row["user2_id"])}:
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    resp = _update_meetup_status(meetup_id, user_id, "completed")
    _record_volunteer_hours(int(row["user1_id"]), "meetup", meetup_id, 1.0, "Completed meetup")
    _record_volunteer_hours(int(row["user2_id"]), "meetup", meetup_id, 1.0, "Completed meetup")
    return resp


@app.post("/api/meetups/<int:meetup_id>/mark_no_show")
def api_meetup_no_show(meetup_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    row = conn.execute("SELECT * FROM meetups WHERE id = ?", (meetup_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "Meetup not found"}), 404
    if int(user_id) not in {int(row["user1_id"]), int(row["user2_id"])}:
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    target_user = int(row["user2_id"]) if int(user_id) == int(row["user1_id"]) else int(row["user1_id"])
    _update_meetup_status(meetup_id, user_id, "no_show")
    _apply_trust_delta(target_user, -10, "No-show on confirmed meetup")
    return jsonify({"ok": True})


@app.post("/api/reviews")
def api_reviews_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    meetup_id = data.get("meetup_id")
    rating = data.get("rating")
    comment = (data.get("comment") or "").strip()
    tags = data.get("tags") or []
    try:
        meetup_id = int(meetup_id)
        rating = int(rating)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "meetup_id and rating are required"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"ok": False, "error": "rating must be 1-5"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    meetup = cur.execute("SELECT * FROM meetups WHERE id = ?", (meetup_id,)).fetchone()
    if not meetup:
        conn.close()
        return jsonify({"ok": False, "error": "Meetup not found"}), 404
    if int(user_id) not in {int(meetup["user1_id"]), int(meetup["user2_id"])}:
        conn.close()
        return jsonify({"ok": False, "error": "Not allowed"}), 403
    if meetup["status"] != "completed" and not (int(meetup["checked_in_user1"]) or int(meetup["checked_in_user2"])):
        conn.close()
        return jsonify({"ok": False, "error": "Reviews are available after completion/check-in"}), 400
    reviewee_id = int(meetup["user2_id"]) if int(user_id) == int(meetup["user1_id"]) else int(meetup["user1_id"])
    try:
        cur.execute(
            "INSERT INTO reviews (meetup_id, reviewer_id, reviewee_id, rating, tags_json, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (meetup_id, user_id, reviewee_id, rating, json.dumps(tags), comment or None, _utc_now_iso()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "You already reviewed this meetup"}), 409
    conn.close()
    delta = (rating - 3) * 3
    if delta:
        _apply_trust_delta(reviewee_id, delta, f"Review rating {rating}")
    _refresh_user_rating(reviewee_id)
    _add_notification(reviewee_id, "review", "You received a new meetup review.", {"meetup_id": meetup_id, "rating": rating})
    return jsonify({"ok": True})


@app.get("/api/events")
def api_events_list():
    category = (request.args.get("category") or "").strip()
    conn = _get_main_conn()
    cur = conn.cursor()
    if category:
        rows = cur.execute("SELECT * FROM events WHERE category = ? ORDER BY start_time ASC, id DESC LIMIT 400", (category,)).fetchall()
    else:
        rows = cur.execute("SELECT * FROM events ORDER BY start_time ASC, id DESC LIMIT 400").fetchall()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "events": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "description": r["description"] or "",
                    "category": r["category"],
                    "tags": _safe_json(r["tags_json"] or "[]", []),
                    "start_time": r["start_time"],
                    "end_time": r["end_time"],
                    "location_name": r["location_name"],
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "capacity": r["capacity"],
                    "accessibility": _safe_json(r["accessibility_json"] or "{}", {}),
                    "created_by": r["created_by"],
                    "organiser_type": (r["organiser_type"] or "admin"),
                    "organiser_name": (r["organiser_name"] or "Re:Connect Admin"),
                    "verification_badge": (r["verification_badge"] or _organiser_badge(r["organiser_type"] or "admin")),
                    "organiser_logo_path": r["organiser_logo_path"] or "",
                    "created_at": r["created_at"],
                }
                for r in rows
            ],
        }
    )


@app.post("/api/events")
def api_events_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    category = (data.get("category") or "").strip()
    start_time = (data.get("start_time") or "").strip()
    location_name = (data.get("location_name") or "").strip()
    if not title or not category or not start_time or not location_name:
        return jsonify({"ok": False, "error": "title, category, start_time, location_name are required"}), 400
    description = (data.get("description") or "").strip()
    end_time = (data.get("end_time") or "").strip() or None
    tags = data.get("tags") or []
    lat = data.get("lat")
    lng = data.get("lng")
    capacity = int(data.get("capacity") or 0)
    accessibility = data.get("accessibility") or {}
    organiser_type = (data.get("organiser_type") or "admin").strip().lower()
    if organiser_type not in {"admin", "government", "corporate", "community"}:
        organiser_type = "admin"
    if not _require_admin() and organiser_type == "admin":
        return jsonify({"ok": False, "error": "Only admin can create admin-hosted events"}), 403
    organiser_name = (data.get("organiser_name") or "").strip() or ("Re:Connect Admin" if organiser_type == "admin" else "Partner Organiser")
    verification_badge = (data.get("verification_badge") or "").strip() or _organiser_badge(organiser_type)
    organiser_logo_path = (data.get("organiser_logo_path") or "").strip() or None
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO events (title, description, category, tags_json, start_time, end_time, location_name, lat, lng, capacity, accessibility_json, created_by, organiser_type, organiser_name, verification_badge, organiser_logo_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title, description or None, category, json.dumps(tags), start_time, end_time, location_name, lat, lng, capacity, json.dumps(accessibility), user_id, organiser_type, organiser_name, verification_badge, organiser_logo_path, _utc_now_iso()),
    )
    event_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "event_id": event_id}), 201


@app.post("/api/events/<int:event_id>/rsvp")
def api_events_rsvp(event_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "going").strip().lower()
    if status not in {"going", "interested", "cancelled"}:
        return jsonify({"ok": False, "error": "Invalid RSVP status"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone()
    if not exists:
        conn.close()
        return jsonify({"ok": False, "error": "Event not found"}), 404
    cur.execute(
        """
        INSERT INTO event_rsvps (event_id, user_id, status, checked_in, created_at)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(event_id, user_id) DO UPDATE SET status = excluded.status
        """,
        (event_id, user_id, status, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    _add_notification(user_id, "event_rsvp", f"RSVP updated: {status}", {"event_id": event_id})
    return jsonify({"ok": True})


@app.post("/api/events/<int:event_id>/checkin")
def api_events_checkin(event_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    event = cur.execute("SELECT id, start_time, end_time, title, organiser_type FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({"ok": False, "error": "Event not found"}), 404
    if not _is_checkin_window(event["start_time"]):
        conn.close()
        return jsonify({"ok": False, "error": "Check-in window closed"}), 400
    rsvp = cur.execute("SELECT id FROM event_rsvps WHERE event_id = ? AND user_id = ?", (event_id, user_id)).fetchone()
    if not rsvp:
        cur.execute(
            "INSERT INTO event_rsvps (event_id, user_id, status, checked_in, created_at) VALUES (?, ?, 'going', 1, ?)",
            (event_id, user_id, _utc_now_iso()),
        )
    else:
        cur.execute("UPDATE event_rsvps SET checked_in = 1 WHERE event_id = ? AND user_id = ?", (event_id, user_id))
    conn.commit()
    conn.close()
    _apply_trust_delta(user_id, 2, f"Event check-in: {event['title']}")
    _increment_quest_progress(user_id, 5)
    hours = _duration_hours(event["start_time"], event["end_time"], default_hours=2.0)
    _record_volunteer_hours(
        user_id,
        "event",
        event_id,
        hours,
        f"{_organiser_badge(event['organiser_type'] or 'admin')} - {event['title']}",
    )
    _add_notification(user_id, "event_checkin", "Event check-in completed.", {"event_id": event_id})
    return jsonify({"ok": True})


@app.post("/api/reports")
def api_reports_create():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    data = request.get_json(silent=True) or {}
    reported_id = data.get("reported_id")
    reason = (data.get("reason") or "").strip().lower()
    details = (data.get("details") or "").strip()
    context_type = (data.get("context_type") or "").strip()
    context_id = data.get("context_id")
    if reason not in {"harassment", "spam", "no-show", "inappropriate messages", "other"}:
        reason = "other"
    try:
        reported_id = int(reported_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "reported_id is required"}), 400
    if reported_id == user_id:
        return jsonify({"ok": False, "error": "Cannot report yourself"}), 400
    incident_date = datetime.utcnow().date().isoformat()
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reports (user_id, reporter_id, reported_id, context_type, context_id, reason, incident_date, details, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
        """,
        (user_id, user_id, reported_id, context_type or None, context_id, reason, incident_date, details or None, _utc_now_iso()),
    )
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    _log_audit("safety", "report_user", user_id, {"reported_id": reported_id, "reason": reason, "report_id": report_id})
    return jsonify({"ok": True, "report_id": report_id}), 201


@app.get("/admin/reports")
def admin_reports_page():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    conn = _get_main_conn()
    rows = conn.execute(
        """
        SELECT id, reporter_id, reported_id, reason, details, status, created_at, context_type, context_id
        FROM reports
        ORDER BY id DESC
        LIMIT 300
        """
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "reports": [dict(r) for r in rows]})


@app.post("/admin/reports/<int:report_id>/resolve")
def admin_reports_resolve(report_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    if status not in {"valid", "invalid", "reviewed"}:
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT reported_id FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Report not found"}), 404
    cur.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
    conn.commit()
    conn.close()
    if status == "valid" and row["reported_id"]:
        _apply_trust_delta(int(row["reported_id"]), -15, "Verified report")
    return jsonify({"ok": True})


@app.post("/api/notifications/<int:notif_id>/read")
def api_notification_read(notif_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/password-reset/request")
def api_password_reset_request():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "email is required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"ok": True})
    token = secrets.token_urlsafe(24)
    expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    conn = _get_main_conn()
    conn.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
        (user.id, token, expires, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    reset_link = f"{request.host_url.rstrip('/')}/login?reset_token={urllib.parse.quote(token)}"
    _send_platform_email(email, "Reset your Re:Connect password", f"Use this link to reset your password:\n{reset_link}\n\nThis link expires in 1 hour.")
    return jsonify({"ok": True})


@app.post("/api/password-reset/confirm")
def api_password_reset_confirm():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("new_password") or ""
    if len(new_password) < 8:
        return jsonify({"ok": False, "error": "Password must be at least 8 characters"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT id, user_id, expires_at, used
        FROM password_reset_tokens
        WHERE token = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (token,),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Invalid token"}), 400
    if int(row["used"]) == 1:
        conn.close()
        return jsonify({"ok": False, "error": "Token already used"}), 400
    expires_dt = _parse_iso_dt(row["expires_at"])
    if not expires_dt or datetime.utcnow() > expires_dt:
        conn.close()
        return jsonify({"ok": False, "error": "Token expired"}), 400
    password_hash = generate_password_hash(new_password)
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, int(row["user_id"])))
    cur.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = ?", (int(row["id"]),))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/admin/login")
def api_admin_login():
    data = request.get_json(silent=True) or request.form
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip() or "unknown"
    allowed, retry_after = _rate_limit_check(f"admin_login:{ip}", limit=8, window_seconds=60)
    if not allowed:
        return jsonify({"ok": False, "error": "Too many admin login attempts", "retry_after": retry_after}), 429
    admin_id = (data.get("adminId") or "").strip().lower()
    password = data.get("password") or ""

    if (admin_id == ADMIN_ID and password == ADMIN_PASSWORD) or (
        admin_id in ADMIN_EMAIL_PASSWORDS and password == ADMIN_EMAIL_PASSWORDS.get(admin_id)
    ):
        session["is_admin"] = True
        session["admin_id"] = admin_id
        _log_audit("roles", "admin_login", None, {"admin_id": admin_id})
        return jsonify({"ok": True})

    return jsonify({"ok": False, "error": "Invalid admin credentials"}), 401


@app.post("/api/admin/logout")
def api_admin_logout():
    if session.get("admin_id"):
        _log_audit("roles", "admin_logout", None, {"admin_id": session.get("admin_id")})
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    return jsonify({"ok": True})


@app.get("/api/admin/overview")
def api_admin_overview():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401

    days = request.args.get("days")
    audience = (request.args.get("audience") or "admin").strip().lower()
    if audience not in {"admin", "government", "corporate"}:
        audience = "admin"
    cutoff = None
    if days:
        try:
            cutoff = datetime.utcnow() - timedelta(days=int(days))
        except Exception:
            cutoff = None

    auth_query = AuthEvent.query
    circle_query = CircleSignup.query
    if cutoff:
        auth_query = auth_query.filter(AuthEvent.created_at >= cutoff)
        circle_query = circle_query.filter(CircleSignup.created_at >= cutoff)

    auth_events = auth_query.order_by(AuthEvent.created_at.desc()).limit(200).all()
    circle_signups = circle_query.order_by(CircleSignup.created_at.desc()).limit(200).all()

    def _u_name(uid):
        u = db.session.get(User, uid) if uid else None
        return u.full_name if u else ""

    conn = _get_main_conn()
    cur = conn.cursor()
    audit_where = ""
    params = []
    if cutoff:
        audit_where = "WHERE created_at >= ?"
        params.append(cutoff.isoformat())

    audit_rows = cur.execute(
        f"SELECT id, component, action, user_id, meta_json, created_at FROM audit_logs {audit_where} ORDER BY id DESC LIMIT 200",
        params,
    ).fetchall()

    def _count_with_cutoff(table: str, col: str = "created_at"):
        if cutoff:
            row = cur.execute(
                f"SELECT COUNT(*) AS c FROM {table} WHERE {col} >= ?",
                (cutoff.isoformat(),),
            ).fetchone()
        else:
            row = cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
        return row["c"] if row else 0

    posts_count = _count_with_cutoff("posts")
    comments_count = _count_with_cutoff("comments")
    matches_count = _count_with_cutoff("matches")
    messages_count = _count_with_cutoff("messages")
    challenge_entries_count = _count_with_cutoff("challenge_entries")
    reports_count = _count_with_cutoff("reports")

    total_seniors_row = cur.execute(
        "SELECT COUNT(*) AS c FROM users WHERE lower(COALESCE(member_type, '')) IN ('senior','elderly')"
    ).fetchone()
    engaged_seniors_row = cur.execute(
        """
        SELECT COUNT(DISTINCT u.id) AS c
        FROM users u
        WHERE lower(COALESCE(u.member_type, '')) IN ('senior','elderly')
          AND (
              EXISTS(SELECT 1 FROM circle_signups cs WHERE cs.user_id = u.id)
              OR EXISTS(SELECT 1 FROM event_rsvps er WHERE er.user_id = u.id AND er.status IN ('going','interested'))
              OR EXISTS(SELECT 1 FROM meetups m WHERE m.user1_id = u.id OR m.user2_id = u.id)
          )
        """
    ).fetchone()
    meetup_total_row = cur.execute("SELECT COUNT(*) AS c FROM meetups").fetchone()
    meetup_completed_row = cur.execute("SELECT COUNT(*) AS c FROM meetups WHERE status = 'completed'").fetchone()
    mood_row = cur.execute(
        """
        SELECT
            SUM(CASE WHEN lower(COALESCE(mood, '')) IN ('sad','stressed','lonely') THEN 1 ELSE 0 END) AS low_mood,
            COUNT(*) AS total_mood
        FROM mood_checkins
        """
    ).fetchone()
    volunteer_total_row = cur.execute("SELECT COALESCE(SUM(hours), 0) AS h FROM volunteer_hours").fetchone()
    corp_hours_row = cur.execute(
        """
        SELECT COALESCE(SUM(vh.hours), 0) AS h
        FROM volunteer_hours vh
        LEFT JOIN events e ON vh.source_type = 'event' AND e.id = vh.source_id
        WHERE vh.source_type != 'event' OR lower(COALESCE(e.organiser_type, '')) = 'corporate'
        """
    ).fetchone()
    corp_events_row = cur.execute(
        "SELECT COUNT(*) AS c FROM events WHERE lower(COALESCE(organiser_type, '')) = 'corporate'"
    ).fetchone()
    corp_seniors_row = cur.execute(
        """
        SELECT COUNT(DISTINCT er.user_id) AS c
        FROM event_rsvps er
        JOIN events e ON e.id = er.event_id
        JOIN users u ON u.id = er.user_id
        WHERE lower(COALESCE(e.organiser_type, '')) = 'corporate'
          AND lower(COALESCE(u.member_type, '')) IN ('senior','elderly')
          AND er.status IN ('going','interested')
        """
    ).fetchone()
    conn.close()

    total_seniors = int(total_seniors_row["c"] or 0)
    engaged_seniors = int(engaged_seniors_row["c"] or 0)
    meetup_total = int(meetup_total_row["c"] or 0)
    meetup_completed = int(meetup_completed_row["c"] or 0)
    low_mood = int(mood_row["low_mood"] or 0)
    total_mood = int(mood_row["total_mood"] or 0)
    audience_metrics = {
        "government": {
            "senior_engagement_rate": round((engaged_seniors / total_seniors) * 100, 1) if total_seniors else 0.0,
            "meetup_success_rate": round((meetup_completed / meetup_total) * 100, 1) if meetup_total else 0.0,
            "loneliness_indicator_pct": round((low_mood / total_mood) * 100, 1) if total_mood else 0.0,
            "volunteer_hours_total": float(volunteer_total_row["h"] or 0),
        },
        "corporate": {
            "employee_volunteer_hours": float(corp_hours_row["h"] or 0),
            "events_sponsored": int(corp_events_row["c"] or 0),
            "seniors_impacted": int(corp_seniors_row["c"] or 0),
        },
    }

    landmark_stats = {name: {"youth": 0, "senior": 0} for name in ONBOARDING_LANDMARKS}
    landmark_settings = UserSetting.query.filter_by(key="onboarding").all()
    for setting in landmark_settings:
        try:
            payload = json.loads(setting.value or "{}")
        except Exception:
            payload = {}
        member_type = (payload.get("memberType") or "").strip().lower()
        if not member_type:
            u = db.session.get(User, setting.user_id)
            member_type = (u.member_type or "").strip().lower() if u else ""
        group = "senior" if member_type in ("senior", "elderly") else "youth"
        for name in payload.get("landmarks") or []:
            if name in landmark_stats:
                landmark_stats[name][group] += 1

    landmark_rows = []
    top_youth = {"name": "", "count": 0}
    top_senior = {"name": "", "count": 0}
    top_overall = {"name": "", "count": 0}
    for name in ONBOARDING_LANDMARKS:
        youth_count = landmark_stats[name]["youth"]
        senior_count = landmark_stats[name]["senior"]
        total = youth_count + senior_count
        if youth_count > top_youth["count"]:
            top_youth = {"name": name, "count": youth_count}
        if senior_count > top_senior["count"]:
            top_senior = {"name": name, "count": senior_count}
        if total > top_overall["count"]:
            top_overall = {"name": name, "count": total}
        landmark_rows.append(
            {
                "name": name,
                "youth": youth_count,
                "senior": senior_count,
                "total": total,
            }
        )

    recent_activity = []
    for e in auth_events[:50]:
        recent_activity.append(
            {
                "type": f"auth:{e.event_type}",
                "source_table": "auth_events",
                "source_id": e.id,
                "user_id": e.user_id,
                "user_name": _u_name(e.user_id),
                "created_at": e.created_at.isoformat(),
                "summary": f"{e.event_type} - {e.email}",
            }
        )
    for r in audit_rows[:80]:
        recent_activity.append(
            {
                "type": "audit",
                "source_table": "audit_logs",
                "source_id": r["id"],
                "user_id": r["user_id"],
                "user_name": _u_name(r["user_id"]),
                "created_at": r["created_at"],
                "summary": f"{r['component']} / {r['action']}",
            }
        )
    recent_activity.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    recent_activity = recent_activity[:120]

    db_sources = []
    try:
        for p in (BASE_DIR.parent.parent / "database").glob("*.db"):
            db_sources.append(p.name)
    except Exception:
        pass

    total_users = User.query.count() if not cutoff else User.query.filter(User.created_at >= cutoff).count()
    total_auth_events = AuthEvent.query.count() if not cutoff else AuthEvent.query.filter(AuthEvent.created_at >= cutoff).count()
    total_circle_signups = CircleSignup.query.count() if not cutoff else CircleSignup.query.filter(CircleSignup.created_at >= cutoff).count()

    return jsonify(
        {
            "ok": True,
            "auth_events": [
                {
                    "id": e.id,
                    "created_at": e.created_at.isoformat(),
                    "event_type": e.event_type,
                    "user_id": e.user_id,
                    "user_name": _u_name(e.user_id),
                    "email": e.email,
                    "ip_address": e.ip_address,
                }
                for e in auth_events
            ],
            "circle_signups": [
                {
                    "id": s.id,
                    "created_at": s.created_at.isoformat(),
                    "user_id": s.user_id,
                    "user_name": _u_name(s.user_id),
                    "circle_title": s.circle_title,
                    "circle_time": s.circle_time,
                    "circle_duration": s.circle_duration,
                    "ip_address": s.ip_address,
                }
                for s in circle_signups
            ],
            "audit_logs": [
                {
                    "id": r["id"],
                    "component": r["component"],
                    "action": r["action"],
                    "user_id": r["user_id"],
                    "meta_json": r["meta_json"],
                    "created_at": r["created_at"],
                }
                for r in audit_rows
            ],
            "recent_activity": recent_activity,
            "db_sources": db_sources,
            "stats": {
                "total_users": total_users,
                "total_auth_events": total_auth_events,
                "total_circle_signups": total_circle_signups,
                "total_posts": posts_count,
                "total_comments": comments_count,
                "total_matches": matches_count,
                "total_messages": messages_count,
                "total_challenge_entries": challenge_entries_count,
                "total_reports": reports_count,
            },
            "audience": audience,
            "audience_metrics": audience_metrics.get(audience, {}),
            "landmark_stats": landmark_rows,
            "landmark_summary": {
                "top_youth": top_youth,
                "top_senior": top_senior,
                "top_overall": top_overall,
            },
        }
    )


@app.get("/api/admin/analytics/funnel")
def api_admin_analytics_funnel():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401

    total_users = User.query.count()

    conn_main = _get_main_conn()
    onboarding_done = conn_main.execute(
        "SELECT COUNT(*) AS c FROM user_settings WHERE key = 'onboarding' AND value IS NOT NULL AND TRIM(value) <> ''"
    ).fetchone()["c"]
    conn_main.close()

    conn_forum = _get_forum_conn()
    forum_posters = conn_forum.execute(
        "SELECT COUNT(DISTINCT author_id) AS c FROM posts WHERE author_id IS NOT NULL"
    ).fetchone()["c"]
    conn_forum.close()

    conn_chat = _get_chat_conn()
    matched_users = conn_chat.execute(
        "SELECT COUNT(DISTINCT user_id) AS c FROM matches"
    ).fetchone()["c"]
    conn_chat.close()

    stages = [
        {"key": "signup", "label": "Signed up", "count": int(total_users)},
        {"key": "onboarding", "label": "Completed onboarding", "count": int(onboarding_done)},
        {"key": "first_post", "label": "Posted in forum", "count": int(forum_posters)},
        {"key": "first_match", "label": "Made first match", "count": int(matched_users)},
    ]

    prev = None
    for row in stages:
        row["conversion"] = round((row["count"] / prev) * 100, 1) if prev else 100.0
        prev = row["count"]

    return jsonify({"ok": True, "stages": stages})


@app.get("/api/admin/safety")
def api_admin_safety():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    low_scores = cur.execute(
        """
        SELECT u.id, u.full_name, u.email, s.score, s.last_updated
        FROM safety_scores s
        JOIN users u ON u.id = s.user_id
        WHERE s.score < 40
        ORDER BY s.score ASC, s.last_updated DESC
        LIMIT 200
        """
    ).fetchall()
    reports = cur.execute(
        """
        SELECT id, user_id, reason, incident_date, details, status, created_at
        FROM reports
        ORDER BY id DESC
        LIMIT 200
        """
    ).fetchall()
    forum_reports = cur.execute(
        """
        SELECT id, post_id, reporter_id, reason, details, status, created_at
        FROM forum_post_reports
        ORDER BY id DESC
        LIMIT 200
        """
    ).fetchall()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "low_scores": [
                {
                    "user_id": r["id"],
                    "full_name": r["full_name"],
                    "email": r["email"],
                    "score": r["score"],
                    "last_updated": r["last_updated"],
                }
                for r in low_scores
            ],
            "reports": [
                {
                    "id": r["id"],
                    "user_id": r["user_id"],
                    "reason": r["reason"],
                    "incident_date": r["incident_date"],
                    "details": r["details"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                }
                for r in reports
            ],
            "forum_reports": [
                {
                    "id": r["id"],
                    "post_id": r["post_id"],
                    "reporter_id": r["reporter_id"],
                    "reason": r["reason"],
                    "details": r["details"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                }
                for r in forum_reports
            ],
        }
    )


@app.post("/api/admin/safety/adjust")
def api_admin_safety_adjust():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    points = data.get("points")
    details = (data.get("details") or "").strip()
    if not user_id or points is None:
        return jsonify({"ok": False, "error": "user_id and points are required"}), 400
    score = _add_safety_event(int(user_id), "admin_adjust", int(points), details or "Manual adjustment")
    _log_audit("safety", "adjust_score", int(user_id), {"points": points, "details": details})
    return jsonify({"ok": True, "score": score})


@app.post("/api/admin/users/<int:target_user_id>/verification_badges")
def api_admin_user_verification_badges(target_user_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    badges = data.get("badges") or []
    if not isinstance(badges, list):
        return jsonify({"ok": False, "error": "badges must be a list"}), 400
    allowed = {
        "Community-Verified Senior",
        "Volunteer-Verified Youth",
        "Programme Participant",
    }
    cleaned = [b for b in [str(x or "").strip() for x in badges] if b in allowed]
    applied = _set_user_verification_badges(target_user_id, cleaned, verified_by=f"admin:{session.get('admin_id') or 'admin'}")
    _log_audit("admin", "set_verification_badges", target_user_id, {"badges": applied})
    return jsonify({"ok": True, "badges": applied})


@app.post("/api/admin/reports/<int:report_id>/status")
def api_admin_report_status(report_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    if status not in {"pending", "confirmed", "resolved", "valid", "invalid"}:
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT reported_id FROM reports WHERE id = ?", (report_id,)).fetchone()
    cur.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
    conn.commit()
    conn.close()
    if status in {"confirmed", "valid"} and row and row["reported_id"]:
        _apply_trust_delta(int(row["reported_id"]), -15, "Verified report")
    _log_audit("safety", "update_report_status", None, {"report_id": report_id, "status": status})
    return jsonify({"ok": True})


@app.post("/api/admin/forum_reports/<int:report_id>/status")
def api_admin_forum_report_status(report_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    if status not in {"pending", "confirmed", "resolved"}:
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute("UPDATE forum_post_reports SET status = ? WHERE id = ?", (status, report_id))
    conn.commit()
    conn.close()
    _log_audit("safety", "update_forum_report_status", None, {"report_id": report_id, "status": status})
    return jsonify({"ok": True})


@app.get("/api/admin/export")
def api_admin_export():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401

    export_type = (request.args.get("type") or "").strip()
    headers = []
    rows = []

    export_format = (request.args.get("format") or "").strip().lower()

    if export_type == "auth_events":
        headers = ["id", "created_at", "event_type", "user_id", "email", "ip_address"]
        events = AuthEvent.query.order_by(AuthEvent.created_at.desc()).limit(2000).all()
        rows = [
            [e.id, e.created_at.isoformat(), e.event_type, e.user_id, e.email, e.ip_address]
            for e in events
        ]
    elif export_type == "circle_signups":
        headers = ["id", "created_at", "user_id", "circle_title", "circle_time", "circle_duration", "ip_address"]
        signups = CircleSignup.query.order_by(CircleSignup.created_at.desc()).limit(2000).all()
        rows = [
            [s.id, s.created_at.isoformat(), s.user_id, s.circle_title, s.circle_time, s.circle_duration, s.ip_address]
            for s in signups
        ]
    elif export_type == "audit_logs":
        headers = ["id", "created_at", "component", "action", "user_id", "meta_json"]
        conn = _get_main_conn()
        cur = conn.cursor()
        rows = [
            [r["id"], r["created_at"], r["component"], r["action"], r["user_id"], r["meta_json"]]
            for r in cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 2000").fetchall()
        ]
        conn.close()
    elif export_type == "reports":
        headers = ["id", "created_at", "user_id", "reason", "incident_date", "details", "status"]
        conn = _get_main_conn()
        cur = conn.cursor()
        rows = [
            [r["id"], r["created_at"], r["user_id"], r["reason"], r["incident_date"], r["details"], r["status"]]
            for r in cur.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 2000").fetchall()
        ]
        conn.close()
    elif export_type == "challenge_entries":
        headers = ["id", "created_at", "challenge_id", "user_id", "author_name", "content", "image_url"]
        conn = _get_main_conn()
        cur = conn.cursor()
        rows = [
            [r["id"], r["created_at"], r["challenge_id"], r["user_id"], r["author_name"], r["content"], r["image_url"]]
            for r in cur.execute("SELECT * FROM challenge_entries ORDER BY id DESC LIMIT 2000").fetchall()
        ]
        conn.close()
    elif export_type == "overview":
        headers = ["metric", "value"]
        conn = _get_main_conn()
        cur = conn.cursor()
        stats = {
            "total_users": User.query.count(),
            "total_auth_events": AuthEvent.query.count(),
            "total_circle_signups": CircleSignup.query.count(),
            "total_posts": cur.execute("SELECT COUNT(*) AS c FROM posts").fetchone()["c"],
            "total_comments": cur.execute("SELECT COUNT(*) AS c FROM comments").fetchone()["c"],
            "total_matches": cur.execute("SELECT COUNT(*) AS c FROM matches").fetchone()["c"],
            "total_messages": cur.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"],
            "total_challenge_entries": cur.execute("SELECT COUNT(*) AS c FROM challenge_entries").fetchone()["c"],
            "total_reports": cur.execute("SELECT COUNT(*) AS c FROM reports").fetchone()["c"],
        }
        rows = [[k, v] for k, v in stats.items()]
        conn.close()
    else:
        return jsonify({"ok": False, "error": "Invalid export type"}), 400

    def _csv_escape(val):
        if val is None:
            return ""
        text = str(val).replace('"', '""')
        return f"\"{text}\""

    if export_format == "xls":
        lines = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(str(v if v is not None else "") for v in row))
        data = "\n".join(lines)
        return Response(
            data,
            mimetype="application/vnd.ms-excel",
            headers={"Content-Disposition": f"attachment; filename={export_type}.xls"},
        )
    csv_lines = [",".join(headers)]
    for row in rows:
        csv_lines.append(",".join(_csv_escape(v) for v in row))
    csv_data = "\n".join(csv_lines)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={export_type}.csv"},
    )


@app.post("/api/admin/bulk")
def api_admin_bulk():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401

    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip()
    conn = _get_main_conn()
    cur = conn.cursor()

    if action == "clear_matches":
        cur.execute("DELETE FROM messages")
        cur.execute("DELETE FROM matches")
        conn.commit()
        conn.close()
        _log_audit("admin", "bulk_clear_matches")
        return jsonify({"ok": True})

    if action == "clear_forum":
        cur.execute("DELETE FROM post_likes")
        cur.execute("DELETE FROM comments")
        cur.execute("DELETE FROM posts")
        conn.commit()
        conn.close()
        _log_audit("admin", "bulk_clear_forum")
        return jsonify({"ok": True})

    if action == "clear_reports":
        cur.execute("DELETE FROM reports")
        conn.commit()
        conn.close()
        _log_audit("admin", "bulk_clear_reports")
        return jsonify({"ok": True})
    if action == "clear_challenges":
        cur.execute("DELETE FROM challenge_entry_likes")
        cur.execute("DELETE FROM challenge_comments")
        cur.execute("DELETE FROM challenge_entries")
        conn.commit()
        conn.close()
        _log_audit("admin", "bulk_clear_challenges")
        return jsonify({"ok": True})

    conn.close()
    return jsonify({"ok": False, "error": "Invalid action"}), 400


@app.get("/api/admin/posts")
def api_admin_posts():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    conn = _get_main_conn()
    rows = conn.execute(
        "SELECT id, author, title, content, category, created_at FROM posts ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "posts": [dict(r) for r in rows]})


@app.get("/api/admin/challenge_entries")
def api_admin_challenge_entries():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    conn = _get_main_conn()
    rows = conn.execute(
        "SELECT id, challenge_id, user_id, author_name, content, image_url, created_at FROM challenge_entries ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "entries": [dict(r) for r in rows]})


@app.put("/api/admin/challenge_entries/<int:entry_id>")
def api_admin_challenge_entry_update(entry_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Content is required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE challenge_entries SET content = ?, image_url = ? WHERE id = ?",
        (content, image_url or None, entry_id),
    )
    conn.commit()
    conn.close()
    _log_audit("admin", "challenge_entry_update", None, {"entry_id": entry_id})
    return jsonify({"ok": True})


@app.delete("/api/admin/challenge_entries/<int:entry_id>")
def api_admin_challenge_entry_delete(entry_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM challenge_entry_likes WHERE entry_id = ?", (entry_id,))
    cur.execute("DELETE FROM challenge_comments WHERE entry_id = ?", (entry_id,))
    cur.execute("DELETE FROM challenge_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    _log_audit("admin", "challenge_entry_delete", None, {"entry_id": entry_id})
    return jsonify({"ok": True})


@app.put("/api/admin/posts/<int:post_id>")
def api_admin_post_update(post_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Content is required"}), 400
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
    conn.commit()
    conn.close()
    _log_audit("admin", "post_update", None, {"post_id": post_id})
    return jsonify({"ok": True})


@app.delete("/api/admin/posts/<int:post_id>")
def api_admin_post_delete(post_id: int):
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM post_likes WHERE post_id = ?", (post_id,))
    cur.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    cur.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    _log_audit("admin", "post_delete", None, {"post_id": post_id})
    return jsonify({"ok": True})


@app.get("/api/achievements")
def api_achievements():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()

    user_row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    points = user_row["total_points"]
    tier = _update_tier(points)
    cur.execute("UPDATE users SET current_tier = ? WHERE id = ?", (tier, user_id))
    user_row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    landmarks = []
    for lm in cur.execute(
        """SELECT l.*, ul.unlocked, ul.completed
           FROM landmarks l
           JOIN user_landmarks ul ON ul.landmark_id = l.id
           WHERE ul.user_id = ?
           ORDER BY l.id""",
        (user_id,),
    ).fetchall():
        opts = cur.execute(
            "SELECT option_text FROM landmark_options WHERE landmark_id = ? ORDER BY option_index",
            (lm["id"],),
        ).fetchall()
        landmarks.append(
            {
                "id": lm["id"],
                "name": lm["name"],
                "icon": lm["icon"],
                "x": lm["x"],
                "y": lm["y"],
                "story": lm["story"],
                "question": lm["question"],
                "options": [o["option_text"] for o in opts],
                "answer": lm["correct_answer"],
                "unlocked": bool(lm["unlocked"]),
                "completed": bool(lm["completed"]),
            }
        )

    quests = []
    for q in cur.execute(
        """SELECT q.*, uq.progress, uq.completed
           FROM quests q
           JOIN user_quests uq ON uq.quest_id = q.id
           WHERE uq.user_id = ?
           ORDER BY q.id""",
        (user_id,),
    ).fetchall():
        quests.append(
            {
                "id": q["id"],
                "title": q["title"],
                "description": q["description"],
                "reward": q["reward"],
                "total": q["total_required"],
                "progress": q["progress"],
                "completed": bool(q["completed"]),
            }
        )

    rewards = []
    redeemed_ids = {
        r["reward_id"]
        for r in cur.execute("SELECT reward_id FROM user_rewards WHERE user_id = ?", (user_id,)).fetchall()
    }
    for r in cur.execute("SELECT * FROM rewards WHERE is_active = 1 ORDER BY id").fetchall():
        if r["id"] in redeemed_ids:
            status = "redeemed"
        else:
            status = "available" if user_row["available_points"] >= r["cost"] else "locked"
        rewards.append(
            {
                "id": r["id"],
                "name": r["name"],
                "icon": r["icon"],
                "cost": r["cost"],
                "description": r["description"],
                "sponsor_type": r["sponsor_type"] if "sponsor_type" in r.keys() else "none",
                "sponsor_name": r["sponsor_name"] if "sponsor_name" in r.keys() else "",
                "reward_type": r["reward_type"] if "reward_type" in r.keys() else "",
                "redemption_method": r["redemption_method"] if "redemption_method" in r.keys() else "Show this in-app code",
                "redemption_code": r["redemption_code"] if "redemption_code" in r.keys() else "",
                "status": status,
            }
        )

    checkins = [
        row["checkin_date"]
        for row in cur.execute(
            "SELECT checkin_date FROM user_checkins WHERE user_id = ? ORDER BY checkin_date",
            (user_id,),
        ).fetchall()
    ]

    skills = []
    for s in cur.execute(
        """SELECT s.*, us.progress, us.completed
           FROM skills s
           JOIN user_skills us ON us.skill_id = s.id
           WHERE us.user_id = ?
           ORDER BY s.id""",
        (user_id,),
    ).fetchall():
        skills.append(
            {
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "required_count": s["required_count"],
                "parent_id": s["parent_id"],
                "category": s["category"],
                "level": s["level"],
                "icon": s["icon"],
                "reward_points": s["reward_points"],
                "progress": s["progress"],
                "completed": bool(s["completed"]),
            }
        )

    quests_completed = len([q for q in quests if q["completed"]])
    landmarks_completed = len([l for l in landmarks if l["completed"]])
    skills_completed = len([s for s in skills if s["completed"]])

    badges = {}
    for b in cur.execute("SELECT * FROM badges ORDER BY id").fetchall():
        requirement = b["requirement_type"]
        current = 0
        if requirement == "landmarks":
            current = landmarks_completed
        elif requirement == "quests":
            current = quests_completed
        elif requirement == "points":
            current = user_row["total_points"]
        elif requirement == "tier":
            current = user_row["current_tier"]
        elif requirement == "skills":
            current = skills_completed
        earned = 1 if current >= b["threshold"] else 0
        cur.execute(
            "UPDATE user_badges SET earned = ?, earned_at = CASE WHEN ?=1 THEN COALESCE(earned_at, ?) ELSE earned_at END WHERE user_id = ? AND badge_id = ?",
            (earned, earned, datetime.utcnow().isoformat(), user_id, b["id"]),
        )
        badges.setdefault(b["category"], []).append(
            {
                "id": b["id"],
                "name": b["name"],
                "icon": b["icon"],
                "description": b["description"],
                "threshold": b["threshold"],
                "earned": bool(earned),
                "current": current,
            }
        )

    leaderboard = [
        {
            "username": row["full_name"],
            "total_points": row["total_points"],
            "current_tier": row["current_tier"],
        }
        for row in cur.execute(
            "SELECT full_name, total_points, current_tier FROM users ORDER BY total_points DESC LIMIT 10"
        ).fetchall()
    ]

    conn.commit()
    conn.close()

    state = {
        "user": {
            "id": user_row["id"],
            "username": user_row["full_name"],
            "total_points": user_row["total_points"],
            "available_points": user_row["available_points"],
            "active_days": user_row["active_days"],
            "current_tier": user_row["current_tier"],
            "current_streak": user_row["current_streak"],
        },
        "landmarks": landmarks,
        "quests": quests,
        "rewards": rewards,
        "badges": badges,
        "leaderboard": leaderboard,
        "checkins": checkins,
        "skills": skills,
    }
    return jsonify({"ok": True, "data": state})


@app.post("/api/achievements/quests/<int:quest_id>/progress")
def api_achievements_quest_progress(quest_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    quest = cur.execute(
        "SELECT q.reward, q.total_required, uq.progress, uq.completed FROM quests q JOIN user_quests uq ON uq.quest_id = q.id WHERE q.id = ? AND uq.user_id = ?",
        (quest_id, user_id),
    ).fetchone()
    if not quest:
        conn.close()
        return jsonify({"ok": False, "error": "Quest not found"}), 404
    progress = quest["progress"]
    completed = quest["completed"]
    was_completed = bool(completed)
    if not completed and progress < quest["total_required"]:
        progress += 1
        if progress >= quest["total_required"]:
            completed = 1
            cur.execute(
                "UPDATE users SET total_points = total_points + ?, available_points = available_points + ? WHERE id = ?",
                (quest["reward"], quest["reward"], user_id),
            )
    cur.execute(
        "UPDATE user_quests SET progress = ?, completed = ?, completed_at = CASE WHEN ?=1 THEN COALESCE(completed_at, ?) ELSE completed_at END WHERE user_id = ? AND quest_id = ?",
        (progress, completed, completed, datetime.utcnow().isoformat(), user_id, quest_id),
    )
    conn.commit()
    conn.close()
    if completed and not was_completed:
        _add_notification(
            user_id,
            "quest_complete",
            f"Quest completed! (+{quest['reward']} pts)",
            {"quest_id": quest_id},
        )
    return api_achievements()


@app.post("/api/achievements/rewards/<int:reward_id>/redeem")
def api_achievements_redeem_reward(reward_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    reward = cur.execute("SELECT cost, name, sponsor_name, redemption_code FROM rewards WHERE id = ? AND is_active = 1", (reward_id,)).fetchone()
    if not reward:
        conn.close()
        return jsonify({"ok": False, "error": "Reward not found"}), 404
    already = cur.execute(
        "SELECT id FROM user_rewards WHERE user_id = ? AND reward_id = ?",
        (user_id, reward_id),
    ).fetchone()
    if already:
        conn.close()
        return jsonify({"ok": False, "error": "Already redeemed"}), 400
    user_row = cur.execute("SELECT available_points FROM users WHERE id = ?", (user_id,)).fetchone()
    if user_row["available_points"] < reward["cost"]:
        conn.close()
        return jsonify({"ok": False, "error": "Not enough points"}), 400
    cur.execute(
        "INSERT INTO user_rewards (user_id, reward_id, redeemed_at) VALUES (?, ?, ?)",
        (user_id, reward_id, datetime.utcnow().isoformat()),
    )
    cur.execute(
        "UPDATE users SET available_points = available_points - ? WHERE id = ?",
        (reward["cost"], user_id),
    )
    conn.commit()
    conn.close()
    _add_notification(
        user_id,
        "reward",
        f"Reward redeemed: {reward['name']}",
        {"reward_id": reward_id, "sponsor_name": reward["sponsor_name"], "redemption_code": reward["redemption_code"]},
    )
    return api_achievements()


@app.post("/api/achievements/skills/<int:skill_id>/progress")
def api_achievements_skill_progress(skill_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    skill = cur.execute(
        "SELECT s.name, s.required_count, s.reward_points, us.progress, us.completed FROM skills s JOIN user_skills us ON us.skill_id = s.id WHERE s.id = ? AND us.user_id = ?",
        (skill_id, user_id),
    ).fetchone()
    if not skill:
        conn.close()
        return jsonify({"ok": False, "error": "Skill not found"}), 404
    if skill["completed"]:
        conn.close()
        return api_achievements()
    progress = min(skill["progress"] + 1, skill["required_count"])
    completed = 1 if progress >= skill["required_count"] else 0
    cur.execute(
        "UPDATE user_skills SET progress = ?, completed = ?, completed_at = CASE WHEN ?=1 THEN COALESCE(completed_at, ?) ELSE completed_at END WHERE user_id = ? AND skill_id = ?",
        (progress, completed, completed, datetime.utcnow().isoformat(), user_id, skill_id),
    )
    if completed:
        cur.execute(
            "UPDATE users SET total_points = total_points + ?, available_points = available_points + ? WHERE id = ?",
            (skill["reward_points"], skill["reward_points"], user_id),
        )
        cur.execute(
            "INSERT INTO user_skill_rewards (user_id, skill_id, reward_points, rewarded_at) VALUES (?, ?, ?, ?)",
            (user_id, skill_id, skill["reward_points"], datetime.utcnow().isoformat()),
        )
    conn.commit()
    conn.close()
    if completed:
        _increment_quest_progress(user_id, 3)
        _add_notification(
            user_id,
            "skill_complete",
            f"Skill completed: {skill['name']} (+{skill['reward_points']} pts)",
            {"skill_id": skill_id},
        )
    return api_achievements()


@app.post("/api/achievements/landmarks/<int:landmark_id>/unlock")
def api_achievements_landmark_unlock(landmark_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    order = cur.execute("SELECT id FROM landmarks ORDER BY id").fetchall()
    ids = [row["id"] for row in order]
    if landmark_id not in ids:
        conn.close()
        return jsonify({"ok": False, "error": "Landmark not found"}), 404
    index = ids.index(landmark_id)
    points_needed = (index + 1) * 1000
    user_row = cur.execute("SELECT total_points FROM users WHERE id = ?", (user_id,)).fetchone()
    if user_row["total_points"] < points_needed:
        conn.close()
        return jsonify({"ok": False, "error": "Not enough points"}), 400
    cur.execute(
        "UPDATE user_landmarks SET unlocked = 1, unlocked_at = COALESCE(unlocked_at, ?) WHERE user_id = ? AND landmark_id = ?",
        (datetime.utcnow().isoformat(), user_id, landmark_id),
    )
    conn.commit()
    conn.close()
    return api_achievements()


@app.post("/api/achievements/landmarks/<int:landmark_id>/complete")
def api_achievements_landmark_complete(landmark_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT completed FROM user_landmarks WHERE user_id = ? AND landmark_id = ?",
        (user_id, landmark_id),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Landmark not found"}), 404
    awarded = 0
    if not row["completed"]:
        awarded = 200
        cur.execute(
            "UPDATE user_landmarks SET completed = 1, completed_at = COALESCE(completed_at, ?) WHERE user_id = ? AND landmark_id = ?",
            (datetime.utcnow().isoformat(), user_id, landmark_id),
        )
        cur.execute(
            "UPDATE users SET total_points = total_points + ?, available_points = available_points + ? WHERE id = ?",
            (awarded, awarded, user_id),
        )
    conn.commit()
    conn.close()
    data = api_achievements().get_json()
    return jsonify({"ok": True, "data": data["data"], "awarded_points": awarded})



ACH_DB_PATH = DB_PATH


def _get_ach_conn():
    conn = sqlite3.connect(ACH_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _get_main_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    return conn


def _init_home_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS home_explore_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT 'orange',
            link TEXT
        );
        """
    )
    cols = {row["name"] for row in cur.execute("PRAGMA table_info(home_explore_cards)").fetchall()}
    if "link" not in cols:
        cur.execute("ALTER TABLE home_explore_cards ADD COLUMN link TEXT")
    count = cur.execute("SELECT COUNT(*) AS c FROM home_explore_cards").fetchone()["c"]
    if count != 4:
        cur.execute("DELETE FROM home_explore_cards")
        cur.executemany(
            "INSERT INTO home_explore_cards (title, description, icon, color, link) VALUES (?, ?, ?, ?, ?)",
            [
                ("Wisdom Forum", "Ask questions and share wisdom", "💡", "orange", "/dashboard#tab-wisdom-forum"),
                ("Matching", "Find people with shared interests", "🤝", "teal", "/discover"),
                ("Learning Circles", "Join group sessions", "📚", "orange", "/dashboard#tab-learning-circles"),
                ("Achievements", "Track quests and badges", "🏅", "teal", "/achievements"),
            ],
        )
    else:
        cur.execute(
            """
            UPDATE home_explore_cards
               SET link = CASE
                   WHEN title = 'Wisdom Forum' THEN '/dashboard#tab-wisdom-forum'
                   WHEN title = 'Matching' THEN '/discover'
                   WHEN title = 'Learning Circles' THEN '/dashboard#tab-learning-circles'
                   WHEN title = 'Achievements' THEN '/achievements'
                   ELSE link
               END
             WHERE link IS NULL OR link = ''
            """
        )
    conn.commit()
    conn.close()


def _list_home_explore_cards():
    conn = _get_main_conn()
    rows = conn.execute(
        "SELECT id, title, description, icon, color, link FROM home_explore_cards ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return rows


def _init_meetup_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS safe_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_name TEXT NOT NULL,
            place_name TEXT NOT NULL,
            venue_type TEXT NOT NULL,
            address TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            walking_mins INTEGER,
            UNIQUE(station_name, place_name)
        );

        CREATE TABLE IF NOT EXISTS user_meetup_preferences (
            user_id INTEGER NOT NULL,
            station_name TEXT NOT NULL,
            PRIMARY KEY (user_id, station_name),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    seed_rows = [
        ("Bishan", "Junction 8 Cafe", "cafe", "9 Bishan Place, Singapore 579837", 1.3509, 103.8487, 4),
        ("Bishan", "Bishan Public Library", "library", "5 Bishan Place, Singapore 579841", 1.3507, 103.8489, 5),
        ("Bishan", "Bishan Community Club", "community_club", "51 Bishan Street 13, Singapore 579799", 1.3516, 103.8499, 6),
        ("Siglap", "Siglap South Community Centre", "community_club", "6 Palm Road, Singapore 456541", 1.3090, 103.9270, 7),
        ("Siglap", "Bedok Public Library", "library", "11 Bedok North Street 1, Singapore 469662", 1.3269, 103.9305, 8),
        ("Marine Parade", "Marine Parade Public Library", "library", "278 Marine Parade Road, Singapore 449282", 1.3027, 103.9070, 6),
        ("Marine Parade", "Marine Parade Community Club", "community_club", "278 Marine Parade Road, Singapore 449282", 1.3028, 103.9066, 5),
        ("Tanjong Katong", "Katong Community Centre", "community_club", "51 Kampong Arang Road, Singapore 438178", 1.3057, 103.8862, 7),
        ("Tanjong Katong", "Geylang East Public Library", "library", "50 Geylang East Avenue 1, Singapore 389777", 1.3183, 103.8856, 9),
        ("Buona Vista", "Buona Vista Community Club", "community_club", "36 Holland Drive, Singapore 270036", 1.3074, 103.7888, 6),
        ("Buona Vista", "The Star Vista", "mall", "1 Vista Exchange Green, Singapore 138617", 1.3066, 103.7890, 4),
        ("Caldecott", "Toa Payoh West Community Club", "community_club", "200 Lorong 2 Toa Payoh, Singapore 319642", 1.3357, 103.8502, 9),
        ("Caldecott", "Lornie Nature Corridor Gate", "park", "Lornie Road, Singapore", 1.3437, 103.8179, 10),
        ("Toa Payoh", "Toa Payoh Public Library", "library", "6 Toa Payoh Central, Singapore 319191", 1.3320, 103.8474, 5),
        ("Bugis", "National Library", "library", "100 Victoria Street, Singapore 188064", 1.2966, 103.8545, 5),
        ("City Hall", "Raffles City", "mall", "252 North Bridge Road, Singapore 179103", 1.2932, 103.8526, 4),
    ]
    cur.executemany(
        """
        INSERT OR IGNORE INTO safe_locations
            (station_name, place_name, venue_type, address, lat, lng, walking_mins)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        seed_rows,
    )

    cur.execute(
        """
        UPDATE safe_locations
           SET station_name = 'Bishan'
         WHERE lower(place_name) = lower('Junction 8 Cafe')
        """
    )
    cur.execute(
        """
        DELETE FROM safe_locations
         WHERE lower(place_name) = lower('Junction 8 Cafe')
           AND station_name <> 'Bishan'
        """
    )
    conn.commit()
    conn.close()


def _init_social_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS hangout_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            mrt_nearby TEXT,
            accessibility_json TEXT,
            lat REAL,
            lng REAL,
            photo_path TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_hangout_spots_user ON hangout_spots(user_id, created_at);

        CREATE TABLE IF NOT EXISTS meetups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            spot_id INTEGER,
            meetup_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            checked_in_user1 INTEGER NOT NULL DEFAULT 0,
            checked_in_user2 INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_meetups_users ON meetups(user1_id, user2_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_meetups_time ON meetups(meetup_time);

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meetup_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            reviewee_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            tags_json TEXT,
            comment TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(meetup_id, reviewer_id)
        );
        CREATE INDEX IF NOT EXISTS idx_reviews_reviewee ON reviews(reviewee_id, created_at);

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            tags_json TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            location_name TEXT NOT NULL,
            lat REAL,
            lng REAL,
            capacity INTEGER NOT NULL DEFAULT 0,
            accessibility_json TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_start_time ON events(start_time);

        CREATE TABLE IF NOT EXISTS event_rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'going',
            checked_in INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(event_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_event_rsvps_event ON event_rsvps(event_id, status);

        CREATE TABLE IF NOT EXISTS moderation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message_preview TEXT,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_moderation_events_user ON moderation_events(user_id, created_at);

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id, created_at);

        CREATE TABLE IF NOT EXISTS volunteer_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            hours REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, source_type, source_id)
        );
        CREATE INDEX IF NOT EXISTS idx_volunteer_hours_user ON volunteer_hours(user_id, created_at);

        CREATE TABLE IF NOT EXISTS titles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS user_titles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title_id INTEGER NOT NULL,
            unlocked_at TEXT NOT NULL,
            UNIQUE(user_id, title_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_titles_user ON user_titles(user_id, unlocked_at);

        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            banner_path TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS club_memberships (
            user_id INTEGER NOT NULL,
            club_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(user_id, club_id)
        );
        CREATE INDEX IF NOT EXISTS idx_club_memberships_club ON club_memberships(club_id, joined_at);
        """
    )
    cols = {row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    if "trust_score" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN trust_score INTEGER NOT NULL DEFAULT 50")
    if "avg_rating" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN avg_rating REAL NOT NULL DEFAULT 0")
    if "review_count" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN review_count INTEGER NOT NULL DEFAULT 0")
    if "strike_count" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN strike_count INTEGER NOT NULL DEFAULT 0")
    if "chat_cooldown_until" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN chat_cooldown_until TEXT")
    if "phone" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "email_notifications_enabled" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN email_notifications_enabled INTEGER NOT NULL DEFAULT 1")
    if "verification_badges_json" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN verification_badges_json TEXT")
    if "verified_by" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN verified_by TEXT")
    if "total_volunteer_hours" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN total_volunteer_hours REAL NOT NULL DEFAULT 0")
    if "equipped_title_id" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN equipped_title_id INTEGER")
    if "username" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "is_private" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN is_private INTEGER NOT NULL DEFAULT 0")

    existing_usernames = set()
    user_rows = cur.execute("SELECT id, full_name, email, username FROM users ORDER BY id ASC").fetchall()
    for row in user_rows:
        uid = int(row["id"])
        raw = (row["username"] or "").strip().lower()
        if not _is_valid_username(raw):
            raw = _username_slug(row["full_name"] or row["email"] or f"user_{uid}", uid)
        candidate = raw[:30]
        suffix = 0
        while candidate in existing_usernames:
            suffix += 1
            base = raw[: max(1, 30 - len(str(suffix)) - 1)]
            candidate = f"{base}_{suffix}"
        existing_usernames.add(candidate)
        cur.execute("UPDATE users SET username = ? WHERE id = ?", (candidate, uid))
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username)")

    event_cols = {row["name"] for row in cur.execute("PRAGMA table_info(events)").fetchall()}
    if "organiser_type" not in event_cols:
        cur.execute("ALTER TABLE events ADD COLUMN organiser_type TEXT")
    if "organiser_name" not in event_cols:
        cur.execute("ALTER TABLE events ADD COLUMN organiser_name TEXT")
    if "verification_badge" not in event_cols:
        cur.execute("ALTER TABLE events ADD COLUMN verification_badge TEXT")
    if "organiser_logo_path" not in event_cols:
        cur.execute("ALTER TABLE events ADD COLUMN organiser_logo_path TEXT")
    cur.execute("UPDATE events SET organiser_type = COALESCE(NULLIF(organiser_type, ''), 'admin')")
    cur.execute("UPDATE events SET organiser_name = COALESCE(NULLIF(organiser_name, ''), 'Re:Connect Admin')")
    cur.execute("UPDATE events SET verification_badge = COALESCE(NULLIF(verification_badge, ''), 'Admin Hosted')")

    hangout_cols = {row["name"] for row in cur.execute("PRAGMA table_info(hangout_spots)").fetchall()}
    if "source_type" not in hangout_cols:
        cur.execute("ALTER TABLE hangout_spots ADD COLUMN source_type TEXT NOT NULL DEFAULT 'user'")
    if "is_verified" not in hangout_cols:
        cur.execute("ALTER TABLE hangout_spots ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
    if "verified_label" not in hangout_cols:
        cur.execute("ALTER TABLE hangout_spots ADD COLUMN verified_label TEXT")
    cur.execute("UPDATE hangout_spots SET source_type = COALESCE(NULLIF(source_type, ''), 'user')")

    report_cols = {row["name"] for row in cur.execute("PRAGMA table_info(reports)").fetchall()}
    if "reporter_id" not in report_cols:
        cur.execute("ALTER TABLE reports ADD COLUMN reporter_id INTEGER")
    if "reported_id" not in report_cols:
        cur.execute("ALTER TABLE reports ADD COLUMN reported_id INTEGER")
    if "context_type" not in report_cols:
        cur.execute("ALTER TABLE reports ADD COLUMN context_type TEXT")
    if "context_id" not in report_cols:
        cur.execute("ALTER TABLE reports ADD COLUMN context_id INTEGER")

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS follows (
            follower_id INTEGER NOT NULL,
            followed_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending','accepted','rejected')),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            UNIQUE(follower_id, followed_id)
        );
        CREATE INDEX IF NOT EXISTS idx_follows_followed_status ON follows(followed_id, status);

        CREATE TABLE IF NOT EXISTS blocks (
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(blocker_id, blocked_id)
        );
        CREATE INDEX IF NOT EXISTS idx_blocks_blocker ON blocks(blocker_id, created_at);

        CREATE TABLE IF NOT EXISTS social_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_social_actions_actor_action ON social_actions(actor_id, action, created_at);
        """
    )
    cur.execute(
        """
        INSERT OR IGNORE INTO blocks (blocker_id, blocked_id, created_at)
        SELECT user_id, blocked_user_id, COALESCE(created_at, ?)
        FROM user_blocks
        """,
        (_utc_now_iso(),),
    )

    count = cur.execute("SELECT COUNT(*) AS c FROM hangout_spots").fetchone()["c"]
    if int(count or 0) == 0:
        cur.executemany(
            """
            INSERT INTO hangout_spots
                (user_id, name, category, description, mrt_nearby, accessibility_json, lat, lng, photo_path, source_type, is_verified, verified_label, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "Marine Parade Public Library", "library", "Quiet reading space for meetups", "Marine Parade", json.dumps({"seating": 1, "toilets": 1, "accessible": 1, "quiet": 1, "well_lit": 1}), 1.3027, 103.9070, None, "government", 1, "Gov Recommended Venue", _utc_now_iso()),
                (1, "Toa Payoh Community Club Cafe", "community_centre", "Friendly small cafe inside community centre", "Toa Payoh", json.dumps({"seating": 1, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}), 1.3320, 103.8476, None, "community", 1, "Community-Verified Venue", _utc_now_iso()),
                (1, "Our Tampines Hub", "community_centre", "Large active ageing and community space", "Tampines", json.dumps({"seating": 1, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}), 1.3546, 103.9401, None, "government", 1, "Gov Recommended Venue", _utc_now_iso()),
                (1, "Jurong Regional Library", "library", "Accessible library floors and quiet corners", "Jurong East", json.dumps({"seating": 1, "toilets": 1, "accessible": 1, "quiet": 1, "well_lit": 1}), 1.3331, 103.7422, None, "government", 1, "Gov Recommended Venue", _utc_now_iso()),
            ],
        )

    club_count = int(cur.execute("SELECT COUNT(*) AS c FROM clubs").fetchone()["c"] or 0)
    if club_count == 0:
        cur.executemany(
            """
            INSERT INTO clubs (name, description, category, banner_path, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Intergen Story Circle", "Weekly storytelling and listening sessions between youth and seniors.", "Community", "/static/images/logo-tree.png", _utc_now_iso()),
                ("Digital Confidence Club", "Hands-on peer support for smartphones, apps, and scam awareness.", "Learning", "/static/images/logo-tree.png", _utc_now_iso()),
                ("Neighbourhood Wellness Walkers", "Gentle walking group with check-ins and health tips.", "Wellbeing", "/static/images/logo-tree.png", _utc_now_iso()),
                ("Creative Makers Club", "Craft, drawing, and memory-journaling sessions for all levels.", "Arts", "/static/images/logo-tree.png", _utc_now_iso()),
            ],
        )

    base = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    seed_events = [
            ("Silver Tech Saturday @ Our Tampines Hub", "Hands-on support for seniors using e-payments and telehealth apps.", "Learning Circle", ["digital literacy", "active ageing"], 2, 10, 2, "Our Tampines Hub", 1.3546, 103.9401, 120, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}, "government", "PA Active Ageing", "Gov Programme"),
            ("National Intergenerational Week: Story Exchange", "Youths and seniors share neighbourhood stories and memory prompts.", "Heritage", ["national intergenerational week", "storytelling"], 3, 15, 2, "National Library, Bugis", 1.2966, 103.8545, 150, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 1, "well_lit": 1}, "government", "National Library Board", "Gov Programme"),
            ("Healthy Steps Walk @ Marina Bay", "Guided low-intensity walk and buddy wellness check-in.", "Walk & Talk", ["wellness", "mobility"], 4, 8, 2, "Marina Bay Promenade", 1.2834, 103.8607, 200, {"seating": 0, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}, "government", "Health Promotion Board", "Gov Programme"),
            ("CPF Retirement Planning Clinic", "Simple CPF and budgeting clinic for seniors and caregivers.", "Workshop", ["financial literacy", "retirement"], 5, 14, 2, "Toa Payoh Central CC", 1.3322, 103.8473, 100, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 1, "well_lit": 1}, "government", "CPF Board", "Gov Programme"),
            ("CyberSafe Neighbourhood Briefing", "Scam trends, safe browsing and practical cyber hygiene tips.", "Workshop", ["cybersecurity awareness"], 6, 19, 2, "Woodlands Regional Library", 1.4360, 103.7865, 120, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 1, "well_lit": 1}, "government", "GovTech x CSA", "Gov Programme"),
            ("Corporate Volunteer Day: DBS Digital Buddies", "DBS volunteers teach secure online banking basics.", "Learning Circle", ["corporate volunteer day", "digital banking"], 2, 15, 2, "Bishan Community Club", 1.3516, 103.8499, 90, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}, "corporate", "DBS Volunteer Corps", "Corporate Volunteer Event"),
            ("Singtel ScamShield Clinic", "Device setup support and scam-filter walkthrough for seniors.", "Workshop", ["digital safety", "scamshield"], 3, 11, 2, "Marine Parade Public Library", 1.3027, 103.9070, 85, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 1, "well_lit": 1}, "corporate", "Singtel Community Care", "Corporate Volunteer Event"),
            ("Google for Seniors: Photos and Maps", "Volunteers help seniors organize photos and navigate with confidence.", "Learning Circle", ["google maps", "smartphone"], 4, 14, 2, "Jurong Regional Library", 1.3331, 103.7422, 95, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 1, "well_lit": 1}, "corporate", "Google Singapore Volunteers", "Corporate Volunteer Event"),
            ("GrabCare Community Mobility Workshop", "Safe ride-booking and accessibility features training.", "Workshop", ["transport", "mobility"], 5, 10, 2, "Paya Lebar Quarter Community Space", 1.3177, 103.8925, 80, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}, "corporate", "Grab Community Team", "Corporate Volunteer Event"),
            ("Shopee x SG Cares E-Commerce Basics", "How to buy safely online and avoid fraudulent listings.", "Learning Circle", ["e-commerce", "online safety"], 6, 13, 2, "Bukit Panjang CC", 1.3796, 103.7711, 88, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}, "corporate", "Shopee Cares", "Corporate Volunteer Event"),
            ("Community Heritage Walk: Katong Stories", "Neighbourhood trail with story checkpoints and photo prompts.", "Heritage", ["community heritage walk", "heritage"], 7, 9, 2, "Katong Community Club", 1.3057, 103.8862, 70, {"seating": 0, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}, "community", "Katong Residents Network", "Community Hosted"),
            ("Intergen Games & Social Evening", "Board games, memory games and partner icebreakers.", "Games & Social", ["intergenerational", "social"], 8, 18, 2, "Yishun Community Club", 1.4287, 103.8332, 110, {"seating": 1, "toilets": 1, "accessible": 1, "quiet": 0, "well_lit": 1}, "community", "North District Volunteers", "Community Hosted"),
        ]
    existing_titles = {
        row["title"]
        for row in cur.execute("SELECT title FROM events").fetchall()
    }
    new_rows = [
            (
                title,
                description,
                category,
                json.dumps(tags),
                (base + timedelta(days=day_offset, hours=hour_offset)).isoformat(),
                (base + timedelta(days=day_offset, hours=hour_offset + duration_hours)).isoformat(),
                location_name,
                lat,
                lng,
                capacity,
                json.dumps(accessibility),
                None,
                organiser_type,
                organiser_name,
                badge,
                None,
                _utc_now_iso(),
            )
            for (
                title,
                description,
                category,
                tags,
                day_offset,
                hour_offset,
                duration_hours,
                location_name,
                lat,
                lng,
                capacity,
                accessibility,
                organiser_type,
                organiser_name,
                badge,
            ) in seed_events
            if title not in existing_titles
    ]
    if new_rows:
        cur.executemany(
            """
            INSERT INTO events
                (title, description, category, tags_json, start_time, end_time, location_name, lat, lng, capacity, accessibility_json, created_by, organiser_type, organiser_name, verification_badge, organiser_logo_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            new_rows,
            )

    title_rows = [
        ("helper", "Helper", "Earned 5 verified volunteer hours."),
        ("community_builder", "Community Builder", "Earned 20 verified volunteer hours."),
        ("mentor_in_training", "Mentor in Training", "Earned 50 verified volunteer hours."),
        ("impact_leader", "Impact Leader", "Earned 100 verified volunteer hours."),
        ("circle_starter", "Circle Starter", "Joined 3 learning circles."),
        ("knowledge_guide", "Knowledge Guide", "Joined 10 learning circles."),
        ("trusted_connector", "Trusted Connector", "Reached trust score 80."),
        ("storyteller", "Storyteller", "Shared 10 community memories."),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO titles (code, display_name, description) VALUES (?, ?, ?)",
        title_rows,
    )
    conn.commit()
    conn.close()


def _init_challenges_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS weekly_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reward_points INTEGER NOT NULL,
            week_label TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS challenge_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (challenge_id) REFERENCES weekly_challenges(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS challenge_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES challenge_entries(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS challenge_entry_likes (
            entry_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, user_id),
            FOREIGN KEY (entry_id) REFERENCES challenge_entries(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS challenge_participation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            partner_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            submission_json TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_challenge_participation_user
            ON challenge_participation(user_id, challenge_id, created_at);
        """
    )
    cols = {row["name"] for row in cur.execute("PRAGMA table_info(weekly_challenges)").fetchall()}
    if "type" not in cols:
        cur.execute("ALTER TABLE weekly_challenges ADD COLUMN type TEXT NOT NULL DEFAULT 'general'")
    count = cur.execute("SELECT COUNT(*) AS c FROM weekly_challenges").fetchone()["c"]
    if count == 0:
        cur.execute(
            "INSERT INTO weekly_challenges (title, description, reward_points, week_label, created_at, type) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "🥟 Recreate Your Childhood Snack",
                "Share a photo or story of a snack you loved as a child. Tell us the memories behind it!",
                20,
                "Week 12 Challenge",
                _utc_now_iso(),
                "photo",
            ),
        )
    cur.execute(
        """
        DELETE FROM challenge_entries
         WHERE id NOT IN (
            SELECT MIN(id)
              FROM challenge_entries
             GROUP BY challenge_id, user_id
         )
        """
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_challenge_entries_unique_user_week ON challenge_entries(challenge_id, user_id)"
    )
    conn.commit()
    conn.close()


def _seed_demo_forum_content():
    conn = _get_forum_conn()
    cur = conn.cursor()
    seeds = [
        (
            "How do you stay close to family across generations?",
            "Relationships",
            "I want to spend more quality time with both grandparents and younger cousins. Any weekly routine ideas?",
            "Mdm Tan",
            8,
            [
                ("A Sunday breakfast routine works well for our family.", "Uncle Raj"),
                ("Try a shared photo album where everyone adds one memory weekly.", "Alyssa"),
            ],
        ),
        (
            "What are simple ways to reduce phone scam risk?",
            "Life Skills",
            "My dad gets many unknown calls. What settings should we enable to stay safer?",
            "Daniel",
            11,
            [
                ("Enable silence unknown callers and never share OTP codes.", "Singtel Mentor"),
                ("Set a family password phrase before discussing money on calls.", "Mr Goh"),
            ],
        ),
        (
            "Any tips for managing retirement spending?",
            "Money",
            "Looking for a beginner-friendly monthly budgeting method that is easy to maintain.",
            "Mr Lim",
            7,
            [
                ("Use the 50/30/20 split and review every payday.", "Finance Volunteer"),
                ("Track essentials first, then fixed savings, then lifestyle.", "Nurul"),
            ],
        ),
        (
            "What is one life lesson you wish you learned earlier?",
            "Career",
            "I am helping younger members prepare for work life. Would love practical advice from seniors.",
            "Ryan",
            13,
            [
                ("Consistency beats intensity. Small habits compound.", "Mdm Lee"),
                ("Ask for feedback early and often.", "Mr Wong"),
            ],
        ),
        (
            "How can we make meetups less awkward at first?",
            "Relationships",
            "Sometimes both sides are shy. What are good first 10-minute conversation starters?",
            "Aden",
            9,
            [
                ("Start with food, places, and favorite old songs.", "Cheryl"),
                ("Bring one printed photo as an easy storytelling prompt.", "Uncle Peter"),
            ],
        ),
        (
            "What helps you feel better on low-energy days?",
            "Health",
            "I am collecting ideas for gentle routines seniors and youths can do together.",
            "Community Coach",
            10,
            [
                ("A short park walk and sunlight helps a lot.", "Mdm Noor"),
                ("Tea chat plus light stretching works well for us.", "Karthik"),
            ],
        ),
    ]

    existing_titles = {
        row["title"]
        for row in cur.execute("SELECT title FROM posts").fetchall()
    }
    now = datetime.utcnow()
    for idx, (title, category, content, author, likes, comments) in enumerate(seeds):
        if title in existing_titles:
            cur.execute(
                "UPDATE posts SET likes = CASE WHEN likes < ? THEN ? ELSE likes END WHERE title = ?",
                (likes, likes, title),
            )
            continue
        created_at = (now - timedelta(days=(len(seeds) - idx))).strftime("%Y-%m-%d %H:%M")
        cur.execute(
            """
            INSERT INTO posts (author_id, author, title, content, category, likes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (None, author, title, content, category, likes, created_at),
        )
        post_id = cur.lastrowid
        for c_idx, (comment_text, comment_author) in enumerate(comments):
            c_time = (now - timedelta(days=(len(seeds) - idx), minutes=10 - c_idx)).strftime("%Y-%m-%d %H:%M")
            cur.execute(
                """
                INSERT INTO comments (post_id, author_id, author, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (post_id, None, comment_author, comment_text, c_time),
            )
    conn.commit()
    conn.close()


def _seed_demo_challenge_content():
    conn = _get_main_conn()
    cur = conn.cursor()

    challenge_rows = [
        ("Heritage Photo Walk", "Share one neighborhood photo and the story behind it.", 20, "Week 10 Challenge", "photo"),
        ("Teach a Small Skill", "Teach someone one practical skill and post what they learned.", 25, "Week 11 Challenge", "duo"),
        ("Favourite Hawker Memory", "Post your favorite hawker food memory and why it matters to you.", 20, "Week 12 Challenge", "story"),
    ]
    existing_titles = {
        row["title"]
        for row in cur.execute("SELECT title FROM weekly_challenges").fetchall()
    }
    for idx, (title, description, reward_points, week_label, challenge_type) in enumerate(challenge_rows):
        if title in existing_titles:
            continue
        created_at = (datetime.utcnow() - timedelta(days=14 - idx)).strftime("%Y-%m-%d %H:%M")
        cur.execute(
            """
            INSERT INTO weekly_challenges (title, description, reward_points, week_label, created_at, type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, description, reward_points, week_label, created_at, challenge_type),
        )

    latest = cur.execute(
        "SELECT id FROM weekly_challenges ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if latest:
        challenge_id = int(latest["id"])
        existing_count = int(
            cur.execute(
                "SELECT COUNT(*) AS c FROM challenge_entries WHERE challenge_id = ?",
                (challenge_id,),
            ).fetchone()["c"]
        )
        if existing_count < 8:
            demo_entries = [
                (9101, "Aiden", "Visited Tiong Bahru Market and tried chwee kueh with my grandma. Great stories today!"),
                (9102, "Mdm Lee", "Shared old photos from Queenstown and compared how the estate changed over time."),
                (9103, "Sarah", "Did a short interview with my neighbor about kampong school days."),
                (9104, "Uncle Raj", "Taught my buddy how to make teh tarik at home."),
                (9105, "Nurul", "My partner and I explored Chinatown murals and discussed heritage memories."),
                (9106, "Daniel", "Helped an elder learn PayNow safely and wrote down the steps together."),
                (9107, "Mdm Tan", "Brought old family recipe cards and we recreated one snack."),
                (9108, "Karthik", "Joined a community walk and documented accessible rest points."),
            ]
            for idx, (user_id, author_name, content) in enumerate(demo_entries):
                exists = cur.execute(
                    "SELECT id FROM challenge_entries WHERE challenge_id = ? AND user_id = ?",
                    (challenge_id, user_id),
                ).fetchone()
                if exists:
                    continue
                created_at = (datetime.utcnow() - timedelta(hours=18 - idx)).strftime("%Y-%m-%d %H:%M")
                cur.execute(
                    """
                    INSERT INTO challenge_entries (challenge_id, user_id, author_name, content, image_url, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (challenge_id, user_id, author_name, content, None, created_at),
                )
    conn.commit()
    conn.close()


def _init_reports_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            incident_date TEXT NOT NULL,
            details TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        );
        """
    )
    cols = {row["name"] for row in cur.execute("PRAGMA table_info(reports)").fetchall()}
    if "status" not in cols:
        cur.execute("ALTER TABLE reports ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
    conn.commit()
    conn.close()


def _init_forum_moderation_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS forum_post_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            reporter_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            details TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_forum_reports_status ON forum_post_reports(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_forum_reports_post ON forum_post_reports(post_id, created_at);

        CREATE TABLE IF NOT EXISTS user_blocks (
            user_id INTEGER NOT NULL,
            blocked_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (user_id, blocked_user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_blocks_user ON user_blocks(user_id, created_at);
        """
    )
    conn.commit()
    conn.close()


def _init_safety_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS safety_scores (
            user_id INTEGER PRIMARY KEY,
            score INTEGER NOT NULL,
            last_updated TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS safety_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            points INTEGER NOT NULL,
            ref_id TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_safety_events_user
            ON safety_events(user_id, created_at);
        """
    )
    conn.commit()
    conn.close()


def _init_wellbeing_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS mood_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood TEXT NOT NULL,
            reason TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mood_user_created
            ON mood_checkins(user_id, created_at);

        CREATE TABLE IF NOT EXISTS wellbeing_recos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood TEXT NOT NULL,
            reco_type TEXT NOT NULL,
            reco_title TEXT NOT NULL,
            reco_link TEXT,
            clicked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_recos_user_created
            ON wellbeing_recos(user_id, created_at);

        CREATE TABLE IF NOT EXISTS wellbeing_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT,
            gratitude TEXT,
            reflection TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_wellbeing_journal_user_created
            ON wellbeing_journal(user_id, created_at);
        """
    )
    conn.commit()
    conn.close()


def _init_partner_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            logo_url TEXT,
            description TEXT,
            verified INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS circle_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            circle_title TEXT NOT NULL,
            partner_id INTEGER,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 20,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'registered',
            created_at TEXT NOT NULL
        );
        """
    )
    session_cols = {row["name"] for row in cur.execute("PRAGMA table_info(circle_sessions)").fetchall()}
    if "host_type" not in session_cols:
        cur.execute("ALTER TABLE circle_sessions ADD COLUMN host_type TEXT NOT NULL DEFAULT 'user'")
    if "host_name" not in session_cols:
        cur.execute("ALTER TABLE circle_sessions ADD COLUMN host_name TEXT")
    if "host_logo_path" not in session_cols:
        cur.execute("ALTER TABLE circle_sessions ADD COLUMN host_logo_path TEXT")
    if "topic_tags_json" not in session_cols:
        cur.execute("ALTER TABLE circle_sessions ADD COLUMN topic_tags_json TEXT")
    conn.commit()
    conn.close()


def _init_scrapbook_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS scrapbook_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            related_user_id INTEGER,
            circle_title TEXT,
            entry_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            visibility TEXT NOT NULL DEFAULT 'private',
            featured INTEGER NOT NULL DEFAULT 0,
            campaign_tag TEXT,
            mood_tag TEXT,
            location TEXT,
            pinned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scrapbook_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            media_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scrapbook_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reaction_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS scrapbook_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(post_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS post_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_post_likes_post ON post_likes(post_id);
        CREATE INDEX IF NOT EXISTS idx_post_comments_post ON post_comments(post_id);
        CREATE TABLE IF NOT EXISTS scrapbook_stats (
            user_id INTEGER PRIMARY KEY,
            total_entries INTEGER NOT NULL DEFAULT 0,
            weekly_streak INTEGER NOT NULL DEFAULT 0,
            last_entry_at TEXT
        );
        CREATE TABLE IF NOT EXISTS storybook_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            place TEXT,
            event TEXT,
            feeling TEXT,
            lesson TEXT,
            media_url TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS trusted_viewers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            viewer_email TEXT NOT NULL,
            access_key TEXT NOT NULL,
            can_view_mood INTEGER NOT NULL DEFAULT 1,
            can_view_activity INTEGER NOT NULL DEFAULT 1,
            can_view_alerts INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    cols = {row["name"] for row in cur.execute("PRAGMA table_info(scrapbook_entries)").fetchall()}
    if "mood_tag" not in cols:
        cur.execute("ALTER TABLE scrapbook_entries ADD COLUMN mood_tag TEXT")
    if "location" not in cols:
        cur.execute("ALTER TABLE scrapbook_entries ADD COLUMN location TEXT")
    if "pinned" not in cols:
        cur.execute("ALTER TABLE scrapbook_entries ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
    if "featured" not in cols:
        cur.execute("ALTER TABLE scrapbook_entries ADD COLUMN featured INTEGER NOT NULL DEFAULT 0")
    if "campaign_tag" not in cols:
        cur.execute("ALTER TABLE scrapbook_entries ADD COLUMN campaign_tag TEXT")

    # Seed community feed posts so dashboard looks alive in demos.
    owner_row = cur.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1").fetchone()
    if owner_row:
        owner_id = int(owner_row["id"])
        seed_posts = [
            ("Sunrise Walk at East Coast", "Morning walk with seniors and youth along East Coast Park.", "https://images.unsplash.com/photo-1475483768296-6163e08872a1?auto=format&fit=crop&w=1200&q=80"),
            ("Digital Buddies at Jurong Library", "Helped with e-payment setup and scam awareness tips.", "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1200&q=80"),
            ("Heritage Story Circle", "Listening to kampong stories at the National Library.", "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80"),
            ("Community Garden Day", "Planted herbs together and shared gardening tips.", "https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=1200&q=80"),
            ("Tech Help Booth @ Tampines", "Quick phone settings clinic for safe messaging and photos.", "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1200&q=80"),
            ("Board Games Social", "A friendly afternoon of games and laughter.", "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80"),
            ("Walk & Talk at Marina Bay", "Gentle walk, hydration breaks, and new friendships.", "https://images.unsplash.com/photo-1470004914212-05527e49370b?auto=format&fit=crop&w=1200&q=80"),
            ("Cooking Memories Session", "Traditional recipes and stories from different generations.", "https://images.unsplash.com/photo-1466637574441-749b8f19452f?auto=format&fit=crop&w=1200&q=80"),
            ("Cyber Safety Clinic", "Learned how to identify scam links and protect accounts.", "https://images.unsplash.com/photo-1510511459019-5dda7724fd87?auto=format&fit=crop&w=1200&q=80"),
            ("Intergen Photo Walk", "Captured neighborhood landmarks together.", "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=80"),
            ("Volunteer Day at CC", "Youth volunteers assisting seniors with transport apps.", "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1200&q=80"),
            ("Weekend Wellness Meetup", "Stretching, breathing, and wellbeing check-in.", "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=1200&q=80"),
        ]
        existing_titles = {
            r["title"]
            for r in cur.execute(
                "SELECT title FROM scrapbook_entries WHERE owner_user_id = ? AND visibility = 'community'",
                (owner_id,),
            ).fetchall()
        }
        for title, caption, media_url in seed_posts:
            if title in existing_titles:
                continue
            cur.execute(
                """
                INSERT INTO scrapbook_entries
                    (owner_user_id, related_user_id, circle_title, entry_type, title, content, visibility, featured, campaign_tag, created_at)
                VALUES (?, NULL, NULL, 'challenge', ?, ?, 'community', 0, NULL, ?)
                """,
                (owner_id, title, caption, _utc_now_iso()),
            )
            entry_id = int(cur.lastrowid)
            cur.execute(
                """
                INSERT INTO scrapbook_media (entry_id, media_type, file_path, uploaded_by, created_at)
                VALUES (?, 'image', ?, ?, ?)
                """,
                (entry_id, media_url, owner_id, _utc_now_iso()),
            )
    conn.commit()
    conn.close()


def _init_avatar_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_avatar (
            user_id INTEGER PRIMARY KEY,
            config_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            snapshot_path TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _init_admin_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            action TEXT NOT NULL,
            user_id INTEGER,
            meta_json TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def _init_meta_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def _init_notifications_schema():
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            meta_json TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_notifications_user
            ON notifications(user_id, is_read, created_at);
        """
    )
    count = cur.execute("SELECT COUNT(*) AS c FROM notifications").fetchone()["c"]
    if count == 0:
        cur.execute(
            "INSERT INTO notifications (user_id, type, message, meta_json, is_read, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (None, "system", "Welcome to Re:Connect SG! New weekly challenges are live.", json.dumps({}), _utc_now_iso()),
        )
    conn.commit()
    conn.close()


def _week_start(dt: datetime) -> datetime:
    return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def _ensure_safety_score(user_id: int) -> int:
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT score FROM safety_scores WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        conn.close()
        return int(row["score"])
    score = 50
    cur.execute(
        "INSERT INTO safety_scores (user_id, score, last_updated) VALUES (?, ?, ?)",
        (user_id, score, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    return score


def _recompute_safety_score(user_id: int) -> int:
    conn = _get_main_conn()
    cur = conn.cursor()
    base = 50
    total = cur.execute(
        "SELECT COALESCE(SUM(points), 0) AS total FROM safety_events WHERE user_id = ?", (user_id,)
    ).fetchone()["total"]
    score = max(0, min(100, base + int(total)))
    cur.execute(
        "INSERT OR REPLACE INTO safety_scores (user_id, score, last_updated) VALUES (?, ?, ?)",
        (user_id, score, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    return score


def _add_safety_event(user_id: int, event_type: str, points: int, details: str = None, ref_id: str = None) -> int:
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO safety_events (user_id, event_type, points, ref_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, event_type, int(points), ref_id, details, _utc_now_iso()),
    )
    conn.commit()
    conn.close()
    return _recompute_safety_score(user_id)


def _get_safety_snapshot(user_id: int) -> dict:
    score = _ensure_safety_score(user_id)
    conn = _get_main_conn()
    cur = conn.cursor()
    events = cur.execute(
        """
        SELECT event_type, points, details, created_at
        FROM safety_events
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    tier = "green" if score >= 80 else ("yellow" if score >= 40 else "red")
    return {
        "score": score,
        "tier": tier,
        "trusted": score >= 80,
        "events": [
            {
                "event_type": e["event_type"],
                "points": e["points"],
                "details": e["details"] or "",
                "created_at": e["created_at"],
            }
            for e in events
        ],
    }


def _partner_circle_keywords():
    return ["dbs", "singtel", "scam", "govtech", "spf"]


def _is_partner_circle(title: str) -> bool:
    if not title:
        return False
    lowered = title.lower()
    return any(k in lowered for k in _partner_circle_keywords())


def _normalize_mood(mood: str) -> str:
    m = (mood or "").strip().lower()
    if m == "lonely":
        return "sad"
    if m in WELLBEING_MOOD_SCORES:
        return m
    return "neutral"


def _format_mood(mood: str) -> str:
    meta = WELLBEING_MOOD_META.get(_normalize_mood(mood), WELLBEING_MOOD_META["neutral"])
    return f"{meta['emoji']} {meta['label']}"


def _parse_iso_dt(raw: str):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", ""))
    except Exception:
        return None


def _humanize_relative_time(raw: str) -> str:
    dt = _parse_iso_dt(raw)
    if not dt:
        return ""
    delta = datetime.utcnow() - dt
    mins = int(max(delta.total_seconds(), 0) // 60)
    if mins < 60:
        return f"{mins} min ago" if mins != 1 else "1 min ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs} hr ago" if hrs == 1 else f"{hrs} hrs ago"
    days = hrs // 24
    return f"{days} day ago" if days == 1 else f"{days} days ago"


def _get_weekly_checkin(user_id: int, now: datetime = None):
    now = now or datetime.utcnow()
    start = _week_start(now)
    end = start + timedelta(days=7)
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT id, mood, reason, notes, created_at
        FROM mood_checkins
        WHERE user_id = ? AND created_at >= ? AND created_at < ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, start.isoformat(), end.isoformat()),
    ).fetchone()
    conn.close()
    return row


def _get_latest_checkin(user_id: int):
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT id, mood, reason, notes, created_at
        FROM mood_checkins
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def _get_recent_checkins(user_id: int, limit: int = 8):
    conn = _get_main_conn()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT mood, reason, notes, created_at
        FROM mood_checkins
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows


def _activity_snapshot(user_id: int):
    conn = _get_main_conn()
    cur = conn.cursor()
    user_row = cur.execute("SELECT full_name FROM users WHERE id = ?", (user_id,)).fetchone()
    full_name = (user_row["full_name"] if user_row else "") or ""
    now = datetime.utcnow()
    week_start = _week_start(now).isoformat()
    circles = cur.execute(
        "SELECT COUNT(*) AS c FROM circle_signups WHERE user_id = ? AND created_at >= ?",
        (user_id, week_start),
    ).fetchone()["c"]
    messages = cur.execute(
        "SELECT COUNT(*) AS c FROM messages WHERE sender = ? AND created_at >= ?",
        (full_name, week_start),
    ).fetchone()["c"] if full_name else 0
    challenges = cur.execute(
        "SELECT COUNT(*) AS c FROM challenge_entries WHERE user_id = ? AND created_at >= ?",
        (user_id, week_start),
    ).fetchone()["c"]
    conn.close()
    return {"circles": int(circles), "messages": int(messages), "challenges": int(challenges)}


def _trend_from_checkins(rows: list) -> dict:
    if not rows:
        return {"arrow": "➡", "label": "Stable", "delta": 0}
    scores = [WELLBEING_MOOD_SCORES.get(_normalize_mood(r["mood"]), 3) for r in rows]
    recent = scores[:7]
    prev = scores[7:14]
    if not prev:
        prev = recent
    recent_avg = sum(recent) / max(len(recent), 1)
    prev_avg = sum(prev) / max(len(prev), 1)
    delta = round(recent_avg - prev_avg, 2)
    if delta >= 0.3:
        return {"arrow": "⬆", "label": "Improving", "delta": delta}
    if delta <= -0.3:
        return {"arrow": "⬇", "label": "Declining", "delta": delta}
    return {"arrow": "➡", "label": "Stable", "delta": delta}


def _emotion_breakdown(rows: list) -> list:
    base = {k: 0 for k in WELLBEING_MOOD_META.keys()}
    for r in rows:
        base[_normalize_mood(r["mood"])] = base.get(_normalize_mood(r["mood"]), 0) + 1
    total = sum(base.values()) or 1
    return [
        {
            "mood": mood,
            "label": WELLBEING_MOOD_META[mood]["label"],
            "emoji": WELLBEING_MOOD_META[mood]["emoji"],
            "count": count,
            "pct": round((count / total) * 100),
        }
        for mood, count in base.items()
    ]


def _line_points_30d(rows: list) -> list:
    now = datetime.utcnow()
    by_day = {}
    for r in rows:
        dt = _parse_iso_dt(r["created_at"])
        if not dt:
            continue
        day_key = dt.date().isoformat()
        by_day.setdefault(day_key, []).append(WELLBEING_MOOD_SCORES.get(_normalize_mood(r["mood"]), 3))
    points = []
    for offset in range(29, -1, -1):
        day = (now - timedelta(days=offset)).date()
        vals = by_day.get(day.isoformat(), [])
        avg = round(sum(vals) / len(vals), 2) if vals else None
        points.append({"day": day.isoformat(), "value": avg})
    return points


def _mood_points_7d(rows: list) -> list:
    now = datetime.utcnow().date()
    by_day = {}
    for r in rows:
        dt = _parse_iso_dt(r["created_at"])
        if not dt:
            continue
        key = dt.date().isoformat()
        by_day.setdefault(key, []).append(WELLBEING_MOOD_SCORES.get(_normalize_mood(r["mood"]), 3))
    points = []
    for offset in range(6, -1, -1):
        day = now - timedelta(days=offset)
        vals = by_day.get(day.isoformat(), [])
        avg = round(sum(vals) / len(vals), 2) if vals else None
        rounded = int(round(avg)) if isinstance(avg, (int, float)) else 3
        mood_key = next((k for k, s in WELLBEING_MOOD_SCORES.items() if s == rounded), "neutral")
        points.append(
            {
                "day": day.isoformat(),
                "day_label": day.strftime("%a"),
                "value": avg,
                "emoji": WELLBEING_MOOD_META[mood_key]["emoji"] if vals else "•",
            }
        )
    return points


def _daily_activity_7d(user_id: int) -> list:
    conn = _get_main_conn()
    cur = conn.cursor()
    user_row = cur.execute("SELECT full_name FROM users WHERE id = ?", (user_id,)).fetchone()
    full_name = (user_row["full_name"] if user_row else "") or ""
    start = (datetime.utcnow().date() - timedelta(days=6)).isoformat()
    circles_rows = cur.execute(
        "SELECT substr(created_at, 1, 10) AS d, COUNT(*) AS c FROM circle_signups WHERE user_id = ? AND created_at >= ? GROUP BY d",
        (user_id, start),
    ).fetchall()
    msg_rows = cur.execute(
        "SELECT substr(created_at, 1, 10) AS d, COUNT(*) AS c FROM messages WHERE sender = ? AND created_at >= ? GROUP BY d",
        (full_name, start),
    ).fetchall() if full_name else []
    challenge_rows = cur.execute(
        "SELECT substr(created_at, 1, 10) AS d, COUNT(*) AS c FROM challenge_entries WHERE user_id = ? AND created_at >= ? GROUP BY d",
        (user_id, start),
    ).fetchall()
    conn.close()

    merged = {}
    for row in circles_rows:
        merged[row["d"]] = merged.get(row["d"], 0) + int(row["c"]) * 2
    for row in msg_rows:
        merged[row["d"]] = merged.get(row["d"], 0) + int(row["c"])
    for row in challenge_rows:
        merged[row["d"]] = merged.get(row["d"], 0) + int(row["c"]) * 3

    out = []
    for offset in range(6, -1, -1):
        day = (datetime.utcnow().date() - timedelta(days=offset))
        raw = int(merged.get(day.isoformat(), 0))
        intensity = min(5, raw)
        out.append(
            {
                "day": day.isoformat(),
                "day_label": day.strftime("%a"),
                "value": raw,
                "intensity": intensity,
            }
        )
    return out


def _social_energy(activity: dict) -> dict:
    score = int(min(100, activity["circles"] * 20 + activity["messages"] * 2 + activity["challenges"] * 18))
    if score >= 70:
        level = "High"
        filled = 5
    elif score >= 40:
        level = "Medium"
        filled = 3
    elif score >= 15:
        level = "Low"
        filled = 2
    else:
        level = "Very Low"
        filled = 1
    return {"score": score, "level": level, "filled": filled, "total": 5}


def _risk_status(rows: list) -> dict:
    if not rows:
        return {"level": "low", "show": False, "message": ""}
    recent = [_normalize_mood(r["mood"]) for r in rows[:5]]
    negative = sum(1 for m in recent if m in {"stressed", "sad"})
    streak = 0
    for mood in recent:
        if mood in {"stressed", "sad"}:
            streak += 1
        else:
            break
    if streak >= 3 or negative >= 4:
        return {
            "level": "high",
            "show": True,
            "message": "We are here for you. Explore support circles or message a buddy.",
        }
    if streak >= 2 or negative >= 3:
        return {
            "level": "medium",
            "show": True,
            "message": "You seem a bit low lately. A small social step can help.",
        }
    return {"level": "low", "show": False, "message": ""}


def _build_wellbeing_recos(mood: str):
    mood = _normalize_mood(mood)
    if mood in {"sad", "stressed"}:
        return [
            {"type": "circle", "title": "Join a Support Circle", "link": "/learning-circles"},
            {"type": "match", "title": "Message a Buddy Match", "link": "/messages"},
            {"type": "forum", "title": "Read encouraging stories", "link": "/forum"},
        ]
    if mood == "neutral":
        return [
            {"type": "challenge", "title": "Try this week's challenge", "link": "/challenges"},
            {"type": "circle", "title": "Join one learning circle", "link": "/learning-circles"},
            {"type": "forum", "title": "Post in the Wisdom Forum", "link": "/forum"},
        ]
    return [
        {"type": "forum", "title": "Share a win in the forum", "link": "/forum"},
        {"type": "circle", "title": "Host or join a circle", "link": "/learning-circles"},
        {"type": "match", "title": "Encourage a connection", "link": "/messages"},
    ]


def _store_wellbeing_recos(user_id: int, mood: str, recos: list):
    conn = _get_main_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM wellbeing_recos WHERE user_id = ?", (user_id,))
    for r in recos:
        norm_mood = _normalize_mood(mood)
        cur.execute(
            """
            INSERT INTO wellbeing_recos (user_id, mood, reco_type, reco_title, reco_link, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, norm_mood, r["type"], r["title"], r.get("link"), _utc_now_iso()),
        )
    conn.commit()
    conn.close()


def _load_wellbeing_recos(user_id: int):
    conn = _get_main_conn()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT reco_type, reco_title, reco_link, created_at
        FROM wellbeing_recos
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 6
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "type": r["reco_type"],
            "title": r["reco_title"],
            "link": r["reco_link"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def _get_scrapbook_settings(user_id: int) -> dict:
    settings = _get_user_settings_map(user_id)
    theme = (settings.get("scrapbook_theme") or "vintage").strip().lower()
    view = (settings.get("scrapbook_view") or "book").strip().lower()
    return {"theme": theme, "view": view}


def _set_scrapbook_settings(user_id: int, theme: str = None, view: str = None):
    if theme:
        _set_user_setting(user_id, "scrapbook_theme", theme)
    if view:
        _set_user_setting(user_id, "scrapbook_view", view)


def _wellbeing_insight(user_id: int) -> str:
    rows = _get_recent_checkins(user_id, limit=12)
    if len(rows) < 2:
        return ""
    moods = [_normalize_mood(r["mood"]) for r in rows[:3]]
    if moods[:2] == ["sad", "sad"] or moods[:2] == ["stressed", "stressed"]:
        return "You have had a tough streak. Try a low-pressure social activity today."
    trend = _trend_from_checkins(rows)
    if trend["label"] == "Improving":
        return "Your mood trend is improving in the last 7 days."
    if trend["label"] == "Declining":
        return "Your mood trend dipped this week. A buddy message may help."
    return "Your mood is stable this week."


def _wellbeing_score(rows: list, activity: dict) -> int:
    mood_vals = [WELLBEING_MOOD_SCORES.get(_normalize_mood(r["mood"]), 3) for r in rows[:14]]
    mood_avg = (sum(mood_vals) / len(mood_vals)) if mood_vals else 3
    mood_component = ((mood_avg - 1) / 4) * 60
    engagement_raw = activity["circles"] * 6 + activity["messages"] * 1.2 + activity["challenges"] * 8
    engagement_component = min(30, engagement_raw)
    checkin_days = len({_parse_iso_dt(r["created_at"]).date().isoformat() for r in rows[:7] if _parse_iso_dt(r["created_at"])})
    consistency_component = min(10, checkin_days * 2)
    score = int(round(mood_component + engagement_component + consistency_component))
    return max(0, min(100, score))


def _wellbeing_badges(rows: list, activity: dict) -> list:
    badges = []
    if activity["messages"] >= 10:
        badges.append({"name": "Active Listener", "unlocked": True})
    if activity["circles"] >= 2:
        badges.append({"name": "Community Helper", "unlocked": True})
    positive = sum(1 for r in rows[:14] if _normalize_mood(r["mood"]) in {"happy", "good"})
    if positive >= 7:
        badges.append({"name": "Positivity Builder", "unlocked": True})
    if not badges:
        badges = [
            {"name": "Positivity Builder", "unlocked": False},
            {"name": "Active Listener", "unlocked": False},
            {"name": "Community Helper", "unlocked": False},
        ]
    return badges


def _wellbeing_analytics(user_id: int) -> dict:
    rows = _get_recent_checkins(user_id, limit=60)
    activity = _activity_snapshot(user_id)
    daily_activity = _daily_activity_7d(user_id)
    trend = _trend_from_checkins(rows)
    breakdown = _emotion_breakdown(rows[:30])
    weekly_breakdown = _emotion_breakdown(rows[:7] if rows else [])
    score = _wellbeing_score(rows, activity)
    risk = _risk_status(rows)
    latest_mood = _normalize_mood(rows[0]["mood"]) if rows else "neutral"
    recommendations = _build_wellbeing_recos(latest_mood)
    insights = []
    if trend["label"] == "Improving":
        insights.append("Your mood is improving compared to the previous week.")
    elif trend["label"] == "Declining":
        insights.append("Your mood trend dipped this week. A quick check-in with a buddy may help.")
    else:
        insights.append("Your mood trend is steady this week.")
    if activity["circles"] > 0 and activity["messages"] > 0:
        insights.append("You tend to feel better on days with social activity.")
    if activity["messages"] == 0:
        insights.append("You have not messaged anyone this week. A short hello can boost connection.")
    if risk["level"] == "high":
        insights.append("You have had repeated low moods. Consider support circles and trusted contacts.")
    while len(insights) < 3:
        insights.append("Small daily reflections can improve emotional awareness over time.")
    return {
        "trend": trend,
        "activity": activity,
        "daily_activity_7d": daily_activity,
        "social_energy": _social_energy(activity),
        "emotion_breakdown": breakdown,
        "weekly_distribution": weekly_breakdown,
        "line_points_30d": _line_points_30d(rows),
        "mood_points_7d": _mood_points_7d(rows),
        "recommendations": recommendations,
        "insights": insights[:3],
        "risk": risk,
        "score": score,
        "badges": _wellbeing_badges(rows, activity),
    }


def _wellbeing_nudge(user_id: int, analytics: dict = None) -> str:
    data = analytics or _wellbeing_analytics(user_id)
    activity = data["activity"]
    trend = data["trend"]["label"]
    if activity["circles"] > 0 and trend == "Improving":
        return "You feel happier on days you join Learning Circles."
    if activity["messages"] == 0 and activity["circles"] == 0:
        return "You have not interacted this week. Say hi to a buddy?"
    if data["risk"]["show"]:
        return "We are here for you. Explore support circles when ready."
    return "Keep your momentum going with one meaningful interaction today."


def _log_audit(component: str, action: str, user_id: int = None, meta: dict = None) -> None:
    try:
        conn = _get_main_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO audit_logs (component, action, user_id, meta_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                component,
                action,
                user_id,
                json.dumps(meta or {}),
                _utc_now_iso(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _add_notification(user_id: int, notif_type: str, message: str, meta: dict = None) -> None:
    try:
        conn = _get_main_conn()
        conn.execute(
            "INSERT INTO notifications (user_id, type, message, meta_json, is_read, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (user_id, notif_type, message, json.dumps(meta or {}), _utc_now_iso()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    try:
        nt = (notif_type or "").strip().lower()
        if nt in {"achievement", "reward", "badge", "quest"}:
            _send_achievement_email_if_enabled(int(user_id), message)
    except Exception:
        pass


def _send_platform_email(to_email: str, subject: str, body: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int((os.getenv("SMTP_PORT", "587") or "587").strip())
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    from_email = os.getenv("SMTP_FROM", smtp_user or "no-reply@reconnect.local")
    use_tls = (os.getenv("SMTP_USE_TLS", "1") or "1").strip() == "1"
    if not smtp_host:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_user:
                smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        return True
    except Exception:
        return False


def _apply_trust_delta(user_id: int, delta: int, reason: str = "") -> int:
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT COALESCE(trust_score, 50) AS trust_score FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    current = int(row["trust_score"] if row else 50)
    updated = max(0, min(100, current + int(delta)))
    cur.execute("UPDATE users SET trust_score = ? WHERE id = ?", (updated, user_id))
    conn.commit()
    conn.close()
    if delta != 0:
        _add_safety_event(user_id, "trust_delta", int(delta), reason or "Trust score adjusted")
        _check_and_unlock_titles(user_id)
    return updated


def _refresh_user_rating(reviewee_id: int):
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT COALESCE(AVG(rating), 0) AS avg_rating, COUNT(*) AS c FROM reviews WHERE reviewee_id = ?",
        (reviewee_id,),
    ).fetchone()
    avg_rating = float(row["avg_rating"] or 0.0)
    count = int(row["c"] or 0)
    cur.execute(
        "UPDATE users SET avg_rating = ?, review_count = ? WHERE id = ?",
        (avg_rating, count, reviewee_id),
    )
    conn.commit()
    conn.close()


def _is_senior_user(user_id: int) -> bool:
    conn = _get_main_conn()
    row = conn.execute("SELECT COALESCE(member_type, '') AS member_type FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    member_type = (row["member_type"] if row else "") or ""
    return member_type.strip().lower() in {"senior", "elderly"}


def _is_youth_user(user_id: int) -> bool:
    return not _is_senior_user(user_id)


def _set_user_verification_badges(user_id: int, badges: list[str], verified_by: str | None = None) -> list[str]:
    cleaned = []
    seen = set()
    for badge in badges or []:
        text = str(badge or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    conn = _get_main_conn()
    conn.execute(
        "UPDATE users SET verification_badges_json = ?, verified_by = COALESCE(?, verified_by) WHERE id = ?",
        (json.dumps(cleaned), (verified_by or "").strip() or None, user_id),
    )
    conn.commit()
    conn.close()
    return cleaned


def _get_user_verification_badges(user_id: int) -> list[str]:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT verification_badges_json FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return _safe_json((row["verification_badges_json"] if row else "[]") or "[]", [])


def _recompute_total_volunteer_hours(user_id: int) -> float:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(hours), 0) AS total FROM volunteer_hours WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    total = float(row["total"] if row else 0.0)
    conn.execute("UPDATE users SET total_volunteer_hours = ? WHERE id = ?", (total, user_id))
    conn.commit()
    conn.close()
    return total


def _record_volunteer_hours(user_id: int, source_type: str, source_id: int, hours: float, notes: str = "") -> bool:
    if not _is_youth_user(user_id):
        return False
    source_type = (source_type or "").strip().lower()
    if source_type not in {"meetup", "learning_circle", "event", "workshop"}:
        return False
    try:
        source_id = int(source_id)
        hours = float(hours)
    except (TypeError, ValueError):
        return False
    if source_id <= 0 or hours <= 0:
        return False
    conn = _get_main_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO volunteer_hours (user_id, source_type, source_id, hours, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, source_type, source_id, round(hours, 2), (notes or "").strip() or None, _utc_now_iso()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    total = _recompute_total_volunteer_hours(user_id)
    _add_notification(user_id, "volunteer", f"Volunteer hours updated (+{round(hours, 2)}h).", {"source_type": source_type, "source_id": source_id, "hours": round(hours, 2), "total": total})
    _check_and_unlock_titles(user_id)
    return True


def _title_id_by_code(code: str) -> int | None:
    conn = _get_main_conn()
    row = conn.execute("SELECT id FROM titles WHERE code = ?", (code,)).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _unlock_title(user_id: int, code: str) -> bool:
    title_id = _title_id_by_code(code)
    if not title_id:
        return False
    conn = _get_main_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO user_titles (user_id, title_id, unlocked_at) VALUES (?, ?, ?)",
            (user_id, title_id, _utc_now_iso()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    row = cur.execute("SELECT display_name FROM titles WHERE id = ?", (title_id,)).fetchone()
    conn.close()
    _add_notification(user_id, "title", f"New Title Unlocked: {(row['display_name'] if row else code)}", {"title_id": title_id, "code": code})
    return True


def _check_and_unlock_titles(user_id: int):
    conn = _get_main_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT COALESCE(total_volunteer_hours, 0) AS h, COALESCE(trust_score, 50) AS t FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    volunteer_hours = float(row["h"] if row else 0.0)
    trust_score = int(row["t"] if row else 50)
    circles = int(
        cur.execute("SELECT COUNT(*) AS c FROM circle_signups WHERE user_id = ?", (user_id,)).fetchone()["c"]
    )
    community_posts = int(
        cur.execute(
            "SELECT COUNT(*) AS c FROM scrapbook_entries WHERE owner_user_id = ? AND visibility = 'community'",
            (user_id,),
        ).fetchone()["c"]
    )
    conn.close()

    if volunteer_hours >= 5:
        _unlock_title(user_id, "helper")
    if volunteer_hours >= 20:
        _unlock_title(user_id, "community_builder")
    if volunteer_hours >= 50:
        _unlock_title(user_id, "mentor_in_training")
    if volunteer_hours >= 100:
        _unlock_title(user_id, "impact_leader")
    if circles >= 3:
        _unlock_title(user_id, "circle_starter")
    if circles >= 10:
        _unlock_title(user_id, "knowledge_guide")
    if trust_score >= 80:
        _unlock_title(user_id, "trusted_connector")
    if community_posts >= 10:
        _unlock_title(user_id, "storyteller")


def _profile_titles_payload(user_id: int) -> dict:
    conn = _get_main_conn()
    cur = conn.cursor()
    unlocked = cur.execute(
        """
        SELECT t.id, t.code, t.display_name, t.description, ut.unlocked_at
        FROM user_titles ut
        JOIN titles t ON t.id = ut.title_id
        WHERE ut.user_id = ?
        ORDER BY ut.unlocked_at DESC
        """,
        (user_id,),
    ).fetchall()
    equipped_row = cur.execute(
        """
        SELECT t.id, t.code, t.display_name
        FROM users u
        LEFT JOIN titles t ON t.id = u.equipped_title_id
        WHERE u.id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()
    equipped = None
    if equipped_row and equipped_row["id"] is not None:
        equipped = {"id": equipped_row["id"], "code": equipped_row["code"], "display_name": equipped_row["display_name"]}
    return {
        "equipped": equipped,
        "titles": [
            {
                "id": r["id"],
                "code": r["code"],
                "display_name": r["display_name"],
                "description": r["description"] or "",
                "unlocked_at": r["unlocked_at"],
            }
            for r in unlocked
        ],
    }


def _organiser_badge(organiser_type: str) -> str:
    o = (organiser_type or "").strip().lower()
    if o == "government":
        return "Gov Programme"
    if o == "corporate":
        return "Corporate Volunteer Event"
    if o == "community":
        return "Community Hosted"
    return "Admin Hosted"


def _duration_hours(start_iso: str, end_iso: str | None, default_hours: float = 2.0) -> float:
    start_dt = _parse_iso_dt(start_iso)
    end_dt = _parse_iso_dt(end_iso or "")
    if not start_dt or not end_dt:
        return float(default_hours)
    hours = (end_dt - start_dt).total_seconds() / 3600.0
    if hours <= 0:
        return float(default_hours)
    return max(0.5, min(12.0, round(hours, 2)))


def _hours_from_text(raw: str, default_hours: float = 2.0) -> float:
    text = str(raw or "").strip().lower()
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        return float(default_hours)
    try:
        value = float(m.group(1))
    except Exception:
        return float(default_hours)
    return max(0.5, min(12.0, value))


def _is_checkin_window(start_iso: str, before_minutes: int = 30, after_minutes: int = 120) -> bool:
    dt = _parse_iso_dt(start_iso)
    if not dt:
        return False
    now = datetime.utcnow()
    return (dt - timedelta(minutes=before_minutes)) <= now <= (dt + timedelta(minutes=after_minutes))


def _send_achievement_email_if_enabled(user_id: int, title: str):
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT email, COALESCE(email_notifications_enabled, 1) AS enabled FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return
    if int(row["enabled"] or 0) != 1:
        return
    email = (row["email"] or "").strip()
    if not email:
        return
    _send_platform_email(
        email,
        "Re:Connect Reward Unlocked",
        f"You unlocked a reward/achievement: {title}\n\nKeep building meaningful connections on Re:Connect.",
    )


def _run_reminder_notifications_for_user(user_id: int):
    conn = _get_main_conn()
    cur = conn.cursor()
    now = datetime.utcnow()
    windows = [(24, "24h"), (2, "2h")]
    meetup_rows = cur.execute(
        """
        SELECT id, meetup_time, user1_id, user2_id, status
        FROM meetups
        WHERE status IN ('proposed','confirmed','rescheduled')
          AND (user1_id = ? OR user2_id = ?)
        ORDER BY meetup_time ASC
        LIMIT 120
        """,
        (user_id, user_id),
    ).fetchall()
    event_rows = cur.execute(
        """
        SELECT e.id, e.title, e.start_time
        FROM events e
        JOIN event_rsvps r ON r.event_id = e.id
        WHERE r.user_id = ? AND r.status IN ('going','interested')
        ORDER BY e.start_time ASC
        LIMIT 120
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    def _notification_key_exists(key: str) -> bool:
        c = _get_main_conn()
        r = c.execute(
            "SELECT 1 FROM notifications WHERE user_id = ? AND meta_json LIKE ? LIMIT 1",
            (user_id, f"%{key}%"),
        ).fetchone()
        c.close()
        return bool(r)

    for row in meetup_rows:
        dt = _parse_iso_dt(row["meetup_time"])
        if not dt:
            continue
        hours_left = (dt - now).total_seconds() / 3600.0
        for threshold, label in windows:
            if 0 <= hours_left <= threshold:
                key = f"meetup_reminder_{label}_{row['id']}"
                if not _notification_key_exists(key):
                    _add_notification(user_id, "meetup_reminder", f"Meetup reminder ({label})", {"meetup_id": row["id"], "key": key})
                break

    for row in event_rows:
        dt = _parse_iso_dt(row["start_time"])
        if not dt:
            continue
        hours_left = (dt - now).total_seconds() / 3600.0
        for threshold, label in windows:
            if 0 <= hours_left <= threshold:
                key = f"event_reminder_{label}_{row['id']}"
                if not _notification_key_exists(key):
                    _add_notification(user_id, "event_reminder", f"Event reminder ({label}): {row['title']}", {"event_id": row["id"], "key": key})
                break


def _get_current_challenge():
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT id, title, description, reward_points, week_label, created_at FROM weekly_challenges ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row


def _get_user_points(user_id: int) -> tuple[int, int]:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT COALESCE(total_points, 0) AS total_points, COALESCE(available_points, 0) AS available_points FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return (0, 0)
    return (int(row["total_points"] or 0), int(row["available_points"] or 0))


def _list_challenge_entries(challenge_id: int, limit: int | None = None):
    conn = _get_main_conn()
    sql = """SELECT id, challenge_id, user_id, author_name, content, image_url, created_at
           FROM challenge_entries
           WHERE challenge_id = ?
           ORDER BY id DESC"""
    params: tuple = (challenge_id,)
    if isinstance(limit, int) and limit > 0:
        sql += " LIMIT ?"
        params = (challenge_id, int(limit))
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def _list_entry_comments(entry_id: int, limit: int | None = None):
    conn = _get_main_conn()
    sql = """SELECT id, entry_id, user_id, author_name, content, created_at
           FROM challenge_comments
           WHERE entry_id = ?
           ORDER BY id ASC"""
    params: tuple = (entry_id,)
    if isinstance(limit, int) and limit > 0:
        sql += " LIMIT ?"
        params = (entry_id, int(limit))
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def _count_challenge_entries(challenge_id: int) -> int:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM challenge_entries WHERE challenge_id = ?",
        (challenge_id,),
    ).fetchone()
    conn.close()
    return int(row["c"] if row else 0)


def _count_challenge_entry_likes(entry_id: int) -> int:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM challenge_entry_likes WHERE entry_id = ?",
        (entry_id,),
    ).fetchone()
    conn.close()
    return row["c"] if row else 0


def _has_challenge_entry_like(entry_id: int, user_id: int) -> bool:
    conn = _get_main_conn()
    row = conn.execute(
        "SELECT 1 FROM challenge_entry_likes WHERE entry_id = ? AND user_id = ?",
        (entry_id, user_id),
    ).fetchone()
    conn.close()
    return bool(row)


def _init_ach_schema():
    conn = _get_ach_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            threshold INTEGER NOT NULL,
            requirement_type TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS landmarks (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            story TEXT NOT NULL,
            question TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS landmark_options (
            id INTEGER PRIMARY KEY,
            landmark_id INTEGER NOT NULL,
            option_text TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            FOREIGN KEY (landmark_id) REFERENCES landmarks(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reward INTEGER NOT NULL,
            total_required INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            cost INTEGER NOT NULL,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            sponsor_type TEXT NOT NULL DEFAULT 'none',
            sponsor_name TEXT,
            reward_type TEXT,
            redemption_method TEXT,
            redemption_code TEXT
        );
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            required_count INTEGER NOT NULL,
            parent_id INTEGER,
            category TEXT NOT NULL,
            level INTEGER NOT NULL,
            icon TEXT NOT NULL,
            reward_points INTEGER NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES skills(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS checkin_rewards (
            id INTEGER PRIMARY KEY,
            streak_days INTEGER NOT NULL,
            reward_points INTEGER NOT NULL,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_id INTEGER NOT NULL,
            earned INTEGER NOT NULL DEFAULT 0,
            earned_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (badge_id) REFERENCES badges(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS user_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS user_landmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            landmark_id INTEGER NOT NULL,
            unlocked INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            unlocked_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (landmark_id) REFERENCES landmarks(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS user_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quest_id INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS user_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_id INTEGER NOT NULL,
            redeemed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reward_id) REFERENCES rewards(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS user_skill_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            reward_points INTEGER NOT NULL,
            rewarded_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS user_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
        );
        """
    )

    # Ensure achievements columns exist on the main users table.
    user_cols = {row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    def _add_col(name: str, ddl: str):
        if name not in user_cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {ddl}")
            user_cols.add(name)

    _add_col("total_points", "total_points INTEGER NOT NULL DEFAULT 0")
    _add_col("available_points", "available_points INTEGER NOT NULL DEFAULT 0")
    _add_col("active_days", "active_days INTEGER NOT NULL DEFAULT 0")
    _add_col("current_tier", "current_tier INTEGER NOT NULL DEFAULT 1")
    _add_col("current_streak", "current_streak INTEGER NOT NULL DEFAULT 0")
    _add_col("is_admin", "is_admin INTEGER NOT NULL DEFAULT 0")

    reward_cols = {row["name"] for row in cur.execute("PRAGMA table_info(rewards)").fetchall()}
    if "sponsor_type" not in reward_cols:
        cur.execute("ALTER TABLE rewards ADD COLUMN sponsor_type TEXT NOT NULL DEFAULT 'none'")
    if "sponsor_name" not in reward_cols:
        cur.execute("ALTER TABLE rewards ADD COLUMN sponsor_name TEXT")
    if "reward_type" not in reward_cols:
        cur.execute("ALTER TABLE rewards ADD COLUMN reward_type TEXT")
    if "redemption_method" not in reward_cols:
        cur.execute("ALTER TABLE rewards ADD COLUMN redemption_method TEXT")
    if "redemption_code" not in reward_cols:
        cur.execute("ALTER TABLE rewards ADD COLUMN redemption_code TEXT")

    def _table_count(table: str) -> int:
        return cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]

    if _table_count("badges") == 0:
        cur.executemany(
            "INSERT INTO badges (id, name, icon, description, category, threshold, requirement_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "First Steps", "badge", "Unlock your first landmark", "Journey", 1, "landmarks"),
                (2, "City Explorer", "badge", "Complete 3 landmarks", "Journey", 3, "landmarks"),
                (3, "Island Voyager", "badge", "Complete all 10 landmarks", "Journey", 10, "landmarks"),
                (4, "Community Builder", "badge", "Complete 5 quests", "Community", 5, "quests"),
                (5, "Helpful Guide", "badge", "Complete 10 quests", "Community", 10, "quests"),
                (6, "Master Connector", "badge", "Complete 20 quests", "Community", 20, "quests"),
                (7, "Point Collector", "coin", "Earn 1,000 points", "Progress", 1000, "points"),
                (8, "Point Master", "trophy", "Earn 5,000 points", "Progress", 5000, "points"),
                (9, "Tier Ascender", "rocket", "Reach Tier 3", "Progress", 3, "tier"),
                (10, "Skill Starter", "badge", "Complete 5 skills", "Skills", 5, "skills"),
                (11, "Skill Builder", "badge", "Complete 10 skills", "Skills", 10, "skills"),
                (12, "Skill Master", "badge", "Complete 15 skills", "Skills", 15, "skills"),
                (13, "Skill Elite", "badge", "Complete 20 skills", "Skills", 20, "skills"),
                (14, "Digital Grandmaster", "badge", "Complete all skills", "Skills", 999, "skills"),
            ],
        )

    if _table_count("landmarks") == 0:
        cur.executemany(
            "INSERT INTO landmarks (id, name, icon, story, question, correct_answer, x, y) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Jurong", "pin", "Singapore's industrial heartland that transformed into a hub for innovation.", "What is Jurong best known for today?", 1, 220, 310),
                (2, "Chinatown", "pin", "A vibrant district preserving Chinese heritage and culture.", "What makes Chinatown special?", 1, 410, 350),
                (3, "Marina Bay", "pin", "This iconic waterfront area features Marina Bay Sands.", "How many towers does Marina Bay Sands have?", 1, 490, 340),
                (4, "Orchard Road", "pin", "Singapore's premier shopping district with over 20 malls.", "What was Orchard Road before becoming a shopping district?", 1, 380, 290),
                (5, "Kampong Glam", "pin", "The historic Malay-Muslim quarter centered around the Sultan Mosque.", "What is the famous mosque in Kampong Glam?", 1, 520, 285),
                (6, "Little India", "pin", "An ethnic district that celebrates Indian culture.", "Which festival is famously celebrated in Little India?", 1, 460, 270),
                (7, "Botanic Gardens", "pin", "A UNESCO World Heritage Site founded in 1859.", "When was the Singapore Botanic Gardens founded?", 1, 310, 250),
                (8, "Marina Bay Sands", "pin", "Marina Bay Sands features three towers connected by a sky park.", "How many towers does Marina Bay Sands have?", 1, 550, 325),
                (9, "Changi", "pin", "Home to Changi Airport, consistently rated the world's best airport.", "What is Changi best known for?", 1, 620, 285),
                (10, "Sentosa", "pin", "Singapore's island resort destination offering beaches and attractions.", "What does 'Sentosa' mean in Malay?", 0, 370, 470),
            ],
        )

    if _table_count("landmark_options") == 0:
        options = {
            1: ["Shopping malls", "Innovation hub", "Beach resorts", "Historic temples"],
            2: ["Modern skyscrapers", "Blend of heritage and modern life", "Beach activities", "Industrial sites"],
            3: ["2", "3", "4", "5"],
            4: ["Industrial area", "Fruit orchards", "Residential zone", "Fishing village"],
            5: ["Blue Mosque", "Sultan Mosque", "Crystal Mosque", "Grand Mosque"],
            6: ["Christmas", "Deepavali", "Chinese New Year", "Hari Raya"],
            7: ["1819", "1859", "1900", "1965"],
            8: ["2", "3", "4", "5"],
            9: ["Shopping malls", "World-class airport", "Historical museums", "Nature parks"],
            10: ["Peace and tranquility", "Beautiful island", "Paradise beach", "Golden sands"],
        }
        for lm_id, opts in options.items():
            for idx, text in enumerate(opts):
                cur.execute(
                    "INSERT INTO landmark_options (landmark_id, option_text, option_index) VALUES (?, ?, ?)",
                    (lm_id, text, idx),
                )

    if _table_count("quests") == 0:
        cur.executemany(
            "INSERT INTO quests (id, title, description, reward, total_required) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "Join Your First Learning Circle", "Connect with others to learn or share a skill together", 1500, 1),
                (2, "Reply in the Community Forum", "Share your thoughts or help answer someone else's question", 75, 1),
                (3, "Share a Skill", "Teach something you know - cooking, language, crafts, anything!", 200, 1),
                (4, "Thank a Connection", "Send appreciation to someone who helped you", 50, 1),
                (5, "Complete 3 Learning Sessions", "Keep learning and growing with the community", 300, 3),
            ],
        )

    if _table_count("rewards") == 0:
        cur.executemany(
            """
            INSERT INTO rewards
                (id, name, icon, cost, description, is_active, sponsor_type, sponsor_name, reward_type, redemption_method, redemption_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "$2 GrabFood Voucher", "gift", 500, None, 1, "corporate", "Grab", "voucher", "Show this in-app code", "GRAB-2"),
                (2, "$3 Starbucks Voucher", "cup", 750, None, 1, "corporate", "Starbucks", "voucher", "Show this in-app code", "STAR-3"),
                (3, "$5 Popular Bookstore", "book", 1250, None, 1, "community", "Community Book Drive", "voucher", "Show this in-app code", "BOOK-5"),
                (4, "$5 Kopitiam Voucher", "bread", 1250, None, 1, "government", "PA Active Ageing", "voucher", "Show this in-app code", "PA-KOPI5"),
                (5, "$10 NTUC Voucher", "cart", 2500, None, 1, "corporate", "NTUC FairPrice", "voucher", "Show this in-app code", "NTUC-10"),
                (6, "$10 Watsons Voucher", "bag", 2500, None, 1, "corporate", "Watsons", "voucher", "Show this in-app code", "WAT-10"),
                (7, "$15 Movie Voucher", "ticket", 3750, None, 1, "community", "Community Arts Network", "voucher", "Show this in-app code", "MOVIE-15"),
                (8, "$15 Uniqlo Voucher", "shirt", 3750, None, 1, "corporate", "Uniqlo", "merch", "Show this in-app code", "UNIQ-15"),
            ],
        )

    if _table_count("skills") == 0:
        cur.executemany(
            "INSERT INTO skills (id, name, description, required_count, parent_id, category, level, icon, reward_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "WhatsApp Basics", "Teach basic messaging and contacts.", 10, None, "Communication", 1, "whatsapp", 50),
                (2, "Emojis & Stickers", "Help seniors use emojis and stickers.", 5, 1, "Communication", 1, "emoji", 30),
                (3, "Voice Messages", "Guide seniors to send voice notes.", 5, 1, "Communication", 2, "voice", 40),
                (4, "Video Calls", "Help seniors make a video call.", 3, 3, "Communication", 3, "video", 60),
                (5, "Group Chats", "Create and manage group chats.", 3, 2, "Communication", 3, "group", 60),
                (6, "Email Basics", "Read and reply to emails.", 8, None, "Communication", 1, "email", 40),
                (7, "Email Attachments", "Send and download attachments.", 4, 6, "Communication", 2, "attachment", 50),
                (8, "Banking Login", "Log in securely to banking apps.", 6, None, "Financial", 1, "bank", 50),
                (9, "Check Balance", "Check account balances.", 4, 8, "Financial", 2, "balance", 40),
                (10, "Transfer Money", "Make a transfer safely.", 5, 9, "Financial", 2, "transfer", 60),
                (11, "Bill Payment", "Pay utility bills online.", 4, 10, "Financial", 3, "bill", 70),
                (12, "Scam Awareness", "Identify common scam patterns.", 5, None, "Safety", 1, "scam", 40),
                (13, "Password Security", "Set strong passwords and manage them.", 3, 12, "Safety", 2, "password", 50),
                (14, "Privacy Settings", "Update privacy and sharing controls.", 4, 13, "Safety", 3, "privacy", 60),
            ],
        )

    if _table_count("checkin_rewards") == 0:
        cur.executemany(
            "INSERT INTO checkin_rewards (id, streak_days, reward_points, description) VALUES (?, ?, ?, ?)",
            [(1, 7, 100, "Perfect week bonus"), (2, 30, 500, "Perfect month bonus")],
        )

    conn.commit()
    conn.close()


def _merge_legacy_databases():
    base_dir = BASE_DIR.parent.parent / "database"
    legacy_paths = [
        base_dir / "reconnect.db",
        base_dir / "sean_reconnect.db",
        base_dir / "reconnect-sg_forum.db",
        base_dir / "dashboard.db",
        base_dir / "app.db",
    ]
    legacy_paths = [p for p in legacy_paths if p.exists() and p.resolve() != DB_PATH.resolve()]
    if not legacy_paths:
        return

    conn = _get_main_conn()
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)")
    merged = cur.execute("SELECT value FROM app_meta WHERE key = ?", ("legacy_merge_done",)).fetchone()
    if merged and (merged["value"] or "").strip() == "1":
        conn.close()
        return

    def ensure_email(base: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", ".", (base or "legacy").lower()).strip(".")
        if not slug:
            slug = "legacy"
        email = f"{slug}@legacy.local"
        suffix = 1
        while cur.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            suffix += 1
            email = f"{slug}{suffix}@legacy.local"
        return email

    def ensure_user(full_name: str, email: str = None, password_hash: str = None, created_at: str = None, is_admin: int = 0) -> int:
        if email:
            row = cur.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                if full_name:
                    cur.execute("UPDATE users SET full_name = COALESCE(full_name, ?) WHERE id = ?", (full_name, row["id"]))
                return row["id"]
        email = ensure_email(full_name or "legacy-user")
        if password_hash:
            text = str(password_hash)
            if ":" not in text:
                password_hash = generate_password_hash(text)
        else:
            password_hash = generate_password_hash("legacy-import")
        created_at = created_at or _utc_now_iso()
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, member_type, created_at, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            (full_name or "Legacy User", email, password_hash, None, created_at, int(is_admin) if is_admin else 0),
        )
        return cur.lastrowid

    def ensure_legacy_user_by_name(name: str) -> int:
        name = (name or "Legacy User").strip() or "Legacy User"
        row = cur.execute("SELECT id FROM users WHERE full_name = ? LIMIT 1", (name,)).fetchone()
        if row:
            return row["id"]
        return ensure_user(name)

    def row_get(row, key: str, default=None):
        if row is None:
            return default
        if key in row.keys():
            value = row[key]
            return value if value is not None else default
        return default

    conn.commit()

    for path in legacy_paths:
        legacy = sqlite3.connect(path)
        legacy.row_factory = sqlite3.Row
        lcur = legacy.cursor()
        tables = {r["name"] for r in lcur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        if "users" in tables:
            for row in lcur.execute("SELECT * FROM users").fetchall():
                email = row_get(row, "email")
                name = row_get(row, "name") or row_get(row, "full_name") or row_get(row, "username") or "Legacy User"
                password_hash = row_get(row, "password_hash") or row_get(row, "password")
                created_at = row_get(row, "created_at")
                is_admin = row_get(row, "is_admin", 0)
                ensure_user(name, email, password_hash, created_at, is_admin)
            conn.commit()

        if "matches" in tables:
            for row in lcur.execute("SELECT * FROM matches").fetchall():
                cur.execute(
                    "INSERT OR IGNORE INTO matches (match_id, name, avatar, location, created_at) VALUES (?, ?, ?, ?, ?)",
                    (row_get(row, "match_id"), row_get(row, "name"), row_get(row, "avatar"), row_get(row, "location"), row_get(row, "created_at")),
                )
            conn.commit()

        if "messages" in tables:
            for row in lcur.execute("SELECT * FROM messages").fetchall():
                exists = cur.execute(
                    "SELECT 1 FROM messages WHERE chat_id = ? AND sender = ? AND text = ? AND created_at = ?",
                    (row_get(row, "chat_id"), row_get(row, "sender"), row_get(row, "text"), row_get(row, "created_at")),
                ).fetchone()
                if not exists:
                    cur.execute(
                        "INSERT INTO messages (chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            row_get(row, "chat_id"),
                            row_get(row, "sender"),
                            row_get(row, "text"),
                            row_get(row, "created_at"),
                            row_get(row, "edited_at"),
                            row_get(row, "is_deleted", 0),
                            row_get(row, "deleted_at"),
                        ),
                    )
            conn.commit()

        if "profanities" in tables:
            for row in lcur.execute("SELECT * FROM profanities").fetchall():
                cur.execute(
                    "INSERT OR IGNORE INTO profanities (word, level, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (row_get(row, "word"), row_get(row, "level"), row_get(row, "created_at"), row_get(row, "updated_at")),
                )
            conn.commit()

        if "posts" in tables:
            post_map = {}
            for row in lcur.execute("SELECT * FROM posts").fetchall():
                author = row_get(row, "author") or "Anonymous"
                author_id = ensure_legacy_user_by_name(author)
                existing = cur.execute(
                    "SELECT id FROM posts WHERE title = ? AND content = ? AND author = ? AND created_at = ?",
                    (row_get(row, "title"), row_get(row, "content"), author, row_get(row, "created_at")),
                ).fetchone()
                if existing:
                    post_id = existing["id"]
                else:
                    cur.execute(
                        "INSERT INTO posts (author_id, author, title, content, category, likes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            author_id,
                            author,
                            row_get(row, "title"),
                            row_get(row, "content"),
                            row_get(row, "category") or "General",
                            row_get(row, "likes") or 0,
                            row_get(row, "created_at"),
                        ),
                    )
                    post_id = cur.lastrowid
                post_map[row_get(row, "id")] = post_id
            conn.commit()

            if "comments" in tables:
                for row in lcur.execute("SELECT * FROM comments").fetchall():
                    post_id = post_map.get(row_get(row, "post_id"))
                    if not post_id:
                        continue
                    author = row_get(row, "author") or "Anonymous"
                    author_id = ensure_legacy_user_by_name(author)
                    existing = cur.execute(
                        "SELECT id FROM comments WHERE post_id = ? AND author = ? AND content = ? AND created_at = ?",
                        (post_id, author, row_get(row, "content"), row_get(row, "created_at")),
                    ).fetchone()
                    if not existing:
                        cur.execute(
                            "INSERT INTO comments (post_id, author_id, author, content, created_at) VALUES (?, ?, ?, ?, ?)",
                            (post_id, author_id, author, row_get(row, "content"), row_get(row, "created_at")),
                        )
                conn.commit()

        if "challenges" in tables:
            challenge_map = {}
            for row in lcur.execute("SELECT * FROM challenges").fetchall():
                existing = cur.execute(
                    "SELECT id FROM weekly_challenges WHERE title = ? AND description = ?",
                    (row_get(row, "title"), row_get(row, "description")),
                ).fetchone()
                if existing:
                    challenge_id = existing["id"]
                else:
                    cur.execute(
                        "INSERT INTO weekly_challenges (title, description, reward_points, week_label, created_at) VALUES (?, ?, ?, ?, ?)",
                        (
                            row_get(row, "title"),
                            row_get(row, "description"),
                            20,
                            "Legacy Challenge",
                            row_get(row, "created_at") or _utc_now_iso(),
                        ),
                    )
                    challenge_id = cur.lastrowid
                challenge_map[row_get(row, "id")] = challenge_id
            conn.commit()

            if "submissions" in tables:
                for row in lcur.execute("SELECT * FROM submissions").fetchall():
                    challenge_id = challenge_map.get(row_get(row, "challenge_id"))
                    if not challenge_id:
                        continue
                    author = row_get(row, "author") or "Legacy Participant"
                    author_id = ensure_legacy_user_by_name(author)
                    existing = cur.execute(
                        "SELECT id FROM challenge_entries WHERE challenge_id = ? AND user_id = ? AND content = ? AND created_at = ?",
                        (challenge_id, author_id, row_get(row, "content"), row_get(row, "created_at")),
                    ).fetchone()
                    if not existing:
                        cur.execute(
                            "INSERT INTO challenge_entries (challenge_id, user_id, author_name, content, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                challenge_id,
                                author_id,
                                author,
                                row_get(row, "content"),
                                row_get(row, "image_path"),
                                row_get(row, "created_at") or _utc_now_iso(),
                            ),
                        )
                conn.commit()

        if "challenge" in tables:
            challenge_map = {}
            for row in lcur.execute("SELECT * FROM challenge").fetchall():
                existing = cur.execute(
                    "SELECT id FROM weekly_challenges WHERE title = ? AND description = ?",
                    (row_get(row, "title"), row_get(row, "description")),
                ).fetchone()
                if existing:
                    challenge_id = existing["id"]
                else:
                    cur.execute(
                        "INSERT INTO weekly_challenges (title, description, reward_points, week_label, created_at) VALUES (?, ?, ?, ?, ?)",
                        (
                            row_get(row, "title"),
                            row_get(row, "description"),
                            20,
                            "Legacy Challenge",
                            _utc_now_iso(),
                        ),
                    )
                    challenge_id = cur.lastrowid
                challenge_map[row_get(row, "id")] = challenge_id
            conn.commit()

            if "submission" in tables:
                legacy_user_id = ensure_legacy_user_by_name("Legacy Participant")
                for row in lcur.execute("SELECT * FROM submission").fetchall():
                    challenge_id = challenge_map.get(row_get(row, "challenge_id"))
                    if not challenge_id:
                        continue
                    existing = cur.execute(
                        "SELECT id FROM challenge_entries WHERE challenge_id = ? AND user_id = ? AND content = ?",
                        (challenge_id, legacy_user_id, row_get(row, "content")),
                    ).fetchone()
                    if not existing:
                        cur.execute(
                            "INSERT INTO challenge_entries (challenge_id, user_id, author_name, content, image_url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                challenge_id,
                                legacy_user_id,
                                "Legacy Participant",
                                row_get(row, "content"),
                                None,
                                _utc_now_iso(),
                            ),
                        )
                conn.commit()

        if "users" in tables and path.name == "app.db":
            for row in lcur.execute("SELECT * FROM users").fetchall():
                email = row_get(row, "email")
                if not email:
                    continue
                user_id = ensure_user(row_get(row, "username") or row_get(row, "full_name") or "Legacy User", email, row_get(row, "password_hash"))
                cur.execute(
                    "UPDATE users SET total_points = MAX(COALESCE(total_points, 0), ?), available_points = MAX(COALESCE(available_points, 0), ?) WHERE id = ?",
                    (row_get(row, "total_points", 0), row_get(row, "available_points", 0), user_id),
                )
            conn.commit()

        legacy.close()

    cur.execute("DELETE FROM app_meta WHERE key = ?", ("legacy_merge_done",))
    cur.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)", ("legacy_merge_done", "1"))
    conn.commit()
    conn.close()


with app.app_context():
    _init_ach_schema()
    _init_home_schema()
    _init_meetup_schema()
    _init_social_schema()
    _init_challenges_schema()
    _init_reports_schema()
    _init_forum_moderation_schema()
    _init_safety_schema()
    _init_wellbeing_schema()
    _init_partner_schema()
    _init_scrapbook_schema()
    _init_avatar_schema()
    _init_admin_schema()
    _init_meta_schema()
    _init_notifications_schema()
    _merge_legacy_databases()
    _seed_demo_forum_content()
    _seed_demo_challenge_content()


def _ensure_ach_user(user: User) -> None:
    conn = _get_ach_conn()
    cur = conn.cursor()
    existing = cur.execute("SELECT id FROM users WHERE id = ?", (user.id,)).fetchone()
    if not existing:
        # User was created in the main app; achievements columns will be initialized below.
        pass
    cur.execute(
        """UPDATE users
           SET full_name = COALESCE(full_name, ?)
           WHERE id = ?""",
        (user.full_name, user.id),
    )

    # Initialize achievements columns if they are NULL.
    cur.execute(
        """UPDATE users
           SET total_points = COALESCE(total_points, 0),
               available_points = COALESCE(available_points, 0),
               active_days = COALESCE(active_days, 0),
               current_tier = COALESCE(current_tier, 1),
               current_streak = COALESCE(current_streak, 0),
               is_admin = COALESCE(is_admin, 0)
           WHERE id = ?""",
        (user.id,),
    )

    count = cur.execute("SELECT COUNT(*) AS c FROM user_badges WHERE user_id = ?", (user.id,)).fetchone()["c"]
    if count == 0:
        for row in cur.execute("SELECT id FROM badges").fetchall():
            cur.execute(
                "INSERT INTO user_badges (user_id, badge_id, earned, earned_at) VALUES (?, ?, 0, NULL)",
                (user.id, row["id"]),
            )

    count = cur.execute("SELECT COUNT(*) AS c FROM user_landmarks WHERE user_id = ?", (user.id,)).fetchone()["c"]
    if count == 0:
        for row in cur.execute("SELECT id FROM landmarks").fetchall():
            cur.execute(
                "INSERT INTO user_landmarks (user_id, landmark_id, unlocked, completed) VALUES (?, ?, 0, 0)",
                (user.id, row["id"]),
            )

    count = cur.execute("SELECT COUNT(*) AS c FROM user_quests WHERE user_id = ?", (user.id,)).fetchone()["c"]
    if count == 0:
        for row in cur.execute("SELECT id, total_required FROM quests").fetchall():
            cur.execute(
                "INSERT INTO user_quests (user_id, quest_id, progress, completed) VALUES (?, ?, 0, 0)",
                (user.id, row["id"]),
            )

    count = cur.execute("SELECT COUNT(*) AS c FROM user_skills WHERE user_id = ?", (user.id,)).fetchone()["c"]
    if count == 0:
        for row in cur.execute("SELECT id FROM skills").fetchall():
            cur.execute(
                "INSERT INTO user_skills (user_id, skill_id, progress, completed) VALUES (?, ?, 0, 0)",
                (user.id, row["id"]),
            )

    conn.commit()
    conn.close()


def _update_tier(points: int) -> int:
    if points >= 4000:
        return 3
    if points >= 2000:
        return 2
    return 1


def _increment_quest_progress(user_id: int, quest_id: int, increment: int = 1) -> None:
    user = db.session.get(User, user_id)
    if not user:
        return
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    quest = cur.execute(
        """SELECT q.title, q.reward, q.total_required, uq.progress, uq.completed
           FROM quests q
           JOIN user_quests uq ON uq.quest_id = q.id
           WHERE q.id = ? AND uq.user_id = ?""",
        (quest_id, user_id),
    ).fetchone()
    if not quest:
        conn.close()
        return
    if quest["completed"]:
        conn.close()
        return
    progress = min(quest["progress"] + increment, quest["total_required"])
    completed = 1 if progress >= quest["total_required"] else 0
    if completed:
        cur.execute(
            "UPDATE users SET total_points = total_points + ?, available_points = available_points + ? WHERE id = ?",
            (quest["reward"], quest["reward"], user_id),
        )
    cur.execute(
        """UPDATE user_quests
           SET progress = ?, completed = ?, completed_at = CASE WHEN ?=1 THEN COALESCE(completed_at, ?) ELSE completed_at END
           WHERE user_id = ? AND quest_id = ?""",
        (progress, completed, completed, datetime.utcnow().isoformat(), user_id, quest_id),
    )
    conn.commit()
    conn.close()
    if completed:
        _add_notification(
            user_id,
            "quest_complete",
            f"Quest completed: {quest['title']} (+{quest['reward']} pts)",
            {"quest_id": quest_id},
        )



# --- Global notifications + local FAQ chatbot ---
FAQ_JSON_PATH = STATIC_DIR / "data" / "faq.json"
FAQ_DEFAULT_SUGGESTIONS = [
    "How matching works",
    "Report someone",
    "Join a circle",
    "Points and badges",
]
FAQ_SYNONYMS = {
    "signin": "login",
    "log in": "login",
    "register": "signup",
    "account": "profile",
    "buddy": "matching",
    "chat": "message",
    "messages": "message",
    "reporting": "report",
    "blocklist": "block",
    "classes": "circles",
    "workshop": "circles",
    "points": "repoints",
    "mrt": "station",
    "location": "meetup",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (value or "").lower())).strip()


def _load_faq_entries() -> list[dict]:
    try:
        raw = FAQ_JSON_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    except Exception:
        pass
    return []


def _expand_tokens(tokens: set[str]) -> set[str]:
    out = set(tokens)
    for token in list(tokens):
        mapped = FAQ_SYNONYMS.get(token)
        if mapped:
            out.add(mapped)
    return out


def _faq_match(message: str) -> tuple[str, list[str]]:
    text = _normalize_text(message)
    if not text:
        return (
            "I can help with account, matching, safety, circles, challenges, and points. Try one of the quick topics.",
            FAQ_DEFAULT_SUGGESTIONS,
        )

    entries = _load_faq_entries()
    if not entries:
        return (
            "I’m not sure yet. Here are common topics: matching, reporting, circles, and points.",
            FAQ_DEFAULT_SUGGESTIONS,
        )

    user_tokens = _expand_tokens(set(text.split()))
    best = None
    best_score = 0.0

    for entry in entries:
        question = str(entry.get("question", ""))
        answer = str(entry.get("answer", ""))
        keywords = entry.get("keywords") or []
        key_text = " ".join([str(k) for k in keywords])
        doc = _normalize_text(question + " " + key_text)
        if not doc or not answer:
            continue

        doc_tokens = _expand_tokens(set(doc.split()))
        overlap = len(user_tokens.intersection(doc_tokens))
        fuzzy = SequenceMatcher(None, text, doc).ratio()
        score = overlap * 2.0 + fuzzy
        if question.lower() in text:
            score += 0.8

        if score > best_score:
            best_score = score
            best = entry

    if best and best_score >= 1.2:
        answer = str(best.get("answer", "")).strip()
        suggestions = [s for s in FAQ_DEFAULT_SUGGESTIONS if _normalize_text(s) != _normalize_text(str(best.get("question", "")))]
        return answer, suggestions[:4]

    return (
        "I’m not sure yet. Here are common topics I can help with. You can also report this or contact admin/support.",
        FAQ_DEFAULT_SUGGESTIONS,
    )


def _notification_stream():
    while True:
        payload = {
            "message": "Live update: system is running.",
            "ts": datetime.utcnow().isoformat(),
        }
        yield f"data: {json.dumps(payload)}\n\n"


        time.sleep(10)


@app.get("/api/notifications/stream")
def api_notifications_stream():
    return Response(_notification_stream(), mimetype="text/event-stream")


@app.post("/faq")
def faq_reply():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "") or "")[:240]
    reply, suggestions = _faq_match(message)
    return jsonify({"reply": reply, "suggestions": suggestions})


@app.errorhandler(403)
def handle_403(err):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Forbidden"}), 403
    return ("Forbidden", 403)


@app.errorhandler(404)
def handle_404(err):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Not found"}), 404
    return ("Not found", 404)


@app.errorhandler(500)
def handle_500(err):
    logger.exception("Unhandled server error")
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "Internal server error"}), 500
    return ("Internal server error", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)

