"""Command-line entry point for the Python SBGN Validator."""

import argparse
import json
from pathlib import Path

from .rules import rules_info
from .validator import validate_sbgn


def main() -> None:
    """Validate one SBGN-ML document and print normalized JSON."""
    parser = argparse.ArgumentParser(prog="sbgn-validator")
    parser.add_argument("document", nargs="?", type=Path)
    parser.add_argument("-s", "--schema", type=Path, help="explicit Schematron override")
    parser.add_argument("-d", "--document", dest="document_option", type=Path)
    parser.add_argument("-p", "--phase", default="basic")
    parser.add_argument("--backend", action="store_true", help="include backend metadata")
    parser.add_argument("--rules-info", action="store_true", help="print built-in rule provenance")
    parser.add_argument(
        "--allow-sbgnml-0.2",
        dest="allow_sbgnml_0_2",
        action="store_true",
        help="allow legacy SBGN-ML 0.2 semantic validation",
    )
    args = parser.parse_args()
    if args.rules_info:
        print(json.dumps(rules_info(), indent=2, sort_keys=True))
        return
    document = args.document_option or args.document
    if document is None:
        parser.error("a document path is required")
    report = validate_sbgn(
        document,
        rules_path=args.schema,
        phase=args.phase,
        allow_sbgnml_0_2=args.allow_sbgnml_0_2,
    )
    if not args.backend:
        report.pop("backend", None)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
