package org.sbgn.schematron;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

/** Creates a private compiler input with an effective Schematron namespace binding. */
final class SchematronNamespace {
    static final String COMPATIBILITY_PHASE = "basic-allow-sbgnml-0.2";
    private static final String ISO = "http://purl.oclc.org/dsdl/schematron";

    private SchematronNamespace() {
    }

    static PreparedSchema prepare(
            byte[] source, String requestedPhase, NamespacePolicy policy,
            String effectiveNamespace) throws Exception {
        if (policy == NamespacePolicy.STRICT_03) {
            return new PreparedSchema(source, requestedPhase);
        }
        Document document = parse(source);
        String phase = requestedPhase;
        if ("basic".equals(requestedPhase) && hasPhase(document, COMPATIBILITY_PHASE)) {
            phase = COMPATIBILITY_PHASE;
        }
        if (NamespacePolicy.SBGN_ML_03.equals(effectiveNamespace)) {
            return new PreparedSchema(source, phase);
        }
        Element binding = sbgnBinding(document);
        String original = binding.getAttribute("uri");
        if (!NamespacePolicy.SBGN_ML_03.equals(original)
                && !NamespacePolicy.SBGN_ML_02.equals(original)) {
            throw new IllegalArgumentException(
                    "SCHEMATRON_NAMESPACE_ERROR: unsafe sbgn binding " + original);
        }
        binding.setAttribute("uri", NamespacePolicy.SBGN_ML_02);
        TransformerFactory transformerFactory = TransformerFactory.newInstance();
        transformerFactory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        transformerFactory.setAttribute(XMLConstants.ACCESS_EXTERNAL_STYLESHEET, "");
        var transformer = transformerFactory.newTransformer();
        transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "no");
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        transformer.transform(new DOMSource(document), new StreamResult(output));
        return new PreparedSchema(output.toByteArray(), phase);
    }

    private static Document parse(byte[] source) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        return factory.newDocumentBuilder().parse(new ByteArrayInputStream(source));
    }

    private static boolean hasPhase(Document document, String id) {
        NodeList phases = document.getElementsByTagNameNS(ISO, "phase");
        for (int index = 0; index < phases.getLength(); index++) {
            if (id.equals(((Element) phases.item(index)).getAttribute("id"))) {
                return true;
            }
        }
        return false;
    }

    private static Element sbgnBinding(Document document) {
        NodeList bindings = document.getElementsByTagNameNS(ISO, "ns");
        Element match = null;
        for (int index = 0; index < bindings.getLength(); index++) {
            Element candidate = (Element) bindings.item(index);
            if (!"sbgn".equals(candidate.getAttribute("prefix"))) {
                continue;
            }
            if (match != null) {
                throw new IllegalArgumentException(
                        "SCHEMATRON_NAMESPACE_ERROR: multiple sbgn namespace bindings");
            }
            match = candidate;
        }
        if (match == null) {
            throw new IllegalArgumentException(
                    "SCHEMATRON_NAMESPACE_ERROR: missing sbgn namespace binding");
        }
        return match;
    }

    record PreparedSchema(byte[] data, String phase) {
    }
}
