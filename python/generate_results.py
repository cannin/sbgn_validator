"""Generate Python results for every case in the shared manifest."""

import argparse
import json
from pathlib import Path

from sbgn_validator import SchematronValidator, validate_sbgn


def main() -> None:
    """Validate the shared manifest with cached per-schema validators."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(".."))
    parser.add_argument("--benchmark-root", type=Path, default=Path(".."))
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    benchmark_root = args.benchmark_root.resolve()
    manifest = json.loads((benchmark_root / "conformance/manifest.json").read_text())
    validators: dict[tuple[str, str], SchematronValidator] = {}
    for case in manifest["cases"]:
        if case.get("namespace_policy") == "allow-sbgnml-0.2":
            report = validate_sbgn(
                repo_root / case["input"],
                repo_root / case["schema"],
                case["phase"],
                allow_sbgnml_0_2=True,
            )
        else:
            key = (case["schema"], case["phase"])
            validator = validators.setdefault(
                key, SchematronValidator(repo_root / case["schema"], case["phase"])
            )
            report = validator.validate(repo_root / case["input"])
        relative = Path(case["oracle"]).relative_to("conformance/oracle/java")
        output = benchmark_root / "build/results/python" / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
