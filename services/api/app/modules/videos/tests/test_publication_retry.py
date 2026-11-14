"""Retry delivery from exact reviewed artifacts; never repeat paid generation."""

import json

import httpx
import pytest
from test_auto_publication import staged as staged

from app.modules.videos import service
from app.modules.videos.generation.providers import ProviderError
from app.modules.videos.media import sha256
from app.modules.videos.models import digest
from app.modules.videos.publication import SupabaseVideoStorage


@pytest.fixture
def storage_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://storage.example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "synthetic")
    path = tmp_path / "video.mp4"
    path.write_bytes(b"synthetic video bytes")
    return path, "a" * 32 + "/" + sha256(path) + ".mp4"


@pytest.mark.parametrize(
    "status,body,code,retryable",
    [
        (400, {"statusCode": "413", "error": "Payload too large"}, "STORAGE_FILE_TOO_LARGE", False),
        (413, {}, "STORAGE_FILE_TOO_LARGE", False),
        (400, {"code": "EntityTooLarge"}, "STORAGE_FILE_TOO_LARGE", False),
        (400, {"error": "synthetic private response"}, "STORAGE_UPLOAD_FAILED", False),
        (409, {"code": "InvalidRequest"}, "STORAGE_UPLOAD_FAILED", False),
        (403, {}, "STORAGE_ACCESS_DENIED", False),
        (429, {}, "STORAGE_UPLOAD_FAILED", True),
        (503, {}, "STORAGE_UPLOAD_FAILED", True),
    ],
)
def test_upload_rejections_are_sanitized_and_never_blindly_verified(
    storage_file, status, body, code, retryable
):
    file, key = storage_file
    calls = []

    def respond(request):
        calls.append(request.method)
        return httpx.Response(status, json=body)

    storage = SupabaseVideoStorage(httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ProviderError) as failure:
        storage.put(key, file)
    assert failure.value.code == code and failure.value.retryable is retryable
    assert str(failure.value) == code and calls == ["POST"]


@pytest.mark.parametrize(
    "status,body",
    [
        (400, {"error": "Duplicate"}),
        (409, {"code": "ResourceAlreadyExists"}),
    ],
)
def test_only_known_duplicate_uploads_may_verify_existing_bytes(storage_file, status, body):
    file, key = storage_file
    calls = []

    def respond(request):
        calls.append(request.method)
        return (
            httpx.Response(status, json=body)
            if request.method == "POST"
            else httpx.Response(200, content=file.read_bytes())
        )

    storage = SupabaseVideoStorage(httpx.Client(transport=httpx.MockTransport(respond)))
    assert storage.put(key, file)["sha256"] == sha256(file)
    assert calls == ["POST", "GET"]


@pytest.mark.parametrize(
    "verification_status,retryable",
    [(404, True), (429, True), (503, True), (400, False), (403, False)],
)
def test_verification_failure_retryability(storage_file, verification_status, retryable):
    file, key = storage_file
    storage = SupabaseVideoStorage(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    201 if request.method == "POST" else verification_status
                )
            )
        )
    )
    with pytest.raises(ProviderError) as failure:
        storage.put(key, file)
    assert failure.value.retryable is retryable


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_storage_network_errors_are_retryable_and_redacted(storage_file, method):
    file, key = storage_file

    def respond(request):
        if request.method == method:
            raise httpx.ReadTimeout("SYNTHETIC_SECRET_UPSTREAM_DETAIL", request=request)
        return httpx.Response(201)

    storage = SupabaseVideoStorage(httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ProviderError) as failure:
        storage.put(key, file)
    assert failure.value.retryable and "SYNTHETIC_SECRET" not in str(failure.value)


def prepare_worker(staged, tmp_path, *, cache=True):
    repo, storage, job, brief, work, manifest, uploads = staged
    target = tmp_path / job["job_id"]
    work.rename(target)
    manifest.update(
        scope="private",
        owner_user_id="alice",
        storyboard_digest=digest(json.loads((target / "storyboard.json").read_text())),
    )
    if cache:
        (target / "generation-manifest.json").write_text(json.dumps(manifest))
    repo.update(job["job_id"], job["fence"], {"state": "queued", "attempt": 0})
    return repo, storage, job, brief, target, manifest, uploads


@pytest.mark.parametrize("transient", [True, False])
def test_failed_publication_reuses_exact_completed_artifacts_without_generation(
    staged, tmp_path, monkeypatch, transient
):
    repo, storage, job, brief, work, manifest, _ = prepare_worker(staged, tmp_path, cache=False)
    clock = [service.time.time()]
    monkeypatch.setattr(service.time, "time", lambda: clock[0])
    generated = []

    def generate(*_args, **_kwargs):
        generated.append(1)
        (work / "generation-manifest.json").write_text(json.dumps(manifest))
        return manifest

    monkeypatch.setattr(service, "generate", generate)
    original = storage.put
    failed = [False]

    def put(key, path):
        if not failed[0]:
            failed[0] = True
            raise ProviderError(
                "STORAGE_UPLOAD_FAILED" if transient else "STORAGE_FILE_TOO_LARGE", transient
            )
        return original(key, path)

    storage.put = put
    assert service.run_once(repo, tmp_path, private_demo_storage=storage)
    row = repo.get(job["job_id"], "alice")
    assert row["state"] == ("retry_wait" if transient else "failed")
    assert row["result_ref"] == job["job_id"]
    assert repo.ready(job["generation_key"], "alice") is None
    if not transient:
        assert repo.retry_failed(job["job_id"], "alice")
    clock[0] += 11
    # Deployment can advance; completed artifacts bind the ORIGINAL queued recipe.
    monkeypatch.setattr(service, "generation_recipe", lambda **_: {"new": "deployment"})
    assert service.run_once(repo, tmp_path, private_demo_storage=storage)
    assert generated == [1]
    assert repo.get(job["job_id"], "alice")["state"] == "succeeded"
    assert repo.ready(job["generation_key"], "alice")["quality_checks"]["human_review"] == "pending"


@pytest.mark.parametrize(
    "change",
    [
        "artifact",
        "owner",
        "recipe",
        "key",
        "fixture",
        "shared",
        "storyboard",
        "content_review",
        "frame_review",
        "media_check",
        "missing",
    ],
)
def test_invalid_completed_assets_fail_closed_before_upload_or_paid_generation(
    staged, tmp_path, monkeypatch, change
):
    repo, storage, job, brief, work, manifest, uploads = prepare_worker(staged, tmp_path)
    if change == "artifact":
        (work / "captions.vtt").write_text("changed")
    elif change == "owner":
        manifest["owner_user_id"] = "bob"
    elif change == "recipe":
        manifest["recipe"] = {"wrong": True}
    elif change == "key":
        manifest["generation_key"] = "wrong"
    elif change == "fixture":
        manifest["fixture"] = True
    elif change == "shared":
        manifest["scope"] = "shared_generic_candidate"
    elif change == "storyboard":
        manifest["storyboard_digest"] = "wrong"
    elif change == "content_review":
        (work / "content-review.json").write_text('{"passed":false}')
    elif change == "frame_review":
        (work / "render-review.json").write_text('{"passed":false}')
    elif change == "media_check":
        manifest["quality"]["media_checks"] = "failed"
    if change == "missing":
        (work / "generation-manifest.json").unlink()
        # This is an interrupted publication, not an unstarted generation job.
        claimed = repo.claim()
        repo.update(
            job["job_id"], claimed["fence"], {"state": "queued", "result_ref": job["job_id"]}
        )
    else:
        (work / "generation-manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(
        service, "generate", lambda *_args, **_kwargs: pytest.fail("Must not regenerate")
    )
    assert service.run_once(repo, tmp_path, private_demo_storage=storage)
    assert repo.get(job["job_id"], "alice")["state"] == "failed"
    assert not uploads and repo.ready(job["generation_key"], "alice") is None


def test_cached_publication_retries_remain_attempt_bounded(staged, tmp_path, monkeypatch):
    repo, storage, job, _, _, _, _ = prepare_worker(staged, tmp_path)
    clock = [service.time.time()]
    monkeypatch.setattr(service.time, "time", lambda: clock[0])
    monkeypatch.setattr(
        service, "generate", lambda *_args, **_kwargs: pytest.fail("Must not regenerate")
    )
    calls = []

    def fail_upload(*_args):
        calls.append(1)
        raise ProviderError("STORAGE_UPLOAD_FAILED", True)

    storage.put = fail_upload
    assert service.run_once(repo, tmp_path, private_demo_storage=storage)
    assert repo.get(job["job_id"], "alice")["state"] == "retry_wait"
    clock[0] += 11
    assert service.run_once(repo, tmp_path, private_demo_storage=storage)
    assert repo.get(job["job_id"], "alice")["state"] == "failed"
    clock[0] += 11
    assert not service.run_once(repo, tmp_path, private_demo_storage=storage)
    assert len(calls) == 2
