"""Owner-scoped background progress without provider secrets or raw sources."""

import os
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Header

from app.core import collections as tables
from app.core import idempotency
from app.core.dependencies import CurrentUser
from app.modules.videos.repository import AtlasVideoRepository


def retry_preparation(database, owner, key):
    def retry(tx):
        prior = idempotency.lookup(tx, owner, "preparation/retry", key, {})
        if prior is not None:
            return prior
        connection = tx.find_one(
            tables.connections, {"user_id": owner, "provider": "canvas", "status": "connected"}
        )
        queued = 0
        for job in tx.find(
            tables.jobs,
            {
                "owner_user_id": owner,
                "state": "failed",
                "job_type": {"$in": ["canvas.sync", "learning.prepare", "learning.render"]},
            },
            limit=100,
        ):
            if job.get("manual_retry_count", 0) >= 3:
                continue
            connection_id = job["input_ref"].get("connection_id")
            if connection_id and (not connection or connection["connection_id"] != connection_id):
                continue
            queued += tx.update(
                tables.jobs,
                {"owner_user_id": owner, "job_id": job["job_id"], "state": "failed"},
                {
                    "state": "queued",
                    "attempt_count": 0,
                    "available_at": 0,
                    "lease_until": None,
                    "lease_token": None,
                    "error_code": None,
                    "manual_retry_count": job.get("manual_retry_count", 0) + 1,
                },
            ).rowcount
        repository = AtlasVideoRepository(database.mongo)
        videos = database.mongo.video_generation_jobs.find(
            {"owner_user_id": owner, "state": "failed"}, {"job_id": 1}, session=tx.session
        ).limit(100)
        for job in videos:
            queued += int(repository.retry_failed(job["job_id"], owner, session=tx.session))
        response = {"schema_version": "1", "queued_jobs": queued}
        idempotency.remember(tx, owner, "preparation/retry", key, {}, response)
        return response

    return database.run(owner, retry)


def create_router(database):
    router = APIRouter(tags=["preparation"])

    @router.get("/v1/preparation")
    def preparation(user: CurrentUser):
        owner = user.user_id
        jobs = database.read(
            lambda tx: tx.find(
                tables.jobs,
                {
                    "owner_user_id": owner,
                    "job_type": {"$in": ["canvas.sync", "learning.prepare", "learning.render"]},
                },
                limit=1000,
            )
        )
        videos = list(
            database.mongo.video_generation_jobs.find({"owner_user_id": owner}, {"state": 1}).limit(
                1000
            )
        )
        return {
            "schema_version": "1",
            "academic_generation_configured": bool(os.getenv("GEMINI_API_KEY")),
            "imports_and_lessons": dict(Counter(row["state"] for row in jobs)),
            "videos": dict(Counter(row["state"] for row in videos)),
        }

    @router.post("/v1/preparation/retry", status_code=202)
    def retry(
        user: CurrentUser, idempotency_key: Annotated[str, Header(min_length=1, max_length=128)]
    ):
        return retry_preparation(database, user.user_id, idempotency_key)

    return router
