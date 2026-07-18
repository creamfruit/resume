from flask import Blueprint, render_template, session, redirect, url_for
from storage import store

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = store.get_user_by_id(session['user_id'])
    quests = store.get_user_quests(session['user_id'])
    
    return render_template('dashboard.html', user=user, quests=quests)

@dashboard_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = store.get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

@dashboard_bp.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    return render_template('messages.html')