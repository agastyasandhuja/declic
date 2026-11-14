from datetime import datetime

from app.core import collections as tables
from app.core.database import UnitOfWork
from app.core.errors import APIError
from app.core.time import iso, new_id


def get_session(conn: UnitOfWork, user_id: str, session_id: str) -> dict:
    row = conn.value(
        tables.sessions, "data", {"$and": [{"user_id": user_id}, {"session_id": session_id}]}
    )
    if row is None:
        raise APIError(404, "NOT_FOUND", "Session not found")
    return row


def save_session(conn: UnitOfWork, user_id: str, state: dict) -> None:
    conn.update(
        tables.sessions,
        {"$and": [{"user_id": user_id}, {"session_id": state["session_id"]}]},
        {"data": state, "last_active": datetime.fromisoformat(state["last_active_at"]).timestamp()},
    )


def create_session(conn: UnitOfWork, user_id: str, now: datetime) -> dict:
    state = {
        "session_id": new_id(),
        "started_at": iso(now),
        "last_active_at": iso(now),
        "active_view_ms": 0,
        "recommendation_revision": 1,
        "pending_quiz_instance_id": None,
        "required_quiz_instance_id": None,
        "root_page_id": None,
        "study_debt": 0,
        "sequence": 0,
        "history": [],
        "quiz_exposures": [],
        "foreground": True,
        "current_item_id": None,
        "last_client_event_at": None,
    }
    conn.insert(
        tables.sessions,
        {
            "session_id": state["session_id"],
            "user_id": user_id,
            "last_active": now.timestamp(),
            "data": state,
        },
    )
    return state


def learning_states(conn: UnitOfWork, user_id: str) -> dict[str, dict]:
    return {r["objective_id"]: r["data"] for r in conn.find(tables.learning, {"user_id": user_id})}


def get_occurrence(conn: UnitOfWork, user_id: str, session_id: str, item_id: str) -> dict:
    row = conn.find_one(
        tables.occurrences,
        {"$and": [{"item_id": item_id}, {"user_id": user_id}, {"session_id": session_id}]},
    )
    if row is None:
        raise APIError(404, "NOT_FOUND", "Feed item not found")
    return dict(row)


def save_occurrence(conn: UnitOfWork, row: dict) -> None:
    conn.update(
        tables.occurrences,
        {"$and": [{"item_id": row["item_id"]}, {"user_id": row["user_id"]}]},
        {"data": row["data"]},
    )


def invalidate_user_feeds(conn: UnitOfWork, user_id: str) -> dict[str, dict]:
    """Drop unseen reservations in every session after a learning-state mutation."""
    updated = {}
    for row in conn.find(tables.sessions, {"user_id": user_id}):
        state = row["data"]
        state["recommendation_revision"] += 1
        state["root_page_id"] = None
        state["study_debt"] = min(state["study_debt"], 1)
        exposed = conn.values(
            tables.occurrences,
            "data",
            {"$and": [{"user_id": user_id}, {"session_id": row["session_id"]}]},
            sort=[("sequence", -1)],
            limit=200,
        )
        state["history"] = [
            r["history"] for r in reversed(exposed) if r.get("exposed") and r.get("history")
        ][-50:]
        save_session(conn, user_id, state)
        updated[row["session_id"]] = state
    return updated
