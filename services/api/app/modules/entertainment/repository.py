"""Bounded private catalog snapshots; no raw provider credentials or media bytes."""
from functools import wraps
from pymongo.errors import PyMongoError
from jsonschema.exceptions import ValidationError

from datetime import datetime, timedelta, timezone

from .service import CatalogFailure, normalized_items
from .pagination import batch_revision


def storage_errors(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except PyMongoError:
            raise CatalogFailure(503, 'CATALOG_UNAVAILABLE', 'Catalog storage is unavailable. Retry shortly.') from None
    return call


class CatalogRepository:
    def __init__(self, database, clock=None):
        self.collection = database['entertainment_catalogs']
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @storage_errors
    def replace_catalog(self, user, items, ttl_seconds=3600):
        if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 86400:
            raise ValueError('Catalog retention must be 60–86400 seconds.')
        items = normalized_items(items)
        now = self.clock()
        revision = batch_revision(items)
        # One bounded document is one atomic publication; readers cannot mix batches.
        self.collection.replace_one({'user_id': user['user_id']}, {
            'schema_version': '1', 'user_id': user['user_id'], 'revision': revision,
            'items': items, 'updated_at': now, 'expires_at': now + timedelta(seconds=ttl_seconds),
        }, upsert=True)
        return {'revision': revision, 'count': len(items)}

    @storage_errors
    def read_items(self, user):
        # TTL cleanup is asynchronous; the expiry predicate is the access boundary.
        document = self.collection.find_one({'user_id': user['user_id'], 'expires_at': {'$gt': self.clock()}}, {'_id': 0, 'items': 1})
        if document is None:
            raise CatalogFailure(404, 'CATALOG_NOT_FOUND', 'No current catalog is connected to this account.')
        try:
            return normalized_items(document['items'])
        except (ValueError, TypeError, KeyError, ValidationError):
            raise CatalogFailure(503, 'CATALOG_UNAVAILABLE', 'Stored catalog metadata is invalid. Retrieve a fresh batch.') from None
