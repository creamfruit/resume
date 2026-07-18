# Import datetime for redemption timestamps.
from datetime import datetime

# Import Flask routing utilities for reward APIs.
from flask import Blueprint, jsonify, request, session

# Import DB connector and admin guard for protected endpoints.
from views.db import get_db
from views.routes.admin_utils import require_admin

# This Blueprint groups reward CRUD and redemption APIs.
rewards_bp = Blueprint("rewards", __name__, url_prefix="/api/rewards")


# Resolve the current user id from session or request payload.
def _get_request_user_id():
    user_id = session.get("user_id")
    if user_id:
        return user_id
    data = request.get_json(silent=True) or {}
    return data.get("user_id")


# List rewards, optionally including user redemption status.
@rewards_bp.get("/")
def list_rewards():
    user_id = _get_request_user_id()
    if not user_id:
        user_id = request.args.get("user_id")
    conn = get_db()
    cur = conn.cursor()
    # Allow admins to query inactive rewards when requested.
    include_inactive = request.args.get("include_inactive") == "1"
    if include_inactive:
        user_id, err = require_admin()
        if err:
            return err
        # Query all rewards including inactive items.
        cur.execute(
            "SELECT id, name, icon, cost, description, is_active FROM rewards ORDER BY cost ASC"
        )
    else:
        # Query only active rewards for normal users.
        cur.execute(
            "SELECT id, name, icon, cost, description, is_active FROM rewards WHERE is_active = 1 ORDER BY cost ASC"
        )
    rewards = [dict(row) for row in cur.fetchall()]

    # Return catalog when no user context is available.
    if not user_id:
        return jsonify({"success": True, "rewards": rewards}), 200

    # Query which rewards the user has already redeemed.
    cur.execute("SELECT reward_id FROM user_rewards WHERE user_id = ?", (user_id,))
    redeemed = {row["reward_id"] for row in cur.fetchall()}

    # Query user balances to compute availability states.
    cur.execute(
        "SELECT total_points, available_points FROM users WHERE id = ?",
        (user_id,),
    )
    user_row = cur.fetchone()
    if user_row:
        available_points = user_row["available_points"]
        total_points = user_row["total_points"]
        # Backfill available points when legacy users have no redemptions.
        if available_points == 0 and total_points > 0:
            cur.execute(
                "SELECT 1 FROM user_rewards WHERE user_id = ?",
                (user_id,),
            )
            if not cur.fetchone():
                available_points = total_points
                cur.execute(
                    "UPDATE users SET available_points = ? WHERE id = ?",
                    (available_points, user_id),
                )
                conn.commit()
    else:
        available_points = 0

    # Compute reward status for each item.
    for reward in rewards:
        if reward["id"] in redeemed:
            reward["status"] = "redeemed"
        elif available_points >= reward["cost"]:
            reward["status"] = "available"
        else:
            reward["status"] = "locked"

    return jsonify({"success": True, "rewards": rewards, "available_points": available_points}), 200


# Return a single reward definition.
@rewards_bp.get("/<int:reward_id>")
def get_reward(reward_id):
    conn = get_db()
    cur = conn.cursor()
    # Query database for the reward by id.
    cur.execute(
        "SELECT id, name, icon, cost, description, is_active FROM rewards WHERE id = ?",
        (reward_id,),
    )
    row = cur.fetchone()
    # Return 404 if reward is not found.
    if not row:
        return jsonify({"success": False, "error": "Reward not found"}), 404
    return jsonify({"success": True, "reward": dict(row)}), 200


# Create a new reward (admin-only).
@rewards_bp.post("/")
def create_reward():
    _, err = require_admin()
    if err:
        return err
    # Validate required reward fields.
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    icon = (data.get("icon") or "").strip()
    cost = data.get("cost")
    if not name:
        return jsonify({"success": False, "error": "Name required"}), 400
    # Validate cost input.
    try:
        cost_val = int(cost)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Cost must be a number"}), 400
    if cost_val <= 0:
        return jsonify({"success": False, "error": "Cost must be positive"}), 400

    conn = get_db()
    cur = conn.cursor()
    # Insert reward record into the database.
    cur.execute(
        "INSERT INTO rewards (name, icon, cost, description, is_active) VALUES (?, ?, ?, ?, 1)",
        (name, icon, cost_val, data.get("description")),
    )
    conn.commit()
    return jsonify({"success": True, "reward_id": cur.lastrowid}), 201


# Update an existing reward (admin-only).
@rewards_bp.put("/<int:reward_id>")
def update_reward(reward_id):
    _, err = require_admin()
    if err:
        return err
    # Validate required reward fields.
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    icon = (data.get("icon") or "").strip()
    cost = data.get("cost")
    if not name:
        return jsonify({"success": False, "error": "Name required"}), 400
    # Validate cost input.
    try:
        cost_val = int(cost)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Cost must be a number"}), 400
    if cost_val <= 0:
        return jsonify({"success": False, "error": "Cost must be positive"}), 400

    conn = get_db()
    cur = conn.cursor()
    # Guard against updates to missing rewards.
    cur.execute("SELECT id FROM rewards WHERE id = ?", (reward_id,))
    if not cur.fetchone():
        return jsonify({"success": False, "error": "Reward not found"}), 404
    # Persist reward updates.
    cur.execute(
        """
        UPDATE rewards
        SET name = ?, icon = ?, cost = ?, description = ?
        WHERE id = ?
        """,
        (name, icon, cost_val, data.get("description"), reward_id),
    )
    conn.commit()
    return jsonify({"success": True, "message": "Reward updated"}), 200


# Archive a reward by toggling its active flag (admin-only).
@rewards_bp.delete("/<int:reward_id>")
def delete_reward(reward_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    # Guard against archiving a missing reward.
    cur.execute("SELECT id FROM rewards WHERE id = ?", (reward_id,))
    if not cur.fetchone():
        return jsonify({"success": False, "error": "Reward not found"}), 404
    # Archive the reward by setting is_active to 0.
    cur.execute("UPDATE rewards SET is_active = 0 WHERE id = ?", (reward_id,))
    conn.commit()
    return jsonify({"success": True, "message": "Reward archived"}), 200


# Redeem a reward for the current user.
@rewards_bp.post("/<int:reward_id>/redeem")
def redeem_reward(reward_id):
    user_id = _get_request_user_id()
    if not user_id:
        return jsonify({"success": False, "error": "Login required"}), 401

    conn = get_db()
    cur = conn.cursor()

    # Query reward cost and existence.
    cur.execute("SELECT id, cost FROM rewards WHERE id = ?", (reward_id,))
    reward = cur.fetchone()
    if not reward:
        return jsonify({"success": False, "error": "Reward not found"}), 404

    # Short-circuit if already redeemed.
    cur.execute(
        "SELECT 1 FROM user_rewards WHERE user_id = ? AND reward_id = ?",
        (user_id, reward_id),
    )
    if cur.fetchone():
        return jsonify({
            "success": True,
            "status": "redeemed",
            "message": "Reward already redeemed",
        }), 200

    # Load user point balances for eligibility checks.
    cur.execute(
        "SELECT total_points, available_points FROM users WHERE id = ?",
        (user_id,),
    )
    user_row = cur.fetchone()
    if not user_row:
        return jsonify({"success": False, "error": "User not found"}), 404

    available_points = user_row["available_points"]
    total_points = user_row["total_points"]
    # Backfill available points for legacy users without redemptions.
    if available_points < reward["cost"] and total_points >= reward["cost"]:
        cur.execute(
            "SELECT 1 FROM user_rewards WHERE user_id = ?",
            (user_id,),
        )
        if not cur.fetchone():
            available_points = total_points
            cur.execute(
                "UPDATE users SET available_points = ? WHERE id = ?",
                (available_points, user_id),
            )
            conn.commit()
    # Reject redemption when points are insufficient.
    if available_points < reward["cost"]:
        return jsonify({
            "success": False,
            "status": "locked",
            "error": "Not enough points",
        }), 400

    now = datetime.utcnow().isoformat()
    try:
        # Wrap redemption insert and points update in a transaction.
        conn.execute("BEGIN")
        cur.execute(
            """
            INSERT INTO user_rewards (user_id, reward_id, redeemed_at)
            VALUES (?, ?, ?)
            """,
            (user_id, reward_id, now),
        )
        cur.execute(
            "UPDATE users SET available_points = available_points - ? WHERE id = ?",
            (reward["cost"], user_id),
        )
        conn.commit()
    except Exception:
        # Roll back on error to preserve consistency.
        conn.rollback()
        raise

    # Fetch updated balance for response payload.
    cur.execute(
        "SELECT available_points FROM users WHERE id = ?",
        (user_id,),
    )
    updated = cur.fetchone()

    return jsonify({
        "success": True,
        "status": "redeemed",
        "message": "Reward redeemed",
        "remaining_points": updated["available_points"] if updated else None,
    }), 200
