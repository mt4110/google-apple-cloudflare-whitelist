from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from google_apple_whitelist import cli
from google_apple_whitelist.core import FetchSummary
from google_apple_whitelist.rendering import RenderSummary


class CliTests(unittest.TestCase):
    def test_fetch_command_invokes_run_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = FetchSummary(
                output_dir=Path(tmp),
                goog_creation_time="goog-time",
                cloud_creation_time="cloud-time",
                cloudflare_retrieved_at="2026-04-02T00:00:00Z",
                counts={"google_owned_ipv4_prefixes": 1},
            )
            with mock.patch("google_apple_whitelist.cli.run_fetch", return_value=summary) as mocked:
                exit_code = cli.main(["fetch", "--output-dir", tmp, "--timeout", "15", "--quiet"])

        self.assertEqual(exit_code, 0)
        mocked.assert_called_once_with(
            output_dir=Path(tmp),
            apple_ranges=None,
            include_cloudflare=True,
            timeout=15,
        )

    def test_render_command_invokes_render_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = RenderSummary(
                input_dir=Path(tmp),
                output_dir=Path(tmp) / "rendered",
                dataset="combined_google_services_plus_apple",
                rendered_files=("nginx/combined_google_services_plus_apple_allow.conf",),
            )
            with mock.patch("google_apple_whitelist.cli.render_artifacts", return_value=summary) as mocked:
                exit_code = cli.main(["render", "--input-dir", tmp, "--output-dir", f"{tmp}/rendered", "--quiet"])

        self.assertEqual(exit_code, 0)
        mocked.assert_called_once()

    def test_daemon_command_runs_requested_number_of_times(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = FetchSummary(
                output_dir=Path(tmp),
                goog_creation_time="goog-time",
                cloud_creation_time="cloud-time",
                cloudflare_retrieved_at=None,
                counts={"google_owned_ipv4_prefixes": 1},
            )
            with mock.patch("google_apple_whitelist.cli.run_fetch", return_value=summary) as mocked_fetch:
                exit_code = cli.main(
                    [
                        "daemon",
                        "--output-dir",
                        tmp,
                        "--interval-seconds",
                        "1",
                        "--max-runs",
                        "2",
                        "--quiet",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(mocked_fetch.call_count, 2)

    def test_bad_apple_ranges_file_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad_file = Path(tmp) / "apple.json"
            bad_file.write_text('{"ipv4": ["not-a-cidr"]}', encoding="utf-8")
            exit_code = cli.main(["fetch", "--output-dir", tmp, "--apple-ranges-file", str(bad_file), "--quiet"])

        self.assertEqual(exit_code, 1)

    def test_version_flag_prints_version(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["--version"])

        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("google-apple-whitelist", stdout.getvalue())
