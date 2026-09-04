# libSBGN integration note

This vendored engine source is compiled directly into the `sbgn-validator`
crate through path-based modules in `rust/src/lib.rs`. This keeps the published
crate self-contained and preserves the profile fixes required by the libSBGN
rules.

`Cargo.toml.orig` records the upstream crate manifest. It intentionally is not
named `Cargo.toml`: Cargo excludes nested packages from an outer `.crate`, even
when their paths are listed explicitly, which previously caused published
`sbgn-validator` crates to substitute an incompatible registry engine.
