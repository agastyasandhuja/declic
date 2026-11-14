"""Selected demo runs must not consume or expire the rest of the queue."""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.modules.videos.repository import AtlasVideoRepository, LocalVideoRepository
from app.modules.videos.service import run_once
from app.workers.demo import video_job_ids


def test_local_selection_retries_reclaims_and_leaves_other_jobs_untouched(tmp_path):
    repo = LocalVideoRepository(tmp_path / "jobs.db")
    other = repo.enqueue("other", "owner", {}, {})
    exhausted = repo.enqueue("exhausted", "owner", {}, {})
    old = repo.claim(now=1, lease=1, job_ids=[exhausted["job_id"]])
    old = repo.claim(now=3, lease=1, job_ids=[old["job_id"]])
    selected = repo.enqueue("selected", "owner", {}, {})
    ids = [selected["job_id"]]

    assert repo.claim(now=5, job_ids=[]) is None
    assert repo.claim(now=5, job_ids=["missing"]) is None
    first = repo.claim(now=5, lease=10, job_ids=ids)
    assert first["job_id"] == selected["job_id"]
    repo.update(first["job_id"], first["fence"], {"state": "retry_wait", "available_at": 8}, now=6)
    assert repo.claim(now=7, job_ids=ids) is None
    second = repo.claim(now=8, lease=1, job_ids=ids)
    assert second["attempt"] == 2
    assert repo.claim(now=10, job_ids=ids) is None
    assert repo.get(first["job_id"], "owner")["state"] == "failed"
    assert repo.get(other["job_id"], "owner") == other
    assert repo.get(old["job_id"], "owner") == old

    assert repo.retry_failed(first["job_id"], "owner")
    restarted = repo.claim(now=11, lease=1, job_ids=ids)
    reclaimed = repo.claim(now=13, lease=1, job_ids=ids)
    assert reclaimed["fence"] > restarted["fence"]
    assert repo.get(old["job_id"], "owner") == old
    # Omitting the filter preserves normal queue selection.
    assert repo.claim(now=14)["job_id"] == other["job_id"]


@pytest.mark.parametrize("selection", [None, [], ["one", "two"]])
def test_atlas_selection_applies_to_both_expiry_and_atomic_claim(selection):
    jobs = Mock()
    jobs.find_one_and_update.return_value = None
    repo = AtlasVideoRepository(
        SimpleNamespace(video_generation_jobs=jobs, video_variants=Mock(), video_outbox=Mock())
    )
    assert repo.claim(now=5, job_ids=selection) is None
    if selection == []:
        jobs.update_many.assert_not_called()
        jobs.find_one_and_update.assert_not_called()
        return
    for query in (jobs.update_many.call_args.args[0], jobs.find_one_and_update.call_args.args[0]):
        if selection is None:
            assert "job_id" not in query
        else:
            assert query["job_id"] == {"$in": selection}
    assert jobs.update_many.call_args.args[0]["attempt"] == {"$gte": 2}
    assert jobs.find_one_and_update.call_args.args[0]["attempt"] == {"$lt": 2}


@pytest.mark.parametrize("selection", [None, [], ["one", "two"]])
def test_service_forwards_explicit_selection_only(tmp_path, selection):
    repo = Mock()
    repo.claim.return_value = None
    assert not run_once(repo, tmp_path, job_ids=selection)
    if selection is None:
        repo.claim.assert_called_once_with()
    else:
        repo.claim.assert_called_once_with(job_ids=selection)


def test_worker_allowlist_environment_and_cli_precedence(monkeypatch):
    monkeypatch.delenv("VIDEO_GENERATION_JOB_IDS", raising=False)
    assert video_job_ids(None) is None
    monkeypatch.setenv("VIDEO_GENERATION_JOB_IDS", "")
    assert video_job_ids(None) == []
    monkeypatch.setenv("VIDEO_GENERATION_JOB_IDS", " one, two ,, ")
    assert video_job_ids(None) == ["one", "two"]
    assert video_job_ids(["three"]) == ["three"]


def test_demo_launcher_forwards_repeated_ids_without_starting_workers(monkeypatch):
    root = Path(__file__).resolve().parents[6]
    call = Mock(return_value=0)
    monkeypatch.setattr("subprocess.call", call)
    monkeypatch.setattr(Path, "exists", lambda _: True)
    monkeypatch.setattr(
        sys, "argv", ["run-demo.py", "workers", "--video-job-id", "one", "--video-job-id", "two"]
    )
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(root / "scripts/run-demo.py"), run_name="__main__")
    assert exit_info.value.code == 0
    assert call.call_args.args[0][-4:] == ["--video-job-id", "one", "--video-job-id", "two"]
