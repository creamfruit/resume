from __future__ import annotations
from dataclasses import dataclass
from .base import ModelBase

@dataclass
class AdenBadges(ModelBase):
    _table: str = "badges"
    id: int | None = None
    name: str | None = None
    icon: str | None = None
    description: str | None = None
    category: str | None = None
    threshold: int | None = None
    requirement_type: str | None = None

@dataclass
class AdenCheckinRewards(ModelBase):
    _table: str = "checkin_rewards"
    id: int | None = None
    user_id: int | None = None
    reward_type: str | None = None
    period_start: str | None = None
    awarded_at: str | None = None

@dataclass
class AdenLandmarkOptions(ModelBase):
    _table: str = "landmark_options"
    id: int | None = None
    landmark_id: int | None = None
    option_text: str | None = None
    option_index: int | None = None

@dataclass
class AdenLandmarks(ModelBase):
    _table: str = "landmarks"
    id: int | None = None
    name: str | None = None
    icon: str | None = None
    story: str | None = None
    question: str | None = None
    correct_answer: int | None = None
    x_coord: int | None = None
    y_coord: int | None = None
    points_value: int | None = None

@dataclass
class AdenQuests(ModelBase):
    _table: str = "quests"
    id: int | None = None
    title: str | None = None
    description: str | None = None
    reward: int | None = None
    total_required: int | None = None

@dataclass
class AdenRewards(ModelBase):
    _table: str = "rewards"
    id: int | None = None
    name: str | None = None
    icon: str | None = None
    cost: int | None = None
    description: str | None = None
    is_active: int | None = None

@dataclass
class AdenSkills(ModelBase):
    _table: str = "skills"
    id: int | None = None
    name: str | None = None
    description: str | None = None
    required_count: int | None = None
    parent_id: int | None = None
    category: str | None = None
    level: int | None = None
    icon: str | None = None
    reward_points: int | None = None

@dataclass
class AdenUserBadges(ModelBase):
    _table: str = "user_badges"
    id: int | None = None
    user_id: int | None = None
    badge_id: int | None = None
    earned: int | None = None
    earned_at: str | None = None

@dataclass
class AdenUserCheckins(ModelBase):
    _table: str = "user_checkins"
    id: int | None = None
    user_id: int | None = None
    checkin_date: str | None = None
    created_at: str | None = None

@dataclass
class AdenUserLandmarks(ModelBase):
    _table: str = "user_landmarks"
    id: int | None = None
    user_id: int | None = None
    landmark_id: int | None = None
    unlocked: int | None = None
    completed: int | None = None
    unlocked_at: str | None = None
    completed_at: str | None = None

@dataclass
class AdenUserQuests(ModelBase):
    _table: str = "user_quests"
    id: int | None = None
    user_id: int | None = None
    quest_id: int | None = None
    progress: int | None = None
    completed: int | None = None
    completed_at: str | None = None

@dataclass
class AdenUserRewards(ModelBase):
    _table: str = "user_rewards"
    id: int | None = None
    user_id: int | None = None
    reward_id: int | None = None
    redeemed_at: str | None = None

@dataclass
class AdenUserSkillRewards(ModelBase):
    _table: str = "user_skill_rewards"
    id: int | None = None
    user_id: int | None = None
    reward_type: str | None = None
    reward_key: str | None = None
    awarded_at: str | None = None

@dataclass
class AdenUserSkills(ModelBase):
    _table: str = "user_skills"
    id: int | None = None
    user_id: int | None = None
    skill_id: int | None = None
    progress: int | None = None
    completed: int | None = None
    completed_at: str | None = None

@dataclass
class AdenUsers(ModelBase):
    _table: str = "users"
    id: int | None = None
    username: str | None = None
    email: str | None = None
    password_hash: str | None = None
    total_points: int | None = None
    available_points: int | None = None
    current_tier: int | None = None
    active_days: int | None = None
    points: int | None = None
    level: int | None = None
    is_admin: int | None = None
    last_login_date: str | None = None
    current_streak: int | None = None
    created_at: str | None = None
