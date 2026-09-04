package org.sbgn.schematron;

/** Controls which SBGN-ML document namespaces validation accepts. */
public enum NamespacePolicy {
    /** Accept only the current SBGN-ML 0.3 namespace. */
    STRICT_03,
    /** Accept SBGN-ML 0.3 and the legacy 0.2 namespace. */
    ALLOW_SBGNML_0_2;

    /** Current SBGN-ML namespace used by the canonical rules. */
    public static final String SBGN_ML_03 = "http://sbgn.org/libsbgn/0.3";
    /** Legacy SBGN-ML namespace supported by the compatibility policy. */
    public static final String SBGN_ML_02 = "http://sbgn.org/libsbgn/0.2";

    /** Return the namespace against which Schematron XPath expressions compile.
     *
     * @param documentNamespace exact namespace URI from the document root
     * @return effective namespace for the Schematron {@code sbgn} prefix
     */
    public String effectiveNamespace(String documentNamespace) {
        if (SBGN_ML_03.equals(documentNamespace)) {
            return SBGN_ML_03;
        }
        if (this == ALLOW_SBGNML_0_2 && SBGN_ML_02.equals(documentNamespace)) {
            return SBGN_ML_02;
        }
        String expected = this == ALLOW_SBGNML_0_2
                ? SBGN_ML_03 + " or " + SBGN_ML_02 : SBGN_ML_03;
        String found = documentNamespace == null || documentNamespace.isEmpty()
                ? "<missing>" : documentNamespace;
        throw new IllegalArgumentException(
                "SBGN_NAMESPACE_ERROR: expected " + expected + "; found " + found);
    }
}
