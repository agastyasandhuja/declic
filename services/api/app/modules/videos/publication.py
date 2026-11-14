"""Trusted publication: uploaded objects are private, readiness is an Atlas transaction."""

import hashlib
import mimetypes
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

from .generation.providers import ProviderError, request_json
from .media import sha256
from .pipeline import artifact_digests


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
        response = self.client.post(url, content=data, headers=headers)
        if response.status_code not in {200, 201, 400, 409}:
            raise ProviderError("STORAGE_UPLOAD_FAILED", response.status_code >= 500)
        # Verify bytes even after an ambiguous response/retry; never trust success alone.
        h = hashlib.sha256()
        count = 0
        with self.client.stream(
            "GET",
            f"{self.url}/storage/v1/object/authenticated/{self.bucket}/{key}",
            headers=self.headers,
        ) as check:
            if check.status_code != 200:
                raise ProviderError("STORAGE_VERIFY_FAILED")
            for chunk in check.iter_bytes():
                count += len(chunk)
                if count > len(data):
                    raise ProviderError("STORAGE_SIZE_MISMATCH")
                h.update(chunk)
        if count != len(data) or h.hexdigest() != sha256(file):
            raise ProviderError("STORAGE_DIGEST_MISMATCH")
        return {"key": key, "sha256": h.hexdigest(), "size": count}

    def signed_url(self, key):
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
        return self.url + "/storage/v1" + signed


def publish_validated_variant(repository, storage, job, brief, work: Path, manifest, review):
    quality = manifest["quality"]
    required = {"content", "visuals", "audio_sync", "assets"}
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
        "quality_checks": {**quality, "human_review": "approved"},
        "created_at": now,
        "ready_at": now,
    }
    repository.publish(job["job_id"], job["fence"], variant)
    return variant
