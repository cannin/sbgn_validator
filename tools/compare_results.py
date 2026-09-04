"""Compare normalized runtime output with the verified Java oracle."""

import argparse
import json
from pathlib import Path

SEMANTIC_FIELDS = (
    "id",
    "type",
    "role",
    "flag",
    "test",
    "text",
    "diagnostic_references",
    "derived",
)


def semantic_finding(finding: dict[str, object]) -> dict[str, object]:
    """Select stable cross-processor finding fields.

    Args:
        finding: Runtime finding object.

    Returns:
        Comparable semantic finding.
    """
    return {field: finding.get(field) for field in SEMANTIC_FIELDS}


def main() -> None:
    """Compare a runtime directory with Java and classify mismatches."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language")
    parser.add_argument("--benchmark-root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.benchmark_root.resolve()
    runtime_root = root / "build/results" / args.language
    oracle_root = root / "conformance/oracle/java"
    mismatches: list[str] = []
    checked = 0
    for oracle_path in sorted(oracle_root.rglob("*.json")):
        relative = oracle_path.relative_to(oracle_root)
        actual_path = runtime_root / relative
        if not actual_path.exists():
            mismatches.append(f"RULE_MISSING output={relative}")
            continue
        expected = json.loads(oracle_path.read_text())
        actual = json.loads(actual_path.read_text())
        if expected.get("schema") != actual.get("schema"):
            mismatches.append(f"SCHEMA_MISMATCH fixture={relative}")
        if expected.get("phase") != actual.get("phase"):
            mismatches.append(f"PHASE_SELECTION_DIFFERENCE fixture={relative}")
        if expected.get("valid") != actual.get("valid"):
            mismatches.append(f"VALIDITY_MISMATCH fixture={relative}")
        expected_findings = [semantic_finding(item) for item in expected["findings"]]
        actual_findings = [semantic_finding(item) for item in actual["findings"]]
        if expected_findings != actual_findings:
            mismatches.append(f"VALIDATION_RESULT_MISMATCH fixture={relative}")
        checked += 1
    if mismatches:
        raise SystemExit("\n".join(mismatches))
    print(f"{args.language}: {checked} reports match Java")


if __name__ == "__main__":
    main()
