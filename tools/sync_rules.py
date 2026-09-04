#!/usr/bin/env python3
"""Synchronize exact canonical Schematron bytes into every package."""

import argparse
import shutil
from pathlib import Path

from rules_manifest import (
    GENERATED_README_NAME,
    MANIFEST_NAME,
    RULE_FILES,
    SNAPSHOT_DIRECTORIES,
    generated_readme_bytes,
    manifest_bytes,
    validate_canonical_directory,
)


def synchronize(repository_root: Path) -> None:
    """Regenerate the canonical manifest and package-local snapshots.

    Args:
        repository_root: Monorepo root directory.
    """
    canonical = repository_root / "validation" / "rules"
    validate_canonical_directory(canonical)
    manifest = manifest_bytes(canonical)
    (canonical / MANIFEST_NAME).write_bytes(manifest)
    expected = {*RULE_FILES, MANIFEST_NAME, GENERATED_README_NAME}
    for relative_directory in SNAPSHOT_DIRECTORIES:
        destination = repository_root / relative_directory
        destination.mkdir(parents=True, exist_ok=True)
        for existing in destination.iterdir():
            if existing.is_file() and existing.name not in expected:
                existing.unlink()
        for name in RULE_FILES:
            shutil.copyfile(canonical / name, destination / name)
        (destination / MANIFEST_NAME).write_bytes(manifest)
        (destination / GENERATED_README_NAME).write_bytes(generated_readme_bytes())


def main() -> None:
    """Parse command-line arguments and synchronize all snapshots."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    synchronize(args.repository_root.resolve())


if __name__ == "__main__":
    main()
