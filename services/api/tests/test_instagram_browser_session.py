"""Authenticated cookie handoff with a mocked Instagram SDK; no live login."""

import pytest
from test_social_connections import setup_social

from app.core import collections as tables
from app.core.errors import APIError
from app.core.social_connections import BrowserSessionLogin, Login, create_router

COOKIE = "123456789%3Asynthetic_browser_cookie_never_log"


def browser_social(database, monkeypatch):
    social, provider = setup_social(database, monkeypatch)
    calls = []
    provider.client.login = lambda *_args, **_kwargs: pytest.fail(
        "Cookie login must not use passwords"
    )
    provider.client.login_by_sessionid = lambda cookie: calls.append(cookie) or True
    provider.client.get_settings = lambda: {
        "authorization_data": {"sessionid": COOKIE, "ds_user_id": "123"},
        "cookies": {"sessionid": COOKIE},
        "uuids": {"phone_id": "synthetic-device"},
    }
    return social, provider, calls


def test_verified_browser_cookie_is_owner_bound_encrypted_and_cooldown_limited(
    database, monkeypatch
):
    social, _, calls = browser_social(database, monkeypatch)
    body = BrowserSessionLogin(username="demo", session_id=COOKIE)
    assert COOKIE not in repr(body)
    assert social.connect("alice", body)["status"] == "connected"
    assert calls == [COOKIE]
    row = social.get("alice")
    assert COOKIE not in str(row) and COOKIE not in str(social.public("alice"))
    saved = social.vault.open("alice", "instagram", row["sealed"])
    assert saved["session"]["authorization_data"]["sessionid"] == COOKIE
    assert saved["surface"] == "discover"
    assert social.get("bob") is None
    with pytest.raises(APIError) as failure:
        social.connect("alice", body)
    assert failure.value.code == "LOGIN_COOLDOWN" and calls == [COOKIE]


def test_wrong_account_cookie_cannot_replace_working_connection(database, monkeypatch):
    social, provider = setup_social(database, monkeypatch)
    social.connect("alice", Login(username="demo", password="synthetic-password"))
    before = social.get("alice")
    database.run(
        "alice",
        lambda tx: tx.update(
            tables.connections, {"user_id": "alice", "provider": "instagram"}, {"last_attempt": 0}
        ),
    )
    provider.client.login_by_sessionid = lambda _cookie: True
    provider.client._send_private_request = lambda *_args, **_kwargs: {
        "user": {"pk": 123, "username": "different_account"}
    }
    with pytest.raises(APIError) as failure:
        social.connect("alice", BrowserSessionLogin(username="demo", session_id=COOKIE))
    assert failure.value.code == "INSTAGRAM_SESSION_ACCOUNT_MISMATCH"
    after = social.get("alice")
    assert after["status"] == "connected" and after["sealed"] == before["sealed"]
    assert after["connection_id"] == before["connection_id"]


def test_disconnect_during_cookie_verification_cannot_be_undone(database, monkeypatch):
    social, provider, _ = browser_social(database, monkeypatch)

    def disconnected(_cookie):
        database.run(
            "alice",
            lambda tx: tx.update(
                tables.connections,
                {"user_id": "alice", "provider": "instagram"},
                {"status": "disconnected", "sealed": None, "attempt_id": "newer-disconnect"},
            ),
        )
        return True

    provider.client.login_by_sessionid = disconnected
    with pytest.raises(APIError) as failure:
        social.connect("alice", BrowserSessionLogin(username="demo", session_id=COOKIE))
    assert failure.value.code == "CONNECTION_CHANGED"
    assert social.get("alice")["status"] == "disconnected"
    assert social.get("alice")["sealed"] is None


def test_cookie_endpoint_requires_app_auth_and_rejects_secret_bearing_extra_fields(
    app, client, database, monkeypatch
):
    social, _, calls = browser_social(database, monkeypatch)
    app.include_router(create_router(social))
    route = "/v1/instagram/browser-session"
    payload = {"username": "demo", "session_id": COOKIE}
    assert client.post(route, json=payload, headers={"Authorization": ""}).status_code == 401
    invalid = client.post(route, json={**payload, "user_id": "bob"})
    assert invalid.status_code == 422 and COOKIE not in invalid.text and calls == []
    short = client.post(route, json={**payload, "session_id": "private-short"})
    assert short.status_code == 422 and "private-short" not in short.text
    result = client.post(route, json=payload)
    assert result.status_code == 202 and result.json()["status"] == "connected"
    assert COOKIE not in result.text and calls == [COOKIE]
    assert social.get("user_demo_01")["status"] == "connected"
    assert social.get("bob") is None
