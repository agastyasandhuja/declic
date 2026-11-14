import base64
import json
import secrets

import pytest

from app.core.connections import Connections
from app.core.credential_vault import CredentialVault
from app.workers.queue import JobQueue


def test_vault_authenticates_owner_provider_and_ciphertext():
    vault = CredentialVault(base64.b64encode(secrets.token_bytes(32)).decode())
    ciphertext = vault.seal("alice", "canvas", {"token": "private-fixture"})
    assert vault.open("alice", "canvas", ciphertext) == {"token": "private-fixture"}
    for owner, provider in [("bob", "canvas"), ("alice", "instagram")]:
        with pytest.raises(ValueError):
            vault.open(owner, provider, ciphertext)
    altered = bytearray(base64.b64decode(ciphertext))
    altered[-1] ^= 1
    with pytest.raises(ValueError):
        vault.open("alice", "canvas", base64.b64encode(altered).decode())


def test_connection_survives_restart_is_private_and_revokes_queued_work(database):
    vault = CredentialVault(base64.b64encode(secrets.token_bytes(32)).decode())

    class Client:
        def __init__(self, origin, token):
            self.token = token

        def get(self, path):
            assert path == "/api/v1/users/self/profile"
            return {"id": 123}

    first = Connections(database, vault, "https://school.instructure.com", Client)
    result = first.connect("alice", "synthetic-personal-token")
    restored = Connections(database, vault, first.origin, Client)
    assert restored.public("alice")["status"] == "connected"
    assert restored.public("bob")["status"] == "disconnected"
    assert "synthetic-personal-token" not in json.dumps(restored.get("alice"))
    assert "sealed" not in result
    job = JobQueue(database).claim(["canvas.sync"])
    assert job["job_id"] == result["job_id"]
    assert "synthetic-personal-token" not in json.dumps(job)
    assert set(job["input_ref"]) == {"connection_id"}
    assert (
        restored.client("alice", result["connection_id"]).token.reveal()
        == "synthetic-personal-token"
    )
    restored.disconnect("alice")
    with pytest.raises(PermissionError):
        restored.client("alice", result["connection_id"])
    assert restored.get("alice")["sealed"] is None


def test_connect_retries_do_not_reverify_or_enqueue_twice(database):
    vault = CredentialVault(base64.b64encode(secrets.token_bytes(32)).decode())
    calls = []

    class Client:
        def __init__(self, *_):
            pass

        def get(self, path):
            calls.append(path)
            return {"id": 123}

    connections = Connections(database, vault, "https://school.instructure.com", Client)
    first = connections.connect("alice", "private-fixture-token", "retry-key")
    assert connections.connect("alice", "private-fixture-token", "retry-key") == first
    assert len(calls) == 1
    from app.core.errors import APIError

    with pytest.raises(APIError):
        connections.connect("alice", "different-private-token", "retry-key")
