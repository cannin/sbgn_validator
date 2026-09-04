"""Build the shared manifest from upstream semantic fixtures."""

import argparse
import json
import re
from pathlib import Path

LANGUAGE_SCHEMA = {"af": "validation/rules/sbgn_af.sch", "er": "validation/rules/sbgn_er.sch", "pd": "validation/rules/sbgn_pd.sch"}
RULE_PREFIX = re.compile(r"^(af|er|pd)\d+", re.IGNORECASE)


def fixture_language(path: Path) -> str:
    """Infer fixture language from its rule prefix or SBGN map.

    Args:
        path: Fixture path.

    Returns:
        Lowercase SBGN language abbreviation.
    """
    match = RULE_PREFIX.match(path.name)
    if match:
        return match.group(1).lower()
    text = path.read_text(errors="ignore")
    match = re.search(r'<map[^>]+language="([^"]+)"', text)
    aliases = {"activity flow": "af", "entity relationship": "er", "process description": "pd"}
    if match and match.group(1).lower() in aliases:
        return aliases[match.group(1).lower()]
    raise ValueError(f"cannot determine SBGN language for {path}")


def main() -> None:
    """Write a deterministic single-source conformance manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path("tests/fixtures/error-test-files"))
    parser.add_argument("--output", type=Path, default=Path("conformance/manifest.json"))
    args = parser.parse_args()
    fixture_root = args.fixtures.resolve()
    cases = []
    for path in sorted(fixture_root.rglob("*.sbgn")):
        language = fixture_language(path)
        relative = path.relative_to(fixture_root).as_posix()
        cases.append({
            "id": path.stem,
            "language": language.upper(),
            "schema": LANGUAGE_SCHEMA[language],
            "phase": "basic",
            "input": f"tests/fixtures/error-test-files/{relative}",
            "oracle": f"conformance/oracle/java/{language}/{path.stem}.json",
        })
    cases.append({
        "id": "profile-namespace-mismatch",
        "language": "PD",
        "schema": LANGUAGE_SCHEMA["pd"],
        "phase": "basic",
        "input": "tests/examples/go_mf_conflicts.sbgn",
        "oracle": "conformance/oracle/java/profile/namespace-mismatch.json",
        "profile_feature": "namespace-mismatch",
    })
    cases.append({
        "id": "profile-current-time",
        "language": "PD",
        "schema": LANGUAGE_SCHEMA["pd"],
        "phase": "sanity",
        "input": "tests/fixtures/error-test-files/PD/pd10101-pass.sbgn",
        "oracle": "conformance/oracle/java/profile/current-time.json",
        "profile_feature": "current-time",
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"version": 1, "fixture_count": len(cases), "cases": cases}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
