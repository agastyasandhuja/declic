"""Inventory traversal must not starve clips beyond the study-history window."""

from app.core import collections as tables
from app.modules.recommendations.service import FeedService


def service(database, catalog, clock, size=100):
    catalog.objectives = []
    base = catalog.clips[0]
    catalog.clips = [base.model_copy(update={
        "video_id": f"reel_{i:03}", "provider_video_id": str(i),
    }) for i in range(size)]
    return FeedService(database, catalog, catalog, catalog, catalog, clock=clock)


def consume(database, session):
    # Mark the fixture page consumed without adding watch/learning credit.
    database.run("user_demo_01", lambda tx: tx.update(
        tables.occurrences, {"user_id": "user_demo_01", "session_id": session},
        {"data": {"terminal": True}},
    ))


def test_full_100_clip_inventory_before_any_repeat(database, catalog, clock):
    feed = service(database, catalog, clock)
    session = feed.start_session("user_demo_01")["session_id"]
    cursor, issued = None, []
    for _ in range(6):
        page = feed.get_feed("user_demo_01", session, cursor, 20)
        issued.extend(item["video"]["video_id"] for item in page["items"])
        cursor = page["next_cursor"]
        consume(database, session)
    assert len(set(issued[:100])) == 100
    assert issued[100:] == issued[:20]


def test_refresh_does_not_replay_recent_reels_and_new_inventory_wins(database, catalog, clock):
    feed = service(database, catalog, clock, 4)
    session = feed.start_session("user_demo_01")["session_id"]
    first = feed.get_feed("user_demo_01", session, None, 3)
    assert len(first["items"]) == 3
    feed.start_session("user_demo_01", session, refresh_unseen=True)
    second = feed.get_feed("user_demo_01", session, None, 3)
    assert second["items"][0]["video"]["video_id"] == "reel_003"
    catalog.clips.append(catalog.clips[0].model_copy(update={
        "video_id": "reel_new", "provider_video_id": "new",
    }))
    consume(database, session)
    third = feed.get_feed("user_demo_01", session, second["next_cursor"], 3)
    assert third["items"][0]["video"]["video_id"] == "reel_new"
