# Project Context

## Project Overview

`flat-adapter` is a Python library intended to convert nested hierarchical
structures into flat records for convenient database loading.

The repository currently contains a recovered prototype from a screen
recording. The behavior, public API, compatibility guarantees, and production
architecture still require an explicit ANALYZE/ARCHITECT step.

## Architecture

Current state: a small synchronous library with two modules:

`flat_adapter.adapter` → `flat_adapter.base`

There are no routers, services, repositories, ORM models, database
integrations, or HTTP APIs. The library should remain dependency-light and
synchronous unless a future requirement explicitly changes that boundary.

## Directory Structure

```text
src/flat_adapter/
├── __init__.py
├── adapter.py
├── base.py
└── py.typed
```

Tests and documentation infrastructure are scaffolded but behavior tests have
not yet been written.

## Dependencies

- Runtime: `python-dateutil`
- Development: `pytest`, `pytest-asyncio`, `pytest-cov`, `mypy`, `ruff`,
  `build`, and `twine`
- Package manager: `uv`
- Supported Python: 3.10+

No database, web framework, ORM, or async runtime is part of the current
library boundary.

## Conventions

- Use typed public APIs and Google-style docstrings for new public code.
- Keep source under `src/flat_adapter`.
- Keep runtime dependencies minimal.
- Use `uv` for dependency changes and keep `uv.lock` committed.
- New behavior follows RED → GREEN → REFACTOR TDD.
- Run `uv run ruff check src tests` and
  `uv run mypy --strict src tests` before completing Python changes.
- Prefer deterministic, explicit type/adapter registration over global module
  discovery.

## Known Patterns

- `AdapterBase` describes annotation-driven field metadata and scalar
  conversion.
- `FlatAdapter` recursively adapts nested adapters and combines list results.
- `Field` is a callable field descriptor for custom source paths, defaults, and
  preprocessing.

These patterns are recovered behavior, not yet an approved production
contract.

## Tech Debt Summary

See `TECHDEBT.md`. The top priorities are:

1. Establish executable tests for the recovered behavior.
2. Validate and, where necessary, redesign type introspection and nested-list
   flattening.
3. Replace placeholder package metadata and define the release contract.
