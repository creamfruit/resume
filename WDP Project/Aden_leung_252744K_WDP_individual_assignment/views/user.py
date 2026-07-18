# Import datetime for user creation timestamps.
from datetime import datetime

# Import password hashing utilities for secure credential handling.
from werkzeug.security import generate_password_hash, check_password_hash


# Create a new user and initialize core account fields.
def createUser(username, email, password):
    # Import locally to avoid circular dependencies during app boot.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Check for existing username or email collisions.
    cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
    if cursor.fetchone():
        conn.close()
        return None

    # Hash the password before persisting credentials.
    password_hash = generate_password_hash(password)

    # Insert a new user row with default progression values.
    cursor.execute(
        '''
        INSERT INTO users (
            username, email, password_hash,
            total_points, available_points, current_tier, active_days,
            points, level, is_admin, last_login_date, current_streak, created_at
        )
        VALUES (?, ?, ?, 0, 0, 1, 1, 0, 1, 0, NULL, 0, ?)
        ''',
        (username, email, password_hash, datetime.utcnow().isoformat()),
    )

    conn.commit()
    user_id = cursor.lastrowid

    # Fetch and return the created user as a model instance.
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    return User.from_db_row(row)


# Retrieve a user by primary key id.
def getUserById(user_id):
    # Import locally to keep model dependencies isolated.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Query database for a single user row.
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    return User.from_db_row(row) if row else None


# Retrieve a user by username.
def getUserByUsername(username):
    # Import locally to avoid global coupling.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Query database for the username match.
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()

    return User.from_db_row(row) if row else None


# Retrieve a user by email address.
def getUserByEmail(email):
    # Import locally to avoid import-time side effects.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Query database for the email match.
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()

    return User.from_db_row(row) if row else None


# Fetch all users ordered by creation date for admin views.
def getAllUsers():
    # Import locally to keep modules decoupled.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Query database for all users in reverse chronological order.
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()

    return [User.from_db_row(row) for row in rows]


# Update user fields based on provided keyword arguments.
def updateUser(user_id, **kwargs):
    # Import locally to avoid circular dependencies.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Guard against updates to non-existent users.
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    if not cursor.fetchone():
        conn.close()
        return None

    updates = []
    params = []

    # Build dynamic update clauses for provided fields.
    if 'username' in kwargs:
        updates.append('username = ?')
        params.append(kwargs['username'])

    if 'email' in kwargs:
        updates.append('email = ?')
        params.append(kwargs['email'])

    if 'password' in kwargs:
        # Hash password updates before saving.
        password_hash = generate_password_hash(kwargs['password'])
        updates.append('password_hash = ?')
        params.append(password_hash)

    if 'points' in kwargs:
        updates.append('points = ?')
        params.append(kwargs['points'])

    if 'level' in kwargs:
        updates.append('level = ?')
        params.append(kwargs['level'])

    if updates:
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        # Execute the parameterized update to persist changes.
        cursor.execute(query, params)
        conn.commit()

    # Return the updated user record.
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    return User.from_db_row(row) if row else None


# Delete a user row by id.
def deleteUser(user_id):
    # Import locally to avoid module coupling.
    from .models import get_db

    conn = get_db()
    cursor = conn.cursor()

    # Ensure the user exists before deletion.
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    # Delete the user record.
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return True


# Verify a plaintext password against a stored hash.
def verifyPassword(user, password):
    return check_password_hash(user.get_password_hash(), password)


# Authenticate a user by username/email and password.
def authenticateUser(username, password):
    # Import locally to avoid circular imports.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Query database for username or email match.
    cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username))
    row = cursor.fetchone()
    conn.close()

    # Abort if no user record exists.
    if not row:
        return None

    user = User.from_db_row(row)

    # Validate password hash before returning user.
    if not verifyPassword(user, password):
        return None

    return user


# Increment points across multiple user point counters.
def addUserPoints(user_id, points):
    # Import locally to keep modules decoupled.
    from .models import get_db, User

    conn = get_db()
    cursor = conn.cursor()

    # Update points atomically across totals and available balances.
    cursor.execute(
        '''
        UPDATE users
        SET points = points + ?,
            total_points = total_points + ?,
            available_points = available_points + ?
        WHERE id = ?
        ''',
        (points, points, points, user_id)
    )
    conn.commit()

    # Return the updated user state after increment.
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    return User.from_db_row(row) if row else None
