from datetime import datetime

from app.extensions import db


class AuthEvent(db.Model):
    __tablename__ = "auth_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    event_type = db.Column(db.String(20), nullable=False, index=True)  # signup, login
    email = db.Column(db.String(255), nullable=True, index=True)

    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
