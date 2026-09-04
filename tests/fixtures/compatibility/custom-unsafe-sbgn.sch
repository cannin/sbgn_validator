<?xml version="1.0" encoding="UTF-8"?>
<iso:schema xmlns:iso="http://purl.oclc.org/dsdl/schematron" defaultPhase="basic">
  <iso:ns prefix="sbgn" uri="urn:not-sbgn"/>
  <iso:phase id="basic">
    <iso:active pattern="unsafe-binding"/>
  </iso:phase>
  <iso:pattern id="unsafe-binding">
    <iso:rule context="sbgn:map">
      <iso:assert id="custom02" role="error" test="true()">Always valid.</iso:assert>
    </iso:rule>
  </iso:pattern>
</iso:schema>
