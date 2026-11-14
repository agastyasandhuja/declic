"""Run with VIDEO_TEST_MONGODB_URI pointing only at a disposable replica set."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from pymongo import MongoClient

from app.modules.videos.repository import AtlasVideoRepository, StaleLease


@pytest.fixture
def repo():
    uri = os.getenv("VIDEO_TEST_MONGODB_URI")
    if not uri:
        pytest.skip("Disposable Mongo replica set not configured")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    database = client["video_test_" + uuid.uuid4().hex]
    repository = AtlasVideoRepository(database)
    repository.initialize()
    yield repository
    client.drop_database(database.name)
    client.close()


def test_atomic_claim_dedupe_and_ownership(repo):
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = list(executor.map(lambda _: repo.enqueue("same", "alice", {}, {}), range(16)))
    assert len({j["job_id"] for j in jobs}) == 1
    with ThreadPoolExecutor(max_workers=8) as executor:
        claimed = list(executor.map(lambda _: repo.claim(now=1), range(8)))
    assert sum(job is not None for job in claimed) == 1
    assert repo.get(jobs[0]["job_id"], "bob") is None


def test_transaction_rollback_then_publication(repo):
    repo.enqueue("key", "alice", {}, {})
    job = repo.claim(now=1)
    with pytest.raises(KeyError):
        repo.publish(job["job_id"], job["fence"], {"video_id": "bad"}, now=2)
    assert repo.get(job["job_id"], "alice")["state"] == "running"
    assert repo.catalog.count_documents({}) == 0
    variant = {
        "video_id": "v",
        "generation_key": "key",
        "status": "ready",
        "scope": "private",
        "owner_user_id": "alice",
        "lesson_request_id": "req",
        "objective_id": "obj",
    }
    repo.publish(job["job_id"], job["fence"], variant, now=2)
    assert repo.ready("key", "alice") and repo.ready("key", "bob") is None
    assert repo.outbox.count_documents({}) == 1


def test_lease_reclaim_cancellation_and_exhaustion(repo):
    repo.enqueue("key", "alice", {}, {})
    first = repo.claim(now=1, lease=1)
    second = repo.claim(now=3, lease=1)
    with pytest.raises(StaleLease):
        repo.update(first["job_id"], first["fence"], {"stage": "ready"}, now=3)
    assert repo.claim(now=5) is None
    assert repo.get(second["job_id"], "alice")["state"] == "failed"


def test_review_digest_and_fence(repo):
    repo.enqueue("key", "alice", {}, {})
    job = repo.claim(now=1)
    repo.update(
        job["job_id"], job["fence"], {"state": "awaiting_review", "video_sha256": "abc"}, now=2
    )
    assert repo.claim_review(job["job_id"], "bob", "abc", now=3) is None
    assert repo.claim_review(job["job_id"], "alice", "changed", now=3) is None
    reviewed = repo.claim_review(job["job_id"], "alice", "abc", now=3)
    assert reviewed["fence"] > job["fence"]
    assert repo.cancel(job["job_id"], "alice")
    with pytest.raises(StaleLease):
        repo.publish(job["job_id"], reviewed["fence"], {}, now=4)


def test_allowlist_preserves_unselected_queue_and_expired_leases(repo):
    queued = repo.enqueue("queued", "alice", {}, {})
    expired = repo.enqueue("expired", "alice", {}, {})
    repo.claim(now=1, lease=1, job_ids=[expired["job_id"]])
    expired = repo.claim(now=3, lease=1, job_ids=[expired["job_id"]])
    selected = repo.enqueue("selected", "alice", {}, {})
    ids = [selected["job_id"]]
    assert repo.claim(now=5, job_ids=[]) is None
    assert repo.claim(now=5, job_ids=["missing"]) is None
    first = repo.claim(now=5, lease=10, job_ids=ids)
    assert first["job_id"] == selected["job_id"]
    repo.update(first["job_id"], first["fence"], {"state": "retry_wait", "available_at": 8}, now=6)
    assert repo.claim(now=7, job_ids=ids) is None
    assert repo.claim(now=8, lease=1, job_ids=ids)["attempt"] == 2
    assert repo.claim(now=10, job_ids=ids) is None
    assert repo.get(first["job_id"], "alice")["state"] == "failed"
    assert repo.get(queued["job_id"], "alice") == queued
    assert repo.get(expired["job_id"], "alice") == expired
    assert repo.retry_failed(first["job_id"], "alice")
    restarted = repo.claim(now=11, lease=1, job_ids=ids)
    reclaimed = repo.claim(now=13, lease=1, job_ids=ids)
    assert reclaimed["fence"] > restarted["fence"]
    assert repo.get(expired["job_id"], "alice") == expired
