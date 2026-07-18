# Import OS utilities, SQLite driver, and timestamps for seeding.
import os
import sqlite3
from datetime import datetime

# Import password hashing for seeded demo accounts.
from werkzeug.security import generate_password_hash

# Define project root and database path for the SQLite file.
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'database', 'app.db'))


# Create a SQLite connection with row access by column name.
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints to maintain relational integrity.
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# Return a request-scoped DB connection or a fallback standalone connection.
def get_db():
    try:
        from flask import g
    except Exception:
        # NOTE: could be refactored for scalability
        return _connect()

    if "db_conn" not in g:
        # Ensure database file and schema exist before serving requests.
        if not os.path.exists(DB_PATH):
            init_db()
        print(">>> SQLite DB connected")
        g.db_conn = _connect()
        try:
            # Validate core tables to detect missing schema.
            if not _table_exists(g.db_conn, "users"):
                g.db_conn.close()
                init_db()
                g.db_conn = _connect()
        except sqlite3.OperationalError:
            # Reinitialize if the schema is unreadable or corrupt.
            g.db_conn.close()
            init_db()
            g.db_conn = _connect()
    return g.db_conn


# Close the request-scoped DB connection if present.
def close_db(error=None):
    try:
        from flask import g
    except Exception:
        return

    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


# Initialize the database schema and seed baseline data.
def init_db():
    # Ensure the instance directory exists before creating the DB file.
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _connect()
    # Run migrations before creating or updating the schema.
    _migrate_db(conn)
    # Create tables and core schema if missing.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            total_points INTEGER NOT NULL DEFAULT 0,
            available_points INTEGER NOT NULL DEFAULT 0,
            current_tier INTEGER NOT NULL DEFAULT 1,
            active_days INTEGER NOT NULL DEFAULT 1,
            points INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            is_admin INTEGER NOT NULL DEFAULT 0,
            last_login_date TEXT,
            current_streak INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reward INTEGER NOT NULL,
            total_required INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quest_id INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            UNIQUE(user_id, quest_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            threshold INTEGER NOT NULL,
            requirement_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            badge_id INTEGER NOT NULL,
            earned INTEGER NOT NULL DEFAULT 0,
            earned_at TEXT,
            UNIQUE(user_id, badge_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (badge_id) REFERENCES badges(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            cost INTEGER NOT NULL,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_id INTEGER NOT NULL,
            redeemed_at TEXT NOT NULL,
            UNIQUE(user_id, reward_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reward_id) REFERENCES rewards(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS landmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT NOT NULL,
            story TEXT NOT NULL,
            question TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            x_coord INTEGER NOT NULL,
            y_coord INTEGER NOT NULL,
            points_value INTEGER NOT NULL DEFAULT 100
        );

        CREATE TABLE IF NOT EXISTS landmark_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            landmark_id INTEGER NOT NULL,
            option_text TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            FOREIGN KEY (landmark_id) REFERENCES landmarks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_landmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            landmark_id INTEGER NOT NULL,
            unlocked INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            unlocked_at TEXT,
            completed_at TEXT,
            UNIQUE(user_id, landmark_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (landmark_id) REFERENCES landmarks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, checkin_date),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS checkin_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_type TEXT NOT NULL,
            period_start TEXT NOT NULL,
            awarded_at TEXT NOT NULL,
            UNIQUE(user_id, reward_type, period_start),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            required_count INTEGER NOT NULL DEFAULT 1,
            parent_id INTEGER,
            category TEXT NOT NULL DEFAULT 'General',
            level INTEGER NOT NULL DEFAULT 1,
            icon TEXT,
            reward_points INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (parent_id) REFERENCES skills(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS user_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            UNIQUE(user_id, skill_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_skill_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_type TEXT NOT NULL,
            reward_key TEXT NOT NULL,
            awarded_at TEXT NOT NULL,
            UNIQUE(user_id, reward_type, reward_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    # Seed demo data to support initial app usage and testing.
    _seed_db(conn)
    conn.close()


# Check whether a column exists to support simple migrations.
def _column_exists(conn, table_name, column_name):
    cur = conn.cursor()
    # Query sqlite schema metadata for column definitions.
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cur.fetchall())


# Add a column only if it does not already exist.
def _ensure_column(conn, table_name, column_name, column_def):
    if not _column_exists(conn, table_name, column_name):
        # Apply ALTER TABLE to evolve the schema in place.
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


# Apply incremental schema updates to older databases.
def _migrate_db(conn):
    # Expand user table columns as features are introduced.
    if _table_exists(conn, "users"):
        _ensure_column(conn, "users", "email", "TEXT")
        _ensure_column(conn, "users", "password_hash", "TEXT")
        _ensure_column(conn, "users", "total_points", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "available_points", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "current_tier", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "users", "active_days", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "users", "points", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "level", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "users", "is_admin", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "last_login_date", "TEXT")
        _ensure_column(conn, "users", "current_streak", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "users", "created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
        # Backfill available_points for legacy users without redemptions.
        conn.execute(
            """
            UPDATE users
            SET available_points = total_points
            WHERE available_points = 0
              AND total_points > 0
              AND id NOT IN (SELECT DISTINCT user_id FROM user_rewards)
            """
        )

    # Add completion timestamps for quest progress tracking.
    if _table_exists(conn, "user_quests"):
        _ensure_column(conn, "user_quests", "completed_at", "TEXT")

    # Add earned timestamps for badges.
    if _table_exists(conn, "user_badges"):
        _ensure_column(conn, "user_badges", "earned_at", "TEXT")

    # Add point values to landmarks for scoring.
    if _table_exists(conn, "landmarks"):
        _ensure_column(conn, "landmarks", "points_value", "INTEGER NOT NULL DEFAULT 100")

    # Add unlock and completion timestamps to user landmarks.
    if _table_exists(conn, "user_landmarks"):
        _ensure_column(conn, "user_landmarks", "unlocked_at", "TEXT")
        _ensure_column(conn, "user_landmarks", "completed_at", "TEXT")

    # Add active flag to rewards for archiving.
    if _table_exists(conn, "rewards"):
        _ensure_column(conn, "rewards", "is_active", "INTEGER NOT NULL DEFAULT 1")

    # Add skill metadata fields for the skill-tree feature.
    if _table_exists(conn, "skills"):
        _ensure_column(conn, "skills", "level", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(conn, "skills", "icon", "TEXT")
        _ensure_column(conn, "skills", "reward_points", "INTEGER NOT NULL DEFAULT 0")


# Check for the existence of a table in the SQLite schema.
def _table_exists(conn, table_name):
    cur = conn.cursor()
    # Query sqlite_master for the specified table.
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


# Seed the database with demo users and reference data.
def _seed_db(conn):
    cur = conn.cursor()

    # Hash a shared password for demo accounts.
    password_hash = generate_password_hash("password123")
    today = datetime.utcnow().date().isoformat()
    users = [
        ("admin", "admin@example.com", 0, 1),
        ("administrator", "administrator@example.com", 0, 1),
        ("demo", "demo@example.com", 2500, 0),
        ("jess", "jess@example.com", 1200, 0),
        ("kai", "kai@example.com", 800, 0),
    ]
    # Insert baseline users if they do not already exist.
    cur.executemany(
        """
        INSERT OR IGNORE INTO users (
            username, email, password_hash,
            total_points, available_points, current_tier, active_days,
            points, level, is_admin, last_login_date, current_streak, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                username,
                email,
                password_hash,
                points,
                points,
                1,
                1,
                0,
                1,
                is_admin,
                today,
                1,
                datetime.utcnow().isoformat(),
            )
            for username, email, points, is_admin in users
        ],
    )
    # Sync point totals and admin flags for seeded users.
    for username, email, points, is_admin in users:
        cur.execute(
            """
            UPDATE users
            SET total_points = CASE WHEN total_points < ? THEN ? ELSE total_points END,
                available_points = CASE WHEN available_points < ? THEN ? ELSE available_points END
            WHERE username = ?
            """,
            (points, points, points, points, username),
        )
        cur.execute(
            "UPDATE users SET is_admin = ? WHERE username = ?",
            (is_admin, username),
        )

    # Insert starter quest definitions.
    quests = [
        (1, "Join Your First Learning Circle", "Connect with others to learn or share a skill together", 1500, 1),
        (2, "Reply in the Community Forum", "Share your thoughts or help answer someone's question", 75, 1),
        (3, "Share a Skill", "Teach something you know - cooking, language, crafts, anything!", 200, 1),
        (4, "Thank a Connection", "Send appreciation to someone who helped you", 50, 1),
        (5, "Complete 3 Learning Sessions", "Keep learning and growing with the community", 300, 3),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO quests (id, title, description, reward, total_required) VALUES (?, ?, ?, ?, ?)",
        quests,
    )

    # Insert badge definitions for achievement tracking.
    badges = [
        (1, "First Steps", "badge", "Unlock your first landmark", "Journey", 1, "landmarks"),
        (2, "City Explorer", "badge", "Complete 3 landmarks", "Journey", 3, "landmarks"),
        (3, "Island Voyager", "badge", "Complete all 10 landmarks", "Journey", 10, "landmarks"),
        (4, "Community Builder", "badge", "Complete 5 quests", "Community", 5, "quests"),
        (5, "Helpful Guide", "badge", "Complete 10 quests", "Community", 10, "quests"),
        (6, "Master Connector", "badge", "Complete 20 quests", "Community", 20, "quests"),
        (7, "Point Collector", "coin", "Earn 1,000 points", "Progress", 1000, "points"),
        (8, "Point Master", "trophy", "Earn 5,000 points", "Progress", 5000, "points"),
        (9, "Tier Ascender", "rocket", "Reach Tier 3", "Progress", 3, "tier"),
        (10, "Skill Starter", "badge", "Complete 5 skills", "Skills", 5, "skills"),
        (11, "Skill Builder", "badge", "Complete 10 skills", "Skills", 10, "skills"),
        (12, "Skill Master", "badge", "Complete 15 skills", "Skills", 15, "skills"),
        (13, "Skill Elite", "badge", "Complete 20 skills", "Skills", 20, "skills"),
        (14, "Digital Grandmaster", "badge", "Complete all skills", "Skills", 999, "skills"),
    ]
    cur.executemany(
        """
        INSERT OR IGNORE INTO badges (id, name, icon, description, category, threshold, requirement_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        badges,
    )

    # Insert reward catalog entries.
    rewards = [
        (1, "$2 GrabFood Voucher", "gift", 500, None),
        (2, "$3 Starbucks Voucher", "cup", 750, None),
        (3, "$5 Popular Bookstore", "book", 1250, None),
        (4, "$5 Kopitiam Voucher", "bread", 1250, None),
        (5, "$10 NTUC Voucher", "cart", 2500, None),
        (6, "$10 Watsons Voucher", "bag", 2500, None),
        (7, "$15 Movie Voucher", "ticket", 3750, None),
        (8, "$15 Uniqlo Voucher", "shirt", 3750, None),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO rewards (id, name, icon, cost, description, is_active) VALUES (?, ?, ?, ?, ?, 1)",
        rewards,
    )

    # Insert skill tree definitions for progression tracking.
    skills = [
        (1, "WhatsApp Basics", "Teach basic messaging and contacts.", 10, None, "Communication", 1, "whatsapp", 50),
        (2, "Emojis & Stickers", "Help seniors use emojis and stickers.", 5, 1, "Communication", 1, "emoji", 30),
        (3, "Voice Messages", "Guide seniors to send voice notes.", 5, 1, "Communication", 2, "voice", 40),
        (4, "Video Calls", "Help seniors make a video call.", 3, 3, "Communication", 3, "video", 60),
        (5, "Group Chats", "Create and manage group chats.", 3, 2, "Communication", 3, "group", 60),
        (6, "Email Basics", "Read and reply to emails.", 8, None, "Communication", 1, "email", 40),
        (7, "Email Attachments", "Send and download attachments.", 4, 6, "Communication", 2, "attachment", 50),
        (8, "Banking Login", "Log in securely to banking apps.", 6, None, "Financial", 1, "bank", 50),
        (9, "Check Balance", "Check account balances.", 4, 8, "Financial", 2, "balance", 40),
        (10, "Transfer Money", "Make a transfer safely.", 5, 9, "Financial", 2, "transfer", 60),
        (11, "Bill Payment", "Pay utility bills online.", 4, 10, "Financial", 3, "bill", 70),
        (12, "Scam Awareness", "Identify common scam patterns.", 5, None, "Safety", 1, "scam", 40),
        (13, "Password Security", "Set strong passwords and manage them.", 3, 12, "Safety", 2, "password", 50),
        (14, "Privacy Settings", "Update privacy and sharing controls.", 4, 13, "Safety", 3, "privacy", 60),
    ]
    cur.executemany(
        """
        INSERT OR IGNORE INTO skills
        (id, name, description, required_count, parent_id, category, level, icon, reward_points)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        skills,
    )

    # Insert initial landmark data for the journey map.
    landmarks = [
        (1, "Jurong", "pin", "Singapore's industrial heartland that transformed into a hub for innovation, featuring Jurong Bird Park and the upcoming Jurong Lake District.", "What is Jurong best known for today?", 1, 220, 310, 100),
        (2, "Chinatown", "pin", "A vibrant district preserving Chinese heritage and culture, where traditional shophouses blend with modern businesses, creating a unique fusion of old and new Singapore.", "What makes Chinatown special?", 1, 410, 350, 100),
        (3, "Marina Bay", "pin", "This iconic waterfront area features Marina Bay Sands with three towers connected by a sky park 200 meters above ground, offering stunning views of Singapore's skyline.", "How many towers does Marina Bay Sands have?", 1, 490, 340, 100),
        (4, "Orchard Road", "pin", "Singapore's premier shopping district with over 20 shopping malls. It was once lined with fruit orchards and nutmeg plantations in the 1800s.", "What was Orchard Road before becoming a shopping district?", 1, 380, 290, 100),
        (5, "Kampong Glam", "pin", "The historic Malay-Muslim quarter centered around the golden-domed Sultan Mosque, showcasing rich Islamic heritage and modern creative culture.", "What is the famous mosque in Kampong Glam?", 1, 520, 285, 100),
        (6, "Little India", "pin", "An ethnic district that celebrates Indian culture, featuring colorful streets, aromatic spices, and vibrant festivals like Deepavali that bring the community together.", "Which festival is famously celebrated in Little India?", 1, 460, 270, 100),
        (7, "Botanic Gardens", "pin", "A UNESCO World Heritage Site founded in 1859, featuring 82 hectares of lush greenery and home to the National Orchid Garden.", "When was the Singapore Botanic Gardens founded?", 1, 310, 250, 100),
        (8, "Marina Bay Sands", "pin", "Marina Bay Sands features three towers connected by a sky park 200 meters above ground.", "How many towers does Marina Bay Sands have?", 1, 550, 325, 100),
        (9, "Changi", "pin", "Home to Changi Airport, consistently rated the world's best airport, and Changi Village with its rich coastal heritage.", "What is Changi best known for?", 1, 620, 285, 100),
        (10, "Sentosa", "pin", "Singapore's island resort destination offering beaches, attractions, and entertainment. The name Sentosa means 'peace and tranquility' in Malay.", "What does 'Sentosa' mean in Malay?", 0, 370, 470, 100),
    ]
    cur.executemany(
        """
        INSERT OR IGNORE INTO landmarks
        (id, name, icon, story, question, correct_answer, x_coord, y_coord, points_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        landmarks,
    )

    # Insert multiple-choice options for landmark quizzes.
    options = [
        (1, 1, "Shopping malls", 0),
        (2, 1, "Innovation hub", 1),
        (3, 1, "Beach resorts", 2),
        (4, 1, "Historic temples", 3),
        (5, 2, "Modern skyscrapers", 0),
        (6, 2, "Blend of heritage and modern life", 1),
        (7, 2, "Beach activities", 2),
        (8, 2, "Industrial sites", 3),
        (9, 3, "2", 0),
        (10, 3, "3", 1),
        (11, 3, "4", 2),
        (12, 3, "5", 3),
        (13, 4, "Industrial area", 0),
        (14, 4, "Fruit orchards", 1),
        (15, 4, "Residential zone", 2),
        (16, 4, "Fishing village", 3),
        (17, 5, "Blue Mosque", 0),
        (18, 5, "Sultan Mosque", 1),
        (19, 5, "Crystal Mosque", 2),
        (20, 5, "Grand Mosque", 3),
        (21, 6, "Christmas", 0),
        (22, 6, "Deepavali", 1),
        (23, 6, "Chinese New Year", 2),
        (24, 6, "Hari Raya", 3),
        (25, 7, "1819", 0),
        (26, 7, "1859", 1),
        (27, 7, "1900", 2),
        (28, 7, "1965", 3),
        (29, 8, "2", 0),
        (30, 8, "3", 1),
        (31, 8, "4", 2),
        (32, 8, "5", 3),
        (33, 9, "Shopping malls", 0),
        (34, 9, "World-class airport", 1),
        (35, 9, "Historical museums", 2),
        (36, 9, "Nature parks", 3),
        (37, 10, "Peace and tranquility", 0),
        (38, 10, "Beautiful island", 1),
        (39, 10, "Paradise beach", 2),
        (40, 10, "Golden sands", 3),
    ]
    cur.executemany(
        """
        INSERT OR IGNORE INTO landmark_options (id, landmark_id, option_text, option_index)
        VALUES (?, ?, ?, ?)
        """,
        options,
    )

    # Seed user quest progress records if missing.
    cur.execute("SELECT COUNT(*) AS count FROM user_quests")
    if cur.fetchone()["count"] == 0:
        # Build a full matrix of users and quests.
        cur.execute("SELECT id FROM users")
        user_ids = [row["id"] for row in cur.fetchall()]
        cur.execute("SELECT id FROM quests")
        quest_ids = [row["id"] for row in cur.fetchall()]
        cur.executemany(
            "INSERT INTO user_quests (user_id, quest_id, progress, completed) VALUES (?, ?, 0, 0)",
            [(uid, qid) for uid in user_ids for qid in quest_ids],
        )

    # Seed user badge records if missing.
    cur.execute("SELECT COUNT(*) AS count FROM user_badges")
    if cur.fetchone()["count"] == 0:
        # Build a full matrix of users and badges.
        cur.execute("SELECT id FROM users")
        user_ids = [row["id"] for row in cur.fetchall()]
        cur.execute("SELECT id FROM badges")
        badge_ids = [row["id"] for row in cur.fetchall()]
        cur.executemany(
            "INSERT INTO user_badges (user_id, badge_id, earned) VALUES (?, ?, 0)",
            [(uid, bid) for uid in user_ids for bid in badge_ids],
        )

    # Seed user landmark records if missing.
    cur.execute("SELECT COUNT(*) AS count FROM user_landmarks")
    if cur.fetchone()["count"] == 0:
        # Build a full matrix of users and landmarks.
        cur.execute("SELECT id FROM users")
        user_ids = [row["id"] for row in cur.fetchall()]
        cur.execute("SELECT id FROM landmarks")
        landmark_ids = [row["id"] for row in cur.fetchall()]
        cur.executemany(
            "INSERT INTO user_landmarks (user_id, landmark_id, unlocked, completed) VALUES (?, ?, 0, 0)",
            [(uid, lid) for uid in user_ids for lid in landmark_ids],
        )

    # Ensure quest progress exists for all users and quests.
    cur.execute("SELECT id FROM users")
    user_ids = [row["id"] for row in cur.fetchall()]
    cur.execute("SELECT id FROM quests")
    quest_ids = [row["id"] for row in cur.fetchall()]
    cur.executemany(
        "INSERT OR IGNORE INTO user_quests (user_id, quest_id, progress, completed) VALUES (?, ?, 0, 0)",
        [(uid, qid) for uid in user_ids for qid in quest_ids],
    )

    # Ensure badge rows exist for all users.
    cur.execute("SELECT id FROM badges")
    badge_ids = [row["id"] for row in cur.fetchall()]
    cur.executemany(
        "INSERT OR IGNORE INTO user_badges (user_id, badge_id, earned) VALUES (?, ?, 0)",
        [(uid, bid) for uid in user_ids for bid in badge_ids],
    )

    # Ensure landmark progress exists for all users.
    cur.execute("SELECT id FROM landmarks")
    landmark_ids = [row["id"] for row in cur.fetchall()]
    cur.executemany(
        "INSERT OR IGNORE INTO user_landmarks (user_id, landmark_id, unlocked, completed) VALUES (?, ?, 0, 0)",
        [(uid, lid) for uid in user_ids for lid in landmark_ids],
    )

    # Ensure skill progress exists for all users.
    cur.execute("SELECT id FROM skills")
    skill_ids = [row["id"] for row in cur.fetchall()]
    cur.executemany(
        "INSERT OR IGNORE INTO user_skills (user_id, skill_id, progress, completed) VALUES (?, ?, 0, 0)",
        [(uid, sid) for uid in user_ids for sid in skill_ids],
    )

    # Commit all seed operations as a single transaction.
    conn.commit()
