# libSBGN Schematron compatibility profile

`libSBGN-Schematron-Profile-1` is generated from the three executable schemas
in `../validation/rules/`. They retain the upstream rules and add one shared
Schematron namespace assertion. The machine-readable inventories are
`conformance/profile/schematron-features.json` and
`conformance/profile/xpath-features.json`.
The source checkout has no Git metadata, so the inventory pins each schema by
SHA-256 content digest rather than inventing an upstream commit identifier.

The pinned corpus contains 59 patterns and rules, 60 assertions, 143 variables,
29 diagnostics, and 34 `value-of` elements. It uses phases, active patterns,
namespace declarations, rule variables, diagnostics, and mixed message text.
There are no reports, includes, abstract rules, extensions, or XQuery constructs.

The XPath compatibility surface is XPath 1 node selection and general
comparisons plus the functions `count`, `current`, `current-time`,
`distinct-values`, `false`, `local-name`, `namespace-uri`, `not`, `position`,
and `true`. `current()` has XSLT semantics: it retains the Schematron rule node
inside nested predicates. `distinct-values()` uses XPath 2 atomized sequence
semantics. The only historical syntax normalization is the corpus expression
`../local-name()`, interpreted as the standards-equivalent `local-name(..)`.

The schemas omit `queryBinding` despite using XPath 2 and XSLT functions. The
benchmark therefore records a schema-specific effective binding of
`xslt2-compatible` for exactly `sbgn_af.sch`, `sbgn_er.sch`, and `sbgn_pd.sch`.
Arbitrary Schematron inputs do not receive that override.

The `basic` phase activates `sbgn-namespace-0.3`, whose root-context assertion
requires `http://sbgn.org/libsbgn/0.3`. The `basic-allow-sbgnml-0.2` phase
contains the same upstream validation patterns without that assertion. CLI
`--allow-sbgnml-0.2` selects this phase after an exact 0.2-or-0.3 preflight. For
0.2 input it transiently rebinds the parsed ISO Schematron `sbgn` namespace to
0.2 before compilation. This is a metadata-only phase difference; every
semantic pattern remains active.

Run `uv run --project tools python tools/inventory_schematron.py` after updating
the upstream rules. A new function or construct is a profile change and must
first gain Java oracle evidence and then pass every native backend. Unsupported
syntax is an error; it is never skipped or coerced to a false result.
