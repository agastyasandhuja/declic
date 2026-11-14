"""Exercise a 12-minute synthetic session through the real ASGI routes (no sleeps/media)."""

import json
import secrets
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def main():
    now = datetime(2026, 11, 14, 12, tzinfo=UTC)
    token = secrets.token_urlsafe(32)
    courses = Counter()
    targets, reasons = set(), Counter()
    videos = studies = quizzes = wrong = 0
    with tempfile.TemporaryDirectory(prefix="api-simulation-") as tmp:
        app = create_app(
            settings=Settings(
                environment="fixture",
                persistence="fixture_sqlite",
                fixture_token=token,
                fixture_database_path=Path(tmp) / "state.db",
                _env_file=None,
            ),
            clock=lambda: now,
        )
        with TestClient(app) as client:
            client.headers["Authorization"] = "Bearer " + token

            def request(method, path, **kwargs):
                response = client.request(method, path, **kwargs)
                assert response.status_code == 200, response.text
                return response.json()

            sid = request("POST", "/v1/feed/sessions", json={})["session_id"]
            cursor = None
            while True:
                session = request(
                    "POST", "/v1/feed/sessions", json={"resume_session_id": sid}
                )
                targets.add(session["study_ratio_target"])
                if session["active_view_seconds"] >= 720:
                    break
                params = {"session_id": sid, "limit": 5}
                if cursor:
                    params["cursor"] = cursor
                page = request("GET", "/v1/feed", params=params)
                assert page["items"], "Synthetic catalog unexpectedly exhausted"
                cursor = page["next_cursor"]
                for item in page["items"]:
                    reasons.update(item["reason_codes"])
                    if item["kind"] == "quiz":
                        qid = item["quiz"]["quiz_instance_id"]
                        request(
                            "POST",
                            f"/v1/feed/sessions/{sid}/quiz-gate",
                            json={
                                "quiz_instance_id": qid,
                                "item_id": item["item_id"],
                            },
                        )
                        selected = "b" if quizzes == 0 else "a"
                        result = request(
                            "POST",
                            f"/v1/quizzes/{qid}/answers",
                            headers={"Idempotency-Key": str(uuid4())},
                            json={"session_id": sid, "selected_option_id": selected},
                        )
                        assert result["scroll_unlocked"]
                        quizzes += 1
                        wrong += int(not result["correct"])
                        cursor = None
                    else:
                        videos += 1
                        if item["kind"] == "study_video":
                            studies += 1
                            courses[item["course_context"]["course_id"]] += 1
                        for kind, elapsed in [
                            ("playback_started", 0),
                            ("video_skipped", 15),
                        ]:
                            now += timedelta(seconds=elapsed)
                            result = request(
                                "POST",
                                "/v1/feed/events",
                                json=[
                                    {
                                        "event_id": str(uuid4()),
                                        "session_id": sid,
                                        "item_id": item["item_id"],
                                        "event_type": kind,
                                        "client_occurred_at": now.isoformat(),
                                        "payload": {
                                            "position_ms": elapsed * 1000,
                                            "visible_watch_ms": elapsed * 1000,
                                        },
                                    }
                                ],
                            )
                            assert not result["rejected"], result
    assert targets == {0.1, 0.2, 0.35, 0.5}
    assert len(courses) == 3 and wrong == 1 and reasons["new_explanation"]
    print(
        json.dumps(
            {
                "mode": "synthetic API simulation; media not played",
                "active_view_seconds": session["active_view_seconds"],
                "observed_study_targets": sorted(targets),
                "video_slots": videos,
                "study_slots": studies,
                "study_slots_by_course": dict(courses),
                "quizzes_submitted": quizzes,
                "wrong_answers_unlocked": wrong,
                "alternate_explanation_slots": reasons["new_explanation"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
