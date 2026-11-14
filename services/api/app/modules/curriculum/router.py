"""Academic API routes composed by the shared API factory."""
import hashlib
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header
from pydantic import BaseModel, ConfigDict, Field

from app.core.dependencies import CurrentUser
from app.core.errors import APIError

from ..canvas.ingestion.uploads import UploadRejected, store_upload, validate_upload
from .corrections import RevisionConflict
from .jobs import DuplicateJob
from .sources import SourceResolver
from .store import LOCK

IdempotencyKey = Annotated[str, Header(min_length=1, max_length=128)]


class Corrections(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    changes: list[dict] = Field(min_length=1, max_length=100)


class Upload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_label: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=30_000)


def create_router(service, jobs):
    router = APIRouter(prefix="/v1/academics", tags=["academics"])

    @router.get("/profile")
    def get_profile(user: CurrentUser):
        profile = service.get_profile(user.user_id)
        if profile is None:
            raise APIError(404, "PROFILE_UNAVAILABLE", "Academic profile unavailable")
        return profile

    @router.patch("/profile")
    def patch_profile(user: CurrentUser, body: Corrections):
        try:
            return service.apply_corrections(user.user_id, body.expected_revision, body.changes)
        except RevisionConflict:
            raise APIError(409, "PROFILE_REVISION_CONFLICT", "Profile revision has changed") from None
        except LookupError:
            raise APIError(404, "PROFILE_UNAVAILABLE", "Profile or assessment unavailable") from None
        except ValueError:
            raise APIError(422, "INVALID_CORRECTION", "Invalid academic correction") from None

    @router.get("/courses/{course_id}/plan")
    def get_plan(user: CurrentUser, course_id: str):
        for plan in service.get_validated_plans(user.user_id):
            if plan["course_id"] == course_id:
                return plan
        raise APIError(404, "PLAN_UNAVAILABLE", "Lesson plan unavailable")

    @router.get("/jobs/{job_id}")
    def get_job(user: CurrentUser, job_id: str):
        job = jobs.get(user.user_id, job_id)
        if job is None:
            raise APIError(404, "JOB_UNAVAILABLE", "Academic job unavailable")
        return job

    @router.post("/uploads", status_code=202)
    def upload(user: CurrentUser, body: Upload, background: BackgroundTasks,
               idempotency_key: IdempotencyKey):
        data = body.content.encode()
        try:
            suffix = validate_upload(body.filename, data)
            if suffix not in {".txt", ".md"} or not body.course_label.strip():
                raise UploadRejected("text upload required")
        except UploadRejected:
            raise APIError(422, "INVALID_UPLOAD", "Upload a course-labeled text or Markdown file") from None

        def run():
            with LOCK:
                store_upload(user_id=user.user_id, course_label=body.course_label,
                             filename=body.filename, data=data, storage_dir=service.storage_dir)
            return service.import_profile(user.user_id, SourceResolver(user.user_id, service.storage_dir))

        fingerprint = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        try:
            return jobs.enqueue(user.user_id, "academic_upload", idempotency_key,
                                fingerprint, background, run)
        except DuplicateJob:
            raise APIError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key already used") from None

    return router
