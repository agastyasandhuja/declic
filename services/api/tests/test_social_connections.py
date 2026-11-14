from types import SimpleNamespace

import pytest

from app.core import collections as tables
from app.core.credential_vault import CredentialVault
from app.core.errors import APIError
from app.core.social_connections import Login, SocialConnections
from app.modules.entertainment.service import CatalogFailure
from app.workers.runner import JobContext


def setup_social(database, monkeypatch):
    import base64
    from app.core import social_connections as module

    vault = CredentialVault(base64.b64encode(b"x" * 32).decode())
    social = SocialConnections(database, vault)
    client = SimpleNamespace(
        login=lambda *args, **kwargs: True,
        get_settings=lambda: {"authorization_data": {"sessionid": "private-session"}},
    )
    provider = SimpleNamespace(client=client, close=lambda: None)
    monkeypatch.setattr(module, "make_instagram_client", lambda *args: client)
    monkeypatch.setattr(module, "InstagramReelsProvider", lambda _: provider)
    return social, provider


def test_login_saves_encrypted_session_not_password_and_limits_attempts(database, monkeypatch):
    social, _ = setup_social(database, monkeypatch)
    assert (
        social.connect("alice", Login(username="demo", password="private-password"))["status"]
        == "connected"
    )
    row = social.get("alice")
    assert "private-session" not in str(row) and "private-password" not in str(row)
    assert (
        social.vault.open("alice", "instagram", row["sealed"])["session"]["authorization_data"][
            "sessionid"
        ]
        == "private-session"
    )
    assert social.public("bob")["status"] == "disconnected"
    with pytest.raises(APIError) as error:
        social.connect("alice", Login(username="demo", password="private-password"))
    assert error.value.status == 429


def test_refresh_does_not_publish_after_disconnect_or_lost_lease(database, monkeypatch):
    social, provider = setup_social(database, monkeypatch)
    social.connect("alice", Login(username="demo", password="private-password"))
    row = social.get("alice")

    def read(_):
        database.run(
            "alice",
            lambda tx: tx.update(
                tables.connections,
                {"user_id": "alice", "provider": "instagram"},
                {"status": "disconnected"},
            ),
        )
        return SimpleNamespace(items=[], next_cursor=None)

    provider.read_page = read
    context = JobContext("job", "alice", {"connection_id": row["connection_id"]}, lambda: True)
    assert social.refresh(context) == {"state": "revoked"}
    database.run(
        "alice",
        lambda tx: tx.update(
            tables.connections,
            {"user_id": "alice", "provider": "instagram"},
            {"status": "connected"},
        ),
    )
    with pytest.raises(RuntimeError, match="Lease lost"):
        social.refresh(JobContext("job", "alice", context.input_ref, lambda: False))


def test_rate_limit_records_cooldown_without_retrying_provider(database, monkeypatch):
    social, provider = setup_social(database, monkeypatch)
    social.connect("alice", Login(username="demo", password="private-password"))
    row = social.get("alice")
    calls = []

    def limited(_):
        calls.append(1)
        error = CatalogFailure(503, "INSTAGRAM_RATE_LIMITED", "Wait")
        error.retry_after = 300
        raise error

    provider.read_page = limited
    context = JobContext("job", "alice", {"connection_id": row["connection_id"]}, lambda: True)
    assert social.refresh(context)["state"] == "cooldown"
    assert social.refresh(context)["state"] == "cooldown"
    assert len(calls) == 1
