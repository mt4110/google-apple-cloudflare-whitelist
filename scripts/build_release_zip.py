#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import pathlib
import zipfile

DEFAULT_EXCLUDES = (
    ".git/*",
    ".venv/*",
    "venv/*",
    "*.egg-info/*",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    "whitelist_output/*",
    "rendered_assets/*",
    "dist/*",
    "build/*",
    ".pytest_cache/*",
    ".mypy_cache/*",
    ".ruff_cache/*",
    ".DS_Store",
    "*.zip",
)


def should_exclude(relative_path: str, patterns: tuple[str, ...]) -> bool:
    normalized = relative_path.replace("\\", "/")
    parts = normalized.split("/")
    for part in parts:
        if part == "__pycache__":
            return True
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def build_release_zip(
    source_dir: pathlib.Path,
    output_path: pathlib.Path,
    root_dir_name: str | None = None,
    exclude_patterns: tuple[str, ...] = DEFAULT_EXCLUDES,
) -> pathlib.Path:
    source_dir = source_dir.resolve()
    root_dir_name = root_dir_name or source_dir.name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            relative_path = path.relative_to(source_dir).as_posix()
            if should_exclude(relative_path, exclude_patterns):
                continue
            archive_name = f"{root_dir_name}/{relative_path}"
            archive.write(path, archive_name)

    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a clean release zip from a working tree.")
    parser.add_argument("--source-dir", type=pathlib.Path, default=pathlib.Path("."), help="Project root to package.")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="Path to the output zip file.")
    parser.add_argument("--root-dir-name", default=None, help="Top-level directory name inside the zip.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = build_release_zip(
        source_dir=args.source_dir,
        output_path=args.output,
        root_dir_name=args.root_dir_name,
    )
    print(output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
