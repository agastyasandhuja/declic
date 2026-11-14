"""Trusted publication: uploaded objects are private, readiness is an Atlas transaction."""

import hashlib
import mimetypes
import os
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from urllib.parse import quote, unquote, urlsplit

import httpx

from .generation.providers import ProviderError, request_json
from .media import sha256
from .pipeline import artifact_digests


def storage_response_error(response, *, verifying=False):
    """Classify fixed storage diagnostics without exposing upstream bodies/keys."""
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    embedded = str(body.get("statusCode", ""))
    status = int(embedded) if embedded.isdigit() and len(embedded) == 3 else response.status_code
    code = body.get("code") or body.get("error") or ""
    code = re.sub(r"[\s_-]", "", code).casefold() if isinstance(code, str) else ""
    if (
        response.status_code == 413
        or status == 413
        or code in {"entitytoolarge", "payloadtoolarge"}
    ):
        return ProviderError("STORAGE_FILE_TOO_LARGE")
    if status in {401, 403}:
        return ProviderError("STORAGE_ACCESS_DENIED")
    transient = status in {408, 429} or status >= 500
    if verifying:
        return ProviderError("STORAGE_VERIFY_FAILED", transient or status == 404)
    if response.status_code in {400, 409} and code in {
        "duplicate",
        "resourcealreadyexists",
        "keyalreadyexists",
    }:
        return None  # Only a known immutable-key conflict permits byte verification.
    return ProviderError("STORAGE_UPLOAD_FAILED", transient)


class SupabaseVideoStorage:
    def __init__(self, client=None):
        self.url = os.environ["SUPABASE_URL"].rstrip("/")
        if (
            urlsplit(self.url).scheme != "https"
            or urlsplit(self.url).query
            or urlsplit(self.url).username
        ):
            raise ValueError("Storage requires a trusted HTTPS origin")
        self.bucket = os.environ.get("VIDEO_STORAGE_BUCKET", "lesson-videos")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", self.bucket):
            raise ValueError("Invalid storage bucket")
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.headers = {"Authorization": f"Bearer {key}", "apikey": key}
        self.client = client or httpx.Client(timeout=180, follow_redirects=False)
        self._signed_cache = {}
        self._cache_lock = Lock()

    def verify_private_bucket(self):
        data = request_json(
            self.client, "GET", f"{self.url}/storage/v1/bucket/{self.bucket}", headers=self.headers
        )
        if data.get("public") is not False:
            raise ValueError("Video storage bucket must be private")

    def put(self, key, file):
        # Hash-addressed object keys can be retried without changing existing content.
        if not re.fullmatch(r"[a-f0-9]{32}/[a-f0-9]{64}\.(mp4|png|vtt|json)", key):
            raise ValueError("Invalid object key")
        url = f"{self.url}/storage/v1/object/{self.bucket}/{key}"
        data = file.read_bytes()
        headers = {
            **self.headers,
            "Content-Type": mimetypes.guess_type(file.name)[0] or "application/octet-stream",
        }
        try:
            response = self.client.post(url, content=data, headers=headers)
        except httpx.TransportError:
            raise ProviderError("STORAGE_UPLOAD_FAILED", True) from None
        if response.status_code not in {200, 201}:
            error = storage_response_error(response)
            if error is not None:
                raise error
        # Verify bytes even after an ambiguous response/retry; never trust success alone.
        h = hashlib.sha256()
        count = 0
        try:
            with self.client.stream(
                "GET",
                f"{self.url}/storage/v1/object/authenticated/{self.bucket}/{key}",
                headers=self.headers,
            ) as check:
                if check.status_code != 200:
                    check.read()
                    raise storage_response_error(check, verifying=True)
                for chunk in check.iter_bytes():
                    count += len(chunk)
                    if count > len(data):
                        raise ProviderError("STORAGE_SIZE_MISMATCH")
                    h.update(chunk)
        except httpx.TransportError:
            raise ProviderError("STORAGE_VERIFY_FAILED", True) from None
        if count != len(data) or h.hexdigest() != sha256(file):
            raise ProviderError("STORAGE_DIGEST_MISMATCH")
        return {"key": key, "sha256": h.hexdigest(), "size": count}

    def signed_url(self, key):
        with self._cache_lock:
            cached = self._signed_cache.get(key)
            if cached and cached[0] > time.monotonic():
                return cached[1]
        data = request_json(
            self.client,
            "POST",
            f"{self.url}/storage/v1/object/sign/{self.bucket}/{quote(key, safe='/')}",
            headers=self.headers,
            json={"expiresIn": 900},
        )
        signed = data["signedURL"]
        if not signed.startswith("/object/sign/"):
            raise ValueError("Unexpected signed URL")
        url = self.url + "/storage/v1" + signed
        with self._cache_lock:
            if len(self._signed_cache) >= 1024:
                self._signed_cache.pop(next(iter(self._signed_cache)))
            self._signed_cache[key] = (time.monotonic() + 120, url)
        return url


    def signed_urls(self, keys):
        """Batch already-authorized asset paths; this cache never grants ownership."""
        keys = list(dict.fromkeys(keys))
        if len(keys) > 600:
            raise ValueError("At most 200 videos may be signed per catalog request")
        started = time.monotonic()
        with self._cache_lock:
            result = {
                key: self._signed_cache[key][1]
                for key in keys
                if key in self._signed_cache and self._signed_cache[key][0] > started
            }
        missing = [key for key in keys if key not in result]
        if not missing:
            return result
        # Refresh siblings too: a slow request must not age cached URLs past
        # their advertised client lease. Fully cached batches make no request.
        missing = keys
        data = request_json(
            self.client,
            "POST",
            f"{self.url}/storage/v1/object/sign/{self.bucket}",
            headers=self.headers,
            json={"expiresIn": 900, "paths": missing},
        )
        if not isinstance(data, list) or len(data) != len(missing):
            raise ProviderError("STORAGE_SIGN_FAILED", True)
        fresh = {}
        for row in data:
            if not isinstance(row, dict):
                raise ProviderError("STORAGE_SIGN_FAILED", True)
            key, signed = row.get("path"), row.get("signedURL")
            if (
                not isinstance(key, str)
                or key not in missing
                or key in fresh
                or row.get("error")
                or not isinstance(signed, str)
            ):
                raise ProviderError("STORAGE_SIGN_FAILED", True)
            parsed = urlsplit(signed)
            if (
                parsed.scheme
                or parsed.netloc
                or parsed.fragment
                or unquote(parsed.path) != f"/object/sign/{self.bucket}/{key}"
            ):
                raise ProviderError("STORAGE_SIGN_FAILED", True)
            fresh[key] = self.url + "/storage/v1" + signed
        with self._cache_lock:
            for key, url in fresh.items():
                if key not in self._signed_cache and len(self._signed_cache) >= 1024:
                    self._signed_cache.pop(next(iter(self._signed_cache)))
                # 900s signatures, <=120s reuse, and a 600s client lease leave
                # >=180s headroom. Start before the request, not after its latency.
                self._signed_cache[key] = (started + 120, url)
        result.update(fresh)
        return result


def publish_validated_variant(
    repository, storage, job, brief, work: Path, manifest, review, *, automated_private=False
):
    quality = manifest["quality"]
    required = {"content", "visuals", "audio_sync", "assets"}
    if automated_private and (
        brief.scope != "private" or review.get("policy") != "private_demo_automated_v1"
    ):
        raise ValueError("Automatic publication is restricted to private demo lessons")
    if (
        manifest["fixture"]
        or quality.get("preview")
        or quality.get("media_checks") != "passed"
        or review.get("video_sha256") != quality.get("sha256")
        or any(review.get(k) is not True for k in required)
    ):
        raise ValueError("Exact final media needs human approval; fixtures cannot publish")
    video = work / "output/lesson.mp4"
    if (
        manifest.get("recipe") != job["recipe"]
        or manifest.get("generation_key") != brief.generation_key(job["recipe"])
        or manifest.get("artifact_digests") != artifact_digests(work)
        or review.get("artifact_digests") != manifest.get("artifact_digests")
    ):
        raise ValueError("Review must bind the queued recipe and every published artifact")
    if sha256(video) != review["video_sha256"]:
        raise ValueError("Reviewed video changed")
    scope = "private"
    if brief.scope == "shared_generic_candidate":
        if review.get("generic_lineage") is not True:
            raise ValueError("Generic lineage approval required")
        scope = "shared_generic"
    storage.verify_private_bucket()
    files = {
        "video": video,
        "captions": work / "captions.vtt",
        "words": work / "captions.json",
        "thumbnail": work / "output/frame-01.png",
        "quality": work / "output/quality.json",
    }
    assets = {}
    extensions = dict(video="mp4", captions="vtt", words="json", thumbnail="png", quality="json")
    for name, file in files.items():
        # Include no owner, course, or lesson names in storage paths.
        key = f"{job['job_id']}/{sha256(file)}.{extensions[name]}"
        assets[name] = storage.put(key, file)
    now = datetime.now(UTC).isoformat()
    variant = {
        "schema_version": "1",
        "video_id": uuid.uuid4().hex,
        "generation_key": brief.generation_key(job["recipe"]),
        "objective_id": brief.objective_id,
        "lesson_request_id": brief.lesson_request_id,
        "format_id": brief.format_id,
        "teaching_approach": brief.teaching_approach,
        "level": brief.level,
        "language": brief.language,
        "notation": brief.notation,
        "scope": scope,
        "owner_user_id": brief.owner_user_id if scope == "private" else None,
        "status": "ready",
        "title": brief.title,
        "learning_goal": brief.learning_goal,
        "duration_seconds": quality["duration_seconds"],
        "asset_id": assets["video"]["sha256"],
        "assets": assets,
        "template_version": brief.template_version,
        "brief_hash": manifest["generation_key"],
        "generation_version": "1.0.0",
        "quality_checks": {
            **quality,
            "human_review": "pending" if automated_private else "approved",
            "publication_policy": "private_demo_automated_v1"
            if automated_private
            else "human_reviewed_v1",
        },
        "created_at": now,
        "ready_at": now,
    }
    repository.publish(job["job_id"], job["fence"], variant)
    return variant


def publish_private_demo(repository, storage, job, brief, work, manifest):
    """Publish private assets only after exact content/frame/media checks.

    This is automated model review and media validation, never human approval.
    Generic/public publication continues through the explicit review route.
    """
    import json

    from .models import digest

    content = json.loads((work / "content-review.json").read_text())
    frames = json.loads((work / "render-review.json").read_text())
    board = json.loads((work / "storyboard.json").read_text())
    lesson = json.loads((work / "pack/lesson.json").read_text())
    if (
        not content.get("passed")
        or content.get("issues")
        or content.get("storyboard_digest") != digest(board)
        or not frames.get("passed")
        or frames.get("issues")
        or frames.get("lesson_digest") != digest(lesson)
        or frames.get("renderer_source") != job["recipe"]["renderer_source"]
    ):
        raise ValueError("Automated private publication checks did not pass")
    review = {
        "policy": "private_demo_automated_v1",
        "content": True,
        "visuals": True,
        "audio_sync": True,
        "assets": True,
        "video_sha256": manifest["quality"]["sha256"],
        "artifact_digests": manifest["artifact_digests"],
    }
    return publish_validated_variant(
        repository, storage, job, brief, work, manifest, review, automated_private=True
    )
