#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import shutil
import tempfile
import zipfile

def detect_root_dir_name(zip_path: pathlib.Path) -> str | None:
    with zipfile.ZipFile(zip_path) as archive:
        top_level = {
            pathlib.PurePosixPath(name).parts[0]
            for name in archive.namelist()
            if name and not name.startswith("__MACOSX/") and len(pathlib.PurePosixPath(name).parts) > 1
        }
    if len(top_level) == 1:
        return next(iter(top_level))
    return None


def _extract_archive_safely(archive: zipfile.ZipFile, destination: pathlib.Path) -> None:
    root = destination.resolve()
    for member in archive.infolist():
        member_name = member.filename.replace("\\", "/")
        if not member_name:
            continue

        target_path = (destination / pathlib.PurePosixPath(member_name)).resolve()
        try:
            target_path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Refusing to extract unsafe path from zip: {member.filename}") from exc

        if member.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as src, target_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def _write_zip_from_directory(source_dir: pathlib.Path, output_path: pathlib.Path) -> pathlib.Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(source_dir).as_posix())
    return output_path


def replace_zip_contents(
    base_zip: pathlib.Path,
    source_dir: pathlib.Path,
    output_path: pathlib.Path,
    root_dir_name: str | None = None,
) -> pathlib.Path:
    detected_root = detect_root_dir_name(base_zip)
    if root_dir_name is None and detected_root is None:
        raise ValueError("Could not detect a single project root directory in base zip. Pass --root-dir-name explicitly.")
    chosen_root = root_dir_name or detected_root

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = pathlib.Path(temp_dir_str)
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(base_zip) as archive:
            _extract_archive_safely(archive, extract_dir)

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

        return _write_zip_from_directory(extract_dir, output_path)


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
