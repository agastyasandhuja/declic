from concurrent.futures import ThreadPoolExecutor

from app.core import collections as tables
from app.core.semantic_topics import SemanticTopics


class Embeddings:
    model = "synthetic"

    def embed(self, text):
        return [1.0, 0.0] if "different" not in text else [0.0, 1.0]


def lesson(title):
    return {"title": title, "learning_goal": "Understand reversal", "subject": "Computer science"}


def test_semantic_reuse_is_atomic_owned_and_compatible(database):
    topics = SemanticTopics(database, Embeddings())
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(
            pool.map(
                lambda pair: topics.bind("alice", pair[0], lesson(pair[1])),
                [("a", "Reverse a list"), ("b", "Invert linked nodes")],
            )
        )
    assert a[0]["topic_id"] == b[0]["topic_id"]
    assert sum([a[1], b[1]]) == 1
    assert database.run("alice", lambda tx: tx.count(tables.topics, {"user_id": "alice"})) == 1
    assert not topics.bind("bob", "c", lesson("Reverse a list"))[1]
    assert not topics.bind("alice", "d", lesson("Reverse a list"), level="advanced")[1]
    assert not topics.bind("alice", "e", lesson("different objective"))[1]
