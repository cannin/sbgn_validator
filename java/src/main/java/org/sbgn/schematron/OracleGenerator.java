package org.sbgn.schematron;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/** Explicit command for generating Java reference results from the shared manifest. */
public final class OracleGenerator {
    private OracleGenerator() {
    }

    /** Generate every committed oracle report.
     *
     * @param args --repo-root and --benchmark-root paths
     * @throws Exception when an input cannot be compiled, validated, or serialized
     */
    public static void main(String[] args) throws Exception {
        Map<String, Path> options = parseArgs(args);
        Path repoRoot = required(options, "--repo-root").toAbsolutePath().normalize();
        Path benchmarkRoot = required(options, "--benchmark-root").toAbsolutePath().normalize();
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        JsonNode manifest = mapper.readTree(benchmarkRoot.resolve("conformance/manifest.json").toFile());
        Map<String, ReferenceValidator> validators = new HashMap<>();

        for (JsonNode testCase : manifest.path("cases")) {
            String schemaRelative = testCase.path("schema").asText();
            String phase = testCase.path("phase").asText();
            Path document = repoRoot.resolve(testCase.path("input").asText());
            CanonicalReport report;
            if ("allow-sbgnml-0.2".equals(testCase.path("namespace_policy").asText())) {
                report = SbgnValidator.validate(
                        document, repoRoot.resolve(schemaRelative), phase,
                        NamespacePolicy.ALLOW_SBGNML_0_2);
            } else {
                String key = schemaRelative + "#" + phase;
                ReferenceValidator validator = validators.computeIfAbsent(
                        key,
                        ignored -> new ReferenceValidator(repoRoot.resolve(schemaRelative), phase));
                report = validator.validate(document);
            }
            String oracle = testCase.path("oracle").asText();
            Path output = benchmarkRoot.resolve(oracle.replaceFirst("^conformance/", "conformance/"));
            Files.createDirectories(output.getParent());
            mapper.writeValue(output.toFile(), report);
        }
    }

    private static Map<String, Path> parseArgs(String[] args) {
        if (args.length % 2 != 0) {
            throw new IllegalArgumentException("arguments must be name/path pairs");
        }
        Map<String, Path> options = new HashMap<>();
        for (int index = 0; index < args.length; index += 2) {
            options.put(args[index], Path.of(args[index + 1]));
        }
        return options;
    }

    private static Path required(Map<String, Path> options, String name) {
        Path value = options.get(name);
        if (value == null) {
            throw new IllegalArgumentException("missing " + name);
        }
        return value;
    }
}
