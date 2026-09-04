#!/usr/bin/env python3
"""Verify canonical and generated Schematron resources without changing files."""

import argparse
import hashlib
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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(repository_root: Path) -> list[str]:
    """Return all synchronization errors found in a repository tree.

    Args:
        repository_root: Monorepo root directory.

    Returns:
        Human-readable mismatch descriptions; empty means success.
    """
    canonical = repository_root / "validation" / "rules"
    errors: list[str] = []
    try:
        validate_canonical_directory(canonical)
    except ValueError as exception:
        return [str(exception)]
    expected_manifest = manifest_bytes(canonical)
    canonical_manifest = canonical / MANIFEST_NAME
    if not canonical_manifest.exists() or canonical_manifest.read_bytes() != expected_manifest:
        errors.append(f"stale canonical manifest: {canonical_manifest}")
    expected_names = {*RULE_FILES, MANIFEST_NAME, GENERATED_README_NAME}
    for relative_directory in SNAPSHOT_DIRECTORIES:
        snapshot = repository_root / relative_directory
        actual_names = {path.name for path in snapshot.iterdir()} if snapshot.is_dir() else set()
        if actual_names != expected_names:
            errors.append(
                f"snapshot contents differ: {relative_directory}; "
                f"missing={sorted(expected_names - actual_names)}, "
                f"unexpected={sorted(actual_names - expected_names)}"
            )
        for name in (*RULE_FILES, MANIFEST_NAME, GENERATED_README_NAME):
            source = canonical / name
            target = snapshot / name
            if not target.exists():
                continue
            if name == MANIFEST_NAME:
                expected = expected_manifest
            elif name == GENERATED_README_NAME:
                expected = generated_readme_bytes()
            else:
                expected = source.read_bytes()
            actual = target.read_bytes()
            if actual != expected:
                errors.append(
                    f"{relative_directory / name}: canonical SHA256={_sha256(expected)}, "
                    f"snapshot SHA256={_sha256(actual)}"
                )
    return errors


def main() -> None:
    """Parse command-line arguments and fail on any stale snapshot."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    errors = verify(args.repository_root.resolve())
    if errors:
        details = "\n".join(f"  {error}" for error in errors)
        raise SystemExit(
            "RULE SNAPSHOT MISMATCH\n\n"
            f"{details}\n\n"
            "Run:\n  uv run --project tools python tools/sync_rules.py"
        )
    print("Schematron snapshots match canonical rules.")


if __name__ == "__main__":
    main()
