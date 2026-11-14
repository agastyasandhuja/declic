"""Explicit local handoff of a verified, app-owner-bound Instagram session."""

import json
import os
import sys
from pathlib import Path

import httpx

from app.core import collections as tables
from app.core.config import Settings
from app.core.credential_vault import CredentialVault
from app.core.database import Database
from app.core.environment import ROOT, load_environment
from app.core.time import iso, new_id, utc_now
from app.modules.entertainment.instagram_connection import load_connection
from app.workers.queue import enqueue


def import_connection(database, vault, connection):
    owner = connection["owner_user_id"]
    identifier = new_id()
    sealed = vault.seal(
        owner,
        "instagram",
        {"session": connection["session"], "cursor": None, "surface": connection["surface"]},
    )

    def save(tx):
        query = {"user_id": owner, "provider": "instagram"}
        tx.insert_if_absent(tables.connections, query, list(query))
        tx.update(
            tables.connections,
            query,
            {
                "status": "connected",
                "sealed": sealed,
                "connection_id": identifier,
                "attempt_id": new_id(),
                "refresh_version": 0,
                "retry_after": 0,
                "connected_at": iso(utc_now()),
                "last_sync_at": None,
            },
        )
        enqueue(
            tx,
            owner_user_id=owner,
            job_type="instagram.refresh",
            dedupe_key=identifier,
            input_ref={"connection_id": identifier},
        )

    database.run(owner, save)


def main():
    load_environment()
    path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".local/instagram-live/connection.json"
    )
    connection = load_connection(path)  # Enforces owned regular file, mode 0600 and UUID.
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        response = client.get(
            os.environ["SUPABASE_URL"].rstrip("/")
            + "/auth/v1/admin/users/"
            + connection["owner_user_id"],
            headers={"apikey": key, "Authorization": "Bearer " + key},
        )
        if response.status_code != 200 or response.json().get("id") != connection["owner_user_id"]:
            raise RuntimeError("Saved connection is not bound to a user in this Supabase project")
    database = Database(Settings())
    try:
        database.verify_ready()
        import_connection(
            database, CredentialVault(os.environ["CONNECTION_ENCRYPTION_KEY"]), connection
        )
        print(
            json.dumps({"instagram_imported": True, "owner_verified": True, "refresh_queued": True})
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
