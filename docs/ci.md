# Continuous integration

`.github/workflows/native-schematron.yml` runs from the repository root.

The `rules-sync-check` job rejects stale or manually edited package snapshots.
The `package-rules` job builds the wheel, R source package, Go and Rust
binaries/crate, shaded JAR, and npm tarball, then validates from isolated
temporary directories. It checks both passing and failing models, compares
archive resource bytes with the canonical rules, and compares all six built-in
ruleset digests.

The Linux job runs the complete six-runtime comparison against committed Java
goldens. A second matrix runs normal R package checks on Linux, macOS, and
Windows because libxml2 discovery and native compilation are platform-sensitive.

`.github/workflows/release.yml` runs for coordinated `vX.Y.Z` tags. Publication
depends on both the full conformance gate and the isolated packaged-resource
gate. It builds all six ecosystems, tagged source archives, supported Go and
Rust binaries, and one SHA-256 checksum file before creating the GitHub
release. A matching `go/vX.Y.Z` tag identifies the module rooted in `go/`.
