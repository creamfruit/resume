import json
import time
from datetime import datetime, date
import os
import sqlite3
from pathlib import Path

from flask import Blueprint, Response, send_from_directory, request, jsonify, session, redirect, render_template

import sys

ryan_bp = Blueprint("ryan", __name__, url_prefix="/ryan")

WORKSPACE_DIR = Path(__file__).resolve().parents[3]
RYAN_DIR = WORKSPACE_DIR / "projDraft5_abso_updated" / "projDraft4_fixed"
INSTANCE_DIR = RYAN_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DB_PATH = WORKSPACE_DIR / "database" / "ryan_WDP_Final_reconnect.db"
CHAT_DB_PATH = INSTANCE_DIR / "chat.db"
FORUM_DB_PATH = INSTANCE_DIR / "forum.db"
STATIC_DIR = (Path(__file__).resolve().parents[2] / "static" / "ryan")

ADMIN_ID = os.getenv("ADMIN_ID", "1234")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "5678")

# Ensure Ryan's package imports resolve (app.extensions, app.models)
if str(RYAN_DIR) not in sys.path:
    sys.path.insert(0, str(RYAN_DIR))

from app.extensions import db, migrate
from app.models import User, UserSetting, AuthEvent, CircleSignup, AchievementState

ADEN_DB_PATH = WORKSPACE_DIR / "database" / "app.db"

def _sync_aden_user(user: User) -> None:
    if not user:
        return
    try:
        conn = sqlite3.connect(str(ADEN_DB_PATH))
        conn.row_factory = sqlite3.Row
        username = user.email or user.full_name or f"user_{user.id}"
        email = user.email or f"user_{user.id}@example.com"
        conn.execute(
            """
            INSERT OR IGNORE INTO users (id, username, email, password_hash, total_points, available_points)
            VALUES (?, ?, ?, NULL, 0, 0)
            """,
            (user.id, username, email),
        )
        conn.execute(
            "UPDATE users SET username = ?, email = ? WHERE id = ?",
            (username, email, user.id),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def init_ryan(app):
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{DB_PATH}")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        db.create_all()
        _init_chat_schema()
        _init_forum_schema()

def render_ryan(template_name: str, **context):
    return render_template(f"ryan/{template_name}", **context)


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _get_chat_conn():
    conn = sqlite3.connect(CHAT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_chat_schema():
    conn = _get_chat_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            avatar TEXT NOT NULL,
            location TEXT,
            created_at TEXT NOT NULL
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
        CREATE TABLE IF NOT EXISTS profanities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            level TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        """
    )
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


def _get_forum_conn():
    conn = sqlite3.connect(FORUM_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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


def _forum_list_posts(selected_category: str):
    conn = _get_forum_conn()
    if selected_category != "all":
        rows = conn.execute(
            """
            SELECT p.*, (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comment_count
            FROM posts p
            WHERE p.category = ?
            ORDER BY p.id DESC
            """,
            (selected_category,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT p.*, (SELECT COUNT(*) FROM comments WHERE post_id = p.id) AS comment_count
            FROM posts p
            ORDER BY p.id DESC
            """
        ).fetchall()
    conn.close()
    return rows

# Create tables automatically for this prototype

PAGES = {
    "dashboard": "dashboard.html",
    "login": "login.html",
    "signup": "signup.html",
    "onboarding": "onboarding.html",
    "profile": "profile.html",
    "explore": "explore.html",
    "messages": "messages.html",
    "circle-confirmation": "circle_confirmation.html",
    "terms": "terms.html",
    "achievements": "achievements.html",
    "admin-login": "admin_login.html",
    "admin-dashboard": "admin_dashboard.html",
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



@ryan_bp.get("/")
def home():
    return render_ryan("index.html")



@ryan_bp.get("/admin-login")
def admin_login_page():
    return render_ryan("admin_login.html")


@ryan_bp.get("/admin-dashboard")
def admin_dashboard_page():
    if not _require_admin():
        return redirect("/admin-login")
    return redirect("/admin")


@ryan_bp.get("/logout")
def logout_page():
    session.pop("user_id", None)
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    return redirect("/login")


@ryan_bp.post("/dashboard")
def dashboard_forum_post():
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    category = (request.form.get("category") or "").strip()

    if not title or not content or not category:
        return redirect("/dashboard#tab-wisdom-forum")

    user = db.session.get(User, user_id)
    author_name = user.full_name if user else "User"

    conn = _get_forum_conn()
    conn.execute(
        "INSERT INTO posts (author_id, author, title, content, category, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, author_name, title, content, category, datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()

    return redirect("/dashboard#tab-wisdom-forum")


@ryan_bp.route("/forum/posts/<int:post_id>", methods=["GET", "POST"])
def forum_post_detail(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    user = db.session.get(User, user_id)
    forum_user_name = user.full_name if user else "User"

    conn = _get_forum_conn()
    if request.method == "POST":
        comment = (request.form.get("comment") or "").strip()
        if comment:
            conn.execute(
                "INSERT INTO comments (post_id, author_id, author, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (post_id, user_id, forum_user_name, comment, datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
            )
            conn.commit()

    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return ("Not found", 404)

    comments = conn.execute(
        "SELECT * FROM comments WHERE post_id = ? ORDER BY id DESC",
        (post_id,),
    ).fetchall()
    conn.close()

    return render_ryan("post.html", post=post, comments=comments, is_admin=_require_admin(), forum_user_name=forum_user_name)


@ryan_bp.post("/forum/posts/<int:post_id>/comments/<int:comment_id>/delete")
def forum_delete_comment(post_id: int, comment_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    forum_user_name = _forum_current_user_name()
    conn = _get_forum_conn()
    comment = conn.execute(
        "SELECT author_id, author FROM comments WHERE id = ? AND post_id = ?",
        (comment_id, post_id),
    ).fetchone()

    if comment and (_require_admin() or comment["author_id"] == user_id or comment["author"] == (forum_user_name or "")):
        conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        conn.commit()

    conn.close()
    return redirect(f"/forum/posts/{post_id}")


@ryan_bp.post("/forum/posts/<int:post_id>/delete")
def forum_delete_post(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    forum_user_name = _forum_current_user_name()
    conn = _get_forum_conn()
    post = conn.execute("SELECT author_id, author FROM posts WHERE id = ?", (post_id,)).fetchone()

    if post and (_require_admin() or post["author_id"] == user_id or post["author"] == (forum_user_name or "")):
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()

    conn.close()
    return redirect("/dashboard#tab-wisdom-forum")


@ryan_bp.post("/forum/posts/<int:post_id>/edit")
def forum_edit_post(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    forum_user_name = _forum_current_user_name()
    content = (request.form.get("content") or "").strip()
    if not content:
        return redirect("/dashboard#tab-wisdom-forum")

    conn = _get_forum_conn()
    post = conn.execute("SELECT author_id, author FROM posts WHERE id = ?", (post_id,)).fetchone()

    if post and (post["author_id"] == user_id or post["author"] == (forum_user_name or "")):
        conn.execute("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
        conn.commit()

    conn.close()
    return redirect("/dashboard#tab-wisdom-forum")


@ryan_bp.post("/forum/posts/<int:post_id>/like")
def forum_like_post(post_id: int):
    user_id = _require_login()
    if not user_id:
        return redirect("/login")

    conn = _get_forum_conn()
    existing = conn.execute(
        "SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?",
        (user_id, post_id),
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM post_likes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE id = ?", (post_id,))
    else:
        conn.execute("INSERT INTO post_likes (user_id, post_id) VALUES (?, ?)", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))

    conn.commit()
    conn.close()
    return redirect("/dashboard#tab-wisdom-forum")


@ryan_bp.get("/api/session")
def api_session():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"logged_in": False})

    user = db.session.get(User, user_id)
    name = user.full_name if user else "User"
    role = (user.member_type or "youth") if user else "youth"
    return jsonify({
        "logged_in": True,
        "name": name,
        "role": role,
        "is_admin": bool(session.get("is_admin")),
    })


@ryan_bp.get("/api/matches")
def api_list_matches():
    conn = _get_chat_conn()
    rows = conn.execute(
        "SELECT match_id, name, avatar, location, created_at FROM matches ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([_chat_match_to_dict(r) for r in rows])


@ryan_bp.post("/api/matches")
def api_create_match():
    data = request.get_json(silent=True) or {}
    match_id = (data.get("match_id") or "").strip()
    name = (data.get("name") or "").strip()
    avatar = (data.get("avatar") or "").strip()
    location = (data.get("location") or "").strip()

    if not match_id or not name or not avatar:
        return jsonify({"error": "match_id, name, avatar are required"}), 400

    conn = _get_chat_conn()
    existing = conn.execute(
        "SELECT match_id, name, avatar, location, created_at FROM matches WHERE match_id = ?",
        (match_id,),
    ).fetchone()
    if existing:
        conn.close()
        return jsonify(_chat_match_to_dict(existing)), 200

    conn.execute(
        "INSERT INTO matches (match_id, name, avatar, location, created_at) VALUES (?, ?, ?, ?, ?)",
        (match_id, name, avatar, location or None, _utc_now_iso()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT match_id, name, avatar, location, created_at FROM matches WHERE match_id = ?",
        (match_id,),
    ).fetchone()
    conn.close()
    return jsonify(_chat_match_to_dict(row)), 201


@ryan_bp.delete("/api/matches")
def api_clear_matches():
    conn = _get_chat_conn()
    conn.execute("DELETE FROM messages")
    conn.execute("DELETE FROM matches")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@ryan_bp.delete("/api/matches/<match_id>")
def api_delete_match(match_id):
    conn = _get_chat_conn()
    existing = conn.execute(
        "SELECT match_id FROM matches WHERE match_id = ?",
        (match_id,),
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "match not found"}), 404

    conn.execute("DELETE FROM messages WHERE chat_id = ?", (match_id,))
    conn.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@ryan_bp.get("/api/messages/<chat_id>")
def api_list_messages(chat_id):
    conn = _get_chat_conn()
    rows = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
        (chat_id,),
    ).fetchall()
    conn.close()
    return jsonify([_chat_message_to_dict(r) for r in rows])


@ryan_bp.post("/api/messages/<chat_id>")
def api_create_message(chat_id):
    data = request.get_json(silent=True) or {}
    sender = (data.get("sender") or "youth").strip().lower()
    text = (data.get("text") or "").strip()

    if sender not in ("youth", "elderly"):
        return jsonify({"error": "sender must be 'youth' or 'elderly'"}), 400
    if not text:
        return jsonify({"error": "text is required"}), 400

    conn = _get_chat_conn()
    conn.execute(
        "INSERT INTO messages (chat_id, sender, text, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, sender, text, _utc_now_iso()),
    )
    conn.commit()
    msg = conn.execute(
        "SELECT id, chat_id, sender, text, created_at, edited_at, is_deleted, deleted_at FROM messages WHERE id = last_insert_rowid()",
    ).fetchone()
    conn.close()
    return jsonify(_chat_message_to_dict(msg)), 201


@ryan_bp.put("/api/messages/<int:message_id>")
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


@ryan_bp.delete("/api/messages/<int:message_id>")
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


@ryan_bp.post("/api/messages/<int:message_id>/restore")
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


@ryan_bp.get("/api/profanities")
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


@ryan_bp.post("/api/profanity-block")
def api_profanity_block():
    data = request.get_json(silent=True) or {}
    chat_id = (data.get("chat_id") or "").strip()
    text = (data.get("text") or "").strip()
    if not chat_id or not text:
        return jsonify({"error": "chat_id and text are required"}), 400
    return jsonify({"ok": True}), 201

@ryan_bp.get("/<path:page>")
def page(page: str):
    if page.endswith(".html"):
        page = page[:-5]

    if page in PAGES:
        if page == "dashboard":
            selected_category = (request.args.get("filter") or "all").strip()
            allowed = {"all", "Money", "Career", "Relationships", "Life Skills", "Health"}
            if selected_category not in allowed:
                selected_category = "all"
            posts = _forum_list_posts(selected_category)
            return render_ryan(PAGES[page], posts=posts, selected_category=selected_category, is_admin=_require_admin(), forum_user_name=_forum_current_user_name())
        if page == "profile":
            if not _require_login():
                return redirect("/login")
            # Get user data
            user_id = session["user_id"]
            u = db.session.get(User, user_id)
            settings = UserSetting.query.filter_by(user_id=user_id).all()
            user_settings = {s.key: s.value for s in settings}
            onboarding = json.loads(user_settings.get("onboarding", "{}"))
            return render_ryan(PAGES[page], user=u, onboarding=onboarding)
        if page == "onboarding":
            user_id = _require_login()
            if user_id:
                settings = UserSetting.query.filter_by(user_id=user_id).all()
                user_settings = {s.key: s.value for s in settings}
                onboarding = json.loads(user_settings.get("onboarding", "{}"))
                return render_ryan(PAGES[page], onboarding=onboarding)
            else:
                return render_ryan(PAGES[page], onboarding={})
        if page == "achievements":
            user_id = _require_login()
            if not user_id:
                return redirect("/login")
            u = db.session.get(User, user_id)
            return render_ryan(PAGES[page], user=u)
        return render_ryan(PAGES[page])

    return ("Not found", 404)


def _require_login():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return user_id



def _require_admin():
    return bool(session.get("is_admin"))

#Create Account
@ryan_bp.post("/api/signup")
def api_signup():
    data = request.get_json(silent=True) or request.form

    full_name = (data.get("fullname") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not full_name or not email or not password:
        return jsonify({"ok": False, "error": "Missing required fields"}), 400

    if len(password) < 8:
        return jsonify({"ok": False, "error": "Password must be at least 8 characters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"ok": False, "error": "Email already exists"}), 409

    u = User(full_name=full_name, email=email)
    u.set_password(password)

    db.session.add(u)
    db.session.commit()
    _ensure_ach_user(u)
    _sync_aden_user(u)

    # Audit log
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
    return jsonify({"ok": True})


@ryan_bp.post("/signup")
def signup():
    full_name = (request.form.get("fullname") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not full_name or not email or not password:
        return render_ryan("signup.html", error="Missing required fields")

    if len(password) < 8:
        return render_ryan("signup.html", error="Password must be at least 8 characters")

    if not email.endswith("@gmail.com"):
        return render_ryan("signup.html", error="Email must be a Gmail address")

    if User.query.filter_by(email=email).first():
        return render_ryan("signup.html", error="Email already exists")

    u = User(full_name=full_name, email=email)
    u.set_password(password)

    db.session.add(u)
    db.session.commit()
    _ensure_ach_user(u)
    _sync_aden_user(u)

    # Audit log
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
    return redirect("/onboarding")

#Log In
@ryan_bp.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or request.form

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Allow admin credentials via the same login endpoint.
    if email == ADMIN_ID and password == ADMIN_PASSWORD:
        session.pop("user_id", None)
        session["is_admin"] = True
        session["admin_id"] = email
        return jsonify({"ok": True, "is_admin": True})

    if not email or not password:
        return jsonify({"ok": False, "error": "Missing email or password"}), 400

    if len(password) < 8:
        return jsonify({"ok": False, "error": "Password must be at least 8 characters"}), 400

    u = User.query.filter_by(email=email).first()
    if not u or not u.check_password(password):
        return jsonify({"ok": False, "error": "Invalid email or password"}), 401

    # Audit log
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
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    _sync_aden_user(u)
    return jsonify({"ok": True, "is_admin": False})


@ryan_bp.post("/api/logout")
def api_logout():
    session.pop("user_id", None)
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    return jsonify({"ok": True})


@ryan_bp.get("/api/me")
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
@ryan_bp.get("/api/profile")
def api_profile():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "User not found"}), 404

    # Get user settings
    settings = UserSetting.query.filter_by(user_id=user_id).all()
    user_settings = {s.key: s.value for s in settings}

    return jsonify(
        {
            "ok": True,
            "profile": {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "member_type": u.member_type,
                "bio": user_settings.get("bio", ""),
                "onboarding": json.loads(user_settings.get("onboarding", "{}")),
            },
        }
    )


@ryan_bp.post("/api/profile")
def api_update_profile():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}

    bio = data.get("bio", "").strip()

    # Update bio in user settings
    setting = UserSetting.query.filter_by(user_id=user_id, key="bio").first()
    if setting is None:
        setting = UserSetting(user_id=user_id, key="bio", value=bio)
        db.session.add(setting)
    else:
        setting.value = bio

    db.session.commit()
    return jsonify({"ok": True})


#Join Circle
@ryan_bp.post("/api/circle_signup")
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
    return jsonify({"ok": True, "id": signup.id})


@ryan_bp.post("/api/onboarding")
def api_onboarding():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}

    member_type = (data.get("memberType") or "").strip()
    interests = data.get("interests") or []
    days = data.get("days") or []
    time = data.get("time") or ""

    # Update a field on the user table for quick access
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "User not found"}), 404

    if member_type:
        u.member_type = member_type

    payload = {
        "memberType": member_type,
        "interests": interests,
        "days": days,
        "time": time,
    }

    setting = UserSetting.query.filter_by(user_id=user_id, key="onboarding").first()
    if setting is None:
        setting = UserSetting(user_id=user_id, key="onboarding", value=json.dumps(payload))
        db.session.add(setting)
    else:
        setting.value = json.dumps(payload)

    db.session.commit()
    return jsonify({"ok": True})

@ryan_bp.post("/api/admin/login")
def api_admin_login():
    data = request.get_json(silent=True) or request.form
    admin_id = (data.get("adminId") or "").strip()
    password = data.get("password") or ""

    if admin_id == ADMIN_ID and password == ADMIN_PASSWORD:
        session["is_admin"] = True
        session["admin_id"] = admin_id
        return jsonify({"ok": True})

    return jsonify({"ok": False, "error": "Invalid admin credentials"}), 401


@ryan_bp.post("/api/admin/logout")
def api_admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    return jsonify({"ok": True})


@ryan_bp.get("/api/admin/overview")
def api_admin_overview():
    if not _require_admin():
        return jsonify({"ok": False, "error": "Not authorised"}), 401

    auth_events = (
        AuthEvent.query.order_by(AuthEvent.created_at.desc()).limit(200).all()
    )
    circle_signups = (
        CircleSignup.query.order_by(CircleSignup.created_at.desc()).limit(200).all()
    )

    def _u_name(uid):
        u = db.session.get(User, uid) if uid else None
        return u.full_name if u else ""

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
            "stats": {
                "total_users": User.query.count(),
                "total_auth_events": AuthEvent.query.count(),
                "total_circle_signups": CircleSignup.query.count(),
            },
        }
    )


@ryan_bp.get("/api/achievements")
def api_achievements():
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()

    user_row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    redeemed_cost = cur.execute(
        "SELECT COALESCE(SUM(r.cost), 0) AS redeemed_points FROM user_rewards ur JOIN rewards r ON r.id = ur.reward_id WHERE ur.user_id = ?",
        (user_id,),
    ).fetchone()["redeemed_points"]
    total_points_calc = max(
        user_row["total_points"],
        (user_row["available_points"] or 0) + (redeemed_cost or 0),
    )
    points = total_points_calc
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
            current = total_points_calc
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
              "total_points": total_points_calc,
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


@ryan_bp.post("/api/achievements/quests/<int:quest_id>/progress")
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
    return api_achievements()


@ryan_bp.post("/api/achievements/rewards/<int:reward_id>/redeem")
def api_achievements_redeem_reward(reward_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    reward = cur.execute("SELECT cost FROM rewards WHERE id = ? AND is_active = 1", (reward_id,)).fetchone()
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
    return api_achievements()


@ryan_bp.post("/api/achievements/skills/<int:skill_id>/progress")
def api_achievements_skill_progress(skill_id: int):
    user_id = _require_login()
    if not user_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401
    user = db.session.get(User, user_id)
    _ensure_ach_user(user)
    conn = _get_ach_conn()
    cur = conn.cursor()
    skill = cur.execute(
        "SELECT s.required_count, s.reward_points, us.progress, us.completed FROM skills s JOIN user_skills us ON us.skill_id = s.id WHERE s.id = ? AND us.user_id = ?",
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
    return api_achievements()


@ryan_bp.post("/api/achievements/landmarks/<int:landmark_id>/unlock")
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


@ryan_bp.post("/api/achievements/landmarks/<int:landmark_id>/complete")
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
            is_active INTEGER NOT NULL DEFAULT 1
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
            "INSERT INTO rewards (id, name, icon, cost, description, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, "$2 GrabFood Voucher", "gift", 500, None, 1),
                (2, "$3 Starbucks Voucher", "cup", 750, None, 1),
                (3, "$5 Popular Bookstore", "book", 1250, None, 1),
                (4, "$5 Kopitiam Voucher", "bread", 1250, None, 1),
                (5, "$10 NTUC Voucher", "cart", 2500, None, 1),
                (6, "$10 Watsons Voucher", "bag", 2500, None, 1),
                (7, "$15 Movie Voucher", "ticket", 3750, None, 1),
                (8, "$15 Uniqlo Voucher", "shirt", 3750, None, 1),
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



# --- Global notifications + FAQ chatbot ---
FAQ_RESPONSES = {
    "help": "You can ask about onboarding, rewards, or points.",
    "rewards": "Rewards are earned by completing quests and activities.",
    "points": "Points are awarded for activity completion and participation.",
    "quests": "Quests guide learning and community participation.",
}


def _faq_reply(message: str) -> str:
    text = (message or "").strip().lower()
    if not text:
        return "Ask me about rewards, points, quests, or onboarding."
    for key, reply in FAQ_RESPONSES.items():
        if key in text:
            return reply
    return "Thanks! I can answer FAQs about rewards, points, quests, and onboarding."


def _notification_stream():
    while True:
        payload = {
            "message": "Live update: system is running.",
            "ts": datetime.utcnow().isoformat(),
        }
        yield f"data: {json.dumps(payload)}\n\n"


        time.sleep(10)


@ryan_bp.get("/api/notifications/stream")
def api_notifications_stream():
    return Response(_notification_stream(), mimetype="text/event-stream")


@ryan_bp.post("/api/chatbot")
def api_chatbot():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    return jsonify({"reply": _faq_reply(message)})
