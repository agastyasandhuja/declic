import pytest

from app.modules.videos.repository import LocalVideoRepository, StaleLease


def test_failed_retry_checks_owner_fences_old_worker_and_preserves_generation_key(tmp_path):
    repo = LocalVideoRepository(tmp_path / "jobs.db")
    job = repo.enqueue("key", "alice", {}, {})
    for attempt in range(4):
        claimed = repo.claim()
        repo.update(job["job_id"], claimed["fence"], {"state": "failed"})
        assert not repo.retry_failed(job["job_id"], "bob")
        assert repo.retry_failed(job["job_id"], "alice") is (attempt < 3)
        assert not repo.retry_failed(job["job_id"], "alice")
        with pytest.raises(StaleLease):
            repo.update(job["job_id"], claimed["fence"], {"state": "succeeded"})
    assert repo.get(job["job_id"], "alice")["generation_key"] == "key"
    assert repo.get(job["job_id"], "alice")["state"] == "failed"
