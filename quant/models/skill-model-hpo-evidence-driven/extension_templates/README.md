# User Extension Templates

`example_extensions.py` is a runnable reference for the three supported user extension points:

- factor provider
- feature pipeline
- model plugin

For production use, place your implementation in a separate user-owned directory, import only dependencies you control, expose `register(registry)`, and point `extensions.plugin_roots` at that directory. Keeping production code outside this skill prevents a future skill update from overwriting user changes.

Run the bundled example from the skill root:

```bash
python scripts/run_hpo_search.py --input examples/hpo_custom_extension_smoke.json
```

Read `references/extension_api.md` before changing method signatures or return values.
