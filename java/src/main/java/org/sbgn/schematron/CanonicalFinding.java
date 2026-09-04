package org.sbgn.schematron;

import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import java.util.List;

/** SVRL-aligned representation of one failed assertion or successful report. */
@JsonPropertyOrder({"id", "type", "role", "flag", "location", "test", "text",
        "diagnostic_references", "derived"})
public record CanonicalFinding(
        String id,
        String type,
        String role,
        String flag,
        String location,
        String test,
        String text,
        List<DiagnosticReference> diagnostic_references,
        DerivedIdentity derived) {
}
