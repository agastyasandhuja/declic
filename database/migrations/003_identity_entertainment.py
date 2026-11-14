"""Additive owner-provided profile/catalog schemas; refuses conflicting validators."""
from app.core.migrate import apply_identity_catalog


def upgrade(database):
    apply_identity_catalog(database)
