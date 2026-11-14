import hashlib
import json

from app.core import collections as tables
from app.core.database import UnitOfWork
from app.core.errors import APIError


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def lookup(conn: UnitOfWork, user_id: str, route: str, key: str, body: dict) -> dict | None:
    row = conn.find_one(
        tables.idempotency, {"$and": [{"user_id": user_id}, {"route": route}, {"key": key}]}
    )
    if row is None:
        return None
    if row["request_hash"] != fingerprint(body):
        raise APIError(409, "IDEMPOTENCY_CONFLICT", "This key was used for different request data")
    return row["response"]


def remember(conn: UnitOfWork, user_id: str, route: str, key: str, body: dict, response: dict):
    conn.insert(
        tables.idempotency,
        {
            "user_id": user_id,
            "route": route,
            "key": key,
            "request_hash": fingerprint(body),
            "response": response,
        },
    )
