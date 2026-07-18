from __future__ import annotations
from dataclasses import dataclass
from .base import ModelBase

@dataclass
class ReconnectSgChallenges(ModelBase):
    _table: str = "challenges"
    id: int | None = None
    title: str | None = None
    description: str | None = None
    created_at: str | None = None

@dataclass
class ReconnectSgComments(ModelBase):
    _table: str = "comments"
    id: int | None = None
    post_id: int | None = None
    author: str | None = None
    content: str | None = None
    created_at: str | None = None

@dataclass
class ReconnectSgPostLikes(ModelBase):
    _table: str = "post_likes"
    user_id: str | None = None
    post_id: int | None = None

@dataclass
class ReconnectSgPosts(ModelBase):
    _table: str = "posts"
    id: int | None = None
    author: str | None = None
    title: str | None = None
    content: str | None = None
    category: str | None = None
    likes: int | None = None
    created_at: str | None = None

@dataclass
class ReconnectSgSubmissions(ModelBase):
    _table: str = "submissions"
    id: int | None = None
    challenge_id: int | None = None
    author: str | None = None
    content: str | None = None
    image_path: str | None = None
    created_at: str | None = None

@dataclass
class ReconnectSgUsers(ModelBase):
    _table: str = "users"
    id: int | None = None
    username: str | None = None
    password: str | None = None
    role: str | None = None
    points: int | None = None
