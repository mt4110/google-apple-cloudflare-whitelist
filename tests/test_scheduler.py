from __future__ import annotations

import unittest
from unittest import mock

from google_apple_whitelist.scheduler import run_interval


class SchedulerTests(unittest.TestCase):
    def test_run_interval_calls_job_repeatedly(self) -> None:
        calls: list[int] = []

        def job() -> None:
            calls.append(1)

        with mock.patch("time.sleep") as mocked_sleep:
            completed = run_interval(job, interval_seconds=10, max_runs=3)

        self.assertEqual(completed, 3)
        self.assertEqual(len(calls), 3)
        self.assertEqual(mocked_sleep.call_count, 2)

    def test_invalid_interval_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            run_interval(lambda: None, interval_seconds=0, max_runs=1)
