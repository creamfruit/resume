from __future__ import annotations
from dataclasses import dataclass
from .base import ModelBase

@dataclass
class RyanAchievementStates(ModelBase):
    _table: str = "achievement_states"
    id: int | None = None
    user_id: int | None = None
    data_json: str | None = None
    updated_at: str | None = None

@dataclass
class RyanAuthEvents(ModelBase):
    _table: str = "auth_events"
    id: int | None = None
    user_id: int | None = None
    event_type: str | None = None
    email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: str | None = None

@dataclass
class RyanBadges(ModelBase):
    _table: str = "badges"
    id: int | None = None
    name: str | None = None
    icon: str | None = None
    description: str | None = None
    category: str | None = None
    threshold: int | None = None
    requirement_type: str | None = None

@dataclass
class RyanCheckinRewards(ModelBase):
    _table: str = "checkin_rewards"
    id: int | None = None
    streak_days: int | None = None
    reward_points: int | None = None
    description: str | None = None

@dataclass
class RyanCircleSignups(ModelBase):
    _table: str = "circle_signups"
    id: int | None = None
    user_id: int | None = None
    circle_title: str | None = None
    circle_time: str | None = None
    circle_duration: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: str | None = None

@dataclass
class RyanLandmarkOptions(ModelBase):
    _table: str = "landmark_options"
    id: int | None = None
    landmark_id: int | None = None
    option_text: str | None = None
    option_index: int | None = None

@dataclass
class RyanLandmarks(ModelBase):
    _table: str = "landmarks"
    id: int | None = None
    name: str | None = None
    icon: str | None = None
    story: str | None = None
    question: str | None = None
    correct_answer: int | None = None
    x: int | None = None
    y: int | None = None

@dataclass
class RyanQuests(ModelBase):
    _table: str = "quests"
    id: int | None = None
    title: str | None = None
    description: str | None = None
    reward: int | None = None
    total_required: int | None = None

@dataclass
class RyanRewards(ModelBase):
    _table: str = "rewards"
    id: int | None = None
    name: str | None = None
    icon: str | None = None
    cost: int | None = None
    description: str | None = None
    is_active: int | None = None

@dataclass
class RyanSkills(ModelBase):
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
class RyanUserBadges(ModelBase):
    _table: str = "user_badges"
    id: int | None = None
    user_id: int | None = None
    badge_id: int | None = None
    earned: int | None = None
    earned_at: str | None = None

@dataclass
class RyanUserCheckins(ModelBase):
    _table: str = "user_checkins"
    id: int | None = None
    user_id: int | None = None
    checkin_date: str | None = None

@dataclass
class RyanUserLandmarks(ModelBase):
    _table: str = "user_landmarks"
    id: int | None = None
    user_id: int | None = None
    landmark_id: int | None = None
    unlocked: int | None = None
    completed: int | None = None
    unlocked_at: str | None = None
    completed_at: str | None = None

@dataclass
class RyanUserQuests(ModelBase):
    _table: str = "user_quests"
    id: int | None = None
    user_id: int | None = None
    quest_id: int | None = None
    progress: int | None = None
    completed: int | None = None
    completed_at: str | None = None

@dataclass
class RyanUserRewards(ModelBase):
    _table: str = "user_rewards"
    id: int | None = None
    user_id: int | None = None
    reward_id: int | None = None
    redeemed_at: str | None = None

@dataclass
class RyanUserSettings(ModelBase):
    _table: str = "user_settings"
    id: int | None = None
    user_id: int | None = None
    key: str | None = None
    value: str | None = None
    updated_at: str | None = None

@dataclass
class RyanUserSkillRewards(ModelBase):
    _table: str = "user_skill_rewards"
    id: int | None = None
    user_id: int | None = None
    skill_id: int | None = None
    reward_points: int | None = None
    rewarded_at: str | None = None

@dataclass
class RyanUserSkills(ModelBase):
    _table: str = "user_skills"
    id: int | None = None
    user_id: int | None = None
    skill_id: int | None = None
    progress: int | None = None
    completed: int | None = None
    completed_at: str | None = None

@dataclass
class RyanUsers(ModelBase):
    _table: str = "users"
    id: int | None = None
    full_name: str | None = None
    email: str | None = None
    password_hash: str | None = None
    member_type: str | None = None
    created_at: str | None = None
    total_points: int | None = None
    available_points: int | None = None
    active_days: int | None = None
    current_tier: int | None = None
    current_streak: int | None = None
    is_admin: int | None = None
