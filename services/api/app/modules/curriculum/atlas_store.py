"""MongoDB Atlas persistence for academic profiles and lesson plans (owner: Amogh).

The caller injects a PyMongo Database (core's Database.mongo). Every query is
filtered by user_id, and documents whose embedded owner differs are refused,
so one user can never read or overwrite another user's academic data.

Install the collections (additive, never drops anything):

    PYTHONPATH=services/api python -m app.modules.curriculum.atlas_store --apply
        --env-file services/api/.env
"""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .corrections import RevisionConflict

MANIFEST = (
    Path(__file__).resolve().parents[5] / "database" / "domains" / "academics" / "manifest.json"
)
PROFILES, REVISIONS, PLANS = (
    "academic_profiles",
    "academic_profile_revisions",
    "academic_lesson_plans",
)


def _now():
    return datetime.now(UTC)


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

    def save_profile(self, user_id: str, profile: dict, *, publication_guard=None) -> None:
        """Atomically append an immutable snapshot and advance exactly one revision.

        Model work happens before this transaction. Competing imports/corrections
        cannot replace the winner, and retrying an identical committed snapshot is
        safe after an ambiguous connection failure.
        """
        _require(user_id)
        if profile.get("user_id") != user_id:
            raise PermissionError("profile owner mismatch")
        revision = profile.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError("profile revision must be a positive integer")
        snapshot = deepcopy(profile)
        plans = snapshot.get("_plans", [])
        if any(
            plan.get("user_id") != user_id or plan.get("profile_revision") != revision
            for plan in plans
        ):
            raise PermissionError("profile plans must belong to the same owner and revision")
        doc = {
            "schema_version": "1",
            "user_id": user_id,
            "revision": revision,
            "profile": snapshot,
            "updated_at": _now(),
        }

        def publish(session):
            current = self._db[PROFILES].find_one({"user_id": user_id}, session=session)
            if current and current["profile"].get("user_id") != user_id:
                raise PermissionError("profile owner mismatch")
            if current and current["revision"] == revision and current["profile"] == snapshot:
                return
            if (current["revision"] if current else 0) != revision - 1:
                raise RevisionConflict("profile changed during preparation; retry")
            if publication_guard is not None and not publication_guard():
                raise PermissionError("import no longer authorized")
            if current is None:
                self._db[PROFILES].insert_one(dict(doc), session=session)
            else:
                result = self._db[PROFILES].replace_one(
                    {"user_id": user_id, "revision": revision - 1}, dict(doc), session=session
                )
                if result.matched_count != 1:
                    raise RevisionConflict("profile changed during preparation; retry")
            self._db[REVISIONS].insert_one(dict(doc), session=session)

        try:
            with self._db.client.start_session() as session:
                session.with_transaction(
                    publish,
                    read_concern=ReadConcern("snapshot"),
                    write_concern=WriteConcern("majority"),
                )
        except DuplicateKeyError:
            # Initial-profile races and a conflicting immutable snapshot must
            # never silently overwrite another completed import.
            raise RevisionConflict("profile revision already exists; retry") from None

    def save_plans(self, user_id: str, plans: list[dict]) -> None:
        _require(user_id)
        if any(plan.get("user_id") != user_id for plan in plans):
            raise PermissionError("plan owner mismatch")
        self._db[PLANS].replace_one(
            {"user_id": user_id},
            {"schema_version": "1", "user_id": user_id, "plans": plans, "updated_at": _now()},
            upsert=True,
        )

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
            database.create_collection(
                spec["name"],
                validator=spec["validator"],
                validationLevel="strict",
                validationAction="error",
            )
            created.append(spec["name"])
        elif existing[0]["options"].get("validator") != spec["validator"]:
            raise RuntimeError(f"{spec['name']}: existing validator differs; plan a migration.")
        for index in spec["indexes"]:
            database[spec["name"]].create_index(
                [tuple(key) for key in index["keys"]],
                **{k: v for k, v in index.items() if k != "keys"},
            )
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
    parser.add_argument(
        "--apply", action="store_true", help="create missing academics collections/indexes"
    )
    parser.add_argument("--env-file", type=Path, default=Path("services/api/.env"))
    args = parser.parse_args()
    if not args.apply:
        parser.error("explicit --apply required")
    client, database = connect(args.env_file)
    with client:
        created = apply_academic_drafts(database)
    print(
        f"academics drafts applied to '{database.name}'; "
        f"created: {created or 'none (already present)'}"
    )
