"""Minimal username/password account system.

Deliberately small: username + password is enough for now, no email
verification, password reset, or social login. Both `main.py` and
`battle_app.py` import this module directly rather than each other, so
the same credentials and the same issued token work against either
process — they're two separate FastAPI apps on two separate ports
(8000 and 8010) with no shared memory, so the token has to be
self-verifying (stateless) rather than looked up in a server-side
session store.

Persistence follows the same flat-JSON convention every other service
here already uses (see `main.py`'s `database/accounts/*.json`) rather
than adding a database dependency: `database/users.json` holds
username -> {password_hash, salt, created_at}, and
`database/auth_secret.key` holds the HMAC signing secret, generated on
first use so both processes agree on it without any setup step.

An account ID *is* the normalized username (see `normalize_username`) --
this reuses `main.py`'s existing save-slot file convention
(`database/accounts/<account_id>.json`) as the one real, password-
gated save per account, rather than inventing a second identity concept
alongside it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
USERS_FILE = os.path.join(DATABASE_DIR, "users.json")
SECRET_FILE = os.path.join(DATABASE_DIR, "auth_secret.key")

PBKDF2_ITERATIONS = 260_000
TOKEN_TTL_SEC = 7 * 24 * 60 * 60  # a week; there's no refresh flow yet

USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,32}$")
MIN_PASSWORD_LENGTH = 8


class AuthError(Exception):
    """Raised with a message safe to show the user directly."""


@dataclass(frozen=True)
class Account:
    id: str
    created_at: int


def normalize_username(name: str) -> str:
    raw = str(name or "").strip().lower()
    return "".join(ch for ch in raw if ch.isalnum() or ch in ("_", "-"))[:32]


def _get_secret() -> bytes:
    os.makedirs(DATABASE_DIR, exist_ok=True)
    if not os.path.exists(SECRET_FILE):
        # Only this process's first-ever run generates the secret; every
        # later run (and the other app's process) just reads the same file.
        with open(SECRET_FILE, "w", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_FILE, "r", encoding="utf-8") as f:
        return bytes.fromhex(f.read().strip())


def _load_users() -> dict[str, dict]:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_users(users: dict[str, dict]) -> None:
    os.makedirs(DATABASE_DIR, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=True)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS).hex()


def register(username: str, password: str) -> str:
    """Create a new account. Returns the account id. Raises AuthError on
    a malformed username, too-short password, or a name already taken."""
    account_id = normalize_username(username)
    if not USERNAME_RE.match(account_id):
        raise AuthError("Username must be 3-32 characters: letters, numbers, _ or -.")
    if len(str(password or "")) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    users = _load_users()
    if account_id in users:
        raise AuthError("That username is already taken.")

    salt = secrets.token_hex(16)
    users[account_id] = {
        "password_hash": _hash_password(password, bytes.fromhex(salt)),
        "salt": salt,
        "created_at": int(time.time()),
    }
    _save_users(users)
    return account_id


def verify_login(username: str, password: str) -> str:
    """Returns the account id on success. Raises AuthError otherwise --
    deliberately the same message for "no such user" and "wrong
    password" so a login attempt can't be used to enumerate usernames."""
    account_id = normalize_username(username)
    record = _load_users().get(account_id)
    if not record:
        raise AuthError("Invalid username or password.")
    salt = bytes.fromhex(record["salt"])
    actual = _hash_password(password, salt)
    if not hmac.compare_digest(str(record["password_hash"]), actual):
        raise AuthError("Invalid username or password.")
    return account_id


def account_exists(account_id: str) -> bool:
    return normalize_username(account_id) in _load_users()


def issue_token(account_id: str) -> str:
    expiry = int(time.time()) + TOKEN_TTL_SEC
    payload = f"{account_id}:{expiry}"
    sig = hmac.new(_get_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def verify_token(token: str) -> str | None:
    """Returns the account id if the token is well-formed, correctly
    signed, and unexpired -- None otherwise. Never raises."""
    try:
        raw = base64.urlsafe_b64decode(str(token or "").encode("ascii")).decode("utf-8")
        account_id, expiry_str, sig = raw.rsplit(":", 2)
        expiry = int(expiry_str)
    except Exception:
        return None

    payload = f"{account_id}:{expiry}"
    expected_sig = hmac.new(_get_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, sig):
        return None
    if expiry < int(time.time()):
        return None
    return account_id


def token_from_authorization_header(header_value: str | None) -> str:
    value = str(header_value or "")
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return ""
