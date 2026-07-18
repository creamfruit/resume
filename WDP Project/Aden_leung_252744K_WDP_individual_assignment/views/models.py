# Import datetime utilities for timestamp normalization.
from datetime import datetime

# Import DB connector for model-level data access where needed.
from .db import get_db


# Helper to safely read keys from Row/dict-like objects.
def _row_get(row, key, default=None):
    # Guard against null rows when parsing optional queries.
    if row is None:
        return default
    # Handle sqlite Row objects that expose keys().
    if hasattr(row, "keys"):
        return row[key] if key in row.keys() else default
    return default


# Domain model representing a user row in the database.
class User:
    def __init__(
        self,
        username,
        email=None,
        password_hash=None,
        id=None,
        total_points=0,
        available_points=0,
        current_tier=1,
        active_days=1,
        points=0,
        level=1,
        is_admin=0,
        last_login_date=None,
        current_streak=0,
        created_at=None,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.total_points = total_points
        self.available_points = available_points
        self.current_tier = current_tier
        self.active_days = active_days
        self.points = points
        self.level = level
        self.is_admin = is_admin
        self.last_login_date = last_login_date
        self.current_streak = current_streak
        self.created_at = created_at or datetime.utcnow()

    def get_id(self):
        return self.id

    def get_username(self):
        return self.username

    def get_password_hash(self):
        return self.password_hash

    def to_dict(self):
        # Serialize the model for API responses.
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "total_points": self.total_points,
            "available_points": self.available_points,
            "current_tier": self.current_tier,
            "active_days": self.active_days,
            "points": self.points,
            "level": self.level,
            "is_admin": self.is_admin,
            "last_login_date": self.last_login_date,
            "current_streak": self.current_streak,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_db_row(cls, row):
        # Convert DB rows into User domain objects.
        if row is None:
            return None
        # Normalize created_at into a datetime when stored as text.
        created = _row_get(row, "created_at")
        created_at = datetime.fromisoformat(created) if isinstance(created, str) else created
        return cls(
            id=_row_get(row, "id"),
            username=_row_get(row, "username"),
            email=_row_get(row, "email"),
            password_hash=_row_get(row, "password_hash"),
            total_points=_row_get(row, "total_points", 0),
            available_points=_row_get(row, "available_points", 0),
            current_tier=_row_get(row, "current_tier", 1),
            active_days=_row_get(row, "active_days", 1),
            points=_row_get(row, "points", 0),
            level=_row_get(row, "level", 1),
            is_admin=_row_get(row, "is_admin", 0),
            last_login_date=_row_get(row, "last_login_date"),
            current_streak=_row_get(row, "current_streak", 0),
            created_at=created_at,
        )

    @classmethod
    def from_dict(cls, data):
        # Rehydrate a user model from API payloads or cached dicts.
        created = data.get("created_at")
        created_at = datetime.fromisoformat(created) if isinstance(created, str) else created
        return cls(
            id=data.get("id"),
            username=data["username"],
            email=data.get("email"),
            password_hash=data.get("password_hash"),
            total_points=data.get("total_points", 0),
            available_points=data.get("available_points", 0),
            current_tier=data.get("current_tier", 1),
            active_days=data.get("active_days", 1),
            points=data.get("points", 0),
            level=data.get("level", 1),
            is_admin=data.get("is_admin", 0),
            last_login_date=data.get("last_login_date"),
            current_streak=data.get("current_streak", 0),
            created_at=created_at,
        )


# Domain model representing landmarks and their quiz metadata.
class Landmark:
    def __init__(
        self,
        name,
        icon,
        story,
        question,
        correct_answer,
        x_coord,
        y_coord,
        points_value=100,
        options=None,
        id=None,
    ):
        self.id = id
        self.name = name
        self.icon = icon
        self.story = story
        self.question = question
        self.correct_answer = correct_answer
        self.x_coord = x_coord
        self.y_coord = y_coord
        self.points_value = points_value
        self.options = options or []

    def to_dict(self):
        # Serialize the landmark for API delivery.
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "story": self.story,
            "question": self.question,
            "correct_answer": self.correct_answer,
            "x_coord": self.x_coord,
            "y_coord": self.y_coord,
            "points_value": self.points_value,
            "options": list(self.options) if self.options is not None else [],
        }

    @classmethod
    def from_dict(cls, data):
        # Build landmark instances from request payloads.
        return cls(
            id=data.get("id"),
            name=data["name"],
            icon=data["icon"],
            story=data["story"],
            question=data["question"],
            correct_answer=data["correct_answer"],
            x_coord=data["x_coord"],
            y_coord=data["y_coord"],
            points_value=data.get("points_value", 100),
            options=data.get("options"),
        )


# Domain model representing multiple-choice options for a landmark quiz.
class LandmarkOption:
    def __init__(self, landmark_id, option_text, option_index, id=None):
        self.id = id
        self.landmark_id = landmark_id
        self.option_text = option_text
        self.option_index = option_index

    def to_dict(self):
        # Serialize option data for API consumption.
        return {
            "id": self.id,
            "landmark_id": self.landmark_id,
            "option_text": self.option_text,
            "option_index": self.option_index,
        }

    @classmethod
    def from_dict(cls, data):
        # Create option instances from JSON payloads.
        return cls(
            id=data.get("id"),
            landmark_id=data["landmark_id"],
            option_text=data["option_text"],
            option_index=data["option_index"],
        )


# Join model representing a user's landmark progression state.
class UserLandmark:
    def __init__(
        self,
        user_id,
        landmark_id,
        id=None,
        unlocked=False,
        completed=False,
        unlocked_at=None,
        completed_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.landmark_id = landmark_id
        self.unlocked = unlocked
        self.completed = completed
        self.unlocked_at = unlocked_at
        self.completed_at = completed_at

    def to_dict(self):
        # Serialize progress state for client dashboards.
        return {
            "id": self.id,
            "user_id": self.user_id,
            "landmark_id": self.landmark_id,
            "unlocked": self.unlocked,
            "completed": self.completed,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        # Build a user-landmark state object from data.
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            landmark_id=data["landmark_id"],
            unlocked=data.get("unlocked", False),
            completed=data.get("completed", False),
            unlocked_at=data.get("unlocked_at"),
            completed_at=data.get("completed_at"),
        )


# Domain model representing a quest definition.
class Quest:
    def __init__(self, title, description, reward, total_required=1, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.reward = reward
        self.total_required = total_required

    def to_dict(self):
        # Serialize quest fields for API output.
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "reward": self.reward,
            "total_required": self.total_required,
        }

    @classmethod
    def from_dict(cls, data):
        # Build quest instances from payloads.
        return cls(
            id=data.get("id"),
            title=data["title"],
            description=data["description"],
            reward=data["reward"],
            total_required=data.get("total_required", 1),
        )


# Join model representing a user's quest progress.
class UserQuest:
    def __init__(self, user_id, quest_id, id=None, progress=0, completed=False):
        self.id = id
        self.user_id = user_id
        self.quest_id = quest_id
        self.progress = progress
        self.completed = completed

    def to_dict(self):
        # Serialize quest progress for responses.
        return {
            "id": self.id,
            "user_id": self.user_id,
            "quest_id": self.quest_id,
            "progress": self.progress,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data):
        # Build user-quest progress from persisted data.
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            quest_id=data["quest_id"],
            progress=data.get("progress", 0),
            completed=data.get("completed", False),
        )


# Domain model representing achievement badges.
class Badge:
    def __init__(self, name, icon, description, category, threshold, requirement_type, id=None):
        self.id = id
        self.name = name
        self.icon = icon
        self.description = description
        self.category = category
        self.threshold = threshold
        self.requirement_type = requirement_type

    def to_dict(self):
        # Serialize badge data for API consumers.
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "category": self.category,
            "threshold": self.threshold,
            "requirement_type": self.requirement_type,
        }

    @classmethod
    def from_dict(cls, data):
        # Build badge instances from request or DB payloads.
        return cls(
            id=data.get("id"),
            name=data["name"],
            icon=data["icon"],
            description=data["description"],
            category=data["category"],
            threshold=data["threshold"],
            requirement_type=data["requirement_type"],
        )


# Join model representing a user's earned badges.
class UserBadge:
    def __init__(self, user_id, badge_id, id=None, earned=False, earned_at=None):
        self.id = id
        self.user_id = user_id
        self.badge_id = badge_id
        self.earned = earned
        self.earned_at = earned_at

    def to_dict(self):
        # Serialize badge completion details.
        return {
            "id": self.id,
            "user_id": self.user_id,
            "badge_id": self.badge_id,
            "earned": self.earned,
            "earned_at": self.earned_at.isoformat() if self.earned_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        # Build user-badge records from stored data.
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            badge_id=data["badge_id"],
            earned=data.get("earned", False),
            earned_at=data.get("earned_at"),
        )


# Domain model representing redeemable rewards.
class Reward:
    def __init__(self, name, icon, cost, description=None, id=None):
        self.id = id
        self.name = name
        self.icon = icon
        self.cost = cost
        self.description = description

    def to_dict(self):
        # Serialize reward details for UI rendering.
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "cost": self.cost,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data):
        # Build reward instances from payloads.
        return cls(
            id=data.get("id"),
            name=data["name"],
            icon=data["icon"],
            cost=data["cost"],
            description=data.get("description"),
        )


# Join model representing user reward redemptions.
class UserReward:
    def __init__(self, user_id, reward_id, id=None, redeemed_at=None):
        self.id = id
        self.user_id = user_id
        self.reward_id = reward_id
        self.redeemed_at = redeemed_at

    def to_dict(self):
        # Serialize redemption details for account history.
        return {
            "id": self.id,
            "user_id": self.user_id,
            "reward_id": self.reward_id,
            "redeemed_at": self.redeemed_at.isoformat() if self.redeemed_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        # Build redemption records from DB rows or payloads.
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            reward_id=data["reward_id"],
            redeemed_at=data.get("redeemed_at"),
        )
