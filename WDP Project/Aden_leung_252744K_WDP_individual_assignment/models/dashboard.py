from __future__ import annotations
from dataclasses import dataclass
from .base import ModelBase

@dataclass
class DashboardChallenge(ModelBase):
    _table: str = "challenge"
    id: int | None = None
    title: str | None = None
    description: str | None = None

@dataclass
class DashboardCircle(ModelBase):
    _table: str = "circle"
    id: int | None = None
    name: str | None = None

@dataclass
class DashboardSubmission(ModelBase):
    _table: str = "submission"
    id: int | None = None
    content: str | None = None
    challenge_id: int | None = None
