import json
import time
from datetime import datetime
import os
import re
import sqlite3
import uuid
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, request, render_template, g, session, redirect, url_for, Response

WORKSPACE_DIR = Path(__file__).resolve().parents[3]
SEAN_DIR = WORKSPACE_DIR / "sean part"
DB_PATH = WORKSPACE_DIR / "database" / "sean_reconnect.db"
STATIC_DIR = (Path(__file__).resolve().parents[2] / "static" / "sean")
UPLOAD_FOLDER = STATIC_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

import sys
if str(SEAN_DIR) not in sys.path:
    sys.path.insert(0, str(SEAN_DIR))

from models import (
    connect_db,
    init_db,
    list_matches,
    get_match,
    create_match,
    delete_match,
    clear_matches,
    list_messages,
    get_message,
    create_message,
    update_message_text,
    delete_message,
    restore_message,
    list_profanities,
    get_profanity,
    create_profanity,
    update_profanity,
    delete_profanity,
    list_reports,
    get_report,
    create_report,
    update_report,
    delete_report,
    create_user,
    get_user_by_email,
    get_user_by_id,
    hash_password,
)

sean_bp = Blueprint("sean", __name__, url_prefix="/sean")

def init_sean():
    init_db(str(DB_PATH))

def render_sean(template_name: str, **context):
    if template_name.startswith("sean/"):
        return render_template(template_name, **context)
    return render_template(f"sean/{template_name}", **context)

def get_db():
    if "db" not in g:
        g.db = connect_db(str(DB_PATH))
    return g.db

@sean_bp.teardown_request
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(get_db(), user_id)

def login_user(user_row):
    session["user_id"] = user_row["id"]
    session["name"] = user_row["name"]
    session["role"] = user_row["role"]
    session["is_admin"] = bool(user_row["is_admin"])

def logout_user():
    session.clear()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "admin access required"}), 403
            return redirect(url_for("sean.admin_login_page"))
        return view(*args, **kwargs)
    return wrapped

@sean_bp.get("/index")
@sean_bp.get("/index.html")
def index_page():
    return render_sean("index.html")

@sean_bp.get("/login")
@sean_bp.get("/login.html")
def login_page():
    return redirect("/login")

@sean_bp.post("/login")
@sean_bp.post("/login.html")
def login_submit():
    return redirect("/login")

@sean_bp.get("/signup")
@sean_bp.get("/signup.html")
def signup_page():
    return redirect("/signup")

@sean_bp.post("/signup")
@sean_bp.post("/signup.html")
def signup_submit():
    return redirect("/signup")

@sean_bp.get("/admin/login")
def admin_login_page():
    return render_sean("admin-login.html")

@sean_bp.post("/admin/login")
@sean_bp.post("/admin/login.html")
def admin_login_submit():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    if not email or not password:
        return render_sean("admin-login.html", error="Email and password are required."), 400
    user = get_user_by_email(get_db(), email)
    if not user or user["password_hash"] != hash_password(password) or not user["is_admin"]:
        return render_sean("admin-login.html", error="Invalid admin credentials."), 401
    login_user(user)
    return redirect(url_for("sean.admin_page"))

@sean_bp.get("/admin/signup")
def admin_signup_page():
    return render_sean("admin-signup.html")

@sean_bp.post("/admin/signup")
@sean_bp.post("/admin/signup.html")
def admin_signup_submit():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    admin_code = (request.form.get("admin_code") or "").strip()
    password = (request.form.get("password") or "")
    expected_code = os.environ.get("RECONNECT_ADMIN_CODE", "ADMIN2025")
    if not name or not email or not password:
        return render_sean("admin-signup.html", error="Name, email, and password are required."), 400
    if admin_code != expected_code:
        return render_sean("admin-signup.html", error="Invalid admin code."), 403
    try:
        user = create_user(get_db(), name, email, hash_password(password), "admin", True)
    except sqlite3.IntegrityError:
        return render_sean("admin-signup.html", error="Email already registered."), 409
    login_user(user)
    return redirect(url_for("sean.admin_page"))

@sean_bp.get("/logout")
def logout_page():
    logout_user()
    return redirect("/logout")

@sean_bp.get("/api/session")
def api_session():
    if not session.get("user_id"):
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "name": session.get("name"),
        "role": session.get("role"),
        "is_admin": bool(session.get("is_admin")),
    })

@sean_bp.get("/dashboard")
@sean_bp.get("/dashboard.html")
def dashboard_page():
    return render_sean("sean/dashboard.html")

@sean_bp.get("/messages")
@sean_bp.get("/messages.html")
def messages_page():
    return render_sean("sean/messages.html")

@sean_bp.get("/admin")
@sean_bp.get("/admin.html")
@admin_required
def admin_page():
    return render_sean("sean/admin.html")

def match_to_dict(row):
    return {
        "match_id": row["match_id"],
        "name": row["name"],
        "avatar": row["avatar"],
        "location": row["location"] or "",
        "created_at": row["created_at"],
    }

def message_to_dict(row):
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

def build_profanity_patterns(rows):
    patterns = []
    for row in rows:
        word = (row["word"] or "").strip()
        if not word:
            continue
        escaped = re.escape(word)
        if " " in word:
            pattern = r"\b" + re.sub(r"\s+", r"\\s+", escaped) + r"\b"
        else:
            pattern = r"\b" + escaped + r"\b"
        patterns.append(re.compile(pattern, re.IGNORECASE))
    return patterns

def find_extreme_profanities(db, text):
    rows = list_profanities(db, "extreme")
    patterns = build_profanity_patterns(rows)
    hits = []
    for pattern in patterns:
        if pattern.search(text or ""):
            hits.append(pattern.pattern)
    return hits

def profanity_to_dict(row):
    return {
        "id": row["id"],
        "word": row["word"],
        "level": row["level"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

def report_to_dict(row):
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "report_type": row["report_type"],
        "reporter": row["reporter"],
        "status": row["status"],
        "summary": row["summary"],
        "user_a": row["user_a"],
        "user_b": row["user_b"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

@sean_bp.get("/api/matches")
def api_list_matches():
    rows = list_matches(get_db())
    return jsonify([match_to_dict(r) for r in rows])

@sean_bp.post("/api/matches")
def api_create_match():
    data = request.get_json(silent=True) or {}
    match_id = (data.get("match_id") or "").strip()
    name = (data.get("name") or "").strip()
    avatar = (data.get("avatar") or "").strip()
    location = (data.get("location") or "").strip()

    if not match_id or not name or not avatar:
        return jsonify({"error": "match_id, name, avatar are required"}), 400

    db = get_db()
    existing = get_match(db, match_id)
    if existing:
        return jsonify(match_to_dict(existing)), 200

    created = create_match(db, match_id, name, avatar, location or None)
    return jsonify(match_to_dict(created)), 201

@sean_bp.delete("/api/matches")
def api_clear_matches():
    clear_matches(get_db())
    return jsonify({"ok": True})

@sean_bp.delete("/api/matches/<match_id>")
def api_delete_match(match_id):
    db = get_db()
    existing = get_match(db, match_id)
    if not existing:
        return jsonify({"error": "match not found"}), 404

    delete_match(db, match_id)
    return jsonify({"ok": True})

@sean_bp.get("/api/messages/<chat_id>")
def api_list_messages(chat_id):
    rows = list_messages(get_db(), chat_id)
    return jsonify([message_to_dict(r) for r in rows])

@sean_bp.post("/api/messages/<chat_id>")
def api_create_message(chat_id):
    data = request.get_json(silent=True) or {}
    sender = (data.get("sender") or "").strip()
    session_role = (session.get("role") or "").strip().lower()
    if session_role in ("youth", "elderly"):
        sender = session_role
    text = (data.get("text") or "").strip()

    if sender not in ("youth", "elderly"):
        return jsonify({"error": "sender must be 'youth' or 'elderly'"}), 400
    if not text:
        return jsonify({"error": "text is required"}), 400

    db = get_db()
    msg = create_message(db, chat_id, sender, text)
    hits = find_extreme_profanities(db, text)
    if hits:
        user_name = session.get("name") or "User"
        match = get_match(db, chat_id)
        other_name = match["name"] if match else "Unknown"
        case_id = f"PROF-{msg['id']}"
        summary = f"Extreme profanity detected between {user_name} and {other_name} in chat {chat_id}."
        try:
            create_report(
                db,
                case_id=case_id,
                report_type="Profanity",
                reporter="Auto Flag",
                status="queued",
                summary=summary,
                user_a=user_name,
                user_b=other_name,
            )
        except sqlite3.IntegrityError:
            pass
    return jsonify(message_to_dict(msg)), 201

@sean_bp.post("/api/profanity-block")
@login_required
def api_profanity_block():
    data = request.get_json(silent=True) or {}
    chat_id = (data.get("chat_id") or "").strip()
    text = (data.get("text") or "").strip()
    if not chat_id or not text:
        return jsonify({"error": "chat_id and text are required"}), 400

    db = get_db()
    user_name = session.get("name") or "User"
    match = get_match(db, chat_id)
    other_name = match["name"] if match else "Unknown"
    case_id = f"PROF-BLOCK-{uuid.uuid4().hex[:8]}"
    summary = f"Blocked profanity attempt by {user_name} in chat {chat_id}."
    try:
        create_report(
            db,
            case_id=case_id,
            report_type="Profanity",
            reporter="Auto Block",
            status="queued",
            summary=summary,
            user_a=user_name,
            user_b=other_name,
        )
    except sqlite3.IntegrityError:
        pass
    return jsonify({"ok": True}), 201

@sean_bp.put("/api/messages/<int:message_id>")
def api_update_message(message_id):
    db = get_db()
    msg = get_message(db, message_id)
    if not msg:
        return jsonify({"error": "message not found"}), 404
    if msg["is_deleted"]:
        return jsonify({"error": "cannot edit deleted message"}), 400

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    updated = update_message_text(db, message_id, text)
    return jsonify(message_to_dict(updated))

@sean_bp.delete("/api/messages/<int:message_id>")
def api_delete_message(message_id):
    db = get_db()
    msg = get_message(db, message_id)
    if not msg:
        return jsonify({"error": "message not found"}), 404

    deleted = delete_message(db, message_id)
    return jsonify(message_to_dict(deleted))

@sean_bp.post("/api/messages/<int:message_id>/restore")
def api_restore_message(message_id):
    db = get_db()
    msg = get_message(db, message_id)
    if not msg:
        return jsonify({"error": "message not found"}), 404

    restored = restore_message(db, message_id)
    return jsonify(message_to_dict(restored))

@sean_bp.get("/api/profanities")
def api_list_profanities():
    level = (request.args.get("level") or "").strip().lower()
    if level and level not in ("mild", "strong", "extreme"):
        return jsonify({"error": "level must be mild, strong, or extreme"}), 400
    rows = list_profanities(get_db(), level or None)
    return jsonify([profanity_to_dict(r) for r in rows])

@sean_bp.post("/api/profanities")
@admin_required
def api_create_profanity():
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip()
    level = (data.get("level") or "").strip().lower()
    if not word or level not in ("mild", "strong", "extreme"):
        return jsonify({"error": "word and level (mild|strong|extreme) are required"}), 400
    try:
        created = create_profanity(get_db(), word, level)
    except sqlite3.IntegrityError:
        return jsonify({"error": "word already exists"}), 409
    return jsonify(profanity_to_dict(created)), 201

@sean_bp.put("/api/profanities/<int:profanity_id>")
@admin_required
def api_update_profanity(profanity_id):
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip()
    level = (data.get("level") or "").strip().lower()
    if not word or level not in ("mild", "strong", "extreme"):
        return jsonify({"error": "word and level (mild|strong|extreme) are required"}), 400
    db = get_db()
    existing = get_profanity(db, profanity_id)
    if not existing:
        return jsonify({"error": "profanity not found"}), 404
    try:
        updated = update_profanity(db, profanity_id, word, level)
    except sqlite3.IntegrityError:
        return jsonify({"error": "word already exists"}), 409
    return jsonify(profanity_to_dict(updated))

@sean_bp.delete("/api/profanities/<int:profanity_id>")
@admin_required
def api_delete_profanity(profanity_id):
    db = get_db()
    existing = get_profanity(db, profanity_id)
    if not existing:
        return jsonify({"error": "profanity not found"}), 404
    delete_profanity(db, profanity_id)
    return jsonify({"ok": True})

@sean_bp.get("/api/reports")
@admin_required
def api_list_reports():
    status = (request.args.get("status") or "").strip().lower()
    rows = list_reports(get_db(), status or None)
    return jsonify([report_to_dict(r) for r in rows])

@sean_bp.post("/api/reports")
@admin_required
def api_create_report():
    data = request.get_json(silent=True) or {}
    case_id = (data.get("case_id") or "").strip()
    report_type = (data.get("report_type") or "").strip()
    reporter = (data.get("reporter") or "").strip()
    status = (data.get("status") or "queued").strip().lower()
    summary = (data.get("summary") or "").strip() or None
    user_a = (data.get("user_a") or "").strip() or None
    user_b = (data.get("user_b") or "").strip() or None
    if not case_id or not report_type or not reporter:
        return jsonify({"error": "case_id, report_type, reporter are required"}), 400
    try:
        created = create_report(get_db(), case_id, report_type, reporter, status, summary, user_a=user_a, user_b=user_b)
    except sqlite3.IntegrityError:
        return jsonify({"error": "case_id already exists"}), 409
    return jsonify(report_to_dict(created)), 201

@sean_bp.put("/api/reports/<int:report_id>")
@admin_required
def api_update_report(report_id):
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower() or None
    summary = (data.get("summary") or "").strip() or None
    user_a = (data.get("user_a") or "").strip() or None
    user_b = (data.get("user_b") or "").strip() or None
    if status is None and summary is None and user_a is None and user_b is None:
        return jsonify({"error": "status, summary, or users are required"}), 400
    updated = update_report(get_db(), report_id, status=status, summary=summary, user_a=user_a, user_b=user_b)
    if not updated:
        return jsonify({"error": "report not found"}), 404
    return jsonify(report_to_dict(updated))

@sean_bp.delete("/api/reports/<int:report_id>")
@admin_required
def api_delete_report(report_id):
    db = get_db()
    existing = get_report(db, report_id)
    if not existing:
        return jsonify({"error": "report not found"}), 404
    delete_report(db, report_id)
    return jsonify({"ok": True})



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


@sean_bp.get("/api/notifications/stream")
def api_notifications_stream():
    return Response(_notification_stream(), mimetype="text/event-stream")


@sean_bp.post("/api/chatbot")
def api_chatbot():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    return jsonify({"reply": _faq_reply(message)})
