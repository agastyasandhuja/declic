"""Synthetic restart checks; no Instagram or Supabase requests are permitted."""

import base64
import json
import socket
from unittest.mock import patch

import pytest

from app.core.credential_vault import CredentialVault
from app.core.database import Database
from app.core.import_instagram import import_connection
from app.core.social_connections import SocialConnections
from app.modules.entertainment.instagram import InstagramReelsProvider, make_instagram_client
from app.modules.entertainment.instagram_connection import (
    SESSION_FIELDS,
    load_connection,
    save_connection,
)

OWNER = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
SESSION = "123456789%3Asynthetic_session_for_offline_restoration"
KEY = base64.b64encode(b"s" * 32).decode()


def session_settings():
    return {
        "authorization_data": {"ds_user_id": "123456789", "sessionid": SESSION},
        "cookies": {"sessionid": SESSION, "ds_user_id": "123456789", "csrftoken": "synthetic-csrf"},
        "uuids": {
            "phone_id": "00000000-0000-4000-8000-000000000003",
            "uuid": "00000000-0000-4000-8000-000000000004",
            "android_device_id": "android-0123456789abcdef",
        },
        "last_login": 1730000000.0,
    }


def test_real_pinned_sdk_restores_saved_session_and_device_without_login(tmp_path):
    path = tmp_path / "private" / "connection.json"
    save_connection(path, OWNER, session_settings(), "discover")
    saved = load_connection(path)
    clients = []
    with patch.object(socket.socket, "connect", side_effect=AssertionError("Unexpected network")):
        try:
            first = make_instagram_client(saved["session"])
            clients.append(first)
            snapshot = {
                key: value for key, value in first.get_settings().items() if key in SESSION_FIELDS
            }
            # Model a separate process: only JSON-serialized settings survive.
            restored = make_instagram_client(json.loads(json.dumps(snapshot)))
            clients.append(restored)
            assert restored.user_id == first.user_id == 123456789
            assert restored.sessionid == first.sessionid == SESSION
            assert restored.private.cookies.get("csrftoken") == "synthetic-csrf"
            assert restored.uuid == first.uuid == saved["session"]["uuids"]["uuid"]
            assert restored.phone_id == first.phone_id == saved["session"]["uuids"]["phone_id"]
            assert restored.last_login == saved["session"]["last_login"]
            assert (
                restored.private.headers["Authorization"] == first.private.headers["Authorization"]
            )
        finally:
            for client in clients:
                InstagramReelsProvider(client).close()


def test_imported_connection_survives_fresh_database_and_vault_instances(database):
    vault = CredentialVault(KEY)
    import_connection(
        database,
        vault,
        {
            "owner_user_id": OWNER,
            "surface": "connected",
            "session": session_settings(),
        },
    )
    first = SocialConnections(database, vault).get(OWNER)
    restarted_database = Database(database.settings)
    try:
        restarted = SocialConnections(restarted_database, CredentialVault(KEY))
        row = restarted.get(OWNER)
        assert row["connection_id"] == first["connection_id"]
        assert restarted.public(OWNER)["status"] == "connected"
        assert restarted.get(OTHER) is None
        restored = restarted.vault.open(OWNER, "instagram", row["sealed"])
        assert restored["surface"] == "connected"
        assert restored["session"] == session_settings()
        assert SESSION not in json.dumps(row)
        with pytest.raises(ValueError):
            restarted.vault.open(OTHER, "instagram", row["sealed"])
        if database.mongo is not None:
            restarted.disconnect(OWNER)
            assert SocialConnections(database, CredentialVault(KEY)).get(OWNER)["sealed"] is None
    finally:
        restarted_database.close()
