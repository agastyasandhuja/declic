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
        user_id=123,
        authorization="synthetic",
        _send_private_request=lambda *args, **kwargs: {"user": {"pk": 123, "username": "demo"}},
        get_settings=lambda: {
            "authorization_data": {"sessionid": "private-session"},
            "uuids": {"phone_id": "synthetic-device"},
        },
    )
    provider = SimpleNamespace(client=client, close=lambda: None)
    monkeypatch.setattr(module, "make_instagram_client", lambda *args: client)
    monkeypatch.setattr(module, "InstagramReelsProvider", lambda _, **kwargs: provider)
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


def test_api_login_never_reuses_saved_account_or_prompts_terminal(database, monkeypatch):
    from app.core import social_connections as module

    social, provider = setup_social(database, monkeypatch)
    social.connect("alice", Login(username="demo", password="private-password"))
    database.run(
        "alice",
        lambda tx: tx.update(
            tables.connections, {"user_id": "alice", "provider": "instagram"}, {"last_attempt": 0}
        ),
    )
    settings = []
    monkeypatch.setattr(
        module, "make_instagram_client", lambda saved: settings.append(saved) or provider.client
    )

    def challenge(client, username, password, report, **callbacks):
        assert callbacks["expected_username"] == username
        assert callbacks["choose_method"]("choose") == "totp"
        callbacks["read_code"]("code")
        pytest.fail("Missing code must not continue or prompt Terminal")

    monkeypatch.setattr(module, "login_interactively", challenge)
    with pytest.raises(APIError) as error:
        social.connect("alice", Login(username="demo", password="private-password"))
    assert error.value.code == "INSTAGRAM_TWO_FACTOR_REQUIRED"
    assert settings[0]["authorization_data"] == {}
    assert not settings[0].get("cookies", {}).get("sessionid")
    assert social.public("alice")["status"] == "reconnect_required"


def test_api_login_rejects_canonical_username_mismatch(database, monkeypatch):
    social, provider = setup_social(database, monkeypatch)
    provider.client._send_private_request = lambda *args, **kwargs: {
        "user": {"pk": 123, "username": "different"}
    }
    with pytest.raises(APIError) as error:
        social.connect("alice", Login(username="demo", password="private-password"))
    assert error.value.code == "INSTAGRAM_SESSION_ACCOUNT_MISMATCH"
    assert social.public("alice")["status"] == "reconnect_required"


def test_api_rejects_sms_continuation_before_delivery_or_submitting_prior_code(
    database, monkeypatch
):
    social, provider = setup_social(database, monkeypatch)

    class TwoFactorRequired(Exception):
        pass

    def login(*args, **kwargs):
        raise TwoFactorRequired("synthetic challenge")

    client = provider.client
    client.login = login
    client._extract_two_step_verification_context = lambda source: "synthetic-context"
    client._login_response_bool = lambda source, key: key == "sms_two_factor_on"

    def unexpected(*args, **kwargs):
        pytest.fail("API must not send a new SMS or submit a code from a prior login context")

    client.bloks_two_step_verification_entrypoint = unexpected
    client.bloks_two_step_verification_method_picker = unexpected
    client.bloks_two_step_verification_select_method = unexpected
    client.bloks_two_step_verification_verify_code = unexpected
    with pytest.raises(APIError) as error:
        social.connect(
            "alice", Login(username="demo", password="private-password", verification_code="123456")
        )
    assert error.value.code == "INSTAGRAM_LOCAL_VERIFICATION_REQUIRED"
    assert social.public("alice")["status"] == "reconnect_required"


def test_successful_reconnect_resets_playback_cooldown(database, monkeypatch):
    social, _ = setup_social(database, monkeypatch)
    social.connect("alice", Login(username="demo", password="private-password"))
    database.run(
        "alice",
        lambda tx: tx.update(
            tables.connections,
            {"user_id": "alice", "provider": "instagram"},
            {
                "last_attempt": 0,
                "playback_refresh_after": 9999999999,
                "playback_refreshed_video_id": "instagram_123",
            },
        ),
    )
    social.connect("alice", Login(username="demo", password="private-password"))
    row = social.get("alice")
    assert row["playback_refresh_after"] == 0
    assert row["playback_refreshed_video_id"] is None
