# Import datetime for completion timestamps.
from datetime import datetime

# Import Flask routing utilities for progress APIs.
from flask import jsonify, request

# Import DB connector for progress updates.
from views.db import get_db


# Helper to fetch a user row by id.
def _get_user(conn, user_id):
    cur = conn.cursor()
    # Query user record for validation and metrics.
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()


# Helper to fetch a quest row by id.
def _get_quest(conn, quest_id):
    cur = conn.cursor()
    # Query quest record for progress logic.
    cur.execute("SELECT * FROM quests WHERE id = ?", (quest_id,))
    return cur.fetchone()


# Helper to fetch a landmark row by id.
def _get_landmark(conn, landmark_id):
    cur = conn.cursor()
    # Query landmark record for unlock/complete logic.
    cur.execute("SELECT * FROM landmarks WHERE id = ?", (landmark_id,))
    return cur.fetchone()


# Ensure a user_quest row exists for progress tracking.
def _ensure_user_quest(conn, user_id, quest_id):
    cur = conn.cursor()
    # Query existing user quest progress.
    cur.execute(
        "SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?",
        (user_id, quest_id),
    )
    row = cur.fetchone()
    if row:
        return row
    # Insert a new user_quest row if missing.
    cur.execute(
        "INSERT INTO user_quests (user_id, quest_id, progress, completed) VALUES (?, ?, 0, 0)",
        (user_id, quest_id),
    )
    cur.execute(
        "SELECT * FROM user_quests WHERE user_id = ? AND quest_id = ?",
        (user_id, quest_id),
    )
    return cur.fetchone()


# Ensure a user_landmark row exists for progress tracking.
def _ensure_user_landmark(conn, user_id, landmark_id):
    cur = conn.cursor()
    # Query existing user landmark progress.
    cur.execute(
        "SELECT * FROM user_landmarks WHERE user_id = ? AND landmark_id = ?",
        (user_id, landmark_id),
    )
    row = cur.fetchone()
    if row:
        return row
    # Insert a new user_landmark row if missing.
    cur.execute(
        "INSERT INTO user_landmarks (user_id, landmark_id, unlocked, completed) VALUES (?, ?, 0, 0)",
        (user_id, landmark_id),
    )
    cur.execute(
        "SELECT * FROM user_landmarks WHERE user_id = ? AND landmark_id = ?",
        (user_id, landmark_id),
    )
    return cur.fetchone()


# Count completed quests for badge evaluation.
def _count_completed_quests(conn, user_id):
    cur = conn.cursor()
    # Query completion count for the given user.
    cur.execute(
        "SELECT COUNT(*) AS count FROM user_quests WHERE user_id = ? AND completed = 1",
        (user_id,),
    )
    return cur.fetchone()["count"]


# Count completed landmarks for badge evaluation.
def _count_completed_landmarks(conn, user_id):
    cur = conn.cursor()
    # Query completion count for the given user.
    cur.execute(
        "SELECT COUNT(*) AS count FROM user_landmarks WHERE user_id = ? AND completed = 1",
        (user_id,),
    )
    return cur.fetchone()["count"]


# Count completed skills for badge evaluation.
def _count_completed_skills(conn, user_id):
    cur = conn.cursor()
    # Query completion count for the given user.
    cur.execute(
        "SELECT COUNT(*) AS count FROM user_skills WHERE user_id = ? AND completed = 1",
        (user_id,),
    )
    return cur.fetchone()["count"]

# Compute tier thresholds based on total points.
def _tier_for_points(points):
    if points >= 35000:
        return 6
    if points >= 20000:
        return 5
    if points >= 10000:
        return 4
    if points >= 5000:
        return 3
    if points >= 2000:
        return 2
    return 1


# Check all badge rules and unlock any that now qualify.
def _check_and_unlock_badges(conn, user_id):
    cur = conn.cursor()
    # Query user points/tier to evaluate badge rules.
    cur.execute("SELECT total_points, current_tier FROM users WHERE id = ?", (user_id,))
    user_row = cur.fetchone()
    if not user_row:
        return []

    # Align persisted tier with computed tier.
    computed_tier = _tier_for_points(user_row["total_points"])
    if user_row["current_tier"] != computed_tier:
        cur.execute(
            "UPDATE users SET current_tier = ? WHERE id = ?",
            (computed_tier, user_id),
        )

    metrics = {
        "quests": _count_completed_quests(conn, user_id),
        "landmarks": _count_completed_landmarks(conn, user_id),
        "skills": _count_completed_skills(conn, user_id),
        "points": user_row["total_points"],
        "tier": computed_tier,
    }

    # Load all badge definitions for evaluation.
    cur.execute("SELECT * FROM badges")
    badges = cur.fetchall()
    unlocked = []

    # Evaluate each badge against current metrics.
    for badge in badges:
        requirement = badge["requirement_type"]
        threshold = badge["threshold"]
        # Treat the "all skills" badge as a dynamic threshold.
        if requirement == "skills" and threshold >= 999:
            cur.execute("SELECT COUNT(*) AS count FROM skills")
            threshold = cur.fetchone()["count"]
        if metrics.get(requirement, 0) < threshold:
            continue

        # Query existing user_badges row to avoid duplicates.
        cur.execute(
            "SELECT * FROM user_badges WHERE user_id = ? AND badge_id = ?",
            (user_id, badge["id"]),
        )
        user_badge = cur.fetchone()

        if user_badge and user_badge["earned"]:
            continue

        # Update existing row or insert a new earned badge.
        if user_badge:
            cur.execute(
                "UPDATE user_badges SET earned = 1, earned_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), user_badge["id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO user_badges (user_id, badge_id, earned, earned_at)
                VALUES (?, ?, 1, ?)
                """,
                (user_id, badge["id"], datetime.utcnow().isoformat()),
            )

        unlocked.append(dict(badge))

    return unlocked


# Register progress-related endpoints on the main app.
def register_progress_routes(app):
    # Update quest progress and award points/badges.
    @app.route("/api/users/<int:user_id>/quests/<int:quest_id>/progress", methods=["POST"])
    def update_quest_progress(user_id, quest_id):
        # Parse increment payload with a default of 1.
        data = request.get_json(silent=True) or {}
        increment = int(data.get("increment", 1))
        # Validate increment to prevent negative updates.
        if increment < 1:
            return jsonify({"success": False, "error": "Increment must be >= 1"}), 400

        conn = get_db()
        # Load user and quest to validate inputs.
        user = _get_user(conn, user_id)
        quest = _get_quest(conn, quest_id)

        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        if not quest:
            return jsonify({"success": False, "error": "Quest not found"}), 404

        # Ensure a user_quest row exists for progress updates.
        user_quest = _ensure_user_quest(conn, user_id, quest_id)

        if user_quest["completed"]:
            return jsonify({"success": False, "error": "Quest already completed"}), 400

        # Compute new progress and completion state.
        new_progress = user_quest["progress"] + increment
        completed = 1 if new_progress >= quest["total_required"] else 0
        completed_at = datetime.utcnow().isoformat() if completed else None

        cur = conn.cursor()
        # Persist quest progress changes.
        cur.execute(
            """
            UPDATE user_quests
            SET progress = ?, completed = ?, completed_at = COALESCE(?, completed_at)
            WHERE id = ?
            """,
            (new_progress, completed, completed_at, user_quest["id"]),
        )

        awarded = 0
        # Award quest points on completion.
        if completed:
            awarded = quest["reward"]
            cur.execute(
                """
                UPDATE users
                SET total_points = total_points + ?,
                    available_points = available_points + ?
                WHERE id = ?
                """,
                (awarded, awarded, user_id),
            )

        conn.commit()
        # Check for any newly unlocked badges after progress update.
        unlocked_badges = _check_and_unlock_badges(conn, user_id)

        return jsonify({
            "message": "Progress updated",
            "progress": new_progress,
            "completed": bool(completed),
            "awarded_points": awarded,
            "unlocked_badges": unlocked_badges,
        }), 200

    # Force a badge evaluation pass for a user.
    @app.route("/api/users/<int:user_id>/achievements/check", methods=["POST"])
    def check_achievements(user_id):
        conn = get_db()
        user = _get_user(conn, user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        # Evaluate badge unlocks and return any newly earned ones.
        unlocked = _check_and_unlock_badges(conn, user_id)
        conn.commit()
        return jsonify({"message": "Checked achievements", "unlocked": unlocked}), 200

    # Unlock a landmark for a user once prerequisites are met.
    @app.route("/api/users/<int:user_id>/landmarks/<int:landmark_id>/unlock", methods=["POST"])
    def unlock_landmark(user_id, landmark_id):
        conn = get_db()
        user = _get_user(conn, user_id)
        landmark = _get_landmark(conn, landmark_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        if not landmark:
            return jsonify({"success": False, "error": "Landmark not found"}), 404

        # Ensure a user_landmark row exists for progress updates.
        user_landmark = _ensure_user_landmark(conn, user_id, landmark_id)
        if user_landmark["unlocked"]:
            return jsonify({"message": "Landmark already unlocked"}), 200

        cur = conn.cursor()
        # Mark the landmark as unlocked with a timestamp.
        cur.execute(
            """
            UPDATE user_landmarks
            SET unlocked = 1, unlocked_at = ?
            WHERE id = ?
            """,
            (datetime.utcnow().isoformat(), user_landmark["id"]),
        )
        conn.commit()
        return jsonify({"message": "Landmark unlocked"}), 200

    # Complete a landmark and award points/badges.
    @app.route("/api/users/<int:user_id>/landmarks/<int:landmark_id>/complete", methods=["POST"])
    def complete_landmark(user_id, landmark_id):
        conn = get_db()
        user = _get_user(conn, user_id)
        landmark = _get_landmark(conn, landmark_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        if not landmark:
            return jsonify({"success": False, "error": "Landmark not found"}), 404

        # Ensure the landmark is unlocked before completion.
        user_landmark = _ensure_user_landmark(conn, user_id, landmark_id)
        if not user_landmark["unlocked"]:
            return jsonify({"success": False, "error": "Landmark not unlocked"}), 400
        if user_landmark["completed"]:
            return jsonify({"success": False, "error": "Landmark already completed"}), 400

        awarded = landmark["points_value"]
        cur = conn.cursor()
        # Mark the landmark as completed with a timestamp.
        cur.execute(
            """
            UPDATE user_landmarks
            SET completed = 1, completed_at = ?
            WHERE id = ?
            """,
            (datetime.utcnow().isoformat(), user_landmark["id"]),
        )
        # Award points to the user for completion.
        cur.execute(
            """
            UPDATE users
            SET total_points = total_points + ?,
                available_points = available_points + ?
            WHERE id = ?
            """,
            (awarded, awarded, user_id),
        )
        conn.commit()
        # Check for any newly unlocked badges after completion.
        unlocked_badges = _check_and_unlock_badges(conn, user_id)

        return jsonify({
            "message": "Landmark completed",
            "awarded_points": awarded,
            "unlocked_badges": unlocked_badges,
        }), 200

    # Return dashboard data for a user including progress summaries.
    @app.route("/api/users/<int:user_id>/dashboard", methods=["GET"])
    def get_dashboard(user_id):
        conn = get_db()
        user = _get_user(conn, user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        # Keep user tier in sync with points.
        computed_tier = _tier_for_points(user["total_points"])
        if user["current_tier"] != computed_tier:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET current_tier = ? WHERE id = ?",
                (computed_tier, user_id),
            )
            conn.commit()
            user = _get_user(conn, user_id)

        # Aggregate metrics used for badge and UI calculations.
        metrics = {
            "quests": _count_completed_quests(conn, user_id),
            "landmarks": _count_completed_landmarks(conn, user_id),
            "skills": _count_completed_skills(conn, user_id),
            "points": user["total_points"],
            "tier": computed_tier,
        }

        cur = conn.cursor()
        # Query quests with progress for the dashboard.
        cur.execute(
            """
            SELECT q.*,
                   COALESCE(uq.progress, 0) AS progress,
                   CASE
                       WHEN uq.completed = 1 OR COALESCE(uq.progress, 0) >= q.total_required THEN 1
                       ELSE 0
                   END AS completed
            FROM quests q
            LEFT JOIN user_quests uq
                ON uq.quest_id = q.id AND uq.user_id = ?
            ORDER BY q.id
            """,
            (user_id,),
        )
        quests = [dict(row) for row in cur.fetchall()]

        # Query badges with earned state.
        cur.execute(
            """
            SELECT b.*, COALESCE(ub.earned, 0) AS earned,
                   ub.earned_at AS earned_at
            FROM badges b
            LEFT JOIN user_badges ub
                ON ub.badge_id = b.id AND ub.user_id = ?
            ORDER BY b.id
            """,
            (user_id,),
        )
        badges = [dict(row) for row in cur.fetchall()]
        # Compute per-badge progress for client display.
        for badge in badges:
            requirement = badge.get("requirement_type")
            if requirement == "skills" and badge.get("threshold", 0) >= 999:
                cur.execute("SELECT COUNT(*) AS count FROM skills")
                badge["threshold"] = cur.fetchone()["count"]
                badge["current"] = metrics["skills"]
            else:
                badge["current"] = metrics.get(requirement)

        # Query landmarks with user unlock/completion state.
        cur.execute(
            """
            SELECT l.*, COALESCE(ul.unlocked, 0) AS unlocked,
                   COALESCE(ul.completed, 0) AS completed
            FROM landmarks l
            LEFT JOIN user_landmarks ul
                ON ul.landmark_id = l.id AND ul.user_id = ?
            ORDER BY l.id
            """,
            (user_id,),
        )
        landmarks = [dict(row) for row in cur.fetchall()]

        # Query rewards with redemption state.
        cur.execute(
            """
            SELECT r.*, CASE WHEN ur.id IS NULL THEN 0 ELSE 1 END AS redeemed
            FROM rewards r
            LEFT JOIN user_rewards ur
                ON ur.reward_id = r.id AND ur.user_id = ?
            WHERE r.is_active = 1
            ORDER BY r.cost
            """,
            (user_id,),
        )
        rewards = [dict(row) for row in cur.fetchall()]

        available_points = user["available_points"]
        # Derive reward status based on balances and redemption.
        for reward in rewards:
            if reward["redeemed"]:
                reward["status"] = "redeemed"
            elif available_points >= reward["cost"]:
                reward["status"] = "available"
            else:
                reward["status"] = "locked"

        # Return consolidated dashboard payload.
        return jsonify({
            "user": dict(user),
            "quests": quests,
            "badges": badges,
            "landmarks": landmarks,
            "rewards": rewards,
        }), 200
