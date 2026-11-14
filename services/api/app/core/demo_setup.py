"""Explicit initialization and non-secret readiness checks for the demo."""

import json
import os
import sys

from app.core.config import Settings
from app.core.database import Database
from app.core.environment import load_environment
from app.core.migrate import apply, apply_identity_catalog, apply_video_indexes
from app.modules.curriculum.atlas_store import apply_academic_drafts
from app.modules.videos.publication import SupabaseVideoStorage


def main():
    load_environment()
    database = Database(Settings())
    try:
        if sys.argv[1] == "init":
            apply(database)
            apply_video_indexes(database)
            apply_identity_catalog(database)
            apply_academic_drafts(database.mongo)
            database.mongo.api_migrations.update_one(
                {"_id": "004_demo_connections_topics"},
                {"$set": {"schema_version": "1"}},
                upsert=True,
            )
        database.verify_ready()
        storage = SupabaseVideoStorage()
        storage.verify_private_bucket()
        storage.client.close()
        print(
            json.dumps(
                {
                    "atlas": "ready",
                    "storage": "private",
                    "configured": {
                        key: bool(os.getenv(key))
                        for key in [
                            "SUPABASE_URL",
                            "SUPABASE_PUBLISHABLE_KEY",
                            "CONNECTION_ENCRYPTION_KEY",
                            "GEMINI_API_KEY",
                            "GEMINI_MODEL",
                            "ANTHROPIC_API_KEY",
                            "ELEVENLABS_API_KEY",
                        ]
                    },
                }
            )
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
