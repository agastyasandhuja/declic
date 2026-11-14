"""Read-only job projection for mobile progress; worker callables are never serialized."""

from app.core import collections as tables
from app.core.errors import APIError


class AcademicJobs:
    def __init__(self, database):
        self.database = database

    def get(self, owner, job_id):
        row = self.database.read(
            lambda tx: tx.find_one(tables.jobs, {"owner_user_id": owner, "job_id": job_id})
        )
        if not row:
            return None
        return {
            "schema_version": "1",
            "job_id": job_id,
            "state": row["state"],
            "courses": (row.get("output_ref") or {}).get("courses", []),
            "error_code": row.get("error_code"),
        }

    def enqueue(self, *args, **kwargs):
        # The legacy upload callback requires an owned durable artifact adapter.
        raise APIError(503, "UPLOAD_UNAVAILABLE", "Connect Canvas using your personal access token")
