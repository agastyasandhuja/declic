"""Single-process development job adapter for domain router and worker tests."""
from threading import RLock
from uuid import uuid4


class DuplicateJob(ValueError):
    pass


class LocalAcademicJobs:
    def __init__(self):
        self._lock = RLock()
        self._jobs = {}
        self._keys = {}

    def enqueue(self, owner, kind, key, fingerprint, background, run):
        with self._lock:
            index = owner, kind, key
            if index in self._keys:
                previous, job_id = self._keys[index]
                if previous != fingerprint:
                    raise DuplicateJob("idempotency key reused for different input")
                return self.get(owner, job_id)
            job_id = str(uuid4())
            self._keys[index] = fingerprint, job_id
            self._jobs[owner, job_id] = {
                "schema_version": "1", "job_id": job_id, "state": "queued", "courses": [],
            }
            background.add_task(self._execute, owner, job_id, run)
            return self.get(owner, job_id)

    def _execute(self, owner, job_id, run):
        with self._lock:
            job = self._jobs[owner, job_id]
            job["state"] = "running"
        try:
            profile = run()
        except Exception:
            with self._lock:
                job.update(state="failed", error_code="ACADEMIC_IMPORT_FAILED")
        else:
            with self._lock:
                job.update(state="succeeded", courses=[
                    {"course_id": row["course_id"], "import_status": row["import_status"]}
                    for row in profile["courses"]
                ])

    def get(self, owner, job_id):
        with self._lock:
            job = self._jobs.get((owner, job_id))
            return dict(job) if job else None
