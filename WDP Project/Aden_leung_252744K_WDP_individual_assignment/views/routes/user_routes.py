# Import Flask routing primitives for user APIs.
from flask import Blueprint, request, jsonify, session
# Import user data access and auth helpers.
from views.user import createUser, getUserById, getUserByUsername, updateUser, deleteUser, authenticateUser, addUserPoints
# Import form validators for user payloads.
from views.forms import UserForm, UserUpdateForm

# Import time utilities for streak and check-in logic.
import calendar
from datetime import datetime, timedelta

# Import DB connector for user-related queries.
from views.db import get_db


# Map total points into tier levels for gamification.
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


# This Blueprint groups user-related API endpoints.
user_bp = Blueprint("user", __name__, url_prefix="/api/users")


@user_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Expected JSON format:
    {
        "username": "johndoe",
        "email": "john@example.com",
        "password": "securepassword123"
    }
    """
    try:
        # Parse and validate incoming JSON with a form schema.
        data = request.get_json(silent=True) or {}
        form = UserForm(data=data, meta={'csrf': False})
        if not form.validate():
            return jsonify({
                'success': False,
                'error': 'Invalid input',
                'details': form.errors
            }), 400
        
        # Create user after validation passes.
        user = createUser(
            username=form.username.data.strip(),
            email=form.email.data.strip(),
            password=form.password.data
        )
        
        # Return conflict if username/email already exists.
        if not user:
            return jsonify({
                'success': False,
                'error': 'Username or email already exists'
            }), 409
        
        # Return the created user payload.
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate a user.
    
    Expected JSON format:
    {
        "username": "johndoe",  // Can be username or email
        "password": "securepassword123"
    }
    """
    try:
        # Parse JSON payload from the client.
        data = request.get_json(silent=True) or {}
        
        # Validate required credentials are provided.
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400
        
        # Authenticate against stored credentials.
        user = authenticateUser(data['username'], data['password'])
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Invalid username or password'
            }), 401
        
        # Store user ID in session for subsequent requests.
        session['user_id'] = user.get_id()
        session['username'] = user.get_username()

        # Update streak and active days for daily login tracking.
        conn = get_db()
        cur = conn.cursor()
        # Query existing streak and last login details.
        cur.execute(
            "SELECT last_login_date, current_streak, active_days FROM users WHERE id = ?",
            (user.get_id(),),
        )
        row = cur.fetchone()
        today = datetime.utcnow().date()
        today_str = today.isoformat()
        current_streak = 0
        active_days = 1
        # Compute streak progression based on last login date.
        if row:
            last_login = row["last_login_date"]
            current_streak = row["current_streak"] or 0
            active_days = row["active_days"] or 1
            if last_login:
                last_date = datetime.fromisoformat(last_login).date()
                if last_date == today:
                    pass
                elif last_date == (today - timedelta(days=1)):
                    current_streak += 1
                    active_days += 1
                else:
                    current_streak = 1
                    active_days += 1
            else:
                current_streak = 1
        else:
            current_streak = 1

        # Persist updated streak and activity counters.
        cur.execute(
            """
            UPDATE users
            SET last_login_date = ?,
                current_streak = ?,
                active_days = ?
            WHERE id = ?
            """,
            (today_str, current_streak, active_days, user.get_id()),
        )
        # Record daily check-in if not already logged.
        cur.execute(
            "SELECT id FROM user_checkins WHERE user_id = ? AND checkin_date = ?",
            (user.get_id(), today_str),
        )
        has_checkin = cur.fetchone()
        # Insert a check-in row for the current date when absent.
        if not has_checkin:
            cur.execute(
                "INSERT INTO user_checkins (user_id, checkin_date, created_at) VALUES (?, ?, ?)",
                (user.get_id(), today_str, datetime.utcnow().isoformat()),
            )

        bonus_points = 0
        # Compute weekly bonus eligibility.
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_start_str = week_start.isoformat()
        week_end_str = week_end.isoformat()
        # Count check-ins within the current week.
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM user_checkins
            WHERE user_id = ? AND checkin_date BETWEEN ? AND ?
            """,
            (user.get_id(), week_start_str, week_end_str),
        )
        # Award weekly bonus once per week if fully checked in.
        if cur.fetchone()["count"] == 7:
            cur.execute(
                """
                SELECT id FROM checkin_rewards
                WHERE user_id = ? AND reward_type = 'weekly' AND period_start = ?
                """,
                (user.get_id(), week_start_str),
            )
            if not cur.fetchone():
                bonus_points += 100
                cur.execute(
                    """
                    INSERT INTO checkin_rewards (user_id, reward_type, period_start, awarded_at)
                    VALUES (?, 'weekly', ?, ?)
                    """,
                    (user.get_id(), week_start_str, datetime.utcnow().isoformat()),
                )

        # Compute monthly bonus eligibility.
        month_start = today.replace(day=1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        month_end = month_start + timedelta(days=days_in_month - 1)
        month_start_str = month_start.isoformat()
        month_end_str = month_end.isoformat()
        # Count check-ins within the current month.
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM user_checkins
            WHERE user_id = ? AND checkin_date BETWEEN ? AND ?
            """,
            (user.get_id(), month_start_str, month_end_str),
        )
        # Award monthly bonus once per month if fully checked in.
        if cur.fetchone()["count"] == days_in_month:
            cur.execute(
                """
                SELECT id FROM checkin_rewards
                WHERE user_id = ? AND reward_type = 'monthly' AND period_start = ?
                """,
                (user.get_id(), month_start_str),
            )
            if not cur.fetchone():
                bonus_points += 500
                cur.execute(
                    """
                    INSERT INTO checkin_rewards (user_id, reward_type, period_start, awarded_at)
                    VALUES (?, 'monthly', ?, ?)
                    """,
                    (user.get_id(), month_start_str, datetime.utcnow().isoformat()),
                )

        # Apply bonus points if any rewards were earned.
        if bonus_points:
            cur.execute(
                """
                UPDATE users
                SET total_points = total_points + ?,
                    available_points = available_points + ?
                WHERE id = ?
                """,
                (bonus_points, bonus_points, user.get_id()),
            )
        conn.commit()
        user = getUserById(user.get_id())
        
        # Return authenticated user payload.
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/logout', methods=['POST'])
def logout():
    """Logout current user"""
    # Clear session to end the user's authenticated state.
    session.clear()
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@user_bp.route('/current', methods=['GET'])
def get_current_user():
    """Get current logged-in user"""
    user_id = session.get('user_id')
    
    # Guard against missing session state.
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Not logged in'
        }), 401
    
    user = getUserById(user_id)
    
    # Clear session if the user record no longer exists.
    if not user:
        session.clear()
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 200


@user_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user by ID"""
    try:
        user = getUserById(user_id)
        
        # Return 404 when the user does not exist.
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>', methods=['PUT'])
def update_user_info(user_id):
    """
    Update user information.
    
    Expected JSON format (all fields optional):
    {
        "username": "newusername",
        "email": "newemail@example.com",
        "password": "newpassword",
        "points": 100,
        "level": 5
    }
    """
    try:
        # Check if user is logged in and updating their own profile.
        current_user_id = session.get('user_id')
        if not current_user_id or current_user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized'
            }), 403
        
        # Parse request payload.
        data = request.get_json(silent=True) or {}
        
        # Guard against empty payloads.
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Enforce whitelist of updateable fields.
        allowed_fields = {'username', 'email', 'password'}
        unknown_fields = set(data.keys()) - allowed_fields
        if unknown_fields:
            return jsonify({
                'success': False,
                'error': f'Unsupported fields: {", ".join(sorted(unknown_fields))}'
            }), 400

        # Validate payload with a form schema.
        form = UserUpdateForm(data=data, meta={'csrf': False})
        if not form.validate():
            return jsonify({
                'success': False,
                'error': 'Invalid input',
                'details': form.errors
            }), 400

        # Build an update payload from validated fields.
        update_payload = {}
        if form.username.data:
            update_payload['username'] = form.username.data.strip()
        if form.email.data:
            update_payload['email'] = form.email.data.strip()
        if form.password.data:
            update_payload['password'] = form.password.data

        # Reject requests that don't include valid updates.
        if not update_payload:
            return jsonify({
                'success': False,
                'error': 'No updatable fields provided'
            }), 400

        # Persist changes through the user data access layer.
        user = updateUser(user_id, **update_payload)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Return updated profile data.
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/points', methods=['POST'])
def add_user_points(user_id):
    """
    Add points to a user.
    
    Expected JSON format:
    {
        "points": 10
    }
    """
    try:
        # Parse points payload.
        data = request.get_json(silent=True) or {}
        
        # Validate required points field.
        if not data or 'points' not in data:
            return jsonify({
                'success': False,
                'error': 'Points value required'
            }), 400
        
        # Apply points increment.
        user = addUserPoints(user_id, int(data['points']))
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Return the updated user totals.
        return jsonify({
            'success': True,
            'message': 'Points added successfully',
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user_account(user_id):
    """Delete a user account"""
    try:
        # Check if user is logged in and deleting their own account.
        current_user_id = session.get('user_id')
        if not current_user_id or current_user_id != user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized'
            }), 403
        
        # Delete the user record.
        success = deleteUser(user_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Clear session after account deletion.
        session.clear()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/leaderboard', methods=['GET'])
def leaderboard():
    """Top 10 users by total points."""
    try:
        conn = get_db()
        cur = conn.cursor()
        # Query top users by total points with tie-breaking.
        cur.execute(
            """
            SELECT username, total_points, current_tier
            FROM users
            ORDER BY total_points DESC, username ASC
            LIMIT 10
            """
        )
        rows = []
        # Compute tier dynamically for each leaderboard entry.
        for row in cur.fetchall():
            item = dict(row)
            item["current_tier"] = _tier_for_points(item.get("total_points", 0))
            rows.append(item)
        return jsonify({
            'success': True,
            'leaders': rows
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/checkins', methods=['GET'])
def get_checkins(user_id):
    """Get check-in dates for a user."""
    try:
        conn = get_db()
        cur = conn.cursor()
        # Query check-in dates in reverse chronological order.
        cur.execute(
            "SELECT checkin_date FROM user_checkins WHERE user_id = ? ORDER BY checkin_date DESC",
            (user_id,),
        )
        dates = [row["checkin_date"] for row in cur.fetchall()]
        # Query current streak to display alongside the calendar.
        cur.execute("SELECT current_streak FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return jsonify({
            'success': True,
            'checkins': dates,
            'current_streak': row["current_streak"] if row else 0,
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_bp.route('/<int:user_id>/skills', methods=['GET'])
def get_user_skills(user_id):
    """Get skill tree with user progress."""
    try:
        conn = get_db()
        cur = conn.cursor()
        # Query skills and left-join user progress.
        cur.execute(
            """
            SELECT s.id, s.name, s.description, s.required_count, s.parent_id, s.category,
                   COALESCE(us.progress, 0) AS progress,
                   COALESCE(us.completed, 0) AS completed
            FROM skills s
            LEFT JOIN user_skills us
                ON us.skill_id = s.id AND us.user_id = ?
            ORDER BY s.category, s.id
            """,
            (user_id,),
        )
        skills = [dict(row) for row in cur.fetchall()]
        return jsonify({'success': True, 'skills': skills}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_bp.route('/<int:user_id>/skills/<int:skill_id>/progress', methods=['POST'])
def update_skill_progress(user_id, skill_id):
    """Increment a user's skill progress."""
    # Parse increment, defaulting to 1.
    data = request.get_json(silent=True) or {}
    increment = int(data.get('increment', 1))
    # Validate increment value for progress updates.
    if increment < 1:
        return jsonify({'success': False, 'error': 'Increment must be >= 1'}), 400

    conn = get_db()
    cur = conn.cursor()
    # Load skill definition to enforce requirements.
    cur.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
    skill = cur.fetchone()
    if not skill:
        return jsonify({'success': False, 'error': 'Skill not found'}), 404

    # Enforce parent completion before allowing child progression.
    if skill["parent_id"]:
        cur.execute(
            "SELECT completed FROM user_skills WHERE user_id = ? AND skill_id = ?",
            (user_id, skill["parent_id"]),
        )
        parent = cur.fetchone()
        if not parent or not parent["completed"]:
            return jsonify({'success': False, 'error': 'Parent skill not completed'}), 400

    # Ensure a user_skill row exists for progress tracking.
    cur.execute(
        "SELECT * FROM user_skills WHERE user_id = ? AND skill_id = ?",
        (user_id, skill_id),
    )
    user_skill = cur.fetchone()
    if not user_skill:
        cur.execute(
            "INSERT INTO user_skills (user_id, skill_id, progress, completed) VALUES (?, ?, 0, 0)",
            (user_id, skill_id),
        )
        cur.execute(
            "SELECT * FROM user_skills WHERE user_id = ? AND skill_id = ?",
            (user_id, skill_id),
        )
        user_skill = cur.fetchone()

    # Short-circuit if the skill is already completed.
    if user_skill["completed"]:
        return jsonify({'success': False, 'error': 'Skill already completed'}), 400

    # Compute new progress and completion status.
    new_progress = user_skill["progress"] + increment
    completed = 1 if new_progress >= skill["required_count"] else 0
    completed_at = datetime.utcnow().isoformat() if completed else None
    # Persist progress changes.
    cur.execute(
        """
        UPDATE user_skills
        SET progress = ?, completed = ?, completed_at = COALESCE(?, completed_at)
        WHERE id = ?
        """,
        (new_progress, completed, completed_at, user_skill["id"]),
    )
    points_awarded = 0
    combo_multiplier = 1.0
    milestone_bonus = 0
    # Award points and milestones when a skill is completed.
    if completed:
        today = datetime.utcnow().date()
        today_str = today.isoformat()
        # Count skills completed today to compute combo multipliers.
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM user_skills
            WHERE user_id = ?
              AND completed = 1
              AND completed_at LIKE ?
            """,
            (user_id, f"{today_str}%"),
        )
        completed_today = cur.fetchone()["count"]
        # Apply multiplier based on the number of completions today.
        if completed_today >= 4:
            combo_multiplier = 1.5
        elif completed_today == 3:
            combo_multiplier = 1.2
        elif completed_today == 2:
            combo_multiplier = 1.1

        base_points = skill["reward_points"] or 0
        points_awarded = int(round(base_points * combo_multiplier))

        # Update user points if any reward was earned.
        if points_awarded:
            cur.execute(
                """
                UPDATE users
                SET total_points = total_points + ?,
                    available_points = available_points + ?
                WHERE id = ?
                """,
                (points_awarded, points_awarded, user_id),
            )

        # Fetch completion counts to check milestone bonuses.
        cur.execute(
            "SELECT COUNT(*) AS count FROM user_skills WHERE user_id = ? AND completed = 1",
            (user_id,),
        )
        completed_count = cur.fetchone()["count"]
        cur.execute("SELECT COUNT(*) AS count FROM skills")
        total_skills = cur.fetchone()["count"]

        # Define milestone thresholds and bonuses.
        milestones = {
            5: 100,
            10: 200,
            15: 300,
            20: 500,
            total_skills: 1000,
        }
        # Grant milestone bonuses once per threshold.
        for threshold, bonus in milestones.items():
            if completed_count >= threshold:
                reward_key = f"skills_{threshold}"
                cur.execute(
                    """
                    SELECT id FROM user_skill_rewards
                    WHERE user_id = ? AND reward_type = 'milestone' AND reward_key = ?
                    """,
                    (user_id, reward_key),
                )
                if not cur.fetchone():
                    milestone_bonus += bonus
                    cur.execute(
                        """
                        INSERT INTO user_skill_rewards (user_id, reward_type, reward_key, awarded_at)
                        VALUES (?, 'milestone', ?, ?)
                        """,
                        (user_id, reward_key, datetime.utcnow().isoformat()),
                    )

        # Apply milestone bonus points in bulk.
        if milestone_bonus:
            cur.execute(
                """
                UPDATE users
                SET total_points = total_points + ?,
                    available_points = available_points + ?
                WHERE id = ?
                """,
                (milestone_bonus, milestone_bonus, user_id),
            )
    conn.commit()
    # Return updated progress and reward details.
    return jsonify({
        'success': True,
        'progress': new_progress,
        'completed': bool(completed),
        'required_count': skill["required_count"],
        'points_awarded': points_awarded,
        'combo_multiplier': combo_multiplier,
        'milestone_bonus': milestone_bonus,
    }), 200

