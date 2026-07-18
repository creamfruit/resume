import json
import time
from datetime import datetime
import os
import sqlite3
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.utils import secure_filename

reconnect_bp = Blueprint("reconnect", __name__, url_prefix="/reconnect")

WORKSPACE_DIR = Path(__file__).resolve().parents[3]
DB_NAME = str(WORKSPACE_DIR / "database" / "reconnect-sg_forum.db")
STATIC_DIR = (Path(__file__).resolve().parents[2] / "static" / "reconnect")
UPLOAD_FOLDER = STATIC_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

def render_reconnect(template_name: str, **context):
    if template_name.startswith("reconnect/"):
        return render_template(template_name, **context)
    return render_template(f"reconnect/{template_name}", **context)

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            points INTEGER DEFAULT 0)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT DEFAULT 'Anonymous',
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            created_at TEXT NOT NULL)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author TEXT DEFAULT 'Anonymous',
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id))""")

        conn.execute("""CREATE TABLE IF NOT EXISTS post_likes (
            user_id TEXT NOT NULL,
            post_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (post_id) REFERENCES posts(id))""")

        conn.execute("""CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL)""")

        conn.execute("""CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(challenge_id, author),
            FOREIGN KEY (challenge_id) REFERENCES challenges(id))""")

        users_to_load = [
            ('admin', '1234', 'admin'),
            ('user', 'pass', 'user'),
            ('sarah', 'sarah123', 'user')
        ]
        for username, password, role in users_to_load:
            conn.execute("INSERT OR IGNORE INTO users (username, password, role, points) VALUES (?, ?, ?, 0)",
                         (username, password, role))
            conn.execute("UPDATE users SET password = ?, role = ? WHERE username = ?",
                         (password, role, username))
        conn.commit()

def init_reconnect():
    init_db()

def _session_username():
    if session.get("user"):
        return session.get("user")
    name = session.get("name")
    user_id = session.get("user_id")
    if name:
        username = name
    elif user_id:
        username = f"user_{user_id}"
    else:
        return None
    session["user"] = username
    if session.get("is_admin"):
        session["role"] = "admin"
    return username

def _ensure_user(username: str):
    if not username:
        return
    conn = get_db()
    try:
        exists = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        if not exists:
            role = session.get("role") or "user"
            conn.execute(
                "INSERT INTO users (username, password, role, points) VALUES (?, ?, ?, 0)",
                (username, "ryan_login", role),
            )
            conn.commit()
    finally:
        conn.close()

@reconnect_bp.before_request
def _sync_session_user():
    if session.get("user_id"):
        username = _session_username()
        _ensure_user(username)

@reconnect_bp.route('/', methods=['GET', 'POST'])
@reconnect_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get("user_id"):
        return redirect(url_for('reconnect.dashboard'))
    return redirect("/login")

@reconnect_bp.route('/logout')
def logout():
    session.clear()
    return redirect("/logout")

# --- CONSOLIDATED DASHBOARD ---
@reconnect_bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')
        
    conn = get_db()
    
    # 1. Handle New Forum Post
    if request.method == 'POST' and 'title' in request.form:
        conn.execute("INSERT INTO posts (author, title, content, category, created_at) VALUES (?, ?, ?, ?, ?)",
                     (session['user'], 
                      request.form['title'], 
                      request.form['content'], 
                      request.form.get('category', 'Life Skills'), 
                      datetime.now().strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        conn.close()
        return redirect(url_for('reconnect.dashboard') + "#tab-wisdom-forum")

    # 2. Fetch User Points & Leaderboard
    user_data = conn.execute("SELECT points FROM users WHERE username = ?", (session['user'],)).fetchone()
    user_points = user_data['points'] if user_data else 0
    leaderboard = conn.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10").fetchall()

    # 3. FIXED FILTERING LOGIC
    selected_category = request.args.get('filter', 'all')
    
    if selected_category != 'all':
        # Filtered Query
        posts = conn.execute("""
            SELECT p.*, (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count 
            FROM posts p 
            WHERE p.category = ?
            ORDER BY p.id DESC
        """, (selected_category,)).fetchall()
    else:
        # Show All Query
        posts = conn.execute("""
            SELECT p.*, (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comment_count 
            FROM posts p 
            ORDER BY p.id DESC
        """).fetchall()

    # 4. Fetch Challenges and Submissions
    challenges = conn.execute("SELECT * FROM challenges ORDER BY id DESC").fetchall()
    
    all_subs = conn.execute("""
        SELECT s.*, COALESCE(c.title, 'Deleted Challenge') AS challenge_name 
        FROM submissions s 
        LEFT JOIN challenges c ON s.challenge_id = c.id 
        ORDER BY s.id DESC
    """).fetchall()
    
    user_subs = conn.execute("""
        SELECT s.*, COALESCE(c.title, 'Deleted Challenge') AS challenge_name 
        FROM submissions s 
        LEFT JOIN challenges c ON s.challenge_id = c.id 
        WHERE s.author = ? 
        ORDER BY s.id DESC
    """, (session['user'],)).fetchall()
    
    user_submitted_ids = [s['challenge_id'] for s in user_subs]

    conn.close()
    
    return render_reconnect('dashboard.html', 
                           posts=posts, 
                           challenges=challenges, 
                           all_submissions=all_subs, 
                           my_submissions=user_subs,
                           user_submissions=user_submitted_ids,
                           user_points=user_points,
                           leaderboard=leaderboard,
                           selected_category=selected_category, # Ensure this is passed!
                           is_admin=(session.get('role') == 'admin'))


@reconnect_bp.get('/messages')
def messages():
    if 'user' not in session:
        return redirect('/login')
    return render_reconnect('messages.html')


@reconnect_bp.get('/profile')
def profile():
    if 'user' not in session:
        return redirect('/login')
    return render_reconnect('profile.html')


@reconnect_bp.get('/explore')
def explore():
    if 'user' not in session:
        return redirect('/login')
    return render_reconnect('explore.html')


@reconnect_bp.get('/submission')
def submission():
    if 'user' not in session:
        return redirect('/login')
    return render_reconnect('submission.html')

# --- FORUM ACTIONS ---
@reconnect_bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    if 'user' not in session: return redirect('/login')
    conn = get_db()
    
    
    if request.method == 'POST' and 'comment' in request.form:
        conn.execute("INSERT INTO comments (post_id, author, content, created_at) VALUES (?, ?, ?, ?)",
                     (post_id, session['user'], request.form['comment'], datetime.now().strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        # Redirect back to the same page to show the comment
        conn.close()
        return redirect(url_for('reconnect.post_detail', post_id=post_id))
    
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    comments = conn.execute("SELECT * FROM comments WHERE post_id = ? ORDER BY id DESC", (post_id,)).fetchall()
    conn.close()
    return render_reconnect('post.html', post=post, comments=comments, is_admin=(session.get('role') == 'admin'))

@reconnect_bp.route('/delete_comment/<int:comment_id>/<int:post_id>', methods=['POST'])
def delete_comment(comment_id, post_id):
    if 'user' not in session: return redirect('/login')
    conn = get_db()
    comment = conn.execute('SELECT author FROM comments WHERE id = ?', (comment_id,)).fetchone()
    if comment and (session.get('role') == 'admin' or session.get('user') == comment['author']):
        conn.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('reconnect.post_detail', post_id=post_id))

# --- OTHER ROUTES 
@reconnect_bp.route('/create_challenge', methods=['POST'])
def create_challenge():
    if session.get('role') != 'admin':
        return redirect(url_for('reconnect.dashboard'))
    title = request.form.get('title')
    desc = request.form.get('description') 
    if not desc or not title:
        flash("Title and Description are required!")
        return redirect(url_for('reconnect.dashboard') + "#tab-challenges")
    conn = get_db()
    try:
        conn.execute("INSERT INTO challenges (title, description, created_at) VALUES (?, ?, ?)",
                     (title, desc, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('reconnect.dashboard') + "#tab-challenges")

@reconnect_bp.route('/submit_challenge/<int:challenge_id>', methods=['POST'])
def submit_challenge(challenge_id):
    if 'user' not in session: return redirect('/login')
    
    user_answer = request.form.get('answer', '').strip()
    word_count = len(user_answer.split())
    if word_count < 30:
        flash(f"Submission too short! You wrote {word_count} words, but 30 are required. ✍️")
        return redirect(url_for('reconnect.dashboard') + "#tab-challenges")
    file = request.files.get('file')
    image_path = None
    
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(UPLOAD_FOLDER / filename)
        image_path = filename
        
    conn = get_db()
    try:
        # 1. Record the challenge submission
        conn.execute("INSERT INTO submissions (challenge_id, author, content, image_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (challenge_id, session['user'], user_answer, image_path, datetime.now().strftime("%Y-%m-%d %H:%M")))
        
        # 2. Award 20 points to the user
        conn.execute("UPDATE users SET points = points + 20 WHERE username = ?", (session['user'],))
        
        conn.commit()
        flash("Challenge submitted! You earned +20 points! 🏆")
    except sqlite3.IntegrityError:
        flash("Already submitted.")
    except Exception as e:
        flash("An error occurred.")
        print(f"Error: {e}")
    finally:
        conn.close()
    return redirect(url_for('reconnect.dashboard') + "#tab-challenges")

# --- ADMIN ACTIONS: DELETE CHALLENGES & SUBMISSIONS ---

@reconnect_bp.route('/delete_challenge/<int:challenge_id>', methods=['POST'])
def delete_challenge(challenge_id):
    if session.get('role') != 'admin':
        return redirect(url_for('reconnect.dashboard'))
    
    conn = get_db()
    # First, delete all submissions associated with this challenge
    conn.execute("DELETE FROM submissions WHERE challenge_id = ?", (challenge_id,))
    # Then delete the challenge itself
    conn.execute("DELETE FROM challenges WHERE id = ?", (challenge_id,))
    conn.commit()
    conn.close()
    flash("Challenge and all associated submissions deleted.")
    return redirect(url_for('reconnect.dashboard') + "#tab-challenges")

@reconnect_bp.route('/delete_submission/<int:submission_id>', methods=['POST'])
def delete_submission(submission_id):
    if 'user' not in session: 
        return redirect('/login')
    
    conn = get_db()
    try:
        # 1. Fetch the submission
        sub = conn.execute("SELECT author, image_path FROM submissions WHERE id = ?", (submission_id,)).fetchone()
        
        if not sub:
            return redirect(url_for('reconnect.dashboard') + "#tab-challenges")

        # 2. PERMISSION CHECK: Admin OR the person who is logged in
        current_user = session.get('user')
        is_admin = session.get('role') == 'admin'
        
        if is_admin or current_user == sub['author']:
            # Delete physical image file
            if sub['image_path']:
                file_path = os.path.join(app.root_path, 'static', 'uploads', sub['image_path'])
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Delete from Database
            conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))

           
            # We deduct from the sub['author'] to ensure the correct person loses points
            conn.execute("UPDATE users SET points = MAX(0, points - 20) WHERE username = ?", (sub['author'],))
            
            conn.commit()
            flash("Successfully deleted! 20 points deducted.")
        else:
            flash("You can only delete your own posts.")
            
    except Exception as e:
        print(f"Delete Error: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('reconnect.dashboard') + "#tab-challenges")

@reconnect_bp.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    conn = get_db()
    post = conn.execute('SELECT author FROM posts WHERE id = ?', (post_id,)).fetchone()
    if post and (session.get('role') == 'admin' or session.get('user') == post['author']):
        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('reconnect.dashboard') + "#tab-wisdom-forum")

@reconnect_bp.route('/edit/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    conn = get_db()
    post = conn.execute('SELECT author FROM posts WHERE id = ?', (post_id,)).fetchone()
    if post and session['user'] == post['author']:
        conn.execute('UPDATE posts SET content = ? WHERE id = ?', (request.form.get('content'), post_id))
        conn.commit()
    conn.close()
    return redirect(url_for('reconnect.dashboard') + "#tab-wisdom-forum")

@reconnect_bp.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    user_id, conn = session['user'], get_db()
    already_liked = conn.execute("SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?", (user_id, post_id)).fetchone()
    if not already_liked:
        conn.execute("INSERT INTO post_likes (user_id, post_id) VALUES (?, ?)", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    else:
        conn.execute("DELETE FROM post_likes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
        conn.execute("UPDATE posts SET likes = likes - 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('reconnect.dashboard') + "#tab-wisdom-forum")
