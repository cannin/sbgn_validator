# SBGN Validator architecture

The libSBGN Schematron files are the sole executable rule source. They contain
the upstream rules plus the shared `sbgn-namespace-0.3` compatibility guard.
Every backend performs schema parsing/compilation, secure XML parsing,
validation, and SVRL-aligned normalization. Unsupported syntax is a hard error.

The common lifecycle is `parse_schema`, `compile_schema`, `parse_document`,
`validate(compiled_schema, document, phase)`, and `normalize_report`. Compiled
schemas are reusable across documents. Host implementations contain generic
Schematron and XPath mechanics only; none contains an SBGN rule assertion.

Namespace acceptance is a small policy applied before compilation. Strict mode
accepts only the exact 0.3 URI; legacy mode additionally accepts only the exact
0.2 URI. For 0.2 input, the validator selects
`basic-allow-sbgnml-0.2` and changes only the parsed ISO Schematron
`ns[prefix="sbgn"]` binding in a transient copy before compiling. The document,
canonical rules, packaged bytes, and XPath expressions remain unchanged.

Java is the behavioral oracle because SchXslt2 and Saxon provide the broadest
Schematron/XPath/XSLT semantics. Java's transformation pipeline is not imposed
on other languages and is never called by them. Rust, Go, Python, and
JavaScript use their native direct processors where they pass the executable
profile. R uses a project-owned Rcpp/libxml2 direct interpreter and implements
only proven profile gaps.

Raw SVRL is not compared because prefixes, location spellings, whitespace, and
metadata differ between processors. All backends emit the SVRL-aligned report
schema in `conformance/normalized-report.schema.json`. Its `findings` retain
SVRL names (`failed-assert`, `successful-report`, `id`, `text`, and ordered
`diagnostic_references`), while SBGN-specific identity is isolated under
`derived`. Dynamic `current-time()` text is replaced by `<CURRENT_TIME>` during
normalization.

The Rust crate's direct-interpreter architecture informs missing-feature work:
an explicit schema model, compiled XPath programs, separate validation state,
and fail-closed feature handling. No Rust source or runtime is embedded by
another backend.

XML external entities, unrestricted DTD loading, network resolution, and
arbitrary filesystem resolution are denied by default. A future include
resolver must be explicitly rooted and supplied by the caller.

The conceptual error taxonomy separates XML parse, Schematron parse/schema,
unsupported Schematron feature, XPath parse/static/dynamic/unsupported feature,
unknown phase, validation assertion/report, and internal validator errors. A
runtime error is never converted into a validation issue.
