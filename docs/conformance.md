# Conformance

`tools/inventory_schematron.py` regenerates the executable compatibility
profile. `tools/build_manifest.py` regenerates the one shared fixture manifest.
All paths are repository-root relative so each independent runtime consumes the
same schemas and inputs.

The manifest currently covers all 98 upstream basic-phase fixtures, one strict
namespace fixture, one sanity-phase execution that proves `current-time()` and
phase selection, and five explicit legacy-compatibility cases. The
upstream rule corpus itself exercises nested-predicate `current()`,
`distinct-values()`, variables, diagnostics, namespaces, and position.

Comparison ignores backend identity and processor-specific locations but
compares validity and sorted semantic finding identity: finding ID, SVRL
finding type, role, flag, derived element ID/kind, normalized text, and ordered
diagnostic references.

Strict namespace failure is tested as the Schematron failed assertion
`sbgn-namespace-0.3`. Legacy fixtures test exact 0.2 acceptance, unchanged 0.3
behavior, and semantic rule execution after the transient `sbgn` binding is
changed to 0.2. The invalid regression fixture must report `pd10102`,
`pd10132`, and `pd10141`; a merely empty successful report is not sufficient.
Mismatches use explicit classifications rather than a generic test failure.
Oracle regeneration is explicit through `scripts/generate-oracle.sh` and is
never part of ordinary tests.

`scripts/test-all.sh` runs language tests, regenerates non-oracle results, runs
R build/check, compares every backend to Java, and regenerates the capability
matrix. The Java oracle must first agree with the upstream fixture intent; it
is not accepted merely because Java produced it.
