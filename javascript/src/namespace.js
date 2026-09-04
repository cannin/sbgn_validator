import fs from "node:fs";
import { parseXmlDocument } from "slimdom";

export const SBGN_ML_03 = "http://sbgn.org/libsbgn/0.3";
export const SBGN_ML_02 = "http://sbgn.org/libsbgn/0.2";

export const NamespacePolicy = Object.freeze({
    STRICT_03: "strict-0.3",
    ALLOW_SBGNML_0_2: "allow-sbgnml-0.2",
});

export function effectiveNamespace(policy, documentNamespace) {
    if (documentNamespace === SBGN_ML_03) return SBGN_ML_03;
    if (policy === NamespacePolicy.ALLOW_SBGNML_0_2 && documentNamespace === SBGN_ML_02) {
        return SBGN_ML_02;
    }
    const expected = policy === NamespacePolicy.ALLOW_SBGNML_0_2
        ? `${SBGN_ML_03} or ${SBGN_ML_02}`
        : SBGN_ML_03;
    throw new Error(
        `SBGN_NAMESPACE_ERROR: expected ${expected}; found ${documentNamespace || "<missing>"}`,
    );
}

export function inspectSbgnDocument(documentPath) {
    const document = parseXmlDocument(fs.readFileSync(documentPath, "utf8"));
    const root = document.documentElement;
    if (!root || root.localName !== "sbgn") {
        throw new Error("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing");
    }
    const map = Array.from(root.childNodes).find(
        (node) => node.nodeType === 1
            && node.localName === "map"
            && node.namespaceURI === root.namespaceURI,
    );
    const language = map?.getAttribute("language");
    if (!language) throw new Error("SCHEMATRON_SCHEMA_ERROR: SBGN map language is missing");
    return { namespace: root.namespaceURI, language };
}
