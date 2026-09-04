#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)

mvn -q -f "$ROOT/java/pom.xml" test compile exec:java
uv run --project "$ROOT/tools" python "$ROOT/tools/verify_oracle.py" \
  --manifest "$ROOT/conformance/manifest.json" --oracle-root "$ROOT"
