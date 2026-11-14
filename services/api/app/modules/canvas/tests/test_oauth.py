import json
import unittest
from urllib.parse import parse_qs, urlsplit

from app.modules.canvas.config import CanvasConfigError, CanvasSettings, Secret
from app.modules.canvas.oauth import (
    CanvasOAuthError,
    StateStore,
    build_authorization_url,
    exchange_code,
    refresh_access_token,
)

ORIGIN = "https://canvas.example.edu"
CLIENT_SECRET = "synthetic-client-secret"
REDIRECT = "https://api.example.test/v1/canvas/callback"


def settings(**overrides):
    env = {
        "CANVAS_BASE_URL": ORIGIN,
        "CANVAS_OAUTH_CLIENT_ID": "1234",
        "CANVAS_OAUTH_CLIENT_SECRET": CLIENT_SECRET,
        "CANVAS_OAUTH_REDIRECT_URI": REDIRECT,
        **overrides,
    }
    return CanvasSettings.from_env(env)


class FakePost:
    def __init__(self, status, payload):
        self.status = status
        self.body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.calls = []

    def __call__(self, url, fields):
        self.calls.append((url, fields))
        return self.status, self.body


class AuthorizationUrlTests(unittest.TestCase):
    def test_points_at_canvas_with_state_and_no_secret(self):
        url = build_authorization_url(settings(), "state-abc")
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        self.assertEqual(f"{parts.scheme}://{parts.netloc}{parts.path}", f"{ORIGIN}/login/oauth2/auth")
        self.assertEqual(query["state"], ["state-abc"])
        self.assertEqual(query["redirect_uri"], [REDIRECT])
        self.assertEqual(query["response_type"], ["code"])
        self.assertNotIn(CLIENT_SECRET, url)

    def test_requires_a_developer_key(self):
        with self.assertRaises(CanvasConfigError):
            build_authorization_url(settings(CANVAS_OAUTH_CLIENT_ID=""), "state-abc")


class StateStoreTests(unittest.TestCase):
    def test_state_returns_its_user_exactly_once(self):
        store = StateStore()
        state = store.issue("user-a")
        self.assertEqual(store.consume(state), "user-a")
        with self.assertRaises(CanvasOAuthError):
            store.consume(state)

    def test_unknown_and_expired_states_are_rejected(self):
        clock = [1000.0]
        store = StateStore(now=lambda: clock[0])
        with self.assertRaises(CanvasOAuthError):
            store.consume("made-up")
        state = store.issue("user-a")
        clock[0] += 601
        with self.assertRaises(CanvasOAuthError):
            store.consume(state)

    def test_states_are_unpredictable_per_user(self):
        store = StateStore()
        self.assertNotEqual(store.issue("user-a"), store.issue("user-a"))


class TokenTests(unittest.TestCase):
    def test_exchange_code(self):
        post = FakePost(
            200,
            {"access_token": "at", "refresh_token": "rt", "expires_in": 3600, "user": {"id": 42}},
        )
        tokens = exchange_code(settings(), "one-time-code", post)
        url, fields = post.calls[0]
        self.assertEqual(url, f"{ORIGIN}/login/oauth2/token")
        self.assertEqual(fields["grant_type"], "authorization_code")
        self.assertEqual(fields["redirect_uri"], REDIRECT)
        self.assertEqual(tokens.access_token.reveal(), "at")
        self.assertEqual(tokens.refresh_token.reveal(), "rt")
        self.assertEqual(tokens.external_user_id, "42")
        self.assertNotIn("at", repr(tokens))

    def test_refresh_keeps_working_without_new_refresh_token(self):
        post = FakePost(200, {"access_token": "at2", "expires_in": 3600})
        tokens = refresh_access_token(settings(), Secret("rt"), post)
        self.assertEqual(post.calls[0][1]["grant_type"], "refresh_token")
        self.assertEqual(tokens.access_token.reveal(), "at2")
        self.assertIsNone(tokens.refresh_token)

    def test_failures_do_not_leak_code_or_secret(self):
        for post in (FakePost(400, {"error": "invalid_grant"}), FakePost(200, b"<html>")):
            with self.assertRaises(CanvasOAuthError) as ctx:
                exchange_code(settings(), "one-time-code", post)
            self.assertNotIn("one-time-code", str(ctx.exception))
            self.assertNotIn(CLIENT_SECRET, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
