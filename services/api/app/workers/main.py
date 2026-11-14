"""Worker entry point. Only explicitly registered domain handlers run."""

import argparse
import importlib
import time

from app.core.config import Settings
from app.core.database import Database
from app.workers.queue import JobQueue
from app.workers.runner import Worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registrar", help="Trusted Python module:function registering handlers")
    parser.add_argument("--fixture-echo", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    database = Database(settings)
    database.initialize_local()
    worker = Worker(JobQueue(database))
    if args.fixture_echo:
        if settings.environment not in {"test", "fixture"}:
            parser.error("Fixture handlers require fixture/test mode")
        worker.register("fixture.echo", lambda context: {"echo_ref": context.input_ref["echo_ref"]})
    if args.registrar:
        module, function = args.registrar.split(":", 1)
        getattr(importlib.import_module(module), function)(worker)
    if not worker.handlers:
        parser.error("Register at least one handler; unregistered jobs are never claimed")
    try:
        while True:
            worked = worker.run_once()
            if args.once:
                break
            if not worked:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        database.close()


if __name__ == "__main__":
    main()
