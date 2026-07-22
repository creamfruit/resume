"""Shared helper for battle_app.py tests (not itself a test file --
doesn't match the test_*.py discovery pattern).

Every existing test file's client() helper used to reset the single
global battle_app.CURRENT directly between tests. Now that accounts are
real and CURRENT resolves per-account (see battle_app.py's auth
middleware), the equivalent reset is simply "use a brand-new account" --
one that's never existed has nothing stale to reset in the first place.
"""
from __future__ import annotations

import os
import tempfile
import uuid

from fastapi.testclient import TestClient

import battle_app
from services import auth

# services/auth.py defaults to backend/database/{users.json,auth_secret.key} --
# every test that registers an account (any test using authed_client()
# below) would otherwise write real accounts into the project's own
# database/ directory. Redirect to a throwaway directory once, for the
# whole test process, so test runs never touch real project files.
_SCRATCH_DIR = tempfile.mkdtemp(prefix="runeted_test_auth_")
auth.DATABASE_DIR = _SCRATCH_DIR
auth.USERS_FILE = os.path.join(_SCRATCH_DIR, "users.json")
auth.SECRET_FILE = os.path.join(_SCRATCH_DIR, "auth_secret.key")


def authed_client() -> TestClient:
    """A TestClient logged in as a freshly registered, never-before-used
    account, with the Authorization header already attached to every
    request it makes from here on."""
    c = TestClient(battle_app.app)
    c.account_id = f"test_{uuid.uuid4().hex[:12]}"
    res = c.post("/auth/register", json={"username": c.account_id, "password": "testpassword123"})
    assert res.status_code == 200 and res.json().get("ok"), res.text
    token = res.json()["token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    # Prime this account's cache entry so tests can reach into its
    # bundle (see bundle_for below) before making any other request.
    c.get("/api/player")
    return c


def bundle_for(c: TestClient) -> dict:
    """The live per-account state dict `c` is authenticated as -- the
    direct replacement for the old bare battle_app.CURRENT[...] access
    in test bodies that need to set up or inspect state directly rather
    than through the API (e.g. `bundle_for(c)["player"].level = 5`)."""
    return battle_app._ACCOUNT_CACHE[c.account_id]
