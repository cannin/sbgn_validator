# SBGN Validator

Cross-language semantic validation of SBGN-ML using the original libSBGN
Schematron files as the single executable rule source.

Current validator version: **0.1.1**. The bundled ruleset has its own version
and digest, reported by `--rules-info`.

The project provides independent implementations for Java, JavaScript, R,
Rust, Go, and Python. Java supplies the verified behavioral oracle, but no
other implementation invokes Java or another language at runtime.

## Status

All six implementations produce equivalent normalized results for the shared
105-case suite:

- 98 upstream libSBGN positive and negative fixtures
- one sanity-phase fixture covering phase selection and `current-time()`
- one strict namespace fixture proving fail-closed behavior
- five legacy compatibility cases covering valid AF/ER/PD, invalid PD semantic
  findings, and unchanged 0.3 behavior
- all three schemas: `sbgn_af.sch`, `sbgn_er.sch`, and `sbgn_pd.sch`

Reported Schematron `test` expressions are trimmed and every whitespace run is
collapsed to one space. This keeps JSON output readable without changing the
expression that was evaluated.

The executable schemas remain in `validation/rules/`; they contain the upstream
rules plus one shared namespace guard and do not translate individual SBGN
rules into host-language code.

Each package and compiled executable includes a byte-identical generated copy
of those schemas. Normal validation detects PD, AF, or ER from the document and
uses the built-in schema, so users do not need the source repository or a rule
path. Explicit `--schema PATH` remains available for custom Schematron.

## Architecture

Each backend performs the same conceptual stages:

```text
Schematron schema -> parse and compile -> reusable compiled schema
SBGN-ML document -> secure XML parse -> validate -> normalized report
```

Java uses ph-schematron, SchXslt2, and Saxon as the reference implementation.
The other runtimes use native direct Schematron interpreters and XPath engines.
R uses a project-owned Rcpp/libxml2 interpreter. Unsupported constructs fail
explicitly rather than being skipped or approximated.

When a language does not have a complete native Schematron stack, its backend
uses the closest native XML, XPath, and Schematron implementation available and
adds only the general language features required by the generated libSBGN
compatibility profile. These adapters implement Schematron or XPath mechanics,
such as preserving the rule context for `current()`; they never contain
translations or special cases for individual SBGN rule IDs.

The current strategies are:

- Java uses the full ph-schematron, SchXslt2, and Saxon reference pipeline.
- Rust compiles vendored `schematron` engine sources directly into the crate
  with narrow, profile-level patches.
- Go uses Helium's native XML, XPath, and Schematron support with a profile
  adapter.
- Python uses pyschematron and elementpath with a profile adapter.
- JavaScript uses node-schematron and FontoXPath with a profile adapter.
- R uses a project-owned direct interpreter built with Rcpp and libxml2 because
  R has no sufficiently complete native Schematron package.

Every backend loads the same original `.sch` files. No backend invokes another
language, shells out to a reference validator, or substitutes generated
host-language rules. If an input schema uses a construct outside the tested
profile, validation stops with an explicit unsupported-feature error. New
features are implemented only after their behavior is established by the Java
oracle and added to the shared conformance suite.

## Result format

Every implementation returns the same SVRL-aligned report. Command-line tools
serialize it as JSON; language APIs return the corresponding native object,
record, struct, dictionary, or R list.

```json
{
  "schema": "sbgn_pd.sch",
  "phase": "basic",
  "valid": false,
  "findings": [
    {
      "id": "pd10110",
      "type": "failed-assert",
      "role": "error",
      "flag": null,
      "location": "/sbgn:sbgn[1]/sbgn:map[1]/sbgn:arc[1]",
      "test": "...",
      "text": "Modulation arc must have target reference to PN classes",
      "diagnostic_references": [
        {"diagnostic": "id", "text": "arc1"}
      ],
      "derived": {
        "element_id": "arc1",
        "element_kind": "arc"
      }
    }
  ]
}
```

The finding names intentionally mirror SVRL: `failed-assert`,
`successful-report`, `id`, `text`, and `diagnostic-reference`. The `derived`
object contains convenient SBGN identity that is not itself part of SVRL. A
rule violation is a successful validation operation with `valid: false`;
parser, schema, XPath, and unsupported-feature failures are errors rather than
findings.

Backend metadata is omitted by default so reports from different language
commands have the same semantic shape. Add `--backend` to any validator command
to include the implementation, engine, XPath, and profile versions used.

## Namespace policy

Strict validation accepts only the exact SBGN-ML 0.3 namespace
`http://sbgn.org/libsbgn/0.3`. Missing, unrelated, and unknown namespaces fail
before semantic validation.

All six commands accept `--allow-sbgnml-0.2` for legacy SBGN-ML 0.2 semantic
compatibility. It additionally accepts the exact 0.2 namespace, keeps the
document unchanged, and applies the normal PD, AF, or ER rules with their
in-memory `sbgn` XPath namespace binding set to 0.2. Semantic rules are not
waived: invalid legacy documents still report their normal rule IDs. The flag
does not accept arbitrary namespace mismatches, convert a document to 0.3, or
claim complete historical 0.2 XSD conformance.

See [`docs/example-output.json`](docs/example-output.json) for a complete
standalone example.

## Requirements

- Java 17 or newer and Maven
- Node.js 18 or newer and npm
- R 4.2 or newer, Rcpp, jsonlite, a C++17 compiler, libxml2 development files, and
  `pkg-config` or `xml2-config`
- Rust 1.96 or newer and Cargo
- Go 1.26.1 or newer
- Python 3.14 or newer and uv

R development and conformance tooling additionally uses `testthat` and `lintr`.
The R runtime backend imports Rcpp and jsonlite and links directly to libxml2.

## Quick start

After building or installing an implementation, validate using only the model:

```sh
sbgn-validator model.sbgn
```

Use `sbgn-validator --rules-info` to report the built-in ruleset version and
digest. Use `--schema custom.sch` only when intentionally overriding the
packaged rules.

Run the complete test, build, and cross-runtime comparison suite:

```sh
./scripts/test-all.sh
```

Build isolated release artifacts and prove their bundled rules work without a
repository-relative rule path:

```sh
./scripts/test-packaged-rules.sh
```

Rule maintainers edit only `validation/rules/*.sch`, then run:

```sh
uv run --project tools python tools/sync_rules.py
uv run --project tools python tools/verify_rules.py
```

Regenerate committed Java oracle files only after intentionally updating the
schemas, fixtures, or pinned Java dependencies:

```sh
./scripts/generate-oracle.sh
```

## Individual implementations

The corresponding library entry points are `SbgnValidator.validate(document)`
in Java, `validateSbgn(document)` in JavaScript, `validate_sbgn(document)` in R
and Python, `sbgnvalidator.Validate(ctx, document, phase)` in Go, and
`Validator::builtin_for_document(document, phase)` in Rust. Each language also
exposes `rules_info`/`rulesInfo`/`RulesInfo` in its idiomatic naming style.

### Java reference

```sh
mvn -f java/pom.xml test package
```

Validate one document and write the normalized JSON report to standard output:

```sh
mvn -q -f java/pom.xml package
java -jar java/target/sbgn-validator-0.1.1.jar \
  tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn \
  --phase basic
```

Oracle generation remains a separate explicit operation through
`scripts/generate-oracle.sh`.

### JavaScript

```sh
cd javascript
npm ci
npm test
```

```sh
node javascript/src/cli.js \
  tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn
```

### R

```sh
R CMD INSTALL r
R CMD build r
R CMD check --no-manual sbgnvalidator_0.1.1.tar.gz
```

```sh
Rscript r/exec/sbgn-validator \
  tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn \
  --phase basic
```

### Rust

```sh
cargo test --manifest-path rust/Cargo.toml
cargo build --release --manifest-path rust/Cargo.toml --bin sbgn-validator
```

Validate with the compiled binary:

```sh
rust/target/release/sbgn-validator \
  tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn \
  --phase basic > docs/example-output-rust.json
```

### Go

```sh
make -C go all
```

Validate with the compiled current-platform binary:

```sh
go/dist/sbgn-validator \
  tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn \
  > docs/example-output-go.json
```

### Python

```sh
cd python
uv sync --extra test
uv run --extra test pytest
```

```sh
uv run --project python sbgn-validator \
  tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn \
  --phase basic
```

## Repository layout

```text
libsbgn_lang/
├── conformance/       shared manifest, profile, schema, and Java oracle
├── docs/              architecture, compatibility, and runtime documentation
├── java/              Java reference validator
├── javascript/        JavaScript direct validator
├── r/                 Rcpp/libxml2 R package
├── rust/              Rust direct validator
├── go/                Go direct validator
├── python/            Python direct validator
├── validation/rules/  authoritative Schematron and generated manifest
├── scripts/           complete test and oracle-generation entry points
└── tools/             inventory, normalization, and comparison tools
```

## Conformance outputs

Every non-Java backend writes normalized, SVRL-aligned JSON beneath
`build/results/<language>/`. The comparison checks schema, phase, validity,
finding ID and type, role, flag, derived element identity, text, and ordered
diagnostic references.
Processor-specific XML serialization and path spelling are not compared.

See:

- [Validation architecture](docs/validation-architecture.md)
- [Compatibility profile](docs/libsbgn-schematron-profile.md)
- [Conformance process](docs/conformance.md)
- [Runtime matrix](docs/runtime-matrix.md)
- [Native R backend](docs/r-backend.md)
- [Remaining profile gaps](docs/remaining-gaps.md)
- [Rules distribution](docs/rules-distribution.md)

## Coordinated releases

A `vX.Y.Z` tag triggers `.github/workflows/release.yml`. The workflow first
runs the complete conformance and packaged-resource gates, then publishes:

- complete and per-language tagged source archives;
- Python wheel and source distribution;
- checked R source package;
- shaded Java JAR and npm package;
- Go binaries for Linux, macOS, and Windows on amd64 and arm64;
- Rust binaries for Linux amd64 musl, macOS arm64, and Windows amd64;
- `SHA256SUMS.txt` for every release asset.

Validator package versions are coordinated through `VERSION`. The embedded
Schematron ruleset version and digest remain independently versioned. Prepare a
release with:

```sh
./scripts/test-all.sh
./scripts/test-packaged-rules.sh
./scripts/check-versions.sh X.Y.Z
git tag -a vX.Y.Z -m "SBGN Validator X.Y.Z"
git tag -a go/vX.Y.Z -m "SBGN Validator Go X.Y.Z"
git push origin main
git push origin vX.Y.Z go/vX.Y.Z
```
