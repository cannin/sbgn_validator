package org.sbgn.schematron;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import javax.xml.parsers.DocumentBuilderFactory;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;

final class SvrlNormalizerTest {
    @Test
    void normalizesDiagnosticsAndCurrentTime() throws Exception {
        String xml = """
                <svrl:schematron-output xmlns:svrl="http://purl.oclc.org/dsdl/svrl">
                  <svrl:failed-assert id="pd1" role="error" location="/sbgn[1]/map[1]/arc[2]" test="false()">
                    <svrl:text>Timestamp: 18:43:22</svrl:text>
                    <svrl:diagnostic-reference diagnostic="id">Id: a1</svrl:diagnostic-reference>
                  </svrl:failed-assert>
                </svrl:schematron-output>
                """;
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        Document document = factory.newDocumentBuilder().parse(
                new ByteArrayInputStream(xml.getBytes(StandardCharsets.UTF_8)));
        List<CanonicalFinding> findings = SvrlNormalizer.normalize(document);
        assertEquals(1, findings.size());
        assertEquals("failed-assert", findings.get(0).type());
        assertEquals("a1", findings.get(0).derived().element_id());
        assertEquals("arc", findings.get(0).derived().element_kind());
        assertEquals("Timestamp: <CURRENT_TIME>", findings.get(0).text());
        assertEquals("id", findings.get(0).diagnostic_references().get(0).diagnostic());
    }
}
