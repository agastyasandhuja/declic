import os
import secrets
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Database
from app.core.errors import APIError
from app.core.fixtures import FixtureCatalog
from app.core.identity import Principal
from app.main import create_app


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 14, 12, tzinfo=UTC)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


class TestIdentity:
    __test__ = False

    def __init__(self):
        self.tokens = {user: secrets.token_urlsafe(32) for user in ["user_demo_01", "user_demo_02"]}

    def verify_access_token(self, token):
        for user_id, candidate in self.tokens.items():
            if secrets.compare_digest(token, candidate):
                return Principal(user_id)
        raise APIError(401, "INVALID_TOKEN", "Invalid or expired access token")


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def database(tmp_path):
    settings = Settings(
        environment="test",
        persistence="fixture_sqlite",
        fixture_database_path=tmp_path / "test.db",
        rate_limit_per_minute=10000,
        _env_file=None,
    )
    mongo_uri = os.environ.get("API_TEST_MONGODB_URI")
    if mongo_uri:
        # Never use the app's normal database for tests. Each test gets a fresh,
        # random API-owned database and cleans up only that database.
        settings = Settings(
            environment="test",
            mongodb_uri=mongo_uri,
            mongodb_database="api_test_" + secrets.token_hex(8),
            rate_limit_per_minute=10000,
            _env_file=None,
        )
    db = Database(settings)
    if mongo_uri:
        from app.core.migrate import apply

        apply(db)
    db.initialize_local()
    yield db
    if mongo_uri:
        db.client.drop_database(settings.mongodb_database)
    db.close()


@pytest.fixture
def catalog():
    return FixtureCatalog()


@pytest.fixture
def app(database, clock, catalog):
    return create_app(
        settings=database.settings,
        database=database,
        clock=clock,
        identity=TestIdentity(),
        academics=catalog,
        entertainment=catalog,
        videos=catalog,
        quiz_reader=catalog,
    )


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_01"]
        yield client


def watch(client, clock, session_id, item, seconds=12):
    import uuid

    def send(kind, ms):
        result = client.post(
            "/v1/feed/events",
            json=[
                {
                    "event_id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "item_id": item["item_id"],
                    "event_type": kind,
                    "client_occurred_at": clock().isoformat(),
                    "payload": {"position_ms": ms, "visible_watch_ms": ms},
                }
            ],
        )
        assert result.status_code == 200, result.text
        assert result.json()["rejected"] == [], result.text

    send("playback_started", 0)
    clock.advance(seconds)
    send("video_skipped", seconds * 1000)


def reached_quiz(client, clock):
    session_id = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    response = client.get("/v1/feed", params={"session_id": session_id, "limit": 20})
    assert response.status_code == 200, response.text
    page = response.json()
    studies = [i for i in page["items"] if i["kind"] == "study_video"]
    assert len(studies) == 2
    for item in studies:
        watch(client, clock, session_id, item)
    quiz_page = client.get(
        "/v1/feed",
        params={
            "session_id": session_id,
            "limit": 20,
            "cursor": page["next_cursor"],
        },
    ).json()
    assert len(quiz_page["items"]) == 1, quiz_page
    quiz = quiz_page["items"][0]
    assert quiz["kind"] == "quiz"
    return session_id, quiz, quiz_page
