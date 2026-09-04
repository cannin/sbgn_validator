package org.sbgn.schematron;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/** Command-line entry point for validating one SBGN-ML document. */
public final class ValidatorCli {
    private ValidatorCli() {
    }

    /** Validate one document and write an SVRL-aligned JSON report to stdout.
     *
     * @param args --schema PATH --document PATH [--phase NAME] [--backend]
     *     [--allow-sbgnml-0.2]
     * @throws Exception when schema compilation, validation, or serialization fails
     */
    public static void main(String[] args) throws Exception {
        Map<String, String> options = parseArgs(args);
        if (options.containsKey("--rules-info")) {
            ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
            mapper.writeValue(System.out, BuiltinRules.rulesInfo());
            return;
        }
        Path document = Path.of(required(options, "--document"));
        String phase = options.getOrDefault("--phase", "basic");
        boolean includeBackend = options.containsKey("--backend");
        NamespacePolicy namespacePolicy = options.containsKey("--allow-sbgnml-0.2")
                ? NamespacePolicy.ALLOW_SBGNML_0_2 : NamespacePolicy.STRICT_03;
        Path customRules = options.containsKey("--schema")
                ? Path.of(options.get("--schema")) : null;
        CanonicalReport report = SbgnValidator.validate(
                document, customRules, phase, namespacePolicy);
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        ObjectNode output = mapper.valueToTree(report);
        if (!includeBackend) {
            output.remove("backend");
        }
        mapper.writeValue(System.out, output);
    }

    private static Map<String, String> parseArgs(String[] args) {
        Map<String, String> options = new HashMap<>();
        for (int index = 0; index < args.length;) {
            String name = args[index];
            if (name.equals("--backend") || name.equals("--allow-sbgnml-0.2")
                    || name.equals("--rules-info")) {
                options.put(name, "true");
                index++;
                continue;
            }
            if (!name.startsWith("--")) {
                if (options.containsKey("--document")) {
                    throw usage("multiple document paths");
                }
                options.put("--document", name);
                index++;
                continue;
            }
            if (!name.equals("--schema") && !name.equals("--document") && !name.equals("--phase")) {
                throw usage("unknown option: " + name);
            }
            if (index + 1 >= args.length) {
                throw usage("missing value for " + name);
            }
            options.put(name, args[index + 1]);
            index += 2;
        }
        return options;
    }

    private static String required(Map<String, String> options, String name) {
        String value = options.get(name);
        if (value == null || value.isBlank()) {
            throw usage("missing " + name);
        }
        return value;
    }

    private static IllegalArgumentException usage(String detail) {
        return new IllegalArgumentException(
                detail + System.lineSeparator()
                        + "usage: sbgn-validator DOCUMENT [--schema PATH] [--phase NAME] "
                        + "[--backend] [--allow-sbgnml-0.2]");
    }
}
