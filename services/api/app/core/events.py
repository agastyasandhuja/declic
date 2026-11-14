from datetime import datetime

from app.core import collections
from app.core.database import UnitOfWork
from app.core.time import iso, new_id


def publish(
    conn: UnitOfWork,
    *,
    event_type: str,
    user_id: str,
    aggregate_id: str,
    revision: int,
    payload: dict,
    now: datetime,
) -> str:
    event_id = new_id()
    envelope = {
        "event_id": event_id,
        "schema_version": "1",
        "event_type": event_type,
        "occurred_at": iso(now),
        "actor_user_id": user_id,
        "aggregate_id": aggregate_id,
        "aggregate_revision": revision,
        "payload": payload,
    }
    conn.insert(
        collections.outbox,
        dict(event_id=event_id, event_type=event_type, data=envelope, created_at=now.timestamp()),
    )
    return event_id


def consume_one(conn: UnitOfWork, consumer: str, event_type: str, handler) -> bool:
    """Use Database.run(None, callback). Handler and receipt commit atomically.

    Handlers must compare aggregate_revision before overwriting a projection and
    perform database-only work. External side effects should become durable jobs.
    """
    seen = conn.values(collections.processed, "event_id", {"consumer": consumer})
    row = conn.find_one(
        collections.outbox,
        {
            "event_type": event_type,
            "event_id": {"$nin": seen},
        },
        sort=[("created_at", 1), ("event_id", 1)],
    )
    if row is None:
        return False
    # A unique receipt makes concurrent consumption retry on a fresh snapshot.
    conn.insert(collections.processed, {"consumer": consumer, "event_id": row["event_id"]})
    handler(conn, row["data"])
    return True
