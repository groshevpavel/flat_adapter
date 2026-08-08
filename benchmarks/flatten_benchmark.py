"""Run repeatable local benchmarks for depth, width, and row expansion."""

from __future__ import annotations

import time
import types
from collections.abc import Mapping
from itertools import islice

from flat_adapter import FlatAdapter


class LeafAdapter(FlatAdapter):
    """Adapt one scalar value for benchmark payloads."""

    value: int


class WidthAdapter(FlatAdapter):
    """Expand one large list for the width benchmark."""

    items: list[LeafAdapter]


class FirstProductAdapter(FlatAdapter):
    """Adapt the first dimension of the Cartesian benchmark."""

    first: int


class SecondProductAdapter(FlatAdapter):
    """Adapt the second dimension of the Cartesian benchmark."""

    second: int


class ThirdProductAdapter(FlatAdapter):
    """Adapt the third dimension of the Cartesian benchmark."""

    third: int


class ProductAdapter(FlatAdapter):
    """Expand three independent list dimensions."""

    first_items: list[FirstProductAdapter]
    second_items: list[SecondProductAdapter]
    third_items: list[ThirdProductAdapter]


def _make_deep_case(depth: int) -> tuple[type[FlatAdapter], Mapping[str, object]]:
    """Build a mixed mapping/list adapter and matching payload."""
    adapter: type[FlatAdapter] = type(
        "BenchmarkLeafAdapter",
        (FlatAdapter,),
        {
            "__annotations__": {"value": int},
            "__doc__": "Adapt the leaf value of a deep benchmark.",
        },
    )
    payload: dict[str, object] = {"value": "7"}

    for level in range(depth, 0, -1):
        field_name = f"level_{level}"
        is_list = level % 2 == 0
        annotation: object = types.GenericAlias(list, adapter) if is_list else adapter
        payload = {field_name: [payload] if is_list else payload}
        adapter = type(
            f"BenchmarkLevel{level}Adapter",
            (FlatAdapter,),
            {
                "__annotations__": {field_name: annotation},
                "__doc__": f"Adapt deep benchmark level {level}.",
            },
        )

    return adapter, payload


def _make_wide_case(columns: int) -> tuple[type[FlatAdapter], Mapping[str, object]]:
    """Build a flat adapter with a configurable number of scalar columns."""
    annotations = {f"column_{index}": int for index in range(columns)}
    payload = {field_name: str(index) for index, field_name in enumerate(annotations)}
    adapter = type(
        f"BenchmarkWide{columns}Adapter",
        (FlatAdapter,),
        {
            "__annotations__": annotations,
            "__doc__": f"Adapt {columns} flat benchmark columns.",
        },
    )
    return adapter, payload


def _measure(
    name: str,
    adapter: type[FlatAdapter],
    payload: Mapping[str, object],
    expected_rows: int,
    runs: int = 5,
) -> None:
    """Measure repeated adaptation and print the fastest and average times."""
    durations: list[float] = []
    for _ in range(runs):
        started_at = time.perf_counter()
        rows = adapter.adapt(payload, max_rows=expected_rows)
        durations.append(time.perf_counter() - started_at)
        if len(rows) != expected_rows:
            raise RuntimeError(f"{name} returned {len(rows)} rows, expected {expected_rows}")

    fastest = min(durations)
    average = sum(durations) / len(durations)
    print(f"{name}: rows={expected_rows}, fastest={fastest:.6f}s, average={average:.6f}s")


def _measure_lazy_prefix(
    name: str,
    adapter: type[FlatAdapter],
    payload: Mapping[str, object],
    expected_rows: int,
    prefix: int,
    runs: int = 5,
) -> None:
    """Measure the time needed to consume only a lazy result prefix."""
    durations: list[float] = []
    for _ in range(runs):
        started_at = time.perf_counter()
        rows = list(islice(adapter.iter_adapt(payload, max_rows=expected_rows), prefix))
        durations.append(time.perf_counter() - started_at)
        if len(rows) != prefix:
            raise RuntimeError(f"{name} returned {len(rows)} rows, expected {prefix}")

    fastest = min(durations)
    average = sum(durations) / len(durations)
    print(f"{name}: consumed={prefix}, total_rows={expected_rows}, fastest={fastest:.6f}s, average={average:.6f}s")


def main() -> None:
    """Run the benchmark scenarios used for local performance comparisons."""
    deep_adapter, deep_payload = _make_deep_case(10)
    _measure("depth-10", deep_adapter, deep_payload, expected_rows=1)

    width_payload = [{"value": str(value)} for value in range(1_000)]
    _measure(
        "width-1000",
        WidthAdapter,
        {"items": width_payload},
        expected_rows=1_000,
    )

    product_payload = {
        "first_items": [{"first": str(value)} for value in range(10)],
        "second_items": [{"second": str(value)} for value in range(10)],
        "third_items": [{"third": str(value)} for value in range(10)],
    }
    _measure("cartesian-10x10x10", ProductAdapter, product_payload, expected_rows=1_000)
    _measure_lazy_prefix(
        "cartesian-lazy-first-10",
        ProductAdapter,
        product_payload,
        expected_rows=1_000,
        prefix=10,
    )

    wide_adapter, wide_payload = _make_wide_case(20)
    _measure("flat-columns-20", wide_adapter, wide_payload, expected_rows=1)


if __name__ == "__main__":
    main()
