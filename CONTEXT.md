# Project Context

## Project Overview

`flat-adapter` is a Python library intended to convert nested hierarchical
structures into flat records for convenient database loading.

The recovered prototype has been converted into a tested v0.1 core. The
approved behavior and remaining release work are recorded below.

## Architecture

Current state: a small synchronous library with a pure transformation core:

`flat_adapter.adapter` → `flat_adapter.base` → `flat_adapter.errors`

The production target is a compact pipeline:

`Mapping input` → `compiled schema` → `field extraction` → `scalar conversion`
→ `list expansion` → `collision validation` → `flat rows`

There are no routers, services, repositories, ORM models, database
integrations, or HTTP APIs. The library remains dependency-light and
synchronous unless a future requirement explicitly changes that boundary.

## Directory Structure

```text
src/flat_adapter/
├── __init__.py
├── adapter.py
├── base.py
├── errors.py
└── py.typed
tests/
└── unit/
docs/
├── README.en.md
├── README.ru.md
└── PROMOTION.md
benchmarks/
└── flatten_benchmark.py
```

Behavior tests live under `tests/unit`; CI and release workflows live under
`.github/workflows`.

## Dependencies

- Runtime: `python-dateutil`
- Development: `pytest`, `pytest-asyncio`, `pytest-cov`, `mypy`, `ruff`,
  `types-python-dateutil`, `pre-commit`, `build`, and `twine`
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
- Run `uv run pre-commit run --all-files` before handing off repository changes.
- Prefer deterministic, explicit type/adapter registration over global module
  discovery.
- Public transformation failures use the `FlatAdapterError` hierarchy.

## Known Patterns

- `AdapterBase` describes annotation-driven field metadata and scalar
  conversion.
- `FlatAdapter` recursively adapts nested adapters and combines list results.
- `Field` is field metadata for custom source paths, defaults, and
  preprocessing; `typing.Annotated` is the preferred strict-typing syntax.

## Approved v0.1 Contract

- `FlatAdapter.adapt()` returns `list[dict[str, object]]` for every input.
- Inputs are `Mapping[str, object]` values with nested mappings and lists.
- Class annotations define fields; a string class attribute is the input alias
  and output column name.
- `Field` metadata may be attached with `Annotated[T, Field(...)]`; the legacy
  class-assignment form remains runtime-compatible.
- Multiple nested lists expand using a deterministic Cartesian product.
- Input order and declared field order are preserved.
- Unknown input keys are ignored.
- Missing required fields, invalid nested shapes, conversion failures, and
  duplicate output keys raise typed adapter exceptions.
- Optional missing values become `None`.
- An empty or `None` nested list preserves the parent row and fills the nested
  fields with `None`.
- A `None` required nested object raises an error.
- `max_rows` is an optional positive fail-fast limit for complete expansion;
  exceeding it raises `RowLimitExceeded`.
- Sets are not accepted as list-like input because their order is not
  deterministic.
- Dataclasses, Pydantic models, columnar output, and DB/HTTP integrations are
  outside v0.1.

## Tech Debt Summary

See `TECHDEBT.md`. The top priorities are:

1. Verify the package on Python 3.10–3.13 in CI.
2. Confirm the release/versioning policy before the first PyPI upload.
3. Keep English and Russian guides synchronized with public API changes.
