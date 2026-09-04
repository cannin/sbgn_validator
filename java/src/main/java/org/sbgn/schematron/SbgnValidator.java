package org.sbgn.schematron;

import java.nio.file.Path;

/** User-facing validation API with packaged rules as the default. */
public final class SbgnValidator {
    private SbgnValidator() {
    }

    /** Validate with the built-in schema selected from the document language. */
    public static CanonicalReport validate(Path document) throws Exception {
        return validate(document, null, "basic", NamespacePolicy.STRICT_03);
    }

    /** Validate with built-in rules or an explicit Schematron override. */
    public static CanonicalReport validate(
            Path document, Path rulesPath, String phase, NamespacePolicy namespacePolicy)
            throws Exception {
        BuiltinRules.DocumentInfo documentInfo = BuiltinRules.inspectDocument(document);
        String effectiveNamespace = namespacePolicy.effectiveNamespace(documentInfo.namespace());
        ReferenceValidator validator = rulesPath == null
                ? ReferenceValidator.builtinForDocument(
                        documentInfo.language(), phase, namespacePolicy, effectiveNamespace)
                : ReferenceValidator.forDocument(
                        rulesPath, phase, namespacePolicy, effectiveNamespace);
        return validator.validate(document);
    }

    /** Return provenance for the built-in rules. */
    public static RulesInfo rulesInfo() throws Exception {
        return BuiltinRules.rulesInfo();
    }
}
