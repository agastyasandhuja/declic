from concurrent.futures import ThreadPoolExecutor

import pytest

from app.core import collections
from app.core.database import Database
from app.core.errors import APIError
from app.core.events import consume_one, publish
from app.workers.queue import JobQueue, enqueue
from app.workers.runner import Worker


def queue_job(database, clock, key="one", **kwargs):
    return database.run(
        "user_demo_01",
        lambda unit: enqueue(
            unit,
            owner_user_id="user_demo_01",
            job_type="fixture.echo",
            dedupe_key=key,
            input_ref={"echo_ref": key},
            now=clock(),
            **kwargs,
        ),
    )


def test_unique_enqueue_and_restart_durability(database, clock):
    first = queue_job(database, clock)
    assert queue_job(database, clock) == first
    restarted = Database(database.settings)
    job = JobQueue(restarted, clock).claim(["fixture.echo"])
    assert job["job_id"] == first
    assert job["attempt_count"] == 1
    assert JobQueue(database, clock).claim(["fixture.echo"]) is None
    restarted.close()


def test_concurrent_claims_do_not_duplicate_work(database, clock):
    ids = {queue_job(database, clock, str(i)) for i in range(8)}
    queue = JobQueue(database, clock)
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = list(pool.map(lambda _: queue.claim(["fixture.echo"]), range(12)))
    assert {j["job_id"] for j in jobs if j} == ids
    assert len([j for j in jobs if j]) == 8


def test_concurrent_enqueues_share_one_durable_job(database, clock):
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: queue_job(database, clock, "same"), range(8)))
    assert len(set(ids)) == 1
    with database.transaction() as unit:
        assert unit.count(collections.jobs) == 1


def test_expired_lease_fences_stale_worker_and_exhaustion_is_terminal(database, clock):
    job_id = queue_job(database, clock, max_attempts=2)
    queue = JobQueue(database, clock)
    first = queue.claim(["fixture.echo"], lease_seconds=5)
    clock.advance(6)
    second = queue.claim(["fixture.echo"], lease_seconds=5)
    assert second["attempt_count"] == 2
    assert not queue.finish(job_id, first["lease_token"], {"result": "stale"})
    assert not queue.heartbeat(job_id, first["lease_token"])
    clock.advance(6)
    assert queue.claim(["fixture.echo"]) is None
    with database.transaction() as unit:
        assert unit.find_one(collections.jobs, {"job_id": job_id})["state"] == "failed"


def test_handler_retry_sanitization_and_cancellation(database, clock):
    job_id = queue_job(database, clock)
    queue = JobQueue(database, clock)
    worker = Worker(queue)
    assert not worker.run_once()  # Unregistered jobs stay queued.

    def broken(context):
        raise RuntimeError("secret provider token and private prompt")

    worker.register("fixture.echo", broken)
    assert worker.run_once()
    with database.transaction() as unit:
        row = unit.find_one(collections.jobs, {"job_id": job_id})
        assert row["state"] == "retry_wait"
        assert "secret" not in str(row)
    assert not queue.cancel("user_demo_02", job_id)
    assert queue.cancel("user_demo_01", job_id)
    clock.advance(10)
    assert queue.claim(["fixture.echo"]) is None


def test_job_deduplication_key_cannot_change_inputs(database, clock):
    queue_job(database, clock)
    with pytest.raises(APIError) as error:
        database.run(
            "user_demo_01",
            lambda unit: enqueue(
                unit,
                owner_user_id="user_demo_01",
                job_type="fixture.echo",
                dedupe_key="one",
                input_ref={"echo_ref": "different"},
                now=clock(),
            ),
        )
    assert error.value.code == "JOB_KEY_CONFLICT"


def test_outbox_and_consumer_receipts_are_atomic(database, clock):
    def produce(unit):
        publish(
            unit,
            event_type="fixture.ready",
            user_id="user_demo_01",
            aggregate_id="one",
            revision=1,
            payload={"record_id": "one"},
            now=clock(),
        )
        raise RuntimeError("abort producer")

    with pytest.raises(RuntimeError):
        database.run("user_demo_01", produce)
    with database.transaction() as unit:
        assert unit.count(collections.outbox) == 0
    database.run(
        "user_demo_01",
        lambda unit: publish(
            unit,
            event_type="fixture.ready",
            user_id="user_demo_01",
            aggregate_id="one",
            revision=1,
            payload={"record_id": "one"},
            now=clock(),
        ),
    )

    def handler(unit, event):
        enqueue(
            unit,
            owner_user_id=event["actor_user_id"],
            job_type="fixture.echo",
            dedupe_key=event["event_id"],
            input_ref={"echo_ref": "one"},
            now=clock(),
        )

    def consume():
        return database.run(None, lambda unit: consume_one(unit, "test", "fixture.ready", handler))

    assert consume()
    assert not consume()
    with database.transaction() as unit:
        assert unit.count(collections.jobs) == 1
        assert unit.count(collections.processed) == 1
