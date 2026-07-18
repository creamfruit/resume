# Import wrapper utility to preserve route metadata on decorators.
from functools import wraps

# Import session access for request authentication checks.
from flask import jsonify, session


# Enforce session-based authentication for protected routes.
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        # Validate user session to prevent unauthorized access.
        if not session.get("user_id"):
            return jsonify({"success": False, "error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped
