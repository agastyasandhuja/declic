"""Ordered API-only MongoDB setup; run from services/api via app.core.migrate.

Source validator/index artifact: database/domains/learning/api-runtime-v1.json.
This migration never touches identity, academics, entertainment, or video collections.
"""

from app.core.migrate import apply


def upgrade(database):
    apply(database)
