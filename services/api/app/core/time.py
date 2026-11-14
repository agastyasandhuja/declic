from datetime import UTC, datetime
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("An explicit timezone is required")
    return value.astimezone(UTC).isoformat()


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("An explicit timezone is required")
    return result.astimezone(UTC)


def new_id() -> str:
    return str(uuid4())
