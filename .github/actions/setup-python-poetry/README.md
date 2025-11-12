# Setup Python and Poetry

Composite action that sets up Python with Poetry and installs project dependencies.

## Usage

```yaml
- uses: actions/checkout@v4
- uses: ./.github/actions/setup-python-poetry
  with:
    python-version: "3.14"
```

## Inputs

### `python-version`

**Required**: Yes  
**Default**: `'3.14'`

The Python version to set up.

## What This Action Does

1. Sets up Python with the specified version
2. Caches Poetry dependencies for faster runs
3. Installs Poetry
4. Configures Poetry to use in-project virtualenv
5. Installs project dependencies

## Cache Strategy

The action caches:

- `~/.cache/pypoetry` - Poetry's global cache
- `.venv` - Project virtualenv

Cache key: `${{ runner.os }}-poetry-${{ inputs.python-version }}-${{ hashFiles('poetry.lock') }}`

This ensures fast CI runs by reusing dependencies when `poetry.lock` hasn't changed.
