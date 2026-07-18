# Import Flask helpers for rendering templates and JSON responses.
from flask import jsonify, render_template
# Import DB connector for lightweight stats queries.
from .db import get_db

# Register landing and dashboard page routes on the app instance.
def register_home_routes(app):
    """Register home/landing page routes"""
    
    # Serve the main landing page for authenticated or public traffic.
    @app.route('/')
    def index():
        """Main landing page"""
        return render_template('index.html')
    
    # Serve the dashboard view for user summaries.
    @app.route('/dashboard')
    def dashboard():
        """Dashboard page"""
        return render_template('dashboard.html')
    
    # Serve the map visualization view.
    @app.route('/map')
    def map_view():
        """Map view page"""
        return render_template('map.html')
    
    # Serve the quests overview page.
    @app.route('/quests')
    def quests_view():
        """Quests page"""
        return render_template('quests.html')
    
    # Provide aggregate stats for UI widgets and system monitoring.
    @app.route('/api/stats', methods=['GET'])
    def get_overall_stats():
        """Get overall application statistics"""
        # NOTE: could be refactored for scalability
        return jsonify({
            'total_users': _count_rows("users"),
            'total_landmarks': _count_rows("landmarks"),
            'total_quests': _count_rows("quests"),
            'total_badges': _count_rows("badges")
        })


# Helper to count records in a table for lightweight metrics.
def _count_rows(table_name):
    # Query database to count table rows for dashboard summaries.
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
    row = cur.fetchone()
    return row["count"] if row else 0
