package org.sbgn.schematron;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;

/** Tests the resources that are packaged in the JAR rather than root rules. */
final class BuiltinRulesTest {
    @Test
    void detectsLanguageAndValidatesWithBuiltins() throws Exception {
        Path root = Path.of("..").toAbsolutePath().normalize();
        Path document = root.resolve("tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn");
        String language = BuiltinRules.detectLanguage(document);
        CanonicalReport report = ReferenceValidator.builtin(language, "basic").validate(document);
        CanonicalReport canonical = new ReferenceValidator(
                root.resolve("validation/rules/sbgn_pd.sch"), "basic").validate(document);
        assertEquals("sbgn_pd.sch", report.schema());
        assertFalse(report.valid());
        assertTrue(report.findings().stream().anyMatch(finding -> "pd10110".equals(finding.id())));
        assertEquals(canonical, report);
        assertTrue(BuiltinRules.rulesInfo().rulesetDigest().startsWith("sha256:"));
    }
}
