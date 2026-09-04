"""Verify Java oracle results against upstream rule-fixture naming intent."""

import argparse
import json
import re
from pathlib import Path

EXPECTED_RULE = re.compile(r"^((?:af|er|pd)\d+)-(pass|fail)", re.IGNORECASE)


def is_normalized_test(value: object) -> bool:
    """Return whether a finding test uses single-space whitespace.

    Args:
        value: Report field value.

    Returns:
        True for null or a normalized test expression.
    """
    return value is None or (isinstance(value, str) and value == " ".join(value.split()))


def main() -> None:
    """Verify every manifest case and its expected focal rule behavior."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("conformance/manifest.json"))
    parser.add_argument("--oracle-root", type=Path, default=Path("."))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    errors: list[str] = []
    checked = 0
    for case in manifest["cases"]:
        if case.get("profile_feature"):
            path = args.oracle_root / case["oracle"]
            if not path.exists():
                errors.append(f"RULE_MISSING oracle={path}")
            else:
                report = json.loads(path.read_text())
                for finding in report["findings"]:
                    if not is_normalized_test(finding.get("test")):
                        errors.append(
                            f"TEST_WHITESPACE_NOT_NORMALIZED fixture={case['id']} "
                            f"rule={finding.get('id')}"
                        )
                feature = case["profile_feature"]
                if feature == "current-time" and "<CURRENT_TIME>" not in json.dumps(report):
                    errors.append(f"XPATH_RESULT_MISMATCH fixture={case['id']}")
                if feature == "namespace-mismatch" and {
                    finding["id"] for finding in report["findings"]
                } != {"sbgn-namespace-0.3"}:
                    errors.append(f"RULE_MISSING fixture={case['id']} rule=sbgn-namespace-0.3")
                if feature in {"sbgnml-0.2-valid", "sbgnml-0.3-compatible"} and not report[
                    "valid"
                ]:
                    errors.append(f"VALIDITY_MISMATCH fixture={case['id']}")
                if feature == "sbgnml-0.2-semantic":
                    required = {"pd10102", "pd10132", "pd10141"}
                    found = {finding["id"] for finding in report["findings"]}
                    for rule_id in sorted(required - found):
                        errors.append(f"RULE_MISSING fixture={case['id']} rule={rule_id}")
                checked += 1
            continue
        match = EXPECTED_RULE.match(case["id"])
        if not match:
            errors.append(f"UNCLASSIFIED_FIXTURE {case['id']}")
            continue
        rule_id, expectation = match.group(1).lower(), match.group(2).lower()
        path = args.oracle_root / case["oracle"]
        if not path.exists():
            errors.append(f"RULE_MISSING oracle={path}")
            continue
        report = json.loads(path.read_text())
        for finding in report["findings"]:
            if not is_normalized_test(finding.get("test")):
                errors.append(
                    f"TEST_WHITESPACE_NOT_NORMALIZED fixture={case['id']} "
                    f"rule={finding.get('id')}"
                )
        found = {finding["id"].lower() for finding in report["findings"]}
        if expectation == "fail" and rule_id not in found:
            errors.append(f"RULE_MISSING fixture={case['id']} rule={rule_id}")
        if expectation == "pass" and rule_id in found:
            errors.append(f"RULE_EXTRA fixture={case['id']} rule={rule_id}")
        checked += 1
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"verified {checked} Java oracle fixtures")


if __name__ == "__main__":
    main()
