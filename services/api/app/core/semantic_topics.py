"""Owner-scoped semantic reuse with atomic selection and objective bindings."""

import math

import httpx

from app.core import collections as tables
from app.modules.videos.models import digest


def normalized(vector):
    if not vector or len(vector) > 4096 or any(not math.isfinite(x) for x in vector):
        raise ValueError("Invalid topic embedding")
    length = math.hypot(*vector)
    if not math.isfinite(length) or length == 0:
        raise ValueError("Empty topic embedding")
    return [x / length for x in vector]


def approved_fact_set(lesson):
    """Compare teaching content independently of titles, ordering, or citations."""
    facts = frozenset(
        " ".join(fact.casefold().split())
        for fact in lesson.get("facts", [])
        if isinstance(fact, str) and fact.strip()
    )
    return facts if len(facts) >= 2 else None


class GeminiEmbeddings:
    model = "gemini-embedding-001"

    def __init__(self, key, client=None):
        self.key = key
        self.client = client or httpx.Client(timeout=60, follow_redirects=False)

    def embed(self, text):
        response = self.client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent",
            headers={"x-goog-api-key": self.key},
            json={
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": text}]},
                "taskType": "SEMANTIC_SIMILARITY",
                "outputDimensionality": 768,
            },
        )
        if response.status_code != 200:
            raise RuntimeError("TOPIC_EMBEDDING_UNAVAILABLE")
        return normalized(response.json()["embedding"]["values"])


class SemanticTopics:
    def __init__(self, database, embeddings, threshold=0.97):
        self.database, self.embeddings, self.threshold = database, embeddings, threshold

    def bind(
        self,
        owner,
        objective_id,
        lesson,
        *,
        level="intro",
        language="en",
        notation="general",
        on_bind=None,
    ):
        compatibility = {
            "level": level,
            "language": language,
            "notation": notation,
            "subject": lesson["subject"].strip().casefold(),
            "embedding_model": self.embeddings.model,
            "version": "2",
        }
        text = "\n".join([lesson["title"], lesson["learning_goal"], *lesson.get("facts", [])])
        exact = digest({"text": " ".join(text.casefold().split()), **compatibility})
        facts = approved_fact_set(lesson)
        existing = self.database.read(
            lambda tx: tx.find_one(tables.topics, {"user_id": owner, "exact_key": exact})
        )
        vector = existing["embedding"] if existing else normalized(self.embeddings.embed(text))

        def choose(tx):
            # database.run(owner) serializes concurrent choices for this owner. A
            # transaction retry re-reads candidates before inserting a new topic.
            candidates = tx.find(
                tables.topics, {"user_id": owner, "compatibility_key": digest(compatibility)}
            )
            matches = []
            for row in candidates:
                if facts is not None and facts == approved_fact_set(row["lesson"]):
                    # Exact fact agreement wins over a title-driven embedding
                    # match. Scope/compatibility were enforced by this query.
                    matches.append((2.0, row))
                    continue
                other = row["embedding"]
                if len(other) == len(vector):
                    similarity = sum(a * b for a, b in zip(vector, other, strict=True))
                    if row["exact_key"] == exact or similarity >= self.threshold:
                        matches.append((similarity, row))
            topic = (
                max(matches, key=lambda pair: pair[0])[1]
                if matches
                else {
                    "user_id": owner,
                    "topic_id": "topic_" + exact[:32],
                    "exact_key": exact,
                    "compatibility": compatibility,
                    "compatibility_key": digest(compatibility),
                    "embedding": vector,
                    "lesson": lesson,
                }
            )
            tx.insert_if_absent(tables.topics, topic, ["user_id", "topic_id"])
            query = {"user_id": owner, "objective_id": objective_id}
            tx.insert_if_absent(
                tables.bindings, {**query, "topic_id": topic["topic_id"]}, list(query)
            )
            tx.update(tables.bindings, query, {"topic_id": topic["topic_id"]})
            if on_bind is not None:
                # Publication and ownership/revision guards share this transaction;
                # a rejection rolls back both the topic and objective binding.
                on_bind(tx, topic, bool(matches))
            return topic, bool(matches)

        return self.database.run(owner, choose)
