import json
from concurrent.futures import ThreadPoolExecutor

from app.core import collections as tables
from conftest import reached_quiz, watch


def test_auth_validation_and_cross_user_isolation(client, app):
    session = client.post("/v1/feed/sessions", json={}).json()
    sid = session["session_id"]
    assert client.get("/health").status_code == 200
    client.headers.pop("Authorization")
    assert client.get("/v1/feed", params={"session_id": sid}).status_code == 401
    client.headers["Authorization"] = "Bearer invalid"
    assert client.get("/v1/learning/progress").status_code == 401
    client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_02"]
    assert client.get("/v1/feed", params={"session_id": sid}).status_code == 404
    assert client.post("/v1/feed/sessions", json={"resume_session_id": sid}).status_code == 404
    response = client.post("/v1/feed/sessions", json={"user_id": "user_demo_01"})
    assert response.status_code == 422
    assert "user_demo_01" not in response.text
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_retrying_page_and_session_does_not_advance_ramp_or_reservations(client, database):
    session = client.post("/v1/feed/sessions", json={}).json()
    resumed = client.post("/v1/feed/sessions", json={}).json()
    assert resumed["session_id"] == session["session_id"]
    first = client.get("/v1/feed", params={"session_id": session["session_id"]}).json()
    assert first == client.get("/v1/feed", params={"session_id": session["session_id"]}).json()
    with database.transaction() as conn:
        assert conn.count(tables.occurrences, {}) == 10
    assert sum(i["kind"] == "study_video" for i in first["items"]) == 1
    assert resumed["active_view_seconds"] == 0


def test_quiz_prefetch_activation_wrong_answer_and_stale_cursor(client, clock, database):
    sid, quiz, page = reached_quiz(client, clock)
    qid = quiz["quiz"]["quiz_instance_id"]
    assert page["pending_quiz_instance_id"] is None
    serialized = json.dumps(page)
    for forbidden in [
        "correct_option_id",
        "explanation",
        "misconception",
        "source_refs",
        "owner_user_id",
    ]:
        assert forbidden not in serialized
    assert (
        client.get(
            "/v1/feed",
            params={
                "session_id": sid,
                "cursor": page["next_cursor"],
                "limit": 20,
            },
        ).status_code
        == 409
    )
    answer_url = f"/v1/quizzes/{qid}/answers"
    body = {"session_id": sid, "selected_option_id": "b"}
    headers = {"Idempotency-Key": "answer-one"}
    assert client.post(answer_url, json=body, headers=headers).status_code == 409
    activation = client.post(
        f"/v1/feed/sessions/{sid}/quiz-gate",
        json={
            "quiz_instance_id": qid,
            "item_id": quiz["item_id"],
        },
    ).json()
    assert activation["scroll_locked"]
    pending = client.get("/v1/feed", params={"session_id": sid, "limit": 20}).json()
    assert [i["kind"] for i in pending["items"]] == ["quiz"]
    answer = client.post(answer_url, json=body, headers=headers)
    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result["accepted"] and result["scroll_unlocked"] and not result["correct"]
    assert client.post(answer_url, json=body, headers=headers).json() == result
    assert (
        client.post(answer_url, json=body, headers={"Idempotency-Key": "retry-new-key"}).json()
        == result
    )
    assert (
        client.post(
            answer_url, json={**body, "selected_option_id": "a"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.get(
            "/v1/feed",
            params={
                "session_id": sid,
                "cursor": page["next_cursor"],
                "limit": 20,
            },
        ).json()["error"]["code"]
        == "STALE_CURSOR"
    )
    activated_again = client.post(
        f"/v1/feed/sessions/{sid}/quiz-gate",
        json={
            "quiz_instance_id": qid,
            "item_id": quiz["item_id"],
        },
    ).json()
    assert not activated_again["scroll_locked"]
    with database.transaction() as conn:
        assert conn.count(tables.attempts, {}) == 1
        assert conn.count(tables.outbox, {}) == 1
        state = conn.value(tables.learning, "data", {})
        assert state["incorrect_count"] == 1 and state["mastery_estimate"] < 0.5
    fresh = client.get("/v1/feed", params={"session_id": sid, "limit": 20}).json()
    reteaching = [
        i
        for i in fresh["items"]
        if i["kind"] == "study_video"
        and i["video"]["objective_id"] in quiz["quiz"]["objective_ids"]
    ]
    assert reteaching
    assert "quiz_weakness" in reteaching[0]["reason_codes"]
    assert "new_explanation" in reteaching[0]["reason_codes"]
    assert reteaching[0]["video"]["video_id"] not in quiz["quiz"]["related_video_ids"]


def test_recovery_ungraded_retryable_and_survives_reopen(client, clock, database):
    sid, quiz, _ = reached_quiz(client, clock)
    qid = quiz["quiz"]["quiz_instance_id"]
    client.post(
        f"/v1/feed/sessions/{sid}/quiz-gate",
        json={
            "quiz_instance_id": qid,
            "item_id": quiz["item_id"],
        },
    )
    clock.advance(3600)
    assert client.post("/v1/feed/sessions", json={}).json()["session_id"] == sid
    body = {"session_id": sid, "reason": "content_error", "client_event_id": "recover-one"}
    url = f"/v1/quizzes/{qid}/recover"
    response = client.post(url, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["graded"] is False
    assert client.post(url, json=body).json() == response.json()
    with database.transaction() as conn:
        assert conn.count(tables.attempts, {}) == 0
        assert conn.count(tables.learning, {}) == 0


def test_concurrent_answers_grade_once(client, app, clock, database):
    from app.modules.quizzes.schemas import AnswerRequest

    sid, quiz, _ = reached_quiz(client, clock)
    qid = quiz["quiz"]["quiz_instance_id"]
    app.state.feed.activate_gate("user_demo_01", sid, qid, quiz["item_id"])

    def answer(i):
        return app.state.quizzes.answer(
            "user_demo_01",
            qid,
            AnswerRequest(
                session_id=sid,
                selected_option_id="b" if i % 2 else "a",
            ),
            f"concurrent-{i}",
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(answer, range(8)))
    assert len({r["attempt_id"] for r in results}) == 1
    with database.transaction() as conn:
        assert conn.count(tables.attempts, {}) == 1


def test_empty_inventory_and_failed_generation_do_not_block_entertainment(client, catalog):
    catalog.variants = []
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    response = client.get("/v1/feed", params={"session_id": sid, "limit": 20})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 20
    assert all(i["kind"] == "entertainment_video" for i in response.json()["items"])
    assert response.json()["availability"]["study"] == "unavailable"


def test_progress_is_neutral_until_graded(client, clock):
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    page = client.get("/v1/feed", params={"session_id": sid}).json()
    study = next(i for i in page["items"] if i["kind"] == "study_video")
    watch(client, clock, sid, study)
    assert all(
        i["mastery_estimate"] is None for i in client.get("/v1/learning/progress").json()["items"]
    )


def test_fresh_unseen_page_preserves_active_session_and_pending_quiz(client, clock):
    session = client.post('/v1/feed/sessions', json={}).json()
    first = client.get('/v1/feed', params={'session_id': session['session_id']}).json()
    video = first['items'][0]
    watch(client, clock, session['session_id'], video, seconds=10)
    refreshed = client.post('/v1/feed/sessions', json={'refresh_unseen': True}).json()
    assert refreshed['session_id'] == session['session_id']
    assert refreshed['active_view_seconds'] == 10
    assert refreshed['recommendation_revision'] > first['recommendation_revision']
