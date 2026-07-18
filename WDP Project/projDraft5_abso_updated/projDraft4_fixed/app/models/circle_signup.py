from datetime import datetime

from app.extensions import db


class CircleSignup(db.Model):
    __tablename__ = "circle_signups"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    circle_title = db.Column(db.String(255), nullable=False)
    circle_time = db.Column(db.String(255), nullable=True)
    circle_duration = db.Column(db.String(255), nullable=True)

    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
