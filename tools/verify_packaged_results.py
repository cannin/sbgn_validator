#!/usr/bin/env python3
"""Verify that isolated packaged validators execute the expected semantic rule."""

import argparse
import json
from pathlib import Path


def verify_test_whitespace(report: dict[str, object], name: str) -> None:
    """Require normalized whitespace in every reported test expression.

    Args:
        report: One normalized validator report.
        name: Report name for error diagnostics.
    """
    for finding in report.get("findings", []):
        value = finding.get("test")
        if value is not None and (
            not isinstance(value, str) or value != " ".join(value.split())
        ):
            raise SystemExit(
                f"PACKAGED TEST WHITESPACE NOT NORMALIZED: {name} rule={finding.get('id')}"
            )


def semantic_projection(
    report: dict[str, object],
) -> tuple[object, object, list[tuple[object, object]]]:
    """Project a report onto processor-independent validation identity.

    Args:
        report: One normalized validator report.

    Returns:
        Schema, validity, and sorted rule/element identities.
    """
    findings = report.get("findings", [])
    identities = sorted(
        (finding.get("id"), finding.get("derived", {}).get("element_id")) for finding in findings
    )
    return report.get("schema"), report.get("valid"), identities


def main() -> None:
    """Require package-isolation reports to match one expected outcome."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid", action="store_true")
    parser.add_argument("--expected-rule", default="pd10110")
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    reports = {
        report.name: json.loads(report.read_text(encoding="utf-8")) for report in args.reports
    }
    for name, report in reports.items():
        verify_test_whitespace(report, name)
    projections = {name: semantic_projection(report) for name, report in reports.items()}
    first = next(iter(projections.values()))
    mismatches = {name: value for name, value in projections.items() if value != first}
    expected_valid = args.valid
    if mismatches or first[0] != "sbgn_pd.sch" or first[1] is not expected_valid:
        raise SystemExit(f"PACKAGED VALIDATION MISMATCH: {projections!r}")
    if expected_valid and first[2]:
        raise SystemExit(f"PACKAGED VALIDATION EXPECTED NO FINDINGS: {projections!r}")
    if (
        not expected_valid
        and args.expected_rule
        and not any(rule_id == args.expected_rule for rule_id, _ in first[2])
    ):
        raise SystemExit(f"PACKAGED VALIDATION MISSING {args.expected_rule}: {projections!r}")
    outcome = "valid" if expected_valid else f"invalid ({args.expected_rule or 'expected'})"
    print(f"All {len(projections)} packaged validators reported {outcome} equivalently.")


if __name__ == "__main__":
    main()
