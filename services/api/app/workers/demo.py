"""Bounded background workers for the same modular API, with Atlas-backed queues."""

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from app.core.environment import ROOT
from app.full_runtime import components
from app.modules.videos.service import run_once as render_once
from app.workers.queue import JobQueue
from app.workers.runner import Worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--academic-workers", type=int, choices=range(1, 5), default=3)
    parser.add_argument("--video-workers", type=int, choices=range(1, 4), default=2)
    args = parser.parse_args()
    database, connections, academics, videos, pipeline = components()
    database.verify_ready()
    stop = Event()

    def work():
        worker = Worker(JobQueue(database))
        worker.register("instagram.refresh", pipeline.social.refresh)
        if os.getenv("GEMINI_API_KEY"):
            worker.register("canvas.sync", pipeline.sync)
            worker.register("learning.prepare", pipeline.prepare)
            worker.register("learning.render", pipeline.render)
            worker.register("learning.reteach.requested", pipeline.reteach)
        while not stop.is_set():
            if not worker.handlers or not worker.run_once():
                stop.wait(1)

    def render():
        artifact_root = ROOT / ".local/video-runs/worker"
        artifact_root.mkdir(parents=True, exist_ok=True)
        while not stop.is_set():
            if not render_once(
                videos.repository, artifact_root, private_demo_storage=videos.storage
            ):
                stop.wait(1)

    pool = ThreadPoolExecutor(max_workers=args.academic_workers + args.video_workers)
    futures = [pool.submit(work) for _ in range(args.academic_workers)]
    futures += [pool.submit(render) for _ in range(args.video_workers)]
    try:
        next_social_refresh = 0
        while not stop.wait(1):
            if time.monotonic() >= next_social_refresh:
                pipeline.social.schedule()
                next_social_refresh = time.monotonic() + 30
            for future in futures:
                if future.done():
                    future.result()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        pool.shutdown(wait=True)
        database.close()


if __name__ == "__main__":
    main()
