# Import Flask routing, templating, and session management utilities.
from flask import Blueprint, redirect, render_template, request, session, url_for
# Import password hashing utilities for credential verification.
from werkzeug.security import check_password_hash, generate_password_hash

# Import DB access and user creation helpers.
from views.db import close_db, get_db
from views.user import createUser

# This Blueprint groups auth-related page routes.
auth_bp = Blueprint("auth", __name__)


# Populate default user relationships after signup.
def _create_user_defaults(conn, user_id):
    cur = conn.cursor()
    # Seed quest progress rows for the new user.
    cur.execute("SELECT id FROM quests")
    quest_ids = [row["id"] for row in cur.fetchall()]
    if quest_ids:
        cur.executemany(
            "INSERT OR IGNORE INTO user_quests (user_id, quest_id, progress, completed) VALUES (?, ?, 0, 0)",
            [(user_id, qid) for qid in quest_ids],
        )

    # Seed badge rows for the new user.
    cur.execute("SELECT id FROM badges")
    badge_ids = [row["id"] for row in cur.fetchall()]
    if badge_ids:
        cur.executemany(
            "INSERT OR IGNORE INTO user_badges (user_id, badge_id, earned) VALUES (?, ?, 0)",
            [(user_id, bid) for bid in badge_ids],
        )

    # Seed landmark rows for the new user.
    cur.execute("SELECT id FROM landmarks")
    landmark_ids = [row["id"] for row in cur.fetchall()]
    if landmark_ids:
        cur.executemany(
            "INSERT OR IGNORE INTO user_landmarks (user_id, landmark_id, unlocked, completed) VALUES (?, ?, 0, 0)",
            [(user_id, lid) for lid in landmark_ids],
        )


# Render login and handle credential submission.
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Normalize input for lookup and authentication.
        username = request.form.get("username","").strip()
        password = request.form.get("password","")

        conn = get_db()
        cur = conn.cursor()
        # Query for user by username or email.
        cur.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, username),
        )
        user = cur.fetchone()
        cur.close()

        # Validate credentials before issuing a session.
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid username or password")

        # Initialize session state for the logged-in user.
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["is_admin"] = bool(user["is_admin"])
        return redirect(url_for("main.index"))

    return render_template("login.html")


# Render signup and handle new user registration.
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        # Normalize input fields for validation and storage.
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # Validate required fields before creating a user.
        if not username or not email or not password:
            return render_template("signup.html", error="Username, email, and password required")

        # Create the user and handle uniqueness violations.
        user = createUser(username, email, password)
        if not user:
            return render_template("signup.html", error="Username or email already exists")

        # Initialize default progress rows for the new account.
        close_db()
        conn = get_db()
        _create_user_defaults(conn, user.id)
        conn.commit()

        # Start a session for the newly registered user.
        session["user_id"] = user.id
        session["username"] = user.username
        session["is_admin"] = bool(getattr(user, "is_admin", 0))
        return redirect(url_for("main.index"))

    return render_template("signup.html")


# Clear the session and redirect to login.
@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
