# Import Flask routing utilities for badge APIs.
from flask import Blueprint, jsonify, request

# Import DB connector and admin guard for protected actions.
from views.db import get_db
from views.routes.admin_utils import require_admin

# This Blueprint groups badge CRUD APIs.
badges_bp = Blueprint("badges", __name__, url_prefix="/api/badges")


# Validate badge payloads for admin CRUD operations.
def _validate_badge(data):
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    category = (data.get("category") or "").strip()
    icon = (data.get("icon") or "").strip()
    requirement_type = (data.get("requirement_type") or "").strip()
    threshold = data.get("threshold")

    # Validate required text fields.
    if not name:
        return "Name required"
    if not description:
        return "Description required"
    if not category:
        return "Category required"
    # Validate requirement_type against supported values.
    if requirement_type not in {"landmarks", "quests", "points", "tier"}:
        return "Requirement type must be landmarks, quests, points, or tier"
    # Validate numeric threshold.
    try:
        threshold_val = int(threshold)
    except (TypeError, ValueError):
        return "Threshold must be a number"
    if threshold_val <= 0:
        return "Threshold must be positive"

    return None


# List all badge definitions.
@badges_bp.get("/")
def list_badges():
    conn = get_db()
    cur = conn.cursor()
    # Query database for badge definitions.
    cur.execute(
        """
        SELECT id, name, icon, description, category, threshold, requirement_type
        FROM badges
        ORDER BY id
        """
    )
    return jsonify({"success": True, "badges": [dict(row) for row in cur.fetchall()]}), 200


# Return a single badge by id.
@badges_bp.get("/<int:badge_id>")
def get_badge(badge_id):
    conn = get_db()
    cur = conn.cursor()
    # Query database for the requested badge.
    cur.execute(
        """
        SELECT id, name, icon, description, category, threshold, requirement_type
        FROM badges
        WHERE id = ?
        """,
        (badge_id,),
    )
    row = cur.fetchone()
    # Return 404 when badge is missing.
    if not row:
        return jsonify({"success": False, "error": "Badge not found"}), 404
    return jsonify({"success": True, "badge": dict(row)}), 200


# Create a new badge (admin-only).
@badges_bp.post("/")
def create_badge():
    _, err = require_admin()
    if err:
        return err
    # Parse and validate payload.
    data = request.get_json(silent=True) or {}
    error = _validate_badge(data)
    if error:
        return jsonify({"success": False, "error": error}), 400

    conn = get_db()
    cur = conn.cursor()
    # Insert badge row into the database.
    cur.execute(
        """
        INSERT INTO badges (name, icon, description, category, threshold, requirement_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"].strip(),
            data.get("icon", "").strip(),
            data["description"].strip(),
            data["category"].strip(),
            int(data["threshold"]),
            data["requirement_type"].strip(),
        ),
    )
    conn.commit()
    return jsonify({"success": True, "badge_id": cur.lastrowid}), 201


# Update an existing badge (admin-only).
@badges_bp.put("/<int:badge_id>")
def update_badge(badge_id):
    _, err = require_admin()
    if err:
        return err
    # Parse and validate payload.
    data = request.get_json(silent=True) or {}
    error = _validate_badge(data)
    if error:
        return jsonify({"success": False, "error": error}), 400

    conn = get_db()
    cur = conn.cursor()
    # Guard against updates to missing badges.
    cur.execute("SELECT id FROM badges WHERE id = ?", (badge_id,))
    if not cur.fetchone():
        return jsonify({"success": False, "error": "Badge not found"}), 404
    # Persist badge field updates.
    cur.execute(
        """
        UPDATE badges
        SET name = ?, icon = ?, description = ?, category = ?, threshold = ?, requirement_type = ?
        WHERE id = ?
        """,
        (
            data["name"].strip(),
            data.get("icon", "").strip(),
            data["description"].strip(),
            data["category"].strip(),
            int(data["threshold"]),
            data["requirement_type"].strip(),
            badge_id,
        ),
    )
    conn.commit()
    return jsonify({"success": True, "message": "Badge updated"}), 200


# Delete a badge (admin-only).
@badges_bp.delete("/<int:badge_id>")
def delete_badge(badge_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    # Guard against deletion of missing records.
    cur.execute("SELECT id FROM badges WHERE id = ?", (badge_id,))
    if not cur.fetchone():
        return jsonify({"success": False, "error": "Badge not found"}), 404
    # Delete the badge row.
    cur.execute("DELETE FROM badges WHERE id = ?", (badge_id,))
    conn.commit()
    return jsonify({"success": True, "message": "Badge deleted"}), 200
