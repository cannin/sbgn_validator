"""PySchematron adapter with correct XSLT current-node semantics."""

import re
from pathlib import Path
from typing import Any

from elementpath import XPath2Parser
from lxml import etree
from pyschematron import DirectModeSchematronValidatorFactory
from pyschematron.direct_mode.xml_validation import validators
from pyschematron.direct_mode.xml_validation.queries.factories import (
    ExtendableQueryProcessorFactory,
)
from pyschematron.direct_mode.xml_validation.queries.xpath import (
    CustomXPathFunction,
    ElementPathXPathQueryParser,
    XPathQueryProcessor,
)

from .rules import (
    SBGN_ML_02,
    SBGN_ML_03,
    NamespacePolicy,
    inspect_sbgn_document,
    load_builtin_rule,
)

ISO = "http://purl.oclc.org/dsdl/schematron"
SVRL = "http://purl.oclc.org/dsdl/svrl"
COMPATIBILITY_PHASE = "basic-allow-sbgnml-0.2"
CURRENT_VARIABLE = "__sbgn_validator_current"
CLOCK = re.compile(r"\b(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-][0-2]\d:[0-5]\d)?\b")


class _CurrentXPath2Parser(XPath2Parser):
    """XPath 2 parser extended with the XSLT current function."""


@_CurrentXPath2Parser.method(_CurrentXPath2Parser.function("current", nargs=0))
def evaluate_current_function(self: Any, context: Any = None) -> Any:
    del self
    if context is None or CURRENT_VARIABLE not in context.variables:
        raise ValueError("XPATH_DYNAMIC_ERROR: current() has no Schematron rule context")
    return context.variables[CURRENT_VARIABLE]


class _CurrentQueryParser(ElementPathXPathQueryParser):
    def __init__(self, namespaces: dict[str, str] | None = None) -> None:
        super().__init__(_CurrentXPath2Parser, namespaces=namespaces)

    def with_namespaces(self, namespaces: dict[str, str]) -> "_CurrentQueryParser":
        return type(self)(self._namespaces | namespaces)

    def with_custom_function(self, custom_function: CustomXPathFunction) -> "_CurrentQueryParser":
        raise ValueError(f"XPATH_UNSUPPORTED_FEATURE: {custom_function.name}")


class _Factory(DirectModeSchematronValidatorFactory):
    def _get_query_processor_factory(self) -> ExtendableQueryProcessorFactory:
        factory = ExtendableQueryProcessorFactory()
        factory.set_query_processor("xslt2", XPathQueryProcessor(_CurrentQueryParser()))
        return factory


def _install_rule_context_adapter() -> None:
    original = validators._RuleValidator._extend_context_with_context_variables
    if getattr(original, "_libsbgn_current", False):
        return

    def extend(self: Any, xml_node: Any, evaluation_context: Any) -> Any:
        context = evaluation_context.with_context_item(xml_node)
        context = context.with_variables({CURRENT_VARIABLE: xml_node}, overwrite=True)
        return validators._get_context_with_variables(self._variable_evaluators, context)

    extend._libsbgn_current = True
    validators._RuleValidator._extend_context_with_context_variables = extend

    match_original = validators._RuleValidator._node_matches_context
    if not getattr(match_original, "_libsbgn_ancestor_context", False):

        def matches_context(self: Any, xml_node: Any, evaluation_context: Any) -> bool:
            candidate = xml_node.parent
            while candidate is not None:
                matches = self._context_query.evaluate(
                    evaluation_context.with_context_item(candidate)
                )
                if xml_node in matches:
                    return True
                candidate = getattr(candidate, "parent", None)
            return False

        matches_context._libsbgn_ancestor_context = True
        validators._RuleValidator._node_matches_context = matches_context

    rich_original = validators._RichTextContentEvaluator.evaluate
    if getattr(rich_original, "_libsbgn_xpath2_value_of", False):
        return

    def evaluate_rich(self: Any, context: Any) -> str:
        rendered: list[str] = []
        for content in self._content_elements:
            if isinstance(content, str):
                rendered.append(content)
                continue
            result = content.evaluate(context)
            if isinstance(result, list):
                values = []
                for item in result:
                    if isinstance(item, validators.XPathNode):
                        if isinstance(item.value, validators._Element):
                            values.append(validators.tostring(item.value).decode())
                        else:
                            values.append(str(item.value))
                    else:
                        values.append(str(item))
                rendered.append(" ".join(values))
            else:
                rendered.append(str(result))
        return "".join(rendered).strip()

    evaluate_rich._libsbgn_xpath2_value_of = True
    validators._RichTextContentEvaluator.evaluate = evaluate_rich


class SchematronValidator:
    """Compile once and validate many documents with PySchematron."""

    def __init__(
        self,
        schema_path: Path,
        phase: str = "basic",
        namespace_policy: NamespacePolicy = NamespacePolicy.STRICT_03,
        effective_sbgn_namespace: str = SBGN_ML_03,
    ) -> None:
        schema_path = Path(schema_path)
        self._compile(
            schema_path.name,
            schema_path.read_bytes(),
            phase,
            namespace_policy,
            effective_sbgn_namespace,
        )

    @classmethod
    def from_builtin(
        cls,
        language: str,
        phase: str = "basic",
        namespace_policy: NamespacePolicy = NamespacePolicy.STRICT_03,
        effective_sbgn_namespace: str = SBGN_ML_03,
    ) -> "SchematronValidator":
        """Compile the packaged schema for an SBGN language.

        Args:
            language: SBGN map language or short code.
            phase: Schematron phase.

        Returns:
            A reusable validator using package resources.
        """
        name, data = load_builtin_rule(language)
        instance = cls.__new__(cls)
        instance._compile(
            name, data, phase, namespace_policy, effective_sbgn_namespace
        )
        return instance

    def _compile(
        self,
        schema_name: str,
        schema_data: bytes,
        phase: str,
        namespace_policy: NamespacePolicy,
        effective_sbgn_namespace: str,
    ) -> None:
        parser = etree.XMLParser(
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
            ns_clean=True,
            remove_comments=True,
        )
        schema_tree = etree.ElementTree(etree.fromstring(schema_data, parser))
        schema_tree.getroot().set("queryBinding", "xslt2")
        compatibility_phases = schema_tree.xpath(
            "//iso:phase[@id=$phase]",
            namespaces={"iso": ISO},
            phase=COMPATIBILITY_PHASE,
        )
        if (
            namespace_policy is NamespacePolicy.ALLOW_SBGNML_0_2
            and phase == "basic"
            and compatibility_phases
        ):
            phase = COMPATIBILITY_PHASE
        if effective_sbgn_namespace == SBGN_ML_02:
            bindings = schema_tree.xpath(
                "//iso:ns[@prefix='sbgn']", namespaces={"iso": ISO}
            )
            if len(bindings) != 1:
                raise ValueError(
                    "SCHEMATRON_NAMESPACE_ERROR: expected one sbgn namespace binding"
                )
            original = bindings[0].get("uri")
            if original not in {SBGN_ML_03, SBGN_ML_02}:
                raise ValueError(
                    f"SCHEMATRON_NAMESPACE_ERROR: unsafe sbgn binding {original}"
                )
            bindings[0].set("uri", SBGN_ML_02)
        self._metadata = {
            node.get("id"): {"role": node.get("role"), "flag": node.get("flag")}
            for node in schema_tree.xpath("//iso:assert | //iso:report", namespaces={"iso": ISO})
            if node.get("id")
        }
        self._diagnostic_order = [
            node.get("id")
            for node in schema_tree.xpath("//iso:diagnostic", namespaces={"iso": ISO})
            if node.get("id")
        ]
        _install_rule_context_adapter()
        self.schema_name = schema_name
        self.phase = phase
        self._validator = _Factory(schema_tree, phase=phase).build()

    def validate(self, document_path: Path) -> dict[str, object]:
        """Validate and normalize one SBGN document.

        Args:
            document_path: XML document path.

        Returns:
            Canonical report dictionary.
        """
        parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
        document = etree.parse(str(document_path), parser)
        result = self._validator.validate(document)
        findings = _normalize_svrl(result.get_svrl(), self._metadata, self._diagnostic_order)
        return {
            "schema": self.schema_name,
            "phase": self.phase,
            "valid": not findings,
            "findings": findings,
            "backend": {
                "language": "python",
                "implementation": "sbgn-validator-python",
                "implementation_version": "0.1.0",
                "schematron_engine": "pyschematron 1.2.1",
                "xpath_engine": "elementpath",
                "xpath_version": "5.0.4",
                "native_schematron": True,
                "profile_version": "libSBGN-Schematron-Profile-1",
            },
        }


def validate_sbgn(
    document_path: Path,
    rules_path: Path | None = None,
    phase: str = "basic",
    allow_sbgnml_0_2: bool = False,
) -> dict[str, object]:
    """Validate an SBGN document with built-in or explicit custom rules.

    Args:
        document_path: SBGN-ML document path.
        rules_path: Optional explicit Schematron override.
        phase: Schematron phase name.
        allow_sbgnml_0_2: Allow legacy SBGN-ML 0.2 semantic validation.

    Returns:
        Canonical validation report.
    """
    document_path = Path(document_path)
    namespace_policy = (
        NamespacePolicy.ALLOW_SBGNML_0_2
        if allow_sbgnml_0_2
        else NamespacePolicy.STRICT_03
    )
    document_info = inspect_sbgn_document(document_path)
    effective_namespace = namespace_policy.effective_namespace(document_info.namespace)
    if rules_path is not None:
        validator = SchematronValidator(
            Path(rules_path), phase, namespace_policy, effective_namespace
        )
    else:
        validator = SchematronValidator.from_builtin(
            document_info.language, phase, namespace_policy, effective_namespace
        )
    return validator.validate(document_path)


def _normalize_svrl(
    tree: etree._ElementTree,
    metadata: dict[str, dict[str, str | None]],
    diagnostic_order: list[str],
) -> list[dict[str, object]]:
    diagnostic_positions = {
        diagnostic_id: position for position, diagnostic_id in enumerate(diagnostic_order)
    }
    findings = []
    for local in ("failed-assert", "successful-report"):
        for finding in tree.xpath(f"//svrl:{local}", namespaces={"svrl": SVRL}):
            diagnostic_references = []
            for node in finding.xpath("./svrl:diagnostic-reference", namespaces={"svrl": SVRL}):
                key = node.get("diagnostic")
                value = " ".join("".join(node.itertext()).split())
                prefix = f"{key}:"
                text = (
                    value[len(prefix) :].strip()
                    if value.lower().startswith(prefix.lower())
                    else value
                )
                diagnostic_references.append({"diagnostic": key, "text": text})
            diagnostic_references.sort(
                key=lambda reference: diagnostic_positions.get(
                    reference["diagnostic"], len(diagnostic_positions)
                )
            )
            text_nodes = finding.xpath("./svrl:text", namespaces={"svrl": SVRL})
            text = " ".join("".join(text_nodes[0].itertext()).split()) if text_nodes else ""
            text = CLOCK.sub("<CURRENT_TIME>", text)
            location = finding.get("location")
            element_kind = None
            if location:
                final = location.rsplit("/", 1)[-1].split("[", 1)[0]
                element_kind = final.split("}", 1)[-1].rsplit(":", 1)[-1]
            finding_id = finding.get("id") or ""
            rule_metadata = metadata.get(finding_id, {})
            element_id = next(
                (
                    reference["text"]
                    for reference in diagnostic_references
                    if reference["diagnostic"] == "id" and reference["text"]
                ),
                None,
            )
            findings.append(
                {
                    "id": finding_id,
                    "type": local,
                    "role": finding.get("role") or rule_metadata.get("role"),
                    "flag": finding.get("flag") or rule_metadata.get("flag"),
                    "location": location,
                    "test": finding.get("test"),
                    "text": text,
                    "diagnostic_references": diagnostic_references,
                    "derived": {
                        "element_id": element_id,
                        "element_kind": element_kind,
                    },
                }
            )
    return sorted(
        findings,
        key=lambda item: (
            item["id"],
            item["derived"]["element_id"] or "",
            item["location"] or "",
            item["text"],
        ),
    )
