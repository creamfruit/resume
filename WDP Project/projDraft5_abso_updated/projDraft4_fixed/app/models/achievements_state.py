from datetime import datetime

from app.extensions import db


class AchievementState(db.Model):
    __tablename__ = "achievement_states"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    data_json = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
