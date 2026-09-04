#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
EXPECTED_VERSION=${1:-$(tr -d '\r\n' <"$ROOT/VERSION")}
ACTUAL_VERSION=$(tr -d '\r\n' <"$ROOT/VERSION")

if [[ "$ACTUAL_VERSION" != "$EXPECTED_VERSION" ]]; then
  printf 'Root version is %s; expected %s\n' \
    "$ACTUAL_VERSION" "$EXPECTED_VERSION" >&2
  exit 1
fi

uv run --project "$ROOT/tools" python "$ROOT/tools/check_versions.py"
printf 'Release version is %s across all six validators.\n' "$EXPECTED_VERSION"
