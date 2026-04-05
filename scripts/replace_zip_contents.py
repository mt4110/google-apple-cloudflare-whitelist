#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import shutil
import tempfile
import zipfile

from build_release_zip import build_release_zip, DEFAULT_EXCLUDES


def detect_root_dir_name(zip_path: pathlib.Path) -> str | None:
    with zipfile.ZipFile(zip_path) as archive:
        top_level = {pathlib.PurePosixPath(name).parts[0] for name in archive.namelist() if name and not name.startswith("__MACOSX/")}
    if len(top_level) == 1:
        return next(iter(top_level))
    return None


def replace_zip_contents(
    base_zip: pathlib.Path,
    source_dir: pathlib.Path,
    output_path: pathlib.Path,
    root_dir_name: str | None = None,
) -> pathlib.Path:
    chosen_root = root_dir_name or detect_root_dir_name(base_zip) or source_dir.resolve().name

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = pathlib.Path(temp_dir_str)
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(base_zip) as archive:
            archive.extractall(extract_dir)

        target_root = extract_dir / chosen_root
        if target_root.exists():
            shutil.rmtree(target_root)

        shutil.copytree(
            source_dir.resolve(),
            target_root,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "venv",
                "*.egg-info",
                "__pycache__",
                "*.pyc",
                "*.pyo",
                "whitelist_output",
                "rendered_assets",
                "dist",
                "build",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                ".DS_Store",
                "*.zip",
            ),
        )

        return build_release_zip(
            source_dir=target_root,
            output_path=output_path,
            root_dir_name=chosen_root,
            exclude_patterns=DEFAULT_EXCLUDES,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract an existing zip, replace its project tree with the current working tree, and write a new clean zip."
    )
    parser.add_argument("--base-zip", type=pathlib.Path, required=True, help="Existing zip to use as the starting point.")
    parser.add_argument("--source-dir", type=pathlib.Path, default=pathlib.Path("."), help="Current project root.")
    parser.add_argument("--output", type=pathlib.Path, required=True, help="Path to the output zip file.")
    parser.add_argument("--root-dir-name", default=None, help="Optional top-level directory name inside the zip.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = replace_zip_contents(
        base_zip=args.base_zip,
        source_dir=args.source_dir,
        output_path=args.output,
        root_dir_name=args.root_dir_name,
    )
    print(output_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
