"""Account system regression tests: registration, login, password
hashing, session tokens, and -- the core promise of this phase -- that
one account's data is never visible to or mutable by another, for both
the new battle screen (battle_app.py) and the legacy game (main.py).
"""
from __future__ import annotations

import hmac
import json
import os
import tempfile
import threading
import time
import unittest
import uuid

from fastapi.testclient import TestClient

import battle_app
from _account_test_helpers import authed_client, bundle_for
from services import auth


def _unique_username(prefix: str = "acct") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------- services/auth.py unit tests ----------

class RegistrationTests(unittest.TestCase):
    def test_register_returns_the_normalized_account_id(self):
        name = _unique_username()
        account_id = auth.register(f"  {name.upper()}  ", "correcthorsebattery")
        self.assertEqual(account_id, name)

    def test_username_must_meet_the_shape_requirements(self):
        # normalize_username strips spaces/punctuation and truncates to
        # 32 chars before the shape check (matching main.py's pre-
        # existing _safe_account_name convention for account names) --
        # so only "still too short after normalizing" actually survives
        # to fail the check.
        for bad in ("ab", ""):
            with self.assertRaises(auth.AuthError):
                auth.register(bad, "areallygoodpassword")

    def test_disallowed_characters_are_stripped_not_rejected(self):
        # Consistent with main.py's existing account-name normalization:
        # a username survives if what's left after stripping spaces and
        # punctuation still meets the shape requirements.
        account_id = auth.register(f"has spaces {_unique_username()}", "areallygoodpassword")
        self.assertNotIn(" ", account_id)

    def test_overly_long_username_is_truncated_not_rejected(self):
        account_id = auth.register("x" * 40, "areallygoodpassword")
        self.assertEqual(len(account_id), 32)

    def test_password_must_meet_the_minimum_length(self):
        with self.assertRaises(auth.AuthError):
            auth.register(_unique_username(), "short1")

    def test_duplicate_username_is_rejected(self):
        name = _unique_username()
        auth.register(name, "correcthorsebattery")
        with self.assertRaises(auth.AuthError):
            auth.register(name, "adifferentpassword")

    def test_duplicate_check_is_case_and_whitespace_insensitive(self):
        name = _unique_username()
        auth.register(name, "correcthorsebattery")
        with self.assertRaises(auth.AuthError):
            auth.register(f" {name.upper()} ", "adifferentpassword")


class LoginTests(unittest.TestCase):
    def test_correct_credentials_return_the_account_id(self):
        name = _unique_username()
        auth.register(name, "correcthorsebattery")
        self.assertEqual(auth.verify_login(name, "correcthorsebattery"), name)

    def test_wrong_password_is_rejected(self):
        name = _unique_username()
        auth.register(name, "correcthorsebattery")
        with self.assertRaises(auth.AuthError):
            auth.verify_login(name, "wrongpassword")

    def test_nonexistent_user_is_rejected(self):
        with self.assertRaises(auth.AuthError):
            auth.verify_login(_unique_username("ghost"), "whatever123")

    def test_wrong_password_and_no_such_user_give_the_same_message(self):
        # A login attempt must not be usable to enumerate registered
        # usernames. (Python deletes an `except ... as e` binding at the
        # end of its block, so the messages are captured into plain
        # locals here rather than compared via the exception objects.)
        name = _unique_username()
        auth.register(name, "correcthorsebattery")
        try:
            auth.verify_login(name, "wrongpassword")
            self.fail("expected AuthError")
        except auth.AuthError as exc:
            wrong_password_message = str(exc)
        try:
            auth.verify_login(_unique_username("ghost"), "whatever123")
            self.fail("expected AuthError")
        except auth.AuthError as exc:
            no_such_user_message = str(exc)
        self.assertEqual(wrong_password_message, no_such_user_message)


class PasswordHashingTests(unittest.TestCase):
    def test_passwords_are_never_stored_in_plain_text(self):
        name = _unique_username()
        password = "correcthorsebattery"
        auth.register(name, password)
        with open(auth.USERS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        record = raw[name]
        self.assertNotIn(password, json.dumps(record))
        self.assertIn("password_hash", record)
        self.assertIn("salt", record)
        # A real, non-trivial hash -- not the password itself re-encoded.
        self.assertNotEqual(record["password_hash"], password)
        self.assertGreaterEqual(len(record["password_hash"]), 32)

    def test_two_accounts_with_the_same_password_get_different_hashes(self):
        # Distinct salts -- confirms salting is actually happening, not
        # just a bare hash of the password.
        password = "correcthorsebattery"
        name_a, name_b = _unique_username("a"), _unique_username("b")
        auth.register(name_a, password)
        auth.register(name_b, password)
        with open(auth.USERS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self.assertNotEqual(raw[name_a]["password_hash"], raw[name_b]["password_hash"])
        self.assertNotEqual(raw[name_a]["salt"], raw[name_b]["salt"])


class TokenTests(unittest.TestCase):
    def test_token_round_trips_to_the_same_account(self):
        name = _unique_username()
        token = auth.issue_token(name)
        self.assertEqual(auth.verify_token(token), name)

    def test_tampered_token_is_rejected(self):
        token = auth.issue_token(_unique_username())
        tampered = token[:-2] + ("xx" if not token.endswith("xx") else "yy")
        self.assertIsNone(auth.verify_token(tampered))

    def test_garbage_token_is_rejected(self):
        self.assertIsNone(auth.verify_token("not-a-real-token"))
        self.assertIsNone(auth.verify_token(""))

    def test_expired_token_is_rejected(self):
        account_id = _unique_username()
        old_expiry = int(time.time()) - 10
        payload = f"{account_id}:{old_expiry}"
        import base64
        import hashlib
        sig = hmac.new(auth._get_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        expired = base64.urlsafe_b64encode(f"{payload}:{sig}".encode("utf-8")).decode("ascii")
        self.assertIsNone(auth.verify_token(expired))

    def test_token_from_authorization_header_extracts_the_bearer_value(self):
        self.assertEqual(auth.token_from_authorization_header("Bearer abc123"), "abc123")
        self.assertEqual(auth.token_from_authorization_header("bearer abc123"), "abc123")
        self.assertEqual(auth.token_from_authorization_header(None), "")
        self.assertEqual(auth.token_from_authorization_header("abc123"), "")  # no "Bearer " prefix


# ---------- battle_app.py cross-account isolation ----------

class BattleAppAuthGateTests(unittest.TestCase):
    def test_protected_endpoint_requires_a_token(self):
        c = TestClient(battle_app.app)
        self.assertEqual(c.get("/api/player").status_code, 401)

    def test_invalid_token_is_rejected(self):
        c = TestClient(battle_app.app)
        c.headers.update({"Authorization": "Bearer not-a-real-token"})
        self.assertEqual(c.get("/api/player").status_code, 401)

    def test_public_pages_need_no_token(self):
        c = TestClient(battle_app.app)
        self.assertEqual(c.get("/").status_code, 200)
        self.assertEqual(c.get("/login").status_code, 200)
        self.assertEqual(c.get("/battle").status_code, 200)


class BattleAppIsolationTests(unittest.TestCase):
    def test_two_accounts_get_independent_player_objects(self):
        a, b = authed_client(), authed_client()
        self.assertIsNot(bundle_for(a)["player"], bundle_for(b)["player"])

    def test_one_accounts_progress_never_appears_on_another(self):
        a, b = authed_client(), authed_client()
        bundle_for(a)["player"].level = 42

        self.assertEqual(a.get("/api/player").json()["level"], 42)
        self.assertEqual(b.get("/api/player").json()["level"], 1)

    def test_ones_wallet_never_leaks_into_anothers(self):
        a, b = authed_client(), authed_client()
        bundle_for(a)["wallet"].gold = 777
        bundle_for(a)["wallet"].chests["rare"] = 3

        self.assertEqual(a.get("/api/player/wallet").json()["gold"], 777)
        wallet_b = b.get("/api/player/wallet").json()
        self.assertEqual(wallet_b["gold"], 0)
        self.assertEqual(wallet_b["chests"], {})

    def test_a_battle_started_by_one_account_is_invisible_to_another(self):
        a, b = authed_client(), authed_client()
        res = a.post("/api/battle/start", json={"seed": 2, "archetype": "brute"})
        self.assertEqual(res.status_code, 200)

        # b has no battle of its own -- a's existence must not leak.
        self.assertEqual(b.get("/api/battle/state").status_code, 404)
        # a's battle is still there, unaffected by b's request.
        self.assertEqual(a.get("/api/battle/state").status_code, 200)

    def test_identity_is_carried_entirely_by_the_token_not_the_http_client(self):
        # A fresh TestClient instance presenting account A's own token
        # must be treated as account A -- identity comes from the
        # token, never from which client object happens to be asking.
        a, b = authed_client(), authed_client()
        a.post("/api/battle/start", json={"seed": 2, "archetype": "brute"})
        bundle_for(a)["player"].level = 99

        token_a = a.headers["Authorization"]
        fresh = TestClient(battle_app.app)
        fresh.headers.update({"Authorization": token_a})
        self.assertEqual(fresh.get("/api/player").json()["level"], 99)
        self.assertEqual(fresh.get("/api/battle/state").status_code, 200)

    def test_concurrent_requests_from_two_accounts_never_cross_contaminate(self):
        # The actual reason a ContextVar-based retrofit was used instead
        # of a naive "reassign the global" middleware: Starlette
        # dispatches sync `def` routes to a real threadpool, so two
        # accounts' requests can genuinely run at the same time.
        a, b = authed_client(), authed_client()
        # Force distinct, easy-to-recognize gold values through the
        # wallet (core/player_state.py's PlayerState has no gold field
        # of its own -- gold lives on the wallet).
        bundle_for(a)["wallet"].gold = 111111
        bundle_for(b)["wallet"].gold = 222222

        mismatches = []

        def hammer(client, expected_gold, rounds):
            for _ in range(rounds):
                got = client.get("/api/player/wallet").json()["gold"]
                if got != expected_gold:
                    mismatches.append((expected_gold, got))

        threads = [
            threading.Thread(target=hammer, args=(a, 111111, 30)),
            threading.Thread(target=hammer, args=(b, 222222, 30)),
            threading.Thread(target=hammer, args=(a, 111111, 30)),
            threading.Thread(target=hammer, args=(b, 222222, 30)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(mismatches, [])


# ---------- main.py cross-account isolation ----------

class MainAppIsolationTests(unittest.TestCase):
    """main.py needs its own scratch database directory (separate from
    battle_app.py's -- they're different globals) so these tests never
    touch the real project's database/ files."""

    @classmethod
    def setUpClass(cls):
        import main
        cls.main = main
        cls._scratch = tempfile.mkdtemp(prefix="runeted_test_main_")
        cls._orig_accounts_dir = main.ACCOUNTS_DIR
        cls._orig_index_file = main.ACCOUNT_INDEX_FILE
        cls._orig_state_file = main.STATE_FILE
        main.ACCOUNTS_DIR = os.path.join(cls._scratch, "accounts")
        main.ACCOUNT_INDEX_FILE = os.path.join(cls._scratch, "accounts.json")
        main.STATE_FILE = os.path.join(cls._scratch, "game_state.json")

    @classmethod
    def tearDownClass(cls):
        cls.main.ACCOUNTS_DIR = cls._orig_accounts_dir
        cls.main.ACCOUNT_INDEX_FILE = cls._orig_index_file
        cls.main.STATE_FILE = cls._orig_state_file

    def setUp(self):
        self.client = TestClient(self.main.app)

    def _register_and_login(self, username: str, password: str = "areallygoodpassword") -> str:
        res = self.client.post("/auth/register", json={"username": username, "password": password})
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()["token"]

    def test_protected_endpoint_requires_a_token(self):
        self.assertEqual(self.client.get("/player/stats").status_code, 401)

    def test_two_accounts_have_independent_player_state(self):
        name_a, name_b = _unique_username("main_a"), _unique_username("main_b")
        token_a = self._register_and_login(name_a)
        token_b = self._register_and_login(name_b)

        # Prime both accounts' caches, then mutate account A's live object.
        self.client.get("/player/stats", headers={"Authorization": f"Bearer {token_a}"})
        self.client.get("/player/stats", headers={"Authorization": f"Bearer {token_b}"})
        self.main._ACCOUNT_CACHE[name_a]["player"].gold = 5000

        stats_a = self.client.get("/player/stats", headers={"Authorization": f"Bearer {token_a}"}).json()
        stats_b = self.client.get("/player/stats", headers={"Authorization": f"Bearer {token_b}"}).json()
        self.assertEqual(stats_a["gold"], 5000)
        self.assertEqual(stats_b["gold"], 0)

    def test_saving_one_account_never_writes_into_anothers_file(self):
        name_a, name_b = _unique_username("main_a"), _unique_username("main_b")
        token_a = self._register_and_login(name_a)
        self._register_and_login(name_b)

        self.client.get("/player/stats", headers={"Authorization": f"Bearer {token_a}"})
        self.main._ACCOUNT_CACHE[name_a]["player"].gold = 4242
        res = self.client.post("/account/save", headers={"Authorization": f"Bearer {token_a}"})
        self.assertEqual(res.status_code, 200, res.text)

        with open(self.main._state_file_for_account(name_a), "r", encoding="utf-8") as f:
            saved_a = json.load(f)
        self.assertEqual(saved_a["player"]["gold"], 4242)
        self.assertEqual(saved_a["account"], name_a)
        self.assertFalse(os.path.exists(self.main._state_file_for_account(name_b)))

    def test_account_list_only_ever_shows_the_callers_own_account(self):
        name_a, name_b = _unique_username("main_a"), _unique_username("main_b")
        token_a = self._register_and_login(name_a)
        token_b = self._register_and_login(name_b)
        self.client.post("/account/save", headers={"Authorization": f"Bearer {token_a}"})
        self.client.post("/account/save", headers={"Authorization": f"Bearer {token_b}"})

        state_a = self.client.get("/account/state", headers={"Authorization": f"Bearer {token_a}"}).json()
        ids = [row["id"] for row in state_a["accounts"]]
        self.assertEqual(ids, [name_a])
        self.assertNotIn(name_b, ids)

    def test_account_switching_endpoints_are_retired(self):
        token = self._register_and_login(_unique_username("main"))
        headers = {"Authorization": f"Bearer {token}"}
        for path, payload in (
            ("/account/use", {"account": "anyone"}),
            ("/account/rename", {"account": "anyone", "new_name": "someoneelse"}),
            ("/account/delete", {"account": "anyone"}),
        ):
            res = self.client.post(path, json=payload, headers=headers)
            self.assertEqual(res.status_code, 200)  # a JSON {"error": ...}, not a 5xx
            self.assertIn("error", res.json())
            self.assertIn("no longer supported", res.json()["error"].lower())

    def test_concurrent_requests_from_two_main_accounts_never_cross_contaminate(self):
        name_a, name_b = _unique_username("main_a"), _unique_username("main_b")
        token_a = self._register_and_login(name_a)
        token_b = self._register_and_login(name_b)
        self.client.get("/player/stats", headers={"Authorization": f"Bearer {token_a}"})
        self.client.get("/player/stats", headers={"Authorization": f"Bearer {token_b}"})
        self.main._ACCOUNT_CACHE[name_a]["player"].gold = 13131
        self.main._ACCOUNT_CACHE[name_b]["player"].gold = 24242

        mismatches = []

        def hammer(token, expected_gold, rounds):
            for _ in range(rounds):
                got = self.client.get("/player/stats", headers={"Authorization": f"Bearer {token}"}).json()["gold"]
                if got != expected_gold:
                    mismatches.append((expected_gold, got))

        threads = [
            threading.Thread(target=hammer, args=(token_a, 13131, 30)),
            threading.Thread(target=hammer, args=(token_b, 24242, 30)),
            threading.Thread(target=hammer, args=(token_a, 13131, 30)),
            threading.Thread(target=hammer, args=(token_b, 24242, 30)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(mismatches, [])


if __name__ == "__main__":
    unittest.main()
