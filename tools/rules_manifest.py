"""Shared manifest and snapshot logic for packaged Schematron resources."""

import hashlib
import json
from pathlib import Path

RULE_FILES = ("sbgn_af.sch", "sbgn_er.sch", "sbgn_pd.sch")
RULESET = "libSBGN"
RULESET_VERSION = "0.0.1"
MANIFEST_NAME = "manifest.json"
CANONICAL_DOCUMENTATION = "README.md"
GENERATED_README_NAME = "README.generated.md"
SNAPSHOT_DIRECTORIES = (
    Path("python/sbgn_validator/_resources/schematron"),
    Path("r/inst/schematron"),
    Path("go/internal/rules/data"),
    Path("rust/src/rules/data"),
    Path("java/src/main/resources/schematron"),
    Path("javascript/resources/schematron"),
)


def ruleset_digest(rule_directory: Path) -> str:
    """Calculate the canonical digest over sorted names, NUL, and file bytes.

    Args:
        rule_directory: Directory containing the three canonical rule files.

    Returns:
        A SHA-256 digest prefixed with ``sha256:``.
    """
    digest = hashlib.sha256()
    for name in sorted(RULE_FILES):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update((rule_directory / name).read_bytes())
    return f"sha256:{digest.hexdigest()}"


def build_manifest(rule_directory: Path) -> dict[str, object]:
    """Build deterministic metadata for canonical rule bytes.

    Args:
        rule_directory: Directory containing canonical Schematron files.

    Returns:
        JSON-compatible manifest data.
    """
    files = {
        name: {"sha256": hashlib.sha256((rule_directory / name).read_bytes()).hexdigest()}
        for name in sorted(RULE_FILES)
    }
    return {
        "ruleset": RULESET,
        "ruleset_version": RULESET_VERSION,
        "source_revision": None,
        "ruleset_digest": ruleset_digest(rule_directory),
        "digest_algorithm": "SHA256(filename UTF-8 + NUL + file bytes), sorted by filename",
        "files": files,
    }


def manifest_bytes(rule_directory: Path) -> bytes:
    """Serialize canonical manifest metadata deterministically.

    Args:
        rule_directory: Directory containing canonical Schematron files.

    Returns:
        UTF-8 encoded, newline-terminated JSON.
    """
    return (json.dumps(build_manifest(rule_directory), indent=2, sort_keys=True) + "\n").encode()


def generated_readme_bytes() -> bytes:
    """Return deterministic generated-directory documentation.

    Returns:
        UTF-8 encoded, newline-terminated Markdown.
    """
    return (
        "# Generated Schematron resources\n\n"
        "Do not edit these files directly. Run `uv run --project tools python "
        "tools/sync_rules.py` from the repository root.\n"
    ).encode("utf-8")


def validate_canonical_directory(rule_directory: Path) -> None:
    """Reject missing or unexpected canonical Schematron files.

    Args:
        rule_directory: Canonical rules directory.

    Raises:
        ValueError: If the supported Schematron file set is not exact.
    """
    actual = {path.name for path in rule_directory.iterdir()}
    required = set(RULE_FILES)
    allowed = required | {MANIFEST_NAME, CANONICAL_DOCUMENTATION}
    missing = sorted(required - actual)
    unexpected = sorted(actual - allowed)
    if missing or unexpected:
        raise ValueError(f"canonical rule set mismatch: missing={missing}, unexpected={unexpected}")
