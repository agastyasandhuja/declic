"""Generic demo isolation, explicit publication gates, and atomic mode switching."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core import collections as tables
from app.core.demo_catalog import (
    DemoCatalog,
    DemoManifest,
    LearningSettings,
    ModeReader,
    create_router,
)
from app.main import create_app
from app.modules.recommendations.schemas import PlaybackEvent
from conftest import TestIdentity, reached_quiz, watch


def demo_fixture(database, catalog):
    courses = [
        {"course_id": "demo_" + key, "title": title}
        for key, title in [
            ("cs210", "CS210 Data Structures"),
            ("acc233", "ACC233 Accounting"),
            ("his110", "HIS110 History before 1500"),
            ("math235", "MATH235 Linear Algebra"),
        ]
    ]
    objectives, lessons, videos = [], [], []
    for course in courses:
        for i in range(6):
            objective = course["course_id"] + "_" + str(i)
            objectives.append(
                {
                    "objective_id": objective,
                    "course_id": course["course_id"],
                    "title": "Generic lesson " + str(i),
                }
            )
            video = {
                **catalog.variants[0].model_dump(mode="json"),
                "video_id": objective + "_video",
                "objective_id": objective,
                "scope": "shared_generic",
                "owner_user_id": None,
                "status": "ready",
                "level": "intro",
                "language": "en",
                "notation": "general",
                "duration_seconds": 40,
                "asset_id": objective + "_asset",
                "assets": {
                    key: {"key": objective + "/" + key}
                    for key in ("video", "thumbnail", "captions")
                },
                "quality_checks": {
                    "media_checks": "passed",
                    "publication_policy": "agent_reviewed_generic_demo_v1",
                },
            }
            quiz = {
                "quiz_id": objective + "_quiz",
                "revision": 1,
                "objective_ids": [objective],
                "prompt": "Which is correct?",
                "options": [
                    {"option_id": "a", "text": "Correct"},
                    {"option_id": "b", "text": "Incorrect"},
                ],
                "correct_option_id": "a",
                "explanation": "A is the correct explanation.",
                "scope": "shared_generic",
                "owner_user_id": None,
                "source_refs": [],
            }
            lessons.append(
                {
                    "objective_id": objective,
                    "video_id": video["video_id"],
                    "quizzes": [quiz, {**quiz, "quiz_id": quiz["quiz_id"] + "_2"}],
                }
            )
            videos.append(video)
    storage = SimpleNamespace(
        signed_urls=lambda keys: {key: "https://media.example.test/" + key for key in keys}
    )
    repository = SimpleNamespace(
        video=lambda identifier, owner: next(
            (v for v in videos if v["video_id"] == identifier), None
        ),
        list_videos=lambda owner, ids: [v for v in videos if v["objective_id"] in ids],
    )
    demo = DemoCatalog(database, SimpleNamespace(storage=storage, repository=repository))
    manifest = {
        "schema_version": "1",
        "catalog_id": "shared_demo_v1",
        "revision": 1,
        "courses": courses,
        "objectives": objectives,
        "lessons": lessons,
    }
    return demo, manifest, videos


def test_registration_refuses_private_or_unreviewed_assets(database, catalog):
    demo, manifest, videos = demo_fixture(database, catalog)
    original = deepcopy(videos[0])
    for changes in (
        {"scope": "private", "owner_user_id": "student"},
        {"quality_checks": {}},
        {"objective_id": "private_objective"},
    ):
        videos[0].update(changes)
        with pytest.raises(ValueError):
            demo.publish(manifest)
        assert demo.public()["courses"] == []
        videos[0] = deepcopy(original)
    assert len(demo.publish(manifest)["courses"]) == 4
    assert demo.publish(manifest)["revision"] == 1  # exact retry
    changed = deepcopy(manifest)
    changed["courses"][0]["title"] = "Updated"
    with pytest.raises(ValueError):
        demo.publish(changed)
    changed["revision"] = 2
    assert demo.publish(changed)["revision"] == 2


def test_manifest_rejects_private_quiz_sources_and_unbalanced_catalog(database, catalog):
    _, manifest, _ = demo_fixture(database, catalog)
    for mutate in (
        lambda m: m["lessons"][0]["quizzes"][0].update(
            source_refs=[{"source_id": "canvas-private"}]
        ),
        lambda m: m["lessons"][0]["quizzes"][0].update(scope="private", owner_user_id="student"),
        lambda m: m["lessons"][0].update(video_id=m["lessons"][1]["video_id"]),
        lambda m: m["objectives"][0].update(course_id="private_course"),
    ):
        value = deepcopy(manifest)
        mutate(value)
        with pytest.raises(ValueError):
            DemoManifest.model_validate(value)


def test_catalog_accepts_short_math_animation_only_for_math_format(database, catalog):
    demo, manifest, videos = demo_fixture(database, catalog)
    videos[0].update(duration_seconds=21.013, format_id="visual_explainer")
    with pytest.raises(ValueError):
        demo.publish(manifest)
    videos[0]["format_id"] = "math_explainer"
    assert demo.publish(manifest)["revision"] == 1


def test_catalog_adds_cs220_and_exposes_a_four_question_bank(database, catalog):
    demo, manifest, videos = demo_fixture(database, catalog)
    demo.publish(manifest)
    objective = "demo_cs220_promise_states"
    lesson = deepcopy(manifest["lessons"][0])
    lesson.update(objective_id=objective, video_id="promise_states_video")
    quiz = lesson["quizzes"][0]
    lesson["quizzes"] = [
        {**quiz, "quiz_id": f"{objective}_{i}", "objective_ids": [objective]} for i in range(4)
    ]
    manifest["revision"] = 2
    manifest["courses"].append({"course_id": "demo_cs220", "title": "CS 220 — JavaScript"})
    manifest["objectives"].append(
        {"objective_id": objective, "course_id": "demo_cs220", "title": "Promise States"}
    )
    manifest["lessons"].append(lesson)
    videos.append({**videos[0], "video_id": lesson["video_id"], "objective_id": objective})
    bad = deepcopy(manifest)
    bad["lessons"][-1]["quizzes"][-1]["quiz_id"] = bad["lessons"][0]["quizzes"][0]["quiz_id"]
    with pytest.raises(ValueError, match="quiz IDs must be unique"):
        demo.publish(bad)

    assert demo.publish(manifest)["courses"][-1]["video_count"] == 1
    quizzes = demo.list_for_objective("user_demo_01", objective)
    assert len(quizzes) == 4
    assert all(
        "correct_option_id" not in q.card("test-quiz", [lesson["video_id"]]) for q in quizzes
    )


def test_owner_setting_switches_every_reader_without_private_bindings(database, catalog, clock):
    demo, manifest, _ = demo_fixture(database, catalog)
    demo.publish(manifest)
    settings = LearningSettings(database)
    reader = ModeReader(settings, demo, catalog)
    assert not settings.enabled("user_demo_01")
    assert not any(
        o.objective_id.startswith("demo_") for o in reader.list_objectives("user_demo_01")
    )
    settings.update("user_demo_01", True)
    objectives = reader.list_objectives("user_demo_01")
    assert len(objectives) == 24 and {o.user_id for o in objectives} == {"user_demo_01"}
    assert not settings.enabled("user_demo_02")
    assert all(
        v.scope == "shared_generic"
        for v in reader.list_variants("user_demo_01", [o.objective_id for o in objectives])
    )
    assert reader.get_variant("user_demo_01", catalog.variants[0].video_id) is None
    assert reader.list_for_objective("user_demo_01", catalog.objectives[0].objective_id) == []
    settings.update("user_demo_01", False)
    assert reader.list_objectives("user_demo_01") == catalog.list_objectives("user_demo_01")


@pytest.mark.parametrize(
    ("demo_mode", "seconds", "expects_quiz"),
    [(True, 4, False), (True, 5, True), (False, 5, False), (False, 10, True)],
)
def test_quiz_watch_threshold_by_learning_mode(
    database, catalog, clock, demo_mode, seconds, expects_quiz
):
    demo, manifest, _ = demo_fixture(database, catalog)
    demo.publish(manifest)
    settings = LearningSettings(database)
    reader = ModeReader(settings, demo, catalog)
    app = create_app(
        database=database,
        settings=database.settings,
        identity=TestIdentity(),
        academics=reader,
        entertainment=catalog,
        videos=reader,
        quiz_reader=reader,
        clock=clock,
        domain_routers=(create_router(settings, demo),),
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_01"]
        assert client.patch("/v1/learning/settings", json={"demo_mode": demo_mode}).is_success
        session_id = client.post("/v1/feed/sessions", json={}).json()["session_id"]
        query = {"session_id": session_id, "limit": 20}
        page = client.get("/v1/feed", params=query).json()
        studies = [item for item in page["items"] if item["kind"] == "study_video"]
        assert len(studies) == (13 if demo_mode else 2)
        for item in studies[:1] if demo_mode else studies:
            watch(client, clock, session_id, item, seconds=seconds)
        next_page = client.get("/v1/feed", params={**query, "cursor": page["next_cursor"]})
        assert next_page.is_success, next_page.text
        assert any(item["kind"] == "quiz" for item in next_page.json()["items"]) is expects_quiz


def test_mode_switch_invalidates_started_media_and_quiz_without_grading(
    client, app, database, clock
):
    session, quiz, page = reached_quiz(client, clock)
    quiz_id = quiz["quiz"]["quiz_instance_id"]
    response = client.post(
        f"/v1/feed/sessions/{session}/quiz-gate",
        json={"item_id": quiz["item_id"], "quiz_instance_id": quiz_id},
    )
    assert response.json()["scroll_locked"]
    before = database.read(lambda tx: tx.find(tables.attempts))
    result = LearningSettings(database).update("user_demo_01", True)
    assert result["recommendation_revision"] == 2
    assert database.read(lambda tx: tx.find(tables.attempts)) == before
    assert (
        client.get(
            "/v1/feed", params={"session_id": session, "cursor": page["next_cursor"], "limit": 20}
        ).status_code
        == 409
    )
    answer = client.post(
        f"/v1/quizzes/{quiz_id}/answers",
        headers={"Idempotency-Key": "late-answer"},
        json={"session_id": session, "selected_option_id": "a"},
    )
    assert answer.status_code == 409
    assert database.read(lambda tx: tx.find(tables.attempts)) == before
    gate = client.post(
        f"/v1/feed/sessions/{session}/quiz-gate",
        json={"item_id": quiz["item_id"], "quiz_instance_id": quiz_id},
    ).json()
    assert gate["scroll_locked"] is False
    occurrence = database.read(
        lambda tx: tx.find_one(
            tables.occurrences, {"user_id": "user_demo_01", "data.started": True}
        )
    )
    event = PlaybackEvent(
        event_id="late",
        session_id=session,
        item_id=occurrence["item_id"],
        event_type="playback_progress",
        client_occurred_at=clock(),
    )
    assert (
        app.state.playback_events.record("user_demo_01", [event])["rejected"][0]["code"]
        == "CURRICULUM_CHANGED"
    )
    assert (
        LearningSettings(database).update("user_demo_01", True)["recommendation_revision"] is None
    )


def test_settings_http_authentication_and_public_catalog_has_no_answers(database, catalog, clock):
    demo, manifest, _ = demo_fixture(database, catalog)
    demo.publish(manifest)
    settings = LearningSettings(database)
    app = create_app(
        database=database,
        settings=database.settings,
        identity=TestIdentity(),
        clock=clock,
        domain_routers=(create_router(settings, demo),),
    )
    with TestClient(app) as client:
        assert client.get("/v1/learning/settings").status_code == 401
        client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_01"]
        assert client.get("/v1/learning/settings").json()["demo_mode"] is False
        assert (
            client.patch(
                "/v1/learning/settings", json={"demo_mode": True, "user_id": "other"}
            ).status_code
            == 422
        )
        assert client.patch("/v1/learning/settings", json={"demo_mode": "true"}).status_code == 422
        assert (
            client.patch("/v1/learning/settings", json={"demo_mode": True}).json()["demo_mode"]
            is True
        )
        public = client.get("/v1/learning/demo-catalog")
        assert public.status_code == 200 and "correct_option_id" not in public.text
        assert all(c["video_count"] == 6 for c in public.json()["courses"])
        client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_02"]
        assert client.get("/v1/learning/settings").json()["demo_mode"] is False


def test_demo_feed_quiz_grades_only_owner_and_never_queues_private_reteaching(
    database, catalog, clock
):
    demo, manifest, _ = demo_fixture(database, catalog)
    demo.publish(manifest)
    settings = LearningSettings(database)
    settings.update("user_demo_01", True)
    academics = ModeReader(settings, demo, catalog)
    app = create_app(
        database=database,
        settings=database.settings,
        identity=TestIdentity(),
        clock=clock,
        academics=academics,
        videos=academics,
        quiz_reader=academics,
        entertainment=catalog,
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_01"]
        session = client.post("/v1/feed/sessions", json={}).json()["session_id"]
        query = {"session_id": session, "limit": 5}
        first = client.get("/v1/feed", params=query).json()
        lesson = next(item for item in first["items"] if item["kind"] == "study_video")
        watch(client, clock, session, lesson, seconds=5)
        page = client.get("/v1/feed", params={**query, "cursor": first["next_cursor"]}).json()
        (quiz,) = page["items"]
        assert quiz["quiz"]["quiz_id"].startswith("demo_")
        assert "correct_option_id" not in quiz["quiz"] and "explanation" not in quiz["quiz"]
        identifier = quiz["quiz"]["quiz_instance_id"]
        client.post(
            f"/v1/feed/sessions/{session}/quiz-gate",
            json={"item_id": quiz["item_id"], "quiz_instance_id": identifier},
        )
        answer = client.post(
            f"/v1/quizzes/{identifier}/answers",
            headers={"Idempotency-Key": "demo-answer"},
            json={"session_id": session, "selected_option_id": "b"},
        )
        assert (
            answer.status_code == 200
            and answer.json()["correct"] is False
            and answer.json()["scroll_unlocked"]
        )
        assert database.read(lambda tx: tx.count(tables.jobs)) == 0
        assert database.read(lambda tx: tx.count(tables.learning, {"user_id": "user_demo_02"})) == 0


def test_request_cache_reads_mode_and_catalog_once_but_patch_invalidates(
    database, catalog, monkeypatch
):
    from app.core.request_cache import request_cache

    demo, manifest, _ = demo_fixture(database, catalog)
    demo.publish(manifest)
    settings = LearningSettings(database)
    settings.update("user_demo_01", True)
    reads = []
    original = database.read
    monkeypatch.setattr(
        database, "read", lambda operation: (reads.append(1), original(operation))[1]
    )
    reader = ModeReader(settings, demo, catalog)
    token = request_cache.set({})
    try:
        for lesson in manifest["lessons"][:10]:
            assert reader.get_variant("user_demo_01", lesson["video_id"])
        assert len(reads) == 2, "one mode read and one shared manifest read per HTTP request"
        settings.update("user_demo_01", False)
        assert reader.list_objectives("user_demo_01") == catalog.list_objectives("user_demo_01")
    finally:
        request_cache.reset(token)
    assert not settings.enabled("user_demo_01")


def test_presentation_bootstrap_and_playback_share_the_four_reviewed_lessons(
    database, catalog, clock
):
    from app.core.demo_catalog import PRESENTATION_OBJECTIVES
    from app.modules.videos.router import create_router as video_router

    all_lessons, manifest, videos = demo_fixture(database, catalog)
    chosen = {}
    for objective_id in sorted(PRESENTATION_OBJECTIVES):
        course_id = "_".join(objective_id.split("_")[:2])
        if course_id == "demo_cs220":
            manifest["courses"].append({"course_id": course_id, "title": "CS 220"})
            objective = {**manifest["objectives"][0], "course_id": course_id}
            lesson = deepcopy(manifest["lessons"][0])
            video = {**videos[0], "video_id": "promise_video"}
            manifest["objectives"].append(objective)
            manifest["lessons"].append(lesson)
            videos.append(video)
        else:
            index = next(
                i for i, o in enumerate(manifest["objectives"]) if o["course_id"] == course_id
            )
            objective, lesson, video = (
                manifest["objectives"][index],
                manifest["lessons"][index],
                videos[index],
            )
        objective["objective_id"] = objective_id
        video["objective_id"] = objective_id
        lesson.update(objective_id=objective_id, video_id=video["video_id"])
        for i, quiz in enumerate(lesson["quizzes"]):
            quiz.update(quiz_id=f"{objective_id}_quiz_{i}", objective_ids=[objective_id])
        chosen[objective_id] = video["video_id"]
    all_lessons.publish(manifest)

    demo = DemoCatalog(database, all_lessons.video_service, objective_ids=PRESENTATION_OBJECTIVES)
    settings = LearningSettings(database)
    reader = ModeReader(settings, demo, catalog)
    # Entertainment cannot leak even through bootstrap cache hints.
    app = create_app(
        database=database,
        settings=database.settings,
        identity=TestIdentity(),
        academics=reader,
        entertainment=catalog,
        videos=reader,
        quiz_reader=reader,
        clock=clock,
        domain_routers=(
            create_router(settings, demo),
            video_router(
                demo.video_service,
                demo=demo,
                learning_settings=settings,
            ),
        ),
    )
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_01"]
        assert client.patch("/v1/learning/settings", json={"demo_mode": True}).is_success
        session = client.post("/v1/feed/sessions", json={}).json()
        assert session["demo_mode"] and session["study_ratio_target"] == 2 / 3
        reel_id = catalog.clips[0].video_id
        page = client.post(
            "/v1/feed/bootstrap",
            headers={"Idempotency-Key": "curated-bootstrap"},
            json={"limit": 7, "preferred_video_ids": [reel_id]},
        ).json()
        assert page["demo_mode"] is True
        assert len(page["items"]) == 7
        assert page["items"][0]["kind"] == "entertainment_video"
        assert page["items"][0]["video"]["video_id"] == reel_id
        studies = [item for item in page["items"] if item["kind"] == "study_video"]
        assert len(studies) == 4
        assert {item["video"]["video_id"] for item in studies} == set(chosen.values())
        assert {
            c["video_count"] for c in client.get("/v1/learning/demo-catalog").json()["courses"]
        } == {1}
        for item in studies:
            video_id = item["video"]["video_id"]
            response = client.get(f"/v1/learning/videos/{video_id}/playback")
            assert (
                response.is_success
                and response.json()["asset_id"] == item["video"]["playback"]["asset_id"]
            )
        off_list = next(v for v in videos if v["video_id"] not in chosen.values())
        missing = client.get(f"/v1/learning/videos/{off_list['video_id']}/playback")
        assert missing.status_code == 404 and missing.json()["error"]["code"] == "VIDEO_NOT_FOUND"
        vanished = studies[0]["video"]["video_id"]
        videos[:] = [v for v in videos if v["video_id"] != vanished]
        replay = client.get(
            "/v1/feed", params={"session_id": page["session_id"], "limit": 7}
        ).json()
        assert {
            i["video"]["video_id"] for i in replay["items"] if i["kind"] == "study_video"
        } == set(chosen.values()) - {vanished}


def test_legacy_demo_gate_does_not_open_outside_the_new_lineup(client, database, clock):
    from app.modules.recommendations import repository as repo

    session, quiz, _ = reached_quiz(client, clock)
    owner = "user_demo_01"
    # Simulate an account already using old demo mode when the updated API starts.
    database.run(owner, lambda tx: tx.update(tables.users, {"user_id": owner}, {"demo_mode": True}))
    resumed = client.post("/v1/feed/sessions", json={"resume_session_id": session}).json()
    assert (
        resumed["session_id"] == session
        and resumed["demo_mode"]
        and resumed["study_ratio_target"] == 2 / 3
    )
    state = database.run(owner, lambda tx: repo.get_session(tx, owner, session))
    assert not state["required_quiz_instance_id"] and not state["pending_quiz_instance_id"]
    identifier = quiz["quiz"]["quiz_instance_id"]
    instance = database.read(
        lambda tx: tx.find_one(tables.quiz_instances, {"instance_id": identifier})
    )
    assert instance["state"] == "recovered" and not instance["data"]["recovery_response"]["graded"]
