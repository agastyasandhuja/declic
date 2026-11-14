"""Owned, bounded playback renewal with mocked Instagram and real MongoDB."""

import base64
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core import collections as tables
from app.core.credential_vault import CredentialVault
from app.core.import_instagram import import_connection
from app.core.social_connections import ConnectedCatalogService, SocialConnections
from app.core.time import utc_now
from app.modules.entertainment.repository import CatalogRepository
from app.modules.entertainment.service import CatalogFailure


@pytest.fixture
def connected(database, catalog, monkeypatch):
    if database.mongo is None:
        pytest.skip("Requires disposable API_TEST_MONGODB_URI")
    vault = CredentialVault(base64.b64encode(b"x" * 32).decode())
    connection = {
        "owner_user_id": "alice",
        "surface": "discover",
        "session": {"authorization_data": {"sessionid": "private-session"}},
    }
    import_connection(database, vault, connection)
    social = SocialConnections(database, vault)
    repository = CatalogRepository(database.mongo)
    clip = catalog.clips[0].model_dump(mode="json")
    clip.update(
        video_id="instagram_123",
        provider="instagram",
        provider_video_id="123",
        acquisition_mode="live",
    )
    clip["playback"].update(
        url="https://synthetic.cdninstagram.com/expired.mp4",
        expires_at=(utc_now() - timedelta(seconds=1)).isoformat(),
    )
    repository.replace_catalog({"user_id": "alice"}, [clip])
    fresh = deepcopy(clip)
    fresh["playback"].update(
        url="https://synthetic.cdninstagram.com/renewed.mp4",
        expires_at=(utc_now() + timedelta(minutes=5)).isoformat(),
    )
    calls = []
    provider = SimpleNamespace(
        client=SimpleNamespace(
            get_settings=lambda: {"authorization_data": {"sessionid": "renewed-private-session"}}
        ),
        close=lambda: None,
    )

    def renew(identifier):
        calls.append(identifier)
        return deepcopy(fresh)

    provider.refresh = renew
    from app.core import social_connections as module

    monkeypatch.setattr(module, "make_instagram_client", lambda *_: provider.client)
    monkeypatch.setattr(module, "InstagramReelsProvider", lambda *args, **kwargs: provider)
    service = ConnectedCatalogService(repository, social)
    return SimpleNamespace(
        database=database,
        repository=repository,
        social=social,
        service=service,
        clip=clip,
        fresh=fresh,
        calls=calls,
        provider=provider,
        connection=connection,
        vault=vault,
    )


def test_expired_owned_reel_renews_once_and_saves_encrypted_session(connected):
    c = connected
    playback = c.service.resolve_playback("instagram_123", {"user_id": "alice"})
    assert playback == c.fresh["playback"] and c.calls == ["123"]
    assert c.service.resolve_playback("instagram_123", {"user_id": "alice"}) == playback
    assert c.calls == ["123"]
    row = c.social.get("alice")
    assert row["refresh_version"] == 1 and "renewed-private-session" not in str(row)
    assert (
        c.vault.open("alice", "instagram", row["sealed"])["session"]["authorization_data"][
            "sessionid"
        ]
        == "renewed-private-session"
    )


def test_foreign_or_unknown_clip_never_reaches_provider(connected):
    c = connected
    for owner, video in [("bob", "instagram_123"), ("alice", "instagram_999")]:
        with pytest.raises(CatalogFailure) as error:
            c.service.resolve_playback(video, {"user_id": owner})
        assert error.value.status == 404
    assert c.calls == []


def test_disconnect_during_renewal_cannot_resurrect_catalog(connected):
    c = connected

    def revoke(identifier):
        c.social.disconnect("alice")
        return c.fresh

    c.provider.refresh = revoke
    with pytest.raises(CatalogFailure) as error:
        c.service.resolve_playback("instagram_123", {"user_id": "alice"})
    assert error.value.code == "INSTAGRAM_RECONNECT_REQUIRED"
    assert c.database.mongo.entertainment_catalogs.find_one({"user_id": "alice"}) is None
    assert c.social.get("alice")["sealed"] is None


def test_newer_background_refresh_fences_playback_publication(connected):
    c = connected

    def race(identifier):
        c.database.run(
            "alice",
            lambda tx: tx.update(
                tables.connections,
                {"user_id": "alice", "provider": "instagram"},
                {"refresh_version": 1},
            ),
        )
        return c.fresh

    c.provider.refresh = race
    with pytest.raises(CatalogFailure) as error:
        c.service.resolve_playback("instagram_123", {"user_id": "alice"})
    assert error.value.code == "INSTAGRAM_BUSY"
    assert c.repository.read_items({"user_id": "alice"})[0]["playback"] == c.clip["playback"]


def test_provider_rate_limit_is_saved_and_prevents_immediate_retry(connected):
    c = connected

    def limited(identifier):
        c.calls.append(identifier)
        error = CatalogFailure(503, "INSTAGRAM_RATE_LIMITED", "Wait")
        error.retry_after = 300
        raise error

    c.provider.refresh = limited
    for _ in range(2):
        with pytest.raises(CatalogFailure) as error:
            c.service.resolve_playback("instagram_123", {"user_id": "alice"})
        assert error.value.code == "INSTAGRAM_RATE_LIMITED"
    assert c.calls == ["123"]


def test_importing_replacement_clears_only_owners_old_catalog(connected):
    c = connected
    c.repository.replace_catalog({"user_id": "bob"}, [c.clip])
    import_connection(c.database, c.vault, c.connection)
    assert c.database.mongo.entertainment_catalogs.find_one({"user_id": "alice"}) is None
    assert c.database.mongo.entertainment_catalogs.find_one({"user_id": "bob"}) is not None


def test_generic_cached_clips_never_use_instagram_renewal(connected, catalog):
    c = connected
    fixture = catalog.clips[0].model_dump(mode="json")
    c.repository.replace_catalog({"user_id": "alice"}, [fixture])
    assert (
        c.service.resolve_playback(fixture["video_id"], {"user_id": "alice"}) == fixture["playback"]
    )
    fixture["playback"]["expires_at"] = (utc_now() - timedelta(seconds=1)).isoformat()
    c.repository.replace_catalog({"user_id": "alice"}, [fixture])
    with pytest.raises(CatalogFailure) as error:
        c.service.resolve_playback(fixture["video_id"], {"user_id": "alice"})
    assert error.value.code == "PLAYBACK_UNAVAILABLE"
    assert c.calls == []


def test_unexpired_revoked_url_is_renewed_on_explicit_retry(connected):
    c = connected
    c.clip["playback"]["expires_at"] = (utc_now() + timedelta(minutes=3)).isoformat()
    c.repository.replace_catalog({"user_id": "alice"}, [c.clip])
    assert c.service.resolve_playback("instagram_123", {"user_id": "alice"}) == c.fresh["playback"]
    assert c.calls == ["123"]


def test_importing_new_session_resets_playback_cooldown(connected):
    c = connected
    c.service.resolve_playback("instagram_123", {"user_id": "alice"})
    import_connection(c.database, c.vault, c.connection)
    row = c.social.get("alice")
    assert row["playback_refresh_after"] == 0
    assert row["playback_refreshed_video_id"] is None


def test_expired_generic_catalog_keeps_existing_not_found_contract(connected, catalog):
    c = connected
    fixture = catalog.clips[0].model_dump(mode="json")
    c.repository.replace_catalog({"user_id": "alice"}, [fixture])
    c.database.mongo.entertainment_catalogs.update_one(
        {"user_id": "alice"}, {"$set": {"expires_at": utc_now() - timedelta(seconds=1)}}
    )
    with pytest.raises(CatalogFailure) as error:
        c.service.resolve_playback(fixture["video_id"], {"user_id": "alice"})
    assert error.value.code == "CATALOG_NOT_FOUND"
    assert c.calls == []


def test_playback_renewal_fences_older_background_worker(connected):
    from app.workers.runner import JobContext

    c = connected
    connection_id = c.social.get("alice")["connection_id"]

    def read_page(_cursor):
        # The page worker captured version zero before an explicit retry won.
        c.service.resolve_playback("instagram_123", {"user_id": "alice"})
        return SimpleNamespace(items=[c.clip], next_cursor="older-cursor")

    c.provider.read_page = read_page
    result = c.social.refresh(
        JobContext("job", "alice", {"connection_id": connection_id}, lambda: True)
    )
    assert result == {"state": "superseded"}
    assert c.repository.read_items({"user_id": "alice"})[0]["playback"] == c.fresh["playback"]
    row = c.social.get("alice")
    assert row["refresh_version"] == 1
    assert c.vault.open("alice", "instagram", row["sealed"])["cursor"] is None


def test_expired_catalog_can_renew_known_instagram_clip_without_reconnect(connected):
    c = connected
    c.database.mongo.entertainment_catalogs.update_one(
        {"user_id": "alice"}, {"$set": {"expires_at": utc_now() - timedelta(seconds=1)}}
    )
    assert c.service.resolve_playback("instagram_123", {"user_id": "alice"}) == c.fresh["playback"]
    assert c.social.public("alice")["status"] == "connected"


@pytest.mark.parametrize("code", ["INSTAGRAM_UNAVAILABLE", "INSTAGRAM_RATE_LIMITED"])
def test_transient_media_failure_preserves_encrypted_login_session(connected, code):
    c = connected
    original = c.social.get("alice")

    def fail(_identifier):
        raise CatalogFailure(503, code, "Synthetic temporary failure")

    c.provider.refresh = fail
    with pytest.raises(CatalogFailure) as failure:
        c.service.resolve_playback("instagram_123", {"user_id": "alice"})
    assert failure.value.code == code
    after = c.social.get("alice")
    assert after["status"] == "connected"
    assert after["sealed"] == original["sealed"]
    assert after["connection_id"] == original["connection_id"]


def test_evicted_media_requires_feed_reload_not_instagram_reauthentication(connected):
    c = connected
    c.database.mongo.entertainment_catalogs.delete_one({"user_id": "alice"})
    with pytest.raises(CatalogFailure) as failure:
        c.service.resolve_playback("instagram_123", {"user_id": "alice"})
    assert failure.value.code == "VIDEO_NOT_FOUND"
    assert c.social.public("alice")["status"] == "connected"
    assert c.calls == []
