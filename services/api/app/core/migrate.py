"""Explicit, ordered API setup with optional owner-provided video indexes."""

import argparse

from app.core import collections
from app.core.config import Settings
from app.core.database import Database
from app.core.time import iso, utc_now

MIGRATION_ID = "001_api_learning_runtime"
VIDEO_MIGRATION_ID = "002_video_indexes"


def definitions():
    result = {}
    for name, keys in collections.KEYS.items():
        all_keys = set(keys)
        for unique_fields in collections.UNIQUE.get(name, []):
            all_keys.update(unique_fields)
        properties = {
            key: {"bsonType": "string", "minLength": 1, "maxLength": 256}
            for key in sorted(all_keys)
        }
        if name == collections.occurrences:
            properties["sequence"] = {"bsonType": ["int", "long"], "minimum": 1}
        if name in {
            collections.sessions,
            collections.occurrences,
            collections.pages,
            collections.quiz_instances,
            collections.attempts,
            collections.learning,
            collections.outbox,
        }:
            properties["data"] = {
                "bsonType": ["object", "null"] if name == collections.pages else "object"
            }
        if name == collections.quiz_instances:
            properties["state"] = {"enum": ["issued", "pending", "answered", "recovered"]}
        if name == collections.jobs:
            properties.update(
                {
                    "state": {
                        "enum": [
                            "queued",
                            "running",
                            "retry_wait",
                            "succeeded",
                            "failed",
                            "cancelled",
                        ]
                    },
                    "attempt_count": {"bsonType": ["int", "long"], "minimum": 0},
                    "max_attempts": {"bsonType": ["int", "long"], "minimum": 1, "maximum": 10},
                    "input_ref": {"bsonType": "object"},
                }
            )
        owner_field = "owner_user_id" if name == collections.jobs else "user_id"
        if name not in {collections.outbox, collections.processed}:
            properties[owner_field] = {"bsonType": "string", "minLength": 1, "maxLength": 128}
        required = list(properties)
        indexes = [
            {"keys": list(fields), "unique": True}
            for fields in [keys, *collections.UNIQUE.get(name, [])]
        ]
        indexes.extend(
            {"keys": list(fields), "unique": False} for fields in collections.INDEXES.get(name, [])
        )
        result[name] = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": required,
                    "properties": properties,
                }
            },
            "indexes": indexes,
        }
    return result


def apply(database: Database):
    if database.mongo is None:
        raise ValueError("This command initializes MongoDB, not the fixture adapter")
    db = database.mongo
    known = set(db.list_collection_names())
    for name, definition in definitions().items():
        if name not in known:
            db.create_collection(name, validator=definition["validator"], validationLevel="strict")
        else:
            db.command("collMod", name, validator=definition["validator"], validationLevel="strict")
        for spec in definition["indexes"]:
            db[name].create_index(
                [(key, 1) for key in spec["keys"]],
                unique=spec["unique"],
                name=("unique_" if spec["unique"] else "lookup_") + "__".join(spec["keys"]),
            )
    db.api_migrations.update_one(
        {"_id": MIGRATION_ID}, {"$set": {"applied_at": iso(utc_now())}}, upsert=True
    )


def apply_video_indexes(database: Database):
    """Delegate domain definitions to their owner; never copy or replace them."""
    if database.mongo is None:
        raise ValueError("Video index setup requires MongoDB")
    db = database.mongo
    if db.api_migrations.find_one({"_id": MIGRATION_ID}) is None:
        raise ValueError("Apply API migration 001 before video migration 002")
    from app.modules.videos.repository import AtlasVideoRepository

    # Index builds are repeatable, but not transactional. A failure leaves any
    # successful indexes in place and must not record the migration as applied.
    AtlasVideoRepository(db).initialize()
    db.api_migrations.update_one(
        {"_id": VIDEO_MIGRATION_ID}, {"$set": {"applied_at": iso(utc_now())}}, upsert=True
    )


def apply_ordered(database: Database, *, include_videos: bool = False):
    apply(database)
    if include_videos:
        apply_video_indexes(database)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", required=True)
    parser.add_argument(
        "--include-videos",
        action="store_true",
        help="Also apply the video owner's index setup after the API migration",
    )
    args = parser.parse_args()
    database = Database(Settings())
    try:
        apply_ordered(database, include_videos=args.include_videos)
        print("API collection validators and indexes applied")
        if args.include_videos:
            print("Video owner indexes applied")
    finally:
        database.close()
