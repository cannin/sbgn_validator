# Authoritative Schematron rules

Edit the `.sch` files in this directory only. Package-local copies are
generated artifacts and must not be edited directly.

After changing a schema, run:

```sh
uv run --project tools python tools/sync_rules.py
uv run --project tools python tools/verify_rules.py
```

`manifest.json` is generated from the exact schema bytes.
