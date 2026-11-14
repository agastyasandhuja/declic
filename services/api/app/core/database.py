"""MongoDB persistence plus an explicit SQLite JSON-document fixture adapter.

The local fake proves application behavior, not MongoDB transaction correctness.
Callbacks passed to run() may be retried and must not have external side effects.
"""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from app.core import collections
from app.core.config import Settings


def _key(values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class WriteResult:
    rowcount: int


class UnitOfWork:
    """Filters are trusted server dictionaries; never accept a client query object."""

    def __init__(self, mongo=None, session=None, local=None):
        self.mongo, self.session, self.local = mongo, session, local

    def find(self, name, query=None, *, sort=None, limit=None):
        if name not in collections.KEYS:
            raise ValueError("Collection is not owned by this runtime")
        query = query or {}
        if self.mongo is not None:
            cursor = self.mongo[name].find(query, {"_id": 0}, session=self.session)
            if sort:
                cursor = cursor.sort(sort)
            if limit is not None:
                cursor = cursor.limit(limit)
            return list(cursor)
        documents = [
            json.loads(r[0])
            for r in self.local.execute("SELECT data FROM documents WHERE collection = ?", (name,))
        ]
        documents = [d for d in documents if _matches(d, query)]
        for key, direction in reversed(sort or []):
            documents.sort(key=lambda d: _value(d, key), reverse=direction < 0)
        return documents[:limit] if limit is not None else documents

    def find_one(self, name, query=None, *, sort=None):
        rows = self.find(name, query, sort=sort, limit=1)
        return rows[0] if rows else None

    def value(self, name, field, query=None, *, sort=None):
        row = self.find_one(name, query, sort=sort)
        return row[field] if row is not None else None

    def values(self, name, field, query=None, *, sort=None, limit=None):
        return [r[field] for r in self.find(name, query, sort=sort, limit=limit)]

    def count(self, name, query=None):
        if self.mongo is not None:
            return self.mongo[name].count_documents(query or {}, session=self.session)
        return len(self.find(name, query))

    def insert(self, name, values):
        if name not in collections.KEYS:
            raise ValueError("Unknown collection")
        if self.mongo is not None:
            self.mongo[name].insert_one(dict(values), session=self.session)
        else:
            key = _key([values[k] for k in collections.KEYS[name]])
            self.local.execute(
                "INSERT INTO documents VALUES (?, ?, ?)",
                (name, key, json.dumps(values, allow_nan=False)),
            )
            for fields in [collections.KEYS[name], *collections.UNIQUE.get(name, [])]:
                self.local.execute(
                    "INSERT INTO unique_keys VALUES (?, ?, ?, ?)",
                    (name, ":".join(fields), _key([values[k] for k in fields]), key),
                )

    def insert_if_absent(self, name, values, keys):
        query = {key: values[key] for key in keys}
        if self.mongo is not None:
            self.mongo[name].update_one(
                query, {"$setOnInsert": dict(values)}, upsert=True, session=self.session
            )
        elif self.find_one(name, query) is None:
            self.insert(name, values)

    def update(self, name, query, values):
        if self.mongo is not None:
            result = self.mongo[name].update_many(query, {"$set": values}, session=self.session)
            return WriteResult(result.matched_count)
        rows = self.find(name, query)
        for row in rows:
            key = _key([row[k] for k in collections.KEYS[name]])
            for fields in [collections.KEYS[name], *collections.UNIQUE.get(name, [])]:
                if any(k in values and values[k] != row[k] for k in fields):
                    raise ValueError("Business keys are immutable")
            row.update(values)
            self.local.execute(
                "UPDATE documents SET data = ? WHERE collection = ? AND key = ?",
                (json.dumps(row, allow_nan=False), name, key),
            )
        return WriteResult(len(rows))


def _value(document, key):
    value = document
    for part in key.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def _matches(document, query):
    """Minimal test-only filter evaluator; unsupported operators fail loudly."""
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(document, q) for q in expected):
                return False
            continue
        if key == "$and":
            if not all(_matches(document, q) for q in expected):
                return False
            continue
        actual = _value(document, key)
        if isinstance(expected, dict):
            for op, target in expected.items():
                if op == "$in":
                    result = actual in target
                elif op == "$nin":
                    result = actual not in target
                elif op == "$ne":
                    result = actual != target
                elif op == "$lt":
                    result = actual is not None and actual < target
                elif op == "$lte":
                    result = actual is not None and actual <= target
                elif op == "$gt":
                    result = actual is not None and actual > target
                elif op == "$gte":
                    result = actual is not None and actual >= target
                else:
                    raise ValueError("Unsupported fixture query operator")
                if not result:
                    return False
        elif actual != expected:
            return False
    return True


def insert_ignore(conn, collection, values, keys):
    conn.insert_if_absent(collection, values, keys)


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self.mongo = None
        if settings.persistence == "mongodb":
            self.client = MongoClient(
                settings.mongodb_uri.get_secret_value(),
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                timeoutMS=10000,
                tz_aware=True,
            )
            self.mongo = self.client[settings.mongodb_database]

    def initialize_local(self):
        if self.settings.persistence != "fixture_sqlite":
            return
        path = self.settings.fixture_database_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS documents (collection TEXT, key TEXT, "
                "data TEXT NOT NULL, PRIMARY KEY(collection, key))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS unique_keys (collection TEXT, "
                "index_name TEXT, value TEXT, document_key TEXT, "
                "PRIMARY KEY(collection, index_name, value))"
            )

    def _lock_user(self, unit, user_id):
        if user_id is None:
            return
        unit.insert_if_absent(
            collections.users,
            {
                "user_id": user_id,
                "learning_revision": 0,
                "rate_window": 0,
                "rate_count": 0,
                "serial_version": 0,
            },
            ["user_id"],
        )
        row = unit.find_one(collections.users, {"user_id": user_id})
        # A write conflict serializes concurrent sessions; with_transaction retries.
        unit.update(
            collections.users,
            {"user_id": user_id},
            {
                "serial_version": row["serial_version"] + 1,
            },
        )

    def run(self, user_id, operation):
        if self.client is None:
            with self.transaction(user_id) as unit:
                return operation(unit)
        for attempt in range(3):
            try:
                with self.client.start_session() as session:

                    def callback(s):
                        unit = UnitOfWork(self.mongo, s)
                        self._lock_user(unit, user_id)
                        return operation(unit)

                    return session.with_transaction(
                        callback,
                        read_concern=ReadConcern("snapshot"),
                        write_concern=WriteConcern("majority"),
                        max_commit_time_ms=5000,
                    )
            except DuplicateKeyError:
                # Retry concurrent initial user/job/key creation on a fresh snapshot.
                if attempt == 2:
                    raise

    def read(self, operation):
        """Read projections can be called inside a feed transaction without nesting writes."""
        if self.mongo is not None:
            return operation(UnitOfWork(mongo=self.mongo))
        with sqlite3.connect(self.settings.fixture_database_path, timeout=15) as conn:
            return operation(UnitOfWork(local=conn))

    @contextmanager
    def transaction(self, user_id=None):
        """Setup/tests only. HTTP services use retryable run(callback)."""
        if self.client is not None:
            with self.client.start_session() as session, session.start_transaction():
                unit = UnitOfWork(self.mongo, session)
                self._lock_user(unit, user_id)
                yield unit
            return
        conn = sqlite3.connect(self.settings.fixture_database_path, timeout=15)
        try:
            conn.execute("BEGIN IMMEDIATE")
            unit = UnitOfWork(local=conn)
            self._lock_user(unit, user_id)
            yield unit
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self):
        if self.client is not None:
            self.client.close()

    def verify_ready(self):
        if self.mongo is not None:
            from app.core.migrate import MIGRATION_ID

            if self.mongo.api_migrations.find_one({"_id": MIGRATION_ID}) is None:
                raise RuntimeError("Apply the API MongoDB migration before starting this service")
