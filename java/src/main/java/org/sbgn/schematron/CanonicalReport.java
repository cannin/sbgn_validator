package org.sbgn.schematron;

import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import java.util.List;

/** Cross-runtime normalized validation report. */
@JsonPropertyOrder({"schema", "phase", "valid", "findings", "backend"})
public record CanonicalReport(
        String schema,
        String phase,
        boolean valid,
        List<CanonicalFinding> findings,
        BackendInfo backend) {
}
