"""Provider diagnostic capture must not corrupt process-global output streams."""

import logging
import sys
from threading import Event, Thread

from app.modules.entertainment.instagram import quiet_instagram


def test_overlapping_callers_serialize_capture_and_restore_open_streams():
    original_out, original_err = sys.stdout, sys.stderr
    original_logging = logging.root.manager.disable
    first_entered, second_attempted, second_entered, first_exited = (Event() for _ in range(4))
    overlap = []

    def first():
        with quiet_instagram():
            first_entered.set()
            assert second_attempted.wait(2)
            # Without serialization the second caller enters while the first
            # capture is active; first-then-second exit restores a closed sink.
            overlap.append(second_entered.wait(0.1))
        first_exited.set()

    def second():
        assert first_entered.wait(2)
        second_attempted.set()
        with quiet_instagram():
            second_entered.set()
            assert first_exited.wait(2)

    threads = [Thread(target=first), Thread(target=second)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        assert all(not thread.is_alive() for thread in threads)
        assert overlap == [False]
        assert sys.stdout is original_out and not sys.stdout.closed
        assert sys.stderr is original_err and not sys.stderr.closed
        assert logging.root.manager.disable == original_logging
    finally:
        # Keep a regression failure from damaging pytest's own capture session.
        sys.stdout, sys.stderr = original_out, original_err
        logging.disable(original_logging)
