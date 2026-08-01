# flat-adapter

`flat-adapter` converts nested mappings into deterministic flat rows suitable
for database imports and ETL pipelines.

## Quick start

```python
from flat_adapter import FlatAdapter


class ItemAdapter(FlatAdapter):
    item_id: int
    quantity: int


class OrderAdapter(FlatAdapter):
    order_id: int
    items: list[ItemAdapter]


rows = OrderAdapter.adapt(
    {
        "order_id": "1001",
        "items": [
            {"item_id": "10", "quantity": "2"},
            {"item_id": "20", "quantity": "1"},
        ],
    }
)
```

Result:

```python
[
    {"order_id": 1001, "item_id": 10, "quantity": 2},
    {"order_id": 1001, "item_id": 20, "quantity": 1},
]
```

## v0.1 contract

- Input is `Mapping[str, object]` with nested mappings and lists.
- The result is always `list[dict[str, object]]`.
- Multiple nested lists produce a deterministic Cartesian product.
- Input order and declared field order are preserved.
- Unknown input keys are ignored.
- Missing required fields, conversion failures, invalid nested shapes, and
  duplicate output keys raise typed exceptions.
- Empty or `None` nested lists preserve the parent row and fill child fields
  with `None`.
- `None` for a required nested object raises an error.
- Dataclasses, Pydantic models, database integrations, and HTTP APIs are
  outside the current scope.

## Field configuration without `cast`

Use `typing.Annotated` to attach extraction metadata without a runtime
assignment or a `cast`:

```python
from typing import Annotated

from flat_adapter import Field, FlatAdapter


class CustomerAdapter(FlatAdapter):
    customer_id: Annotated[int, Field(source="payload.customer_id")]
    display_name: Annotated[str, Field(source="payload.name", default="Unknown")]
```

The legacy `name: int = Field(...)` form remains supported at runtime, but
`Annotated` is preferred for `mypy --strict` projects.

## Performance and row limits

Seven to ten nested adapter levels are normally safe; the main cost comes
from Cartesian expansion. For list lengths `L1`, `L2`, ..., the result count
can grow as `product(max(1, len(Li)))`, and returned rows are materialized in
memory.

Use `max_rows` to fail fast before an expansion becomes too large:

```python
rows = OrderAdapter.adapt(payload, max_rows=10_000)
```

Run the local benchmark scenarios with:

```bash
uv run python benchmarks/flatten_benchmark.py
```

## Development

The project uses [uv](https://docs.astral.sh/uv/) for environments,
dependencies, and lockfile management.

```bash
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest --cov=flat_adapter --cov-report=term-missing
uv run ruff check src tests
uv run mypy --strict src tests
uv build
uv run twine check dist/*
```

## Package layout

```text
src/flat_adapter/  Library package
tests/unit/        Pure behavior tests
docs/              English and Russian guides and promotion notes
benchmarks/        Manual performance scenarios
```

See [CONTEXT.md](../CONTEXT.md) for architecture boundaries and
[TECHDEBT.md](../TECHDEBT.md) for known risks.

Русская версия: [README.ru.md](README.ru.md).

## Versioning

Releases follow Semantic Versioning. While the package is below `1.0.0`, a
minor release may include a documented contract change; patch releases remain
backward-compatible fixes. `CHANGELOG.md` records user-visible changes.
