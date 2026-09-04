#!/usr/bin/env python3
"""Compare built-in rules provenance reports emitted by language artifacts."""

import argparse
import json
from pathlib import Path


def main() -> None:
    """Require every named JSON report to equal the canonical manifest identity."""
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected = {
        "source": "builtin",
        "ruleset": manifest["ruleset"],
        "ruleset_version": manifest["ruleset_version"],
        "ruleset_digest": manifest["ruleset_digest"],
        "source_revision": manifest["source_revision"],
    }
    failures = []
    for report_path in args.reports:
        actual = json.loads(report_path.read_text(encoding="utf-8"))
        if actual != expected:
            failures.append(f"{report_path}: expected {expected!r}, got {actual!r}")
    if failures:
        raise SystemExit("RULE DIGEST MISMATCH\n" + "\n".join(failures))
    print(f"All {len(args.reports)} artifacts report {expected['ruleset_digest']}.")


if __name__ == "__main__":
    main()
