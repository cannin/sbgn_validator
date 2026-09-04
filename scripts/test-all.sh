#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
REPOSITORY_ROOT=$ROOT
PACKAGE_VERSION=$(tr -d '\r\n' <"$ROOT/VERSION")

uv run --project "$ROOT/tools" python "$ROOT/tools/verify_rules.py"
uv run --project "$ROOT/tools" pytest -q "$ROOT/tools/test_rules_sync.py"
uv run --project "$ROOT/tools" ruff check "$ROOT/tools"
uv run --project "$ROOT/tools" python "$ROOT/tools/check_versions.py"
mvn -q -f "$ROOT/java/pom.xml" test
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_oracle.py" \
  --manifest "$ROOT/conformance/manifest.json" --oracle-root "$ROOT"

(
  cd "$ROOT/python"
  uv sync --extra test
  uv run --extra test ruff check .
  uv run --extra test pytest
  uv run python generate_results.py
)
uv run --project "$ROOT/tools" python "$ROOT/tools/compare_results.py" python \
  --benchmark-root "$ROOT"

node_major=$(node -p 'process.versions.node.split(".")[0]')
if ((node_major < 18)); then
  echo "JavaScript tests require Node 18 or newer" >&2
  exit 1
fi
(
  cd "$ROOT/javascript"
  npm ci
  npm test
  npm run results
)
uv run --project "$ROOT/tools" python "$ROOT/tools/compare_results.py" javascript \
  --benchmark-root "$ROOT"

(
  cd "$ROOT/go"
  go test ./...
  go vet ./...
  mkdir -p dist
  go build -o dist/generate-results ./cmd/generate-results
  ./dist/generate-results
)
uv run --project "$ROOT/tools" python "$ROOT/tools/compare_results.py" go \
  --benchmark-root "$ROOT"

(
  cd "$ROOT/rust"
  cargo fmt --check
  cargo test
  cargo build --quiet --release --bin generate_results
  ./target/release/generate_results
)
uv run --project "$ROOT/tools" python "$ROOT/tools/compare_results.py" rust \
  --benchmark-root "$ROOT"

R CMD INSTALL --preclean "$ROOT/r"
Rscript -e 'lints <- c(lintr::lint(commandArgs(TRUE)[1]), lintr::lint(commandArgs(TRUE)[2])); print(lints); quit(status = length(lints) > 0)' \
  "$ROOT/r/R/validator.R" "$ROOT/r/generate_results.R"
(
  cd "$ROOT"
  R CMD build r
)
r_tarball="$ROOT/sbgnvalidator_$PACKAGE_VERSION.tar.gz"
r_check_dir=$(mktemp -d "${TMPDIR:-/tmp}/libsbgn-r-check.XXXXXX")
LIBSBGN_REPO_ROOT="$REPOSITORY_ROOT" R CMD check --no-manual \
  --output="$r_check_dir" "$r_tarball"
(
  cd "$ROOT/r"
  Rscript generate_results.R
)
uv run --project "$ROOT/tools" python "$ROOT/tools/compare_results.py" r \
  --benchmark-root "$ROOT"

uv run --project "$ROOT/tools" python "$ROOT/tools/generate_capability_matrix.py" \
  --benchmark-root "$ROOT"
