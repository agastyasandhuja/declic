from datetime import datetime

from app.core import collections
from app.core.database import Database, UnitOfWork
from app.core.errors import APIError
from app.core.idempotency import fingerprint
from app.core.time import new_id, utc_now


def enqueue(
    conn: UnitOfWork,
    *,
    owner_user_id: str,
    job_type: str,
    dedupe_key: str,
    input_ref: dict,
    max_attempts: int = 3,
    now: datetime | None = None,
) -> str:
    """Enqueue scoped references inside a retryable domain transaction."""
    if not (1 <= max_attempts <= 10 and 1 <= len(dedupe_key) <= 256):
        raise ValueError("Invalid retry/deduplication settings")
    if len(str(input_ref)) > 16_000:
        raise ValueError("Large job artifacts must be stored separately")
    now = now or utc_now()
    query = dict(owner_user_id=owner_user_id, job_type=job_type, dedupe_key=dedupe_key)
    digest = fingerprint(input_ref)
    conn.insert_if_absent(
        collections.jobs,
        {
            **query,
            "job_id": new_id(),
            "request_hash": digest,
            "state": "queued",
            "attempt_count": 0,
            "max_attempts": max_attempts,
            "available_at": now.timestamp(),
            "lease_until": None,
            "lease_token": None,
            "input_ref": input_ref,
            "output_ref": None,
            "error_code": None,
        },
        list(query),
    )
    row = conn.find_one(collections.jobs, query)
    if row["request_hash"] != digest:
        raise APIError(409, "JOB_KEY_CONFLICT", "Job key already identifies different inputs")
    return row["job_id"]


class JobQueue:
    def __init__(self, database: Database, clock=utc_now):
        self.database, self.clock = database, clock

    def claim(self, job_types: list[str], *, lease_seconds: int = 60) -> dict | None:
        if not job_types:
            return None
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("Lease duration outside allowed range")

        def operation(conn):
            now = self.clock().timestamp()
            candidates = conn.find(
                collections.jobs,
                {
                    "job_type": {"$in": job_types},
                    "$or": [
                        {"state": {"$in": ["queued", "retry_wait"]}, "available_at": {"$lte": now}},
                        {"state": "running", "lease_until": {"$lte": now}},
                    ],
                },
                sort=[("available_at", 1), ("job_id", 1)],
                limit=100,
            )
            for row in candidates:
                if row["attempt_count"] >= row["max_attempts"]:
                    conn.update(
                        collections.jobs,
                        {"job_id": row["job_id"]},
                        {
                            "state": "failed",
                            "error_code": "LEASE_EXHAUSTED",
                            "lease_token": None,
                        },
                    )
                    continue
                claimed = {
                    **row,
                    "state": "running",
                    "lease_token": new_id(),
                    "lease_until": now + lease_seconds,
                    "attempt_count": row["attempt_count"] + 1,
                    "error_code": None,
                }
                # Concurrent claims conflict on this write and retry the transaction.
                conn.update(
                    collections.jobs,
                    {"job_id": row["job_id"]},
                    {
                        key: claimed[key]
                        for key in (
                            "state",
                            "lease_token",
                            "lease_until",
                            "attempt_count",
                            "error_code",
                        )
                    },
                )
                return claimed
            return None

        return self.database.run(None, operation)

    def _owned_lease(self, job_id, lease_token):
        return {
            "job_id": job_id,
            "state": "running",
            "lease_token": lease_token,
            "lease_until": {"$gt": self.clock().timestamp()},
        }

    def heartbeat(self, job_id: str, lease_token: str, *, lease_seconds: int = 60) -> bool:
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("Lease duration outside allowed range")
        return self.database.run(
            None,
            lambda conn: (
                conn.update(
                    collections.jobs,
                    self._owned_lease(job_id, lease_token),
                    {"lease_until": self.clock().timestamp() + lease_seconds},
                ).rowcount
                == 1
            ),
        )

    def finish(self, job_id: str, lease_token: str, output_ref: dict) -> bool:
        return self.database.run(
            None,
            lambda conn: (
                conn.update(
                    collections.jobs,
                    self._owned_lease(job_id, lease_token),
                    {
                        "state": "succeeded",
                        "output_ref": output_ref,
                        "lease_token": None,
                        "lease_until": None,
                    },
                ).rowcount
                == 1
            ),
        )

    def fail(self, job_id: str, lease_token: str, *, retryable: bool = True) -> bool:
        def operation(conn):
            row = conn.find_one(collections.jobs, self._owned_lease(job_id, lease_token))
            if row is None:
                return False
            retry = retryable and row["attempt_count"] < row["max_attempts"]
            conn.update(
                collections.jobs,
                self._owned_lease(job_id, lease_token),
                {
                    "state": "retry_wait" if retry else "failed",
                    "available_at": self.clock().timestamp() + min(300, 2 ** row["attempt_count"]),
                    "error_code": "HANDLER_FAILED",
                    "lease_token": None,
                    "lease_until": None,
                },
            )
            return True

        return self.database.run(None, operation)

    def cancel(self, owner_user_id: str, job_id: str) -> bool:
        return self.database.run(
            owner_user_id,
            lambda conn: (
                conn.update(
                    collections.jobs,
                    {
                        "owner_user_id": owner_user_id,
                        "job_id": job_id,
                        "state": {"$in": ["queued", "retry_wait", "running"]},
                    },
                    {"state": "cancelled", "lease_token": None, "lease_until": None},
                ).rowcount
                == 1
            ),
        )
