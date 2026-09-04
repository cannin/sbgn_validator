"""Access and verify the Schematron rules distributed with the Python package."""

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from importlib.resources import files
from pathlib import Path

from lxml import etree

LANGUAGE_SCHEMAS = {
    "activity flow": "sbgn_af.sch",
    "AF": "sbgn_af.sch",
    "entity relationship": "sbgn_er.sch",
    "ER": "sbgn_er.sch",
    "process description": "sbgn_pd.sch",
    "PD": "sbgn_pd.sch",
}
RESOURCE_DIRECTORY = files("sbgn_validator").joinpath("_resources", "schematron")
SBGN_ML_03 = "http://sbgn.org/libsbgn/0.3"
SBGN_ML_02 = "http://sbgn.org/libsbgn/0.2"


class NamespacePolicy(Enum):
    """Accepted SBGN-ML document namespace policy."""

    STRICT_03 = "strict-0.3"
    ALLOW_SBGNML_0_2 = "allow-sbgnml-0.2"

    def effective_namespace(self, document_namespace: str | None) -> str:
        """Return the namespace used to compile Schematron expressions.

        Args:
            document_namespace: Exact namespace URI on the document root.

        Returns:
            The accepted effective namespace.

        Raises:
            ValueError: If the document namespace is not accepted.
        """
        if document_namespace == SBGN_ML_03:
            return SBGN_ML_03
        if self is NamespacePolicy.ALLOW_SBGNML_0_2 and document_namespace == SBGN_ML_02:
            return SBGN_ML_02
        expected = SBGN_ML_03
        if self is NamespacePolicy.ALLOW_SBGNML_0_2:
            expected = f"{SBGN_ML_03} or {SBGN_ML_02}"
        found = document_namespace or "<missing>"
        raise ValueError(f"SBGN_NAMESPACE_ERROR: expected {expected}; found {found}")


@dataclass(frozen=True)
class DocumentInfo:
    """Namespace and map language read from an SBGN-ML document."""

    namespace: str | None
    language: str


def _manifest() -> dict[str, object]:
    return json.loads(RESOURCE_DIRECTORY.joinpath("manifest.json").read_text(encoding="utf-8"))


def rules_info() -> dict[str, object]:
    """Return provenance for the package's built-in rules.

    Returns:
        Ruleset identity, version, digest, and upstream revision.
    """
    manifest = _manifest()
    return {
        "source": "builtin",
        "ruleset": manifest["ruleset"],
        "ruleset_version": manifest["ruleset_version"],
        "ruleset_digest": manifest["ruleset_digest"],
        "source_revision": manifest["source_revision"],
    }


def load_builtin_rule(language: str) -> tuple[str, bytes]:
    """Load and integrity-check the built-in schema for an SBGN language.

    Args:
        language: Canonical SBGN map language or short code.

    Returns:
        Resource filename and its exact bytes.

    Raises:
        ValueError: If the language is unsupported or resources are corrupt.
    """
    name = LANGUAGE_SCHEMAS.get(language)
    if name is None:
        raise ValueError(f"SCHEMATRON_SCHEMA_ERROR: unsupported SBGN language {language!r}")
    data = RESOURCE_DIRECTORY.joinpath(name).read_bytes()
    expected = _manifest()["files"][name]["sha256"]
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"BUILTIN_RULES_CORRUPT: {name}")
    return name, data


def inspect_sbgn_document(document_path: Path) -> DocumentInfo:
    """Read the root namespace and map language from an SBGN-ML document.

    Args:
        document_path: SBGN-ML file to inspect.

    Returns:
        Parsed namespace and map language.
    """
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    document = etree.parse(str(document_path), parser)
    root = document.getroot()
    if etree.QName(root).localname != "sbgn":
        raise ValueError("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing")
    namespace = etree.QName(root).namespace
    maps = document.xpath(
        "/*[local-name()='sbgn']/*[local-name()='map' and namespace-uri()=$namespace]",
        namespace=namespace or "",
    )
    if not maps or not maps[0].get("language"):
        raise ValueError("SCHEMATRON_SCHEMA_ERROR: SBGN map language is missing")
    return DocumentInfo(namespace=namespace, language=maps[0].get("language"))


def detect_sbgn_language(document_path: Path) -> str:
    """Read the map language from an SBGN-ML document.

    Args:
        document_path: SBGN-ML file to inspect.

    Returns:
        The map's language attribute.
    """
    return inspect_sbgn_document(document_path).language
