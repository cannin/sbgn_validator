package org.sbgn.schematron;

import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Provenance for the Schematron rules packaged in the JAR. */
@JsonPropertyOrder({"source", "ruleset", "ruleset_version", "ruleset_digest", "source_revision"})
public record RulesInfo(
        String source,
        String ruleset,
        @JsonProperty("ruleset_version") String rulesetVersion,
        @JsonProperty("ruleset_digest") String rulesetDigest,
        @JsonProperty("source_revision") String sourceRevision) {
}
