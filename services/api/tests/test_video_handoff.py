"""Exercise owner-supplied video interfaces through core, without generating media."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.videos.adapters import FeedVideoReader
from app.modules.videos.repository import LocalVideoRepository
from app.modules.videos.router import create_router
from app.modules.videos.service import VideoService
from conftest import TestIdentity


def test_video_owner_adapter_and_routes_compose_with_authenticated_feed(
    database, catalog, tmp_path
):
    repository = LocalVideoRepository(tmp_path / "video-handoff.db")
    prototype = catalog.variants[0].model_dump(mode="json")
    for video_id, scope, owner in (
        ("own-video", "private", "user_demo_01"),
        ("other-video", "private", "user_demo_02"),
        ("shared-video", "shared_generic", None),
    ):
        repository.enqueue(video_id, owner or "user_demo_01", {}, {})
        job = repository.claim()
        # Synthetic catalog seeding, not generation or publication validation.
        repository.publish(
            job["job_id"],
            job["fence"],
            {
                **prototype,
                "schema_version": "1",
                "video_id": video_id,
                "scope": scope,
                "owner_user_id": owner,
                "status": "ready",
                "generation_key": video_id,
                "lesson_request_id": "private-request-" + video_id,
                "asset_id": video_id,
                "assets": {
                    kind: {"key": f"{video_id}/{kind}"}
                    for kind in ("video", "thumbnail", "captions")
                },
            },
        )

    class SyntheticSigner:
        def __init__(self):
            self.calls = []

        def signed_url(self, key):
            self.calls.append(key)
            return "https://fixture.invalid/" + key

    signer = SyntheticSigner()
    service = VideoService(repository, None, signer)
    identity = TestIdentity()
    reader = FeedVideoReader(service)
    app = create_app(
        settings=database.settings,
        database=database,
        identity=identity,
        academics=catalog,
        entertainment=catalog,
        videos=reader,
        quiz_reader=catalog,
        domain_routers=(create_router(service),),
    )
    with TestClient(app) as client:
        assert client.get("/v1/learning/videos/own-video").status_code == 401
        assert signer.calls == []
        client.headers["Authorization"] = "Bearer " + identity.tokens["user_demo_01"]
        sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
        response = client.get("/v1/feed", params={"session_id": sid, "limit": 20})
        assert response.status_code == 200, response.text
        studies = [i["video"] for i in response.json()["items"] if i["kind"] == "study_video"]
        assert {v["video_id"] for v in studies} == {"own-video", "shared-video"}
        for video in studies:
            assert "owner_user_id" not in video
            assert "lesson_request_id" not in video
            assert datetime.fromisoformat(video["playback"]["expires_at"]) > datetime.now(UTC)
            playback = client.get(f"/v1/learning/videos/{video['video_id']}/playback")
            assert playback.status_code == 200
            assert playback.json()["asset_id"] == video["asset_id"]

        signer.calls.clear()
        for suffix in ("", "/playback"):
            assert client.get("/v1/learning/videos/other-video" + suffix).status_code == 404
        assert signer.calls == []

        client.headers["Authorization"] = "Bearer " + identity.tokens["user_demo_02"]
        assert client.get("/v1/learning/videos/own-video/playback").status_code == 404
        shared = client.get("/v1/learning/videos/shared-video")
        assert shared.status_code == 200
        assert shared.json()["lesson_request_id"] is None
