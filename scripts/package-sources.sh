#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUTPUT_DIRECTORY=${1:-"$ROOT/dist"}
RELEASE_REF=${2:-HEAD}
VERSION=$(tr -d '\r\n' <"$ROOT/VERSION")

mkdir -p "$OUTPUT_DIRECTORY"

git -C "$ROOT" archive \
  --format=tar.gz \
  --prefix="sbgn_validator-$VERSION/" \
  --output="$OUTPUT_DIRECTORY/sbgn_validator-$VERSION-all-source.tar.gz" \
  "$RELEASE_REF"

for language in java javascript python r rust go; do
  git -C "$ROOT" archive \
    --format=tar.gz \
    --prefix="sbgn_validator-$language-$VERSION/" \
    --output="$OUTPUT_DIRECTORY/sbgn_validator-$language-$VERSION-source.tar.gz" \
    "$RELEASE_REF:$language"
done

printf 'Packaged source archives from %s in %s\n' \
  "$RELEASE_REF" "$OUTPUT_DIRECTORY"
