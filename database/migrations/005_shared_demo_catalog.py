"""Add the bounded shared generic demo registry; existing accounts remain opted out.

Run using the configured API runtime after reviewing the generic catalog manifest.
This only applies validators/indexes; it publishes no assets and changes no flags.
"""
from app.core.migrate import apply


def upgrade(database):
    apply(database)
    database.mongo.api_migrations.update_one(
        {"_id": "005_shared_demo_catalog"},
        {"$set": {"schema_version": "1"}}, upsert=True,
    )
