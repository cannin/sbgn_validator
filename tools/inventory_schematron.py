"""Inventory executable features in the libSBGN Schematron corpus."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

EXPRESSION_ATTRIBUTES = {"context", "test", "value", "select"}
FUNCTION_PATTERN = re.compile(r"(?<![\w:-])([A-Za-z_][\w.-]*)\s*\(")
VARIABLE_PATTERN = re.compile(r"\$([A-Za-z_][\w.-]*)")
AXIS_PATTERN = re.compile(r"\b([A-Za-z-]+)::")
XPATH_KEYWORDS = {"and", "div", "mod", "or"}
OPERATOR_PATTERNS = {
    "and": re.compile(r"\band\b"),
    "or": re.compile(r"\bor\b"),
    "equals": re.compile(r"(?<![!<>])=(?!=)"),
    "not_equals": re.compile(r"!="),
    "less_than": re.compile(r"(?<!<)<(?!=)"),
    "less_than_or_equal": re.compile(r"<="),
    "greater_than": re.compile(r"(?<!>)>(?!=)"),
    "greater_than_or_equal": re.compile(r">="),
}


def local_name(tag: str) -> str:
    """Return an XML expanded name's local part.

    Args:
        tag: Expanded or plain XML name.

    Returns:
        Local XML name.
    """
    return tag.rsplit("}", 1)[-1]


def inventory_schema(path: Path) -> dict[str, object]:
    """Inventory one schema without executing it.

    Args:
        path: Schematron path.

    Returns:
        JSON-compatible feature inventory.
    """
    root = ElementTree.parse(path).getroot()
    counted = {name: Counter() for name in ("elements", "attributes", "functions", "variables", "axes", "operators")}
    expressions: list[dict[str, str]] = []
    for element in root.iter():
        element_name = local_name(element.tag)
        counted["elements"][element_name] += 1
        for raw_attribute, value in element.attrib.items():
            attribute = local_name(raw_attribute)
            counted["attributes"][attribute] += 1
            if attribute not in EXPRESSION_ATTRIBUTES:
                continue
            expression = " ".join(value.split())
            expressions.append({"element": element_name, "attribute": attribute, "expression": expression})
            counted["functions"].update(name for name in FUNCTION_PATTERN.findall(expression) if name not in XPATH_KEYWORDS)
            counted["variables"].update(VARIABLE_PATTERN.findall(expression))
            counted["axes"].update(AXIS_PATTERN.findall(expression))
            for token, marker in (("descendant-abbreviation", "//"), ("parent-abbreviation", "../"), ("attribute-abbreviation", "@")):
                if marker in expression:
                    counted["axes"][token] += 1
            for operator, pattern in OPERATOR_PATTERNS.items():
                if pattern.search(expression):
                    counted["operators"][operator] += 1
    return {
        "schema": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "query_binding": root.attrib.get("queryBinding"),
        "default_phase": root.attrib.get("defaultPhase"),
        "schema_version": root.attrib.get("schemaVersion"),
        **{name: dict(sorted(values.items())) for name, values in counted.items()},
        "expressions": expressions,
    }


def aggregate(inventories: list[dict[str, object]], field: str) -> dict[str, int]:
    """Combine a counted field from each schema.

    Args:
        inventories: Per-schema inventories.
        field: Field to aggregate.

    Returns:
        Sorted counts.
    """
    counts: Counter[str] = Counter()
    for inventory in inventories:
        counts.update(inventory[field])
    return dict(sorted(counts.items()))


def main() -> None:
    """Generate deterministic Schematron and XPath inventories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, default=Path("validation/rules"))
    parser.add_argument("--output", type=Path, default=Path("conformance/profile"))
    args = parser.parse_args()
    inventories = [inventory_schema(path) for path in sorted(args.rules.resolve().glob("*.sch"))]
    if not inventories:
        raise SystemExit(f"no Schematron files found in {args.rules.resolve()}")
    args.output.mkdir(parents=True, exist_ok=True)
    schematron = {
        "profile": "libSBGN-Schematron-Profile-1",
        "source": "validation/rules/*.sch",
        "schemas": inventories,
        "constructs": aggregate(inventories, "elements"),
        "attributes": aggregate(inventories, "attributes"),
    }
    xpath = {
        "profile": "libSBGN-Schematron-Profile-1",
        "effective_semantics": "XPath 2 compatible plus XSLT current()",
        "xquery_required": False,
        "functions": aggregate(inventories, "functions"),
        "variables": aggregate(inventories, "variables"),
        "axes": aggregate(inventories, "axes"),
        "operators": aggregate(inventories, "operators"),
        "expressions": [{"schema": item["schema"], **expression} for item in inventories for expression in item["expressions"]],
    }
    for filename, content in (("schematron-features.json", schematron), ("xpath-features.json", xpath)):
        (args.output / filename).write_text(json.dumps(content, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
