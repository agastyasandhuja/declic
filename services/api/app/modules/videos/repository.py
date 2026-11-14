"""Atlas is the application store. SQLite below is an explicit local test adapter."""

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


class StaleLease(RuntimeError):
    pass


def new_job(key, owner, brief, recipe):
    return {
        "job_id": uuid.uuid4().hex,
        "generation_key": key,
        "owner_user_id": owner,
        "brief": brief,
        "recipe": recipe,
        "state": "queued",
        "stage": "queued",
        "attempt": 0,
        "fence": 0,
        "lease_until": 0,
        "available_at": 0,
        "created_at": datetime.now(UTC).isoformat(),
    }


class AtlasVideoRepository:
    def __init__(self, database):
        self.db = database
        self.jobs = database.video_generation_jobs
        self.catalog = database.video_variants
        self.outbox = database.video_outbox

    def initialize(self):
        self.jobs.create_index("generation_key", unique=True)
        self.jobs.create_index("job_id", unique=True)
        self.jobs.create_index([("state", 1), ("available_at", 1), ("lease_until", 1)])
        self.catalog.create_index("generation_key", unique=True)
        self.catalog.create_index("video_id", unique=True)
        self.outbox.create_index("event_id", unique=True)

    def enqueue(self, key, owner, brief, recipe):
        row = new_job(key, owner, brief, recipe)
        try:
            self.jobs.insert_one(row)
        except DuplicateKeyError:
            row = self.jobs.find_one({"generation_key": key})
        row.pop("_id", None)
        return row

    def get(self, job_id, owner):
        return self.jobs.find_one({"job_id": job_id, "owner_user_id": owner}, {"_id": 0})

    def claim(self, now=None, lease=90):
        now = time.time() if now is None else now
        self.jobs.update_many(
            {"state": "running", "lease_until": {"$lte": now}, "attempt": {"$gte": 2}},
            {"$set": {"state": "failed", "error_code": "LEASE_EXHAUSTED"}},
        )
        return self.jobs.find_one_and_update(
            {
                "attempt": {"$lt": 2},
                "$or": [
                    {"state": {"$in": ["queued", "retry_wait"]}, "available_at": {"$lte": now}},
                    {"state": "running", "lease_until": {"$lte": now}},
                ],
            },
            {
                "$set": {"state": "running", "lease_until": now + lease},
                "$inc": {"fence": 1, "attempt": 1},
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )

    def update(self, job_id, fence, changes, now=None):
        now = time.time() if now is None else now
        result = self.jobs.update_one(
            {"job_id": job_id, "fence": fence, "state": "running", "lease_until": {"$gt": now}},
            {"$set": changes},
        )
        if result.matched_count != 1:
            raise StaleLease("Job cancelled or lease expired")

    def cancel(self, job_id, owner):
        return (
            self.jobs.update_one(
                {
                    "job_id": job_id,
                    "owner_user_id": owner,
                    "state": {"$nin": ["succeeded", "cancelled"]},
                },
                {"$set": {"state": "cancelled"}, "$inc": {"fence": 1}},
            ).modified_count
            == 1
        )

    def claim_review(self, job_id, owner, video_hash, now=None):
        now = time.time() if now is None else now
        return self.jobs.find_one_and_update(
            {
                "job_id": job_id,
                "owner_user_id": owner,
                "state": "awaiting_review",
                "video_sha256": video_hash,
            },
            {
                "$set": {"state": "running", "stage": "validating", "lease_until": now + 900},
                "$inc": {"fence": 1},
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )

    def publish(self, job_id, fence, variant, now=None):
        now = time.time() if now is None else now
        with self.db.client.start_session() as session:
            with session.start_transaction():
                result = self.jobs.update_one(
                    {
                        "job_id": job_id,
                        "fence": fence,
                        "state": "running",
                        "lease_until": {"$gt": now},
                    },
                    {"$set": {"state": "succeeded", "stage": "ready"}},
                    session=session,
                )
                if result.matched_count != 1:
                    raise StaleLease("Publication lease lost")
                self.catalog.insert_one(variant.copy(), session=session)
                self.outbox.insert_one(ready_event(variant), session=session)

    def ready(self, key, owner):
        return self.catalog.find_one(
            {
                "generation_key": key,
                "status": "ready",
                "$or": [{"scope": "shared_generic"}, {"scope": "private", "owner_user_id": owner}],
            },
            {"_id": 0},
        )

    def video(self, video_id, owner):
        return self.catalog.find_one(
            {
                "video_id": video_id,
                "status": "ready",
                "$or": [{"scope": "shared_generic"}, {"scope": "private", "owner_user_id": owner}],
            },
            {"_id": 0},
        )

    def list_videos(self, owner, objective_ids):
        return list(
            self.catalog.find(
                {
                    "objective_id": {"$in": objective_ids[:200]},
                    "status": "ready",
                    "$or": [
                        {"scope": "shared_generic"},
                        {"scope": "private", "owner_user_id": owner},
                    ],
                },
                {"_id": 0},
            ).limit(200)
        )


def ready_event(variant):
    return {
        "event_id": variant["video_id"],
        "schema_version": "1",
        "event_type": "learning.video.ready",
        "occurred_at": datetime.now(UTC).isoformat(),
        "actor_user_id": variant["owner_user_id"],
        "aggregate_id": variant["video_id"],
        "aggregate_revision": 1,
        "payload": {
            k: variant[k] for k in ("video_id", "lesson_request_id", "objective_id", "scope")
        },
    }


class LocalVideoRepository:
    """Durable fake for development/tests. Never a production fallback."""

    def __init__(self, path):
        self.path = str(path)
        with self.transaction() as conn:
            conn.executescript(
                "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, key TEXT UNIQUE, data TEXT);"
                "CREATE TABLE IF NOT EXISTS catalog "
                "(id TEXT PRIMARY KEY, key TEXT UNIQUE, data TEXT);"
                "CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, data TEXT);"
            )

    @contextmanager
    def transaction(self):
        conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def enqueue(self, key, owner, brief, recipe):
        with self.transaction() as conn:
            row = new_job(key, owner, brief, recipe)
            conn.execute(
                "INSERT OR IGNORE INTO jobs VALUES(?,?,?)", (row["job_id"], key, json.dumps(row))
            )
            return json.loads(
                conn.execute("SELECT data FROM jobs WHERE key=?", (key,)).fetchone()[0]
            )

    def get(self, job_id, owner):
        with self.transaction() as conn:
            row = conn.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
            data = json.loads(row[0]) if row else None
            return data if data and data["owner_user_id"] == owner else None

    def claim(self, now=None, lease=90):
        now = time.time() if now is None else now
        with self.transaction() as conn:
            for (raw,) in conn.execute("SELECT data FROM jobs ORDER BY rowid"):
                row = json.loads(raw)
                if row["state"] == "running" and row["lease_until"] <= now and row["attempt"] >= 2:
                    row.update(state="failed", error_code="LEASE_EXHAUSTED")
                    conn.execute(
                        "UPDATE jobs SET data=? WHERE id=?", (json.dumps(row), row["job_id"])
                    )
                    continue
                eligible = row["state"] in {"queued", "retry_wait"} and row["available_at"] <= now
                eligible |= row["state"] == "running" and row["lease_until"] <= now
                if eligible and row["attempt"] < 2:
                    row.update(
                        state="running",
                        lease_until=now + lease,
                        fence=row["fence"] + 1,
                        attempt=row["attempt"] + 1,
                    )
                    conn.execute(
                        "UPDATE jobs SET data=? WHERE id=?", (json.dumps(row), row["job_id"])
                    )
                    return row

    def _update(self, conn, job_id, fence, changes, now):
        raw = conn.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
        row = json.loads(raw[0]) if raw else None
        if (
            not row
            or row["state"] != "running"
            or row["fence"] != fence
            or row["lease_until"] <= now
        ):
            raise StaleLease("Job cancelled or lease expired")
        row.update(changes)
        conn.execute("UPDATE jobs SET data=? WHERE id=?", (json.dumps(row), job_id))

    def update(self, job_id, fence, changes, now=None):
        with self.transaction() as conn:
            self._update(conn, job_id, fence, changes, time.time() if now is None else now)

    def cancel(self, job_id, owner):
        with self.transaction() as conn:
            raw = conn.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
            row = json.loads(raw[0]) if raw else None
            if (
                not row
                or row["owner_user_id"] != owner
                or row["state"] in {"succeeded", "cancelled"}
            ):
                return False
            row.update(state="cancelled", fence=row["fence"] + 1)
            conn.execute("UPDATE jobs SET data=? WHERE id=?", (json.dumps(row), job_id))
            return True

    def publish(self, job_id, fence, variant, now=None):
        with self.transaction() as conn:
            self._update(
                conn,
                job_id,
                fence,
                {"state": "succeeded", "stage": "ready"},
                time.time() if now is None else now,
            )
            conn.execute(
                "INSERT INTO catalog VALUES(?,?,?)",
                (variant["video_id"], variant["generation_key"], json.dumps(variant)),
            )
            conn.execute(
                "INSERT INTO outbox VALUES(?,?)",
                (variant["video_id"], json.dumps(ready_event(variant))),
            )

    def claim_review(self, job_id, owner, video_hash, now=None):
        now = time.time() if now is None else now
        with self.transaction() as conn:
            raw = conn.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
            row = json.loads(raw[0]) if raw else None
            if (
                not row
                or row["owner_user_id"] != owner
                or row["state"] != "awaiting_review"
                or row.get("video_sha256") != video_hash
            ):
                return None
            row.update(
                state="running", stage="validating", lease_until=now + 900, fence=row["fence"] + 1
            )
            conn.execute("UPDATE jobs SET data=? WHERE id=?", (json.dumps(row), job_id))
            return row

    def _lookup(self, column, value, owner):
        # Column is selected only by internal methods, never an API parameter.
        with self.transaction() as conn:
            raw = conn.execute(f"SELECT data FROM catalog WHERE {column}=?", (value,)).fetchone()
            row = json.loads(raw[0]) if raw else None
            return (
                row
                if row
                and row["status"] == "ready"
                and (row["scope"] == "shared_generic" or row["owner_user_id"] == owner)
                else None
            )

    def ready(self, key, owner):
        return self._lookup("key", key, owner)

    def video(self, video_id, owner):
        return self._lookup("id", video_id, owner)

    def list_videos(self, owner, objective_ids):
        with self.transaction() as conn:
            rows = [json.loads(row[0]) for row in conn.execute("SELECT data FROM catalog")]
        return [
            row
            for row in rows
            if row["status"] == "ready"
            and row["objective_id"] in objective_ids[:200]
            and (row["scope"] == "shared_generic" or row["owner_user_id"] == owner)
        ][:200]
