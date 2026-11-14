from copy import deepcopy
from uuid import uuid4


def issue_video(client):
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    page = client.get("/v1/feed", params={"session_id": sid}).json()
    return sid, page["items"][0]


def event(clock, sid, item, kind, position=0, visible=0):
    return {
        "event_id": str(uuid4()),
        "session_id": sid,
        "item_id": item["item_id"],
        "event_type": kind,
        "client_occurred_at": clock().isoformat(),
        "payload": {"position_ms": position, "visible_watch_ms": visible},
    }


def send(client, value):
    response = client.post("/v1/feed/events", json=[value])
    assert response.status_code == 200, response.text
    return response.json()


def test_replayed_progress_counts_once_and_new_id_cannot_inflate(client, clock):
    sid, item = issue_video(client)
    start = event(clock, sid, item, "playback_started")
    assert send(client, start)["rejected"] == []
    clock.advance(10)
    progress = event(clock, sid, item, "playback_progress", 10000, 10000)
    assert send(client, progress)["rejected"] == []
    assert send(client, progress)["rejected"] == []
    same_time = event(clock, sid, item, "playback_progress", 10000, 10000)
    assert send(client, same_time)["rejected"] == []
    inflated = event(clock, sid, item, "playback_progress", 30000, 30000)
    assert send(client, inflated)["rejected"][0]["code"] == "IMPLAUSIBLE_WATCH_TIME"
    session = client.post("/v1/feed/sessions", json={"resume_session_id": sid}).json()
    assert session["active_view_seconds"] == 10
    changed = deepcopy(progress)
    changed["payload"]["position_ms"] = 11000
    assert send(client, changed)["rejected"][0]["code"] == "EVENT_ID_CONFLICT"


def test_background_interval_is_not_active_viewing(client, clock):
    sid, item = issue_video(client)
    send(client, event(clock, sid, item, "playback_started"))
    clock.advance(10)
    send(client, event(clock, sid, item, "playback_progress", 10000, 10000))
    send(client, event(clock, sid, item, "app_backgrounded", 10000, 10000))
    clock.advance(900)
    rejected = send(client, event(clock, sid, item, "playback_progress", 20000, 20000))
    assert rejected["rejected"][0]["code"] == "PLAYBACK_INACTIVE"
    assert send(client, event(clock, sid, item, "app_foregrounded", 10000, 10000))["rejected"] == []
    assert send(client, event(clock, sid, item, "playback_started", 10000, 10000))["rejected"] == []
    clock.advance(5)
    assert (
        send(client, event(clock, sid, item, "playback_progress", 15000, 15000))["rejected"] == []
    )
    session = client.post("/v1/feed/sessions", json={"resume_session_id": sid}).json()
    assert session["active_view_seconds"] == 15
    assert session["study_ratio_target"] == 0.1


def test_events_validate_owner_issuance_time_order_and_bounds(client, clock, app):
    sid, item = issue_video(client)
    start = event(clock, sid, item, "playback_started")
    assert send(client, start)["rejected"] == []
    clock.advance(5)
    progress = event(clock, sid, item, "playback_progress", 5000, 5000)
    assert send(client, progress)["rejected"] == []
    old = {**start, "event_id": str(uuid4())}
    assert send(client, old)["rejected"][0]["code"] == "OUT_OF_ORDER_EVENT"
    unknown = event(clock, sid, {"item_id": "not-issued"}, "playback_started")
    assert send(client, unknown)["rejected"][0]["code"] == "NOT_FOUND"
    client.headers["Authorization"] = "Bearer " + app.state.identity.tokens["user_demo_02"]
    assert (
        send(client, event(clock, sid, item, "playback_progress", 5000, 5000))["rejected"][0][
            "code"
        ]
        == "NOT_FOUND"
    )


def test_mixed_batch_preserves_valid_events_and_rejects_mass_assignment(client, clock):
    sid, item = issue_video(client)
    good = event(clock, sid, item, "playback_started")
    bad = event(clock, sid, {"item_id": "missing"}, "playback_started")
    result = client.post("/v1/feed/events", json=[good, bad]).json()
    assert result["accepted_event_ids"] == [good["event_id"]]
    assert result["rejected"] == [{"event_id": bad["event_id"], "code": "NOT_FOUND"}]
    illegal = {**good, "correct": True}
    assert client.post("/v1/feed/events", json=[illegal]).status_code == 422
    assert client.post("/v1/feed/events", json=[good] * 101).status_code == 422


def test_empty_page_is_refreshable_when_inventory_arrives(client, catalog):
    original = catalog.clips
    catalog.clips = []
    catalog.variants = []
    sid = client.post("/v1/feed/sessions", json={}).json()["session_id"]
    assert client.get("/v1/feed", params={"session_id": sid}).json()["items"] == []
    catalog.clips = original
    assert client.get("/v1/feed", params={"session_id": sid}).json()["items"]
