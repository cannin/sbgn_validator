#!/usr/bin/env python3
"""Verify exact canonical rule bytes inside a release archive."""

import argparse
import tarfile
import zipfile
from pathlib import Path

from rules_manifest import (
    GENERATED_README_NAME,
    MANIFEST_NAME,
    RULE_FILES,
    generated_readme_bytes,
)


def _archive_entries(archive: Path) -> dict[str, bytes]:
    """Read regular-file entries from a ZIP/JAR/wheel or tar archive.

    Args:
        archive: Release archive to inspect.

    Returns:
        Mapping from archive-relative path to exact file bytes.
    """
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as package:
            return {
                info.filename: package.read(info)
                for info in package.infolist()
                if not info.is_dir()
            }
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as package:
            entries = {}
            for member in package.getmembers():
                if not member.isfile():
                    continue
                extracted = package.extractfile(member)
                if extracted is not None:
                    entries[member.name] = extracted.read()
            return entries
    raise ValueError(f"unsupported archive format: {archive}")


def verify_archive(archive: Path, prefix: str, canonical: Path) -> list[str]:
    """Compare packaged resources with canonical files byte for byte.

    Args:
        archive: Release archive to inspect.
        prefix: Directory before resource filenames inside the archive.
        canonical: Canonical rules directory.

    Returns:
        Mismatch descriptions; empty means success.
    """
    entries = _archive_entries(archive)
    errors = []
    normalized_prefix = prefix.rstrip("/")
    expected_names = {*RULE_FILES, MANIFEST_NAME, GENERATED_README_NAME}
    resource_names = {
        path.removeprefix(f"{normalized_prefix}/")
        for path in entries
        if path.startswith(f"{normalized_prefix}/")
        and "/" not in path.removeprefix(f"{normalized_prefix}/")
    }
    if resource_names != expected_names:
        errors.append(
            "resource contents differ: "
            f"missing={sorted(expected_names - resource_names)}, "
            f"unexpected={sorted(resource_names - expected_names)}"
        )
    for name in (*RULE_FILES, MANIFEST_NAME, GENERATED_README_NAME):
        archive_name = f"{normalized_prefix}/{name}"
        actual = entries.get(archive_name)
        if actual is None:
            errors.append(f"missing {archive_name}")
        expected = (
            generated_readme_bytes()
            if name == GENERATED_README_NAME
            else (canonical / name).read_bytes()
        )
        if actual is not None and actual != expected:
            errors.append(f"changed bytes in {archive_name}")
    return errors


def main() -> None:
    """Parse command-line arguments and verify one release archive."""
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("prefix")
    parser.add_argument(
        "--canonical",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "validation/rules",
    )
    args = parser.parse_args()
    errors = verify_archive(args.archive, args.prefix, args.canonical)
    if errors:
        raise SystemExit("RULE ARCHIVE MISMATCH\n" + "\n".join(f"  {item}" for item in errors))
    print(f"Packaged rules match canonical bytes: {args.archive}")


if __name__ == "__main__":
    main()
