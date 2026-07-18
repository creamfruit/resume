# Import Flask routing primitives for main UI endpoints.
from flask import Blueprint, jsonify, render_template, session, redirect

# Import auth guard and DB connector for dashboard data.
from views.authenticate import login_required
from views.db import get_db

# This Blueprint groups primary UI routes for the app shell.
main_bp = Blueprint("main", __name__)

def _render_aden_dashboard(user_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, username, points, is_admin FROM users WHERE id = ?",
        (user_id,)
    )
    user = cur.fetchone()

    cur.execute("""
        SELECT q.*,
               COALESCE(ql.progress, 0) AS progress,
               COALESCE(ql.completed, 0) AS completed
        FROM quests q
        LEFT JOIN user_quests ql
          ON q.id = ql.quest_id AND ql.user_id = ?
        ORDER BY q.id
    """, (user_id,))
    quests = cur.fetchall()

    cur.execute("""
        SELECT r.*,
               CASE WHEN ur.id IS NULL THEN 0 ELSE 1 END AS redeemed
        FROM rewards r
        LEFT JOIN user_rewards ur
          ON r.id = ur.reward_id AND ur.user_id = ?
        ORDER BY r.cost
    """, (user_id,))
    rewards = cur.fetchall()

    cur.execute("""
        SELECT a.*,
               CASE WHEN ua.id IS NULL THEN 0 ELSE 1 END AS earned
        FROM badges a
        LEFT JOIN user_badges ua
          ON a.id = ua.badge_id AND ua.user_id = ?
        ORDER BY a.id
    """, (user_id,))
    achievements = cur.fetchall()

    cur.close()

    return render_template(
        "index.html",
        user=user,
        quests=quests,
        rewards=rewards,
        achievements=achievements
    )


# Public homepage: send users to Ryan's landing UI.
@main_bp.route("/", methods=["GET"])
def index():
    return redirect("/ryan/")


# Dashboard page for logged-in users.
@main_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    user_id = session["user_id"]
    return _render_aden_dashboard(user_id)


@main_bp.route("/achievements", methods=["GET"])
@login_required
def achievements():
    user_id = session["user_id"]
    return _render_aden_dashboard(user_id)


# Explore page for map and discovery content.
@main_bp.route("/explore", methods=["GET"])
@login_required
def explore():
    return render_template("explore.html")


# Lightweight health check endpoint for uptime monitoring.
@main_bp.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
