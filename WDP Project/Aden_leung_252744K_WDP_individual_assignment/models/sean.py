from __future__ import annotations
from dataclasses import dataclass
from .base import ModelBase

@dataclass
class SeanMatches(ModelBase):
    _table: str = "matches"
    id: int | None = None
    match_id: str | None = None
    name: str | None = None
    avatar: str | None = None
    location: str | None = None
    created_at: str | None = None

@dataclass
class SeanMessages(ModelBase):
    _table: str = "messages"
    id: int | None = None
    chat_id: str | None = None
    sender: str | None = None
    text: str | None = None
    created_at: str | None = None
    edited_at: str | None = None
    is_deleted: int | None = None
    deleted_at: str | None = None

@dataclass
class SeanProfanities(ModelBase):
    _table: str = "profanities"
    id: int | None = None
    word: str | None = None
    level: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

@dataclass
class SeanReports(ModelBase):
    _table: str = "reports"
    id: int | None = None
    case_id: str | None = None
    report_type: str | None = None
    reporter: str | None = None
    status: str | None = None
    summary: str | None = None
    user_a: str | None = None
    user_b: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

@dataclass
class SeanUsers(ModelBase):
    _table: str = "users"
    id: int | None = None
    name: str | None = None
    email: str | None = None
    password_hash: str | None = None
    role: str | None = None
    is_admin: int | None = None
    created_at: str | None = None
