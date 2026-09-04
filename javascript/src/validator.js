import fs from "node:fs";
import fontoxpath from "fontoxpath";
import { Schema } from "node-schematron";
import { parseXmlDocument, serializeToWellFormedString } from "slimdom";

import {
    NamespacePolicy,
    SBGN_ML_02,
    SBGN_ML_03,
    effectiveNamespace,
    inspectSbgnDocument,
} from "./namespace.js";
import { loadBuiltinRule } from "./rules.js";

export { rulesInfo } from "./rules.js";
export { NamespacePolicy } from "./namespace.js";

const FN_NAMESPACE = "http://www.w3.org/2005/xpath-functions";
const ISO_NAMESPACE = "http://purl.oclc.org/dsdl/schematron";
const COMPATIBILITY_PHASE = "basic-allow-sbgnml-0.2";
let schematronCurrent = null;
let currentRegistered = false;
const { evaluateXPath, registerCustomXPathFunction } = fontoxpath;

function registerCurrent() {
    if (currentRegistered) return;
    registerCustomXPathFunction(
        { localName: "current", namespaceURI: FN_NAMESPACE },
        [],
        "node()",
        () => {
            if (!schematronCurrent) {
                throw new Error("XPATH_DYNAMIC_ERROR: current() has no rule context");
            }
            return schematronCurrent;
        },
    );
    currentRegistered = true;
}

function elements(node) {
    return Array.from(node.childNodes ?? []).filter((child) => child.nodeType === 1);
}

function walk(node, output = []) {
    for (const child of elements(node)) {
        output.push(child);
        walk(child, output);
    }
    return output;
}

function parts(node) {
    return Array.from(node.childNodes ?? []).map((child) => {
        if (child.nodeType === 3) return { type: "text", value: child.nodeValue ?? "" };
        if (child.namespaceURI === ISO_NAMESPACE && child.localName === "value-of") {
            return { type: "value-of", value: child.getAttribute("select") };
        }
        if (child.namespaceURI === ISO_NAMESPACE && child.localName === "name") {
            return { type: "name", value: child.getAttribute("path") ?? "." };
        }
        return { type: "text", value: child.textContent ?? "" };
    });
}

function metadata(schemaDocument) {
    const checks = new Map();
    const diagnostics = new Map();
    for (const node of walk(schemaDocument)) {
        if (node.namespaceURI !== ISO_NAMESPACE) continue;
        if ((node.localName === "assert" || node.localName === "report") && node.getAttribute("id")) {
            checks.set(node.getAttribute("id"), {
                role: node.getAttribute("role"),
                flag: node.getAttribute("flag"),
                test: node.getAttribute("test"),
                diagnostics: (node.getAttribute("diagnostics") ?? "").trim().split(/\s+/).filter(Boolean),
            });
        }
        if (node.localName === "diagnostic") diagnostics.set(node.getAttribute("id"), parts(node));
    }
    return { checks, diagnostics };
}

function xpathValue(value) {
    const values = Array.isArray(value) ? value : [value];
    return values.map((item) => {
        if (item == null) return "";
        if (item.nodeType === 2) return item.value ?? item.nodeValue ?? "";
        if (item.nodeType) return item.textContent ?? item.nodeValue ?? "";
        return String(item);
    }).join(" ");
}

function renderDiagnostic(content, context, variables, options) {
    return content.map((part) => {
        if (part.type === "text") return part.value;
        if (part.type === "name") return xpathValue(evaluateXPath(`name(${part.value})`, context, null, variables, undefined, options));
        return xpathValue(evaluateXPath(part.value, context, null, variables, undefined, options));
    }).join("").replace(/\s+/g, " ").trim();
}

function normalizeText(value) {
    return value.replace(/\s+/g, " ").trim().replace(
        /\b(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-][0-2]\d:[0-5]\d)?\b/g,
        "<CURRENT_TIME>",
    );
}

function normalizeWhitespace(value) {
    return value == null ? null : value.replace(/\s+/g, " ").trim();
}

function canonicalLocation(node) {
    const segments = [];
    for (let current = node; current && current.nodeType === 1; current = current.parentNode) {
        const siblings = elements(current.parentNode).filter(
            (sibling) => sibling.localName === current.localName && sibling.namespaceURI === current.namespaceURI,
        );
        const index = siblings.indexOf(current) + 1;
        segments.push(`Q{${current.namespaceURI ?? ""}}${current.localName}[${index}]`);
    }
    return `/${segments.reverse().join("/")}`;
}

export class SchematronValidator {
    constructor(
        schemaPath,
        phase = "basic",
        namespacePolicy = NamespacePolicy.STRICT_03,
        effectiveSbgnNamespace = SBGN_ML_03,
    ) {
        this._initialize(
            schemaPath.split(/[\\/]/).at(-1),
            fs.readFileSync(schemaPath, "utf8"),
            phase,
            namespacePolicy,
            effectiveSbgnNamespace,
        );
    }

    static fromBuiltin(
        language,
        phase = "basic",
        namespacePolicy = NamespacePolicy.STRICT_03,
        effectiveSbgnNamespace = SBGN_ML_03,
    ) {
        const rule = loadBuiltinRule(language);
        const validator = Object.create(SchematronValidator.prototype);
        validator._initialize(
            rule.name, rule.text, phase, namespacePolicy, effectiveSbgnNamespace,
        );
        return validator;
    }

    _initialize(schemaName, schemaText, phase, namespacePolicy, effectiveSbgnNamespace) {
        registerCurrent();
        this.schemaName = schemaName;
        this.schemaDocument = parseXmlDocument(schemaText);
        const compatibilityPhase = walk(this.schemaDocument).find(
            (node) => node.namespaceURI === ISO_NAMESPACE
                && node.localName === "phase"
                && node.getAttribute("id") === COMPATIBILITY_PHASE,
        );
        this.phase = namespacePolicy === NamespacePolicy.ALLOW_SBGNML_0_2
            && phase === "basic" && compatibilityPhase
            ? COMPATIBILITY_PHASE
            : phase;
        if (effectiveSbgnNamespace === SBGN_ML_02) {
            const bindings = walk(this.schemaDocument).filter(
                (node) => node.namespaceURI === ISO_NAMESPACE
                    && node.localName === "ns"
                    && node.getAttribute("prefix") === "sbgn",
            );
            if (bindings.length !== 1) {
                throw new Error(
                    "SCHEMATRON_NAMESPACE_ERROR: expected one sbgn namespace binding",
                );
            }
            const original = bindings[0].getAttribute("uri");
            if (original !== SBGN_ML_03 && original !== SBGN_ML_02) {
                throw new Error(`SCHEMATRON_NAMESPACE_ERROR: unsafe sbgn binding ${original}`);
            }
            bindings[0].setAttribute("uri", SBGN_ML_02);
        }
        this.schemaText = serializeToWellFormedString(this.schemaDocument);
        this.meta = metadata(this.schemaDocument);
        this.schema = Schema.fromString(this.schemaText);
        for (const pattern of this.schema.patterns) {
            for (const rule of pattern.rules) {
                const original = rule.validateNode.bind(rule);
                rule.validateNode = (context, parentVariables, options) => {
                    const previous = schematronCurrent;
                    schematronCurrent = context;
                    const variables = { ...(parentVariables ?? {}) };
                    for (const variable of rule.variables) {
                        variables[variable.name] = variable.value
                            ? evaluateXPath(variable.value, context, null, variables, undefined, options)
                            : context;
                    }
                    try {
                        const results = original(context, parentVariables, options);
                        for (const result of results) result.__variables = variables;
                        return results;
                    } finally {
                        schematronCurrent = previous;
                    }
                };
            }
        }
    }

    validate(documentPath) {
        const document = parseXmlDocument(fs.readFileSync(documentPath, "utf8"));
        const results = this.schema.validateDocument(document, { phaseId: this.phase });
        const findings = results.map((result) => {
            const check = this.meta.checks.get(result.assertId) ?? {};
            const diagnosticReferences = [];
            const selectedDiagnostics = new Set(check.diagnostics ?? []);
            for (const [id, content] of this.meta.diagnostics) {
                if (!selectedDiagnostics.has(id)) continue;
                const text = renderDiagnostic(
                    content, result.context, result.__variables ?? {},
                    { namespaceResolver: this.schema.getNamespaceUriForPrefix.bind(this.schema) },
                ).replace(new RegExp(`^${id}:\\s*`, "i"), "");
                diagnosticReferences.push({ diagnostic: id, text });
            }
            const diagnosticId = diagnosticReferences.find((item) => item.diagnostic === "id")?.text;
            return {
                id: result.assertId ?? "",
                type: result.isReport ? "successful-report" : "failed-assert",
                role: check.role ?? null,
                flag: check.flag ?? null,
                location: canonicalLocation(result.context),
                test: normalizeWhitespace(check.test),
                text: normalizeText(result.message ?? ""),
                diagnostic_references: diagnosticReferences,
                derived: {
                    element_id: diagnosticId || result.context.getAttribute?.("id") || null,
                    element_kind: result.context.localName ?? null,
                },
            };
        }).sort((left, right) => JSON.stringify([
            left.id, left.derived.element_id, left.location, left.text,
        ]).localeCompare(JSON.stringify([
            right.id, right.derived.element_id, right.location, right.text,
        ])));
        return {
            schema: this.schemaName,
            phase: this.phase,
            valid: findings.length === 0,
            findings,
            backend: {
                language: "javascript",
                implementation: "sbgn-validator-javascript",
                implementation_version: "0.1.1",
                schematron_engine: "node-schematron 2.1.0",
                xpath_engine: "FontoXPath",
                xpath_version: "3.34.0",
                native_schematron: true,
                profile_version: "libSBGN-Schematron-Profile-1",
            },
        };
    }
}

export function validateSbgn(documentPath, options = {}) {
    const requestedPhase = options.phase ?? "basic";
    const namespacePolicy = options.allowSbgnml02
        ? NamespacePolicy.ALLOW_SBGNML_0_2
        : NamespacePolicy.STRICT_03;
    const documentInfo = inspectSbgnDocument(documentPath);
    const effectiveSbgnNamespace = effectiveNamespace(namespacePolicy, documentInfo.namespace);
    const validator = options.schemaPath
        ? new SchematronValidator(
            options.schemaPath,
            requestedPhase,
            namespacePolicy,
            effectiveSbgnNamespace,
        )
        : SchematronValidator.fromBuiltin(
            documentInfo.language,
            requestedPhase,
            namespacePolicy,
            effectiveSbgnNamespace,
        );
    return validator.validate(documentPath);
}
