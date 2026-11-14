from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, Thread

from app.workers.queue import JobQueue


@dataclass(frozen=True)
class JobContext:
    job_id: str
    owner_user_id: str
    input_ref: dict
    heartbeat: Callable[[], bool]


class Worker:
    """Handlers heartbeat between bounded stages and make side effects idempotent.

    A lease is fenced by a random token. Lost/cancelled jobs cannot report success.
    The worker never claims job types for which no handler has been registered.
    """

    def __init__(self, queue: JobQueue):
        self.queue = queue
        self.handlers: dict[str, Callable[[JobContext], dict]] = {}

    def register(self, job_type: str, handler: Callable[[JobContext], dict]) -> None:
        if job_type in self.handlers:
            raise ValueError(f"Handler already registered: {job_type}")
        self.handlers[job_type] = handler

    def run_once(self) -> bool:
        job = self.queue.claim(list(self.handlers))
        if job is None:
            return False
        context = JobContext(
            job["job_id"],
            job["owner_user_id"],
            job["input_ref"],
            lambda: self.queue.heartbeat(job["job_id"], job["lease_token"]),
        )
        stop, lost = Event(), Event()

        def maintain_lease():
            while not stop.wait(20):
                try:
                    if not context.heartbeat():
                        lost.set()
                        return
                except Exception:
                    lost.set()
                    return

        heartbeat_thread = Thread(target=maintain_lease, daemon=True)
        heartbeat_thread.start()
        try:
            result = self.handlers[job["job_type"]](context)
        except Exception:
            # Provider exceptions often contain URLs/headers/prompts: persist a code only.
            self.queue.fail(job["job_id"], job["lease_token"])
        else:
            if not lost.is_set():
                self.queue.finish(job["job_id"], job["lease_token"], result)
        finally:
            stop.set()
            heartbeat_thread.join(timeout=2)
        return True
