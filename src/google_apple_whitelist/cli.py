from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Sequence

from . import __version__
from .core import AppleRanges, FetchSummary, run_fetch
from .rendering import RenderSummary, render_artifacts
from .scheduler import run_interval


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="google-apple-whitelist",
        description=(
            "Fetch public IP feeds for Google, Apple, and optionally Cloudflare, "
            "then render network allowlist helper outputs."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch allowlists once")
    _add_common_fetch_options(fetch_parser)
    fetch_parser.set_defaults(handler=_handle_fetch)

    render_parser = subparsers.add_parser("render", help="Render nginx/ipset/nftables helper files")
    render_parser.add_argument(
        "--input-dir",
        type=pathlib.Path,
        default=pathlib.Path("./whitelist_output"),
        help="Directory containing the fetched txt files (default: ./whitelist_output)",
    )
    render_parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=pathlib.Path("./rendered_assets"),
        help="Directory to write rendered helper files into (default: ./rendered_assets)",
    )
    render_parser.add_argument(
        "--dataset",
        default="combined_google_services_plus_apple",
        help=(
            "Dataset prefix to render from whitelist_output, for example "
            "combined_google_services_plus_apple (default)."
        ),
    )
    render_parser.add_argument(
        "--set-prefix",
        default="gaw",
        help="Short prefix used in generated ipset/nftables set names (default: gaw)",
    )
    render_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the summary output.",
    )
    render_parser.set_defaults(handler=_handle_render)

    daemon_parser = subparsers.add_parser("daemon", help="Run periodic refreshes in a Python loop")
    _add_common_fetch_options(daemon_parser)
    daemon_parser.add_argument(
        "--interval-seconds",
        type=int,
        default=86400,
        help="Seconds between refreshes (default: 86400)",
    )
    daemon_parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    daemon_parser.set_defaults(handler=_handle_daemon)
    return parser


def _add_common_fetch_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=pathlib.Path("./whitelist_output"),
        help="Directory to write output files into (default: ./whitelist_output)",
    )
    parser.add_argument(
        "--apple-ranges-file",
        type=pathlib.Path,
        default=None,
        help="Optional JSON file with Apple ranges in the form {'ipv4': [...], 'ipv6': [...]}.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Network timeout in seconds for feed downloads (default: 30)",
    )
    parser.add_argument(
        "--include-cloudflare",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include Cloudflare origin IP ranges in the generated output files (default: enabled)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the summary output.",
    )


def _load_apple_ranges(path: pathlib.Path | None) -> AppleRanges | None:
    if path is None:
        return None
    return AppleRanges.from_file(path)


def _print_fetch_summary(summary: FetchSummary) -> None:
    print(f"Wrote files to: {summary.output_dir.resolve()}")
    print(f"- goog.json creationTime:  {summary.goog_creation_time}")
    print(f"- cloud.json creationTime: {summary.cloud_creation_time}")
    print(f"- cloudflare retrieved_at: {summary.cloudflare_retrieved_at}")
    for key, value in sorted(summary.counts.items()):
        print(f"- {key}: {value}")


def _print_render_summary(summary: RenderSummary) -> None:
    print(f"Read files from: {summary.input_dir.resolve()}")
    print(f"Wrote rendered files to: {summary.output_dir.resolve()}")
    print(f"- dataset: {summary.dataset}")
    for relative_path in summary.rendered_files:
        print(f"- {relative_path}")


def _handle_fetch(args: argparse.Namespace) -> int:
    apple_ranges = _load_apple_ranges(args.apple_ranges_file)
    summary = run_fetch(
        output_dir=args.output_dir,
        apple_ranges=apple_ranges,
        include_cloudflare=args.include_cloudflare,
        timeout=args.timeout,
    )
    if not args.quiet:
        _print_fetch_summary(summary)
    return 0


def _handle_render(args: argparse.Namespace) -> int:
    summary = render_artifacts(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        dataset=args.dataset,
        set_prefix=args.set_prefix,
    )
    if not args.quiet:
        _print_render_summary(summary)
    return 0


def _handle_daemon(args: argparse.Namespace) -> int:
    apple_ranges = _load_apple_ranges(args.apple_ranges_file)

    def job() -> None:
        summary = run_fetch(
            output_dir=args.output_dir,
            apple_ranges=apple_ranges,
            include_cloudflare=args.include_cloudflare,
            timeout=args.timeout,
        )
        if not args.quiet:
            _print_fetch_summary(summary)

    run_interval(job=job, interval_seconds=args.interval_seconds, max_runs=args.max_runs)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover - defensive CLI wrapper
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
