"""Public service surface for the academic/API integrator; identity is a trusted argument."""

import time
from datetime import UTC, datetime, timedelta
from threading import Event, Thread

from .generation.providers import ProviderError
from .models import Brief
from .pipeline import generate, generation_recipe
from .repository import StaleLease


class VideoService:
    def __init__(self, repository, academic_resolver, storage=None):
        self.repository, self.academics, self.storage = repository, academic_resolver, storage

    def request_generation(self, actor, lesson_request_id, format_id, recipe):
        # Resolver must check plan/profile revision, binding ownership and source access.
        brief = Brief.model_validate(
            self.academics.resolve_generation_brief(actor, lesson_request_id, format_id)
        )
        if brief.format_id != format_id or (
            brief.scope == "private" and brief.owner_user_id != actor
        ):
            raise PermissionError("Inaccessible lesson")
        key = brief.generation_key(recipe)
        ready = self.repository.ready(key, actor)
        if ready:
            return {"state": "ready", "video_id": ready["video_id"]}
        # Pending generic candidates remain owner-scoped until approved publication.
        job = self.repository.enqueue(
            key + (":" + actor if brief.scope == "shared_generic_candidate" else ""),
            actor,
            brief.model_dump(),
            recipe,
        )
        return {"state": job["state"], "job_id": job["job_id"]}

    def get_generation_status(self, actor, job_id):
        job = self.repository.get(job_id, actor)
        if not job:
            raise LookupError("Job not found")
        return {k: job[k] for k in ("job_id", "state", "stage", "attempt")}

    def cancel_generation(self, actor, job_id):
        return self.repository.cancel(job_id, actor)

    def get_video(self, actor, video_id):
        video = self.repository.video(video_id, actor)
        if not video:
            raise LookupError("Video not found")
        # Shared response never leaks another learner's request or internal asset metadata.
        fields = {
            "schema_version",
            "video_id",
            "objective_id",
            "format_id",
            "teaching_approach",
            "level",
            "language",
            "notation",
            "scope",
            "status",
            "title",
            "learning_goal",
            "duration_seconds",
            "asset_id",
            "template_version",
            "generation_version",
            "created_at",
            "ready_at",
        }
        result = {k: v for k, v in video.items() if k in fields}
        result["lesson_request_id"] = (
            video["lesson_request_id"] if video["scope"] == "private" else None
        )
        result["playback"] = self.playback(actor, video_id)
        result["thumbnail_url"] = self.storage.signed_url(video["assets"]["thumbnail"]["key"])
        result["captions_ref"] = self.storage.signed_url(video["assets"]["captions"]["key"])
        return result

    def playback(self, actor, video_id):
        video = self.repository.video(video_id, actor)
        if not video:
            raise LookupError("Video not found")
        return {
            "kind": "mp4",
            "asset_id": video["asset_id"],
            "url": self.storage.signed_url(video["assets"]["video"]["key"]),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=600)).isoformat(),
            "mime_type": "video/mp4",
        }


def run_once(repository, artifact_root, *, fixture=False, private_demo_storage=None, job_ids=None):
    job = repository.claim() if job_ids is None else repository.claim(job_ids=job_ids)
    if not job:
        return False
    stop, lost = Event(), Event()

    def heartbeat():
        while not stop.wait(20):
            try:
                repository.update(job["job_id"], job["fence"], {"lease_until": time.time() + 90})
            except Exception:
                lost.set()
                return

    def stage(value):
        if lost.is_set():
            raise StaleLease("Lease lost")
        repository.update(job["job_id"], job["fence"], {"stage": value})

    thread = Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        brief = Brief.model_validate(job["brief"])
        if job["recipe"] != generation_recipe(
            fixture=fixture, custom_scene=job["recipe"].get("custom_scene", False)
        ):
            raise ValueError("Worker recipe differs from queued recipe")

        def check_cancelled():
            if lost.is_set():
                raise StaleLease("Lease lost")

        result = generate(
            brief,
            artifact_root / job["job_id"],
            fixture=fixture,
            custom_scene=job["recipe"].get("custom_scene", False),
            stage=stage,
            check_cancelled=check_cancelled,
        )
        if (
            private_demo_storage is not None
            and not fixture
            and brief.scope == "private"
            and brief.format_id != "math_explainer"
        ):
            from .publication import publish_private_demo

            stage("publishing")
            publish_private_demo(
                repository, private_demo_storage, job, brief, artifact_root / job["job_id"], result
            )
            return True
        repository.update(
            job["job_id"],
            job["fence"],
            {
                "state": "awaiting_review",
                "stage": "validating",
                "result_ref": job["job_id"],
                "video_sha256": result["quality"]["sha256"],
            },
        )
    except StaleLease:
        pass
    except Exception as error:
        retry = isinstance(error, ProviderError) and error.retryable and job["attempt"] < 2
        try:
            repository.update(
                job["job_id"],
                job["fence"],
                {
                    "state": "retry_wait" if retry else "failed",
                    "available_at": time.time() + 10,
                    "error_code": error.code
                    if isinstance(error, ProviderError)
                    else "GENERATION_FAILED",
                },
            )
        except StaleLease:
            pass
    finally:
        stop.set()
        thread.join(timeout=2)
    return True
