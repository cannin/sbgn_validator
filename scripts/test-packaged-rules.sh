#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PACKAGE_VERSION=$(tr -d '\r\n' <"$ROOT/VERSION")
ARTIFACT_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/sbgn-validator-packages.XXXXXX")
JAVA_JAR="$ROOT/java/target/sbgn-validator-$PACKAGE_VERSION.jar"
RUST_CRATE="$ROOT/rust/target/package/sbgn-validator-$PACKAGE_VERSION.crate"
R_TARBALL="$ARTIFACT_ROOT/sbgnvalidator_$PACKAGE_VERSION.tar.gz"
INVALID_SOURCE="$ROOT/tests/fixtures/error-test-files/PD/pd10110-fail-1.sbgn"
VALID_SOURCE="$ROOT/tests/fixtures/error-test-files/PD/pd10110-pass.sbgn"
LEGACY_INVALID_SOURCE="$ROOT/tests/examples/go_mf_conflicts.sbgn"
LEGACY_VALID_SOURCE="$ROOT/tests/fixtures/compatibility/sbgnml-0.2-pd-valid.sbgn"
INVALID_DOCUMENT="$ARTIFACT_ROOT/pd10110-fail-1.sbgn"
VALID_DOCUMENT="$ARTIFACT_ROOT/pd10110-pass.sbgn"
LEGACY_INVALID_DOCUMENT="$ARTIFACT_ROOT/go_mf_conflicts.sbgn"
LEGACY_VALID_DOCUMENT="$ARTIFACT_ROOT/sbgnml-0.2-pd-valid.sbgn"
mkdir -p "$ARTIFACT_ROOT/info" "$ARTIFACT_ROOT/python" "$ARTIFACT_ROOT/javascript"
cp "$INVALID_SOURCE" "$INVALID_DOCUMENT"
cp "$VALID_SOURCE" "$VALID_DOCUMENT"
cp "$LEGACY_INVALID_SOURCE" "$LEGACY_INVALID_DOCUMENT"
cp "$LEGACY_VALID_SOURCE" "$LEGACY_VALID_DOCUMENT"

uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rules.py"

mvn -q -f "$ROOT/java/pom.xml" package
(cd "$ARTIFACT_ROOT" && java -jar "$JAVA_JAR" \
  "$INVALID_DOCUMENT" >java-invalid-result.json)
(cd "$ARTIFACT_ROOT" && java -jar "$JAVA_JAR" \
  "$VALID_DOCUMENT" >java-valid-result.json)
(cd "$ARTIFACT_ROOT" && java -jar "$JAVA_JAR" --allow-sbgnml-0.2 \
  "$LEGACY_INVALID_DOCUMENT" >java-legacy-invalid-result.json)
(cd "$ARTIFACT_ROOT" && java -jar "$JAVA_JAR" --allow-sbgnml-0.2 \
  "$LEGACY_VALID_DOCUMENT" >java-legacy-valid-result.json)
(cd "$ARTIFACT_ROOT" && java -jar "$JAVA_JAR" \
  --rules-info >"$ARTIFACT_ROOT/info/java.json")
jar tf "$JAVA_JAR" >"$ARTIFACT_ROOT/java-files.txt"
grep -q schematron/sbgn_pd.sch "$ARTIFACT_ROOT/java-files.txt"
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rule_archive.py" \
  "$JAVA_JAR" schematron

uv build "$ROOT/python" --out-dir "$ARTIFACT_ROOT/python"
uv venv --python 3.14 "$ARTIFACT_ROOT/python-venv" >/dev/null
uv pip install --python "$ARTIFACT_ROOT/python-venv/bin/python" \
  "$ARTIFACT_ROOT"/python/*.whl >/dev/null
(cd "$ARTIFACT_ROOT" && "$ARTIFACT_ROOT/python-venv/bin/sbgn-validator" \
  "$INVALID_DOCUMENT" >python-invalid-result.json)
(cd "$ARTIFACT_ROOT" && "$ARTIFACT_ROOT/python-venv/bin/sbgn-validator" \
  "$VALID_DOCUMENT" >python-valid-result.json)
(cd "$ARTIFACT_ROOT" && "$ARTIFACT_ROOT/python-venv/bin/sbgn-validator" \
  --allow-sbgnml-0.2 "$LEGACY_INVALID_DOCUMENT" >python-legacy-invalid-result.json)
(cd "$ARTIFACT_ROOT" && "$ARTIFACT_ROOT/python-venv/bin/sbgn-validator" \
  --allow-sbgnml-0.2 "$LEGACY_VALID_DOCUMENT" >python-legacy-valid-result.json)
"$ARTIFACT_ROOT/python-venv/bin/sbgn-validator" \
  --rules-info >"$ARTIFACT_ROOT/info/python.json"
unzip -l "$ARTIFACT_ROOT"/python/*.whl >"$ARTIFACT_ROOT/python-files.txt"
grep -q schematron/sbgn_pd.sch "$ARTIFACT_ROOT/python-files.txt"
python_wheel=$(find "$ARTIFACT_ROOT/python" -maxdepth 1 -name '*.whl' -print -quit)
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rule_archive.py" \
  "$python_wheel" sbgn_validator/_resources/schematron
python_sdist=$(find "$ARTIFACT_ROOT/python" -maxdepth 1 -name '*.tar.gz' -print -quit)
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rule_archive.py" \
  "$python_sdist" "sbgn_validator-$PACKAGE_VERSION/sbgn_validator/_resources/schematron"

(cd "$ROOT/javascript" && npm pack \
  --pack-destination "$ARTIFACT_ROOT/javascript" >/dev/null)
mkdir -p "$ARTIFACT_ROOT/javascript-install"
(cd "$ARTIFACT_ROOT/javascript-install" && tar -xzf "$ARTIFACT_ROOT"/javascript/*.tgz)
cp -R "$ROOT/javascript/node_modules" "$ARTIFACT_ROOT/javascript-install/package/node_modules"
(cd "$ARTIFACT_ROOT" && node "$ARTIFACT_ROOT/javascript-install/package/src/cli.js" \
  "$INVALID_DOCUMENT" >javascript-invalid-result.json)
(cd "$ARTIFACT_ROOT" && node "$ARTIFACT_ROOT/javascript-install/package/src/cli.js" \
  "$VALID_DOCUMENT" >javascript-valid-result.json)
(cd "$ARTIFACT_ROOT" && node "$ARTIFACT_ROOT/javascript-install/package/src/cli.js" \
  --allow-sbgnml-0.2 "$LEGACY_INVALID_DOCUMENT" >javascript-legacy-invalid-result.json)
(cd "$ARTIFACT_ROOT" && node "$ARTIFACT_ROOT/javascript-install/package/src/cli.js" \
  --allow-sbgnml-0.2 "$LEGACY_VALID_DOCUMENT" >javascript-legacy-valid-result.json)
node "$ARTIFACT_ROOT/javascript-install/package/src/cli.js" \
  --rules-info >"$ARTIFACT_ROOT/info/javascript.json"
tar -tzf "$ARTIFACT_ROOT"/javascript/*.tgz >"$ARTIFACT_ROOT/javascript-files.txt"
grep -q package/resources/schematron/sbgn_pd.sch "$ARTIFACT_ROOT/javascript-files.txt"
javascript_package=$(find "$ARTIFACT_ROOT/javascript" -maxdepth 1 -name '*.tgz' -print -quit)
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rule_archive.py" \
  "$javascript_package" package/resources/schematron

(cd "$ROOT/go" && go build -o "$ARTIFACT_ROOT/sbgn-validator-go" ./cmd/validator)
(cd "$ARTIFACT_ROOT" && ./sbgn-validator-go "$INVALID_DOCUMENT" >go-invalid-result.json)
(cd "$ARTIFACT_ROOT" && ./sbgn-validator-go "$VALID_DOCUMENT" >go-valid-result.json)
(cd "$ARTIFACT_ROOT" && ./sbgn-validator-go --allow-sbgnml-0.2 \
  "$LEGACY_INVALID_DOCUMENT" >go-legacy-invalid-result.json)
(cd "$ARTIFACT_ROOT" && ./sbgn-validator-go --allow-sbgnml-0.2 \
  "$LEGACY_VALID_DOCUMENT" >go-legacy-valid-result.json)
"$ARTIFACT_ROOT/sbgn-validator-go" --rules-info >"$ARTIFACT_ROOT/info/go.json"

(cd "$ROOT/rust" && cargo package --allow-dirty >/dev/null)
mkdir -p "$ARTIFACT_ROOT/rust-package"
tar -xzf "$RUST_CRATE" -C "$ARTIFACT_ROOT/rust-package"
RUST_PACKAGE_DIR="$ARTIFACT_ROOT/rust-package/sbgn-validator-$PACKAGE_VERSION"
cargo build --release --manifest-path "$RUST_PACKAGE_DIR/Cargo.toml" \
  --bin sbgn-validator
RUST_BINARY="$RUST_PACKAGE_DIR/target/release/sbgn-validator"
(cd "$ARTIFACT_ROOT" && "$RUST_BINARY" \
  "$INVALID_DOCUMENT" >rust-invalid-result.json)
(cd "$ARTIFACT_ROOT" && "$RUST_BINARY" \
  "$VALID_DOCUMENT" >rust-valid-result.json)
(cd "$ARTIFACT_ROOT" && "$RUST_BINARY" --allow-sbgnml-0.2 \
  "$LEGACY_INVALID_DOCUMENT" >rust-legacy-invalid-result.json)
(cd "$ARTIFACT_ROOT" && "$RUST_BINARY" --allow-sbgnml-0.2 \
  "$LEGACY_VALID_DOCUMENT" >rust-legacy-valid-result.json)
"$RUST_BINARY" --rules-info >"$ARTIFACT_ROOT/info/rust.json"
tar -tf "$RUST_CRATE" >"$ARTIFACT_ROOT/rust-files.txt"
grep -q src/rules/data/sbgn_pd.sch "$ARTIFACT_ROOT/rust-files.txt"
grep -q vendor/schematron/src/schema/compile.rs "$ARTIFACT_ROOT/rust-files.txt"
grep -q vendor/schematron/src/validate/engine.rs "$ARTIFACT_ROOT/rust-files.txt"
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rule_archive.py" \
  "$RUST_CRATE" "sbgn-validator-$PACKAGE_VERSION/src/rules/data"

mkdir -p "$ARTIFACT_ROOT/r-library"
(cd "$ARTIFACT_ROOT" && R CMD build "$ROOT/r" >/dev/null)
R CMD INSTALL --library="$ARTIFACT_ROOT/r-library" \
  "$R_TARBALL" >/dev/null
R_EXEC=$(R_LIBS="$ARTIFACT_ROOT/r-library" Rscript -e \
  'cat(system.file("exec", "sbgn-validator", package = "sbgnvalidator"))')
(cd "$ARTIFACT_ROOT" && R_LIBS="$ARTIFACT_ROOT/r-library" Rscript "$R_EXEC" \
  "$INVALID_DOCUMENT" >r-invalid-result.json)
(cd "$ARTIFACT_ROOT" && R_LIBS="$ARTIFACT_ROOT/r-library" Rscript "$R_EXEC" \
  "$VALID_DOCUMENT" >r-valid-result.json)
(cd "$ARTIFACT_ROOT" && R_LIBS="$ARTIFACT_ROOT/r-library" Rscript "$R_EXEC" \
  --allow-sbgnml-0.2 "$LEGACY_INVALID_DOCUMENT" >r-legacy-invalid-result.json)
(cd "$ARTIFACT_ROOT" && R_LIBS="$ARTIFACT_ROOT/r-library" Rscript "$R_EXEC" \
  --allow-sbgnml-0.2 "$LEGACY_VALID_DOCUMENT" >r-legacy-valid-result.json)
R_LIBS="$ARTIFACT_ROOT/r-library" Rscript "$R_EXEC" \
  --rules-info >"$ARTIFACT_ROOT/info/r.json"
tar -tzf "$R_TARBALL" >"$ARTIFACT_ROOT/r-files.txt"
grep -q inst/schematron/sbgn_pd.sch "$ARTIFACT_ROOT/r-files.txt"
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rule_archive.py" \
  "$R_TARBALL" sbgnvalidator/inst/schematron

uv run --project "$ROOT/tools" python "$ROOT/tools/compare_rules_info.py" \
  "$ROOT/validation/rules/manifest.json" "$ARTIFACT_ROOT"/info/*.json
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_packaged_results.py" \
  --expected-rule pd10110 \
  "$ARTIFACT_ROOT"/{java,javascript,python,go,rust,r}-invalid-result.json
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_packaged_results.py" \
  --valid "$ARTIFACT_ROOT"/{java,javascript,python,go,rust,r}-valid-result.json
for rule_id in pd10102 pd10132 pd10141; do
  uv run --project "$ROOT/tools" python "$ROOT/tools/verify_packaged_results.py" \
    --expected-rule "$rule_id" "$ARTIFACT_ROOT"/*-legacy-invalid-result.json
done
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_packaged_results.py" \
  --valid "$ARTIFACT_ROOT"/*-legacy-valid-result.json
echo "Packaged-rule validation passed; artifacts are in $ARTIFACT_ROOT"
