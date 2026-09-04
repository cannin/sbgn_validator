package org.sbgn.schematron;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

/** Convert processor-specific SVRL DOM output into canonical findings. */
public final class SvrlNormalizer {
    private static final String SVRL = "http://purl.oclc.org/dsdl/svrl";
    private static final Pattern CLOCK = Pattern.compile("\\b(?:[01]\\d|2[0-3]):[0-5]\\d:[0-5]\\d(?:\\.\\d+)?(?:Z|[+-][0-2]\\d:[0-5]\\d)?\\b");
    private static final Pattern LOCATION_ELEMENT = Pattern.compile("(?:\\*:|[A-Za-z_][\\w.-]*:)?([A-Za-z_][\\w.-]*)\\[");

    private SvrlNormalizer() {
    }

    /** Normalize failed assertions and successful reports.
     *
     * @param svrl processor-generated SVRL document
     * @return deterministically ordered SVRL-aligned findings
     */
    public static List<CanonicalFinding> normalize(Document svrl) {
        List<CanonicalFinding> findings = new ArrayList<>();
        collect(svrl, "failed-assert", findings);
        collect(svrl, "successful-report", findings);
        findings.sort(Comparator.comparing(CanonicalFinding::id, Comparator.nullsFirst(String::compareTo))
                .thenComparing(item -> item.derived().element_id(), Comparator.nullsFirst(String::compareTo))
                .thenComparing(CanonicalFinding::location, Comparator.nullsFirst(String::compareTo))
                .thenComparing(CanonicalFinding::text));
        return List.copyOf(findings);
    }

    private static void collect(Document svrl, String elementName,
            List<CanonicalFinding> findings) {
        NodeList nodes = svrl.getElementsByTagNameNS(SVRL, elementName);
        for (int index = 0; index < nodes.getLength(); index++) {
            Element failure = (Element) nodes.item(index);
            List<DiagnosticReference> diagnostics = diagnostics(failure);
            String location = nullableAttribute(failure, "location");
            String elementId = diagnostics.stream()
                    .filter(item -> "id".equals(item.diagnostic()))
                    .map(DiagnosticReference::text)
                    .findFirst()
                    .orElse(null);
            findings.add(new CanonicalFinding(
                    nullableAttribute(failure, "id"),
                    elementName,
                    nullableAttribute(failure, "role"),
                    nullableAttribute(failure, "flag"),
                    location,
                    nullableAttribute(failure, "test"),
                    message(failure),
                    diagnostics,
                    new DerivedIdentity(blankToNull(elementId), elementKind(location))));
        }
    }

    private static List<DiagnosticReference> diagnostics(Element failure) {
        List<DiagnosticReference> values = new ArrayList<>();
        NodeList nodes = failure.getElementsByTagNameNS(SVRL, "diagnostic-reference");
        for (int index = 0; index < nodes.getLength(); index++) {
            Element diagnostic = (Element) nodes.item(index);
            String key = diagnostic.getAttribute("diagnostic");
            String value = normalizeText(diagnostic.getTextContent());
            int colon = value.indexOf(':');
            if (colon >= 0 && value.substring(0, colon).trim().equalsIgnoreCase(key)) {
                value = value.substring(colon + 1).trim();
            }
            values.add(new DiagnosticReference(key, value));
        }
        return List.copyOf(values);
    }

    private static String message(Element failure) {
        for (Node child = failure.getFirstChild(); child != null; child = child.getNextSibling()) {
            if (child instanceof Element element
                    && SVRL.equals(element.getNamespaceURI())
                    && "text".equals(element.getLocalName())) {
                return normalizeText(element.getTextContent());
            }
        }
        return "";
    }

    private static String normalizeText(String value) {
        String whitespace = value.replaceAll("\\s+", " ").trim();
        return CLOCK.matcher(whitespace).replaceAll("<CURRENT_TIME>");
    }

    private static String nullableAttribute(Element element, String name) {
        return blankToNull(element.getAttribute(name));
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private static String elementKind(String location) {
        if (location == null) {
            return null;
        }
        Matcher matcher = LOCATION_ELEMENT.matcher(location);
        String last = null;
        while (matcher.find()) {
            last = matcher.group(1).toLowerCase(Locale.ROOT);
        }
        return last;
    }
}
