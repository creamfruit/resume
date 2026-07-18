# Import Flask utilities for session access and JSON errors.
from flask import jsonify, session

# Import DB connector to validate admin status.
from views.db import get_db


# Validate that the current session belongs to an admin user.
def require_admin():
    if session.get("is_admin"):
        return session.get("user_id"), None
    user_id = session.get("user_id")
    if not user_id:
        return None, (jsonify({"success": False, "error": "Not logged in"}), 401)
    conn = get_db()
    cur = conn.cursor()
    # Query admin flag for the current user.
    cur.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row or not row["is_admin"]:
        return None, (jsonify({"success": False, "error": "Admin access required"}), 403)
    return user_id, None
