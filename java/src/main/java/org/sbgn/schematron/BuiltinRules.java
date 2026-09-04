package org.sbgn.schematron;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.helger.io.resource.ClassPathResource;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

/** Loads and verifies the generated Schematron resources in the classpath. */
public final class BuiltinRules {
    private static final String RESOURCE_ROOT = "schematron/";
    private static final Map<String, String> SCHEMAS = Map.of(
            "activity flow", "sbgn_af.sch",
            "AF", "sbgn_af.sch",
            "entity relationship", "sbgn_er.sch",
            "ER", "sbgn_er.sch",
            "process description", "sbgn_pd.sch",
            "PD", "sbgn_pd.sch");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private BuiltinRules() {
    }

    /** Return provenance for the built-in rules. */
    public static RulesInfo rulesInfo() throws IOException {
        JsonNode manifest = manifest();
        return new RulesInfo(
                "builtin",
                manifest.path("ruleset").asText(),
                manifest.path("ruleset_version").asText(),
                manifest.path("ruleset_digest").asText(),
                manifest.path("source_revision").isNull()
                        ? null : manifest.path("source_revision").asText());
    }

    static String schemaName(String language) {
        String name = SCHEMAS.get(language);
        if (name == null) {
            throw new IllegalArgumentException(
                    "SCHEMATRON_SCHEMA_ERROR: unsupported SBGN language " + language);
        }
        return name;
    }

    static ClassPathResource resource(String name) throws IOException {
        byte[] data = data(name);
        return new ClassPathResource(RESOURCE_ROOT + name, BuiltinRules.class.getClassLoader());
    }

    static byte[] data(String name) throws IOException {
        byte[] data = read(name);
        String expected = manifest().path("files").path(name).path("sha256").asText();
        String actual;
        try {
            actual = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
        if (!actual.equals(expected)) {
            throw new IllegalStateException("BUILTIN_RULES_CORRUPT: " + name);
        }
        return data;
    }

    /** Detect the map language in one SBGN-ML document. */
    public static String detectLanguage(Path documentPath) throws Exception {
        return inspectDocument(documentPath).language();
    }

    static DocumentInfo inspectDocument(Path documentPath) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        Element root = factory.newDocumentBuilder().parse(documentPath.toFile()).getDocumentElement();
        String namespace = root.getNamespaceURI();
        if (!"sbgn".equals(root.getLocalName())) {
            throw new IllegalArgumentException("SCHEMATRON_SCHEMA_ERROR: SBGN root is missing");
        }
        for (Node child = root.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child instanceof Element element && "map".equals(element.getLocalName())
                    && java.util.Objects.equals(namespace, element.getNamespaceURI())) {
                String language = element.getAttribute("language");
                if (!language.isBlank()) {
                    return new DocumentInfo(namespace, language);
                }
            }
        }
        throw new IllegalArgumentException("SCHEMATRON_SCHEMA_ERROR: SBGN map language is missing");
    }

    record DocumentInfo(String namespace, String language) {
    }

    private static JsonNode manifest() throws IOException {
        return MAPPER.readTree(read("manifest.json"));
    }

    private static byte[] read(String name) throws IOException {
        try (InputStream input = BuiltinRules.class.getClassLoader()
                .getResourceAsStream(RESOURCE_ROOT + name)) {
            if (input == null) {
                throw new IOException("BUILTIN_RULES_MISSING: " + name);
            }
            return input.readAllBytes();
        }
    }
}
