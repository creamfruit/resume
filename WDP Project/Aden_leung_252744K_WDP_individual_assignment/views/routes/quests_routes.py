# Import Flask routing utilities for quest APIs.
from flask import Blueprint, jsonify, request

# Import DB connector, admin guard, and form validation.
from views.db import get_db
from views.routes.admin_utils import require_admin
from views.forms import QuestForm

# This Blueprint exposes quest CRUD endpoints.
api_quests_bp = Blueprint('api_quests', __name__)

# List all quest definitions.
@api_quests_bp.route('/quests', methods=['GET'])
def get_quests():
    conn = get_db()
    cur = conn.cursor()
    # Query database for quest metadata.
    cur.execute(
        """
        SELECT id, title, description, reward, total_required
        FROM quests
        ORDER BY id
        """
    )
    return jsonify([dict(row) for row in cur.fetchall()]), 200

# Get a single quest by id.
@api_quests_bp.route('/quests/<int:quest_id>', methods=['GET'])
def get_quest(quest_id):
    conn = get_db()
    cur = conn.cursor()
    # Query database for the requested quest.
    cur.execute(
        """
        SELECT id, title, description, reward, total_required
        FROM quests
        WHERE id = ?
        """,
        (quest_id,),
    )
    row = cur.fetchone()
    # Return 404 if the quest does not exist.
    if not row:
        return jsonify({'success': False, 'error': 'Quest not found'}), 404
    return jsonify(dict(row)), 200

# Create a new quest (admin-only).
@api_quests_bp.route('/quests', methods=['POST'])
def create_quest():
    _, err = require_admin()
    if err:
        return err
    # Validate input payload using a form schema.
    form = QuestForm(data=request.get_json(silent=True) or {})
    
    if not form.validate():
        return jsonify({'success': False, 'error': 'Validation failed', 'messages': form.errors}), 400
    
    conn = get_db()
    cur = conn.cursor()
    # Insert the quest into the database.
    cur.execute(
        """
        INSERT INTO quests (title, description, reward, total_required)
        VALUES (?, ?, ?, ?)
        """,
        (form.title.data, form.description.data, form.reward.data, form.total_required.data),
    )
    conn.commit()
    
    return {
        'message': 'Quest created successfully',
        'quest_id': cur.lastrowid
    }, 201

# Update an existing quest (admin-only).
@api_quests_bp.route('/quests/<int:quest_id>', methods=['PUT'])
def update_quest(quest_id):
    _, err = require_admin()
    if err:
        return err
    # Validate input payload using a form schema.
    form = QuestForm(data=request.get_json(silent=True) or {})
    
    if not form.validate():
        return jsonify({'success': False, 'error': 'Validation failed', 'messages': form.errors}), 400

    conn = get_db()
    cur = conn.cursor()
    # Guard against updates to missing quests.
    cur.execute("SELECT id FROM quests WHERE id = ?", (quest_id,))
    if not cur.fetchone():
        return jsonify({'success': False, 'error': 'Quest not found'}), 404

    # Persist updated quest fields.
    cur.execute(
        """
        UPDATE quests
        SET title = ?, description = ?, reward = ?, total_required = ?
        WHERE id = ?
        """,
        (form.title.data, form.description.data, form.reward.data, form.total_required.data, quest_id),
    )
    conn.commit()
    return {'message': 'Quest updated successfully'}, 200

# Delete a quest and its data (admin-only).
@api_quests_bp.route('/quests/<int:quest_id>', methods=['DELETE'])
def delete_quest(quest_id):
    _, err = require_admin()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    # Guard against deleting a missing quest.
    cur.execute("SELECT id FROM quests WHERE id = ?", (quest_id,))
    if not cur.fetchone():
        return jsonify({'success': False, 'error': 'Quest not found'}), 404
    # Delete the quest record.
    cur.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
    conn.commit()
    return {'message': 'Quest deleted successfully'}, 200
