<?xml version="1.0" encoding="UTF-8"?>
<iso:schema xmlns:iso="http://purl.oclc.org/dsdl/schematron" defaultPhase="basic">
  <iso:ns prefix="sbgn" uri="http://sbgn.org/libsbgn/0.3"/>
  <iso:ns prefix="custom" uri="urn:libsbgn-validator:test"/>
  <iso:phase id="basic">
    <iso:active pattern="custom-namespace"/>
  </iso:phase>
  <iso:pattern id="custom-namespace">
    <iso:rule context="sbgn:map">
      <iso:assert id="custom01" role="error" test="custom:marker">
        The custom namespace binding must remain available.
      </iso:assert>
    </iso:rule>
  </iso:pattern>
</iso:schema>
