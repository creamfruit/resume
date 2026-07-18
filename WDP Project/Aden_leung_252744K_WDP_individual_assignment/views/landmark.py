# Import datetime for any timestamp-related logic in landmark workflows.
from datetime import datetime

# Import DB connector and Landmark model for persistence operations.
from views.db import get_db
from views.models import Landmark


# Validate landmark payloads before insert/update operations.
def _validate_landmark_payload(data):
    name = data.get("name", "").strip()
    story = data.get("story", "").strip()
    question = data.get("question", "").strip()
    x_coord = data.get("x_coord")
    y_coord = data.get("y_coord")
    correct_answer = data.get("correct_answer")
    options = data.get("options") or []

    # Enforce required text length constraints for content quality.
    if not (3 <= len(name) <= 100):
        raise ValueError("Name must be between 3 and 100 characters")
    if not (20 <= len(story) <= 1000):
        raise ValueError("Story must be between 20 and 1000 characters")
    if not (10 <= len(question) <= 200):
        raise ValueError("Question must be between 10 and 200 characters")

    try:
        answer_val = int(correct_answer)
    except (TypeError, ValueError):
        raise ValueError("Correct answer must be an integer")

    # Validate coordinate types to avoid invalid geometry.
    try:
        x_val = int(x_coord)
        y_val = int(y_coord)
    except (TypeError, ValueError):
        raise ValueError("Coordinates must be integers")

    # Ensure coordinates fit within the SVG map bounds.
    if not (0 <= x_val <= 800):
        raise ValueError("X coordinate must be between 0 and 800")
    if not (0 <= y_val <= 550):
        raise ValueError("Y coordinate must be between 0 and 550")

    if options and not (0 <= answer_val < len(options)):
        raise ValueError("Correct answer must be a valid option index")


# Fetch all landmarks with their option sets for client rendering.
def getAllLandmarksDB():
    conn = get_db()
    cur = conn.cursor()
    # Query database for base landmark metadata.
    cur.execute(
        """
        SELECT id, name, icon, story, question, correct_answer, x_coord, y_coord, points_value
        FROM landmarks
        ORDER BY id
        """
    )
    rows = cur.fetchall()
    # Load option lists and merge them into Landmark objects.
    options_map = _get_landmark_options(conn)
    return [
        Landmark(
            id=row["id"],
            name=row["name"],
            icon=row["icon"],
            story=row["story"],
            question=row["question"],
            correct_answer=row["correct_answer"],
            x_coord=row["x_coord"],
            y_coord=row["y_coord"],
            points_value=row["points_value"],
            options=options_map.get(row["id"], []),
        )
        for row in rows
    ]


# Fetch a single landmark with options for detail views.
def getLandmarkDB(landmark_id):
    conn = get_db()
    cur = conn.cursor()
    # Query database for the requested landmark.
    cur.execute(
        """
        SELECT id, name, icon, story, question, correct_answer, x_coord, y_coord, points_value
        FROM landmarks
        WHERE id = ?
        """,
        (landmark_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    # Retrieve option list scoped to the landmark.
    options = _get_landmark_options(conn, landmark_id=landmark_id).get(landmark_id, [])
    return Landmark(
        id=row["id"],
        name=row["name"],
        icon=row["icon"],
        story=row["story"],
        question=row["question"],
        correct_answer=row["correct_answer"],
        x_coord=row["x_coord"],
        y_coord=row["y_coord"],
        points_value=row["points_value"],
        options=options,
    )


# Create a landmark and any associated options in the database.
def createLandmarkDB(landmark_obj):
    data = landmark_obj.to_dict() if hasattr(landmark_obj, "to_dict") else dict(landmark_obj)
    # Validate incoming payload to prevent bad records.
    _validate_landmark_payload(data)

    conn = get_db()
    cur = conn.cursor()
    # Insert the landmark core attributes.
    cur.execute(
        """
        INSERT INTO landmarks (name, icon, story, question, correct_answer, x_coord, y_coord, points_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"],
            data["icon"],
            data["story"],
            data["question"],
            data["correct_answer"],
            int(data["x_coord"]),
            int(data["y_coord"]),
            int(data.get("points_value", 100)),
        ),
    )
    options = data.get("options") or []
    # Insert multiple-choice options if provided.
    if options:
        cur.executemany(
            """
            INSERT INTO landmark_options (landmark_id, option_text, option_index)
            VALUES (?, ?, ?)
            """,
            [(cur.lastrowid, str(text), idx) for idx, text in enumerate(options)],
        )
    conn.commit()
    return getLandmarkDB(cur.lastrowid)


# Update an existing landmark after validation checks.
def updateLandmarkDB(landmark_id, landmark_obj):
    data = landmark_obj.to_dict() if hasattr(landmark_obj, "to_dict") else dict(landmark_obj)
    # Validate payload before applying changes.
    _validate_landmark_payload(data)

    conn = get_db()
    cur = conn.cursor()
    # Guard against updates to missing records.
    cur.execute("SELECT id FROM landmarks WHERE id = ?", (landmark_id,))
    if not cur.fetchone():
        return None

    # Persist updated landmark fields.
    cur.execute(
        """
        UPDATE landmarks
        SET name = ?, icon = ?, story = ?, question = ?, correct_answer = ?,
            x_coord = ?, y_coord = ?, points_value = ?
        WHERE id = ?
        """,
        (
            data["name"],
            data["icon"],
            data["story"],
            data["question"],
            data["correct_answer"],
            int(data["x_coord"]),
            int(data["y_coord"]),
            int(data.get("points_value", 100)),
            landmark_id,
        ),
    )
    conn.commit()
    return getLandmarkDB(landmark_id)


# Remove a landmark and its options from the database.
def deleteLandmarkDB(landmark_id):
    conn = get_db()
    cur = conn.cursor()
    # Ensure the landmark exists before deletion.
    cur.execute("SELECT id FROM landmarks WHERE id = ?", (landmark_id,))
    if not cur.fetchone():
        return False
    # Cascade delete dependent options then the landmark record.
    cur.execute("DELETE FROM landmark_options WHERE landmark_id = ?", (landmark_id,))
    cur.execute("DELETE FROM landmarks WHERE id = ?", (landmark_id,))
    conn.commit()
    return True


# Return a user's landmark progress with unlock/completion flags.
def get_user_landmarks_db(user_id):
    conn = get_db()
    cur = conn.cursor()
    # Query join between landmarks and user progression rows.
    cur.execute(
        """
        SELECT l.*, COALESCE(ul.unlocked, 0) AS unlocked,
               COALESCE(ul.completed, 0) AS completed,
               ul.unlocked_at, ul.completed_at
        FROM landmarks l
        LEFT JOIN user_landmarks ul
            ON ul.landmark_id = l.id AND ul.user_id = ?
        ORDER BY l.id
        """,
        (user_id,),
    )
    return [dict(row) for row in cur.fetchall()]


# Fetch landmark quiz options, optionally scoped to a single landmark.
def _get_landmark_options(conn, landmark_id=None):
    cur = conn.cursor()
    # Choose query based on whether a specific landmark is requested.
    if landmark_id is None:
        # Query all options for bulk landmark list assembly.
        cur.execute(
            """
            SELECT landmark_id, option_text, option_index
            FROM landmark_options
            ORDER BY landmark_id, option_index
            """
        )
    else:
        # Query options for a single landmark detail.
        cur.execute(
            """
            SELECT landmark_id, option_text, option_index
            FROM landmark_options
            WHERE landmark_id = ?
            ORDER BY option_index
            """,
            (landmark_id,),
        )
    options_map = {}
    # Group option text by landmark id for API output.
    for row in cur.fetchall():
        options_map.setdefault(row["landmark_id"], []).append(row["option_text"])
    return options_map
