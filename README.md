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

assert rows == [
    {"order_id": 1001, "item_id": 10, "quantity": 2},
    {"order_id": 1001, "item_id": 20, "quantity": 1},
]
```

The first release supports `Mapping[str, object]` input, nested mappings,
typed scalar conversion, optional fields, aliases, custom `Field` paths, and
deterministic Cartesian expansion of nested lists. `adapt()` returns
`list[dict[str, object]]`; `iter_adapt()` returns an iterator over the same
rows.

## Field configuration

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
`Annotated` is the preferred form for `mypy --strict` projects.

## Performance and row limits

Depth of seven to ten nested adapters is normally safe; the main cost comes
from Cartesian expansion. For list lengths `L1`, `L2`, ..., the result count
can grow as `product(max(1, len(Li)))`. `adapt()` materializes all rows in
memory, while `iter_adapt()` yields them lazily.

Use `max_rows` to fail fast before an expansion becomes too large. The limit
works with both eager and lazy APIs:

```python
rows = OrderAdapter.adapt(payload, max_rows=10_000)
```

For large results, consume rows lazily:

```python
for row in OrderAdapter.iter_adapt(payload, max_rows=10_000):
    process(row)
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
docs/              English/Russian guides and promotion notes
benchmarks/        Manual performance scenarios
```

See [CONTEXT.md](CONTEXT.md) for architecture boundaries and
[TECHDEBT.md](TECHDEBT.md) for known risks.

Русская версия руководства: [docs/README.ru.md](docs/README.ru.md).
English guide: [docs/README.en.md](docs/README.en.md).

## Versioning

Releases follow Semantic Versioning. While the package is below `1.0.0`, a
minor release may include a documented contract change; patch releases remain
backward-compatible fixes. `CHANGELOG.md` records user-visible changes.
