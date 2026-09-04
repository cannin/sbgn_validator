# Repository agent instructions

## Commands

Run the full repository verification from the root:

```sh
scripts/test-all.sh
```

After editing `validation/rules/*.sch`, regenerate and verify package snapshots:

```sh
uv run --project tools python tools/sync_rules.py
uv run --project tools python tools/verify_rules.py
```

Regenerate Java oracle reports only when intentionally changing the schemas,
fixtures, or pinned Java reference stack:

```sh
scripts/generate-oracle.sh
```

Language-specific checks:

```sh
mvn -f java/pom.xml test package
(cd javascript && npm test)
(cd python && uv run --extra test ruff check . && uv run --extra test pytest)
(cd go && go test ./... && go vet ./...)
(cd rust && cargo fmt --check && cargo test)
R CMD build r
R CMD check --no-manual sbgnvalidator_0.1.1.tar.gz
```

## Architecture boundaries

- `validation/rules/*.sch` is the single executable semantic rule source.
- Package-local Schematron directories are generated; never edit them directly.
- Do not translate individual SBGN rules into host-language conditions.
- Java is a test oracle, never a runtime service for another implementation.
- Each backend must parse, compile, and execute Schematron independently.
- No backend may invoke another language, subprocess validator, or network
  validation service.
- Unsupported Schematron or XPath constructs must fail explicitly.
- Keep XML structural validation separate from semantic Schematron validation.
- Preserve deterministic normalized report ordering and clock normalization.
- Normalize each reported Schematron `test` expression by trimming it and
  collapsing all whitespace runs to one ASCII space. Never change the
  canonical XPath expression itself.

## Legacy SBGN-ML 0.2 compatibility

The sole public compatibility option is `--allow-sbgnml-0.2`. Do not add a
deprecated or generic namespace-tolerance alias. The corresponding built-in
phase is `basic-allow-sbgnml-0.2`.

Treat compatibility as an explicit namespace policy, separate from phase,
language, and rule-source selection:

- strict mode accepts exactly `http://sbgn.org/libsbgn/0.3`;
- legacy mode accepts exactly 0.3 or `http://sbgn.org/libsbgn/0.2`;
- missing, unrelated, and unknown/future namespaces always fail preflight;
- 0.3 behavior must be identical with or without the legacy option.

For an accepted 0.2 document, keep the document unchanged. Parse a private
in-memory Schematron representation and change only the ISO Schematron
`<iso:ns prefix="sbgn" uri="...">` binding from 0.3 to 0.2 before compilation.
Do not use regex or raw-text replacement, rewrite XPath expressions, mutate a
shared parsed schema, or modify canonical/package resources at runtime. Apply
the same operation to built-in and explicit custom rules; fail explicitly when
a custom schema cannot establish the expected `sbgn` binding safely. Include
the effective namespace policy in any compiled-schema cache identity.

The previous implementation merely selected a phase without rebinding
`sbgn`. Consequently, `sbgn:*` rules matched no 0.2 nodes and invalid documents
could report `valid: true`. Tests must prove that semantic rules execute, not
only that the namespace assertion disappears. In particular,
`tests/examples/go_mf_conflicts.sbgn` must remain unchanged and, in legacy mode,
must report at least `pd10102`, `pd10132`, and `pd10141`. Do not repair its
biology as part of namespace compatibility.

Implement Java first as the oracle, then require Go, Rust, Python, JavaScript,
and R normalized reports to match. Cover PD, AF, ER, built-in and custom rules,
strict rejection, sequential 0.2/0.3 reuse, reasonable concurrency, and actual
packaged artifacts.

The phase identifier change in the canonical `.sch` files was explicitly
authorized as metadata-only. No assertion, diagnostic, pattern activation, or
semantic XPath rule changed. After synchronization, every package snapshot and
manifest must report this ruleset digest:

```text
sha256:1a601e1f5ff4f02b53a329bf7cdcd7149eed1b537ea2964f4ed4cfa0a9d87c14
```

The working implementation uses exact root-namespace preflight followed by a
private compiler input. For 0.2, mutate only the parsed ISO Schematron `sbgn`
binding; preserve custom-resource base resolution and reject missing, duplicate,
or contradictory bindings. Never key or reuse compiled state without the
effective namespace. The conformance manifest contains 105 cases, including
valid AF/ER/PD 0.2 inputs, unchanged 0.3 behavior, and the invalid process
fixture. `scripts/test-packaged-rules.sh` must run both valid and invalid legacy
cases from isolated built artifacts and compare all six built-in digests.

## Testing requirements

- Every backend consumes `conformance/manifest.json`.
- Every backend must match all committed Java reports in
  `conformance/oracle/java/`.
- Run R package build and check after changing R or C++ sources.
- Run the feature inventory after changing an authoritative schema.
- Do not silently update committed Java oracle files during ordinary tests.

## Release process

The public upstream repository is
`https://github.com/cannin/sbgn_validator`. Release 0.1.1 established the
cross-language normalized-`test` contract; all six backends and packaged
artifact checks must preserve it.

Both CI and release workflows must provision Python 3.14 explicitly through
`astral-sh/setup-uv`; hosted runners must not be assumed to provide it.

Keep `VERSION`, all six ecosystem package versions, generated lockfiles, and
reported backend implementation versions synchronized. The Schematron ruleset
version is independent and must not be bumped merely for a validator release.
Check a proposed coordinated version with:

```sh
scripts/check-versions.sh X.Y.Z
```

Before tagging, run both `scripts/test-all.sh` and
`scripts/test-packaged-rules.sh`. The tag-driven release workflow publishes
complete and per-language source archives, Python, R, Java, and npm packages,
Go and Rust executables, plus `SHA256SUMS.txt`. Create both tags at the same
tested commit and never move a published tag:

```sh
git tag -a vX.Y.Z -m "SBGN Validator X.Y.Z"
git tag -a go/vX.Y.Z -m "SBGN Validator Go X.Y.Z"
git push origin main
git push origin vX.Y.Z go/vX.Y.Z
```

The root tag triggers publication; the `go/` tag supplies the semantic version
for the nested Go module. Release artifacts must come from the tagged commit,
and publication must remain blocked on conformance, rules synchronization,
packaged-resource tests, and cross-runtime digest equality.

## Repository layout

- `java/`, `javascript/`, `r/`, `rust/`, `go/`, and `python/`: active backends.
- `validation/` and `tests/fixtures/`: authoritative shared inputs.
- `conformance/`: manifest, profile inventory, report schema, and oracle.
- `tools/`: inventory and comparison utilities.
- `ignore/`: archived implementations and generated artifacts; do not import
  or build code from it.
