from types import SimpleNamespace

from app.core import collections as tables
from app.core.learning_readers import BoundVideoReader


def test_shared_topic_is_projected_to_each_owned_objective_and_refreshes(database):
    rows = [
        dict(user_id="alice", objective_id="course_a", topic_id="topic"),
        dict(user_id="alice", objective_id="course_b", topic_id="topic"),
    ]
    for row in rows:
        database.run("alice", lambda tx, row=row: tx.insert(tables.bindings, row))
    video = {"video_id": "v", "objective_id": "topic"}
    repo = SimpleNamespace(list_videos=lambda owner, ids: [video], video=lambda vid, owner: video)
    reader = BoundVideoReader(SimpleNamespace(repository=repo), database)
    reader._project = lambda owner, value, signed: value
    reader._sign_owned = lambda videos: {}
    assert {v["objective_id"] for v in reader.list_variants("alice", ["course_a", "course_b"])} == {
        "course_a",
        "course_b",
    }
    assert reader.get_variant_for_objective("alice", "v", "course_b")["objective_id"] == "course_b"
    assert reader.get_variant_for_objective("bob", "v", "course_b") is None
