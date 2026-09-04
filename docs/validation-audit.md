# Validation audit

Audit date: 2026-09-02.

The repository contains three authoritative ISO Schematron files at
`validation/rules/sbgn_{af,er,pd}.sch`. They target SBGN-ML 0.3 and declare no
`queryBinding`, while using XPath 1.0 expressions, XSLT `current()`, XPath 2
`distinct-values()`, and XPath 2 `current-time()`.

Earlier root implementations used manually implemented semantic equivalents.
They are preserved under `ignore/legacy-root/` for reference and are not part
of the active build, package, or test paths.

The upstream semantic fixture directory contains 98 `.sbgn` files and one text
note. All active backends reference these root schemas and fixtures rather than
duplicating them.

Installed local toolchains include Java 23, Maven 3.9.16, Node 24, npm 11,
R 4.2.2, Rust 1.97, Go, and uv. The private SearXNG endpoint returned HTTP 502,
so dependency versions were verified against authoritative registries.
