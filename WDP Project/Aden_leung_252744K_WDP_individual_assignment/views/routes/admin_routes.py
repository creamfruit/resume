# Import datetime for audit timestamps and comparisons.
from datetime import datetime, timedelta
import os
import sqlite3
from collections import defaultdict
import zipfile
import io
import csv

# Import Flask routing utilities for admin pages.
from flask import Blueprint, redirect, render_template, request, url_for, Response, session

# Import DB connector and admin guard.
from views.db import get_db
from views.routes.admin_utils import require_admin

# This Blueprint groups admin dashboard and management routes.
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXTERNAL_DB_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "database"))
EXTERNAL_APPS = {
    "reconnect": {
        "label": "Reconnect-SG Forum",
        "db_name": "reconnect-sg_forum.db",
    },
    "sean": {
        "label": "Sean App",
        "db_name": "sean_reconnect.db",
    },
    "ryan": {
        "label": "Ryan App",
        "db_name": "ryan_WDP_Final_reconnect.db",
    },
    "dashboard": {
        "label": "Reconnect Dashboard",
        "db_name": "dashboard.db",
    },
    "aden": {
        "label": "Aden App",
        "db_name": "app.db",
    },
}

APP_ADMIN_LINKS = {
    "aden": "/admin",
    "ryan": "/ryan/admin-dashboard",
    "sean": "/sean/admin",
    "reconnect": "/reconnect/dashboard",
    "dashboard": "/",
}


def _external_db_path(app_key: str) -> str:
    config = EXTERNAL_APPS.get(app_key)
    if not config:
        return ""
    return os.path.join(EXTERNAL_DB_DIR, config["db_name"])


def _get_external_conn(app_key: str) -> sqlite3.Connection:
    db_path = _external_db_path(app_key)
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found for {app_key}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _get_external_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def _get_table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.cursor()
    cols = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return [col["name"] for col in cols]


def _get_table_rows(conn: sqlite3.Connection, table: str, limit: int = 200) -> list[dict]:
    cur = conn.cursor()
    rows = cur.execute(
        f"SELECT rowid AS _rowid, * FROM {table} ORDER BY rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def _count_rows(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.cursor()
    try:
        return cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    except sqlite3.OperationalError:
        return 0


def _detect_time_columns(columns: list[str]) -> list[str]:
    candidates = []
    for col in columns:
        lc = col.lower()
        if lc.endswith("_at") or lc in {"created", "updated", "timestamp", "ts"}:
            candidates.append(col)
    return candidates


def _load_time_series(conn: sqlite3.Connection, table: str, time_col: str, days: int = 7) -> dict:
    cur = conn.cursor()
    since = (datetime.utcnow() - timedelta(days=days)).date()
    rows = cur.execute(f"SELECT {time_col} FROM {table}").fetchall()
    counts = defaultdict(int)
    for row in rows:
        raw = row[time_col]
        if not raw:
            continue
        try:
            # Support ISO-like strings or SQLite timestamps.
            ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if ts.date() < since:
            continue
        counts[str(ts.date())] += 1
    # Fill missing days
    timeline = []
    for i in range(days, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        timeline.append({"date": str(day), "count": counts.get(str(day), 0)})
    return {
        "table": table,
        "column": time_col,
        "series": timeline,
    }


def _load_external_analytics() -> dict:
    app_totals = []
    table_totals = []
    time_series = []
    for key, meta in EXTERNAL_APPS.items():
        db_path = _external_db_path(key)
        if not db_path or not os.path.exists(db_path):
            continue
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        tables = _get_external_tables(conn)
        total_rows = 0
        for table in tables:
            count = _count_rows(conn, table)
            total_rows += count
            table_totals.append({"app": meta["label"], "table": table, "count": count})
            cols = _get_table_columns(conn, table)
            for tcol in _detect_time_columns(cols)[:1]:
                time_series.append(_load_time_series(conn, table, tcol))
        app_totals.append({"app": meta["label"], "count": total_rows})
        conn.close()
    # Sort table totals
    table_totals.sort(key=lambda x: x["count"], reverse=True)
    return {
        "app_totals": app_totals,
        "table_totals": table_totals[:12],
        "time_series": time_series[:6],
    }


def _load_app_summaries() -> list[dict]:
    summaries: list[dict] = []
    for key, meta in EXTERNAL_APPS.items():
        db_path = _external_db_path(key)
        if not db_path or not os.path.exists(db_path):
            summaries.append(
                {
                    "app_key": key,
                    "label": meta["label"],
                    "link": APP_ADMIN_LINKS.get(key),
                    "error": "Database not found",
                    "tables": 0,
                    "total_rows": 0,
                    "counts": {},
                }
            )
            continue

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        tables = _get_external_tables(conn)
        tables_set = set(tables)

        def count_if(table: str) -> int:
            if table not in tables_set:
                return 0
            return _count_rows(conn, table)

        total_rows = 0
        for table in tables:
            total_rows += _count_rows(conn, table)

        counts = {
            "users": count_if("users"),
            "posts": count_if("posts"),
            "comments": count_if("comments"),
            "challenges": count_if("challenges"),
            "submissions": count_if("submissions"),
            "matches": count_if("matches"),
            "messages": count_if("messages"),
            "reports": count_if("reports"),
            "profanities": count_if("profanities"),
            "quests": count_if("quests"),
            "badges": count_if("badges"),
            "rewards": count_if("rewards"),
            "auth_events": count_if("auth_events"),
        }

        summaries.append(
            {
                "app_key": key,
                "label": meta["label"],
                "link": APP_ADMIN_LINKS.get(key),
                "error": None,
                "tables": len(tables),
                "total_rows": total_rows,
                "counts": counts,
            }
        )
        conn.close()
    return summaries


def _load_external_table(app_key: str, table: str, columns: list[str] | None = None, limit: int = 200) -> dict | None:
    try:
        conn = _get_external_conn(app_key)
    except FileNotFoundError:
        return None
    tables = set(_get_external_tables(conn))
    if table not in tables:
        conn.close()
        return None
    all_cols = _get_table_columns(conn, table)
    if columns:
        selected = [c for c in columns if c in all_cols]
    else:
        selected = all_cols
    if not selected:
        conn.close()
        return None
    rows = conn.execute(
        f"SELECT {', '.join(selected)} FROM {table} ORDER BY rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return {"columns": selected, "rows": [dict(r) for r in rows]}


def _load_external_admin_views() -> dict:
    views = {
        "users": [],
        "quests": [],
        "landmarks": [],
        "badges": [],
        "rewards": [],
        "activity": [],
        "roles": [],
        "audit": [],
        "reports": [],
        "forum_posts": [],
        "forum_comments": [],
        "forum_challenges": [],
        "forum_submissions": [],
        "safety_matches": [],
        "safety_messages": [],
        "safety_profanities": [],
        "safety_reports": [],
    }
    for key, meta in EXTERNAL_APPS.items():
        label = meta["label"]
        link = APP_ADMIN_LINKS.get(key)

        users = _load_external_table(
            key,
            "users",
            ["id", "username", "name", "email", "role", "is_admin", "created_at"],
        )
        if users:
            views["users"].append({"app_key": key, "label": label, "link": link, **users})
            views["roles"].append({"app_key": key, "label": label, "link": link, **users})

        quests = _load_external_table(
            key, "quests", ["id", "title", "description", "reward", "total_required"]
        )
        if quests:
            views["quests"].append({"app_key": key, "label": label, "link": link, **quests})

        landmarks = _load_external_table(
            key, "landmarks", ["id", "name", "description", "points", "story"]
        )
        if landmarks:
            views["landmarks"].append({"app_key": key, "label": label, "link": link, **landmarks})

        badges = _load_external_table(
            key, "badges", ["id", "name", "category", "threshold", "requirement_type"]
        )
        if badges:
            views["badges"].append({"app_key": key, "label": label, "link": link, **badges})

        rewards = _load_external_table(
            key, "rewards", ["id", "name", "cost", "status"]
        )
        if rewards:
            views["rewards"].append({"app_key": key, "label": label, "link": link, **rewards})

        auth_events = _load_external_table(
            key, "auth_events", ["id", "created_at", "event_type", "email", "ip_address"]
        )
        if auth_events:
            views["activity"].append({"app_key": key, "label": label, "link": link, **auth_events})

        posts = _load_external_table(
            key, "posts", ["id", "author", "title", "category", "created_at", "likes"]
        )
        if posts:
            views["forum_posts"].append({"app_key": key, "label": label, "link": link, **posts})

        comments = _load_external_table(
            key, "comments", ["id", "post_id", "author", "content", "created_at"]
        )
        if comments:
            views["forum_comments"].append({"app_key": key, "label": label, "link": link, **comments})

        challenges = _load_external_table(
            key, "challenges", ["id", "title", "description", "created_at"]
        )
        if challenges:
            views["forum_challenges"].append({"app_key": key, "label": label, "link": link, **challenges})

        submissions = _load_external_table(
            key, "submissions", ["id", "challenge_id", "author", "content", "created_at"]
        )
        if submissions:
            views["forum_submissions"].append({"app_key": key, "label": label, "link": link, **submissions})

        matches = _load_external_table(
            key, "matches", ["id", "match_id", "name", "created_at"]
        )
        if matches:
            views["safety_matches"].append({"app_key": key, "label": label, "link": link, **matches})

        messages = _load_external_table(
            key, "messages", ["id", "chat_id", "sender", "text", "created_at", "is_deleted"]
        )
        if messages:
            views["safety_messages"].append({"app_key": key, "label": label, "link": link, **messages})

        profanities = _load_external_table(
            key, "profanities", ["id", "word", "level", "created_at"]
        )
        if profanities:
            views["safety_profanities"].append({"app_key": key, "label": label, "link": link, **profanities})

        admin_logs = _load_external_table(
            key, "admin_audit_logs", ["id", "created_at", "actor_id", "action", "table_name", "details"]
        )
        if admin_logs:
            views["audit"].append({"app_key": key, "label": label, "link": link, **admin_logs})

        reports = _load_external_table(
            key, "reports", ["id", "created_at", "status", "reason", "reported_by"]
        )
        if reports:
            views["reports"].append({"app_key": key, "label": label, "link": link, **reports})
            views["safety_reports"].append({"app_key": key, "label": label, "link": link, **reports})

    return views


def _ensure_audit_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            actor_id INTEGER,
            action TEXT NOT NULL,
            app_key TEXT,
            table_name TEXT,
            details TEXT
        )
        """
    )
    conn.commit()


def _log_admin_action(actor_id: int | None, action: str, app_key: str | None, table_name: str | None, details: str) -> None:
    conn = get_db()
    _ensure_audit_log_table(conn)
    conn.execute(
        """
        INSERT INTO admin_audit_logs (created_at, actor_id, action, app_key, table_name, details)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (datetime.utcnow().isoformat(), actor_id, action, app_key, table_name, details),
    )
    conn.commit()


def _get_audit_logs(limit: int = 200) -> list[dict]:
    conn = get_db()
    _ensure_audit_log_table(conn)
    rows = conn.execute(
        """
        SELECT id, created_at, actor_id, action, app_key, table_name, details
        FROM admin_audit_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def _get_external_users() -> list[dict]:
    results = []
    for key, meta in EXTERNAL_APPS.items():
        db_path = _external_db_path(key)
        if not db_path or not os.path.exists(db_path):
            continue
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        tables = _get_external_tables(conn)
        if "users" not in tables:
            conn.close()
            continue
        cols = _get_table_columns(conn, "users")
        cols_set = set(cols)
        select_cols = ["rowid AS _rowid"]
        for col in ["id", "username", "name", "email", "role", "is_admin"]:
            if col in cols_set:
                select_cols.append(col)
        rows = conn.execute(
            f"SELECT {', '.join(select_cols)} FROM users ORDER BY rowid DESC LIMIT 500"
        ).fetchall()
        for row in rows:
            row = dict(row)
            results.append(
                {
                    "app_key": key,
                    "app_label": meta["label"],
                    "rowid": row.get("_rowid"),
                    "id": row.get("id"),
                    "username": row.get("username") or row.get("name"),
                    "email": row.get("email"),
                    "role": row.get("role"),
                    "is_admin": row.get("is_admin"),
                }
            )
        conn.close()
    return results


def _list_scheduled_reports() -> list[dict]:
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    if not os.path.exists(reports_dir):
        return []
    items = []
    for name in sorted(os.listdir(reports_dir), reverse=True):
        path = os.path.join(reports_dir, name)
        if not os.path.isfile(path):
            continue
        items.append(
            {
                "name": name,
                "size": os.path.getsize(path),
                "url": f"/admin/reports/{name}",
            }
        )
    return items[:50]


def _load_external_apps() -> list[dict]:
    apps = []
    for key, meta in EXTERNAL_APPS.items():
        app_payload = {"key": key, "label": meta["label"], "error": None, "tables": []}
        try:
            conn = _get_external_conn(key)
        except FileNotFoundError as exc:
            app_payload["error"] = str(exc)
            apps.append(app_payload)
            continue
        try:
            tables = _get_external_tables(conn)
            for table in tables:
                columns = _get_table_columns(conn, table)
                editable_columns = [col for col in columns if col != "id"]
                app_payload["tables"].append(
                    {
                        "name": table,
                        "columns": columns,
                        "editable_columns": editable_columns,
                        "rows": _get_table_rows(conn, table),
                    }
                )
        finally:
            conn.close()
        apps.append(app_payload)
    return apps


# Helper to preserve active tab across admin actions.
def _redirect_tab(tab_id):
    return redirect(url_for("admin.admin_dashboard") + f"#{tab_id}")


# Compute tier thresholds for admin adjustments.
def _tier_for_points(points):
    if points >= 20000:
        return 5
    if points >= 10000:
        return 4
    if points >= 5000:
        return 3
    if points >= 2000:
        return 2
    return 1


# Query aggregate stats for the admin overview cards.
def _get_stats(conn):
    cur = conn.cursor()
    # Query total users.
    cur.execute("SELECT COUNT(*) AS count FROM users")
    total_users = cur.fetchone()["count"]
    # Query total quests.
    cur.execute("SELECT COUNT(*) AS count FROM quests")
    total_quests = cur.fetchone()["count"]
    # Query total landmarks.
    cur.execute("SELECT COUNT(*) AS count FROM landmarks")
    total_landmarks = cur.fetchone()["count"]
    # Query total redeemed rewards.
    cur.execute("SELECT COUNT(*) AS count FROM user_rewards")
    rewards_redeemed = cur.fetchone()["count"]
    # Query total points across all users.
    cur.execute("SELECT COALESCE(SUM(total_points), 0) AS total_points FROM users")
    total_points = cur.fetchone()["total_points"]
    # Query active users with any completed activity.
    cur.execute(
        """
        SELECT COUNT(DISTINCT u.id) AS count
        FROM users u
        LEFT JOIN user_quests uq
            ON uq.user_id = u.id AND uq.completed = 1
        LEFT JOIN user_landmarks ul
            ON ul.user_id = u.id AND ul.completed = 1
        LEFT JOIN user_rewards ur
            ON ur.user_id = u.id
        WHERE uq.id IS NOT NULL OR ul.id IS NOT NULL OR ur.id IS NOT NULL
        """
    )
    active_users = cur.fetchone()["count"]
    return {
        "total_users": total_users,
        "total_quests": total_quests,
        "total_landmarks": total_landmarks,
        "rewards_redeemed": rewards_redeemed,
        "total_points": total_points,
        "active_users": active_users,
    }


# Query a user list with aggregated completion stats.
def _get_users(conn):
    cur = conn.cursor()
    # Query user profiles with quest and landmark completion counts.
    cur.execute(
        """
        SELECT u.id, u.username, u.email, u.total_points, u.current_tier, u.active_days,
               COALESCE(lm.completed_count, 0) AS landmarks_completed,
               COALESCE(q.completed_count, 0) AS quests_completed
        FROM users u
        LEFT JOIN (
            SELECT user_id, COUNT(*) AS completed_count
            FROM user_landmarks
            WHERE completed = 1
            GROUP BY user_id
        ) lm ON lm.user_id = u.id
        LEFT JOIN (
            SELECT user_id, COUNT(*) AS completed_count
            FROM user_quests
            WHERE completed = 1
            GROUP BY user_id
        ) q ON q.user_id = u.id
        ORDER BY u.id
        """
    )
    return [dict(row) for row in cur.fetchall()]


# Query quest list with completion counts.
def _get_quests(conn):
    cur = conn.cursor()
    # Query quests joined with completion totals.
    cur.execute(
        """
        SELECT q.*, COALESCE(uq.times_completed, 0) AS times_completed
        FROM quests q
        LEFT JOIN (
            SELECT quest_id, COUNT(*) AS times_completed
            FROM user_quests
            WHERE completed = 1
            GROUP BY quest_id
        ) uq ON uq.quest_id = q.id
        ORDER BY q.id
        """
    )
    return [dict(row) for row in cur.fetchall()]


# Query landmark list with completion counts.
def _get_landmarks(conn):
    cur = conn.cursor()
    # Query landmarks joined with completion totals.
    cur.execute(
        """
        SELECT l.*, COALESCE(ul.times_completed, 0) AS times_completed
        FROM landmarks l
        LEFT JOIN (
            SELECT landmark_id, COUNT(*) AS times_completed
            FROM user_landmarks
            WHERE completed = 1
            GROUP BY landmark_id
        ) ul ON ul.landmark_id = l.id
        ORDER BY l.id
        """
    )
    return [dict(row) for row in cur.fetchall()]


# Query badge list with earned counts.
def _get_badges(conn):
    cur = conn.cursor()
    # Query badges joined with earned totals.
    cur.execute(
        """
        SELECT b.*, COALESCE(ub.times_earned, 0) AS times_earned
        FROM badges b
        LEFT JOIN (
            SELECT badge_id, COUNT(*) AS times_earned
            FROM user_badges
            WHERE earned = 1
            GROUP BY badge_id
        ) ub ON ub.badge_id = b.id
        ORDER BY b.category, b.id
        """
    )
    return [dict(row) for row in cur.fetchall()]


# Query reward list with redemption counts.
def _get_rewards(conn):
    cur = conn.cursor()
    # Query rewards joined with redemption totals.
    cur.execute(
        """
        SELECT r.*, COALESCE(ur.times_redeemed, 0) AS times_redeemed
        FROM rewards r
        LEFT JOIN (
            SELECT reward_id, COUNT(*) AS times_redeemed
            FROM user_rewards
            GROUP BY reward_id
        ) ur ON ur.reward_id = r.id
        ORDER BY r.cost
        """
    )
    return [dict(row) for row in cur.fetchall()]


# Query recent reward redemptions for the activity feed.
def _get_redemptions(conn):
    cur = conn.cursor()
    # Query recent reward redemptions with user context.
    cur.execute(
        """
        SELECT ur.redeemed_at, u.username, r.name AS reward_name, r.cost
        FROM user_rewards ur
        JOIN users u ON u.id = ur.user_id
        JOIN rewards r ON r.id = ur.reward_id
        ORDER BY ur.redeemed_at DESC
        LIMIT 50
        """
    )
    return [dict(row) for row in cur.fetchall()]


# Query recent activity across quests, landmarks, and rewards.
def _get_activity(conn):
    cur = conn.cursor()
    # Union multiple activity sources into a single timeline.
    cur.execute(
        """
        SELECT * FROM (
            SELECT uq.completed_at AS ts, u.username, 'quest' AS activity_type, q.title AS item_name
            FROM user_quests uq
            JOIN users u ON u.id = uq.user_id
            JOIN quests q ON q.id = uq.quest_id
            WHERE uq.completed = 1 AND uq.completed_at IS NOT NULL
            UNION ALL
            SELECT ul.completed_at AS ts, u.username, 'landmark' AS activity_type, l.name AS item_name
            FROM user_landmarks ul
            JOIN users u ON u.id = ul.user_id
            JOIN landmarks l ON l.id = ul.landmark_id
            WHERE ul.completed = 1 AND ul.completed_at IS NOT NULL
            UNION ALL
            SELECT ur.redeemed_at AS ts, u.username, 'reward' AS activity_type, r.name AS item_name
            FROM user_rewards ur
            JOIN users u ON u.id = ur.user_id
            JOIN rewards r ON r.id = ur.reward_id
            WHERE ur.redeemed_at IS NOT NULL
        )
        ORDER BY ts DESC
        LIMIT 50
        """
    )
    return [dict(row) for row in cur.fetchall()]


@admin_bp.get("/")
def admin_dashboard():
    _, err = require_admin()
    if err:
        return redirect(url_for("auth.login"))
    conn = get_db()
    # Assemble dashboard datasets for the admin view.
    stats = _get_stats(conn)
    return render_template(
        "admin.html",
        stats=stats,
        users=_get_users(conn),
        quests=_get_quests(conn),
        landmarks=_get_landmarks(conn),
        badges=_get_badges(conn),
        rewards=_get_rewards(conn),
        redemptions=_get_redemptions(conn),
        activity=_get_activity(conn),
        external_apps=_load_external_apps(),
        external_analytics=_load_external_analytics(),
        app_summaries=_load_app_summaries(),
        external_views=_load_external_admin_views(),
        external_users=_get_external_users(),
        audit_logs=_get_audit_logs(),
        scheduled_reports=_list_scheduled_reports(),
    )


@admin_bp.get("/users/<int:user_id>")
def admin_user_detail(user_id):
    _, err = require_admin()
    if err:
        return redirect(url_for("auth.login"))
    conn = get_db()
    cur = conn.cursor()
    # Query the selected user profile.
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        return redirect(url_for("admin.admin_dashboard"))

    # Query quest progress for the user.
    cur.execute(
        """
        SELECT q.title, q.total_required, uq.progress, uq.completed, uq.completed_at
        FROM quests q
        LEFT JOIN user_quests uq
            ON uq.quest_id = q.id AND uq.user_id = ?
        ORDER BY q.id
        """,
        (user_id,),
    )
    quests = [dict(row) for row in cur.fetchall()]

    # Query badge progress for the user.
    cur.execute(
        """
        SELECT b.name, b.category, b.threshold, b.requirement_type,
               COALESCE(ub.earned, 0) AS earned, ub.earned_at
        FROM badges b
        LEFT JOIN user_badges ub
            ON ub.badge_id = b.id AND ub.user_id = ?
        ORDER BY b.id
        """,
        (user_id,),
    )
    badges = [dict(row) for row in cur.fetchall()]

    # Query landmark progress for the user.
    cur.execute(
        """
        SELECT l.name, COALESCE(ul.unlocked, 0) AS unlocked,
               COALESCE(ul.completed, 0) AS completed,
               ul.unlocked_at, ul.completed_at
        FROM landmarks l
        LEFT JOIN user_landmarks ul
            ON ul.landmark_id = l.id AND ul.user_id = ?
        ORDER BY l.id
        """,
        (user_id,),
    )
    landmarks = [dict(row) for row in cur.fetchall()]

    # Query reward redemption history for the user.
    cur.execute(
        """
        SELECT r.name, r.cost, ur.redeemed_at
        FROM user_rewards ur
        JOIN rewards r ON r.id = ur.reward_id
        WHERE ur.user_id = ?
        ORDER BY ur.redeemed_at DESC
        """,
        (user_id,),
    )
    rewards = [dict(row) for row in cur.fetchall()]

    # Render the admin user detail page.
    return render_template(
        "admin_user.html",
        user=dict(user),
        quests=quests,
        badges=badges,
        landmarks=landmarks,
        rewards=rewards,
    )


@admin_bp.post("/users/<int:user_id>/delete")
def admin_delete_user(user_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    # Delete all user-owned rows to maintain referential integrity.
    conn.execute("DELETE FROM user_quests WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_badges WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_rewards WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_landmarks WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_checkins WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM checkin_rewards WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_skill_rewards WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return _redirect_tab("tab-users")


@admin_bp.post("/users/<int:user_id>/reset")
def admin_reset_user(user_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    # Reset quest progress and completion timestamps.
    conn.execute(
        """
        UPDATE user_quests
        SET progress = 0, completed = 0, completed_at = NULL
        WHERE user_id = ?
        """,
        (user_id,),
    )
    # Reset landmark unlock and completion state.
    conn.execute(
        """
        UPDATE user_landmarks
        SET unlocked = 0, completed = 0, unlocked_at = NULL, completed_at = NULL
        WHERE user_id = ?
        """,
        (user_id,),
    )
    # Reset badge earned state.
    conn.execute(
        """
        UPDATE user_badges
        SET earned = 0, earned_at = NULL
        WHERE user_id = ?
        """,
        (user_id,),
    )
    # Clear reward redemptions and point balances.
    conn.execute("DELETE FROM user_rewards WHERE user_id = ?", (user_id,))
    conn.execute(
        """
        UPDATE users
        SET total_points = 0,
            available_points = 0,
            current_tier = 1,
            active_days = 1
        WHERE id = ?
        """,
        (user_id,),
    )
    conn.commit()
    return redirect(url_for("admin.admin_user_detail", user_id=user_id))


@admin_bp.post("/users/<int:user_id>/points")
def admin_adjust_points(user_id):
    _, err = require_admin()
    if err:
        return err
    points_value = request.form.get("points", "0")
    # Validate points input from the admin form.
    try:
        points_value = int(points_value)
    except ValueError:
        points_value = 0
    # Recalculate tier based on the new point total.
    tier = _tier_for_points(points_value)
    conn = get_db()
    # Persist adjusted points and tier.
    conn.execute(
        """
        UPDATE users
        SET total_points = ?,
            available_points = ?,
            current_tier = ?
        WHERE id = ?
        """,
        (points_value, points_value, tier, user_id),
    )
    conn.commit()
    return redirect(url_for("admin.admin_user_detail", user_id=user_id))


# Validate text input length constraints for admin forms.
def _validate_text(value, min_len, max_len):
    text = (value or "").strip()
    if not (min_len <= len(text) <= max_len):
        raise ValueError(f"Length must be between {min_len} and {max_len} characters")
    return text


# Validate integer input ranges for admin forms.
def _validate_int(value, min_val, max_val=None):
    try:
        num = int(value)
    except (TypeError, ValueError):
        raise ValueError("Value must be an integer")
    if max_val is None and num < min_val:
        raise ValueError(f"Value must be >= {min_val}")
    if max_val is not None and not (min_val <= num <= max_val):
        raise ValueError(f"Value must be between {min_val} and {max_val}")
    return num


@admin_bp.post("/quests/create")
def admin_create_quest():
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate quest inputs from the admin form.
        title = _validate_text(request.form.get("title"), 5, 100)
        description = _validate_text(request.form.get("description"), 10, 500)
        reward = _validate_int(request.form.get("reward"), 10, 10000)
        total_required = _validate_int(request.form.get("total_required"), 1, 100)
    except ValueError:
        return _redirect_tab("tab-quests")

    conn = get_db()
    # Insert the quest into the database.
    conn.execute(
        """
        INSERT INTO quests (title, description, reward, total_required)
        VALUES (?, ?, ?, ?)
        """,
        (title, description, reward, total_required),
    )
    # Fetch the new quest id for user progress seeding.
    quest_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    cur = conn.cursor()
    # Seed user_quests rows for all existing users.
    cur.execute("SELECT id FROM users")
    user_ids = [row["id"] for row in cur.fetchall()]
    if user_ids:
        cur.executemany(
            "INSERT OR IGNORE INTO user_quests (user_id, quest_id, progress, completed) VALUES (?, ?, 0, 0)",
            [(user_id, quest_id) for user_id in user_ids],
        )
    conn.commit()
    return _redirect_tab("tab-quests")


@admin_bp.post("/quests/<int:quest_id>/update")
def admin_update_quest(quest_id):
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate quest inputs from the admin form.
        title = _validate_text(request.form.get("title"), 5, 100)
        description = _validate_text(request.form.get("description"), 10, 500)
        reward = _validate_int(request.form.get("reward"), 10, 10000)
        total_required = _validate_int(request.form.get("total_required"), 1, 100)
    except ValueError:
        return _redirect_tab("tab-quests")

    conn = get_db()
    # Persist quest updates.
    conn.execute(
        """
        UPDATE quests
        SET title = ?, description = ?, reward = ?, total_required = ?
        WHERE id = ?
        """,
        (title, description, reward, total_required, quest_id),
    )
    conn.commit()
    return _redirect_tab("tab-quests")


@admin_bp.post("/quests/<int:quest_id>/delete")
def admin_delete_quest(quest_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    # Remove user progress rows before deleting the quest.
    conn.execute("DELETE FROM user_quests WHERE quest_id = ?", (quest_id,))
    conn.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
    conn.commit()
    return _redirect_tab("tab-quests")


@admin_bp.post("/landmarks/create")
def admin_create_landmark():
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate landmark inputs from the admin form.
        name = _validate_text(request.form.get("name"), 3, 100)
        icon = _validate_text(request.form.get("icon"), 1, 10)
        story = _validate_text(request.form.get("story"), 20, 1000)
        question = _validate_text(request.form.get("question"), 10, 200)
        correct_answer = _validate_int(request.form.get("correct_answer"), 0, 3)
        x_coord = _validate_int(request.form.get("x_coord"), 0, 800)
        y_coord = _validate_int(request.form.get("y_coord"), 0, 550)
        points_value = _validate_int(request.form.get("points_value") or 100, 0, 10000)
    except ValueError:
        return _redirect_tab("tab-landmarks")

    conn = get_db()
    # Insert landmark definition into the database.
    conn.execute(
        """
        INSERT INTO landmarks
        (name, icon, story, question, correct_answer, x_coord, y_coord, points_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, icon, story, question, correct_answer, x_coord, y_coord, points_value),
    )
    # Fetch new landmark id for user progress seeding.
    landmark_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    cur = conn.cursor()
    # Seed user_landmarks rows for all existing users.
    cur.execute("SELECT id FROM users")
    user_ids = [row["id"] for row in cur.fetchall()]
    if user_ids:
        cur.executemany(
            "INSERT OR IGNORE INTO user_landmarks (user_id, landmark_id, unlocked, completed) VALUES (?, ?, 0, 0)",
            [(user_id, landmark_id) for user_id in user_ids],
        )
    conn.commit()
    return _redirect_tab("tab-landmarks")


@admin_bp.post("/landmarks/<int:landmark_id>/update")
def admin_update_landmark(landmark_id):
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate landmark inputs from the admin form.
        name = _validate_text(request.form.get("name"), 3, 100)
        icon = _validate_text(request.form.get("icon"), 1, 10)
        story = _validate_text(request.form.get("story"), 20, 1000)
        question = _validate_text(request.form.get("question"), 10, 200)
        correct_answer = _validate_int(request.form.get("correct_answer"), 0, 3)
        x_coord = _validate_int(request.form.get("x_coord"), 0, 800)
        y_coord = _validate_int(request.form.get("y_coord"), 0, 550)
        points_value = _validate_int(request.form.get("points_value") or 100, 0, 10000)
    except ValueError:
        return _redirect_tab("tab-landmarks")

    conn = get_db()
    # Persist landmark updates.
    conn.execute(
        """
        UPDATE landmarks
        SET name = ?, icon = ?, story = ?, question = ?, correct_answer = ?,
            x_coord = ?, y_coord = ?, points_value = ?
        WHERE id = ?
        """,
        (name, icon, story, question, correct_answer, x_coord, y_coord, points_value, landmark_id),
    )
    conn.commit()
    return _redirect_tab("tab-landmarks")


@admin_bp.post("/landmarks/<int:landmark_id>/delete")
def admin_delete_landmark(landmark_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    # Delete associated options and user progress before the landmark.
    conn.execute("DELETE FROM landmark_options WHERE landmark_id = ?", (landmark_id,))
    conn.execute("DELETE FROM user_landmarks WHERE landmark_id = ?", (landmark_id,))
    conn.execute("DELETE FROM landmarks WHERE id = ?", (landmark_id,))
    conn.commit()
    return _redirect_tab("tab-landmarks")


@admin_bp.post("/badges/create")
def admin_create_badge():
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate badge inputs from the admin form.
        name = _validate_text(request.form.get("name"), 3, 100)
        description = _validate_text(request.form.get("description"), 5, 500)
        category = _validate_text(request.form.get("category"), 3, 50)
        icon = _validate_text(request.form.get("icon"), 0, 50)
        threshold = _validate_int(request.form.get("threshold"), 1, 100000)
        requirement_type = request.form.get("requirement_type", "").strip()
        if requirement_type not in {"landmarks", "quests", "points", "tier"}:
            raise ValueError("Invalid requirement type")
    except ValueError:
        return _redirect_tab("tab-badges")

    conn = get_db()
    # Insert badge definition into the database.
    conn.execute(
        """
        INSERT INTO badges (name, icon, description, category, threshold, requirement_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, icon or "badge", description, category, threshold, requirement_type),
    )
    # Fetch new badge id for user badge seeding.
    badge_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    cur = conn.cursor()
    # Seed user_badges rows for all existing users.
    cur.execute("SELECT id FROM users")
    user_ids = [row["id"] for row in cur.fetchall()]
    if user_ids:
        cur.executemany(
            "INSERT OR IGNORE INTO user_badges (user_id, badge_id, earned) VALUES (?, ?, 0)",
            [(user_id, badge_id) for user_id in user_ids],
        )
    conn.commit()
    return _redirect_tab("tab-badges")


@admin_bp.post("/badges/<int:badge_id>/update")
def admin_update_badge(badge_id):
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate badge inputs from the admin form.
        name = _validate_text(request.form.get("name"), 3, 100)
        description = _validate_text(request.form.get("description"), 5, 500)
        category = _validate_text(request.form.get("category"), 3, 50)
        icon = _validate_text(request.form.get("icon"), 0, 50)
        threshold = _validate_int(request.form.get("threshold"), 1, 100000)
        requirement_type = request.form.get("requirement_type", "").strip()
        if requirement_type not in {"landmarks", "quests", "points", "tier"}:
            raise ValueError("Invalid requirement type")
    except ValueError:
        return _redirect_tab("tab-badges")

    conn = get_db()
    # Persist badge updates.
    conn.execute(
        """
        UPDATE badges
        SET name = ?, icon = ?, description = ?, category = ?, threshold = ?, requirement_type = ?
        WHERE id = ?
        """,
        (name, icon or "badge", description, category, threshold, requirement_type, badge_id),
    )
    conn.commit()
    return _redirect_tab("tab-badges")


@admin_bp.post("/badges/<int:badge_id>/delete")
def admin_delete_badge(badge_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    # Remove user badge rows before deleting the badge definition.
    conn.execute("DELETE FROM user_badges WHERE badge_id = ?", (badge_id,))
    conn.execute("DELETE FROM badges WHERE id = ?", (badge_id,))
    conn.commit()
    return _redirect_tab("tab-badges")


@admin_bp.post("/rewards/create")
def admin_create_reward():
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate reward inputs from the admin form.
        name = _validate_text(request.form.get("name"), 3, 100)
        cost = _validate_int(request.form.get("cost"), 1, 100000)
        icon = _validate_text(request.form.get("icon"), 0, 50)
        description = _validate_text(request.form.get("description"), 0, 200)
    except ValueError:
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_db()
    # Insert reward into the catalog.
    conn.execute(
        """
        INSERT INTO rewards (name, icon, cost, description, is_active)
        VALUES (?, ?, ?, ?, 1)
        """,
        (name, icon or "gift", cost, description),
    )
    conn.commit()
    return _redirect_tab("tab-rewards")


@admin_bp.post("/rewards/<int:reward_id>/update")
def admin_update_reward(reward_id):
    _, err = require_admin()
    if err:
        return err
    try:
        # Validate reward inputs from the admin form.
        name = _validate_text(request.form.get("name"), 3, 100)
        cost = _validate_int(request.form.get("cost"), 1, 100000)
        icon = _validate_text(request.form.get("icon"), 0, 50)
        description = _validate_text(request.form.get("description"), 0, 200)
        is_active = 1 if request.form.get("is_active") == "1" else 0
    except ValueError:
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_db()
    # Persist reward updates and active status.
    conn.execute(
        """
        UPDATE rewards
        SET name = ?, icon = ?, cost = ?, description = ?, is_active = ?
        WHERE id = ?
        """,
        (name, icon or "gift", cost, description, is_active, reward_id),
    )
    conn.commit()
    return _redirect_tab("tab-rewards")


@admin_bp.post("/rewards/<int:reward_id>/delete")
def admin_delete_reward(reward_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    # Archive the reward by toggling its active flag.
    conn.execute("UPDATE rewards SET is_active = 0 WHERE id = ?", (reward_id,))
    conn.commit()
    return _redirect_tab("tab-rewards")


def _require_external_access(app_key: str, table: str):
    if app_key not in EXTERNAL_APPS:
        raise ValueError("Unknown app key")
    conn = _get_external_conn(app_key)
    tables = _get_external_tables(conn)
    if table not in tables:
        conn.close()
        raise ValueError("Unknown table")
    columns = _get_table_columns(conn, table)
    return conn, columns


def _external_editable_columns(columns: list[str]) -> list[str]:
    return [col for col in columns if col != "id"]


def _filter_rows(conn: sqlite3.Connection, table: str, columns: list[str], query: str) -> list[dict]:
    if not query:
        return _get_table_rows(conn, table, limit=1000)
    like = f"%{query.strip()}%"
    where = " OR ".join([f"CAST({col} AS TEXT) LIKE ?" for col in columns])
    params = [like] * len(columns)
    cur = conn.cursor()
    rows = cur.execute(
        f"SELECT rowid AS _rowid, * FROM {table} WHERE {where} ORDER BY rowid DESC LIMIT 1000",
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def _export_to_csv(columns: list[str], rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(col) for col in columns])
    return buf.getvalue().encode("utf-8")


def _load_csv_rows(file_storage) -> tuple[list[str], list[list]]:
    content = file_storage.read().decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return [], []
    header = [str(h).strip() for h in rows[0]]
    data_rows = [r for r in rows[1:] if any(cell.strip() for cell in r if isinstance(cell, str)) or any(cell for cell in r)]
    return header, data_rows


@admin_bp.post("/external/<app_key>/<table>/create")
def admin_external_create(app_key: str, table: str):
    _, err = require_admin()
    if err:
        return err
    try:
        conn, columns = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        editable_columns = _external_editable_columns(columns)
        if not editable_columns:
            return _redirect_tab(f"tab-external-{app_key}")
        values = [request.form.get(col) for col in editable_columns]
        placeholders = ", ".join(["?"] * len(editable_columns))
        col_list = ", ".join(editable_columns)
        conn.execute(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        _log_admin_action(session.get("user_id"), "create", app_key, table, f"Inserted row into {table}")
    finally:
        conn.close()
    return _redirect_tab(f"tab-external-{app_key}")


@admin_bp.post("/external/<app_key>/<table>/<int:rowid>/update")
def admin_external_update(app_key: str, table: str, rowid: int):
    _, err = require_admin()
    if err:
        return err
    try:
        conn, columns = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        editable_columns = _external_editable_columns(columns)
        if not editable_columns:
            return _redirect_tab(f"tab-external-{app_key}")
        values = [request.form.get(col) for col in editable_columns]
        assignments = ", ".join([f"{col} = ?" for col in editable_columns])
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE rowid = ?",
            values + [rowid],
        )
        conn.commit()
        _log_admin_action(session.get("user_id"), "update", app_key, table, f"Updated rowid {rowid}")
    finally:
        conn.close()
    return _redirect_tab(f"tab-external-{app_key}")


@admin_bp.post("/external/<app_key>/<table>/<int:rowid>/delete")
def admin_external_delete(app_key: str, table: str, rowid: int):
    _, err = require_admin()
    if err:
        return err
    try:
        conn, _ = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        conn.execute(f"DELETE FROM {table} WHERE rowid = ?", (rowid,))
        conn.commit()
        _log_admin_action(session.get("user_id"), "delete", app_key, table, f"Deleted rowid {rowid}")
    finally:
        conn.close()
    return _redirect_tab(f"tab-external-{app_key}")


@admin_bp.get("/external/<app_key>/<table>/export")
def admin_external_export(app_key: str, table: str):
    _, err = require_admin()
    if err:
        return err
    query = (request.args.get("q") or "").strip()
    try:
        conn, columns = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        rows = _filter_rows(conn, table, columns, query)
        data = _export_to_csv(columns, rows)
    finally:
        conn.close()
    filename = f"{app_key}_{table}_export.csv"
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.get("/external/<app_key>/<table>/template")
def admin_external_template(app_key: str, table: str):
    _, err = require_admin()
    if err:
        return err
    try:
        conn, columns = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        cols = ["_rowid"] + columns
        data = _export_to_csv(cols, [])
    finally:
        conn.close()
    filename = f"{app_key}_{table}_template.csv"
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.post("/external/<app_key>/<table>/import")
def admin_external_import(app_key: str, table: str):
    _, err = require_admin()
    if err:
        return err
    file = request.files.get("file")
    if not file:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        conn, columns = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        header, data_rows = _load_csv_rows(file)
        if not header:
            return _redirect_tab(f"tab-external-{app_key}")
        header_map = {h: idx for idx, h in enumerate(header)}
        usable_cols = [c for c in columns if c in header_map]
        if not usable_cols:
            return _redirect_tab(f"tab-external-{app_key}")
        for row in data_rows:
            # Normalize cell values (trim whitespace from strings)
            row = [cell.strip() if isinstance(cell, str) else cell for cell in row]
            rowid = None
            if "_rowid" in header_map and header_map["_rowid"] < len(row):
                raw = row[header_map["_rowid"]]
                rowid = int(raw) if str(raw).strip().isdigit() else None
            values = [row[header_map[col]] if header_map[col] < len(row) else None for col in usable_cols]
            if rowid is not None:
                update_cols = [col for col in usable_cols if col != "id"]
                if not update_cols:
                    continue
                assignments = ", ".join([f"{col} = ?" for col in update_cols])
                conn.execute(
                    f"UPDATE {table} SET {assignments} WHERE rowid = ?",
                    [row[header_map[col]] if header_map[col] < len(row) else None for col in update_cols] + [rowid],
                )
                continue
            if "id" in header_map and "id" in columns and header_map["id"] < len(row):
                raw_id = row[header_map["id"]]
                id_value = int(raw_id) if str(raw_id).strip().isdigit() else None
                if id_value is not None:
                    update_cols = [col for col in usable_cols if col != "id"]
                    if not update_cols:
                        continue
                    assignments = ", ".join([f"{col} = ?" for col in update_cols])
                    conn.execute(
                        f"UPDATE {table} SET {assignments} WHERE id = ?",
                        [row[header_map[col]] if header_map[col] < len(row) else None for col in update_cols] + [id_value],
                    )
                    continue
            placeholders = ", ".join(["?"] * len(usable_cols))
            col_list = ", ".join(usable_cols)
            conn.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                values,
            )
        conn.commit()
        _log_admin_action(session.get("user_id"), "import", app_key, table, f"Imported {len(data_rows)} rows")
    finally:
        conn.close()
    return _redirect_tab(f"tab-external-{app_key}")


@admin_bp.post("/external/<app_key>/<table>/bulk-delete")
def admin_external_bulk_delete(app_key: str, table: str):
    _, err = require_admin()
    if err:
        return err
    rowids_raw = (request.form.get("rowids") or "").strip()
    if not rowids_raw:
        return _redirect_tab(f"tab-external-{app_key}")
    rowids = [int(r) for r in rowids_raw.split(",") if r.strip().isdigit()]
    if not rowids:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        conn, _ = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        conn.executemany(f"DELETE FROM {table} WHERE rowid = ?", [(r,) for r in rowids])
        conn.commit()
        _log_admin_action(session.get("user_id"), "bulk_delete", app_key, table, f"Deleted {len(rowids)} rows")
    finally:
        conn.close()
    return _redirect_tab(f"tab-external-{app_key}")


@admin_bp.post("/external/<app_key>/<table>/bulk-update")
def admin_external_bulk_update(app_key: str, table: str):
    _, err = require_admin()
    if err:
        return err
    column = (request.form.get("column") or "").strip()
    value = request.form.get("value")
    rowids_raw = (request.form.get("rowids") or "").strip()
    if not column or not rowids_raw:
        return _redirect_tab(f"tab-external-{app_key}")
    rowids = [int(r) for r in rowids_raw.split(",") if r.strip().isdigit()]
    if not rowids:
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        conn, columns = _require_external_access(app_key, table)
    except ValueError:
        return _redirect_tab(f"tab-external-{app_key}")
    if column not in columns or column == "id":
        conn.close()
        return _redirect_tab(f"tab-external-{app_key}")
    try:
        conn.executemany(
            f"UPDATE {table} SET {column} = ? WHERE rowid = ?",
            [(value, r) for r in rowids],
        )
        conn.commit()
        _log_admin_action(session.get("user_id"), "bulk_update", app_key, table, f"Updated {len(rowids)} rows column {column}")
    finally:
        conn.close()
    return _redirect_tab(f"tab-external-{app_key}")


@admin_bp.post("/external/users/<app_key>/<int:rowid>/role")
def admin_external_update_role(app_key: str, rowid: int):
    _, err = require_admin()
    if err:
        return err
    role = (request.form.get("role") or "").strip()
    is_admin = 1 if request.form.get("is_admin") == "1" else 0
    try:
        conn, columns = _require_external_access(app_key, "users")
    except ValueError:
        return _redirect_tab("tab-roles")
    cols = set(columns)
    try:
        if "role" in cols:
            conn.execute("UPDATE users SET role = ? WHERE rowid = ?", (role, rowid))
        if "is_admin" in cols:
            conn.execute("UPDATE users SET is_admin = ? WHERE rowid = ?", (is_admin, rowid))
        conn.commit()
        _log_admin_action(session.get("user_id"), "role_update", app_key, "users", f"Updated role for rowid {rowid}")
    finally:
        conn.close()
    return _redirect_tab("tab-roles")


@admin_bp.get("/external/export-all")
def admin_external_export_all():
    _, err = require_admin()
    if err:
        return err
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for key, meta in EXTERNAL_APPS.items():
            db_path = _external_db_path(key)
            if not db_path or not os.path.exists(db_path):
                continue
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            tables = _get_external_tables(conn)
            for table in tables:
                cols = _get_table_columns(conn, table)
                rows = _get_table_rows(conn, table, limit=100000)
                data = _export_to_csv(cols, rows)
                zf.writestr(f"{key}/{table}.csv", data)
            conn.close()
    buf.seek(0)
    _log_admin_action(session.get("user_id"), "export_all", "all", None, "Exported all DBs")
    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=all_databases.zip"},
    )


@admin_bp.get("/reports/<path:filename>")
def admin_download_report(filename: str):
    _, err = require_admin()
    if err:
        return err
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    path = os.path.join(reports_dir, filename)
    if not os.path.isfile(path):
        return _redirect_tab("tab-reports")
    with open(path, "rb") as f:
        data = f.read()
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
