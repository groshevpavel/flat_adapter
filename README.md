# flat-adapter

`flat-adapter` is a Python library for converting nested hierarchical data into
flat records suitable for database imports.

The current source is a recovered prototype. Its public contract and production
architecture are intentionally not finalized yet; see `CONTEXT.md` and
`TECHDEBT.md` before implementing new behavior.

## Development

The project uses [uv](https://docs.astral.sh/uv/) for environments,
dependencies, and lockfile management.

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run mypy --strict src tests
uv build
```

## Package layout

```text
src/flat_adapter/  Library package
tests/             Unit and future integration tests
```
