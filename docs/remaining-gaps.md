# Remaining gaps and compatibility patches

All six backends compile the three authoritative schemas and match the 100
committed normalized Java oracle reports. There is no unsupported construct in
the current pinned libSBGN profile.

The profile is intentionally not a claim of general ISO Schematron or XPath
3.1 completeness. Inputs outside the generated inventory can fail with an
unsupported-feature error. Includes, abstract patterns/rules, arbitrary XSLT
extensions, and XQuery are outside the current profile.

Three general compatibility fixes were needed:

- ph-schematron 10.0.1 passes a legacy unqualified phase parameter, so the Java
  adapter also supplies SchXslt2 1.11.2's namespaced phase parameter.
- the Rust 0.5.1 dependency is vendored with narrow profile patches for the
  effective query binding, referenced diagnostics, sequence rendering, and the
  historical `../local-name()` spelling.
- Go, Python, JavaScript, and R register or preserve XSLT `current()` separately
  from the changing predicate context.

These changes implement language features, never SBGN rule IDs or assertions.
