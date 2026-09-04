# Rules distribution

`validation/rules/` is the only editable Schematron directory. Its three
schemas are the semantic source of truth. Every language package contains a
generated, byte-identical snapshot so installed artifacts work offline and do
not depend on the monorepo layout.

## Updating rules

1. Edit or update only `validation/rules/*.sch`.
2. Update upstream provenance when a specific revision is known.
3. Run `uv run --project tools python tools/sync_rules.py`.
4. Review the canonical manifest and all generated snapshots.
5. Run `uv run --project tools python tools/verify_rules.py`.
6. Run `scripts/test-all.sh` and the package artifact tests.
7. Commit canonical and generated changes together.

Package-local `.sch` files and manifests must not be edited directly. Their
adjacent `README.generated.md` files identify them as generated resources.

## Manifest and digest

`validation/rules/manifest.json` records the ruleset version, optional pinned
source revision, each file's SHA-256, and one ruleset digest. The ruleset
digest is SHA-256 over the concatenation of `filename` encoded as UTF-8, one
NUL byte, and the exact file bytes, repeated in lexicographic filename order.
No XML or newline normalization occurs.

`tools/verify_rules.py` is read-only. It reports missing, extra, stale, or
byte-different generated resources, including generated-directory metadata.
It also rejects unexpected files in the canonical directory so a new runtime
dependency cannot be omitted from package snapshots accidentally. CI runs it
before language tests.

## Runtime selection

The default validation API reads the SBGN map's `language` attribute and
selects the packaged PD, AF, or ER schema. Callers may explicitly supply a
Schematron path to override built-in selection. There is no current-directory,
environment-variable, network, or monorepo-root fallback.

Resource mechanisms are idiomatic to each package:

- Python uses `importlib.resources` and includes files in wheel and sdist.
- R installs files beneath `inst/schematron` and locates them with
  `system.file()`.
- Go uses `embed.FS`.
- Rust uses `include_str!`; the crate also carries the patched pure-Rust
  Schematron engine sources it compiles against, so Cargo cannot silently
  substitute an incompatible registry engine while packaging.
- Java loads classpath resources, including from the shaded JAR.
- JavaScript is currently Node-only and ships resource files in the npm
  package.

Every implementation exposes built-in rules provenance. Each CLI provides
`--rules-info`. Custom rules remain explicit through `--schema PATH` or the
corresponding language API.

## Test separation

Canonical-source conformance tests continue to pass root schema paths so they
measure processor equivalence over exactly the same source bytes. Package
tests omit schema paths and execute built-in rules from actual or compiled
artifacts. These are separate guarantees: semantic equivalence and deployment
self-containment.

Artifact tests copy both a passing and failing model into an isolated temporary
directory, invoke every CLI without a schema option, and require the failing
model to emit `pd10110`. Wheel, JAR, crate, npm, and R archives are also opened
and their packaged rule and manifest bytes are compared directly with the
canonical files. The same isolated artifacts also validate a passing 0.2 model
and require the legacy invalid process fixture to emit `pd10102`, `pd10132`,
and `pd10141` with `--allow-sbgnml-0.2`.
