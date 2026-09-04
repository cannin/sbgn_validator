package org.sbgn.schematron;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

final class NamespacePolicyTest {
    private static Path repositoryRoot() {
        Path current = Path.of("").toAbsolutePath();
        return current.getFileName().toString().equals("java") ? current.getParent() : current;
    }

    @Test
    void legacyPolicyRunsSemanticRulesAgainstZeroTwo() throws Exception {
        Path root = repositoryRoot();
        Path schema = root.resolve("validation/rules/sbgn_pd.sch");
        Path document = root.resolve("tests/examples/go_mf_conflicts.sbgn");
        CanonicalReport report = new ReferenceValidator(schema, "basic").validate(document);
        assertEquals(false, report.valid());
        assertEquals("sbgn-namespace-0.3", report.findings().get(0).id());
        CanonicalReport compatible = SbgnValidator.validate(
                document, schema, "basic", NamespacePolicy.ALLOW_SBGNML_0_2);
        assertEquals(false, compatible.valid());
        assertEquals("basic-allow-sbgnml-0.2", compatible.phase());
        var ids = compatible.findings().stream().map(CanonicalFinding::id).toList();
        org.junit.jupiter.api.Assertions.assertTrue(ids.contains("pd10102"));
        org.junit.jupiter.api.Assertions.assertTrue(ids.contains("pd10132"));
        org.junit.jupiter.api.Assertions.assertTrue(ids.contains("pd10141"));
        String expectedTest = "$port-class='process' or $port-class='omitted process' or "
                + "$port-class='uncertain process' or $port-class='association' or "
                + "$port-class='dissociation' or $port-class='phenotype'";
        compatible.findings().stream()
                .filter(finding -> "pd10102".equals(finding.id()))
                .forEach(finding -> assertEquals(expectedTest, finding.test()));
    }

    @Test
    void strictPolicyRejectsLegacyNamespaceBeforeValidation() {
        Path document = repositoryRoot().resolve("tests/examples/go_mf_conflicts.sbgn");
        var error = assertThrows(
                IllegalArgumentException.class,
                () -> SbgnValidator.validate(
                        document, null, "basic", NamespacePolicy.STRICT_03));
        org.junit.jupiter.api.Assertions.assertTrue(
                error.getMessage().startsWith("SBGN_NAMESPACE_ERROR:"));
    }

    @Test
    void compatibilityPolicyRejectsUnsupportedNamespaces() {
        Path root = repositoryRoot();
        for (String name : List.of(
                "missing-namespace.sbgn",
                "unrelated-namespace.sbgn",
                "future-namespace.sbgn")) {
            Path document = root.resolve("tests/fixtures/compatibility").resolve(name);
            var error = assertThrows(
                    IllegalArgumentException.class,
                    () -> SbgnValidator.validate(
                            document, null, "basic", NamespacePolicy.ALLOW_SBGNML_0_2));
            org.junit.jupiter.api.Assertions.assertTrue(
                    error.getMessage().startsWith("SBGN_NAMESPACE_ERROR:"));
        }
    }

    @Test
    void compatibilityPolicySupportsEveryLanguageAndCustomRules() throws Exception {
        Path root = repositoryRoot();
        for (String language : List.of("af", "er", "pd")) {
            Path document = root.resolve("tests/fixtures/compatibility")
                    .resolve("sbgnml-0.2-" + language + "-valid.sbgn");
            assertEquals(true, SbgnValidator.validate(
                    document, null, "basic", NamespacePolicy.ALLOW_SBGNML_0_2).valid());
            assertEquals(true, SbgnValidator.validate(
                    document,
                    root.resolve("validation/rules/sbgn_" + language + ".sch"),
                    "basic",
                    NamespacePolicy.ALLOW_SBGNML_0_2).valid());
        }
    }

    @Test
    void compatibilityPolicyDoesNotLeakAcrossConcurrentCompilations() {
        Path root = repositoryRoot();
        List<Path> documents = List.of(
                root.resolve("tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn"),
                root.resolve("tests/fixtures/error-test-files/PD/pd10110-pass.sbgn"),
                root.resolve("tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn"),
                root.resolve("tests/fixtures/error-test-files/PD/pd10110-pass.sbgn"));
        documents.parallelStream().forEach(document -> {
            try {
                assertEquals(true, SbgnValidator.validate(
                        document, null, "basic", NamespacePolicy.ALLOW_SBGNML_0_2).valid());
            } catch (Exception exception) {
                throw new AssertionError(exception);
            }
        });
    }

    @Test
    void customSchemaRebindsOnlyTheSbgnPrefix() throws Exception {
        Path root = repositoryRoot();
        Path document = root.resolve(
                "tests/fixtures/compatibility/custom-sbgnml-0.2.sbgn");
        CanonicalReport report = SbgnValidator.validate(
                document,
                root.resolve("tests/fixtures/compatibility/custom-sbgn.sch"),
                "basic",
                NamespacePolicy.ALLOW_SBGNML_0_2);
        assertEquals(true, report.valid());
        var error = assertThrows(
                IllegalArgumentException.class,
                () -> SbgnValidator.validate(
                        document,
                        root.resolve("tests/fixtures/compatibility/custom-unsafe-sbgn.sch"),
                        "basic",
                        NamespacePolicy.ALLOW_SBGNML_0_2));
        org.junit.jupiter.api.Assertions.assertTrue(
                error.getMessage().startsWith("SCHEMATRON_NAMESPACE_ERROR:"));
    }
}
