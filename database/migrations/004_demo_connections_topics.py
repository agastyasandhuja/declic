"""Add private provider connections, semantic topic cache, bindings and quiz bank.

Run through scripts/run-demo.py init. Existing validators remain unchanged.
"""

from app.core.migrate import apply
from app.modules.curriculum.atlas_store import apply_academic_drafts


def upgrade(database):
    apply(database)
    apply_academic_drafts(database.mongo)
    database.mongo.api_migrations.update_one(
        {"_id": "004_demo_connections_topics"},
        {"$set": {"schema_version": "1"}},
        upsert=True,
    )
