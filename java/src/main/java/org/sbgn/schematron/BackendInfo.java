package org.sbgn.schematron;

import com.fasterxml.jackson.annotation.JsonPropertyOrder;

/** Reproducible metadata for the Java reference backend. */
@JsonPropertyOrder({"language", "implementation", "implementation_version", "schematron_engine",
        "xpath_engine", "xpath_version", "native_schematron", "profile_version"})
public record BackendInfo(
        String language,
        String implementation,
        String implementation_version,
        String schematron_engine,
        String xpath_engine,
        String xpath_version,
        boolean native_schematron,
        String profile_version) {

    /** Return pinned Java oracle metadata. */
    public static BackendInfo javaOracle() {
        return new BackendInfo(
                "java",
                "sbgn-validator-java",
                "0.1.0",
                "ph-schematron-schxslt2 10.0.1 / SchXslt2",
                "Saxon-HE",
                "12.10",
                true,
                "libSBGN-Schematron-Profile-1");
    }
}
