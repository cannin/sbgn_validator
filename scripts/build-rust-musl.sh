#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MUSL_TARGET=${RUST_MUSL_TARGET:-x86_64-unknown-linux-musl}

rustup target add "$MUSL_TARGET"
cargo build \
  --manifest-path "$ROOT/rust/Cargo.toml" \
  --release \
  --target "$MUSL_TARGET" \
  --bin sbgn-validator

printf 'Built %s\n' \
  "$ROOT/rust/target/$MUSL_TARGET/release/sbgn-validator"
