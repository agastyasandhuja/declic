"""Run with pytest in a checkout containing Agastya's API core."""
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import APIError
from app.core.identity import Principal
from app.main import create_app
from app.modules.canvas.config import CanvasSettings, Secret
from app.modules.canvas.oauth import OAuthTokens
from app.modules.canvas.router import create_router as canvas_router
from app.modules.curriculum.adapters import FeedAcademicReader
from app.modules.curriculum.client.gemini import GeminiClient
from app.modules.curriculum.jobs import LocalAcademicJobs
from app.modules.curriculum.router import create_router as academic_router
from app.modules.curriculum.service import AcademicService
from app.modules.curriculum.tests.test_curriculum import gemini_response, settings


def test_academic_handoff(tmp_path):
    class Identity:
        def verify_access_token(self, credential):
            if credential in {"owner", "other"}:
                return Principal(credential)
            raise APIError(401, "INVALID_TOKEN", "Invalid token")

    def gemini(url, body, headers):
        if "Allowed suggested_formats" in str(body):
            return gemini_response({"lessons": [{"objective_title": "Reverse a list",
                                                  "learning_goal": "Trace a reversal",
                                                  "unit_title": "Pointers"}]})
        return gemini_response({
            "course_title": "Synthetic DSA",
            "units": [{"title": "Pointers"}],
            "assessments": [{"title": "Final Exam", "kind": "final"}],
        })

    def exchange(config, code):
        assert code == "synthetic-code"
        return OAuthTokens(Secret("synthetic-canvas-secret"), None, None, "external-user")

    service = AcademicService(tmp_path, GeminiClient(settings(), transport=gemini))
    jobs = LocalAcademicJobs()
    reader = FeedAcademicReader(service)
    canvas = CanvasSettings(
        "https://canvas.example", Secret("synthetic-developer-token"), "owner",
        "synthetic-client", Secret("synthetic-client-secret"),
        "https://api.example/v1/canvas/callback",
    )
    app = create_app(
        settings=Settings(environment="test", persistence="fixture_sqlite",
                          fixture_database_path=tmp_path / "core.db", _env_file=None),
        identity=Identity(), academics=reader,
        domain_routers=(canvas_router(canvas, service, jobs, app_return_url="demo://canvas",
                                      exchange=exchange), academic_router(service, jobs)),
    )

    with TestClient(app, follow_redirects=False) as client:
        assert client.get("/v1/academics/profile").status_code == 401
        assert client.get("/v1/canvas/connection").status_code == 401
        owner = {"Authorization": "Bearer owner"}
        other = {"Authorization": "Bearer other"}
        connection = client.get("/v1/canvas/connection", headers=owner).json()
        assert connection["mode"] == "developer_token"
        assert "synthetic-developer-token" not in str(connection)
        assert client.get("/v1/canvas/connection", headers=other).json()["status"] == "disconnected"
        assert client.post("/v1/canvas/sync", headers={**other, "Idempotency-Key": "x"}).status_code == 409
        from urllib.parse import parse_qs, urlsplit

        start = client.post("/v1/canvas/connect", json={"institution": "https://canvas.example"}, headers=other)
        state = parse_qs(urlsplit(start.json()["authorization_url"]).query)["state"][0]
        callback = {"state": state, "code": "synthetic-code"}
        result = client.get("/v1/canvas/callback", params=callback)
        assert result.status_code == 303 and result.headers["Location"] == "demo://canvas"
        assert client.get("/v1/canvas/callback", params=callback).status_code == 400
        assert client.get("/v1/canvas/connection", headers=other).json()["mode"] == "oauth"
        assert client.delete("/v1/canvas/connection", headers=other).status_code == 204

        path = "/v1/academics/uploads"
        upload_headers = {**owner, "Idempotency-Key": "synthetic-upload"}
        body = {"course_label": "Synthetic DSA", "filename": "sample.txt", "content": "Final Exam TBA"}
        submit = client.post(path, json=body, headers=upload_headers)
        assert submit.status_code == 202
        job_id = submit.json()["job_id"]
        assert client.post(path, json=body, headers=upload_headers).json()["job_id"] == job_id
        assert client.post(path, json={**body, "content": "different"}, headers=upload_headers).status_code == 409
        job_path = f"/v1/academics/jobs/{job_id}"
        assert client.get(job_path, headers=owner).json()["state"] == "succeeded"
        assert client.get(job_path, headers=other).status_code == 404
        path = "/v1/academics/profile"
        profile = client.get(path, headers=owner).json()
        assert "_sources" not in profile
        assert client.get(path, headers=other).status_code == 404
        plan_path = f"/v1/academics/courses/{profile['course_ids'][0]}/plan"
        assert client.get(plan_path, headers=owner).status_code == 200
        assert client.get(plan_path, headers=other).status_code == 404
        assert len(reader.list_objectives("owner")) == 1
        assert reader.list_objectives("other") == []
        correction = {"expected_revision": 1, "changes": [
            {"assessment_id": profile["assessments"][0]["assessment_id"], "date": "2026-12-01"}
        ]}
        assert client.patch(path, json=correction, headers=other).status_code == 404
        assert client.patch(path, json=correction, headers=owner).status_code == 200
        assert client.patch(path, json=correction, headers=owner).status_code == 409
        assert client.get(plan_path, headers=owner).status_code == 404


def test_canvas_reader_expires_a_saved_plan_without_reimport():
    from datetime import datetime, timezone

    class SavedProfile:
        def get_profile(self, owner):
            return {
                "revision": 1,
                "courses": [{"course_id": "calculus", "external_course_id": "123",
                             "title": "Calculus", "timezone": "America/New_York"}],
                "assessments": [{
                    "course_id": "calculus", "assessment_id": "exam", "kind": "midterm",
                    "title": "Midterm 2", "scope_status": "explicit",
                    "covered_topics": ["line integrals"],
                    "scheduled": {"date": "2026-11-14", "precision": "date",
                                  "evidence_status": "explicit", "timezone": "America/New_York"},
                }],
            }

        def get_validated_plans(self, owner):
            return [{"profile_revision": 1, "course_id": "calculus", "requests": [{
                "title": "line integrals", "timeline_topic": "line integrals",
                "objective_id": "line-integrals", "assessment_ids": ["exam"],
                "exam_scope_status": "explicit", "prerequisite_objective_ids": [],
            }, {
                "title": "Lagrange multipliers", "objective_id": "old-lesson",
                "assessment_ids": [], "exam_scope_status": "unknown",
                "prerequisite_objective_ids": [],
            }]}]

    now = datetime(2026, 11, 15, 2, tzinfo=timezone.utc)
    reader = FeedAcademicReader(SavedProfile(), clock=lambda: now)
    assert [item.objective_id for item in reader.list_objectives("owner")] == ["line-integrals"]
    now = now.replace(hour=6)
    assert reader.list_objectives("owner") == []
