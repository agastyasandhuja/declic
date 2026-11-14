from concurrent.futures import ThreadPoolExecutor

import pytest

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


FACTS = [
    "Fixed costs remain constant within the relevant range.",
    "Variable costs change with the volume of activity.",
]


def test_identical_facts_reuse_despite_titles_goals_order_and_source_ids(database):
    topics = SemanticTopics(database, Embeddings())
    original = {**lesson("Cost behavior"), "facts": FACTS, "source_ids": ["lecture_a"]}
    first, _ = topics.bind("alice", "a", original)
    alternate = {
        **lesson("different CVP title"),
        "learning_goal": "Analyze changing activity levels",
        "facts": ["  VARIABLE costs change with the volume  of activity. ", FACTS[0]],
        "source_ids": ["lecture_b"],
    }
    callbacks = []
    second, reused = topics.bind(
        "alice",
        "b",
        alternate,
        on_bind=lambda tx, topic, reused: callbacks.append((topic["topic_id"], reused)),
    )
    assert reused and second["topic_id"] == first["topic_id"]
    assert second["lesson"] == original
    bindings = database.read(lambda tx: tx.find(tables.bindings, {"user_id": "alice"}))
    assert {row["objective_id"] for row in bindings} == {"a", "b"}
    assert {row["topic_id"] for row in bindings} == {first["topic_id"]}
    assert callbacks == [(first["topic_id"], True)]


@pytest.mark.parametrize(
    "facts",
    [
        [],
        [FACTS[0]],
        [FACTS[0], " ", FACTS[0]],
        [FACTS[0], "Marginal cost measures incremental output cost."],
    ],
)
def test_fact_reuse_requires_two_distinct_matching_nonempty_facts(database, facts):
    topics = SemanticTopics(database, Embeddings())
    first, _ = topics.bind("alice", "a", {**lesson("Cost behavior"), "facts": FACTS})
    second, reused = topics.bind("alice", "b", {**lesson("different"), "facts": facts})
    assert not reused and first["topic_id"] != second["topic_id"]


@pytest.mark.parametrize(
    "owner,options,subject",
    [
        ("bob", {}, "accounting"),
        ("alice", {"level": "advanced"}, "accounting"),
        ("alice", {"language": "es"}, "accounting"),
        ("alice", {"notation": "alternate"}, "accounting"),
    ],
)
def test_identical_facts_do_not_cross_ownership_or_compatibility(database, owner, options, subject):
    topics = SemanticTopics(database, Embeddings())
    first, _ = topics.bind("alice", "a", {**lesson("Cost behavior"), "facts": FACTS})
    second, reused = topics.bind(
        owner, "b", {**lesson("different"), "subject": subject, "facts": FACTS}, **options
    )
    assert not reused
    assert second["user_id"] == owner
    if owner == "alice":
        assert second["topic_id"] != first["topic_id"]


def test_concurrent_identical_facts_with_different_embeddings_share_one_topic(database):
    topics = SemanticTopics(database, Embeddings())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda title: topics.bind("alice", title, {**lesson(title), "facts": FACTS}),
                ["Cost behavior", "different CVP"],
            )
        )
    assert results[0][0]["topic_id"] == results[1][0]["topic_id"]
    assert sum(reused for _, reused in results) == 1


def test_fact_match_wins_over_different_topic_with_closer_title_embedding(database):
    topics = SemanticTopics(database, Embeddings())
    other_facts = [
        "A stack removes the newest item first.",
        "A queue removes the oldest item first.",
    ]
    unrelated, _ = topics.bind("alice", "a", {**lesson("Structures"), "facts": other_facts})
    expected, _ = topics.bind("alice", "b", {**lesson("different Cost behavior"), "facts": FACTS})
    chosen, reused = topics.bind("alice", "c", {**lesson("Costs"), "facts": FACTS})
    assert reused and chosen["topic_id"] == expected["topic_id"]
    assert chosen["topic_id"] != unrelated["topic_id"]


def test_identical_facts_preserve_embedding_model_compatibility(database):
    topics = SemanticTopics(database, Embeddings())
    first, _ = topics.bind("alice", "a", {**lesson("Cost behavior"), "facts": FACTS})
    embeddings = Embeddings()
    embeddings.model = "different-model"
    second, reused = SemanticTopics(database, embeddings).bind(
        "alice", "b", {**lesson("Cost behavior"), "subject": "accounting", "facts": FACTS}
    )
    assert not reused and second["topic_id"] != first["topic_id"]


def test_identical_facts_bridge_generated_subject_labels(database):
    topics = SemanticTopics(database, Embeddings())
    original = {**lesson("Cost behavior"), "subject": "cost-volume-profit analysis", "facts": FACTS}
    first, _ = topics.bind("alice", "a", original)
    second, reused = topics.bind(
        "alice", "b", {**lesson("different CVP title"), "subject": "accounting", "facts": FACTS}
    )
    assert reused and second["topic_id"] == first["topic_id"]
    assert second["lesson"] == original


@pytest.mark.parametrize(
    "facts", [[], [FACTS[0]], [FACTS[0], "Marginal cost measures incremental output cost."]]
)
def test_subject_labels_cannot_be_bridged_by_cosine_similarity_alone(database, facts):
    topics = SemanticTopics(database, Embeddings())
    first, _ = topics.bind(
        "alice", "a", {**lesson("Cost behavior"), "subject": "accounting", "facts": FACTS}
    )
    second, reused = topics.bind(
        "alice", "b", {**lesson("Costs"), "subject": "economics", "facts": facts}
    )
    assert not reused and second["topic_id"] != first["topic_id"]


def test_identical_facts_preserve_compatibility_version(database):
    topics = SemanticTopics(database, Embeddings())
    first, _ = topics.bind("alice", "a", {**lesson("Cost behavior"), "facts": FACTS})
    database.run(
        "alice",
        lambda tx: tx.update(
            tables.topics,
            {"user_id": "alice", "topic_id": first["topic_id"]},
            {"compatibility": {**first["compatibility"], "version": "1"}},
        ),
    )
    second, reused = topics.bind(
        "alice", "b", {**lesson("different title"), "subject": "accounting", "facts": FACTS}
    )
    assert not reused and second["topic_id"] != first["topic_id"]
