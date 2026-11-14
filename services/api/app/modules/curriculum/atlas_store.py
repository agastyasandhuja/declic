"""MongoDB Atlas persistence for academic profiles and lesson plans (owner: Amogh).

The caller injects a PyMongo Database (core's Database.mongo). Every query is
filtered by user_id, and documents whose embedded owner differs are refused,
so one user can never read or overwrite another user's academic data.

Install the collections (additive, never drops anything):

    PYTHONPATH=services/api python -m app.modules.curriculum.atlas_store --apply --env-file services/api/.env
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[5] / "database" / "domains" / "academics" / "manifest.json"
PROFILES, REVISIONS, PLANS = "academic_profiles", "academic_profile_revisions", "academic_lesson_plans"


def _now():
    return datetime.now(timezone.utc)


class AtlasAcademicStore:
    def __init__(self, database) -> None:
        self._db = database

    def load_profile(self, user_id: str) -> dict | None:
        _require(user_id)
        doc = self._db[PROFILES].find_one({"user_id": user_id})
        if not doc or doc["profile"].get("user_id") != user_id:
            return None
        return doc["profile"]

    def latest_revision(self, user_id: str) -> int:
        return (self.load_profile(user_id) or {}).get("revision", 0)

    def save_profile(self, user_id: str, profile: dict) -> None:
        """Store a revision snapshot and make it the user's current profile."""
        _require(user_id)
        if profile.get("user_id") != user_id:
            raise PermissionError("profile owner mismatch")
        doc = {"schema_version": "1", "user_id": user_id, "revision": int(profile["revision"]),
               "profile": profile, "updated_at": _now()}
        self._db[REVISIONS].replace_one({"user_id": user_id, "revision": doc["revision"]},
                                        dict(doc), upsert=True)
        self._db[PROFILES].replace_one({"user_id": user_id}, dict(doc), upsert=True)

    def save_plans(self, user_id: str, plans: list[dict]) -> None:
        _require(user_id)
        if any(plan.get("user_id") != user_id for plan in plans):
            raise PermissionError("plan owner mismatch")
        self._db[PLANS].replace_one(
            {"user_id": user_id},
            {"schema_version": "1", "user_id": user_id, "plans": plans, "updated_at": _now()},
            upsert=True)

    def load_plans(self, user_id: str) -> list[dict]:
        _require(user_id)
        doc = self._db[PLANS].find_one({"user_id": user_id})
        return [p for p in (doc or {}).get("plans", []) if p.get("user_id") == user_id]


def _require(user_id: str) -> None:
    if not user_id:
        raise ValueError("a user id is required")


def apply_academic_drafts(database) -> list[str]:
    """Create missing academics collections/indexes. Refuses a conflicting validator."""
    manifest = json.loads(MANIFEST.read_text())
    created = []
    for spec in manifest["collections"]:
        existing = list(database.list_collections(filter={"name": spec["name"]}))
        if not existing:
            database.create_collection(spec["name"], validator=spec["validator"],
                                       validationLevel="strict", validationAction="error")
            created.append(spec["name"])
        elif existing[0]["options"].get("validator") != spec["validator"]:
            raise RuntimeError(f"{spec['name']}: existing validator differs; plan a migration.")
        for index in spec["indexes"]:
            database[spec["name"]].create_index(
                [tuple(key) for key in index["keys"]],
                **{k: v for k, v in index.items() if k != "keys"})
    return created


def read_mongo_env(env_file: Path | None) -> tuple[str, str]:
    """MONGODB_URI / MONGODB_DATABASE from the process, else from the env file."""
    values = {}
    if env_file and env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    uri = os.environ.get("MONGODB_URI") or values.get("MONGODB_URI")
    name = os.environ.get("MONGODB_DATABASE") or values.get("MONGODB_DATABASE") or "hackumass"
    if not uri:
        raise SystemExit("MONGODB_URI is not configured (services/api/.env)")
    if name in ("admin", "local", "config"):
        raise SystemExit("choose an application database")
    return uri, name


def connect(env_file: Path | None):
    from pymongo import MongoClient

    uri, name = read_mongo_env(env_file)
    client = MongoClient(uri, serverSelectionTimeoutMS=10000, timeoutMS=20000)
    return client, client[name]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="create missing academics collections/indexes")
    parser.add_argument("--env-file", type=Path, default=Path("services/api/.env"))
    args = parser.parse_args()
    if not args.apply:
        parser.error("explicit --apply required")
    client, database = connect(args.env_file)
    with client:
        created = apply_academic_drafts(database)
    print(f"academics drafts applied to '{database.name}'; created: {created or 'none (already present)'}")
