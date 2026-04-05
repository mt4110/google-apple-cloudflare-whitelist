from __future__ import annotations

import time
from collections.abc import Callable


class SchedulerStopped(Exception):
    """Raised when a scheduled loop is interrupted."""


def run_interval(job: Callable[[], None], interval_seconds: int, max_runs: int | None = None) -> int:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than 0")
    if max_runs is not None and max_runs <= 0:
        raise ValueError("max_runs must be greater than 0 when provided")

    completed = 0
    while True:
        job()
        completed += 1
        if max_runs is not None and completed >= max_runs:
            return completed
        time.sleep(interval_seconds)
