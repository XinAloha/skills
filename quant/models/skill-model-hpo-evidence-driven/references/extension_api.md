# Extension API

Current API version: `2`. Version 2 removes validation/holdout targets from feature transformation and adds optional sample weights to model fitting.

The extension layer separates user-specific factor access and model code from the stable HPO core.

```text
explicit plugin module
        |
        v
ExtensionRegistry
   | factor provider -> canonical PanelData
   | feature pipeline -> target-isolated feature frames
   | model plugin     -> parameter normalization + model instance
        |
        v
search -> evidence -> guarded decision -> multi-seed confirmation
                                                    |
                                                    v
                                      separate audited holdout
```

The runtime does not scan directories, download code, install packages, or evaluate source strings. An external module must declare `HPO_EXTENSION_API_VERSION = 2` and is imported only when all three fields are present:

```json
{
  "extensions": {
    "allow_external": true,
    "plugin_roots": ["/absolute/path/to/my_hpo_extensions"],
    "modules": ["my_project_hpo"]
  }
}
```

- `allow_external`: explicit authorization to import local user code.
- `plugin_roots`: directories allowed to contain imported modules. Relative paths are resolved from the input JSON or YAML.
- `modules`: importable module names without `.py`. Each module must expose `register(registry)`.

Start from `extension_templates/example_extensions.py`. The template directory is the isolated user-facing example area; production extension files should live in a user-owned project directory outside this skill so skill upgrades do not overwrite them.

## Factor Provider

Register a factory:

```python
registry.register_factor_provider("my_provider", MyProvider)
```

The runtime calls `MyProvider(params)` and then `provider.load(cfg)`. During search, provider output must not contain rows beyond the resolved validation boundary.

- `params`: mapping from `data.provider.params`; use it for dataset names, factor lists, or provider-specific options.
- `cfg`: full resolved HPO config.
- return value: `data_adapter.PanelData`.

`PanelData` fields:

- `panel`: pandas DataFrame with canonical `date`, `ticker`, `y`, and factor columns.
- `feature_columns`: non-empty list of numeric factor column names used by the model.
- `warnings`: data-quality or point-in-time warnings.
- `metadata`: reproducibility metadata written into `search_manifest.json`.

The runtime rejects empty panels, duplicate `(date, ticker)` keys, missing canonical columns, undeclared factor columns, and non-numeric factors.

Use the provider only for data access and schema adaptation. It must not select factors or transform data using validation/test labels. The built-in `file_panel` provider retains the original CSV/parquet behavior.

Configuration:

```json
{
  "data": {
    "provider": {
      "name": "my_provider",
      "params": {"dataset": "daily_factors_v3"}
    }
  }
}
```

## Feature Pipeline

Register a factory:

```python
registry.register_feature_pipeline("my_pipeline", MyPipeline)
```

For every model and walk-forward window, the runtime creates a new pipeline instance and calls:

```python
pipeline.fit(
    X_train,
    y_train,
    train_context,
    feature_columns,
    cfg,
    normalize_method=normalize_method,
    preserve_nan=preserve_nan,
)
train_out = pipeline.transform(X_train, train_context, ...)
valid_out = pipeline.transform(X_valid, valid_context, ...)
```

Variables:

- `X_train`: current training factors only.
- `y_train`: training target supplied only to `fit`.
- `X_valid`: validation factors; it never contains `y`.
- `train_context` and `valid_context`: `date` and `ticker` only.
- `feature_columns`: canonical factor list from the provider.
- `cfg`: full resolved HPO config.
- `normalize_method`: optional trial-level normalization override.
- `preserve_nan`: whether the selected model plugin declares native missing-value support.

`transform` must return exactly the declared numeric feature columns while preserving index and row order. It cannot access validation or holdout targets. A supervised transformer may use `y_train` in `fit`, but target-dependent state must be estimated from training rows only.

Configuration:

```json
{
  "features": {
    "pipeline": {
      "name": "my_pipeline",
      "params": {"clip": 5.0}
    }
  }
}
```

## Model Plugin

A model plugin object defines:

```python
class MyModelPlugin:
    name = "my_model"
    aliases = ("my_model_v1",)
    capabilities = ModelCapabilities(accepts_nan=False)

    def default_search_space(self): ...
    def normalize_params(self, params): ...
    def create(self, params, seed): ...
    def prepare_features(self, features, cfg): ...
```

Register it with:

```python
registry.register_model_plugin(MyModelPlugin())
```

Variables and return contracts:

- `name`: canonical value used in artifacts and trial IDs.
- `aliases`: optional accepted config names.
- `capabilities.accepts_nan`: controls whether preprocessing preserves missing values.
- `default_search_space()`: returns the standard `search.space` mapping used when users omit it.
- `normalize_params(params)`: casts and adds model-specific fixed parameters; it must be deterministic.
- `create(params, seed)`: returns a model with `fit(X, y, sample_weight=None)`, `predict(X)`, and `complexity()`.
- `prepare_features(features, cfg)`: receives feature columns only and handles model-specific missing values.
- `seed`: trial/window seed supplied by the runtime.
- `capabilities.supports_sample_weight`: must be true when `training.sample_weight` is enabled.
- `complexity()`: mapping used by the existing complexity penalty; set `model_family_complexity` when relevant.

Configuration:

```json
{
  "model": {
    "type": "my_model",
    "plugin": "my_model"
  },
  "search": {
    "model_type": "my_model",
    "sampler": "adaptive"
  }
}
```

External models support the generic `adaptive` sampler and deterministic `grid` search. The built-in structured probes encode LGBM/MLP-specific directions, so `evidence_probe`, `structured_probe`, and `local_probe` remain limited to those built-in model families.

## Registration Example

Every external module must expose:

```python
def register(registry):
    registry.register_factor_provider("my_provider", MyProvider)
    registry.register_feature_pipeline("my_pipeline", MyPipeline)
    registry.register_model_plugin(MyModelPlugin())
```

Run the complete bundled example:

```bash
python scripts/run_hpo_search.py --input examples/hpo_custom_extension_smoke.json
```

`search_manifest.json` records the selected component names and each external module's resolved file, SHA-256, and optional `__version__`.
